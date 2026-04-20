#!/usr/bin/env python3
"""Two-canary validation gate for each task.

Canary 1: gold patch applied  → eval_script exits 0
Canary 2: no patch            → eval_script exits non-0
"""

import json
import subprocess
import sys
import tempfile
import time
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


def run_eval(tag: str, gold_patch: str | None, timeout: int = 120) -> tuple[int, str]:
    """Run eval_script.sh inside container, optionally applying gold_patch first."""
    if gold_patch:
        cmd = [
            "docker", "run", "--rm", "--network", "none",
            "-e", "PYTHONDONTWRITEBYTECODE=1",
            tag,
            "/bin/bash", "-c",
            f"cd /repo && git apply - <<'PATCH_EOF'\n{gold_patch}\nPATCH_EOF\n"
            "bash /eval_script.sh",
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

    results = []
    for attempt in range(CANARY1_RETRIES):
        print(f"  Canary 1: gold patch should PASS (attempt {attempt+1}/{CANARY1_RETRIES})...", flush=True)
        try:
            rc, out = run_eval(tag, gold_patch)
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
        log_failure(instance_id, "canary1_gold_failed", last_out)
        return False, "canary1_gold_failed"

    if len(passing) < CANARY1_RETRIES:
        log_failure(instance_id, "canary1_flaky",
                    f"{len(passing)}/{CANARY1_RETRIES} runs passed")
        return False, "canary1_flaky"

    print(f"  ✓ Canary 1 passed ({CANARY1_RETRIES}/{CANARY1_RETRIES} runs)", flush=True)

    # Clean up validation image
    subprocess.run(["docker", "rmi", tag], capture_output=True)
    return True, "ok"


def main():
    # validate specific task dirs or all
    if len(sys.argv) > 1:
        task_dirs = [Path(p) for p in sys.argv[1:]]
    else:
        task_dirs = sorted(TASKS_DIR.glob("task_*"))

    results = {"ok": [], "failed": {}}
    for task_dir in task_dirs:
        if not (task_dir / "task.json").exists():
            continue
        ok, category = validate_task(task_dir)
        instance_id = json.loads((task_dir / "task.json").read_text())["instance_id"]
        if ok:
            results["ok"].append(instance_id)
        else:
            results["failed"][instance_id] = category

    print(f"\n=== Validation Summary ===")
    print(f"Passed: {len(results['ok'])}")
    print(f"Failed: {len(results['failed'])}")
    for iid, cat in results["failed"].items():
        print(f"  {iid}: {cat}")

    # write summary to tasks/validation_summary.json
    summary_path = TASKS_DIR / "validation_summary.json"
    with open(summary_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSummary written to {summary_path}")


if __name__ == "__main__":
    main()
