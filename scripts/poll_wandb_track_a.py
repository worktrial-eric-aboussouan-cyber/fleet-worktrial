import wandb
import os
import time
import sys
import matplotlib.pyplot as plt
from datetime import datetime, timezone

os.environ['WANDB_API_KEY'] = os.environ.get('WANDB_API_KEY', '')
start_time_real = datetime.now(timezone.utc)
api = wandb.Api()

print("Waiting for new run (Track A)...")
run = None
while True:
    runs = api.runs('thefleet/fleet-worktrial-eric', order='-created_at')
    if runs:
        latest = runs[0]
        created_at = datetime.strptime(latest.created_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        if created_at > start_time_real:
            run = latest
            break
    time.sleep(30)

print(f"Monitoring run: {run.url}")

start_time = time.time()
while True:
    elapsed = time.time() - start_time
    if elapsed > 15 * 60: # 15 minutes
        print("15 minutes passed. Exiting.")
        break
        
    run.update()
    hist = list(run.scan_history(keys=['_step', 'reward/avg_raw_reward', 'policy/final_loss'], page_size=100))
    
    steps = [r.get('_step', 0) for r in hist]
    rewards = [r.get('reward/avg_raw_reward', 0) for r in hist]
    
    print(f"[{elapsed:.1f}s] Steps: {len(steps)}, Rewards: {rewards}")
    
    if any(r > 0 for r in rewards) or len(steps) >= 5:
        if any(r > 0 for r in rewards):
            print("FOUND REWARD > 0!")
        else:
            print("REACHED 5 STEPS")
        break
        
    time.sleep(60)

hist = list(run.scan_history(keys=['_step', 'reward/avg_raw_reward', 'policy/final_loss'], page_size=100))
steps = [r.get('_step', 0) for r in hist]
rewards = [r.get('reward/avg_raw_reward', 0) for r in hist]
losses = [r.get('policy/final_loss', 0) for r in hist]

plt.figure(figsize=(10, 5))
plt.subplot(1, 2, 1)
plt.plot(steps, rewards, marker='o', color='blue')
plt.title('Reward over Steps')
plt.xlabel('Step')
plt.ylabel('Avg Raw Reward')

plt.subplot(1, 2, 2)
plt.plot(steps, losses, marker='o', color='red')
plt.title('Loss over Steps')
plt.xlabel('Step')
plt.ylabel('Final Loss')

plt.tight_layout()
os.makedirs('results', exist_ok=True)
plt.savefig('results/training_curve.png')
print("Plot saved to results/training_curve.png")
