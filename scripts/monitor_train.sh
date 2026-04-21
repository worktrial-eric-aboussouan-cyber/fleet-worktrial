#!/usr/bin/env bash
mkdir -p logs
mkdir -p notes
touch notes/wandb-url.txt
REWARD_ZEROS=0

for i in {1..6}; do
  echo "--- Check $i @ $(date) ---" | tee -a logs/train-monitor.log
  source .venv/bin/activate
  sky status >> logs/train-monitor.log
  
  # Get logs
  LOGS=$(sky logs sky-bc93-fleet --no-follow 2>&1)
  echo "$LOGS" | tail -n 50 >> logs/train-monitor.log
  
  # 1. Extract WANDB URL
  WANDB=$(echo "$LOGS" | grep -o "https://wandb.ai/[^ ]*" | head -n 1)
  if [ -n "$WANDB" ] && [ ! -s notes/wandb-url.txt ]; then
    echo "$WANDB" > notes/wandb-url.txt
    echo "WandB URL found: $WANDB"
  fi
  
  # 2. Check for OOM / Errors
  if echo "$LOGS" | grep -Ei "CUDA out of memory|OOM|traceback|DAYTONA_IMAGE_FAIL" > /dev/null; then
    ERROR_LINE=$(echo "$LOGS" | grep -Ei "CUDA out of memory|OOM|traceback|DAYTONA_IMAGE_FAIL" | tail -n 1)
    echo "CRITICAL_ERROR: $ERROR_LINE" >> logs/train-monitor.log
    break
  fi
  
  # 3. Reward check
  REWARD=$(echo "$LOGS" | grep -o "reward: [0-9.]*" | tail -n 1 | awk '{print $2}')
  if [ -n "$REWARD" ]; then
    if (( $(echo "$REWARD == 0" | bc -l) )); then
      REWARD_ZEROS=$((REWARD_ZEROS + 1))
    else
      REWARD_ZEROS=0
    fi
    if [ "$REWARD_ZEROS" -ge 3 ]; then
       echo "REWARD_STUCK_AT_ZERO" >> logs/train-monitor.log
    fi
  fi

  sleep 180
done

# Generate summary
echo "Generating summary..."
SUMMARY="notes/train-status.md"
echo "# Training Status Summary" > $SUMMARY
echo "- Timestamp: $(date)" >> $SUMMARY
STEP=$(grep -o "step: [0-9]*" logs/train-monitor.log | tail -n 1)
REWARD=$(grep -o "reward: [0-9.]*" logs/train-monitor.log | tail -n 1)
GNORM=$(grep -o "grad_norm: [0-9.]*" logs/train-monitor.log | tail -n 1)
WANDB=$(cat notes/wandb-url.txt)

echo "- Step: ${STEP:-0}" >> $SUMMARY
echo "- Latest Reward: ${REWARD:-N/A}" >> $SUMMARY
echo "- Grad Norm: ${GNORM:-N/A}" >> $SUMMARY
echo "- WandB: ${WANDB:-Pending}" >> $SUMMARY

if grep "CRITICAL_ERROR" logs/train-monitor.log; then
  echo "- Status: ERROR ($(grep 'CRITICAL_ERROR' logs/train-monitor.log | tail -n 1))" >> $SUMMARY
elif grep "REWARD_STUCK_AT_ZERO" logs/train-monitor.log; then
  echo "- Status: REWARD STUCK AT ZERO" >> $SUMMARY
else
  echo "- Status: Healthy" >> $SUMMARY
fi
