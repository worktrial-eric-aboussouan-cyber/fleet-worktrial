#!/usr/bin/env bash
A100="fleet-swe-final"
L4="fleet-swe-l4-backup"
WANDB_FILE="notes/wandb-url-final.txt"
START_TIME=$(date +%s)

for i in {1..20}; do
  ELAPSED=$(( $(date +%s) - $START_TIME ))
  echo "--- Poll $i (T+$((ELAPSED/60)) min) @ $(date) ---"
  
  # 1. Check A100 status
  A_LOGS=$(sky logs $A100 --no-follow 2>&1)
  if echo "$A_LOGS" | grep -q "View run"; then
    URL=$(echo "$A_LOGS" | grep -o "https://wandb.ai/[^ ]*" | tail -n 1)
    echo "WINNER: $A100 with $URL"
    echo "$URL" > $WANDB_FILE
    sky down $L4 -y
    exit 0
  fi
  
  # 2. Check L4 status
  L_LOGS=$(sky logs $L4 --no-follow 2>&1)
  if echo "$L_LOGS" | grep -q "View run"; then
    URL=$(echo "$L_LOGS" | grep -o "https://wandb.ai/[^ ]*" | tail -n 1)
    echo "WINNER: $L4 with $URL"
    echo "$URL" > $WANDB_FILE
    sky down $A100 -y
    exit 0
  fi
  
  # 3. T+15 Failover
  if [ $ELAPSED -gt 900 ] && ! echo "$A_LOGS" | grep -q "Started: 'eval'"; then
    echo "A100 STUCK IN SETUP. KILLING AND PIVOTING TO L4."
    sky down $A100 -y
  fi
  
  # 4. T+30 Hard Stop
  if [ $ELAPSED -gt 1800 ]; then
    echo "HARD STOP REACHED."
    sky down $A100 $L4 -y
    exit 0
  fi
  
  sleep 90
done
