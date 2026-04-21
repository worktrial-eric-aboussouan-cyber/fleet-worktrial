import json
import glob
import os

for path in glob.glob("tasks/task_*/task.json"):
    with open(path, "r") as f:
        data = json.load(f)
    
    # Replace pytest command
    old_script = data["eval_script"]
    
    # remove set -e so bash doesn't exit early and we can do pipe to tee
    new_script = old_script.replace("set -e\n", "")
    new_script = new_script.replace(" -x ", " ")
    
    # modify the pytest line to use tee and tail
    lines = new_script.split('\n')
    for i, line in enumerate(lines):
        if line.startswith("pytest "):
            lines[i] = line + " -q | tee /tmp/result.txt; tail -1 /tmp/result.txt"
    
    new_script = '\n'.join(lines)
    data["eval_script"] = new_script
    
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        
    script_path = os.path.join(os.path.dirname(path), "eval_script.sh")
    with open(script_path, "w") as f:
        f.write(new_script)

print("Tasks patched.")
