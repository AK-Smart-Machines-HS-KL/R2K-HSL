#!/usr/bin/env python3
"""WIN experiment materials: W1-W6 single-lever arms.

Prompt-only "make blue win" arms per docs/v7/win_experiment_plan.md
(Phase 0 pre-registration, frozen 2026-08-22). NO bridge/evaluator changes,
no production files modified. Arms assemble from s1_variants example bodies
(B13 = current production samples) + one new wing example (W5) + rule
appends (W2/W3/W6).

Arms:
  W1  kicker-anchor samples (all field kicks concentrated on blue_2,
      rebound kicker back to blue_2; blue_3 keeps exactly ONE plain kick)
  W2  goalie-Y quantization rule (samples = B13)
  W3  gated shoot-on-sight rule (samples = B13)
  W4  latency diet: 6 examples (drop new3b + ex5; goalie ratio 2:4)
  W5  wing-attack sample (wing1 replaces ex5, n=8)
  W6  finishing rule (samples = B13)

Usage:
  python3 tools/win_variants.py lint
  python3 tools/win_variants.py write <ARM> <output_path>   # staging file
"""
import os
import sys

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.join(TOOLS_DIR, "..")
sys.path.insert(0, TOOLS_DIR)

import s1_variants as V  # noqa: E402


def read_frag(name):
    try:
        with open(os.path.join(BASE_DIR, "strategy", "fragments", name)) as f:
            return f.read()
    except FileNotFoundError:
        return ""


# ====================================================================
# W5 wing example (new body; all others reuse s1_variants EX_BODIES)
# ====================================================================

WING1_BODY = """INPUT: {"soccer_ball": {"x": 0.5, "y": -0.2}, "blue_1": {"x": -4.0, "y": 0.0}, "blue_2": {"x": 0.4, "y": -0.1}, "blue_3": {"x": 1.5, "y": -1.8}, "red_1": {"x": 1.3, "y": -0.1}, "red_2": {"x": 1.0, "y": 0.8}, "red_3": {"x": 3.0, "y": 0.5}}
OUTPUT: {
  "assignments": {
    "blue_1": {"role": "goalie", "action": "Move", "x": -4.0, "y": -0.1},
    "blue_2": {"role": "attacker", "action": "Kick", "target_x": 3.5, "target_y": -2.0},
    "blue_3": {"role": "attacker", "action": "Move", "x": 3.5, "y": -2.0}
  }
}"""

EXTRA_BODIES = {"wing1": WING1_BODY}

WING_HEADERS = {
    "wing1": "PASS TO THE WING (blue_2 passes to blue_3 attacking the open right wing)",
}


def compose(keys):
    """Compose samples text from s1_variants keys + win-only bodies."""
    bodies = {**V.EX_BODIES, **EXTRA_BODIES}
    headers = {**V.HEADERS_NEUTRAL, **WING_HEADERS}
    chunks = []
    for i, k in enumerate(keys, 1):
        chunks.append(f"--- EXAMPLE {i}: {headers[k]} ---\n{bodies[k]}")
    return "\n".join(chunks)


# ====================================================================
# Rule appends (W2 / W3 / W6)
# ====================================================================

RULE_W2 = """
- GOALIE Y: The goalie's Move target Y equals the ball's Y multiplied by 0.5, rounded to one decimal place. The goalie never uses any other Y value."""

RULE_W3 = """
- SHOOT ON SIGHT: When the ball is in the opponent half (X from 0 to 4.5), the blue bot closest to the ball kicks toward the opponent goal (X=4.5) immediately. Do not reposition first."""

RULE_W6 = """
- FINISHING: When the ball is inside the opponent goal area (X from 3.5 to 4.5, Y from -1.0 to 1.0), the blue bot with the ball kicks at the opponent goal immediately instead of passing."""


# ====================================================================
# Sample-set key lists
# ====================================================================

SAMPLES_W1_KEYS = ["ex1", "ex2", "ex5", "ex6", "ex7", "new1", "new2b", "new3"]
SAMPLES_W4_KEYS = ["ex1", "ex2", "ex6", "ex7", "new1", "new2b"]
SAMPLES_W5_KEYS = ["ex1", "ex2", "wing1", "ex6", "ex7", "new1", "new2b", "new3b"]


