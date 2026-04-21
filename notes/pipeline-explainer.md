# Pipeline Explainer: SWE-bench Training

This document explains the architecture of the end-to-end pipeline and the mechanics of the GRPO training loop.

## 1. System Architecture

The pipeline integrates several specialized services to enable automated training on real-world software bugs.

### Key Components

*   **GitHub**: The source of truth for "ground truth" data. We scrape closed PRs that link to issues. The PR diff provides the **Gold Patch** (the solution), and the repository state before the PR provides the **Base Commit** (the buggy environment).
*   **Docker**: Provides environment isolation. Every task is materialized into a unique Docker image containing the code at the base commit, all dependencies, and a customized `eval_script.sh`.
*   **GHCR (GitHub Container Registry)**: A public host for our Docker images. These images must be public so that remote sandbox providers can pull them without complex authentication.
*   **SkyPilot**: An orchestration layer that allows us to run heavy GPU workloads (4x L4 GPUs) on GCP using a simple YAML config. It handles cluster provisioning, environment setup, and log tailing.
*   **Daytona**: The **Sandbox Provider**. During training, the model needs to "try out" its code fixes. Daytona creates ephemeral, high-performance remote environments by pulling our Docker images from GHCR.
*   **WandB (Weights & Biases)**: The monitoring dashboard. It tracks training metrics (reward, loss, grad norm) and stores the model's intermediate "thoughts" and code attempts.

### How they interact
1.  **Preparation**: Local scripts scrape **GitHub**, build **Docker** images, and push them to **GHCR**.
2.  **Launch**: **SkyPilot** starts a GPU cluster on GCP and initiates the training script.
3.  **Rollout**: The training script requests a sandbox from **Daytona**.
4.  **Execution**: Daytona pulls the image from **GHCR**, and the model executes bash commands within it.
5.  **Feedback**: The exit code of the `eval_script.sh` is returned to the trainer as a reward, which is logged to **WandB**.

---

## 2. The Training Loop (GRPO)

We use **Group Relative Policy Optimization (GRPO)**, a reinforcement learning algorithm that enables the model to improve through trial and error.

### Model Architecture on the GCP Cluster
The 4x L4 GPU cluster hosts **two copies** of the Qwen3-8B model simultaneously:
1.  **Policy Model**: The "active student" that is being updated and trained.
2.  **Reference Model**: A "frozen" copy of the original model. It is used to ensure the Policy Model doesn't drift too far or "forget" how to speak English (KL Divergence penalty).

### The Loop Steps

1.  **Prompting**: The trainer script (on **GCP**) sends the Problem Statement to the **Policy Model**.
2.  **Sampling (Group Generation)**:
    - **Where**: This happens entirely on the **GCP GPU Cluster**.
    - **Process**: The **Policy Model** generates $N$ different attempts (e.g., $N=16$). Each attempt includes a "thought" process and a code patch.
3.  **Evaluation (Off-Cluster)**: 
    - Each of the $N$ attempts is sent to an individual **Daytona Sandbox**.
    - **Daytona** pulls the task image from **GHCR** and applies the model's patch.
    - The `eval_script.sh` is executed inside the sandbox.
    - **Reward Calculation**: If the tests pass, the reward is `1.0`. If they fail, `0.0`.
4.  **Relative Optimization (On-Cluster)**: 
    - The trainer compares the rewards within the group.
    - It also compares the **Policy Model's** output probability against the **Reference Model's** probability.
    - It penalizes attempts that performed worse than the group average and rewards those that did better.
5.  **Policy Update**: The **Policy Model's** weights are updated. The **Reference Model** remains frozen.
6.  **Repeat**: This continues for multiple iterations across the 12 tasks.

---
*Created for the Fleet SWE Worktrial.*
