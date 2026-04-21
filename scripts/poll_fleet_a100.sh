#!/usr/bin/env bash
CLUSTER="fleet-swe-a100"
YAML="harbor-train/skyrl-train/tasks/harbor-grpo-qwen3-8b.yaml"
WANDB_FILE="notes/wandb-url.txt"
START_TIME=$(date +%s)

for i in {1..8}; do # Poll every 2 min for 16 min
  echo "--- Poll $i (T+$(( ( $(date +%s) - $START_TIME ) / 60 )) min) ---"
  source .venv/bin/activate
  STATUS=$(sky status $CLUSTER 2>/dev/null)
  echo "$STATUS"
  
  if echo "$STATUS" | grep -q "UP"; then
    echo "Cluster is UP. Checking logs..."
    LOGS=$(sky logs $CLUSTER --no-follow 2>&1)
    WANDB=$(echo "$LOGS" | grep -o "https://wandb.ai/[^ ]*" | head -n 1)
    if [ -n "$WANDB" ]; then
      echo "$WANDB" > $WANDB_FILE
      echo "WANDB_FOUND: $WANDB"
      exit 0
    fi
  fi
  
  # Check if we should fail over after 15 min
  ELAPSED=$(( $(date +%s) - $START_TIME ))
  if [ "$ELAPSED" -gt 900 ] && ! echo "$STATUS" | grep -q "UP"; then
    echo "TIMEOUT: Cluster not UP after 15 min. Failing over to us-central1..."
    sky down $CLUSTER -y
    sky launch $YAML -c fleet-swe-a100-us --region us-central1 -y --env WANDB_API_KEY=$WANDB_API_KEY --env DAYTONA_API_KEY=$DAYTONA_API_KEY
    exit 0
  fi
  
  sleep 120
done