def get_win_variants():
    """Return dict: variant key -> {header, rules_core, rules_mode, samples}."""
    header_prod = read_frag("header.txt")
    rules_core_prod = read_frag("rules_core.txt")
    rules_3vs3_prod = read_frag("rules_3vs3.txt")

    samples_b13 = compose(V.SAMPLES_B13_KEYS)
    samples_w1 = compose(SAMPLES_W1_KEYS)
    samples_w4 = compose(SAMPLES_W4_KEYS)
    samples_w5 = compose(SAMPLES_W5_KEYS)

    variants = {
        "W1": {"header": header_prod, "rules_core": rules_core_prod,
               "rules_mode": rules_3vs3_prod, "samples": samples_w1,
               "desc": "kicker-anchor: all field kicks on blue_2 (blue_3 keeps 1)"},
        "W2": {"header": header_prod, "rules_core": rules_core_prod,
               "rules_mode": rules_3vs3_prod + RULE_W2, "samples": samples_b13,
               "desc": "goalie-Y quantization rule (Y = ball Y * 0.5)"},
        "W3": {"header": header_prod, "rules_core": rules_core_prod,
               "rules_mode": rules_3vs3_prod + RULE_W3, "samples": samples_b13,
               "desc": "gated shoot-on-sight rule (opp half X>0)"},
        "W4": {"header": header_prod, "rules_core": rules_core_prod,
               "rules_mode": rules_3vs3_prod, "samples": samples_w4,
               "desc": "latency diet: 6 examples, goalie ratio 2:4"},
        "W5": {"header": header_prod, "rules_core": rules_core_prod,
               "rules_mode": rules_3vs3_prod, "samples": samples_w5,
               "desc": "wing-attack sample (wing1 replaces ex5, n=8)"},
        "W6": {"header": header_prod, "rules_core": rules_core_prod,
               "rules_mode": rules_3vs3_prod + RULE_W6, "samples": samples_b13,
               "desc": "finishing rule (kick over pass in opp goal area)"},
    }
    return variants


# ====================================================================
# CLI: lint / write staging
# ====================================================================

def run_lint():
    """Lint the W sample sets. W1's blue_2 kicker concentration is a
    DELIBERATE design decision (documented lint exception, see plan)."""
    variants = get_win_variants()
    sets = {k: variants[k]["samples"] for k in ("W1", "W4", "W5")}
    # W2/W3/W6 use B13 samples — lint B13 once for reference
    sets["B13_reference"] = variants["W2"]["samples"]
    for name, text in sets.items():
        rep, viol = V.lint_samples(text, name)
        print(f"\n=== {name} (n={rep['n_examples']}) ===")
        print(f"  kickers:        {rep['kickers']}  (goalie-kick examples: {rep['goalie_kicks']})")
        print(f"  roles:          {rep['roles']}")
        print(f"  ball Y:         {rep['ball_y_pos']} pos / {rep['ball_y_neg']} neg")
        print(f"  dangerous red:  {rep['danger_red']}")
        print(f"  entity counts:  {rep['entity_counts']}")
        if viol:
            print(f"  VIOLATIONS: {viol}")
        else:
            print("  no violations")
    print("\nNOTE: accepted lint exceptions (documented in plan pre-registration):")
    print("  W1 'kicker imbalance blue_2 5/8' — deliberate design lever (V0-style anchoring).")
    print("  W5 'role stereotype blue_3 attacker 6/8' — consequence of wing-runner design")
    print("  (ex5 replacement is pre-registered; defending stays covered by new1; the")
    print("  last_man kill criterion guards the anchoring risk directly).")


def run_write(arm, path):
    variants = get_win_variants()
    if arm not in variants:
        print(f"Unknown arm: {arm}. Available: {', '.join(variants)}")
        sys.exit(1)
    with open(path, "w") as f:
        f.write(variants[arm]["samples"])
    print(f"[ok] wrote {arm} samples -> {path}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "lint":
        run_lint()
    elif cmd == "write":
        if len(sys.argv) != 4:
            print("Usage: win_variants.py write <ARM> <output_path>")
            sys.exit(1)
        run_write(sys.argv[2], sys.argv[3])
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
