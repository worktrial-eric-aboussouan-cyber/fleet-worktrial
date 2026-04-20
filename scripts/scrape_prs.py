#!/usr/bin/env python3
"""Scrape merged PRs from GitHub repos that are suitable SWE task candidates."""

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from github import Auth, Github, GithubException

REPOS = [
    "psf/requests",
    "pallets/click",
    "pallets/flask",
    "encode/httpx",
]

# Hard require: "Fixes/Closes/Resolves #NNN" in PR body or commit messages
STRICT_ISSUE_RE = re.compile(
    r"(?:fix(?:es|ed)?|clos(?:es|ed)?|resolv(?:es|ed)?)\s+#(\d+)",
    re.IGNORECASE,
)

# Soft drop: title starts with these prefixes
TITLE_PREFIX_RE = re.compile(
    r"^(merge|release|bump|chore|ci|docs?|typo|cleanup|refactor|style|test\s*:)",
    re.IGNORECASE,
)

# Soft drop: title contains these substrings
TITLE_SUBSTR_RE = re.compile(
    r"\b(cosmetic|build.failure|dependency|deps|pre-commit)\b",
    re.IGNORECASE,
)

CUTOFF = datetime(2022, 6, 1, tzinfo=timezone.utc)
MIN_LINES = 5
MAX_LINES = 500
MAX_FILES = 8         # drop PRs touching > 8 files
MAX_CANDIDATES = 40   # per repo
MAX_SCAN = 800        # max PRs to walk per repo


def find_linked_issue(pr) -> str | None:
    """Return issue number if PR body or any commit message has Fixes/Closes/Resolves #N."""
    text = (pr.title or "") + " " + (pr.body or "")
    m = STRICT_ISSUE_RE.search(text)
    if m:
        return m.group(1)
    try:
        for commit in pr.get_commits():
            m = STRICT_ISSUE_RE.search(commit.commit.message or "")
            if m:
                return m.group(1)
    except GithubException:
        pass
    return None


def is_bot_pr(pr) -> bool:
    login = (pr.user.login or "").lower()
    labels = [la.name.lower() for la in pr.labels]
    return (
        "bot" in login
        or "dependabot" in login
        or "renovate" in login
        or "dependencies" in labels
        or "automated" in labels
    )


def is_noisy_title(title: str) -> bool:
    return bool(TITLE_PREFIX_RE.match(title)) or bool(TITLE_SUBSTR_RE.search(title))


def is_doc_only(files) -> bool:
    non_doc = [
        f for f in files
        if not any(
            f.filename.startswith(p)
            for p in ("docs/", "doc/", "CHANGES", "CHANGELOG", "README", ".github/")
        )
        and not f.filename.endswith((".md", ".rst", ".txt"))
    ]
    return len(non_doc) == 0


def scrape_repo(g: Github, repo_name: str) -> list[dict]:
    print(f"\n=== Scraping {repo_name} ===", flush=True)
    repo = g.get_repo(repo_name)
    candidates = []

    pulls = repo.get_pulls(state="closed", sort="created", direction="desc")
    checked = 0
    for pr in pulls:
        if checked >= MAX_SCAN:
            break
        checked += 1

        if not pr.merged:
            continue
        if pr.created_at < CUTOFF:
            break

        if is_bot_pr(pr):
            continue

        if is_noisy_title(pr.title or ""):
            continue

        additions = pr.additions
        deletions = pr.deletions
        total_lines = additions + deletions
        if not (MIN_LINES <= total_lines <= MAX_LINES):
            continue

        try:
            files = list(pr.get_files())
        except GithubException:
            continue

        if len(files) > MAX_FILES:
            continue

        if is_doc_only(files):
            continue

        test_files = [
            f.filename for f in files
            if f.filename.endswith(".py")
            and re.search(r"(^|/)tests?/|test_.*\.py$|.*_test\.py$", f.filename)
        ]
        if not test_files:
            continue

        source_files = [
            f.filename for f in files
            if f.filename.endswith(".py") and f.filename not in test_files
        ]

        if not source_files:
            continue

        # Commits API call only for PRs that pass all other filters
        issue_num = find_linked_issue(pr)
        if not issue_num:
            continue

        issue_body = ""
        issue_title = ""
        try:
            issue = repo.get_issue(int(issue_num))
            issue_body = issue.body or ""
            issue_title = issue.title or ""
        except GithubException:
            pass

        base_commit = pr.base.sha

        candidates.append({
            "repo": repo_name,
            "pr_number": pr.number,
            "pr_title": pr.title,
            "pr_body": (pr.body or "")[:2000],
            "issue_number": issue_num,
            "issue_title": issue_title,
            "issue_body": issue_body[:2000],
            "merge_sha": pr.merge_commit_sha,
            "base_commit": base_commit,
            "merged_at": pr.merged_at.isoformat(),
            "additions": additions,
            "deletions": deletions,
            "total_lines": total_lines,
            "test_files": test_files,
            "source_files": source_files,
            "all_files": [f.filename for f in files],
        })

        print(
            f"  PR #{pr.number}: +{additions}/-{deletions} lines | "
            f"issue #{issue_num} | src: {source_files} | tests: {test_files}",
            flush=True,
        )

        if len(candidates) >= MAX_CANDIDATES:
            break

        time.sleep(0.05)

    print(f"  → {len(candidates)} candidates from {repo_name} (scanned {checked} PRs)", flush=True)
    return candidates


def main():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("ERROR: GITHUB_TOKEN not set", file=sys.stderr)
        sys.exit(1)

    repos_arg = sys.argv[1:] if len(sys.argv) > 1 else REPOS
    g = Github(auth=Auth.Token(token))

    out_dir = Path(__file__).parent.parent / "tasks"
    out_dir.mkdir(exist_ok=True)

    all_candidates = []
    for repo_name in repos_arg:
        candidates = scrape_repo(g, repo_name)
        all_candidates.extend(candidates)
        out_file = out_dir / f"candidates_{repo_name.replace('/', '_')}.json"
        with open(out_file, "w") as f:
            json.dump(candidates, f, indent=2)
        print(f"  Saved → {out_file}")

    print(f"\nTotal candidates: {len(all_candidates)}")


if __name__ == "__main__":
    main()
