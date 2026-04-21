#!/usr/bin/env bash
CLUSTER="fleet-swe-a100"
REWARD_LOG="logs/first-rewards.log"
touch $REWARD_LOG
COUNT=0

for i in {1..30}; do
  echo "--- Poll $i @ $(date) ---"
  LOGS=$(sky logs $CLUSTER --no-follow 2>&1)
  
  # Check for error
  if echo "$LOGS" | grep -Ei "OOM|CUDA|Traceback" > /dev/null; then
    echo "FATAL_ERROR_FOUND"
    echo "$LOGS" | grep -Ei "OOM|CUDA|Traceback" -B 20 -A 20
    exit 1
  fi
  
  # Check for steps with rewards
  # Example pattern: "step: 5, reward: 0.123"
  NEW_STEPS=$(echo "$LOGS" | grep -i "step" | grep -i "reward" | tail -n $((3 - COUNT)))
  if [ -n "$NEW_STEPS" ]; then
    while read -r line; do
      echo "$(date): $line" >> $REWARD_LOG
      COUNT=$((COUNT + 1))
      if [ "$COUNT" -ge 3 ]; then
        echo "TARGET_REACHED"
        exit 0
      fi
    done <<< "$NEW_STEPS"
  fi
  
  sleep 90
done
