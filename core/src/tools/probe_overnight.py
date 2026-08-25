#!/usr/bin/env python3
"""Overnight probe: sample-count sweep with precision/recall metrics.

Tests 9 sample configurations against 231 scenarios (5 reps each) to find
the inflection point where goalie-kick and pass behavior stabilizes.

Configurations:
  C0: Ex1-5 only (original baseline)
  C1: + Ex6 (1 goalie clearance sample)
  C2: + Ex7 (1 pass sample)
  C3: + Ex6 + Ex7 (both new samples)
  C4: + Ex6 + Ex7 + Ex8 (2nd goalie clearance, different position)
  C5: + Ex6 + Ex7 + Ex9 (pass to blue_2 instead of blue_3)
  C6: + Ex6 + Ex7 + Ex8 + Ex9 (all samples)
  C7: C3 + status samples (goal_kick + kickoff) = current production
  C8: C6 + status samples = max everything

Usage:
  python3 tools/probe_overnight.py --tag overnight_sweep
  python3 tools/probe_overnight.py --tag overnight_sweep --reps 3
"""
import argparse
import json
import os
import sys
import time
import urllib.request
import re
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.abspath(__file__)) + "/.."
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, BASE_DIR + "/ai_tactics")

import r2k_evaluator as ev  # noqa: E402

