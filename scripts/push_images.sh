#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PASSED=$(jq -r '.ok[]' tasks/validation_summary.json)
for id in $PASSED; do
  TASK_JSON=$(grep -l "\"instance_id\": \"$id\"" tasks/task_*/task.json)
  OLD_IMG=$(jq -r .image_name "$TASK_JSON")
  NEW_IMG="ghcr.io/$GH_USER/swe-$id:latest"
  
  echo ">>> Re-tagging $OLD_IMG -> $NEW_IMG"
  docker tag "$OLD_IMG" "$NEW_IMG"
  
  echo ">>> Pushing $NEW_IMG"
  docker push "$NEW_IMG"
  
  tmp=$(mktemp)
  jq -S --arg img "$NEW_IMG" '.image_name = $img' "$TASK_JSON" > "$tmp" && mv "$tmp" "$TASK_JSON"
done
