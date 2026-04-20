#!/usr/bin/env python3
import json
import os
import tarfile
import io
import pandas as pd
from pathlib import Path

def create_task_tar(task_dir):
    """Create a tar.gz archive of the task directory content (instruction.md, etc)."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        # We need an instruction.md for Harbor to recognize it as a task
        # We'll use the problem_statement from task.json as the instruction
        task_json_path = task_dir / "task.json"
        if not task_json_path.exists():
            return None
        
        task_data = json.loads(task_json_path.read_text())
        
        # Add instruction.md
        instruction_content = task_data.get("problem_statement", "No instruction provided.")
        info = tarfile.TarInfo(name="instruction.md")
        info.size = len(instruction_content.encode("utf-8"))
        tar.addfile(info, io.BytesIO(instruction_content.encode("utf-8")))
        
        # Add other files in the directory
        for f in task_dir.iterdir():
            if f.name == "task.json": continue # Skip the source json
            tar.add(f, arcname=f.name)
            
    return buf.getvalue()

def main():
    tasks_root = Path("tasks")
    output_path = Path("data/train.parquet")
    output_path.parent.mkdir(exist_ok=True)
    
    # Read validation results to only include passed tasks
    val_summary_path = tasks_root / "validation_summary.json"
    if not val_summary_path.exists():
        print("Error: validation_summary.json not found. Run validation first.")
        return
    
    val_data = json.loads(val_summary_path.read_text())
    passed_ids = val_data.get("ok", [])
    
    if not passed_ids:
        print("No passed tasks found in validation_summary.json.")
        return

    dataset_rows = []
    
    for task_dir in sorted(tasks_root.glob("task_*")):
        task_json_path = task_dir / "task.json"
        if not task_json_path.exists(): continue
        
        task_data = json.loads(task_json_path.read_text())
        instance_id = task_data["instance_id"]
        
        if instance_id not in passed_ids:
            continue
            
        print(f"Processing {instance_id}...")
        tar_bytes = create_task_tar(task_dir)
        if tar_bytes:
            dataset_rows.append({
                "path": instance_id,
                "task_binary": tar_bytes
            })

    if dataset_rows:
        df = pd.DataFrame(dataset_rows)
        df.to_parquet(output_path)
        print(f"Saved {len(dataset_rows)} tasks to {output_path}")
    else:
        print("No tasks were processed.")

if __name__ == "__main__":
    main()
