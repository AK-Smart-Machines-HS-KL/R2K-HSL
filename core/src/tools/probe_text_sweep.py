#!/usr/bin/env python3
"""TEXT mode variant sweep probe.

Tests creative prompt variants in TEXT mode against the 231-scenario
corpus. Each variant modifies samples, titles, role labels, or ordering
to attack specific open problems (goalie kick, passing, clustering).

Variants:
  V0: TEXT baseline (current fragments + new vocab)
  V1: Sample primacy (Ex6/Ex7 first, Ex1-5 last)
  V2: Role-swap saturation (4 swap examples)
  V3: Situation-tagged headers ("IF ball X<0 AND goalie closest:")
  V4: Per-status sample gating (goal_kick->Ex6 only, playing->Ex1-5)
  V5: Qualitative tags replace roles ("closest to ball" not "attacker")
  V6: Micro-CoT reason clause ("blue_2 kick -- closest to ball")
  V7: V1+V3 combined (primacy + situation tags)
  V8: JSON C7 (control group, runs in JSON mode)

Usage:
  python3 tools/probe_text_sweep.py --tag text_sweep --reps 10
  python3 tools/probe_text_sweep.py --tag text_sweep --variants V0,V1,V2
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

# --- Sample block definitions (JSON format, cleaned per mode) ---

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

# 3 new role-swap examples for V2 (different field positions)
EX2B = """--- EXAMPLE 2B: GOALIE SWAPS FROM THE WING ---
INPUT: {"soccer_ball": {"x": -3.5, "y": 2.0}, "blue_1": {"x": -3.8, "y": 1.8}, "blue_2": {"x": -1.0, "y": 0.5}, "blue_3": {"x": 0.5, "y": -1.0}, "red_1": {"x": -3.0, "y": 1.5}, "red_2": {"x": -0.5, "y": 0.0}, "red_3": {"x": 2.0, "y": 1.0}}
OUTPUT: {
  "assignments": {
    "blue_1": {"role": "attacker", "action": "Kick"},
    "blue_2": {"role": "goalie", "action": "Move", "x": -4.0, "y": 0.0},
    "blue_3": {"role": "defender", "action": "Move", "x": -1.5, "y": -0.5}
  }
}"""

EX2C = """--- EXAMPLE 2C: GOALIE SWAPS FROM CENTER ---
INPUT: {"soccer_ball": {"x": -2.5, "y": 0.0}, "blue_1": {"x": -3.0, "y": 0.2}, "blue_2": {"x": 0.0, "y": 1.0}, "blue_3": {"x": 1.5, "y": -1.0}, "red_1": {"x": -2.0, "y": 0.0}, "red_2": {"x": 1.0, "y": 0.5}, "red_3": {"x": 3.0, "y": -1.5}}
OUTPUT: {
  "assignments": {
    "blue_1": {"role": "attacker", "action": "Kick"},
    "blue_2": {"role": "goalie", "action": "Move", "x": -4.0, "y": 0.0},
    "blue_3": {"role": "defender", "action": "Move", "x": -1.0, "y": 0.5}
  }
}"""

EX2D = """--- EXAMPLE 2D: GOALIE SWAPS FROM DEEP CORNER ---
INPUT: {"soccer_ball": {"x": -4.0, "y": -1.5}, "blue_1": {"x": -4.2, "y": -1.2}, "blue_2": {"x": -1.5, "y": 0.0}, "blue_3": {"x": 1.0, "y": 1.5}, "red_1": {"x": -3.5, "y": -1.0}, "red_2": {"x": -1.0, "y": -0.5}, "red_3": {"x": 2.0, "y": 0.5}}
OUTPUT: {
  "assignments": {
    "blue_1": {"role": "attacker", "action": "Kick"},
    "blue_2": {"role": "goalie", "action": "Move", "x": -4.0, "y": 0.0},
    "blue_3": {"role": "defender", "action": "Move", "x": -1.0, "y": 1.0}
  }
}"""

# Original 5 examples (Ex1-5)
EX1 = """--- EXAMPLE 1: STANDARD ATTACK (blue_2 closest to ball, blue_1 closest to goal) ---
INPUT: {"soccer_ball": {"x": -1.0, "y": 0.0}, "blue_1": {"x": -4.0, "y": 0.0}, "blue_2": {"x": -1.5, "y": 0.0}, "blue_3": {"x": -0.5, "y": 1.5}, "red_1": {"x": 0.0, "y": 0.0}}
OUTPUT: {
  "assignments": {
    "blue_1": {"role": "goalie", "action": "Move", "x": -4.0, "y": 0.0},
    "blue_2": {"role": "attacker", "action": "Kick"},
    "blue_3": {"role": "defender", "action": "Move", "x": 1.5, "y": 2.0}
  }
}"""

EX2 = """--- EXAMPLE 2: GOALIE BECOMES CLOSEST — ROLE SWAP ---
INPUT: {"soccer_ball": {"x": -3.8, "y": 0.2}, "blue_1": {"x": -3.9, "y": 0.2}, "blue_2": {"x": -2.0, "y": 0.5}, "blue_3": {"x": -1.0, "y": -0.5}, "red_1": {"x": -3.5, "y": 0.3}}
OUTPUT: {
  "assignments": {
    "blue_1": {"role": "attacker", "action": "Kick"},
    "blue_2": {"role": "goalie", "action": "Move", "x": -4.0, "y": 0.2},
    "blue_3": {"role": "defender", "action": "Move", "x": -2.0, "y": 0.0}
  }
}"""

EX3 = """--- EXAMPLE 3: PASS FORWARD TO FREE BOT ---
INPUT: {"soccer_ball": {"x": 1.0, "y": 0.0}, "blue_1": {"x": -4.0, "y": 0.0}, "blue_2": {"x": 0.8, "y": 0.2}, "blue_3": {"x": 3.0, "y": -1.0}, "red_1": {"x": 2.0, "y": 0.5}}
OUTPUT: {
  "assignments": {
    "blue_1": {"role": "goalie", "action": "Move", "x": -4.0, "y": 0.0},
    "blue_2": {"role": "attacker", "action": "Kick"},
    "blue_3": {"role": "attacker", "action": "Move", "x": 3.5, "y": -0.5}
  }
}"""

EX4 = """--- EXAMPLE 4: CARRY BALL FORWARD (OPEN SPACE) ---
INPUT: {"soccer_ball": {"x": 0.0, "y": 0.0}, "blue_1": {"x": -4.0, "y": 0.0}, "blue_2": {"x": -0.2, "y": 0.1}, "blue_3": {"x": -1.5, "y": 1.0}, "red_1": {"x": 3.0, "y": 0.0}}
OUTPUT: {
  "assignments": {
    "blue_1": {"role": "goalie", "action": "Move", "x": -4.0, "y": 0.0},
    "blue_2": {"role": "attacker", "action": "Move", "x": 2.0, "y": 0.0},
    "blue_3": {"role": "defender", "action": "Move", "x": 0.0, "y": 1.0}
  }
}"""

EX5 = """--- EXAMPLE 5: ALL BOTS BEHIND THE BALL (DEFENDING) ---
INPUT: {"soccer_ball": {"x": -2.0, "y": 0.5}, "blue_1": {"x": -4.0, "y": 0.0}, "blue_2": {"x": -2.5, "y": 0.5}, "blue_3": {"x": -1.5, "y": -0.5}, "red_1": {"x": -1.8, "y": 0.6}}
OUTPUT: {
  "assignments": {
    "blue_1": {"role": "goalie", "action": "Move", "x": -4.0, "y": 0.5},
    "blue_2": {"role": "attacker", "action": "Kick"},
    "blue_3": {"role": "defender", "action": "Move", "x": -2.5, "y": -0.5}
  }
}"""

ORIGINAL_5 = [EX1, EX2, EX3, EX4, EX5]

# --- Situation-tagged versions (V3) ---

EX6_TAGGED = """--- IF ball X<0 AND goalie closest AND ball deep in own zone: GOALIE CLEARANCE ---
INPUT: {"soccer_ball": {"x": -3.8, "y": 0.5}, "blue_1": {"x": -4.0, "y": 0.3}, "blue_2": {"x": -1.5, "y": 0.0}, "blue_3": {"x": 1.0, "y": -1.0}, "red_1": {"x": -3.5, "y": 0.5}, "red_2": {"x": -1.0, "y": 0.0}, "red_3": {"x": 2.0, "y": 1.5}}
OUTPUT: {
  "assignments": {
    "blue_1": {"role": "goalie", "action": "Kick"},
    "blue_2": {"role": "defender", "action": "Move", "x": -1.0, "y": 0.5},
    "blue_3": {"role": "attacker", "action": "Move", "x": 2.5, "y": -0.5}
  }
}"""

EX7_TAGGED = """--- IF teammate open at X>0 AND you have the ball: PASS ---
INPUT: {"soccer_ball": {"x": 1.0, "y": 0.0}, "blue_1": {"x": -4.0, "y": 0.0}, "blue_2": {"x": 0.8, "y": 0.2}, "blue_3": {"x": 3.0, "y": -1.0}, "red_1": {"x": 2.0, "y": 0.5}, "red_2": {"x": -1.0, "y": 0.0}, "red_3": {"x": 4.0, "y": 1.5}}
OUTPUT: {
  "assignments": {
    "blue_1": {"role": "goalie", "action": "Move", "x": -4.0, "y": 0.0},
    "blue_2": {"role": "attacker", "action": "Kick", "target_x": 3.0, "target_y": -1.0},
    "blue_3": {"role": "attacker", "action": "Move", "x": 3.5, "y": -1.0}
  }
}"""

EX1_TAGGED = """--- IF ball in midfield AND blue_2 closest: STANDARD ATTACK ---
INPUT: {"soccer_ball": {"x": -1.0, "y": 0.0}, "blue_1": {"x": -4.0, "y": 0.0}, "blue_2": {"x": -1.5, "y": 0.0}, "blue_3": {"x": -0.5, "y": 1.5}, "red_1": {"x": 0.0, "y": 0.0}}
OUTPUT: {
  "assignments": {
    "blue_1": {"role": "goalie", "action": "Move", "x": -4.0, "y": 0.0},
    "blue_2": {"role": "attacker", "action": "Kick"},
    "blue_3": {"role": "defender", "action": "Move", "x": 1.5, "y": 2.0}
  }
}"""

EX5_TAGGED = """--- IF all bots behind ball AND red pressing: DEFEND ---
INPUT: {"soccer_ball": {"x": -2.0, "y": 0.5}, "blue_1": {"x": -4.0, "y": 0.0}, "blue_2": {"x": -2.5, "y": 0.5}, "blue_3": {"x": -1.5, "y": -0.5}, "red_1": {"x": -1.8, "y": 0.6}}
OUTPUT: {
  "assignments": {
    "blue_1": {"role": "goalie", "action": "Move", "x": -4.0, "y": 0.5},
    "blue_2": {"role": "attacker", "action": "Kick"},
    "blue_3": {"role": "defender", "action": "Move", "x": -2.5, "y": -0.5}
  }
}"""


def _qualitative_tags(sample_str):
    """Replace role labels with qualitative tags (V5). Keeps 'goalie' for bridge."""
    return (sample_str
            .replace('"role": "attacker"', '"proximity": "closest to ball"')
            .replace('"role": "defender"', '"position": "deep in own half"'))


def _add_reason(sample_str):
    """Add micro-CoT reason clause to Kick actions (V6)."""
    # Add reason to goalie Kick
    sample_str = sample_str.replace(
        '"role": "goalie", "action": "Kick"',
        '"role": "goalie", "action": "Kick", "reason": "goalie closest, clear danger"')
    # Add reason to pass Kick
    sample_str = sample_str.replace(
        '"action": "Kick", "target_x"',
        '"action": "Kick", "reason": "teammate open", "target_x"')
    # Add reason to shot Kick (attacker without target)
    sample_str = sample_str.replace(
        '"role": "attacker", "action": "Kick"}',
        '"role": "attacker", "action": "Kick", "reason": "closest to ball"}')
    return sample_str


def build_samples(variant, status, text_mode):
    """Build the samples content string for a given variant and status.
    Returns the raw sample string (before cleaning)."""
    is_json_control = (variant == "V8")

    if variant == "V0":
        # TEXT baseline: Ex1-5 + Ex6 + Ex7 (same as C7 production but in TEXT mode)
        samples = ORIGINAL_5 + [EX6, EX7]
    elif variant == "V1":
        # Sample primacy: Ex6, Ex7 first, then Ex1-5
        samples = [EX6, EX7] + ORIGINAL_5
    elif variant == "V2":
        # Role-swap saturation: Ex1-5 + Ex2 + Ex2B + Ex2C + Ex2D + Ex6 + Ex7 (4 swaps)
        samples = [EX1, EX3, EX4, EX5] + [EX2, EX2B, EX2C, EX2D, EX6, EX7]
    elif variant == "V3":
        # Situation-tagged headers
        samples = [EX1_TAGGED, EX2, EX3, EX4, EX5_TAGGED, EX6_TAGGED, EX7_TAGGED]
    elif variant == "V4":
        # Per-status gating: only relevant samples per status
        if status == "goal_kick":
            samples = [EX6]
        elif status == "kickoff":
            samples = [EX1]
        else:
            samples = ORIGINAL_5 + [EX6, EX7]
    elif variant == "V5":
        # Qualitative tags replace roles
        samples = [_qualitative_tags(s) for s in ORIGINAL_5 + [EX6, EX7]]
    elif variant == "V6":
        # Micro-CoT reason clause
        samples = [_add_reason(s) for s in ORIGINAL_5 + [EX6, EX7]]
    elif variant == "V7":
        # V1+V3 combined: tagged + primacy
        samples = [EX6_TAGGED, EX7_TAGGED] + [EX1_TAGGED, EX2, EX3, EX4, EX5_TAGGED]
    elif variant == "V8":
        # JSON control: same as C7 production (Ex1-5 + Ex6 + Ex7)
        samples = ORIGINAL_5 + [EX6, EX7]
    else:
        samples = ORIGINAL_5 + [EX6, EX7]

    content = "\n".join(samples)

    # Add status samples if applicable
    if variant != "V4":  # V4 does its own gating
        if status != "playing":
            phase_samples = read_fragment(f"samples_{status}.txt")
            if phase_samples:
                content = content + "\n" + phase_samples

    return content


def read_fragment(name):
    path = os.path.join(FRAG_DIR, name)
    try:
        with open(path) as f:
            return f.read()
    except FileNotFoundError:
        return ""


def assemble_prompt(variant, status, mode="3vs3", n_blue=3):
    """Assemble system prompt for a variant. V8 uses JSON mode, all others TEXT."""
    is_json = (variant == "V8")
    is_explain = False

    if is_json:
        text_header = ev._text_output_header(n_blue)
        explain_instr = "- Output ONLY the 'assignments' key."
        output_format = "Output ONLY pure, raw JSON."
        cleaner = ev._clean_json_samples
        core_rules = read_fragment("rules_core.txt")
    else:
        text_header = ev._text_output_header(n_blue)
        explain_instr = "- Output ONLY the 'assignments' key."
        output_format = "OUTPUT FORMAT: " + text_header
        cleaner = ev._clean_text_samples
        core_rules = read_fragment("rules_core_text.txt") or read_fragment("rules_core.txt")

    parts = []
    # header.txt
    header = read_fragment("header.txt")
    header = header.replace("Output ONLY pure, raw JSON.", output_format)
    header = header.replace("{{EXPLAIN_INSTRUCTION}}", explain_instr)
    parts.append(header)

    # Core rules
    parts.append(core_rules)

    # Game-phase rules (additive)
    if status != "playing":
        phase_rules = read_fragment(f"rules_{status}.txt")
        if phase_rules:
            parts.append(phase_rules)

    # Mode rules
    parts.append(read_fragment(f"rules_{mode}.txt"))

    # Samples
    samples_content = build_samples(variant, status, not is_json)
    parts.append(cleaner(samples_content, is_explain))

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
    """Determine if a goalie kick occurred and whether it was correct."""
    ball = ents.get("soccer_ball", {})
    blue_bots = {k: v for k, v in ents.items() if k.startswith("blue_")}

    closest_bot = min(blue_bots.keys(), key=lambda b: dist(ball, blue_bots[b]))
    closest_dist = dist(ball, blue_bots[closest_bot])

    goalie_kicker = None
    for bot, a in asn.items():
        if str(a.get("role", "")).lower() == "goalie" and str(a.get("action", "")).lower() == "kick":
            goalie_kicker = bot
            break

    if not goalie_kicker:
        return False, None, "no_goalie_kick"

    is_goalie_closest = (goalie_kicker == closest_bot)
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
    """Determine if a pass occurred and whether it was correct."""
    ball = ents.get("soccer_ball", {})
    blue_bots = {k: v for k, v in ents.items() if k.startswith("blue_")}
    red_bots = {k: v for k, v in ents.items() if k.startswith("red_")}

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
    for bot, a in asn.items():
        if str(a.get("action", "")).lower() == "move":
            x = a.get("x", 0)
            y = a.get("y", 0)
            if abs(x) > 4.5 or abs(y) > 3.0:
                return False
    return True


def run_one(variant, scenario, rep):
    """Probe a single scenario with a specific variant."""
    label = scenario["label"]
    category = scenario.get("category", "existing")
    status = scenario.get("status", "playing")
    ents = scenario["entities"]
    expected = scenario.get("expected", {})
    is_json = (variant == "V8")

    sys_prompt = assemble_prompt(variant, status)

    if is_json:
        # JSON mode (V8 control)
        min_ents = {k: {"x": round(v["x"], 1), "y": round(v["y"], 1)} for k, v in ents.items()}
        if status != "playing":
            min_ents["match_state"] = {"status": status, "restart_team": ""}
        req_keys = "Output ONLY the 'assignments' key."
        user_prompt = json.dumps(min_ents) + f"\n\nCRITICAL: Output ONLY valid JSON. {req_keys} End immediately after closing bracket."
        raw, lat_ms, eval_count, prompt_eval_count = call_ollama(user_prompt, sys_prompt, num_predict=150)
        data, err = ev.fast_parse(raw)
    else:
        # TEXT mode
        ev.TEXT_MODE = True
        match_state = {"status": status}
        if "score_blue" in scenario:
            match_state["blue"] = scenario.get("score_blue", 0)
            match_state["red"] = scenario.get("score_red", 0)
        world_text = ev._build_text_world(ents, match_state)
        blue_names = ", ".join(sorted(k for k in ents if k.startswith("blue")))
        user_prompt = world_text + f"\n\nCommand: {blue_names}\n\n" + ev._text_output_header(len([k for k in ents if k.startswith("blue")]))
        raw, lat_ms, eval_count, prompt_eval_count = call_ollama(user_prompt, sys_prompt, num_predict=200)
        data, err = ev.text_parse(raw)
        if data is None:
            data, json_err = ev.fast_parse(raw)
            if data is not None:
                err = 10 + json_err
        ev.TEXT_MODE = False

    if data and "assignments" not in data:
        data = {"assignments": data}

    record = {
        "variant": variant,
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

        gk, gk_correct, gk_reason = classify_goalie_kick(asn, ents, status)
        record["goalie_kicked"] = gk
        record["goalie_kick_correct"] = gk_correct
        record["goalie_kick_reason"] = gk_reason

        passed, pass_correct, pass_reason = classify_pass(asn, ents, status)
        record["passed"] = passed
        record["pass_correct"] = pass_correct
        record["pass_reason"] = pass_reason

        record["expected_goalie_kick"] = expected.get("goalie_should_kick")
        record["expected_pass"] = expected.get("pass_should_occur")

    return record


VARIANT_LABELS = {
    "V0": "V0: TEXT baseline",
    "V1": "V1: Sample primacy",
    "V2": "V2: Role-swap saturation",
    "V3": "V3: Situation-tagged headers",
    "V4": "V4: Per-status gating",
    "V5": "V5: Qualitative tags",
    "V6": "V6: Micro-CoT reason",
    "V7": "V7: Primacy+tags",
    "V8": "V8: JSON control",
}


def generate_report(records, variants_run, output_path):
    """Generate markdown report with precision/recall by variant."""
    lines = []
    lines.append("# TEXT Mode Variant Sweep Report\n")
    lines.append(f"Model: {MODEL}\n")
    lines.append(f"Total calls: {len(records)}\n")
    lines.append(f"Variants: {', '.join(variants_run)}\n")
    lines.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

    # Summary table
    lines.append("## Summary: Precision/Recall by Variant\n")
    header = "| Variant | Goalie Recall | Goalie Precision | Pass Recall | Pass Precision | Parse OK | Latency p50 | Eval tokens |"
    sep = "|---------|---------------|------------------|-------------|----------------|----------|-------------|-------------|"
    lines.append(header)
    lines.append(sep)

    for v in variants_run:
        v_recs = [r for r in records if r["variant"] == v and r.get("parse_ok")]
        goalie_should = [r for r in v_recs if r.get("expected_goalie_kick") is True]
        goalie_did = [r for r in goalie_should if r.get("goalie_kicked")]
        goalie_recall = len(goalie_did) / len(goalie_should) * 100 if goalie_should else 0

        goalie_did_all = [r for r in v_recs if r.get("goalie_kicked")]
        goalie_correct = [r for r in goalie_did_all if r.get("goalie_kick_correct") is True]
        goalie_precision = len(goalie_correct) / len(goalie_did_all) * 100 if goalie_did_all else 0

        pass_should = [r for r in v_recs if r.get("expected_pass") is True]
        pass_did = [r for r in pass_should if r.get("passed")]
        pass_recall = len(pass_did) / len(pass_should) * 100 if pass_should else 0

        pass_did_all = [r for r in v_recs if r.get("passed")]
        pass_correct = [r for r in pass_did_all if r.get("pass_correct") is True]
        pass_precision = len(pass_correct) / len(pass_did_all) * 100 if pass_did_all else 0

        all_v = [r for r in records if r["variant"] == v]
        parse_ok = sum(1 for r in all_v if r.get("parse_ok"))
        parse_pct = parse_ok / len(all_v) * 100 if all_v else 0

        lats = sorted(r["latency_ms"] for r in all_v)
        lat_p50 = lats[len(lats) // 2] if lats else 0

        tokens = [r.get("eval_count", 0) for r in v_recs if r.get("eval_count")]
        avg_tokens = sum(tokens) / len(tokens) if tokens else 0

        lines.append(f"| {v:<7} | {goalie_recall:>12.1f}% | {goalie_precision:>15.1f}% | {pass_recall:>10.1f}% | {pass_precision:>13.1f}% | {parse_pct:>6.1f}% | {lat_p50:>9}ms | {avg_tokens:>9.0f} |")

    lines.append("")

    # Per-category breakdown
    lines.append("## Per-Category Breakdown\n")
    categories = sorted(set(r.get("category", "existing") for r in records))
    for cat in categories:
        cat_recs = [r for r in records if r.get("category") == cat]
        if not cat_recs:
            continue
        n_per_v = len(cat_recs) // len(variants_run) if variants_run else 0
        lines.append(f"### {cat} ({n_per_v} scenarios x {len(variants_run)} variants)\n")
        lines.append("| Variant | Goalie Kick% | Pass% | Parse% | Latency |")
        lines.append("|---------|-------------|-------|--------|---------|")
        for v in variants_run:
            v_cat = [r for r in cat_recs if r["variant"] == v]
            if not v_cat:
                continue
            gk = sum(1 for r in v_cat if r.get("goalie_kicked")) / len(v_cat) * 100
            ps = sum(1 for r in v_cat if r.get("passed")) / len(v_cat) * 100
            pk = sum(1 for r in v_cat if r.get("parse_ok")) / len(v_cat) * 100
            lats = sorted(r["latency_ms"] for r in v_cat)
            lat = lats[len(lats) // 2]
            lines.append(f"| {v:<7} | {gk:>9.0f}% | {ps:>4.0f}% | {pk:>5.0f}% | {lat:>5}ms |")
        lines.append("")

    # Determinism check
    lines.append("## Determinism Check\n")
    det_issues = []
    for v in variants_run:
        v_recs = [r for r in records if r["variant"] == v]
        by_label = defaultdict(list)
        for r in v_recs:
            by_label[r["label"]].append(r)
        for label, reps in by_label.items():
            if len(reps) < 2:
                continue
            gk_vals = set(r.get("goalie_kicked") for r in reps if r.get("parse_ok"))
            pass_vals = set(r.get("passed") for r in reps if r.get("parse_ok"))
            if len(gk_vals) > 1 or len(pass_vals) > 1:
                det_issues.append(f"  {v} / {label}: goalie_kicked={gk_vals}, passed={pass_vals}")

    if det_issues:
        lines.append(f"**{len(det_issues)} determinism issues found:**\n")
        for issue in det_issues[:20]:
            lines.append(issue)
        if len(det_issues) > 20:
            lines.append(f"  ... and {len(det_issues) - 20} more")
    else:
        lines.append("All scenarios produced identical results across reps (temperature=0.0 deterministic).\n")

    lines.append("")

    # Variant descriptions
    lines.append("## Variant Descriptions\n")
    for v in variants_run:
        lines.append(f"- **{v}**: {VARIANT_LABELS.get(v, v)}")
    lines.append("")

    with open(output_path, "w") as f:
        f.write("\n".join(lines))
    return output_path


def main():
    ap = argparse.ArgumentParser(description="TEXT mode variant sweep probe")
    ap.add_argument("--corpus", default=os.path.join(BASE_DIR, "tests", "synthetic_worldstates", "corpus_overnight.jsonl"))
    ap.add_argument("--tag", default="text_sweep")
    ap.add_argument("--reps", type=int, default=10)
    ap.add_argument("--variants", default="V0,V1,V2,V3,V4,V5,V6,V7,V8", help="comma-separated variant names")
    args = ap.parse_args()

    with open(args.corpus) as f:
        corpus = [json.loads(l) for l in f if l.strip()]

    variants_run = args.variants.split(",")
    total_calls = len(corpus) * args.reps * len(variants_run)

    print(f"=== TEXT Mode Variant Sweep ===")
    print(f"Model: {MODEL}")
    print(f"Corpus: {len(corpus)} scenarios")
    print(f"Variants: {len(variants_run)} ({', '.join(variants_run)})")
    print(f"Reps: {args.reps}")
    print(f"Total calls: {total_calls}")
    # TEXT mode ~450ms, JSON mode ~650ms; estimate blended
    est_min = total_calls * 0.5 / 60
    print(f"Estimated time: {est_min:.0f}min ({est_min / 60:.1f}h)")
    print()

    # Warmup
    print("Warming up model...", end=" ", flush=True)
    call_ollama("hello", "Output ONLY pure, raw JSON.", num_predict=5)
    print("done")

    all_records = []
    raw_path = os.path.join(RESULTS_DIR, f"probe_{args.tag}_raw.jsonl")

    for vi, v in enumerate(variants_run):
        print(f"\n--- Variant {v} ({VARIANT_LABELS.get(v, v)}) ---")
        t0 = time.time()

        for rep in range(args.reps):
            for si, scenario in enumerate(corpus):
                try:
                    rec = run_one(v, scenario, rep)
                    all_records.append(rec)
                except Exception as e:
                    print(f"  ERROR: {v} rep{rep} {scenario.get('label', '?')}: {e}")
                    all_records.append({
                        "variant": v, "label": scenario.get("label", "?"),
                        "category": scenario.get("category", "?"), "status": scenario.get("status", "?"),
                        "rep": rep, "parse_ok": False, "error": str(e)[:100],
                        "latency_ms": 0, "eval_count": 0, "prompt_eval_count": 0,
                    })

                if (si + 1) % 50 == 0:
                    elapsed = time.time() - t0
                    done = rep * len(corpus) + si + 1
                    total_in_v = args.reps * len(corpus)
                    rate = done / elapsed if elapsed > 0 else 0
                    eta = (total_in_v - done) / rate if rate > 0 else 0
                    print(f"  rep{rep} {si + 1}/{len(corpus)} ({done}/{total_in_v}) {rate:.1f}/s ETA {eta:.0f}s", flush=True)

            with open(raw_path, "w") as f:
                for r in all_records:
                    f.write(json.dumps(r) + "\n")

        elapsed = time.time() - t0
        v_recs = [r for r in all_records if r["variant"] == v]
        parse_ok = sum(1 for r in v_recs if r.get("parse_ok"))
        gk = sum(1 for r in v_recs if r.get("goalie_kicked"))
        ps = sum(1 for r in v_recs if r.get("passed"))
        lats = [r["latency_ms"] for r in v_recs if r["latency_ms"] > 0]
        lat_p50 = sorted(lats)[len(lats) // 2] if lats else 0
        print(f"  Done: {len(v_recs)} calls, parse_ok={parse_ok}, goalie_kicks={gk}, passes={ps}, lat_p50={lat_p50}ms, {elapsed:.0f}s")

    report_path = os.path.join(RESULTS_DIR, f"probe_{args.tag}_report.md")
    generate_report(all_records, variants_run, report_path)

    print(f"\n=== Sweep complete: {len(all_records)} records ===")
    print(f"Raw: {raw_path}")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()