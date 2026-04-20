# Phase 2 Launch Plan: Harbor Training

## 1. Launch Command
Run this command from the repository root to launch the training task on GCP via SkyPilot:

```bash
# Load secrets and launch
set -a && source .env && set +a && \
sky launch harbor-train/skyrl-train/tasks/harbor-grpo-qwen3-8b.yaml \
  --env WANDB_API_KEY=$WANDB_API_KEY \
  --env DAYTONA_API_KEY=$DAYTONA_API_KEY \
  --env HF_TOKEN=${HF_TOKEN:-""}
```

## 2. Environment Variables (.env)
Check your `~/fleet-worktrial/.env` file. Based on current state:
- **WANDB_API_KEY**: [SET]
- **DAYTONA_API_KEY**: [SET]
- **HF_TOKEN**: [MISSING] - Required if `Qwen/Qwen3-8B` is a gated model or for private HF datasets.

## 3. Dataset Preparation
Harbor expects a Parquet file with `path` and `task_binary` columns. I have created a local converter script:
[scripts/prepare_harbor_dataset.py](file:///Users/fleet/fleet-worktrial/scripts/prepare_harbor_dataset.py).

**How it works:**
- It reads `tasks/validation_summary.json` and only includes tasks marked as `"ok"`.
- It bundles each task directory into a `.tar.gz` (including `instruction.md`, `Dockerfile`, and `eval_script.sh`).
- It saves the result to `data/train.parquet`.

**Run it before launch:**
```bash
python3 scripts/prepare_harbor_dataset.py
```

## 4. Required YAML Adjustments
Modify `harbor-train/skyrl-train/tasks/harbor-grpo-qwen3-8b.yaml` with these values:

- **WandB Project**: `trainer.project_name=fleet-worktrial-eric`
- **Model**: `trainer.policy.model.path=Qwen/Qwen3-8B`
- **Dataset Path**: Set `data.train_data` to point to the `data/` directory created by the preparation script.
- **GPUs**: The default `B200:4` is already the smallest high-end spec requested.

## 5. Cost & Smoke Test
**Estimated Cost:** 
- A 4x B200 cluster costs ~$15-25/hr depending on the provider.
- A full 3-epoch run with 24 tasks could take 4-8 hours ($100-$200).

**Smoke Test Config (First Run):**
To stay under $50, run a "tiny" config first:
- **Tasks**: 2
- **Epochs**: 1
- **Command Override**:
  ```bash
  python -m examples.harbor.entrypoints.main_harbor \
    trainer.epochs=1 \
    generator.n_samples_per_prompt=2 \
    ... (other flags)
  ```

---
**Next Step**: Run `python3 scripts/prepare_harbor_dataset.py` then review the YAML before launching.
