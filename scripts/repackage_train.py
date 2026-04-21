import pandas as pd
import os
from pathlib import Path
import tarfile
import shutil

def main():
    df = pd.read_parquet("data/train.parquet")
    out_dir = Path("data/harbor_repackaged/train")
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    
    for _, row in df.iterrows():
        task_id = row['path']
        task_binary = row['task_binary']
        
        task_dir = out_dir / task_id
        task_dir.mkdir()
        
        # Write the tarball
        tar_path = task_dir / "task.tar.gz"
        with open(tar_path, "wb") as f:
            f.write(task_binary)
        
        # Extract it so Harbor sees the directories
        with tarfile.open(tar_path, "r:gz") as tar:
            tar.extractall(path=task_dir)
        
        print(f"Repackaged {task_id}")

if __name__ == "__main__":
    main()
