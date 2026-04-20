# Phase 0 Worklog

| # | Step | Status | Timestamp (UTC) | Notes |
|---|------|--------|-----------------|-------|
| 1 | PREREQS | DONE | 2026-04-20T12:16Z | git+python3 present; uv 0.11.7 installed; gcloud 565.0.0 working; docker ps clean; all tools confirmed ✅ |
| 2 | GCP AUTH | DONE | 2026-04-20T12:09Z | gcloud auth login + ADC complete for worktrial-eric-aboussouan@fleet.so; project fleet-compute-489000 set |
| 3 | SKYPILOT | DONE | 2026-04-20T12:09Z | `.venv` Python 3.11; skypilot[gcp]==0.12.0 + wandb==0.26.0 installed; `sky check` → **GCP: enabled [compute, storage]** ✅ |
| 4 | WANDB | DONE | 2026-04-20T12:16Z | Credentials loaded from ~/.netrc; wandb login confirmed ✅ |
| 5 | DOCKER HUB | DONE | 2026-04-20T12:15Z | Docker Desktop installed+running; logged in as ericaboussouanfleet ✅ |
| 6 | REPO CLONE | DONE | 2026-04-20T00:00Z | harbor-train cloned to ~/fleet-worktrial/harbor-train; see findings below |
| 7 | PROBE YAML | DONE | 2026-04-20T13:05Z | probe.yaml confirmed working — `hello world` on GCP n1-standard-1, auto-torn down ✅ |
| P1.0 | PHASE 1 SCAFFOLD | DONE | 2026-04-20T13:10Z | scripts/, templates/, tasks/ created; all 4 Dockerfiles + 4 scripts written; PyGithub installed |

## Step 6 Findings

**Canonical launch command (Harbor GRPO on Qwen3-8B):**
```bash
sky launch skyrl-train/tasks/harbor-grpo-qwen3-8b.yaml \
  --env WANDB_API_KEY=<key> \
  --env DAYTONA_API_KEY=<key>
```

**GRPO config path:**  
`skyrl-train/tasks/harbor-grpo-qwen3-8b.yaml`  
(GSM8K SkyPilot reference: `skyrl-train/examples/gsm8k/gsm8k-grpo-skypilot.yaml`)

**Supported base models (out of the box):**
- Qwen/Qwen3-8B ✅ (has dedicated harbor task YAML)
- Qwen/Qwen3-0.6B, Qwen3-4B, Qwen3-Coder-30B-A3B-Instruct
- Qwen/Qwen2.5-0.5B-Instruct, 1.5B-Instruct, 3B-Instruct, 7B-Instruct (Coder), 32B-Instruct
- Qwen/Qwen1.5-MoE-A2.7B-Chat
- unsloth/gpt-oss-20b-BF16
- Any HF model path via `trainer.policy.model.path=<path>` override
