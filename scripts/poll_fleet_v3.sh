#!/usr/bin/env bash
SUMMARY="logs/train-first-steps.log"
WANDB_FILE="notes/wandb-url.txt"
touch $WANDB_FILE

for i in {1..7}; do
  echo "--- Check $i @ $(date) ---"
  STATUS=$(sky status fleet-swe-v3 2>/dev/null)
  echo "$STATUS"
  
  if echo "$STATUS" | grep -q "UP"; then
    LOGS=$(sky logs fleet-swe-v3 --no-follow 2>&1)
    echo "$LOGS" | tail -n 30
    
    # Capture WandB
    WANDB=$(echo "$LOGS" | grep -o "https://wandb.ai/[^ ]*" | head -n 1)
    if [ -n "$WANDB" ]; then echo "$WANDB" > $WANDB_FILE; fi
    
    # Check for Error
    if echo "$LOGS" | grep -Ei "OOM|CUDA|Traceback" > /dev/null; then
       echo "FATAL ERROR DETECTED"
       echo "$LOGS" | tail -n 200 > logs/train-error.log
       exit 1
    fi
    
    # Check for Activity
    if echo "$LOGS" | grep -Ei "step|reward" > /dev/null; then
       echo "Training Active. Capturing logs..."
       echo "$LOGS" > $SUMMARY
       # Check for non-zero reward or first step
       break
    fi
  fi
  sleep 120
done
