# Status — Fleet Work Trial

## 🏆 Current State: Training Loop Live & Telemetry Flowing
We have successfully moved from raw PR scraping to a live end-to-end GRPO training run on an 8x A100 GPU cluster.

### Live Run Details
- **Winning Track**: Track B (Easy Task Injection) + Track A (Fractional Reward Patch)
- **Active WandB Run**: [ajachaix](https://wandb.ai/thefleet/fleet-worktrial-eric/runs/ajachaix)
- **Hardware**: 8x A100 (GCP `fleet-swe-final`)
- **Model**: Qwen3-8B

---

## ✅ Accomplishments (Sprint 2 & 3)
### 1. Training Pipeline Automation
- **`prepare_harbor_dataset.py`**: Fully automated extraction of validated tasks into Harbor's parquet format.
- **`repackage_train.py`**: Handles local structure preparation for SkyPilot file mounts.
- **`harbor-grpo-qwen3-8b.yaml`**: Hardened SkyPilot config with explicit environment injection and optimized VRAM utilization.

### 2. Reward Engineering (Track A)
- **Fractional Rewards**: Patched `mini_swe_utils.py` to calculate rewards as `passed_tests / total_tests` instead of binary success/failure.
- **Eval Script Hardening**: Modified `eval_script.sh` templates to remove `set -e` and pipe Pytest output to `tee`, ensuring the reward parser always sees the test summary line.

### 3. Dataset Injection (Track B)
- **Insurance Tasks**: Injected "easy" tasks (`requests-7309`, `requests-7305`) which had empty canary passes, ensuring the model sees positive reward signal early to bootstrap learning.

### 4. Critical Debugging (The "1 Token" Bug)
- **Root Cause**: Identified that `generator.max_input_length` defaulted to 512 tokens, causing severe truncation of SWE-bench prompts and resulting in `max_num_tokens: 1` errors.
- **Fix**: Aligned `trainer.max_prompt_length` and `generator.max_input_length` to 16,384 tokens and increased generation budget to 8,192 tokens.

---

## 🛠️ Infrastructure Status
- **Cluster `fleet-swe-final`**: **UP** & Training.
- **Cluster `fleet-swe-track-a`**: **UP** & Standby (Backup for 4B model).
- **Daytona Sandboxes**: Actively executing agent rollouts.

---

## ⏭️ Next Steps
1. **Monitor `ajachaix`**: Verify `avg_num_tokens > 1` and `reward > 0` on the first training step.
2. **OOD Evaluation**: Prepare the materialized OOD tasks for a checkpoint evaluation.
3. **Cleanup**: Execute `sky down` across all clusters once the demo window closes.

---

## 📄 References
- **Root Cause Analysis**: [notes/root-cause.md](file:///Users/fleet/fleet-worktrial/notes/root-cause.md)
- **Training Config**: [harbor-grpo-qwen3-8b.yaml](file:///Users/fleet/fleet-worktrial/harbor-train/skyrl-train/tasks/harbor-grpo-qwen3-8b.yaml)