#!/usr/bin/env python3
"""SP experiment materials: spinning-fix variants (SP0-SP4).

Prompt-only spinning fix — NO bridge/evaluator changes, no production files
modified. Variants are assembled from:
  - production fragments read from disk (B13 samples currently applied)
  - SP rule additions / Hold-action rules (inline strings)
  - SP4: B13 sample bodies with non-kicker Move targets moved onto
    ball-relative geometry (kicker identities + goalie anchors untouched)

Design per docs/v7/sp_spinning_fix_plan.md:
  SP0  control (B13 as-is)
  SP1  + DEFAULT POSITIONING rule (ball-relative anchoring)
  SP2t + Hold action in VALID ACTIONS, tight gate
  SP2l + Hold action in VALID ACTIONS, loose gate
  SP3  SP1 + better of SP2t/SP2l (built after sequence probe round 1)
  SP4  B13 samples reworked onto ball-relative geometry
"""
import math
import os

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.join(TOOLS_DIR, "..")
FRAG_DIR = os.path.join(BASE_DIR, "strategy", "fragments")


def read_frag(name):
    try:
        with open(os.path.join(FRAG_DIR, name)) as f:
            return f.read()
    except FileNotFoundError:
        return ""


# ====================================================================
# SP rule additions (appended to rules_3vs3.txt unless noted)
# ====================================================================

RULE_SP1 = """
- DEFAULT POSITIONING: A blue field bot that is not kicking and not covering the goal line positions itself on the line between the ball and your own goal, 1.5m away from the ball. Compute the position from the ball's X,Y in the INPUT: the target is the ball position moved 1.5m toward your own goal (X=-4.5). This position is the default for every bot without a more specific duty."""

# Hold action added to VALID ACTIONS in rules_core.txt
RULES_CORE_HOLD = """4. {"action": "Hold"} — Stay exactly where you are. Do not move."""

RULE_SP2T = """
- HOLD (use carefully): A bot outputs Hold ONLY when it is already within 1m of its correct position (its ball-relative position between ball and own goal, or the goal line for the goalie) AND the ball is more than 2m away from it. Otherwise it outputs a Move."""

RULE_SP2L = """
- HOLD: A bot that is already in a good position outputs Hold and stays there. Do not output small corrective moves for a bot that is roughly where it should be."""


# ====================================================================
# SP4: B13 sample bodies with ball-relative non-kicker targets.
# Kicker assignments, goalie Kick anchors, and the goalie role rows are
# IDENTICAL to B13 — only non-kicker Move targets move onto the
# ball<->own-goal axis (the "default positioning" geometry, 1.5m from ball
# on the ball side, clamped to field).
# ====================================================================

def _ball_relative_target(ball_x, ball_y, dist=1.5):
    """Point on the ball -> own-goal(-4.5,0) axis, `dist` meters from ball."""
    gx, gy = -4.5, 0.0
    dx, dy = gx - ball_x, gy - ball_y
    n = math.hypot(dx, dy)
    if n < 1e-6:
        return ball_x, ball_y
    tx, ty = ball_x + dx / n * dist, ball_y + dy / n * dist
    return round(max(-4.5, min(4.5, tx)), 1), round(max(-3.0, min(3.0, ty)), 1)


def _retarget_non_kickers(body):
    """Rewrite one B13 example body: every non-kick, non-goalie-row Move
    target becomes the ball-relative default. Goalie rows and Kick rows
    (with or without target) are left untouched."""
    import json
    import re
    lines = body.split("\n")
    m = re.search(r"INPUT: (\{.*\})", lines[0])
    if not m:
        return body
    ents = json.loads(m.group(1))
    bx, by = ents["soccer_ball"]["x"], ents["soccer_ball"]["y"]

    # Parse the OUTPUT JSON block (brace matching from first '{' after OUTPUT:)
    out_idx = body.find("OUTPUT:")
    json_start = body.find("{", out_idx)
    brace = 0
    json_end = -1
    for i in range(json_start, len(body)):
        if body[i] == "{":
            if brace == 0:
                json_start = i
            brace += 1
        elif body[i] == "}":
            brace -= 1
            if brace == 0:
                json_end = i + 1
                break
    if json_end == -1:
        return body
    try:
        data = json.loads(body[json_start:json_end])
    except json.JSONDecodeError:
        return body
    asn = data.get("assignments", data)

    for bot, a in asn.items():
        if not isinstance(a, dict):
            continue
        action = str(a.get("action", "")).lower()
        role = str(a.get("role", "")).lower()
        if action == "move" and role != "goalie":
            tx, ty = _ball_relative_target(bx, by)
            a["x"], a["y"] = tx, ty

    new_json = json.dumps(data, indent=2)
    new_body = body[:json_start] + new_json + body[json_end:]
    return new_body


def build_sp4_samples():
    """Read the current (B13) samples file and retarget non-kicker moves."""
    samples = read_frag("samples_3vs3.txt")
    import re
    # Split into (header_line, body) pairs without losing the preamble
    parts = re.split(r"(?=--- EXAMPLE \d+:)", samples)
    out = []
    for part in parts:
        if not part.strip():
            continue
        m = re.match(r"--- EXAMPLE \d+: .*? ---\n", part)
        if not m:
            out.append(part)
            continue
        header, body = part[:m.end()], part[m.end():]
        out.append(header + _retarget_non_kickers(body))
    return "".join(out)


def get_sp_variants():
    """Return dict: variant key -> {header, rules_core, rules_mode, samples}."""
    header_prod = read_frag("header.txt")
    rules_core_prod = read_frag("rules_core.txt")
    rules_3vs3_prod = read_frag("rules_3vs3.txt")
    samples_b13 = read_frag("samples_3vs3.txt")
    samples_sp4 = build_sp4_samples()

    core_with_hold = rules_core_prod.rstrip() + "\n" + RULES_CORE_HOLD + "\n"

    variants = {
        "SP0": {"header": header_prod, "rules_core": rules_core_prod,
                "rules_mode": rules_3vs3_prod, "samples": samples_b13,
                "desc": "control (B13 as-is)"},
        "SP1": {"header": header_prod, "rules_core": rules_core_prod,
                "rules_mode": rules_3vs3_prod + RULE_SP1, "samples": samples_b13,
                "desc": "+ ball-relative DEFAULT POSITIONING rule"},
        "SP2t": {"header": header_prod, "rules_core": core_with_hold,
                 "rules_mode": rules_3vs3_prod + RULE_SP2T, "samples": samples_b13,
                 "desc": "+ Hold action, tight gate"},
        "SP2l": {"header": header_prod, "rules_core": core_with_hold,
                 "rules_mode": rules_3vs3_prod + RULE_SP2L, "samples": samples_b13,
                 "desc": "+ Hold action, loose gate"},
        "SP4": {"header": header_prod, "rules_core": rules_core_prod,
                "rules_mode": rules_3vs3_prod, "samples": samples_sp4,
                "desc": "B13 samples with ball-relative non-kicker targets"},
    }
    return variants


def get_sp3_variants(hold_rule):
    """Build SP3 after round 1: SP1 + the better Hold gate."""
    v = get_sp_variants()
    sp0 = v["SP0"]
    return {"SP3": {"header": sp0["header"], "rules_core": v["SP2t"]["rules_core"],
                    "rules_mode": sp0["rules_mode"] + RULE_SP1 + hold_rule,
                    "samples": sp0["samples"],
                    "desc": "SP1 + winning Hold gate"}}
