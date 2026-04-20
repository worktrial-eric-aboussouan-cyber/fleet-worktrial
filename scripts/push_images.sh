#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PASSED=$(jq -r '.ok[]' tasks/validation_summary.json)
for id in $PASSED; do
  DIR=$(grep -l "\"instance_id\": \"$id\"" tasks/task_*/task.json | xargs dirname)
  IMG=$(jq -r .image_name "$DIR/task.json")
  echo ">>> $id -> $IMG"
  docker build -t "$IMG" "$DIR" && docker push "$IMG"
done
# Handle empty case for wc -l
NUM_IMAGES=$(echo "$PASSED" | grep -c . || echo 0)
echo "done: $NUM_IMAGES images"
