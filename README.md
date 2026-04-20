# Fleet SWE Worktrial — Eric Aboussouan

End-to-end pipeline: GitHub PRs → verifiable Docker tasks → GRPO training on Qwen3 → OOD evaluation on SWE-bench Verified.

## Results at a glance

| Metric | Value |
|---|---|
| In-distribution validated tasks | 12 / 24 |
| OOD eval instances | 0 / 30 |
| Training reward (start → end) | 0.0 → <TBD> |
| OOD pass@1 (base model) | <TBD> |
| OOD pass@1 (trained model) | <TBD> |
| Wandb run | Pending |

## Phase 1 — Task generation

**Source repos** (in-distribution): `psf/requests`, `pallets/click`, `pallets/flask`, `encode/httpx`.

**Pipeline**:
1. `scripts/scrape_prs.py` — scrape closed+merged PRs with a linked issue (`Fixes #N`), 5–500 LoC, ≤8 files, excluding meta/cosmetic titles.
2. `scripts/build_task.py` — materialize `tasks/task_XXX/` with `Dockerfile`, `eval_script.sh`, `task.json`. `eval_script.sh` runs only the tests the PR added (`extract_new_test_names` via `git grep` against `base_commit`).
3. `scripts/validate_task.py` — two-canary gate:
   - Canary 1: `git apply gold_patch && eval_script` → exit 0
   - Canary 2: empty patch → exit non-0
4. `scripts/push_images.sh` — builds and pushes validated tasks to `ghcr.io/worktrial-eric-aboussouan-cyber/swe-<id>:latest` (public).

**Stats**: 77 candidates scraped → 24 materialized (requests only, time-boxed) → 12 validated → 12 pushed.

## Phase 2 — GRPO training

- **Model**: Qwen3-8B
- **Algorithm**: GRPO (group size <TBD>, KL coeff <TBD>)
- **Framework**: `fleet-ai/harbor-train` (upstream SkyRL + Daytona sandboxes)
- **Hardware**: 4× L4 on GCP via SkyPilot
- **Reward**: exit code of `eval_script.sh` inside our GHCR image (1 if 0, else 0)
- **Dataset**: `data/train.parquet` (12 tasks, Harbor format)

Launch:
```bash
sky launch harbor-train/configs/harbor-grpo-qwen3-8b.yaml -c fleet-swe
```

Training curve: `results/training_curve.png` (export from wandb).

## Phase 3 — OOD evaluation

- **Dataset**: SWE-bench Verified, filtered to repos disjoint from training set
- **Repos**: django, sympy, sphinx, matplotlib, scikit-learn, astropy, xarray, pytest, pylint, seaborn
- **Instances**: 30 (1 django, rest balanced)
- **Images**: `ghcr.io/worktrial-eric-aboussouan-cyber/swebench-<id>:latest`
- **Metric**: pass@1 via `eval_script.sh` exit code

Results: `results/eval_results.json`.

## Reproduction

```bash
# 1. Scrape
export GITHUB_TOKEN=...
uv run scripts/scrape_prs.py --repo psf/requests --limit 25

# 2. Materialize + validate
uv run scripts/build_task.py
uv run scripts/validate_task.py --all --parallel 4

# 3. Push
bash scripts/push_images.sh

# 4. Train
uv run scripts/prepare_harbor_dataset.py
sky launch harbor-train/configs/harbor-grpo-qwen3-8b.yaml

# 5. Eval
uv run scripts/prepare_ood_eval.py --build --push
# eval config TBD based on harbor eval path
```

## Files

```
fleet-worktrial/
├── README.md                          # this file
├── notes.md                           # design decisions, tradeoffs, known issues
├── scripts/
│   ├── scrape_prs.py
│   ├── build_task.py
│   ├── validate_task.py
│   ├── push_images.sh
│   ├── prepare_harbor_dataset.py
│   └── prepare_ood_eval.py
├── templates/Dockerfile.{requests,click,flask,httpx}
├── tasks/task_XXX/                    # 12 validated tasks
├── data/
│   ├── train.parquet
│   └── ood_eval.parquet
├── results/
│   ├── training_curve.png
│   └── eval_results.json
├── notes/                             # recon docs, debug logs
└── harbor-train/                      # upstream clone
```
