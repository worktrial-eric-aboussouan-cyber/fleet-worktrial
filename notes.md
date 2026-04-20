# Design notes

## Key decisions

**Repo selection.** Picked `requests`, `click`, `flask`, `httpx` for (a) mature pytest-based test suites, (b) merged PRs that fix narrow issues with clear regression tests, (c) fast Docker builds (<2 min each). Deliberately excluded `django`/`sympy` from the training set — build times and test-suite size would have dominated the wall-clock budget.

**Idiomatic Docker per repo.** Each repo has its own dependency mechanism (requirements-dev.txt, pyproject dependency-groups, extras). Rather than a one-size template, produced four Dockerfile templates that use each repo's native mechanism. Each is parametrized on `BASE_COMMIT` via `ARG`.

**Two-canary validation.** Every task must show that (1) the gold patch + targeted tests → exit 0, AND (2) empty patch + same tests → exit non-0. Catches two common failure modes: tests that always pass (no signal) and tests that always fail (broken env). Dropped tasks that failed either canary rather than trying to fix them — preserves reward-signal integrity at the cost of yield.

**Narrowing eval targets.** `eval_script.sh` runs only the tests the PR *added* (detected via `git grep` against `base_commit`). Without this, canary 2 trivially passes because pre-existing tests work without the patch.

**GHCR over GCR.** GCR needed write permissions on Fleet's GCP project, which I didn't have. Pivoted to GHCR (tied to GitHub login, instant, free, public pulls work with Daytona without auth).

**Harbor on L4 instead of B200.** L4s are ~5× cheaper per hour and available without quota asks. Risk: 96 GB total VRAM is tight for Qwen3-8B + vLLM. Fallback plan was to swap to Qwen3-4B if OOM.

## What worked

- The scraper filter (title blocklist + linked-issue requirement + patch-size band) cut noise from 77 candidates to a clean working set quickly.
- Smoke-testing one Dockerfile per repo before materializing all tasks caught dependency issues early (pytest not in path, extras missing) and saved rework.
- Writing an explicit `validate_task.py` with retry + categorized failure logs (`canary2_empty_passed`, `gold_patch_tests_failed`, `canary1_flaky`) made it obvious *why* each task failed, not just *that* it did.

## What didn't work / had to fix

- **`--network none` in the validator killed every requests/httpx test** — they hit httpbin. Removed network isolation; accepted the small risk of network-flaky canary 2.
- **Tempfile lifecycle bug on macOS.** `tempfile.NamedTemporaryFile` created files outside Docker's mount-allowed paths on Docker Desktop. Moved patch files to a repo-local `.tmp_patches/` dir.
- **canary2_empty_passed at 8/24.** Some "new" tests were actually modifications of existing tests; `pytest -k` matched the existing version. Tightened extraction with `git grep` at `base_commit` but some false positives remain. Dropped these rather than hand-fixing.
- **HuggingFace 401 on first training launch.** Dataset path was right but `HF_TOKEN` wasn't threaded into the SkyPilot env. Fixed in relaunch.

## Tradeoffs taken

| Tradeoff | Choice | Why |
|---|---|---|
| Task count vs. validation strictness | Strictness | Noisy rewards destabilize GRPO more than small dataset hurts it |
| Build from scratch vs. reuse SWE-bench images | Build from scratch | No prebuilt images existed for the selected instance IDs |
| Sync training vs. async | Sync (default Harbor) | 1-day budget; async debugging would eat the runway |
| Phase 2 smoke test vs. full launch | Full launch | Time-boxed; could have caught issues earlier with smoke test first |

## If I had another day

1. **Expand training set.** The other 3 repos (click, flask, httpx) are scraped and Docker-ready — just need a second validator pass. Conservative estimate: +30 validated tasks.
2. **Fix `extract_new_test_names` properly.** Parse `git diff` AST instead of grep-matching, to distinguish added tests from modified ones. Would recover ~6 of the 8 `canary2_empty_passed` drops.
3. **Long-horizon task set.** Identify 3–5 multi-file refactor PRs (SWE-EVO style) and bundle them as a secondary eval — tests whether GRPO-on-narrow-bugs transfers to broader changes.
4. **Reward shaping.** Current reward is {0, 1}. A partial-credit signal (fraction of target tests passing) would give denser gradients, especially early in training when most rollouts fail completely.
5. **Per-task budget in Daytona.** Today every rollout runs the full test suite. Capping at `pytest --timeout=60 --maxfail=1` would halve rollout cost.

## Known issues at time of writing

- Training was launched on L4:4; if Qwen3-8B OOMs, need to swap to Qwen3-4B in the YAML (single line change).
- OOD images not yet pushed at time of `sky launch` — OOD eval is a separate run after training completes.
- Validator still retries 3× on canary 1 and labels consistent failures as "flaky"; the label is misleading, should rename to `canary1_failed`.
