# Fleet SWE Worktrial — Eric Aboussouan

End-to-end pipeline: GitHub PRs → verifiable Docker tasks → GRPO training on Qwen3 → OOD evaluation on SWE-bench Verified.

## 🚀 Live Training Results
We have successfully operationalized the Harbor training pipeline on an 8x A100 cluster.

| Metric | Value |
|---|---|
| In-distribution validated tasks | 14 / 24 (Injected 2 Easy Canary tasks) |
| OOD eval instances | 30 / 30 (Materialized) |
| **Active WandB Run** | [ajachaix](https://wandb.ai/thefleet/fleet-worktrial-eric/runs/ajachaix) |
| **Latest Reward** | 0.0 (Step 0) → Bootstrapping with Easy Tasks |
| **Context Length** | 16,384 tokens (Fixed Truncation Bug) |

---

## 🛠️ Phase 1 — Task Generation

**Source repos** (in-distribution): `psf/requests`, `pallets/click`, `pallets/flask`, `encode/httpx`.

**Pipeline**:
1. `scripts/scrape_prs.py` — Scrape closed+merged PRs with a linked issue (`Fixes #N`).
2. `scripts/build_task.py` — Materialize `tasks/task_XXX/` with `Dockerfile`, `eval_script.sh`, `task.json`.
3. `scripts/validate_task.py` — Two-canary gate:
   - Canary 1: Gold patch → pass
   - Canary 2: Empty patch → fail
4. `scripts/push_images.sh` — Pushes validated tasks to `ghcr.io/worktrial-eric-aboussouan-cyber/swe-<id>:latest`.

**Stats**: 77 candidates scraped → 24 materialized → 14 validated (including 2 injected canary tasks) → 14 pushed.

---

## 🧠 Phase 2 — GRPO Training

- **Model**: Qwen3-8B
- **Algorithm**: GRPO
- **Infrastructure**: SkyPilot on GCP (`fleet-swe-final`)
- **Hardware**: 8x A100 (Primary), 4x L4 (Backup)
- **Reward Shaping**: Patched `mini_swe_utils.py` to provide fractional rewards (`passed / total`).
- **Context Fix**: Fixed a critical bug where `generator.max_input_length` defaulted to 512, causing all rollouts to truncate and fail with 1 token. Aligned to 16,384.

Launch command:
```bash
sky launch harbor-train/skyrl-train/tasks/harbor-grpo-qwen3-8b.yaml -c fleet-swe-final
```

---

## 📂 Project Structure

```
fleet-worktrial/
├── status.md                          # Live sprint status and milestone tracking
├── harbor-train/                      # Patched upstream training repository
├── scripts/
│   ├── scrape_prs.py
│   ├── build_task.py
│   ├── validate_task.py               # Two-canary validation
│   ├── push_images.sh                 # Docker registry automation
│   ├── prepare_harbor_dataset.py      # Parquet generation
│   └── repackage_train.py             # SkyPilot workspace preparation
├── tasks/task_XXX/                    # Validated task instances
├── notes/                             # Root cause analysis & telemetry logs
└── results/                           # Training curves and eval results
```

## 🔍 Key Findings
See [notes/root-cause.md](notes/root-cause.md) for the detailed breakdown of the context length truncation bug that caused the initial zero-reward steps.
