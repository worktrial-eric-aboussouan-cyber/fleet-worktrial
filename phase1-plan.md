# Phase 1: SWE Task Generation Plan

## 1. What we're actually trying to do

We're converting real GitHub pull requests into **self-contained, reproducible training environments**. Each resulting task is essentially an exam question for a coding agent:

- **Problem statement** = the linked issue description (what the user/reporter wanted fixed)
- **Gold answer** = the PR's actual merged diff (what a human maintainer ended up shipping)
- **Grading rubric** = the repo's existing test suite, narrowed to the tests the PR touched (the regression test that was added or modified as part of the fix)
- **Environment** = a Docker image that pins Python version, system deps, and the repo *at the parent commit of the fix* — so the tests are failing on day zero and will only pass if the agent produces a correct patch

An agent "solves" the task if its proposed patch flips the failing tests to passing without breaking any of the previously-passing ones. This is the SWE-Universe blueprint: every merged PR is turned into a gym.

Downstream, these task images get fed to SkyRL+Harbor as rollout environments. The reward signal is binary (exit 0 = +1, exit 1 = 0) or fractional (Fix Rate = fraction of target tests passing, à la SWE-EVO), and that signal drives GRPO updates on the policy model.

For Phase 1, the only thing that matters is that each task is **hermetic and verifiable**. Every minute spent generating tasks that don't build cleanly, or whose tests pass trivially without the patch, is wasted.

## 2. Why these specific candidate repos

I was optimizing for a set of properties that most aggressively de-risk the "reward stuck at zero" failure mode. The candidates I proposed — `psf/requests`, `pallets/click`, `pallets/flask`, `encode/httpx` — all share the following traits.

**Pure Python, no compiled extensions.** `pip install -e .` finishes in under 30 seconds because there's nothing to compile. No `gcc`, no `libxml2`, no system-level package hunts. Compare to `numpy`, `scipy`, `pandas`, `lxml`, `psycopg2`, `cryptography` (sometimes), `scikit-learn` — all of which require heavyweight native builds inside the container. At scale, a 4-minute Docker build versus a 30-second one is the difference between pushing 40 tasks before lunch and pushing 8.

**Fast test suite.** `requests`'s full test suite runs in ~20 seconds on a laptop, `click` in under 10, `flask` in under 30, `httpx` in ~30. During RL training the agent does thousands of rollouts, and each rollout runs the eval script. A test suite that takes 5 minutes per rollout means you can't afford more than a few hundred rollouts in a day, which will show as a flat reward curve for reasons that have nothing to do with task quality. Avoid `django`, `pandas`, `matplotlib` for exactly this reason.

**Culture of "every fix ships with a regression test."** This is the quietly load-bearing property. For the verifier to actually verify, the PR must include a test that *specifically exercises the bug*. These four repos have maintainers who reject PRs without tests. You'll find a consistent pattern of `test_foo.py::test_bug_1234` added alongside the fix. When you scrape PRs, filtering for "modifies at least one file in `tests/`" cheaply gets you high-signal candidates.

**Mature and PR-rich.** 8+ years of history, thousands of merged PRs, wide distribution of bug complexities. You can cherry-pick 10–15 good tasks per repo without scraping the bottom of the barrel.

**Small-to-medium codebase.** 5k–20k lines of source. Big enough for real bugs to live in real modules; small enough that an agent can plausibly explore the repo within its context window. Repos like `kubernetes` or `llvm` have too much ambient complexity; repos like a 300-line hobby project don't have enough real-world signal.

**Different skills per repo.** `requests` and `httpx` are HTTP client libraries, `flask` is a web framework, `click` is a CLI framework. Training across this spread encourages the policy to learn transferable bug-fixing behavior rather than overfitting to one library's idioms. Crucially, it also sets up the Phase 3 OOD eval — these repos are different enough from SWE-bench Verified targets like `astropy`, `sympy`, `matplotlib`, `pylint`, `pytest` that a positive transfer delta would be meaningful.

**Anti-patterns I deliberately avoided:** numpy/scipy/pandas (compiled, slow), Django (slow tests, DB setup), TensorFlow/PyTorch (GPU setup, multi-GB images), compiled scientific stacks, anything that requires a running database or external service at test time.

One caveat: `requests` and `flask` both appear in SWE-bench Verified. That's fine for *training* — we just can't use them in our Phase 3 OOD held-out set. We'll OOD-eval on non-overlapping SWE-bench repos like `astropy`, `sympy`, `pylint`, `pytest`, or `matplotlib`.

