import json
import math
import time
import requests
import os
import re
import traceback
import hashlib
from datetime import datetime

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
WORLD_STATE_PATH = os.path.join(BASE_DIR, "shared_state", "Worldstate.json")
STRATEGY_PATH = os.path.join(BASE_DIR, "shared_state", "current_strategy.json")
PROMPT_PATH = os.path.join(BASE_DIR, "ai_tactics", "system_prompt.txt")
FRAGMENTS_DIR = os.path.join(BASE_DIR, "strategy", "fragments")
SCENARIO_PATH = os.path.join(BASE_DIR, "ai_tactics", "active_scenario.json")

# FIX 1: Harte Bindung an natives lokales IPv4
OLLAMA_URL = os.getenv("R2K_OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
MODEL_NAME = os.getenv("R2K_OLLAMA_MODEL", "qwen2.5-coder:3b")

# --- Phase 1 instrumentation: LLM trace logger ---
RUN_ID = os.getenv("R2K_RUN_ID", f"run_{int(time.time())}")
LOG_DIR = os.path.join(BASE_DIR, "logs")
LLM_TRACE_PATH = os.path.join(LOG_DIR, f"llm_trace_{RUN_ID}.jsonl")
os.makedirs(LOG_DIR, exist_ok=True)

# --- Phase 2.5b: Dynamic prompt injection ---
# Ollama is stateless — it receives the `system` field in every /api/generate call
# and doesn't cache it. We can change sys_prompt between calls without restarting.
# This assembles the prompt from fragments based on (match_state.status, mode),
# caching by tuple to avoid re-reading files every 20ms poll.
_prompt_cache = {}  # (status, mode) -> assembled prompt string
_active_mode = None  # determined once at startup from active_scenario.json

# --- Phase I (C3 inter-lingua): text transform mode ---
# R2K_TEXT_MODE=1 replaces the JSON min_ents world encoding with a condensed
# text transform in dictionary vocabulary, and expects text-line output
# ("blue_1 move to (2.2, 0.3)") instead of JSON. Env-gated so K2 can A/B
# both encodings without code changes. Default 0 = current JSON behavior.
TEXT_MODE = os.getenv("R2K_TEXT_MODE", "0") == "1"

TEXT_OUTPUT_HEADER = (
    "Output exactly one line per blue bot in the INPUT above (blue_1, blue_2, "
    "blue_3, ...). Never use the same bot twice. Format: 'blue_1 move to (X, Y)', "
    "'blue_1 kick', 'blue_1 cover the goal line at (-4.0, Y)', or "
    "'blue_1 hold position'. Use the positions from the INPUT. "
    "Do NOT copy example coordinates."
)
TEXT_EXPLAIN_INSTRUCTION = (
    "Start with 'ANALYSIS: <assessment>', then 'ORACLE: <prediction>', "
    "then one line per blue bot."
)

def _build_text_world(ents, match_state, velocities=None):
    """Condensed text transform of the world snapshot in dictionary vocabulary.
    Ball first, then blue bots, then red bots; score and status appended.
    ~250 tok cap (~40 tokens for a 7-line 3vs3 world)."""
    lines = []
    if "soccer_ball" in ents:
        b = ents["soccer_ball"]
        lines.append(f"soccer_ball at ({b['x']:.1f}, {b['y']:.1f})")
    for name in sorted(k for k in ents if k.startswith("blue")):
        v = ents[name]
        base = f"{name} at ({v['x']:.1f}, {v['y']:.1f})"
        if velocities and name in velocities:
            vx, vy = velocities[name]
            if math.hypot(vx, vy) >= 0.3:
                base += f" moving ({vx:.1f}, {vy:.1f})"
        lines.append(base)
    for name in sorted(k for k in ents if k.startswith("red")):
        v = ents[name]
        base = f"{name} at ({v['x']:.1f}, {v['y']:.1f})"
        if velocities and name in velocities:
            vx, vy = velocities[name]
            if math.hypot(vx, vy) >= 0.3:
                base += f" moving ({vx:.1f}, {vy:.1f})"
        lines.append(base)
    ms = match_state or {}
    lines.append(f"score blue {ms.get('blue', 0)} : {ms.get('red', 0)} red")
    lines.append(f"status {ms.get('status', 'playing')}")
    return "\n".join(lines)

def _world_text_from_dict(data):
    """Render a sample INPUT JSON dict as text world lines (text-mode samples)."""
    lines = []
    if "soccer_ball" in data:
        b = data["soccer_ball"]
        lines.append(f"soccer_ball at ({b['x']:.1f}, {b['y']:.1f})")
    for name in sorted(data):
        if name == "soccer_ball" or not isinstance(data[name], dict):
            continue
        v = data[name]
        if "x" not in v or "y" not in v:
            continue
        lines.append(f"{name} at ({v['x']:.1f}, {v['y']:.1f})")
    return "\n".join(lines)

def _text_from_assignments(assignments, explain_active, analysis_val, oracle_val):
    """Render sample ASSISTANT assignments as text output lines."""
    out = []
    if explain_active:
        out.append(f"ANALYSIS: {analysis_val}")
        out.append(f"ORACLE: {oracle_val}")
    for bot in sorted(assignments):
        a = assignments[bot]
        action = a.get("action", "Move")
        if str(action).lower() == "kick":
            out.append(f"{bot} kick")
        elif a.get("role", "") == "goalie":
            out.append(f"{bot} cover the goal line at ({a['x']}, {a['y']})")
        else:
            out.append(f"{bot} move to ({a['x']}, {a['y']})")
    return "\n".join(out)

def _extract_json_block(content, start_pos):
    """Brace-match a JSON object starting at start_pos. Returns (json_str, end_idx)."""
    brace_count = 0
    json_start = -1
    for idx in range(start_pos, len(content)):
        char = content[idx]
        if char == '{':
            if brace_count == 0:
                json_start = idx
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0:
                return content[json_start:idx + 1], idx + 1
    return None, -1

def _clean_text_samples(content, explain_active):
    """Convert sample JSON blocks to text format (Phase I text mode).
    INPUT JSON -> world lines; ASSISTANT JSON -> bot lines
    (ANALYSIS:/ORACLE: prefixes in explain mode)."""
    output = ""
    last_idx = 0
    for m in re.finditer(r'INPUT:\s*', content):
        output += content[last_idx:m.start()]
        input_json, after_input = _extract_json_block(content, m.end())
        if input_json is None:
            output += content[last_idx:]
            return output
        a_match = re.search(r'(?:ASSISTANT|OUTPUT):\s*', content[after_input:])
        if not a_match:
            output += content[last_idx:]
            return output
        assistant_pos = after_input + a_match.end()
        output += content[after_input:after_input + a_match.start()] + "INPUT:\n"
        try:
            in_data = json.loads(input_json)
            world_text = _world_text_from_dict(in_data)
        except Exception:
            world_text = ""
        output += world_text + "\n"
        assist_json, after_assist = _extract_json_block(content, assistant_pos)
        if assist_json is None:
            output += content[last_idx:]
            return output
        try:
            data = json.loads(assist_json)
        except Exception:
            try:
                data = json.loads(re.sub(r'\n\s*', ' ', assist_json))
            except Exception:
                data = {}
        analysis_val = data.get("analysis", "Tactical assessment of entity positions and ball trajectory.")
        oracle_val = data.get("oracle", "Predictive optimization of team response to secure match advantage.")
        assignments = data.get("assignments", data)
        assignments.pop("analysis", None)
        assignments.pop("oracle", None)
        output += "ASSISTANT:\n" + _text_from_assignments(assignments, explain_active, analysis_val, oracle_val) + "\n"
        last_idx = after_assist
    output += content[last_idx:]
    return output

def _determine_mode():
    """Read mode from active_scenario.json (written by setup_r2k.py at boot).
    Falls back to '3vs3' if unavailable."""
    try:
        with open(SCENARIO_PATH, 'r') as f:
            data = json.load(f)
        scenario_name = data.get("scenario", data.get("scenario_name", ""))
        mode = data.get("mode") or (scenario_name.split('_')[0] if '_' in scenario_name else "3vs3")
        return mode
    except Exception:
        return "3vs3"

def _read_fragment(name):
    """Read a fragment file, return empty string if missing."""
    path = os.path.join(FRAGMENTS_DIR, name)
    try:
        with open(path, 'r') as f:
            return f.read()
        # Strip trailing newline to avoid double-newlines when concatenating
    except FileNotFoundError:
        return ""


def _clean_json_samples(content, explain_active):
    """Transform sample ASSISTANT blocks: inject or strip analysis/oracle keys.
    Duplicated from setup_r2k.py — needed at runtime because the evaluator
    assembles prompts from fragments directly (Phase 2.5b), bypassing
    setup_r2k.py's boot-time transformation. Without this, --explain mode
    has no string examples for analysis/oracle, and Qwen 3B fills oracle
    with JSON strategy data instead of text.
    """
    pattern = r'(?:ASSISTANT|OUTPUT):\s*'
    matches = list(re.finditer(pattern, content))
    if not matches:
        return content
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
                if brace_count == 0:
                    json_start = idx
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
        before_text = content[max(0, start_pos - 300):start_pos]
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
            except Exception:
                data = {}

        if explain_active:
            new_data = {}
            new_data["analysis"] = data.get("analysis", analysis_val)
            new_data["oracle"] = data.get("oracle", oracle_val)
            if "assignments" in data:
                new_data["assignments"] = data["assignments"]
            else:
                data.pop("analysis", None)
                data.pop("oracle", None)
                new_data["assignments"] = data
            formatted_json = json.dumps(new_data, separators=(',', ': '))
        else:
            if "assignments" in data:
                new_data = {"assignments": data["assignments"]}
            else:
                data.pop("analysis", None)
                data.pop("oracle", None)
                new_data = {"assignments": data}
            formatted_json = json.dumps(new_data, separators=(',', ': '))
        output += "ASSISTANT: " + formatted_json
        last_idx = json_end
    output += content[last_idx:]
    return output

def _assemble_prompt(status, mode):
    """Assemble system prompt from fragments based on (status, mode).
    Fragment load order (matches setup_r2k.py / dump_prompt.py):
      1. header.txt (static, contains {{EXPLAIN_INSTRUCTION}} placeholder)
      2. rules_core.txt (static)
      3. rules_<status>.txt (game-phase; falls back to rules_<mode>.txt)
      4. rules_<mode>.txt (mode rules — always loaded; rules_<status> is ADDITIVE)
      5. samples_<status>.txt (game-phase; falls back to samples_<mode>.txt)
      6. samples_<mode>.txt (mode samples — always loaded; samples_<status> is ADDITIVE)

    Note: game-phase fragments are ADDITIVE to mode fragments, not replacements.
    The mode fragments (rules_3vs3.txt, samples_3vs3.txt) define the base behavior;
    game-phase fragments add status-specific instructions on top.
    Fallback: if rules_<status>.txt doesn't exist → skip it (mode rules suffice).
    """
    is_explain = os.getenv("R2K_EXPLAIN", "0") == "1"
    if TEXT_MODE:
        explain_instr = TEXT_EXPLAIN_INSTRUCTION if is_explain else TEXT_OUTPUT_HEADER
        output_format = "OUTPUT FORMAT: " + (TEXT_EXPLAIN_INSTRUCTION if is_explain else TEXT_OUTPUT_HEADER)
    else:
        explain_instr = (
            "- Include 'analysis', 'oracle', and 'assignments' keys."
            if is_explain
            else "- Output ONLY the 'assignments' key."
        )
        output_format = "Output ONLY pure, raw JSON."
    parts = []
    # Static fragments
    header = _read_fragment("header.txt")
    header = header.replace("Output ONLY pure, raw JSON.", output_format)
    header = header.replace("{{EXPLAIN_INSTRUCTION}}", explain_instr)
    parts.append(header)
    if TEXT_MODE:
        parts.append(_read_fragment("rules_core_text.txt") or _read_fragment("rules_core.txt"))
    else:
        parts.append(_read_fragment("rules_core.txt"))
    # Game-phase rules (additive — falls back to nothing if missing)
    if status != "playing":
        phase_rules = _read_fragment(f"rules_{status}.txt")
        if phase_rules:
            parts.append(phase_rules)
    # Mode rules (always loaded)
    parts.append(_read_fragment(f"rules_{mode}.txt"))
    # Game-phase samples (additive — falls back to nothing if missing)
    if status != "playing":
        phase_samples = _read_fragment(f"samples_{status}.txt")
        if phase_samples:
            parts.append(_clean_text_samples(phase_samples, is_explain) if TEXT_MODE else _clean_json_samples(phase_samples, is_explain))
    # Mode samples (always loaded)
    mode_samples = _read_fragment(f"samples_{mode}.txt")
    if mode_samples:
        parts.append(_clean_text_samples(mode_samples, is_explain) if TEXT_MODE else _clean_json_samples(mode_samples, is_explain))
    # Join with double-newlines between fragments, strip trailing whitespace
    return "\n\n".join(p for p in parts if p.strip()).strip()

def _get_sys_prompt(status):
    """Return the assembled system prompt for the current (status, mode).
    Caches by (status, mode) tuple — re-reads fragment files only on status change."""
    global _active_mode
    if _active_mode is None:
        _active_mode = _determine_mode()
    key = (status, _active_mode)
    if key not in _prompt_cache:
        _prompt_cache[key] = _assemble_prompt(status, _active_mode)
    return _prompt_cache[key]

def log_llm_call(world_snapshot, sys_prompt, raw_response, parse_code, latency_ms, tokens_limit, is_explain, timings=None):
    try:
        prompt_hash = hashlib.sha1(sys_prompt.encode()).hexdigest()[:16]
        record = {
            "t": time.time(),
            "world_snapshot": world_snapshot,
            "sys_prompt_hash": prompt_hash,
            "raw_response": raw_response[:2000] if raw_response else "",
            "parse_code": parse_code,
            "latency_ms": latency_ms,
            "model": MODEL_NAME,
            "num_predict": tokens_limit,
            "explain": is_explain,
        }
        # Ollama cache/timing metrics (from /api/generate response, ns → ms).
        # prompt_eval_count drops on prefix-cache hits (system prompt reused);
        # prompt_eval_duration vs eval_duration splits prefill vs generation.
        if timings:
            record["prompt_eval_count"] = timings.get("prompt_eval_count")
            record["eval_count"] = timings.get("eval_count")
            record["prompt_eval_duration_ms"] = round(timings.get("prompt_eval_duration", 0) / 1e6, 1)
            record["eval_duration_ms"] = round(timings.get("eval_duration", 0) / 1e6, 1)
            record["load_duration_ms"] = round(timings.get("load_duration", 0) / 1e6, 1)
            record["total_duration_ms"] = round(timings.get("total_duration", 0) / 1e6, 1)
        with open(LLM_TRACE_PATH, 'a') as f:
            f.write(json.dumps(record) + "\n")
    except Exception:
        pass

def fast_parse(text):
    start = text.find('{')
    end = text.rfind('}')
    if start == -1 or end == -1: return None, 0
    json_str = text[start:end+1]
    
    try: return json.loads(json_str), 0
    except json.JSONDecodeError: pass 
        
    json_str = re.sub(r',\s*\}', '}', json_str)
    json_str = re.sub(r',\s*\]', ']', json_str)
    json_str = re.sub(r'"y:', '"y":', json_str)  # fix missing closing quote on y key (compact JSON artifact)
    try: return json.loads(json_str), 1
    except json.JSONDecodeError:
        assignments_match = re.search(r'"assignments"\s*:\s*(\{.*?\})\s*\}', json_str, re.DOTALL)
        if assignments_match:
            fallback = '{"analysis": "⚡ Fallback aktiv.", "assignments": ' + assignments_match.group(1) + '}'
            try: return json.loads(fallback), 2
            except: pass
    return None, 3

TEXT_LINE_RE = re.compile(
    r'^\s*blue_(\d+)\s+(?:move to \((-?[\d.]+),\s*(-?[\d.]+)\)|'
    r'cover the goal line at \((-?[\d.]+),\s*(-?[\d.]+)\)|(kick)|(hold position))\s*$'
)

def text_parse(text):
    """Parse condensed text output (Phase I text mode): one line per bot.
    Accepts: 'blue_1 move to (2.2, 0.3)', 'blue_1 cover the goal line at
    (-4.0, 1.5)', 'blue_1 kick', 'blue_1 hold position'. Ignores
    ANALYSIS:/ORACLE:/prose lines.
    Returns (assignments_dict, code); code 0 = all lines parsed,
    1 = partial (some lines unparseable), None if no bot line found
    (caller falls back to fast_parse)."""
    assignments = {}
    partial = False
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        m = TEXT_LINE_RE.match(line)
        if not m:
            if line.startswith("blue_"):
                partial = True
            continue
        bot = f"blue_{int(m.group(1))}"
        if m.group(6):  # kick
            assignments[bot] = {"role": "attacker", "action": "Kick"}
        elif m.group(7):  # hold position
            assignments[bot] = {"role": "defender", "action": "Hold"}
        elif m.group(4):  # cover the goal line at (x, y) -> role goalie
            assignments[bot] = {
                "role": "goalie",
                "action": "Move",
                "x": float(m.group(4)),
                "y": float(m.group(5)),
            }
        else:  # move to (x, y)
            assignments[bot] = {
                "role": "attacker",
                "action": "Move",
                "x": float(m.group(2)),
                "y": float(m.group(3)),
            }
    if not assignments:
        return None, 2
    return {"assignments": assignments}, 1 if partial else 0

def main():
    print(f"--- R2K Evaluator (Native Edition) ---", flush=True)
    print(f"Trace log: {LLM_TRACE_PATH}", flush=True)
    last_mtime = 0
    last_ents_hash = 0
    prev_ents = {}  # position history for velocity computation
    prev_ents_time = 0.0  # timestamp of last prev_ents update
    
    while True:
        try:
            if not os.path.exists(WORLD_STATE_PATH):
                time.sleep(0.1); continue
                
            mtime = os.path.getmtime(WORLD_STATE_PATH)
            if mtime == last_mtime:
                time.sleep(0.02); continue
                
            try:
                with open(WORLD_STATE_PATH, 'r') as f: world_data = json.load(f)
            except Exception:
                time.sleep(0.05); continue
            
            ents = world_data.get("entities", {})
            if not any("blue" in k for k in ents.keys()):
                last_mtime = mtime; continue

            match_state = world_data.get("match_state", {})
            status = match_state.get("status", "playing")

            # Skip LLM call if entity positions AND status haven't changed
            # (aggregator writes at 10Hz unconditionally — 64% of writes have
            # identical positions). temperature: 0.0 makes the LLM deterministic,
            # so identical input → identical output → wasted GPU time + repetitive
            # visualizer output. Including status in the hash prevents missing
            # status transitions (e.g. ball_out while bots hold still).
            # Phase I: hash the TRANSFORMED text (or JSON) — the exact payload.
            if TEXT_MODE:
                hash_src = _build_text_world(ents, match_state)
            else:
                hash_src = json.dumps({"ents": ents, "status": status}, sort_keys=True)
            ents_hash = hash(hash_src)
            if ents_hash == last_ents_hash:
                last_mtime = mtime; continue
            last_ents_hash = ents_hash

            # Future world model — project all entities to t + horizon.
            # Ball: exponential velocity decay (k=1.26, empirically measured).
            # Bots: linear motion capped at max speed (bridge PD controller).
            # Blue bot prediction is valid: at t+horizon they're still executing
            # the PREVIOUS command, not the one being generated now.
            PREDICT_HORIZON_S = 0.746  # hardwired; future: dynamic from measured latency
            BALL_DECAY_K = 1.26
            BOT_MAX_SPEED = 0.8

            velocities = {}
            now_t = time.time()
            dt = now_t - prev_ents_time if prev_ents_time > 0 else 0.1
            prev_ents_time = now_t
            if dt < 0.01:
                dt = 0.1
            for k, v in ents.items():
                if k in prev_ents:
                    pv = prev_ents[k]
                    velocities[k] = ((v["x"] - pv["x"]) / dt, (v["y"] - pv["y"]) / dt)

            prev_ents = {k: {"x": v["x"], "y": v["y"]} for k, v in ents.items()}

            for k, v in ents.items():
                if k not in velocities:
                    continue
                vx, vy = velocities[k]
                speed = math.hypot(vx, vy)
                if speed < 0.3:
                    continue
                if k == "soccer_ball":
                    dist = (speed / BALL_DECAY_K) * (1 - math.exp(-BALL_DECAY_K * PREDICT_HORIZON_S))
                else:
                    dist = min(speed * PREDICT_HORIZON_S, BOT_MAX_SPEED * PREDICT_HORIZON_S)
                v["x"] = v["x"] + (vx / speed) * dist
                v["y"] = v["y"] + (vy / speed) * dist

            # Phase 2.5b: Dynamic prompt injection — assemble prompt from fragments
            # based on match_state.status. Cached by (status, mode) tuple.
            sys_prompt = _get_sys_prompt(status)

            is_explain = os.getenv("R2K_EXPLAIN", "0") == "1"

            # Phase I: text transform (dictionary vocabulary) or JSON min_ents.
            if TEXT_MODE:
                world_text = _build_text_world(ents, match_state, velocities)
                blue_names = ", ".join(sorted(k for k in ents if k.startswith("blue")))
                user_prompt = (world_text + f"\n\nCommand: {blue_names}\n\n" +
                               (TEXT_EXPLAIN_INSTRUCTION if is_explain else TEXT_OUTPUT_HEADER))
                tokens_limit = 600 if is_explain else 200
            else:
                min_ents = {k: {"x": round(v["x"], 1), "y": round(v["y"], 1)} for k, v in ents.items()}
                
                # B3 experiment: optionally include match_state in the LLM payload
                if os.getenv("R2K_INCLUDE_MATCH_STATE", "0") == "1":
                    if match_state:
                        min_ents["match_state"] = {
                            "status": match_state.get("status", "playing"),
                            "restart_team": match_state.get("restart_team", ""),
                        }
                
                tokens_limit = 600 if is_explain else 150
                req_keys = "Include 'analysis', 'oracle', and 'assignments' keys." if is_explain else "Output ONLY the 'assignments' key."
                
                payload = {
                    "model": MODEL_NAME,
                    "prompt": json.dumps(min_ents) + f"\n\nCRITICAL: Output ONLY valid JSON. {req_keys} End immediately after closing bracket.",
                    "system": sys_prompt,
                    "stream": False,
                    "keep_alive": "1h", 
                    "options": {
                        "temperature": 0.0, 
                        "num_predict": tokens_limit,
                        "num_ctx": 4096,
                        "stop": ["<|im_end|>", "<|endoftext|>"] 
                    }
                }
            
            if TEXT_MODE:
                payload = {
                    "model": MODEL_NAME,
                    "prompt": user_prompt,
                    "system": sys_prompt,
                    "stream": False,
                    "keep_alive": "1h", 
                    "options": {
                        "temperature": 0.0, 
                        "num_predict": tokens_limit,
                        "num_ctx": 4096,
                        "stop": ["<|im_end|>", "<|endoftext|>"] 
                    }
                }
            
            payload["stream"] = False
            
            start_t = time.time()
            # FIX 2: Absolut sicherer Timeout für alte CPUs
            resp = requests.post(OLLAMA_URL, json=payload, timeout=150.0)
            lat = int((time.time() - start_t) * 1000)

            if resp.status_code == 200:
                resp_data = resp.json()
                timings = {
                    "prompt_eval_count": resp_data.get("prompt_eval_count"),
                    "eval_count": resp_data.get("eval_count"),
                    "prompt_eval_duration": resp_data.get("prompt_eval_duration", 0),
                    "eval_duration": resp_data.get("eval_duration", 0),
                    "load_duration": resp_data.get("load_duration", 0),
                    "total_duration": resp_data.get("total_duration", 0),
                }
                raw_response = resp_data.get("response", "")
                if TEXT_MODE:
                    # Phase I: text output — regex bot lines, JSON fallback
                    data, err = text_parse(raw_response)
                    if data is None:
                        data, json_err = fast_parse(raw_response)
                        if data is not None:
                            err = 10 + json_err  # JSON fallback after failed text parse
                else:
                    data, err = fast_parse(raw_response)
                
                if data:
                    if "assignments" not in data:
                        data = {"assignments": data}
                    data["latency_ms"] = lat
                    data["model_name"] = MODEL_NAME
                    with open(STRATEGY_PATH + ".tmp", 'w') as f: json.dump(data, f)
                    os.replace(STRATEGY_PATH + ".tmp", STRATEGY_PATH)
                    log_llm_call(world_text if TEXT_MODE else min_ents, sys_prompt, raw_response, 0, lat, tokens_limit, is_explain, timings)
                else:
                    err_preview = raw_response[:150] if raw_response else "EMPTY RESPONSE"
                    print(f"❌ [Parse Error] KI-Antwort zerstört! Rohdaten: {err_preview}", flush=True)
                    log_llm_call(world_text if TEXT_MODE else min_ents, sys_prompt, raw_response, err, lat, tokens_limit, is_explain, timings)
            else:
                print(f"❌ [HTTP Error] Ollama meldet Code: {resp.status_code}", flush=True)
            
            last_mtime = mtime

        # FIX 3: Sauberes Error-Handling ohne Absturz
        except requests.exceptions.ConnectTimeout:
            print("🚨 [Timeout] Kann 127.0.0.1 nicht erreichen (Verbindungsaufbau)!", flush=True)
            time.sleep(1)
        except requests.exceptions.ReadTimeout:
            print("🚨 [Timeout] Ollama rechnet zu lange (> 150s)!", flush=True)
            last_mtime = mtime
        except requests.exceptions.ConnectionError:
            print("🚨 [Connection Refused] Ollama läuft nicht auf 127.0.0.1!", flush=True)
            time.sleep(1)
        except Exception as e:
            print(f"💥 [CRITICAL ERROR] {e}", flush=True)
            traceback.print_exc()
            time.sleep(1)

if __name__ == "__main__":
    main()
