#!/usr/bin/env bash
LOG_FILE="logs/server_polling.log"
echo "--- Starting Server Poll ---" > $LOG_FILE

while true; do
  echo "--- Poll at $(date) ---" >> $LOG_FILE
  
  echo ">>> STATUS:" >> $LOG_FILE
  sky status >> $LOG_FILE 2>&1
  
  echo ">>> A100 (Track B) LAST 10 LINES:" >> $LOG_FILE
  sky logs fleet-swe-final --no-follow 2>&1 | tail -n 10 >> $LOG_FILE
  
  echo ">>> L4 (Track A) LAST 10 LINES:" >> $LOG_FILE
  sky logs fleet-swe-track-a --no-follow 2>&1 | tail -n 10 >> $LOG_FILE
  
  echo "---------------------------" >> $LOG_FILE
  sleep 60
done
