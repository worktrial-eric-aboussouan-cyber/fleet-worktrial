# Harbor Training & Daytona Integration Analysis

## 1. SWE Training Configuration
The primary SkyPilot task configuration for training on Harbor-managed sandboxes is located at [harbor-grpo-qwen3-8b.yaml](file:///Users/fleet/fleet-worktrial/harbor-train/skyrl-train/tasks/harbor-grpo-qwen3-8b.yaml).

```yaml
# /Users/fleet/fleet-worktrial/harbor-train/skyrl-train/tasks/harbor-grpo-qwen3-8b.yaml (Full File)
# Harbor GRPO Training via SkyPilot - Qwen3-8B
# Usage: sky launch skyrl-train/tasks/harbor-grpo-qwen3-8b.yaml --env WANDB_API_KEY=<key> --env DAYTONA_API_KEY=<key>
#
# This task trains GRPO on Harbor-managed sandboxed environments (CodeContests, TerminalBench, etc).
# Harbor handles sandbox lifecycle, agent execution, and verification.
# SkyRL handles training via the HarborGenerator interface.
#
# Model: Qwen/Qwen3-8B (8B parameters)
# GPUs: B200:4 (preferred), H200:4 (fallback)
# Agent: Terminus-2 (configurable via harbor_trial_config)

name: harbor-grpo-qwen3-8b

resources:
  disk_size: 500
  ports: 6479
  any_of:
    - accelerators: B200:4
      cloud: lambda
      memory: 750+
    - accelerators: B200:4
      cloud: runpod
      memory: 750+
    - accelerators: B200:4
      cloud: primeintellect
      memory: 750+
    - accelerators: H200-SXM:4
      cloud: lambda
      memory: 750+
    - accelerators: H200-SXM:4
      cloud: runpod
      memory: 750+
    - accelerators: H200-SXM:4
      cloud: vast
      memory: 750+
    - accelerators: H200-SXM:4
      cloud: primeintellect
      memory: 750+

num_nodes: 1

workdir:
  url: https://github.com/fleet-ai/harbor-train.git
  ref: main

envs:
  WANDB_API_KEY: ""
  # Sandbox provider credentials (set at least one)
  DAYTONA_API_KEY: ""
  MODAL_TOKEN_ID: ""
  MODAL_TOKEN_SECRET: ""
  # Harbor dataset (HuggingFace dataset name)
  TRAIN_DATASET: "open-thoughts/CodeContests"
  EVAL_DATASET: "open-thoughts/OpenThoughts-TB-dev"
  # Sandbox provider: daytona or modal
  SANDBOX_PROVIDER: "daytona"
  # Training parameters
  RUN_NAME: "harbor-codecontest"
  NUM_EPOCHS: "3"
  MAX_MODEL_LEN: "32768"
  MINI_BATCH_SIZE: "32"
  N_SAMPLES_PER_PROMPT: "8"
  EVAL_N_SAMPLES_PER_PROMPT: "4"
  LR: "1.0e-6"
  # Rate limiting for sandbox provider
  TRAJECTORIES_PER_SECOND: "5"
  MAX_CONCURRENCY: "512"
  # Agent config
  AGENT_NAME: "terminus-2"
  AGENT_MAX_TURNS: "32"
  AGENT_TIMEOUT_SEC: "1200"

setup: |
  set -euo pipefail
  cd skyrl-train

  echo "Validating environment variables..."
  if [ -z "$WANDB_API_KEY" ]; then echo "ERROR: WANDB_API_KEY is required"; exit 1; fi
  if [ "$SANDBOX_PROVIDER" = "daytona" ] && [ -z "$DAYTONA_API_KEY" ]; then echo "ERROR: DAYTONA_API_KEY is required for daytona provider"; exit 1; fi
  if [ "$SANDBOX_PROVIDER" = "modal" ] && ([ -z "$MODAL_TOKEN_ID" ] || [ -z "$MODAL_TOKEN_SECRET" ]); then echo "ERROR: MODAL_TOKEN_ID and MODAL_TOKEN_SECRET are required for modal provider"; exit 1; fi
  echo "Environment validation passed"

  uv venv --python 3.12 --seed
  source .venv/bin/activate
  uv sync --extra vllm --extra harbor

  # Prepare datasets from HuggingFace
  DATA_DIR="$HOME/data/harbor"
  mkdir -p "$DATA_DIR"
  echo "Preparing training dataset: $TRAIN_DATASET"
  python examples/harbor/prepare_harbor_dataset.py --dataset "$TRAIN_DATASET"
  echo "Preparing eval dataset: $EVAL_DATASET"
  python examples/harbor/prepare_harbor_dataset.py --dataset "$EVAL_DATASET"

run: |
  set -euo pipefail
  cd skyrl-train
  source .venv/bin/activate

  TMP_DIR="$HOME/skyrl-tmp"
  mkdir -p "$TMP_DIR"
  export TMPDIR="$TMP_DIR"
  export PYTORCH_ALLOC_CONF=expandable_segments:True

  # Login to Weights & Biases
  uv run -- python3 -c "import wandb; wandb.login(relogin=True, key='$WANDB_API_KEY')"

  # Ray cluster setup
  export RAY_RUNTIME_ENV_HOOK=ray._private.runtime_env.uv_runtime_env_hook.hook
  export RAY_object_store_memory=10000000000
  if ! ray status --address 127.0.0.1:6479 >/dev/null 2>&1; then
    ray start --head --disable-usage-stats --port 6479 --object-store-memory=10000000000
  fi
  for i in $(seq 1 24); do
    if ray status --address 127.0.0.1:6479 >/dev/null 2>&1; then break; fi
    sleep 5
  done

  TOTAL_GPUS=$SKYPILOT_NUM_GPUS_PER_NODE

  DATA_DIR="$HOME/data/harbor"
  TRAIN_DIR=$(echo "$TRAIN_DATASET" | sed 's|.*/||')
  EVAL_DIR=$(echo "$EVAL_DATASET" | sed 's|.*/||')
  CKPTS_DIR="$HOME/$RUN_NAME/ckpts"
  EXPORTS_DIR="$HOME/$RUN_NAME/exports"
  TRIALS_DIR="$HOME/$RUN_NAME/trials_run"
  LOG_DIR="/tmp/skyrl-logs/$RUN_NAME"

  CHAT_TEMPLATE_PATH="skyrl_train/utils/templates/qwen3_acc_thinking.jinja2"

  python -m examples.harbor.entrypoints.main_harbor \
    data.train_data="['$DATA_DIR/$TRAIN_DIR']" \
    data.val_data="['$DATA_DIR/$EVAL_DIR']" \
    trainer.policy.model.path=Qwen/Qwen3-8B \
    generator.served_model_name=Qwen3-8B \
    hydra.searchpath="['file://examples/harbor']" \
    +harbor_trial_config=default \
    ++harbor_trial_config.trials_dir=$TRIALS_DIR \
    ++harbor_trial_config.agent.name=$AGENT_NAME \
    ++harbor_trial_config.agent.override_timeout_sec=$AGENT_TIMEOUT_SEC \
    ++harbor_trial_config.agent.kwargs.max_turns=$AGENT_MAX_TURNS \
    ++harbor_trial_config.environment.type=$SANDBOX_PROVIDER \
    trainer.export_path=$EXPORTS_DIR \
    trainer.ckpt_path=$CKPTS_DIR \
    trainer.log_path=$LOG_DIR \
    trainer.algorithm.advantage_estimator=grpo \
    trainer.algorithm.loss_reduction=seq_mean_token_sum_norm \
    trainer.algorithm.grpo_norm_by_std=false \
    trainer.algorithm.use_kl_loss=false \
    trainer.placement.colocate_all=true \
    trainer.strategy=fsdp2 \
    trainer.placement.policy_num_nodes=1 \
    trainer.placement.ref_num_nodes=1 \
    trainer.placement.policy_num_gpus_per_node=$TOTAL_GPUS \
    trainer.placement.ref_num_gpus_per_node=$TOTAL_GPUS \
    generator.num_inference_engines=$TOTAL_GPUS \
    generator.inference_engine_tensor_parallel_size=1 \
    +generator.engine_init_kwargs.chat_template=$CHAT_TEMPLATE_PATH \
    +generator.engine_init_kwargs.max_model_len=$MAX_MODEL_LEN \
    +generator.engine_init_kwargs.enable_log_requests=false \
    trainer.epochs=$NUM_EPOCHS \
    trainer.eval_batch_size=128 \
    trainer.eval_before_train=true \
    trainer.eval_interval=20 \
    trainer.update_epochs_per_batch=1 \
    trainer.train_batch_size=$MINI_BATCH_SIZE \
    trainer.policy_mini_batch_size=$MINI_BATCH_SIZE \
    trainer.micro_forward_batch_size_per_gpu=1 \
    trainer.micro_train_batch_size_per_gpu=1 \
    trainer.ckpt_interval=5 \
    trainer.hf_save_interval=5 \
    trainer.algorithm.max_seq_len=$MAX_MODEL_LEN \
    trainer.policy.optimizer_config.lr=$LR \
    generator.n_samples_per_prompt=$N_SAMPLES_PER_PROMPT \
    generator.eval_n_samples_per_prompt=$EVAL_N_SAMPLES_PER_PROMPT \
    generator.apply_overlong_filtering=true \
    generator.gpu_memory_utilization=0.8 \
    trainer.logger=wandb \
    trainer.project_name=harbor \
    trainer.run_name=$RUN_NAME \
    trainer.resume_mode=latest \
    generator.backend=vllm \
    generator.run_engines_locally=true \
    generator.weight_sync_backend=nccl \
    generator.async_engine=true \
    generator.batched=false \
    generator.enforce_eager=false \
    generator.enable_http_endpoint=true \
    generator.http_endpoint_host=127.0.0.1 \
    generator.http_endpoint_port=8000 \
    +generator.rate_limit.enabled=true \
    +generator.rate_limit.trajectories_per_second=$TRAJECTORIES_PER_SECOND \
    +generator.rate_limit.max_concurrency=$MAX_CONCURRENCY
```

## 2. Task Instance Loading
Tasks are prepared using [prepare_harbor_dataset.py](file:///Users/fleet/fleet-worktrial/harbor-train/skyrl-train/examples/harbor/prepare_harbor_dataset.py) and loaded via Hydra in the entrypoint.

- **Format**: 
  - **HF Dataset (Parquet)**: "parquet files containing tar-archived task directories (columns: path, task_binary)" ([L4-5](file:///Users/fleet/fleet-worktrial/harbor-train/skyrl-train/examples/harbor/prepare_harbor_dataset.py#L4-L5)).
  - **Directory of Folders**: Extracted into a local directory where each subfolder represents a task ([L75-76](file:///Users/fleet/fleet-worktrial/harbor-train/skyrl-train/examples/harbor/prepare_harbor_dataset.py#L75-L76)).
- **Fields required**:
  - Each task folder needs an `instruction.md` ([L81](file:///Users/fleet/fleet-worktrial/harbor-train/skyrl-train/examples/harbor/prepare_harbor_dataset.py#L81)).
  - In `harbor-grpo-qwen3-8b.yaml`, data is passed via `data.train_data` and `data.val_data` ([L132-133](file:///Users/fleet/fleet-worktrial/harbor-train/skyrl-train/tasks/harbor-grpo-qwen3-8b.yaml#L132-L133)).

## 3. Daytona Integration & Docker Images
The integration is managed through the `HarborGenerator` which interfaces with Harbor's `Trial` system.

- **Pulling Docker Images**: The image name is retrieved directly from the task instance record. If it's missing, it defaults to a pre-built SWE-bench image URL.
- **Reference**:
  - [mini_swe_utils.py:L38](file:///Users/fleet/fleet-worktrial/harbor-train/skyrl-train/examples/mini_swe_agent/mini_swe_utils.py#L38): `image_name = instance.get("image_name", None)`
  - [mini_swe_utils.py:L40-47](file:///Users/fleet/fleet-worktrial/harbor-train/skyrl-train/examples/mini_swe_agent/mini_swe_utils.py#L40-L47): Fallback logic for `docker.io/swebench/sweb.eval...` images.

## 4. Reward Function & Eval Script
The reward calculation relies on the exit code of the evaluation script.

- **Logic**: It parses the **return code** of the `eval_cmd` (which runs the `eval_script`). A code of `0` is treated as success.
- **Reference**:
  - [mini_swe_utils.py:L80-85](file:///Users/fleet/fleet-worktrial/harbor-train/skyrl-train/examples/mini_swe_agent/mini_swe_utils.py#L80-L85): 
    ```python
    80:         eval_script = instance["eval_script"]
    81:         eval_cmd = f"bash <<'EOF'\n{eval_script}\nEOF"
    ...
    85:         ret["resolved"] = obs["returncode"] == 0
    ```
  - [harbor_generator.py:L268](file:///Users/fleet/fleet-worktrial/harbor-train/skyrl-train/examples/harbor/harbor_generator.py#L268): `reward = results.verifier_result.rewards["reward"]`

## 5. Environment Variables & Secrets
The following secrets are explicitly checked during the `setup` phase of the `sky launch` task:

- **WANDB_API_KEY**: Required ([L78](file:///Users/fleet/fleet-worktrial/harbor-train/skyrl-train/tasks/harbor-grpo-qwen3-8b.yaml#L78)).
- **DAYTONA_API_KEY**: Required if `SANDBOX_PROVIDER` is "daytona" ([L79](file:///Users/fleet/fleet-worktrial/harbor-train/skyrl-train/tasks/harbor-grpo-qwen3-8b.yaml#L79)).
- **MODAL_TOKEN_ID / MODAL_TOKEN_SECRET**: Required if using "modal" ([L80](file:///Users/fleet/fleet-worktrial/harbor-train/skyrl-train/tasks/harbor-grpo-qwen3-8b.yaml#L80)).
- **HF_TOKEN**: Not listed in the `envs` block ([L46-51](file:///Users/fleet/fleet-worktrial/harbor-train/skyrl-train/tasks/harbor-grpo-qwen3-8b.yaml#L46-L51)), but typically needed for gated models.
- **GCR auth**: Not explicitly mentioned in this YAML, though required for registry access if pulling private images.

## 6. Default GPU Specification
The task allows for several accelerator types, with a preference for B200s.

- **Preferred**: `B200:4` ([L18](file:///Users/fleet/fleet-worktrial/harbor-train/skyrl-train/tasks/harbor-grpo-qwen3-8b.yaml#L18)).
- **Fallback**: `H200-SXM:4` ([L27](file:///Users/fleet/fleet-worktrial/harbor-train/skyrl-train/tasks/harbor-grpo-qwen3-8b.yaml#L27)).
- **Resources section**: [L14-38](file:///Users/fleet/fleet-worktrial/harbor-train/skyrl-train/tasks/harbor-grpo-qwen3-8b.yaml#L14-L38).
