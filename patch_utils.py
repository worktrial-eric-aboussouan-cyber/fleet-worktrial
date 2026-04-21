with open("harbor-train/skyrl-train/examples/mini_swe_agent/mini_swe_utils.py", "r") as f:
    content = f.read()

old_content = """        # use the return value
        ret["resolved"] = obs["returncode"] == 0
        # truncate to last 1000 characters for brevity
        ret["eval_error"] = (
            f"(truncated to last 1000 characters)\\n{obs["output"][-1000:]}" if not ret["resolved"] else None
        )"""

new_content = """        output = obs.get("output", "")
        score = float(obs["returncode"] == 0)
        if output:
            lines = [l for l in output.split('\\n') if l.strip()]
            if lines:
                last_line = lines[-1]
                import re
                passed_m = re.search(r"(\\d+) passed", last_line)
                failed_m = re.search(r"(\\d+) failed", last_line)
                error_m = re.search(r"(\\d+) error", last_line)
                
                passed = int(passed_m.group(1)) if passed_m else 0
                failed = int(failed_m.group(1)) if failed_m else 0
                errors = int(error_m.group(1)) if error_m else 0
                total = passed + failed + errors
                
                if total > 0:
                    score = passed / total
                    
        ret["resolved"] = score
        ret["eval_error"] = (
            f"(truncated to last 1000 characters)\\n{output[-1000:]}" if score < 1.0 else None
        )"""

content = content.replace(old_content, new_content)
with open("harbor-train/skyrl-train/examples/mini_swe_agent/mini_swe_utils.py", "w") as f:
    f.write(content)
