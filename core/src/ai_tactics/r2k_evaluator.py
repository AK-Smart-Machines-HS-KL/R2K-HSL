import json
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

# FIX 1: Harte Bindung an natives lokales IPv4
OLLAMA_URL = os.getenv("R2K_OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
MODEL_NAME = os.getenv("R2K_OLLAMA_MODEL", "qwen2.5-coder:3b")

# --- Phase 1 instrumentation: LLM trace logger ---
RUN_ID = os.getenv("R2K_RUN_ID", f"run_{int(time.time())}")
LOG_DIR = os.path.join(BASE_DIR, "logs")
LLM_TRACE_PATH = os.path.join(LOG_DIR, f"llm_trace_{RUN_ID}.jsonl")
os.makedirs(LOG_DIR, exist_ok=True)

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
    print(f"--- 🟢 R2K Evaluator (Native Edition) ---", flush=True)
    print(f"📋 Trace log: {LLM_TRACE_PATH}", flush=True)
    last_mtime = 0
    
    while True:
        try:
            if not os.path.exists(WORLD_STATE_PATH):
                time.sleep(0.1); continue
                
            mtime = os.path.getmtime(WORLD_STATE_PATH)
            if mtime == last_mtime:
                time.sleep(0.02); continue
                
            try:
                with open(WORLD_STATE_PATH, 'r') as f: world_data = json.load(f)
                with open(PROMPT_PATH, 'r') as f: sys_prompt = f.read()
            except Exception:
                time.sleep(0.05); continue
            
            ents = world_data.get("entities", {})
            if not any("blue" in k for k in ents.keys()):
                last_mtime = mtime; continue
                
            min_ents = {k: {"x": round(v["x"], 1), "y": round(v["y"], 1)} for k, v in ents.items()}
            
            # B3 experiment: optionally include match_state in the LLM payload
            if os.getenv("R2K_INCLUDE_MATCH_STATE", "0") == "1":
                match_state = world_data.get("match_state", {})
                if match_state:
                    min_ents["match_state"] = {
                        "status": match_state.get("status", "playing"),
                        "restart_team": match_state.get("restart_team", ""),
                    }
            
            is_explain = "analysis" in sys_prompt.lower()
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
            
            if "nemotron" in MODEL_NAME.lower() or "llama" in MODEL_NAME.lower():
                payload["format"] = "json"
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
