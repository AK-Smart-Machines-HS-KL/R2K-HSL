#!/usr/bin/env python3
import argparse
import shutil
import os
import json
import re
import requests

def clean_json_samples(content, explain_active):
    pattern = r'ASSISTANT:\s*'
    matches = list(re.finditer(pattern, content))
    if not matches: return content
    output = ""
    last_idx = 0
    for m in matches:
        start_pos = m.start()
        end_pos = m.end()
        output += content[last_idx:start_pos]
        brace_count = 0
        json_start = -1
        json_end = -1
        for idx in range(end_pos, len(content)):
            char = content[idx]
            if char == '{':
                if brace_count == 0: json_start = idx
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    json_end = idx + 1
                    break
        if json_start == -1 or json_end == -1:
            output += content[start_pos:end_pos]
            last_idx = end_pos
            continue
        raw_json = content[json_start:json_end]
        before_text = content[max(0, start_pos-300):start_pos]
        analysis_val = "Tactical assessment of entity positions and ball trajectory."
        oracle_val = "Predictive optimization of team response to secure match advantage."
        if "DEFENSIVE PASS" in before_text or "CLEARANCE" in before_text:
            analysis_val = "blue_1 clears the ball from the defensive zone towards blue_2."
            oracle_val = "Passing the ball out of danger into the midfield."
        elif "ANTI-CLUSTERING" in before_text:
            analysis_val = "blue_1 attacks the ball while blue_2 drops back to support and avoid clustering."
            oracle_val = "Maintain optimal distance between teammates to control the field."
        elif "BOUNDARY STAGING" in before_text:
            analysis_val = "blue_1 moves to intercept the ball near the boundary while blue_2 guards the goal."
            oracle_val = "Secure the defensive line to prevent any immediate shots on goal."
        try:
            data = json.loads(raw_json)
        except Exception:
            try:
                sanitized = re.sub(r'\n\s*', ' ', raw_json)
                data = json.loads(sanitized)
            except Exception: data = {}
                
        if explain_active:
            new_data = {}
            new_data["analysis"] = data.get("analysis", analysis_val)
            new_data["oracle"] = data.get("oracle", oracle_val)
            if "assignments" in data: new_data["assignments"] = data["assignments"]
            else:
                data.pop("analysis", None)
                data.pop("oracle", None)
                new_data["assignments"] = data
            formatted_json = json.dumps(new_data, separators=(',', ': '))
        else:
            if "assignments" in data: new_data = {"assignments": data["assignments"]}
            else:
                data.pop("analysis", None)
                data.pop("oracle", None)
                new_data = {"assignments": data}
            formatted_json = json.dumps(new_data, separators=(',', ': '))
        output += "ASSISTANT: " + formatted_json
        last_idx = json_end
    output += content[last_idx:]
    return output

def default_hexagonal_waypoints():
    """Default calibration path: hexagonal loop."""
    return [
        {"label": "FIRST",  "x": -1.0, "y": 1.5, "hold_duration": 0},
        {"label": "SECOND", "x":  1.0, "y": 1.5, "hold_duration": 0},
        {"label": "THIRD",  "x":  3.0, "y": 0.0, "hold_duration": 0},
        {"label": "FOURTH", "x":  1.0, "y": -1.5, "hold_duration": 0},
        {"label": "FIFTH",  "x": -1.0, "y": -1.5, "hold_duration": 0},
        {"label": "SIXTH",  "x": -3.0, "y": 0.0, "hold_duration": 0},
    ]

def compile_task_to_waypoints(task, executor_model):
    """One-shot LLM call: translate NL task to named waypoint list.

    Uses a larger model (qwen2.5:7b) for compilation — the executor model
    (3b) is too small for reliable NL→waypoint generation.
    """
    compiler_model = "qwen2.5:7b"
    if "7b" in executor_model or "14b" in executor_model:
        compiler_model = executor_model

    sys_prompt = """You are a robot path planner. Convert the task into a list of named waypoints.

Output ONLY raw JSON:
{"waypoints": [{"label": "FIRST", "x": <float>, "y": <float>}, {"label": "SECOND", ...}, ...]}

Rules:
- Label waypoints sequentially: FIRST, SECOND, THIRD, FOURTH, FIFTH, SIXTH, ...
- Use absolute coordinates.
- Insert a "START" waypoint at the bot's current position if needed.
- No timing, no Hold — just the waypoint list.

Example:
Task: "move to (2, 0), then move to (2, 3)"
Output: {"waypoints": [{"label": "FIRST", "x": 2.0, "y": 0.0}, {"label": "SECOND", "x": 2.0, "y": 3.0}]}
"""

    payload = {
        "model": compiler_model,
        "prompt": f"Task: {task}\n\nOutput the JSON.",
        "system": sys_prompt,
        "stream": False,
        "keep_alive": "30m",
        "options": {"temperature": 0.0, "num_predict": 400, "num_ctx": 4096, "stop": ["<|im_end|>"]},
    }
    try:
        print(f"Compiling task with {compiler_model}: \"{task[:60]}...\"")
        resp = requests.post("http://127.0.0.1:11434/api/generate", json=payload, timeout=120)
        raw = resp.json().get("response", "").strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1].strip("json\n")
        data = json.loads(raw)
        wps = data.get("waypoints", data)
        if isinstance(wps, list) and len(wps) > 0:
            return [{"label": w["label"], "x": float(w["x"]), "y": float(w["y"]),
                     "hold_duration": float(w.get("hold_duration", 0))} for w in wps]
    except Exception as e:
        print(f"⚠️ Compiler failed ({e}), using default hexagonal path")
    return default_hexagonal_waypoints()