## 3. Step-by-step plan

### Step 0 — Directory scaffold (5 min)

```
~/fleet-worktrial/
├── tasks/                      # Generated task instances land here
├── scripts/
│   ├── scrape_prs.py           # GitHub API scraper
│   ├── build_task.py           # PR → task_XXX/ materializer
│   ├── validate_task.py        # Canary validation
│   └── push_images.py          # Docker build + push loop
├── templates/
│   ├── Dockerfile.requests     # One template per repo
│   ├── Dockerfile.click
│   ├── Dockerfile.flask
│   └── Dockerfile.httpx
├── worklog.md                  # Append-only progress log
└── .env                        # GITHUB_TOKEN, DOCKER_REGISTRY, etc.
```

### Step 1 — PR scraper (45 min)

Write `scripts/scrape_prs.py` that, for each target repo, hits the GitHub API (PyGithub or `gh api`) and returns PRs matching **all** of:

1. State is `closed` and `merged == True`
2. PR body or commit message contains `Fixes #NNNN` / `Closes #NNNN` / `Resolves #NNNN` (links to an issue)
3. At least one changed file lives under `tests/` (or repo equivalent)
4. Patch size between 5 and 500 lines changed (small enough to be tractable, big enough to be non-trivial)
5. Merged within the last 2 years (older PRs often can't be rebuilt because deps have drifted)
6. Not a dependabot / renovate / doc-only PR (check author and labels)

For each passing PR, record: repo, PR number, merge SHA, parent SHA (= `base_commit`), linked issue number, PR body, issue body, list of test files touched, list of source files touched, patch size.

Aim for ~20 candidates per repo before filtering. You'll lose about half to validation.

### Step 2 — Dockerfile templates (30 min)

One template per repo, parametrized on `BASE_COMMIT`. Minimal shape:

```dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
WORKDIR /repo
RUN git clone https://github.com/psf/requests.git . \
 && git checkout ${BASE_COMMIT}
RUN pip install --no-cache-dir -e ".[socks]" \
 && pip install --no-cache-dir pytest pytest-httpbin pytest-mock
CMD ["/bin/bash"]
```

Each repo needs its own idiomatic extras (`flask[test]`, `click[dev]`, etc.). Look at each repo's `tox.ini` / `pyproject.toml` to find the right extras group. **Pre-installing all test deps in the image is critical** — do not let the agent `pip install` at rollout time, it'll tank throughput and introduce non-determinism.

Pin a specific Python minor (3.11 is safe for all four of these as of 2024+ PRs). If a specific PR's deps break under 3.11, fall back to 3.10 for that task.

### Step 3 — Task materializer (45 min)

`scripts/build_task.py` takes a scraped PR record and writes out `tasks/task_XXX/`:

**`task.json`**:
```json
{
  "instance_id": "requests-6234",
  "repo": "psf/requests",
  "base_commit": "abc123...",
  "problem_statement": "<concatenation of issue title + body + PR description>",
  "gold_patch": "<raw unified diff from git diff base..head>",
  "image_name": "gcr.io/fleet-compute-489000/swe-task-requests-6234:latest",
  "eval_script": "#!/bin/bash\ncd /repo && pytest tests/test_foo.py tests/test_bar.py -x\nexit $?",
  "test_paths": ["tests/test_foo.py", "tests/test_bar.py"],
  "source_paths": ["src/requests/foo.py"]
}
```

**`Dockerfile`**: rendered from the template with `BASE_COMMIT` substituted.

**`eval_script.sh`**: targets *only the tests the PR modified*, not the whole suite — this makes rollouts fast and makes the signal sharp.

```bash
#!/bin/bash
set -e
cd /repo
pytest <test_paths joined with spaces> -x --tb=short
exit $?
```

### Step 4 — Validation gate (the critical step, 30 min to write + hours to run)

`scripts/validate_task.py` does this for each task, and any task that fails either check gets discarded:

**Canary 1 — "gold patch should pass":**
1. Build the Dockerfile
2. Run the container with `gold_patch` applied (`git apply` inside the container)
3. Run `eval_script.sh`
4. Expect exit 0

**Canary 2 — "empty patch should fail":**
1. Build the Dockerfile
2. Run the container with **no patch**
3. Run `eval_script.sh`
4. Expect exit 1

Canary 1 catches: broken Dockerfile, missing deps, wrong test path, patch that doesn't apply cleanly. Canary 2 catches: tests that pass even without the fix (i.e., the "verifier" isn't actually verifying anything — the worst failure mode because it produces "easy" tasks that reward gaming).

