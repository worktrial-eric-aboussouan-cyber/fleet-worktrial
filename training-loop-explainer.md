# Training Loop — How Everything Fits Together

## The Big Picture

We're training an LLM (Qwen3-8B) to get better at fixing software bugs. The training signal comes from whether the model's code patch actually passes the repo's tests.

```
GitHub PRs → Task Instances → Docker Images → GCP GPU Training → Reward Signal → Better Model
```

---

## Services and What They Do

### 1. GitHub (data source)
- `scrape_prs.py` pulls merged PRs from `psf/requests`, `pallets/click`, etc.
- Each PR becomes a **task**: here's a broken repo + a test that fails, fix it.
- We extract: the base commit (broken state), the gold patch (correct fix), and the test files.

### 2. Docker (task environments)
- Each task gets a `Dockerfile` that clones the repo at `base_commit` and installs deps.
- This is the **sandbox** the agent runs inside — isolated, reproducible.
- `eval_script.sh` runs pytest inside the container and returns 0 (pass) or 1 (fail).
- Images are built locally and pushed to GCR (Google Container Registry).

### 3. GCR — Google Container Registry (`gcr.io/fleet-compute-489000`)
- Stores the built Docker images so GCP training machines can pull them.
- Each task image is ~`gcr.io/fleet-compute-489000/swe-task-requests-7328:latest`

### 4. SkyPilot (compute orchestration)
- `sky launch` spins up a GPU VM on GCP (or Lambda/RunPod) and runs the training job.
- Handles: node provisioning, file sync, teardown.
- Config lives in `harbor-grpo-qwen3-8b.yaml`.

### 5. GCP (compute)
- Provides the actual GPU machines (A100s via SkyPilot).
- Project: `fleet-compute-489000`
- Also hosts GCR for image storage.

### 6. Harbor (agent + environment framework)
- Manages the **trial loop**: for each training prompt, Harbor spins up a Docker sandbox, runs the agent inside it, and calls `eval_script.sh` to get a reward.
- The agent (Terminus-2 or OHCodeAct) sees the problem statement and tries to produce a patch.
- Harbor returns: did the patch pass the tests? → reward = 1.0 or 0.0.

### 7. SkyRL / veRL (training framework)
- Implements **GRPO** (Group Relative Policy Optimization) — a variant of PPO used for RL on LLMs.
- Takes the agent's trajectories (prompt → patch → reward) and updates model weights.
- Logs metrics (reward mean, grad norm, etc.) to W&B.

### 8. W&B (Weights & Biases)
- Tracks the training reward curve over steps.
- Key deliverable: reward must go from ~0 → non-zero and improve over time.
- If reward stays at 0.0, tasks are broken or too hard.

### 9. vLLM (inference engine)
- Runs the model efficiently during training for rollout generation.
- SkyRL spins this up automatically on the GPU node.

---

## Data Flow During Training

```
1. SkyRL samples a task from our dataset (problem_statement from task.json)
2. vLLM generates a patch attempt (the model's rollout)
3. Harbor spins up the Docker container for that task
4. Harbor applies the patch and runs eval_script.sh
5. eval_script.sh runs pytest → exit 0 (pass) or exit 1 (fail)
6. Harbor returns reward 1.0 or 0.0 to SkyRL
7. SkyRL runs GRPO update on the model weights
8. Repeat for next batch
```

---

## Our Task Format

```
tasks/task_001/
├── task.json        # instance_id, repo, base_commit, problem_statement, gold_patch, image_name
├── Dockerfile       # clones repo at base_commit, installs deps
└── eval_script.sh   # runs pytest on the relevant test files
```

The `image_name` in `task.json` points to GCR so Harbor knows which container to pull.

---

## What We Still Need to Configure

- `environment.type: docker` in Harbor config (not `daytona`) — we're using our own images
- A HuggingFace dataset wrapping our `task.json` files — SkyRL reads data from HF format
- GPU node with enough VRAM for Qwen3-8B (needs ~4x A100 80GB or H200)
- `WANDB_API_KEY` set for logging

---

## Key Question for Colleagues

> The `skyrl_swe.yaml` config uses `environment.type: daytona`. For our self-hosted Docker task images on GCR, should we set `environment.type: docker` and point `image_name` at our GCR images? Or does Harbor pull the image automatically from `task.json`?