def main():
    parser = argparse.ArgumentParser(description="ROS2K Setup")
    parser.add_argument('--scenario', type=str, default='2vs2_default')
    parser.add_argument('--strategy', type=str, default='strat_aggro')
    parser.add_argument('--model', type=str, default='qwen2.5-coder:3b')
    parser.add_argument('--relay', type=str, default='only_sim_bots')
    parser.add_argument('--explain', action='store_true', dest='explain', default=True)
    parser.add_argument('--no-explain', action='store_false', dest='explain')
    parser.add_argument('--demo', action='store_true', help='Demo/calibration mode — overrides mode to "demo"')
    args = parser.parse_args()
    
    os.makedirs('ai_tactics', exist_ok=True)
    os.makedirs('strategy', exist_ok=True)
    os.makedirs('relay', exist_ok=True)

    # --- Relay Profil kopieren ---
    # Transient files (active_relay.json etc.) may be root-owned when the GUI
    # supervisor wrote them from inside the Docker container. The directory is
    # user-owned, so deleting and rewriting is always possible — chown is not.
    TRANSIENT_FILES = ('ai_tactics/active_relay.json', 'ai_tactics/active_scenario.json',
                       'ai_tactics/system_prompt.txt')

    def writable_or_unlink(path):
        if os.path.exists(path) and not os.access(path, os.W_OK):
            try:
                os.unlink(path)
            except OSError as e:
                print(f"❌ {path} is not writable and could not be removed ({e}).")
                print(f"   Fix manually:  sudo chown $(id -u):$(id -g) {path}")
                exit(1)

    for tf in TRANSIENT_FILES:
        writable_or_unlink(tf)

    relay_file = f"relay/{args.relay}.json"
    if os.path.exists(relay_file):
        shutil.copy(relay_file, 'ai_tactics/active_relay.json')
    else:
        print(f"⚠️ Warnung: Relay-Profil '{relay_file}' nicht gefunden. Erstelle Fallback ohne Hardware.")
        fallback = {"relay_id": "fallback", "requires_hardware_sync": False, "mapping": {}}
        with open('ai_tactics/active_relay.json', 'w') as f: json.dump(fallback, f)

    # Support both package (scenario/<name>/scenario.json) and flat (scenario/<name>.json) formats
    pkg_scene = f"scenario/{args.scenario}/scenario.json"
    flat_scene = f"scenarios/{args.scenario}.json" if os.path.exists(f"scenarios/{args.scenario}.json") else f"scenario/{args.scenario}.json"
    scene_file = pkg_scene if os.path.exists(pkg_scene) else flat_scene
    if not os.path.exists(scene_file): 
        print(f"❌ Szenario {scene_file} nicht gefunden!")
        exit(1)
        
    shutil.copy(scene_file, 'ai_tactics/active_scenario.json')
    with open(scene_file, 'r') as f:
        data = json.load(f)
        blue_bots = sorted([k for k in data.get('entities', {}).keys() if 'blue' in k])

    mode = data.get('mode') or (args.scenario.split('_')[0] if '_' in args.scenario else "3vs3")
    if args.demo:
        mode = "demo"
        data['mode'] = "demo"
        with open('ai_tactics/active_scenario.json', 'w') as f:
            json.dump(data, f, indent=2)

        # Compile waypoints: if scenario has a "task" field, use the 7B compiler;
        # otherwise use the default hexagonal path (no LLM call needed).
        os.makedirs('shared_state', exist_ok=True)
        task = data.get('task', '')
        if task:
            waypoints = compile_task_to_waypoints(task, args.model)
        else:
            waypoints = default_hexagonal_waypoints()
        with open('shared_state/waypoints.json', 'w') as f:
            json.dump({"waypoints": waypoints}, f, indent=2)
        wp_labels = [w["label"] for w in waypoints]
        print(f"Demo mode: {len(waypoints)} waypoints: {wp_labels}")
    clean_strat = args.strategy.replace('strat_', '')
    frag_path = "strategy/fragments"
    prompt_lines = [f"ACT_ON_BOTS: {', '.join(blue_bots)}", f"MODE: {mode}\n"]
    core_file = "rules_demo_core.txt" if mode == "demo" else "rules_core.txt"
    files = ["header.txt", core_file]
    files.append(f"rules_{clean_strat}.txt" if os.path.exists(f"{frag_path}/rules_{clean_strat}.txt") else f"rules_{mode}.txt")
    if os.path.exists(f"{frag_path}/samples_{clean_strat}.txt"):
        files.append(f"samples_{clean_strat}.txt")
    else:
        files.append(f"samples_{mode}.txt")
    
    for comp in files:
        c_path = f"{frag_path}/{comp}"
        if os.path.exists(c_path):
            prompt_lines.append(f"### {comp.upper()} ###")
            with open(c_path, 'r') as f:
                content = f.read()
                if comp == "header.txt":
                    instr = "- Include 'analysis' and 'oracle' keys." if args.explain else "- Output ONLY the 'assignments' key."
                    content = content.replace("{{EXPLAIN_INSTRUCTION}}", instr)
                if "samples" in comp:
                    content = clean_json_samples(content, args.explain)
            prompt_lines.append(content + "\n")
            
    final_prompt = '\n'.join(prompt_lines).strip()
    with open('ai_tactics/system_prompt.txt', 'w') as f: f.write(final_prompt)
    print(f"✅ Setup: {args.scenario} | Relay: {args.relay} | Explain: {args.explain}")

if __name__ == "__main__": main()
