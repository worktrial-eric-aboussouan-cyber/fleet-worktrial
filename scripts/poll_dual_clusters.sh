#!/usr/bin/env bash
WANDB_FILE="notes/wandb-url.txt"
START_TIME=$(date +%s)

while true; do
  echo "--- Poll @ $(date) ---"
  source .venv/bin/activate
  
  for CLUSTER in "fleet-swe-a100" "fleet-swe-l4-4b"; do
    STATUS=$(sky status $CLUSTER 2>/dev/null)
    echo "[$CLUSTER] Status: $(echo "$STATUS" | grep $CLUSTER | awk '{print $ status}')"
    
    if echo "$STATUS" | grep -q "UP"; then
      LOGS=$(sky logs $CLUSTER --no-follow 2>&1)
      WANDB=$(echo "$LOGS" | grep -o "https://wandb.ai/[^ ]*" | head -n 1)
      if [ -n "$WANDB" ]; then
        echo "$WANDB" > $WANDB_FILE
        echo "WINNER: $CLUSTER with $WANDB"
        # Kill the other
        OTHER="fleet-swe-a100"
        if [ "$CLUSTER" == "fleet-swe-a100" ]; then OTHER="fleet-swe-l4-4b"; fi
        sky down $OTHER -y
        exit 0
      fi
    fi
  done
  
  sleep 300 # 5 min
done
