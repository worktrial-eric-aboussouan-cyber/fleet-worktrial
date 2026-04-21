#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path
import pandas as pd
from datasets import load_dataset
from collections import Counter

def main():
    parser = argparse.ArgumentParser(description="Prepare OOD eval dataset from SWE-bench Verified")
    parser.add_argument("--dry-run", action="store_true", help="Print selected instances without processing")
    parser.add_argument("--limit", type=int, default=30, help="Total instances to take")
    args = parser.parse_args()

    # 1. Load SWE-bench Verified
    print("Loading SWE-bench Verified...")
    ds = load_dataset("princeton-nlp/SWE-bench_Verified", split="test")
    
    # 2. Filter out training repos
    training_repos = ["psf/requests", "pallets/click", "pallets/flask", "encode/httpx"]
    # Adjust for potential mismatches in repo naming (e.g., 'requests' vs 'psf/requests')
    filtered_ds = [
        ins for ins in ds 
        if ins["repo"] not in training_repos and ins["repo"].split("/")[-1] not in [r.split("/")[-1] for r in training_repos]
    ]
    
    print(f"Total instances after filtering training repos: {len(filtered_ds)}")

    # 3. Balance across remaining repos
    repo_counts = Counter([ins["repo"] for ins in filtered_ds])
    sorted_repos = sorted(repo_counts.items(), key=lambda x: x[1], reverse=True)
    
    # Group by repo
    by_repo = {}
    for ins in filtered_ds:
        repo = ins["repo"]
        if repo not in by_repo:
            by_repo[repo] = []
        by_repo[repo].append(ins)
    
    selected_instances = []
    # Round-robin selection
    repos_list = [r[0] for r in sorted_repos]
    idx = 0
    while len(selected_instances) < args.limit and any(by_repo.values()):
        repo = repos_list[idx % len(repos_list)]
        if by_repo[repo]:
            selected_instances.append(by_repo[repo].pop(0))
        idx += 1

    if args.dry_run:
        print(f"\nDry-run: Selected {len(selected_instances)} instances")
        print(f"{'Instance ID':<40} | {'Repo':<20}")
        print("-" * 65)
        for ins in selected_instances:
            print(f"{ins['instance_id']:<40} | {ins['repo']:<20}")
        
        # Summary of repo distribution
        final_counts = Counter([ins["repo"] for ins in selected_instances])
        print("\nRepo Distribution:")
        for repo, count in final_counts.items():
            print(f"  {repo}: {count}")
        return

    # 4. (For later) Build images and save task.json
    # This part will be implemented once the dry-run is approved.
    print("Dry-run only. Re-run with --dry-run to see selection.")

if __name__ == "__main__":
    main()
