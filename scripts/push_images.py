#!/usr/bin/env python3
"""Build and push validated task images to GCR with parallelism."""

import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

TASKS_DIR = Path(__file__).parent.parent / "tasks"
WORKLOG = Path(__file__).parent.parent / "worklog.md"
MAX_WORKERS = 6


def append_worklog(line: str):
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(WORKLOG, "a") as f:
        f.write(f"- [{ts}] {line}\n")


def build_and_push(task_dir: Path) -> tuple[str, bool, str]:
    task_json = json.loads((task_dir / "task.json").read_text())
    instance_id = task_json["instance_id"]
    image_name = task_json["image_name"]

    print(f"[{instance_id}] Building {image_name} ...", flush=True)
    t0 = time.time()

    build = subprocess.run(
        ["docker", "build", "-t", image_name, "."],
        cwd=task_dir,
        capture_output=True,
        text=True,
        timeout=600,
    )
    if build.returncode != 0:
        return instance_id, False, f"build failed: {build.stderr[-500:]}"

    push = subprocess.run(
        ["docker", "push", image_name],
        capture_output=True,
        text=True,
        timeout=300,
    )
    elapsed = time.time() - t0
    if push.returncode != 0:
        return instance_id, False, f"push failed: {push.stderr[-500:]}"

    print(f"[{instance_id}] ✓ pushed in {elapsed:.0f}s", flush=True)
    return instance_id, True, f"{elapsed:.0f}s"


def main():
    # load validated task list
    summary_path = TASKS_DIR / "validation_summary.json"
    if not summary_path.exists():
        print("Run validate_task.py first to generate validation_summary.json")
        sys.exit(1)

    summary = json.loads(summary_path.read_text())
    validated_ids = set(summary.get("ok", []))

    if len(sys.argv) > 1:
        task_dirs = [Path(p) for p in sys.argv[1:]]
    else:
        task_dirs = [
            d for d in sorted(TASKS_DIR.glob("task_*"))
            if (d / "task.json").exists()
            and json.loads((d / "task.json").read_text())["instance_id"] in validated_ids
        ]

    print(f"Pushing {len(task_dirs)} validated task images with {MAX_WORKERS} workers")

    failures = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(build_and_push, d): d for d in task_dirs}
        for fut in as_completed(futures):
            instance_id, ok, detail = fut.result()
            if ok:
                task_json = json.loads((futures[fut] / "task.json").read_text())
                append_worklog(f"PUSHED {instance_id} → {task_json['image_name']} ({detail})")
            else:
                failures.append((instance_id, detail))
                print(f"[{instance_id}] FAILED: {detail}", flush=True)

    print(f"\n=== Push Summary ===")
    print(f"Succeeded: {len(task_dirs) - len(failures)}")
    print(f"Failed:    {len(failures)}")
    for iid, detail in failures:
        print(f"  {iid}: {detail}")


if __name__ == "__main__":
    main()
