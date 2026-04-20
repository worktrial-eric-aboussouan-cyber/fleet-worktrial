#!/usr/bin/env python3
"""Materialize a scraped PR candidate into tasks/task_XXX/{task.json,Dockerfile,eval_script.sh}."""

import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

REGISTRY = os.environ.get("DOCKER_REGISTRY", "gcr.io/fleet-compute-489000")
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
TASKS_DIR = Path(__file__).parent.parent / "tasks"

REPO_TEMPLATE = {
    "psf/requests": "Dockerfile.requests",
    "pallets/click": "Dockerfile.click",
    "pallets/flask": "Dockerfile.flask",
    "encode/httpx": "Dockerfile.httpx",
}


def get_gold_patch(repo: str, base_commit: str, merge_sha: str) -> str:
    """Clone repo into a temp dir and compute the gold diff."""
    clone_url = f"https://github.com/{repo}.git"
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(
            ["git", "clone", "--quiet", "--no-tags", clone_url, tmp],
            check=True, capture_output=True,
        )
        result = subprocess.run(
            ["git", "diff", f"{base_commit}..{merge_sha}"],
            cwd=tmp, capture_output=True, text=True, check=True,
        )
        return result.stdout


def extract_new_test_names(gold_patch: str) -> list[str]:
    """Extract test function names added by the patch (lines starting with +)."""
    names = []
    for line in gold_patch.splitlines():
        if line.startswith("+") and "def test_" in line:
            m = re.search(r"def (test_\w+)", line)
            if m:
                names.append(m.group(1))
    return names


def build_problem_statement(candidate: dict) -> str:
    parts = []
    if candidate.get("issue_title"):
        parts.append(f"Issue: {candidate['issue_title']}")
    if candidate.get("issue_body"):
        parts.append(candidate["issue_body"].strip())
    if candidate.get("pr_title"):
        parts.append(f"PR: {candidate['pr_title']}")
    if candidate.get("pr_body"):
        parts.append(candidate["pr_body"].strip())
    return "\n\n".join(parts)


def repo_short(repo: str) -> str:
    return repo.split("/")[1]


def make_instance_id(repo: str, pr_number: int) -> str:
    return f"{repo_short(repo)}-{pr_number}"


def materialize(candidate: dict, task_index: int) -> Path:
    repo = candidate["repo"]
    pr_number = candidate["pr_number"]
    instance_id = make_instance_id(repo, pr_number)
    base_commit = candidate["base_commit"]
    merge_sha = candidate["merge_sha"]

    task_dir = TASKS_DIR / f"task_{task_index:03d}"
    task_dir.mkdir(parents=True, exist_ok=True)

    # Gold patch
    print(f"  Computing gold patch for {instance_id}...", flush=True)
    try:
        gold_patch = get_gold_patch(repo, base_commit, merge_sha)
    except subprocess.CalledProcessError as e:
        print(f"  ERROR getting patch: {e.stderr}", flush=True)
        gold_patch = ""

    # Dockerfile
    template_name = REPO_TEMPLATE[repo]
    template_path = TEMPLATES_DIR / template_name
    dockerfile_content = template_path.read_text().replace("${BASE_COMMIT}", base_commit)
    (task_dir / "Dockerfile").write_text(dockerfile_content)

    # eval_script.sh — run only new tests added by the PR if we can find them
    test_paths = " ".join(candidate["test_files"])
    test_names = extract_new_test_names(gold_patch)
    if test_names:
        test_filter = " or ".join(test_names)
        eval_script = f"""#!/bin/bash
set -e
cd /repo
pytest {test_paths} -x --tb=short -k "{test_filter}"
exit $?
"""
    else:
        eval_script = f"""#!/bin/bash
set -e
cd /repo
pytest {test_paths} -x --tb=short
exit $?
"""

    eval_path = task_dir / "eval_script.sh"
    eval_path.write_text(eval_script)
    eval_path.chmod(eval_path.stat().st_mode | stat.S_IEXEC)

    image_name = f"{REGISTRY}/swe-task-{instance_id}:latest"

    task_json = {
        "instance_id": instance_id,
        "repo": repo,
        "base_commit": base_commit,
        "merge_sha": merge_sha,
        "pr_number": pr_number,
        "problem_statement": build_problem_statement(candidate),
        "gold_patch": gold_patch,
        "image_name": image_name,
        "eval_script": eval_script,
        "test_paths": candidate["test_files"],
        "source_paths": candidate["source_files"],
        "total_lines": candidate["total_lines"],
        "merged_at": candidate["merged_at"],
    }
    (task_dir / "task.json").write_text(json.dumps(task_json, indent=2))

    print(f"  Materialized {instance_id} → {task_dir}", flush=True)
    return task_dir


def main():
    if len(sys.argv) < 2:
        print("Usage: build_task.py candidates_file.json [start_index]")
        sys.exit(1)

    candidates_file = Path(sys.argv[1])
    start_index = int(sys.argv[2]) if len(sys.argv) > 2 else 0

    candidates = json.loads(candidates_file.read_text())
    print(f"Materializing {len(candidates)} candidates from {candidates_file}")

    for i, candidate in enumerate(candidates):
        materialize(candidate, start_index + i)


if __name__ == "__main__":
    main()