OLLAMA_URL = os.getenv("R2K_OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
MODEL = os.getenv("R2K_OLLAMA_MODEL", "qwen2.5:3b")
RESULTS_DIR = os.path.join(BASE_DIR, "results")
FRAG_DIR = os.path.join(BASE_DIR, "strategy", "fragments")
os.makedirs(RESULTS_DIR, exist_ok=True)

# --- Sample block definitions ---
# Each example as a self-contained string (INPUT + OUTPUT block)

EX6 = """--- EXAMPLE 6: GOALIE CLEARANCE (goalie closest, ball deep in own zone) ---
INPUT: {"soccer_ball": {"x": -3.8, "y": 0.5}, "blue_1": {"x": -4.0, "y": 0.3}, "blue_2": {"x": -1.5, "y": 0.0}, "blue_3": {"x": 1.0, "y": -1.0}, "red_1": {"x": -3.5, "y": 0.5}, "red_2": {"x": -1.0, "y": 0.0}, "red_3": {"x": 2.0, "y": 1.5}}
OUTPUT: {
  "assignments": {
    "blue_1": {"role": "goalie", "action": "Kick"},
    "blue_2": {"role": "defender", "action": "Move", "x": -1.0, "y": 0.5},
    "blue_3": {"role": "attacker", "action": "Move", "x": 2.5, "y": -0.5}
  }
}"""

EX7 = """--- EXAMPLE 7: PASS TO FREE TEAMMATE (blue_2 passes to blue_3 in opponent half) ---
INPUT: {"soccer_ball": {"x": 1.0, "y": 0.0}, "blue_1": {"x": -4.0, "y": 0.0}, "blue_2": {"x": 0.8, "y": 0.2}, "blue_3": {"x": 3.0, "y": -1.0}, "red_1": {"x": 2.0, "y": 0.5}, "red_2": {"x": -1.0, "y": 0.0}, "red_3": {"x": 4.0, "y": 1.5}}
OUTPUT: {
  "assignments": {
    "blue_1": {"role": "goalie", "action": "Move", "x": -4.0, "y": 0.0},
    "blue_2": {"role": "attacker", "action": "Kick", "target_x": 3.0, "target_y": -1.0},
    "blue_3": {"role": "attacker", "action": "Move", "x": 3.5, "y": -1.0}
  }
}"""

EX8 = """--- EXAMPLE 8: GOALIE CLEARANCE FROM CORNER (ball deep in goal corner) ---
INPUT: {"soccer_ball": {"x": -4.0, "y": -2.0}, "blue_1": {"x": -4.2, "y": -1.8}, "blue_2": {"x": -1.5, "y": 0.0}, "blue_3": {"x": 0.5, "y": 1.0}, "red_1": {"x": -3.5, "y": -1.5}, "red_2": {"x": -1.0, "y": -0.5}, "red_3": {"x": 3.0, "y": 0.5}}
OUTPUT: {
  "assignments": {
    "blue_1": {"role": "goalie", "action": "Kick"},
    "blue_2": {"role": "defender", "action": "Move", "x": -1.0, "y": -0.5},
    "blue_3": {"role": "attacker", "action": "Move", "x": 2.0, "y": 1.0}
  }
}"""

EX9 = """--- EXAMPLE 9: PASS TO BLUE_2 (blue_3 passes to blue_2 on the wing) ---
INPUT: {"soccer_ball": {"x": 0.5, "y": 1.5}, "blue_1": {"x": -4.0, "y": 0.0}, "blue_2": {"x": 2.5, "y": 2.0}, "blue_3": {"x": 0.3, "y": 1.7}, "red_1": {"x": 1.5, "y": 0.5}, "red_2": {"x": -1.0, "y": -1.0}, "red_3": {"x": 4.0, "y": 1.0}}
OUTPUT: {
  "assignments": {
    "blue_1": {"role": "goalie", "action": "Move", "x": -4.0, "y": 0.0},
    "blue_2": {"role": "attacker", "action": "Move", "x": 3.0, "y": 2.0},
    "blue_3": {"role": "attacker", "action": "Kick", "target_x": 2.5, "target_y": 2.0}
  }
}"""

# Original 5 examples (Ex1-5, without Ex6/7)
SAMPLES_ORIGINAL = """--- EXAMPLE 1: STANDARD ATTACK (blue_2 closest to ball, blue_1 closest to goal) ---
INPUT: {"soccer_ball": {"x": -1.0, "y": 0.0}, "blue_1": {"x": -4.0, "y": 0.0}, "blue_2": {"x": -1.5, "y": 0.0}, "blue_3": {"x": -0.5, "y": 1.5}, "red_1": {"x": 0.0, "y": 0.0}}
OUTPUT: {
  "assignments": {
    "blue_1": {"role": "goalie", "action": "Move", "x": -4.0, "y": 0.0},
    "blue_2": {"role": "attacker", "action": "Kick"},
    "blue_3": {"role": "defender", "action": "Move", "x": 1.5, "y": 2.0}
  }
}
--- EXAMPLE 2: GOALIE BECOMES CLOSEST — ROLE SWAP ---
INPUT: {"soccer_ball": {"x": -3.8, "y": 0.2}, "blue_1": {"x": -3.9, "y": 0.2}, "blue_2": {"x": -2.0, "y": 0.5}, "blue_3": {"x": -1.0, "y": -0.5}, "red_1": {"x": -3.5, "y": 0.3}}
OUTPUT: {
  "assignments": {
    "blue_1": {"role": "attacker", "action": "Kick"},
    "blue_2": {"role": "goalie", "action": "Move", "x": -4.0, "y": 0.2},
    "blue_3": {"role": "defender", "action": "Move", "x": -2.0, "y": 0.0}
  }
}
--- EXAMPLE 3: PASS FORWARD TO FREE BOT ---
INPUT: {"soccer_ball": {"x": 1.0, "y": 0.0}, "blue_1": {"x": -4.0, "y": 0.0}, "blue_2": {"x": 0.8, "y": 0.2}, "blue_3": {"x": 3.0, "y": -1.0}, "red_1": {"x": 2.0, "y": 0.5}}
OUTPUT: {
  "assignments": {
    "blue_1": {"role": "goalie", "action": "Move", "x": -4.0, "y": 0.0},
    "blue_2": {"role": "attacker", "action": "Kick"},
    "blue_3": {"role": "attacker", "action": "Move", "x": 3.5, "y": -0.5}
  }
}
--- EXAMPLE 4: CARRY BALL FORWARD (OPEN SPACE) ---
INPUT: {"soccer_ball": {"x": 0.0, "y": 0.0}, "blue_1": {"x": -4.0, "y": 0.0}, "blue_2": {"x": -0.2, "y": 0.1}, "blue_3": {"x": -1.5, "y": 1.0}, "red_1": {"x": 3.0, "y": 0.0}}
OUTPUT: {
  "assignments": {
    "blue_1": {"role": "goalie", "action": "Move", "x": -4.0, "y": 0.0},
    "blue_2": {"role": "attacker", "action": "Move", "x": 2.0, "y": 0.0},
    "blue_3": {"role": "defender", "action": "Move", "x": 0.0, "y": 1.0}
  }
}
--- EXAMPLE 5: ALL BOTS BEHIND THE BALL (DEFENDING) ---
INPUT: {"soccer_ball": {"x": -2.0, "y": 0.5}, "blue_1": {"x": -4.0, "y": 0.0}, "blue_2": {"x": -2.5, "y": 0.5}, "blue_3": {"x": -1.5, "y": -0.5}, "red_1": {"x": -1.8, "y": 0.6}}
OUTPUT: {
  "assignments": {
    "blue_1": {"role": "goalie", "action": "Move", "x": -4.0, "y": 0.5},
    "blue_2": {"role": "attacker", "action": "Kick"},
    "blue_3": {"role": "defender", "action": "Move", "x": -2.5, "y": -0.5}
  }
}"""

# Status sample files (loaded from disk)
STATUS_SAMPLES_GOAL_KICK = "samples_goal_kick.txt"
STATUS_SAMPLES_KICKOFF = "samples_kickoff.txt"

# --- Configurations ---
CONFIGS = {
    "C0": {"label": "C0: original 5 samples (baseline)", "extra_samples": [], "status_samples": False},
    "C1": {"label": "C1: + Ex6 (goalie clearance)", "extra_samples": [EX6], "status_samples": False},
    "C2": {"label": "C2: + Ex7 (pass to teammate)", "extra_samples": [EX7], "status_samples": False},
    "C3": {"label": "C3: + Ex6 + Ex7 (both new)", "extra_samples": [EX6, EX7], "status_samples": False},
    "C4": {"label": "C4: + Ex6 + Ex7 + Ex8 (2nd goalie)", "extra_samples": [EX6, EX7, EX8], "status_samples": False},
    "C5": {"label": "C5: + Ex6 + Ex7 + Ex9 (pass to blue_2)", "extra_samples": [EX6, EX7, EX9], "status_samples": False},
    "C6": {"label": "C6: + Ex6 + Ex7 + Ex8 + Ex9 (all)", "extra_samples": [EX6, EX7, EX8, EX9], "status_samples": False},
    "C7": {"label": "C7: Ex6+Ex7 + status (OLD production)", "extra_samples": [EX6, EX7], "status_samples": True},
    "C8": {"label": "C8: Ex6+Ex7+Ex8+Ex9 + status (NEW production)", "extra_samples": [EX6, EX7, EX8, EX9], "status_samples": True},
}


def read_fragment(name):
    path = os.path.join(FRAG_DIR, name)
    try:
        with open(path) as f:
            return f.read()
    except FileNotFoundError:
        return ""


def clean_json_samples(content, explain_active=False):
    """Use the evaluator's cleaning function."""
    return ev._clean_json_samples(content, explain_active)


def assemble_prompt_for_config(config_name, status, mode="3vs3", n_blue=3):
    """Assemble system prompt with custom sample configuration."""
    cfg = CONFIGS[config_name]
    is_explain = False
    text_header = ev._text_output_header(n_blue)

    explain_instr = "- Output ONLY the 'assignments' key."
    output_format = "Output ONLY pure, raw JSON."

    parts = []
    # header.txt
    header = read_fragment("header.txt")
    header = header.replace("Output ONLY pure, raw JSON.", output_format)
    header = header.replace("{{EXPLAIN_INSTRUCTION}}", explain_instr)
    parts.append(header)

    # rules_core.txt
    parts.append(read_fragment("rules_core.txt"))

    # Game-phase rules (additive)
    if status != "playing":
        phase_rules = read_fragment(f"rules_{status}.txt")
        if phase_rules:
            parts.append(phase_rules)

    # Mode rules (always loaded)
    parts.append(read_fragment(f"rules_{mode}.txt"))

    # Game-phase samples (additive)
    if status != "playing" and cfg["status_samples"]:
        phase_samples = read_fragment(f"samples_{status}.txt")
        if phase_samples:
            parts.append(clean_json_samples(phase_samples, is_explain))

    # Mode samples: original 5 + extra samples
    samples_content = SAMPLES_ORIGINAL
    for extra in cfg["extra_samples"]:
        samples_content += "\n" + extra
    parts.append(clean_json_samples(samples_content, is_explain))

    return "\n\n".join(p for p in parts if p.strip()).strip()


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
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    lat_ms = int((time.time() - t0) * 1000)
    eval_count = data.get("eval_count", 0)
    prompt_eval_count = data.get("prompt_eval_count", 0)
    return data.get("response", ""), lat_ms, eval_count, prompt_eval_count


def dist(a, b):
    return ((a.get("x", 0) - b.get("x", 0)) ** 2 + (a.get("y", 0) - b.get("y", 0)) ** 2) ** 0.5


def classify_goalie_kick(asn, ents, status):
    """Determine if a goalie kick occurred and whether it was correct.
    
    Returns: (goalie_kicked, goalie_kick_correct, reason)
    """
    ball = ents.get("soccer_ball", {})
    blue_bots = {k: v for k, v in ents.items() if k.startswith("blue_")}
    
    # Find closest blue bot to ball
    closest_bot = min(blue_bots.keys(), key=lambda b: dist(ball, blue_bots[b]))
    closest_dist = dist(ball, blue_bots[closest_bot])
    
    # Check if any bot was assigned goalie role + Kick action
    goalie_kicker = None
    for bot, a in asn.items():
        if str(a.get("role", "")).lower() == "goalie" and str(a.get("action", "")).lower() == "kick":
            goalie_kicker = bot
            break
    
    if not goalie_kicker:
        return False, None, "no_goalie_kick"
    
    # Was the goalie actually the closest bot?
    is_goalie_closest = (goalie_kicker == closest_bot)
    # Was the ball in own half?
    ball_in_own_half = ball.get("x", 0) < 0
    
    if is_goalie_closest and ball_in_own_half:
        return True, True, "correct_goalie_kick"
    elif is_goalie_closest and not ball_in_own_half:
        return True, False, "goalie_kicked_but_ball_in_opp_half"
    elif not is_goalie_closest and ball_in_own_half:
        return True, False, "goalie_kicked_but_not_closest"
    else:
        return True, False, "goalie_kicked_wrong_situation"


def classify_pass(asn, ents, status):
    """Determine if a pass occurred and whether it was correct.
    
    Returns: (passed, pass_correct, reason)
    """
    ball = ents.get("soccer_ball", {})
    blue_bots = {k: v for k, v in ents.items() if k.startswith("blue_")}
    red_bots = {k: v for k, v in ents.items() if k.startswith("red_")}
    
    # Find pass (Kick with target_x/y)
    passer = None
    target_x, target_y = None, None
    for bot, a in asn.items():
        if str(a.get("action", "")).lower() == "kick" and "target_x" in a:
            passer = bot
            tx = a.get("target_x")
            ty = a.get("target_y", 0)
            if tx is None:
                continue
            target_x = float(tx)
            target_y = float(ty) if ty is not None else 0.0
            break
    
    if not passer:
        return False, None, "no_pass"
    
    # Check if target is near a teammate
    target_pos = {"x": target_x, "y": target_y}
    nearest_teammate = None
    nearest_teammate_dist = 999
    for bot, pos in blue_bots.items():
        if bot == passer:
            continue
        d = dist(target_pos, pos)
        if d < nearest_teammate_dist:
            nearest_teammate_dist = d
            nearest_teammate = bot
    
    # Check if that teammate is open (no red within 1.5m)
    teammate_open = False
    if nearest_teammate and nearest_teammate_dist < 2.0:
        teammate_pos = blue_bots[nearest_teammate]
        min_red_dist = min(dist(teammate_pos, r) for r in red_bots.values()) if red_bots else 999
        teammate_open = min_red_dist > 1.5
    
    if teammate_open:
        return True, True, "correct_pass_to_open_teammate"
    elif nearest_teammate and nearest_teammate_dist < 2.0:
        return True, False, "pass_to_covered_teammate"
    else:
        return True, False, "pass_to_empty_space"


def check_target_in_field(asn):
    """Check if all Move targets are within field bounds."""
    for bot, a in asn.items():
        if str(a.get("action", "")).lower() == "move":
            x = a.get("x", 0)
            y = a.get("y", 0)
            if abs(x) > 4.5 or abs(y) > 3.0:
                return False
    return True


def run_one(config_name, scenario, rep):
    """Probe a single scenario with a specific config. Returns a record dict."""
    label = scenario["label"]
    category = scenario.get("category", "existing")
    status = scenario.get("status", "playing")
    ents = scenario["entities"]
    expected = scenario.get("expected", {})
    
    sys_prompt = assemble_prompt_for_config(config_name, status)
    
    min_ents = {k: {"x": round(v["x"], 1), "y": round(v["y"], 1)} for k, v in ents.items()}
    if status != "playing":
        min_ents["match_state"] = {"status": status, "restart_team": ""}
    
    req_keys = "Output ONLY the 'assignments' key."
    user_prompt = json.dumps(min_ents) + f"\n\nCRITICAL: Output ONLY valid JSON. {req_keys} End immediately after closing bracket."
    
    raw, lat_ms, eval_count, prompt_eval_count = call_ollama(user_prompt, sys_prompt)
    data, err = ev.fast_parse(raw)
    if data and "assignments" not in data:
        data = {"assignments": data}
    
    record = {
        "config": config_name,
        "label": label,
        "category": category,
        "status": status,
        "rep": rep,
        "latency_ms": lat_ms,
        "eval_count": eval_count,
        "prompt_eval_count": prompt_eval_count,
        "parse_ok": bool(data),
        "parse_code": err if data is None else 0,
        "raw_preview": (raw[:200] if raw else ""),
    }
    
    if data:
        asn = data.get("assignments", {})
        record["assignments"] = asn
        record["role_coverage"] = len(asn)
        actions = set(str(a.get("action", "")).lower() for a in asn.values())
        record["action_diversity"] = len(actions)
        record["target_in_field"] = check_target_in_field(asn)
        
        # Goalie kick classification
        gk, gk_correct, gk_reason = classify_goalie_kick(asn, ents, status)
        record["goalie_kicked"] = gk
        record["goalie_kick_correct"] = gk_correct
        record["goalie_kick_reason"] = gk_reason
        
        # Pass classification
        passed, pass_correct, pass_reason = classify_pass(asn, ents, status)
        record["passed"] = passed
        record["pass_correct"] = pass_correct
        record["pass_reason"] = pass_reason
        
        # Expected behavior
        record["expected_goalie_kick"] = expected.get("goalie_should_kick")
        record["expected_pass"] = expected.get("pass_should_occur")
    
    return record


def generate_report(records, configs_run, output_path):
    """Generate markdown report with inflection point analysis."""
    lines = []
    lines.append(f"# Overnight Probe Report: Sample Sweep\n")
    lines.append(f"Model: {MODEL}\n")
    lines.append(f"Total calls: {len(records)}\n")
    lines.append(f"Configs: {', '.join(configs_run)}\n")
    lines.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    
    # --- Summary table ---
    lines.append("## Summary: Precision/Recall by Config\n")
    header = f"| Config | Goalie Recall | Goalie Precision | Pass Recall | Pass Precision | Parse OK | Latency p50 | Eval tokens |"
    sep =    f"|--------|---------------|------------------|-------------|----------------|----------|-------------|-------------|"
    lines.append(header)
    lines.append(sep)
    
    for cfg in configs_run:
        cfg_recs = [r for r in records if r["config"] == cfg and r.get("parse_ok")]
        
        # Goalie recall: of scenarios where goalie SHOULD kick, how many did?
        goalie_should = [r for r in cfg_recs if r.get("expected_goalie_kick") is True]
        goalie_did = [r for r in goalie_should if r.get("goalie_kicked")]
        goalie_recall = len(goalie_did) / len(goalie_should) * 100 if goalie_should else 0
        
        # Goalie precision: of scenarios where goalie DID kick, how many were correct?
        goalie_did_all = [r for r in cfg_recs if r.get("goalie_kicked")]
        goalie_correct = [r for r in goalie_did_all if r.get("goalie_kick_correct") is True]
        goalie_precision = len(goalie_correct) / len(goalie_did_all) * 100 if goalie_did_all else 0
        
        # Pass recall: of scenarios where pass SHOULD occur, how many did?
        pass_should = [r for r in cfg_recs if r.get("expected_pass") is True]
        pass_did = [r for r in pass_should if r.get("passed")]
        pass_recall = len(pass_did) / len(pass_should) * 100 if pass_should else 0
        
        # Pass precision: of scenarios where pass DID occur, how many were correct?
        pass_did_all = [r for r in cfg_recs if r.get("passed")]
        pass_correct = [r for r in pass_did_all if r.get("pass_correct") is True]
        pass_precision = len(pass_correct) / len(pass_did_all) * 100 if pass_did_all else 0
        
        # Parse
        all_cfg = [r for r in records if r["config"] == cfg]
        parse_ok = sum(1 for r in all_cfg if r.get("parse_ok"))
        parse_pct = parse_ok / len(all_cfg) * 100 if all_cfg else 0
        
        # Latency
        lats = sorted(r["latency_ms"] for r in all_cfg)
        lat_p50 = lats[len(lats)//2] if lats else 0
        
        # Tokens
        tokens = [r.get("eval_count", 0) for r in cfg_recs if r.get("eval_count")]
        avg_tokens = sum(tokens) / len(tokens) if tokens else 0
        
        cfg_label = CONFIGS[cfg]["label"].split(":")[0]
        lines.append(f"| {cfg_label:<6} | {goalie_recall:>12.1f}% | {goalie_precision:>15.1f}% | {pass_recall:>10.1f}% | {pass_precision:>13.1f}% | {parse_pct:>6.1f}% | {lat_p50:>9}ms | {avg_tokens:>9.0f} |")
    
    lines.append("")
    
    # --- Inflection point analysis ---
    lines.append("## Inflection Point Analysis\n")
    
    # Goalie kick recall by sample count
    lines.append("### Goalie Kick Recall by Sample Count\n")
    lines.append("| Samples | Config | Recall | Delta |")
    lines.append("|---------|--------|--------|-------|")
    goalie_configs = [("0", "C0"), ("1", "C1"), ("2", "C4")]
    prev_recall = None
    for n, cfg in goalie_configs:
        cfg_recs = [r for r in records if r["config"] == cfg and r.get("parse_ok") and r.get("expected_goalie_kick") is True]
        did = [r for r in cfg_recs if r.get("goalie_kicked")]
        recall = len(did) / len(cfg_recs) * 100 if cfg_recs else 0
        delta = f"{recall - prev_recall:+.1f}%" if prev_recall is not None else "—"
        lines.append(f"| {n} goalie | {cfg} | {recall:.1f}% | {delta} |")
        prev_recall = recall
    
    lines.append("")
    
    # Pass recall by sample count
    lines.append("### Pass Recall by Sample Count\n")
    lines.append("| Samples | Config | Recall | Delta |")
    lines.append("|---------|--------|--------|-------|")
    pass_configs = [("0", "C0"), ("1", "C2"), ("2", "C5")]
    prev_recall = None
    for n, cfg in pass_configs:
        cfg_recs = [r for r in records if r["config"] == cfg and r.get("parse_ok") and r.get("expected_pass") is True]
        did = [r for r in cfg_recs if r.get("passed")]
        recall = len(did) / len(cfg_recs) * 100 if cfg_recs else 0
        delta = f"{recall - prev_recall:+.1f}%" if prev_recall is not None else "—"
        lines.append(f"| {n} pass | {cfg} | {recall:.1f}% | {delta} |")
        prev_recall = recall
    
    lines.append("")
    
    # --- Per-category breakdown ---
    lines.append("## Per-Category Breakdown\n")
    categories = sorted(set(r.get("category", "existing") for r in records))
    for cat in categories:
        cat_recs = [r for r in records if r.get("category") == cat]
        if not cat_recs:
            continue
        lines.append(f"### {cat} ({len(cat_recs)//len(configs_run)} scenarios × {len(configs_run)} configs)\n")
        lines.append("| Config | Goalie Kick% | Pass% | Parse% | Latency |")
        lines.append("|--------|-------------|-------|--------|---------|")
        for cfg in configs_run:
            cfg_cat = [r for r in cat_recs if r["config"] == cfg]
            if not cfg_cat:
                continue
            gk = sum(1 for r in cfg_cat if r.get("goalie_kicked")) / len(cfg_cat) * 100
            ps = sum(1 for r in cfg_cat if r.get("passed")) / len(cfg_cat) * 100
            pk = sum(1 for r in cfg_cat if r.get("parse_ok")) / len(cfg_cat) * 100
            lats = sorted(r["latency_ms"] for r in cfg_cat)
            lat = lats[len(lats)//2]
            cfg_label = CONFIGS[cfg]["label"].split(":")[0]
            lines.append(f"| {cfg_label:<6} | {gk:>9.0f}% | {ps:>4.0f}% | {pk:>5.0f}% | {lat:>5}ms |")
        lines.append("")
    
    # --- Determinism check ---
    lines.append("## Determinism Check\n")
    det_issues = []
    for cfg in configs_run:
        cfg_recs = [r for r in records if r["config"] == cfg]
        by_label = defaultdict(list)
        for r in cfg_recs:
            by_label[r["label"]].append(r)
        for label, reps in by_label.items():
            if len(reps) < 2:
                continue
            # Check if goalie_kicked or passed differs across reps
            gk_vals = set(r.get("goalie_kicked") for r in reps if r.get("parse_ok"))
            pass_vals = set(r.get("passed") for r in reps if r.get("parse_ok"))
            if len(gk_vals) > 1 or len(pass_vals) > 1:
                det_issues.append(f"  {cfg} / {label}: goalie_kicked={gk_vals}, passed={pass_vals}")
    
    if det_issues:
        lines.append(f"**{len(det_issues)} determinism issues found:**\n")
        for issue in det_issues[:20]:
            lines.append(issue)
        if len(det_issues) > 20:
            lines.append(f"  ... and {len(det_issues)-20} more")
    else:
        lines.append("All scenarios produced identical results across reps (temperature=0.0 deterministic).\n")
    
    lines.append("")
    
    # --- Recommendation ---
    lines.append("## Recommendation\n")
    lines.append("Based on the inflection point analysis above:\n")
    lines.append("- If goalie recall plateaus at C1 (1 sample), Ex8 is unnecessary\n")
    lines.append("- If pass recall plateaus at C2 (1 sample), Ex9 is unnecessary\n")
    lines.append("- If C7 ≈ C3, status samples add no value\n")
    lines.append("- Choose the config with highest recall where precision > 80% and latency < 700ms\n")
    
    with open(output_path, "w") as f:
        f.write("\n".join(lines))
    return output_path


def main():
    ap = argparse.ArgumentParser(description="Overnight sample sweep probe")
    ap.add_argument("--corpus", default=os.path.join(BASE_DIR, "tests", "synthetic_worldstates", "corpus_overnight.jsonl"))
    ap.add_argument("--tag", default="overnight_sweep")
    ap.add_argument("--reps", type=int, default=5)
    ap.add_argument("--configs", default="C0,C1,C2,C3,C4,C5,C6,C7,C8", help="comma-separated config names")
    args = ap.parse_args()
    
    with open(args.corpus) as f:
        corpus = [json.loads(l) for l in f if l.strip()]
    
    configs_run = args.configs.split(",")
    total_calls = len(corpus) * args.reps * len(configs_run)
    
    print(f"=== Overnight Sample Sweep ===")
    print(f"Model: {MODEL}")
    print(f"Corpus: {len(corpus)} scenarios")
    print(f"Configs: {len(configs_run)} ({', '.join(configs_run)})")
    print(f"Reps: {args.reps}")
    print(f"Total calls: {total_calls}")
    est_min = total_calls * 0.65 / 60  # ~650ms per call
    print(f"Estimated time: {est_min:.0f}min ({est_min/60:.1f}h)")
    print()
    
    # Warmup
    print("Warming up model...", end=" ", flush=True)
    call_ollama("hello", "Output ONLY pure, raw JSON.", num_predict=5)
    print("done")
    
    all_records = []
    raw_path = os.path.join(RESULTS_DIR, f"probe_{args.tag}_raw.jsonl")
    
    for ci, cfg in enumerate(configs_run):
        print(f"\n--- Config {cfg} ({CONFIGS[cfg]['label']}) ---")
        t0 = time.time()
        
        for rep in range(args.reps):
            for si, scenario in enumerate(corpus):
                try:
                    rec = run_one(cfg, scenario, rep)
                    all_records.append(rec)
                except Exception as e:
                    print(f"  ERROR: {cfg} rep{rep} {scenario.get('label','?')}: {e}")
                    all_records.append({
                        "config": cfg, "label": scenario.get("label", "?"),
                        "category": scenario.get("category", "?"), "status": scenario.get("status", "?"),
                        "rep": rep, "parse_ok": False, "error": str(e)[:100],
                        "latency_ms": 0, "eval_count": 0, "prompt_eval_count": 0,
                    })
                
                # Progress
                if (si + 1) % 50 == 0:
                    elapsed = time.time() - t0
                    done = rep * len(corpus) + si + 1
                    total_in_cfg = args.reps * len(corpus)
                    rate = done / elapsed if elapsed > 0 else 0
                    eta = (total_in_cfg - done) / rate if rate > 0 else 0
                    print(f"  rep{rep} {si+1}/{len(corpus)} ({done}/{total_in_cfg}) {rate:.1f}/s ETA {eta:.0f}s", flush=True)
            
            # Write raw after each rep (incremental save)
            with open(raw_path, "w") as f:
                for r in all_records:
                    f.write(json.dumps(r) + "\n")
        
        elapsed = time.time() - t0
        cfg_recs = [r for r in all_records if r["config"] == cfg]
        parse_ok = sum(1 for r in cfg_recs if r.get("parse_ok"))
        gk = sum(1 for r in cfg_recs if r.get("goalie_kicked"))
        ps = sum(1 for r in cfg_recs if r.get("passed"))
        lats = [r["latency_ms"] for r in cfg_recs if r["latency_ms"] > 0]
        lat_p50 = sorted(lats)[len(lats)//2] if lats else 0
        print(f"  Done: {len(cfg_recs)} calls, parse_ok={parse_ok}, goalie_kicks={gk}, passes={ps}, lat_p50={lat_p50}ms, {elapsed:.0f}s")
    
    # Generate report
    report_path = os.path.join(RESULTS_DIR, f"probe_{args.tag}_report.md")
    generate_report(all_records, configs_run, report_path)
    
    print(f"\n=== Sweep complete: {len(all_records)} records ===")
    print(f"Raw: {raw_path}")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
