#!/usr/bin/env python3
"""Minimal probe using the real evaluator's prompt assembly + Ollama call.
Uses r2k_evaluator._assemble_prompt(status, mode, n_blue) so the probe
exercises the EXACT prompt the production evaluator sends to the LLM.

Usage:
  python3 tools/probe_simple.py --corpus tests/synthetic_worldstates/corpus.jsonl --tag pre_fix
  python3 tools/probe_simple.py --corpus corpus.jsonl --tag post_fix --repeat 3
"""
import argparse
import json
import os
import sys
import time
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__)) + "/.."
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, BASE_DIR + "/ai_tactics")

import r2k_evaluator as ev  # noqa: E402

OLLAMA_URL = os.getenv("R2K_OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
MODEL = os.getenv("R2K_OLLAMA_MODEL", "qwen2.5:3b")
RESULTS_DIR = os.path.join(BASE_DIR, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)


def call_ollama(prompt, system, num_predict=150):
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "keep_alive": "1h",
        "options": {
            "temperature": 0.0,
            "num_predict": num_predict,
            "num_ctx": 4096,
            "stop": ["<|im_end|>", "<|endoftext|>"]
        },
    }
    t0 = time.time()
    body = json.dumps(payload).encode()
    req = urllib.request.Request(OLLAMA_URL, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
    lat_ms = int((time.time() - t0) * 1000)
    return data.get("response", ""), lat_ms


def run_one(label, status, ents, match_state, mode="3vs3", n_blue=3):
    """Probe a single scenario. Returns a record dict."""
    # Force the evaluator mode
    ev._active_mode = mode
    ev._active_n_blue = n_blue
    # Assemble system prompt exactly as the evaluator does
    sys_prompt = ev._assemble_prompt(status, mode, n_blue)

    # Build the user prompt exactly as the evaluator does (JSON path)
    min_ents = {k: {"x": round(v["x"], 1), "y": round(v["y"], 1)} for k, v in ents.items()}
    if match_state:
        min_ents["match_state"] = {
            "status": status,
            "restart_team": match_state.get("restart_team", ""),
        }
    is_explain = False
    req_keys = "Output ONLY the 'assignments' key."
    user_prompt = json.dumps(min_ents) + f"\n\nCRITICAL: Output ONLY valid JSON. {req_keys} End immediately after closing bracket."

    raw, lat_ms = call_ollama(user_prompt, sys_prompt, num_predict=150)
    data, err = ev.fast_parse(raw)
    if data and "assignments" not in data:
        data = {"assignments": data}

    # --- Metrics ---
    record = {
        "label": label,
        "status": status,
        "latency_ms": lat_ms,
        "parse_ok": bool(data),
        "parse_code": err if data is None else 0,
        "raw_preview": (raw[:200] if raw else ""),
    }
    if data:
        asn = data.get("assignments", {})
        # Goalie kick: any bot with role=goalie AND action=Kick
        goalie_kicks = sum(1 for b, a in asn.items() if str(a.get("role", "")).lower() == "goalie" and str(a.get("action", "")).lower() == "kick")
        # Goalie total: any bot with role=goalie
        goalie_total = sum(1 for b, a in asn.items() if str(a.get("role", "")).lower() == "goalie")
        # Pass: any bot with action=Kick AND target_x/target_y keys present
        pass_kicks = sum(1 for b, a in asn.items() if str(a.get("action", "")).lower() == "kick" and ("target_x" in a or "target" in a))
        kick_total = sum(1 for b, a in asn.items() if str(a.get("action", "")).lower() == "kick")
        record["goalie_kicks"] = goalie_kicks
        record["goalie_total"] = goalie_total
        record["pass_kicks"] = pass_kicks
        record["kick_total"] = kick_total
        record["assignments"] = asn
    return record


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--tag", default="probe")
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--mode", default="3vs3")
    ap.add_argument("--n-blue", type=int, default=3)
    args = ap.parse_args()

    with open(args.corpus) as f:
        corpus = [json.loads(l) for l in f if l.strip()]

    all_records = []
    for rep in range(args.repeat):
        for item in corpus:
            label = item["label"]
            status = item.get("status", "playing")
            ents = item["entities"]
            ms = item.get("match_state") or {"status": status}
            if "score_blue" in item:
                ms = {**ms, "blue": item["score_blue"], "red": item["score_red"]}
            rec = run_one(label, status, ents, ms, mode=args.mode, n_blue=args.n_blue)
            rec["repeat"] = rep
            all_records.append(rec)

    raw_path = os.path.join(RESULTS_DIR, f"probe_{args.tag}_raw.jsonl")
    with open(raw_path, "w") as f:
        for r in all_records:
            f.write(json.dumps(r) + "\n")

    # Report
    n = len(all_records)
    parse_ok = sum(1 for r in all_records if r["parse_ok"])
    goalie_recs = [r for r in all_records if r["parse_ok"] and r.get("goalie_total", 0) > 0]
    goalie_kicks_total = sum(r.get("goalie_kicks", 0) for r in goalie_recs)
    goalie_total_bots = sum(r.get("goalie_total", 0) for r in goalie_recs)
    kick_recs = [r for r in all_records if r["parse_ok"] and r.get("kick_total", 0) > 0]
    pass_total = sum(r.get("pass_kicks", 0) for r in all_records)
    kick_total = sum(r.get("kick_total", 0) for r in kick_recs)
    lats = [r["latency_ms"] for r in all_records]
    lats_sorted = sorted(lats)

    print(f"\n=== Probe report: {args.tag} ===")
    print(f"Corpus: {args.corpus}  |  N={n}  |  repeat={args.repeat}  |  model={MODEL}")
    print(f"Parse OK:        {parse_ok}/{n}  ({100*parse_ok/n:.1f}%)")
    print(f"Goalie Kick rate: {goalie_kicks_total}/{goalie_total_bots}  ({(100*goalie_kicks_total/goalie_total_bots if goalie_total_bots else 0):.1f}% of goalie-role bots)")
    print(f"Pass (Kick+tgt):  {pass_total}/{kick_total}  ({(100*pass_total/kick_total if kick_total else 0):.1f}% of Kick actions)")
    print(f"Latency p50:      {lats_sorted[n//2]}ms   p95: {lats_sorted[int(n*0.95)]}ms   max: {lats_sorted[-1]}ms")
    print(f"\nRaw: {raw_path}")

    # Status breakdown
    from collections import defaultdict
    by_status = defaultdict(lambda: {"n": 0, "gk": 0, "gt": 0, "pk": 0, "kt": 0})
    for r in all_records:
        s = r["status"]
        by_status[s]["n"] += 1
        if r["parse_ok"]:
            by_status[s]["gk"] += r.get("goalie_kicks", 0)
            by_status[s]["gt"] += r.get("goalie_total", 0)
            by_status[s]["pk"] += r.get("pass_kicks", 0)
            by_status[s]["kt"] += r.get("kick_total", 0)
    print("\nBy status:")
    print(f"  {'status':<18} {'N':>4} {'goalie_k/total':>16} {'pass/kicks':>12}")
    for s, d in sorted(by_status.items()):
        gk_pct = f"{d['gk']}/{d['gt']}" if d['gt'] else "-"
        pk_pct = f"{d['pk']}/{d['kt']}" if d['kt'] else "-"
        print(f"  {s:<18} {d['n']:>4} {gk_pct:>16} {pk_pct:>12}")


if __name__ == "__main__":
    main()
