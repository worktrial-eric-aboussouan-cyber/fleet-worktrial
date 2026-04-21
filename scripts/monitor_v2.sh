#!/usr/bin/env bash
CLUSTER="fleet-swe-final"
WANDB_FILE="notes/wandb-url-v2.txt"
REWARD_LOG="logs/rewards-v2.log"
START_TIME=$(date +%s)

for i in {1..20}; do
  echo "--- Poll $i @ $(date) ---"
  LOGS=$(sky logs $CLUSTER --no-follow 2>&1)
  
  # Capture WandB URL
  WANDB=$(echo "$LOGS" | grep -o "https://wandb.ai/[^ ]*" | head -n 1)
  if [ -n "$WANDB" ]; then 
    echo "$WANDB" > $WANDB_FILE
    RUN_ID=$(echo "$WANDB" | sed 's|.*/||')
  fi
  
  # Log rewards
  echo "$LOGS" | grep -i "step" | grep -i "reward" >> $REWARD_LOG
  
  # Fail fast check
  if echo "$LOGS" | grep -Ei "OOM|CUDA|Traceback" > /dev/null; then
    echo "FATAL ERROR DETECTED"
    exit 1
  fi

  # Hard stop at 30 min
  ELAPSED=$(( $(date +%s) - $START_TIME ))
  if [ $ELAPSED -gt 1800 ]; then exit 0; fi

  sleep 90
done
