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
    pattern = r'ASSISTANT:\s*'
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
            formatted_json = json.dumps(new_data, indent=2)
        else:
            if "assignments" in data:
                new_data = {"assignments": data["assignments"]}
            else:
                data.pop("analysis", None)
                data.pop("oracle", None)
                new_data = {"assignments": data}
            formatted_json = json.dumps(new_data, indent=2)
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
    explain_instr = (
        "- Include 'analysis', 'oracle', and 'assignments' keys."
        if is_explain
        else "- Output ONLY the 'assignments' key."
    )
    parts = []
    # Static fragments
    header = _read_fragment("header.txt")
    header = header.replace("{{EXPLAIN_INSTRUCTION}}", explain_instr)
    parts.append(header)
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
            parts.append(_clean_json_samples(phase_samples, is_explain))
    # Mode samples (always loaded)
    mode_samples = _read_fragment(f"samples_{mode}.txt")
    if mode_samples:
        parts.append(_clean_json_samples(mode_samples, is_explain))
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

def log_llm_call(world_snapshot, sys_prompt, raw_response, parse_code, latency_ms, tokens_limit, is_explain):
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
    try: return json.loads(json_str), 1
    except json.JSONDecodeError:
        assignments_match = re.search(r'"assignments"\s*:\s*(\{.*?\})\s*\}', json_str, re.DOTALL)
        if assignments_match:
            fallback = '{"analysis": "⚡ Fallback aktiv.", "assignments": ' + assignments_match.group(1) + '}'
            try: return json.loads(fallback), 2
            except: pass
    return None, 3

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
            ents_hash = hash(json.dumps({"ents": ents, "status": status}, sort_keys=True))
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
            
            min_ents = {k: {"x": round(v["x"], 1), "y": round(v["y"], 1)} for k, v in ents.items()}
            
            # B3 experiment: optionally include match_state in the LLM payload
            if os.getenv("R2K_INCLUDE_MATCH_STATE", "0") == "1":
                if match_state:
                    min_ents["match_state"] = {
                        "status": match_state.get("status", "playing"),
                        "restart_team": match_state.get("restart_team", ""),
                    }
            
            is_explain = os.getenv("R2K_EXPLAIN", "0") == "1"
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
            
            payload["stream"] = False
            
            start_t = time.time()
            # FIX 2: Absolut sicherer Timeout für alte CPUs
            resp = requests.post(OLLAMA_URL, json=payload, timeout=150.0)
            lat = int((time.time() - start_t) * 1000)

            if resp.status_code == 200:
                raw_response = resp.json().get("response", "")
                data, err = fast_parse(raw_response)
                
                if data:
                    data["latency_ms"] = lat
                    data["model_name"] = MODEL_NAME
                    with open(STRATEGY_PATH + ".tmp", 'w') as f: json.dump(data, f)
                    os.replace(STRATEGY_PATH + ".tmp", STRATEGY_PATH)
                    log_llm_call(min_ents, sys_prompt, raw_response, 0, lat, tokens_limit, is_explain)
                else:
                    err_preview = raw_response[:150] if raw_response else "EMPTY RESPONSE"
                    print(f"❌ [Parse Error] KI-Antwort zerstört! Rohdaten: {err_preview}", flush=True)
                    log_llm_call(min_ents, sys_prompt, raw_response, err, lat, tokens_limit, is_explain)
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
