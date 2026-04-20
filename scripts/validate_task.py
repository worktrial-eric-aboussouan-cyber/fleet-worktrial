#!/usr/bin/env python3
"""Two-canary validation gate for each task.

Canary 1: gold patch applied  → eval_script exits 0
Canary 2: no patch            → eval_script exits non-0
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

TASKS_DIR = Path(__file__).parent.parent / "tasks"
FAILURES_LOG = Path(__file__).parent.parent / "validation_failures.log"
CANARY1_RETRIES = 3  # for flaky-test detection


def log_failure(instance_id: str, category: str, detail: str = ""):
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    line = f"{ts} | {instance_id} | {category} | {detail}\n"
    with open(FAILURES_LOG, "a") as f:
        f.write(line)
    print(f"  FAIL [{category}]: {detail[:120]}", flush=True)


def docker_build(task_dir: Path, tag: str) -> tuple[bool, str]:
    result = subprocess.run(
        ["docker", "build", "-t", tag, "."],
        cwd=task_dir,
        capture_output=True,
        text=True,
        timeout=600,
    )
    return result.returncode == 0, result.stderr[-2000:] if result.returncode != 0 else ""


def run_eval(tag: str, patch_file: str | None, timeout: int = 120) -> tuple[int, str]:
    """Run eval_script.sh inside container, optionally applying patch_file first."""
    if patch_file:
        cmd = [
            "docker", "run", "--rm", "--network", "none",
            "-e", "PYTHONDONTWRITEBYTECODE=1",
            "-v", f"{patch_file}:/tmp/patch.diff:ro",
            tag,
            "/bin/bash", "-c",
            "cd /repo && git apply /tmp/patch.diff && bash /eval_script.sh",
        ]
    else:
        cmd = [
            "docker", "run", "--rm", "--network", "none",
            "-e", "PYTHONDONTWRITEBYTECODE=1",
            tag,
            "/bin/bash", "-c", "bash /eval_script.sh",
        ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    output = (result.stdout + result.stderr)[-1000:]
    return result.returncode, output


def validate_task(task_dir: Path) -> tuple[bool, str]:
    task_json = json.loads((task_dir / "task.json").read_text())
    instance_id = task_json["instance_id"]
    gold_patch = task_json.get("gold_patch", "")
    tag = f"swe-validate-{instance_id}:latest"

    print(f"\nValidating {instance_id} ...", flush=True)

    # Build
    print("  Building image...", flush=True)
    ok, err = docker_build(task_dir, tag)
    if not ok:
        log_failure(instance_id, "build_failed", err)
        return False, "build_failed"

    # Canary 2 first — cheaper to catch trivially-passing tests early
    print("  Canary 2: empty patch should FAIL...", flush=True)
    try:
        rc, out = run_eval(tag, None)
    except subprocess.TimeoutExpired:
        log_failure(instance_id, "canary2_timeout")
        return False, "canary2_timeout"
    if rc == 0:
        log_failure(instance_id, "canary2_empty_passed", out)
        return False, "canary2_empty_passed"
    print("  ✓ Canary 2 passed (tests fail without patch)", flush=True)

    # Canary 1 — gold patch should pass; retry up to CANARY1_RETRIES for flakiness
    if not gold_patch.strip():
        log_failure(instance_id, "no_gold_patch")
        return False, "no_gold_patch"

    patch_file_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".diff", mode="w", encoding="utf-8") as f:
            f.write(gold_patch)
            patch_file_path = f.name

        results = []
        for attempt in range(CANARY1_RETRIES):
            print(f"  Canary 1: gold patch should PASS (attempt {attempt+1}/{CANARY1_RETRIES})...", flush=True)
            try:
                rc, out = run_eval(tag, patch_file_path)
            except subprocess.TimeoutExpired:
                results.append(("timeout", ""))
                continue
            results.append((rc, out))
            if rc == 0:
                break

        passing = [r for r in results if r[0] == 0]
        if not passing:
            last_rc, last_out = results[-1]
            if last_rc == "timeout":
                log_failure(instance_id, "canary1_timeout")
                return False, "canary1_timeout"
            
            if last_rc == 128 or "patch does not apply" in last_out:
                log_failure(instance_id, "patch_apply_failed", last_out)
                return False, "patch_apply_failed"
            else:
                log_failure(instance_id, "gold_patch_tests_failed", last_out)
                return False, "gold_patch_tests_failed"

        if len(passing) < CANARY1_RETRIES:
            log_failure(instance_id, "canary1_flaky",
                        f"{len(passing)}/{CANARY1_RETRIES} runs passed")
            return False, "canary1_flaky"

        print(f"  ✓ Canary 1 passed ({CANARY1_RETRIES}/{CANARY1_RETRIES} runs)", flush=True)
    finally:
        if patch_file_path and os.path.exists(patch_file_path):
            os.unlink(patch_file_path)

    # Clean up validation image
    subprocess.run(["docker", "rmi", tag], capture_output=True)
    return True, "ok"


def main():
    parser = argparse.ArgumentParser(description="Two-canary validation gate for each task.")
    parser.add_argument("--all", action="store_true", help="Validate all task_* directories in TASKS_DIR")
    parser.add_argument("--parallel", type=int, default=1, help="Number of parallel workers")
    parser.add_argument("tasks", nargs="*", help="Specific task directories to validate")
    args = parser.parse_args()

    if args.all or not args.tasks:
        task_dirs = sorted(TASKS_DIR.glob("task_*"))
    else:
        task_dirs = [Path(p) for p in args.tasks]

    task_dirs = [d for d in task_dirs if d.is_dir() and (d / "task.json").exists()]

    if not task_dirs:
        print("No tasks found to validate.")
        return

    print(f"Validating {len(task_dirs)} tasks with {args.parallel} workers...", flush=True)

    results = {"ok": [], "failed": {}}

    if args.parallel > 1:
        with ThreadPoolExecutor(max_workers=args.parallel) as executor:
            future_to_dir = {executor.submit(validate_task, d): d for d in task_dirs}
            for future in as_completed(future_to_dir):
                task_dir = future_to_dir[future]
                instance_id = json.loads((task_dir / "task.json").read_text())["instance_id"]
                try:
                    ok, category = future.result()
                    if ok:
                        results["ok"].append(instance_id)
                    else:
                        results["failed"][instance_id] = category
                except Exception as e:
                    print(f"  ERROR [executor]: {instance_id} failed with {e}", flush=True)
                    results["failed"][instance_id] = "executor_error"
    else:
        for task_dir in task_dirs:
            ok, category = validate_task(task_dir)
            instance_id = json.loads((task_dir / "task.json").read_text())["instance_id"]
            if ok:
                results["ok"].append(instance_id)
            else:
                results["failed"][instance_id] = category

    print(f"\n=== Validation Summary ===")
    print(f"Passed: {len(results['ok'])}")
    print(f"Failed: {len(results['failed'])}")
    for iid, cat in sorted(results["failed"].items()):
        print(f"  {iid}: {cat}")

    # write summary to tasks/validation_summary.json
    summary_path = TASKS_DIR / "validation_summary.json"
    with open(summary_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSummary written to {summary_path}")


if __name__ == "__main__":
    main()
