# Root Cause: All Rollouts Erroring (reward = 0, num_error_trajectories = 40)

## Discovery Date
2026-04-21, identified during live sprint

## Symptom
- WandB run `h46gf83j`: Steps 1+, rewards all 0
- `generate/num_error_trajectories`: 40 (equal to batch size = all rollouts failing)
- `eval/all/generate/max_num_tokens`: 1 (critical tell)
- `eval/all/generate/avg_num_tokens`: 1

## Root Cause

`generator.max_input_length` defaults to **512 tokens** in `skyrl_train/config/config.py` (line 362):

```python
@dataclass
class GeneratorConfig(BaseConfig):
    ...
    max_input_length: int = 512   # <--- THE CULPRIT
```

Our launch YAML never overrode this. Harbor task prompts (system prompt + SWE-bench issue description) are typically 3000-8000 tokens. When the vLLM engine receives a request with `prompt_tokens >> max_input_length`, it truncates the input so severely that only 1 token of generation budget remains, resulting in every rollout immediately terminating with an error/empty trajectory.

Additionally, `generator.sampling_params.max_generate_length` defaulted to **1024 tokens** — far too short for multi-turn SWE-bench agent responses (which need 4000-8000 tokens per turn).

## Fix Applied

Added to `harbor-train/skyrl-train/tasks/harbor-grpo-qwen3-8b.yaml`:

```yaml
generator.max_input_length=16384
generator.sampling_params.max_generate_length=8192
generator.eval_sampling_params.max_generate_length=4096
```

Also applied same fix to 4B YAML for Track A cluster.

## Confidence
High. The `max_num_tokens: 1` in WandB is a deterministic signal that the model was being constrained to output exactly 1 token. This is the canonical symptom of `prompt_len >= max_model_len - max_generate_length` where `max_model_len` is set by vLLM and `max_input_length` controls how much of the prompt survives.

## Status
Fix applied and relaunched on `fleet-swe-final` (A100). Monitoring for non-zero `max_num_tokens` in next WandB step.