Log the failure reason so you can categorize: "build failed," "gold didn't pass," "empty didn't fail," etc. Patterns in the failures will tell you whether your template needs adjustment.

**Target: 30–50 validated tasks total across all four repos after this gate.**

### Step 5 — Build + push images (1–2 hrs, mostly waiting)

`scripts/push_images.py` loops over validated tasks:

```bash
docker build -t gcr.io/fleet-compute-489000/swe-task-<id>:latest tasks/task_XXX/
docker push gcr.io/fleet-compute-489000/swe-task-<id>:latest
```

Use Google Container Registry (or Artifact Registry) rather than Docker Hub — you're already authed into GCP, pushes are fast, pulls from your training VMs are free and nearby. Authenticate once with `gcloud auth configure-docker gcr.io`.

Parallelize 4–8 builds concurrently (GNU parallel or a Python `ThreadPoolExecutor`). Expect each image to be 300–500 MB.

### Step 6 — Long-horizon (SWE-EVO-style) bundles (1 hr)

For 3–5 composite tasks, pick a minor-version release of one repo (e.g., all PRs merged between `requests 2.31.0` and `2.32.0`) and bundle them:

- `problem_statement` = release-notes entry concatenated with each sub-PR's issue body
- `base_commit` = the commit right before the first PR in the release window
- `gold_patch` = the *union diff* from that base commit to the release tag (this may span 10–30 files)
- `eval_script` = union of all test paths touched by any sub-PR
- `image_name` = `gcr.io/.../swe-task-requests-release-2.32.0:latest`

Validate with the same two-canary gate. These are genuinely hard — expect 50%+ to fail validation. Keeping even 2–3 is a win because they're the SWE-EVO-flavored signal the hiring manager called out.

### Step 7 — Final inventory (15 min)

Produce `tasks/INDEX.md` listing every task with instance_id, repo, patch size, test count, and image URL. Commit everything to a git repo. Append a summary line to `worklog.md`:

> Phase 1 complete: N single-PR tasks + M release-bundle tasks, images pushed to gcr.io/fleet-compute-489000/.

## 4. Timeboxing and decision points

- **Hour 1:** scaffold + scraper + one working Dockerfile template + materializer for `requests`. Goal: 5 validated `requests` tasks by end of hour 1. If you can't produce 5 clean tasks in an hour for the easiest repo, something's wrong with the template — stop and debug before adding more repos.
- **Hour 2:** extend to `click`, `flask`, `httpx`. Target: 25–30 validated single-PR tasks total.
- **Hour 3:** build + push all images to GCR in parallel.
- **Hour 4:** 3–5 release-bundle long-horizon tasks, validate, push.

**Hard stop at 4 hours.** Move to Phase 2. More tasks beyond this gives diminishing returns versus getting an actual reward curve running.

## 5. Things that will go wrong (pre-mortem)

**Tests that pass even without the patch.** Canary 2 will catch these, but expect 15–30% of scraped PRs to fail this check. Causes: the test was added as a non-regression test that always passed, the fix was in a file other than the one the test is in, the linked issue wasn't actually fixed by this PR. Discard and move on; don't try to salvage.

**Deps that no longer resolve.** Older PRs (even just 2 years back) reference versions of transitive deps that have since been yanked. Workaround: pin `pip install` to the versions that were current at merge time using `git log -1 --format=%cd <base_commit>`, or just discard those PRs.

**Flaky tests.** Some PRs touch tests that are flaky (network, timing, randomness). Run canary 1 three times; if it's not consistent, drop the task.

**Patch doesn't apply cleanly on base_commit.** Rare but happens if the PR was rebased or force-pushed after merge. Use the merge commit's parent rather than trusting the PR's `base.sha`.

**Docker Hub rate limits** (if you use it instead of GCR). Use GCR — you're already paying for GCP.

## 6. What to hand Claude Code

You can literally paste this entire file into Claude Code as a follow-up message after Phase 0 setup and say:

> Execute Phase 1 from phase1-plan.md. Start with Step 0, do each step in order, validate each step before moving on. Stop and ask me if (a) you need a GitHub token, (b) you need to decide on GCR project path, (c) any validation canary is failing in a way you can't self-correct. Update worklog.md after each step.

Then check in every 30–45 minutes.
