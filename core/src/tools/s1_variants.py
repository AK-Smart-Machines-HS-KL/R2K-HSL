#!/usr/bin/env python3
"""S1 experiment materials: variant fragment/sample definitions, A-phase
phrasings, and the sample-balance linter.

No production files are modified. Variants are assembled from:
  - production fragments read from disk (B0 baseline)
  - inline example bodies copied verbatim from production samples_3vs3.txt
  - new examples (NEW-1 last man, NEW-2 through ball, NEW-3 rebound)

Design constraints (S1 amendments):
  - sample count constancy: B2 holds 7 examples by REPLACING (Ex3 teaches
    goalie opp-half kick = over-kick; Ex4 is semantically broken carry)
  - kicker identity rotation, ball-Y balance, dangerous-red rotation
  - B6 grow-arm adds only non-goalie examples (count-vs-content disambiguation)
"""
import json
import math
import os
import re

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
# Example bodies (INPUT/OUTPUT blocks, no headers)
# ex1/ex2/ex5/ex6/ex7 copied VERBATIM from production samples_3vs3.txt (V1)
# ====================================================================

EX_BODIES = {
    "ex1": """INPUT: {"soccer_ball": {"x": -3.8, "y": 0.5}, "blue_1": {"x": -4.0, "y": 0.3}, "blue_2": {"x": -1.5, "y": 0.0}, "blue_3": {"x": 1.0, "y": -1.0}, "red_1": {"x": 0.5, "y": 0.5}, "red_2": {"x": -3.5, "y": 0.5}, "red_3": {"x": 2.0, "y": 1.5}}
OUTPUT: {
  "assignments": {
    "blue_1": {"role": "goalie", "action": "Kick"},
    "blue_2": {"role": "defender", "action": "Move", "x": -1.0, "y": 0.5},
    "blue_3": {"role": "attacker", "action": "Move", "x": 2.5, "y": -0.5}
  }
}""",
    "ex2": """INPUT: {"soccer_ball": {"x": -3.8, "y": 0.2}, "blue_1": {"x": -3.9, "y": 0.2}, "blue_2": {"x": -2.0, "y": 0.5}, "blue_3": {"x": -1.0, "y": -0.5}, "red_1": {"x": 0.0, "y": 0.0}, "red_2": {"x": 1.5, "y": -1.0}, "red_3": {"x": -3.5, "y": 0.3}}
OUTPUT: {
  "assignments": {
    "blue_1": {"role": "goalie", "action": "Kick"},
    "blue_2": {"role": "defender", "action": "Move", "x": -2.0, "y": 0.0},
    "blue_3": {"role": "defender", "action": "Move", "x": 0.0, "y": -0.5}
  }
}""",
    "ex5": """INPUT: {"soccer_ball": {"x": -2.0, "y": 0.5}, "blue_1": {"x": -4.0, "y": 0.0}, "blue_2": {"x": -2.5, "y": 0.5}, "blue_3": {"x": -1.5, "y": -0.5}, "red_1": {"x": -1.8, "y": 0.6}, "red_2": {"x": -0.5, "y": -1.5}, "red_3": {"x": 0.5, "y": 1.5}}
OUTPUT: {
  "assignments": {
    "blue_1": {"role": "goalie", "action": "Move", "x": -4.0, "y": 0.5},
    "blue_2": {"role": "attacker", "action": "Kick"},
    "blue_3": {"role": "defender", "action": "Move", "x": -2.5, "y": -0.5}
  }
}""",
    "ex6": """INPUT: {"soccer_ball": {"x": 0.5, "y": -1.0}, "blue_1": {"x": -4.0, "y": 0.0}, "blue_2": {"x": 0.0, "y": 1.5}, "blue_3": {"x": 0.3, "y": -0.9}, "red_1": {"x": 2.5, "y": 0.0}, "red_2": {"x": 1.5, "y": -1.0}, "red_3": {"x": 3.5, "y": 1.0}}
OUTPUT: {
  "assignments": {
    "blue_1": {"role": "goalie", "action": "Move", "x": -4.0, "y": -0.3},
    "blue_2": {"role": "defender", "action": "Move", "x": -1.0, "y": 0.5},
    "blue_3": {"role": "attacker", "action": "Kick"}
  }
}""",
    "ex7": """INPUT: {"soccer_ball": {"x": 1.0, "y": 0.0}, "blue_1": {"x": -4.0, "y": 0.0}, "blue_2": {"x": 0.8, "y": 0.2}, "blue_3": {"x": 3.0, "y": -1.0}, "red_1": {"x": 4.0, "y": 1.5}, "red_2": {"x": -1.0, "y": 0.0}, "red_3": {"x": 2.0, "y": 0.5}}
OUTPUT: {
  "assignments": {
    "blue_1": {"role": "goalie", "action": "Move", "x": -4.0, "y": 0.0},
    "blue_2": {"role": "attacker", "action": "Kick", "target_x": 3.0, "target_y": -1.0},
    "blue_3": {"role": "attacker", "action": "Move", "x": 3.5, "y": -1.0}
  }
}""",
    # NEW-1: last man holds deep while two attack (blue_3 = last man,
    # counteracts production blue_3=attacker stereotype; ball Y negative)
    "new1": """INPUT: {"soccer_ball": {"x": 2.0, "y": -0.8}, "blue_1": {"x": -4.0, "y": 0.0}, "blue_2": {"x": 1.8, "y": -0.9}, "blue_3": {"x": -1.5, "y": -0.3}, "red_1": {"x": 1.0, "y": 0.0}, "red_2": {"x": 1.4, "y": -1.7}, "red_3": {"x": 3.0, "y": 1.5}}
OUTPUT: {
  "assignments": {
    "blue_1": {"role": "goalie", "action": "Move", "x": -4.0, "y": -0.4},
    "blue_2": {"role": "attacker", "action": "Kick"},
    "blue_3": {"role": "defender", "action": "Move", "x": -2.0, "y": -0.4}
  }
}""",
    # NEW-2: through ball into space behind the red line (kick into SPACE,
    # not to a teammate — covers self-pass + through-ball mechanism)
    "new2": """INPUT: {"soccer_ball": {"x": 0.8, "y": -0.3}, "blue_1": {"x": -4.0, "y": 0.0}, "blue_2": {"x": -0.5, "y": -1.2}, "blue_3": {"x": 0.7, "y": -0.2}, "red_1": {"x": 2.0, "y": 0.3}, "red_2": {"x": 2.2, "y": -0.5}, "red_3": {"x": 0.3, "y": 0.8}}
OUTPUT: {
  "assignments": {
    "blue_1": {"role": "goalie", "action": "Move", "x": -4.0, "y": -0.2},
    "blue_2": {"role": "attacker", "action": "Move", "x": 2.5, "y": -0.8},
    "blue_3": {"role": "attacker", "action": "Kick", "target_x": 3.2, "target_y": -0.6}
  }
}""",
    # NEW-3 (B6 grow-arm only): rebound positioning after a shot
    "new3": """INPUT: {"soccer_ball": {"x": 3.8, "y": 0.3}, "blue_1": {"x": -4.0, "y": 0.0}, "blue_2": {"x": 3.6, "y": 0.2}, "blue_3": {"x": 1.5, "y": -1.0}, "red_1": {"x": 4.3, "y": 0.2}, "red_2": {"x": 2.0, "y": 0.8}, "red_3": {"x": 2.5, "y": -1.5}}
OUTPUT: {
  "assignments": {
    "blue_1": {"role": "goalie", "action": "Move", "x": -4.0, "y": 0.2},
    "blue_2": {"role": "attacker", "action": "Kick"},
    "blue_3": {"role": "attacker", "action": "Move", "x": 3.0, "y": -0.8}
  }
}""",
    # NEW-2b: through ball with BLUE_2 kicker (steal-safe identity: with-target
    # kicks live only on blue_2, matching ex7). Attack-side coverage.
    "new2b": """INPUT: {"soccer_ball": {"x": 0.8, "y": -0.3}, "blue_1": {"x": -4.0, "y": 0.0}, "blue_2": {"x": 0.7, "y": -0.2}, "blue_3": {"x": -0.5, "y": -1.2}, "red_1": {"x": 2.0, "y": 0.3}, "red_2": {"x": 2.2, "y": -0.5}, "red_3": {"x": 0.3, "y": 0.8}}
OUTPUT: {
  "assignments": {
    "blue_1": {"role": "goalie", "action": "Move", "x": -4.0, "y": -0.2},
    "blue_2": {"role": "attacker", "action": "Kick", "target_x": 3.2, "target_y": -0.6},
    "blue_3": {"role": "attacker", "action": "Move", "x": 2.5, "y": -0.8}
  }
}""",
    # NEW-3b (B11): rebound with REVERSED kicker identity (blue_3 shoots,
    # blue_2 takes rebound position) — keeps rebound concept with zero
    # blue_3-kicks-with-target examples (steal-anomaly isolation arm).
    "new3b": """INPUT: {"soccer_ball": {"x": 3.8, "y": 0.3}, "blue_1": {"x": -4.0, "y": 0.0}, "blue_2": {"x": 1.5, "y": -1.0}, "blue_3": {"x": 3.6, "y": 0.2}, "red_1": {"x": 4.3, "y": 0.2}, "red_2": {"x": 2.0, "y": 0.8}, "red_3": {"x": 2.5, "y": -1.5}}
OUTPUT: {
  "assignments": {
    "blue_1": {"role": "goalie", "action": "Move", "x": -4.0, "y": 0.2},
    "blue_2": {"role": "attacker", "action": "Move", "x": 3.0, "y": -0.8},
    "blue_3": {"role": "attacker", "action": "Kick"}
  }
}""",
    # NEW-4: REVERSED pass (blue_3 carrier -> blue_2 receiver). Y-mirrored
    # vs the pc_02 TEST situation (ball Y +0.8 vs test's -1.2) so the probe
    # measures identity-pattern transfer, not memorization.
    "new4": """INPUT: {"soccer_ball": {"x": 0.8, "y": 0.8}, "blue_1": {"x": -4.0, "y": 0.0}, "blue_2": {"x": 2.8, "y": -1.2}, "blue_3": {"x": 0.7, "y": 0.7}, "red_1": {"x": 1.8, "y": 1.2}, "red_2": {"x": -1.0, "y": -0.5}, "red_3": {"x": 4.0, "y": 0.8}}
OUTPUT: {
  "assignments": {
    "blue_1": {"role": "goalie", "action": "Move", "x": -4.0, "y": 0.3},
    "blue_2": {"role": "attacker", "action": "Move", "x": 3.2, "y": -1.2},
    "blue_3": {"role": "attacker", "action": "Kick", "target_x": 2.8, "target_y": -1.2}
  }
}""",
    # NEW-5: 3rd goalie-clearance anchor (crisis: red_3 pressing hard, ball
    # deep in own goal-area corner, ball Y negative — diverse vs ex1/ex2).
    # Own-half ONLY — must not reintroduce the opp-half over-kick pattern.
    "new5": """INPUT: {"soccer_ball": {"x": -3.9, "y": -1.3}, "blue_1": {"x": -4.2, "y": -1.1}, "blue_2": {"x": -1.2, "y": 0.0}, "blue_3": {"x": 0.0, "y": 1.0}, "red_1": {"x": 1.0, "y": 0.0}, "red_2": {"x": 1.5, "y": 1.5}, "red_3": {"x": -3.5, "y": -1.4}}
OUTPUT: {
  "assignments": {
    "blue_1": {"role": "goalie", "action": "Kick"},
    "blue_2": {"role": "defender", "action": "Move", "x": -1.5, "y": -0.5},
    "blue_3": {"role": "defender", "action": "Move", "x": 0.0, "y": 0.5}
  }
}""",
    # B1z minimal neutral samples (format anchoring only — no tactical pattern)
    "m1": """INPUT: {"soccer_ball": {"x": 4.0, "y": 2.5}, "blue_1": {"x": -4.0, "y": 0.0}, "blue_2": {"x": -0.5, "y": 0.0}, "blue_3": {"x": -1.5, "y": -1.0}, "red_1": {"x": 2.0, "y": 1.5}, "red_2": {"x": 3.0, "y": -1.0}, "red_3": {"x": 1.0, "y": 0.5}}
OUTPUT: {
  "assignments": {
    "blue_1": {"role": "goalie", "action": "Move", "x": -4.0, "y": 0.5},
    "blue_2": {"role": "defender", "action": "Move", "x": 1.0, "y": 0.5},
    "blue_3": {"role": "attacker", "action": "Move", "x": 0.0, "y": -1.0}
  }
}""",
    "m2": """INPUT: {"soccer_ball": {"x": 0.5, "y": 0.0}, "blue_1": {"x": -4.0, "y": 0.0}, "blue_2": {"x": 0.4, "y": 0.1}, "blue_3": {"x": -1.5, "y": 1.0}, "red_1": {"x": 2.0, "y": 0.5}, "red_2": {"x": 1.0, "y": -1.5}, "red_3": {"x": 3.0, "y": 1.0}}
OUTPUT: {
  "assignments": {
    "blue_1": {"role": "goalie", "action": "Move", "x": -4.0, "y": 0.0},
    "blue_2": {"role": "attacker", "action": "Kick"},
    "blue_3": {"role": "defender", "action": "Move", "x": 0.0, "y": 1.0}
  }
}""",
    "m3": """INPUT: {"soccer_ball": {"x": 2.0, "y": 1.0}, "blue_1": {"x": -4.0, "y": 0.0}, "blue_2": {"x": -0.5, "y": 0.0}, "blue_3": {"x": 1.8, "y": 1.1}, "red_1": {"x": 3.0, "y": 0.5}, "red_2": {"x": 1.0, "y": -1.0}, "red_3": {"x": 2.5, "y": 2.0}}
OUTPUT: {
  "assignments": {
    "blue_1": {"role": "goalie", "action": "Move", "x": -4.0, "y": 0.5},
    "blue_2": {"role": "defender", "action": "Move", "x": 0.5, "y": 0.0},
    "blue_3": {"role": "attacker", "action": "Kick"}
  }
}""",
}

# ====================================================================
# Header sets (per variant wording style — bodies shared)
# ====================================================================

HEADERS_NEUTRAL = {
    "ex1": "GOALIE CLEARANCE (goalie closest, ball deep in own zone)",
    "ex2": "GOALIE CLOSEST, BALL DEEP IN OWN ZONE",
    "ex5": "ALL BOTS BEHIND THE BALL (DEFENDING)",
    "ex6": "BLUE_3 CLOSEST TO BALL",
    "ex7": "PASS TO FREE TEAMMATE (blue_2 passes to blue_3 in opponent half)",
    "new1": "LAST MAN HOLDS DEEP WHILE TWO ATTACK",
    "new2": "THROUGH BALL INTO SPACE BEHIND THE RED LINE",
    "new2b": "THROUGH BALL INTO SPACE BEHIND THE RED LINE",
    "new3": "REBOUND POSITIONING AFTER A SHOT",
    "new3b": "REBOUND POSITIONING AFTER A SHOT",
    "new4": "PASS TO FREE TEAMMATE (blue_3 passes to blue_2 in opponent half)",
    "new5": "GOALIE CLEARANCE UNDER PRESSURE (ball deep in own goal area)",
    "m1": "REPOSITIONING",
    "m2": "CLOSEST BOT KICKS",
    "m3": "GOALIE STAYS ON THE LINE",
}

HEADERS_NARRATIVE = {
    "ex1": "THE GOALIE IS CLOSEST TO A DANGEROUS BALL — THE GOALIE CLEARS",
    "ex2": "THE GOALIE IS CLOSEST IN OUR HALF — THE GOALIE KICKS TO CLEAR",
    "ex5": "ALL BLUE BOTS ARE BEHIND THE BALL — THE CLOSEST BOT CONTESTS",
    "ex6": "BLUE_3 IS CLOSEST TO THE BALL — BLUE_3 KICKS",
    "ex7": "BLUE_3 IS THE FREE MAN IN THE OPPONENT HALF — BLUE_2 PASSES TO HIM",
    "new1": "BLUE ATTACKS WITH TWO BOTS — BLUE_3 IS THE LAST MAN AND STAYS DEEP",
    "new2": "THE RED LINE IS HIGH — BLUE_2 KICKS INTO THE SPACE BEHIND IT AND BLUE_3 RUNS",
    "new3": "A SHOT IS GOING IN — BLUE_3 MOVES CLOSE FOR THE REBOUND",
}

HEADERS_ZONES = {
    "ex1": "GOALIE CLEARANCE (ball in the own goal area)",
    "ex2": "GOALIE CLOSEST IN THE OWN GOAL AREA",
    "ex5": "DEFENDING IN THE OWN HALF",
    "ex6": "BLUE_3 CLOSEST TO BALL IN MIDFIELD",
    "ex7": "PASS TO THE FREE MAN ON THE RIGHT WING",
    "new1": "LAST MAN HOLDS THE OWN HALF WHILE TWO ATTACK",
    "new2": "THROUGH BALL INTO THE SPACE BEHIND THE RED LINE",
    "new3": "REBOUND POSITIONING IN THE OPPONENT GOAL AREA",
}


def compose_samples(keys, header_map):
    """Compose full samples text from example keys + header map (renumbers 1..N)."""
    chunks = []
    for i, k in enumerate(keys, 1):
        chunks.append(f"--- EXAMPLE {i}: {header_map[k]} ---\n{EX_BODIES[k]}")
    return "\n".join(chunks)


# ====================================================================
# Rule additions
# ====================================================================

RULES_NEW = """
- LAST MAN: When two blue bots attack in the opponent half, the deepest blue field bot stays between the ball and your own goal (around X=-2.0). It does NOT join the attack.
- SHORTEN THE ANGLE: When a red bot has the ball near your goal, the closest blue defender moves onto the line between the ball and your own goal (X=-4.5). This shortens the red shooting angle.
- KICK INTO SPACE: You can kick the ball into open space instead of passing to a teammate. Set target_x/target_y to a point in open space ahead of a running blue bot (or ahead of the kicker). The blue bots run to the ball there.
- REBOUND: When a blue bot shoots at the opponent goal, another blue bot moves near the opponent goal area (X=3.0 to 4.0) and waits for the rebound.
- WING STRETCH: When red bots crowd the center, move one blue bot to the open wing (Y above 1.5 or below -1.5) to stretch the red defense."""

RULES_NEW_ZONES = """
- LAST MAN: When two blue bots attack in the opponent half, the deepest blue field bot stays in the own half between the ball and the own goal area. It does NOT join the attack.
- SHORTEN THE ANGLE: When a red bot has the ball near the own goal area, the closest blue defender moves onto the line between the ball and the own goal. This shortens the red shooting angle.
- KICK INTO SPACE: You can kick the ball into open space instead of passing to a teammate. Set target_x/target_y to a point in open space ahead of a running blue bot (or ahead of the kicker). The blue bots run to the ball there.
- REBOUND: When a blue bot shoots, another blue bot moves into the opponent goal area and waits for the rebound.
- WING STRETCH: When red bots crowd the midfield, move one blue bot to the open wing to stretch the red defense."""

RULES_NEW_NOSPACE = """
- LAST MAN: When two blue bots attack in the opponent half, the deepest blue field bot stays between the ball and your own goal (around X=-2.0). It does NOT join the attack.
- SHORTEN THE ANGLE: When a red bot has the ball near your goal, the closest blue defender moves onto the line between the ball and your own goal (X=-4.5). This shortens the red shooting angle.
- REBOUND: When a blue bot shoots at the opponent goal, another blue bot moves near the opponent goal area (X=3.0 to 4.0) and waits for the rebound.
- WING STRETCH: When red bots crowd the center, move one blue bot to the open wing (Y above 1.5 or below -1.5) to stretch the red defense."""

GLOSSARY = """
FIELD ZONES: Own goal area = X from -4.5 to -3.5 and Y from -1.0 to 1.0. Opponent goal area = X from 3.5 to 4.5 and Y from -1.0 to 1.0. Midfield = X from -1.5 to 1.5. Left wing = Y above 1.5. Right wing = Y below -1.5."""

# ====================================================================
# Variant registry
# B0  production control (V1 samples, current rules)
# B1  rules-only addition (production samples untouched)
# B1z rules-only + minimal neutral samples (3) — rules-without-pattern arm
# B2  samples-replaced (7): ex1,ex2,ex5,ex6,ex7 + new1,new2; production rules
# B3  B2 samples + B1 rules
# B4  zone glossary: glossary in rules_core + zone rules + zone headers
# B5  wording: B2 bodies + narrative headers + B1 rules
# B6  grow-arm: B2 + new3 (8 samples) + B1 rules — count-vs-content test
# ====================================================================

SAMPLES_B2_KEYS = ["ex1", "ex2", "ex5", "ex6", "ex7", "new1", "new2"]
SAMPLES_B6_KEYS = ["ex1", "ex2", "ex5", "ex6", "ex7", "new1", "new2", "new3"]
SAMPLES_B9_KEYS = ["ex1", "ex2", "ex5", "ex6", "ex7", "new1", "new2", "new3", "new4"]
SAMPLES_B9G_KEYS = ["ex1", "ex2", "ex5", "ex6", "ex7", "new1", "new2", "new3", "new5"]
SAMPLES_B10_KEYS = ["ex1", "ex2", "ex5", "ex6", "ex7", "new1", "new2", "new3", "new4", "new5"]
SAMPLES_B11_KEYS = ["ex1", "ex2", "ex5", "ex6", "ex7", "new1", "new3b", "new5"]
SAMPLES_B12_KEYS = ["ex1", "ex2", "ex5", "ex6", "ex7", "new1", "new2b", "new3b", "new5"]
SAMPLES_B13_KEYS = ["ex1", "ex2", "ex5", "ex6", "ex7", "new1", "new2b", "new3b"]
SAMPLES_MIN_KEYS = ["m1", "m2", "m3"]


def get_variants():
    """Return dict: variant key -> {header, rules_core, rules_mode, samples}."""
    header_prod = read_frag("header.txt")
    rules_core_prod = read_frag("rules_core.txt")
    rules_3vs3_prod = read_frag("rules_3vs3.txt")
    samples_prod = read_frag("samples_3vs3.txt")

    samples_b2 = compose_samples(SAMPLES_B2_KEYS, HEADERS_NEUTRAL)
    samples_b5 = compose_samples(SAMPLES_B2_KEYS, HEADERS_NARRATIVE)
    samples_b6 = compose_samples(SAMPLES_B6_KEYS, HEADERS_NEUTRAL)
    samples_b4 = compose_samples(SAMPLES_B2_KEYS, HEADERS_ZONES)
    samples_min = compose_samples(SAMPLES_MIN_KEYS, HEADERS_NEUTRAL)
    samples_b9 = compose_samples(SAMPLES_B9_KEYS, HEADERS_NEUTRAL)
    samples_b9g = compose_samples(SAMPLES_B9G_KEYS, HEADERS_NEUTRAL)
    samples_b10 = compose_samples(SAMPLES_B10_KEYS, HEADERS_NEUTRAL)
    samples_b11 = compose_samples(SAMPLES_B11_KEYS, HEADERS_NEUTRAL)
    samples_b12 = compose_samples(SAMPLES_B12_KEYS, HEADERS_NEUTRAL)
    samples_b13 = compose_samples(SAMPLES_B13_KEYS, HEADERS_NEUTRAL)

    variants = {
        "B0": {"header": header_prod, "rules_core": rules_core_prod,
               "rules_mode": rules_3vs3_prod, "samples": samples_prod,
               "desc": "production control (V1 samples + current rules)"},
        "B1": {"header": header_prod, "rules_core": rules_core_prod,
               "rules_mode": rules_3vs3_prod + RULES_NEW, "samples": samples_prod,
               "desc": "rules-only addition (5 new-concept rules)"},
        "B1z": {"header": header_prod, "rules_core": rules_core_prod,
                "rules_mode": rules_3vs3_prod + RULES_NEW, "samples": samples_min,
                "desc": "rules-only + 3 minimal neutral samples (no pattern anchoring)"},
        "B2": {"header": header_prod, "rules_core": rules_core_prod,
               "rules_mode": rules_3vs3_prod, "samples": samples_b2,
               "desc": "samples-replaced (7: 5 kept + last-man + through-ball)"},
        "B3": {"header": header_prod, "rules_core": rules_core_prod,
               "rules_mode": rules_3vs3_prod + RULES_NEW, "samples": samples_b2,
               "desc": "B2 samples + B1 rules combined"},
        "B4": {"header": header_prod, "rules_core": rules_core_prod + GLOSSARY,
               "rules_mode": rules_3vs3_prod + RULES_NEW_ZONES, "samples": samples_b4,
               "desc": "zone glossary + zone-term rules + zone headers (B2 bodies)"},
        "B5": {"header": header_prod, "rules_core": rules_core_prod,
               "rules_mode": rules_3vs3_prod + RULES_NEW, "samples": samples_b5,
               "desc": "B2 bodies + narrative situation headers + B1 rules"},
        "B6": {"header": header_prod, "rules_core": rules_core_prod,
               "rules_mode": rules_3vs3_prod + RULES_NEW, "samples": samples_b6,
               "desc": "grow-arm: B2 + rebound example (8 total, non-goalie add)"},
        "B7": {"header": header_prod, "rules_core": rules_core_prod,
               "rules_mode": rules_3vs3_prod, "samples": samples_b6,
               "desc": "samples-only grow: B2 + rebound example (8), production rules"},
        "B8": {"header": header_prod, "rules_core": rules_core_prod,
               "rules_mode": rules_3vs3_prod + RULES_NEW_NOSPACE, "samples": samples_b2,
               "desc": "B2 samples + rules WITHOUT kick-into-space rule"},
        "B9": {"header": header_prod, "rules_core": rules_core_prod,
               "rules_mode": rules_3vs3_prod, "samples": samples_b9,
               "desc": "B7 + reversed-pass example (9) — pass generalization fix"},
        "B9g": {"header": header_prod, "rules_core": rules_core_prod,
                "rules_mode": rules_3vs3_prod, "samples": samples_b9g,
                "desc": "B7 + 3rd goalie-clearance anchor (9) — goalie ratio fix"},
        "B10": {"header": header_prod, "rules_core": rules_core_prod,
                "rules_mode": rules_3vs3_prod, "samples": samples_b10,
                "desc": "B7 + reversed-pass + goalie anchor (10) — both fixes"},
        "B11": {"header": header_prod, "rules_core": rules_core_prod,
                "rules_mode": rules_3vs3_prod, "samples": samples_b11,
                "desc": "B9g minus through-ball, rebound kicker swapped (9) — steal isolation"},
        "B12": {"header": header_prod, "rules_core": rules_core_prod,
                "rules_mode": rules_3vs3_prod, "samples": samples_b12,
                "desc": "3 goalie anchors + 4 attack kicks, targets only on blue_2 (9) — synthesis"},
        "B13": {"header": header_prod, "rules_core": rules_core_prod,
                "rules_mode": rules_3vs3_prod, "samples": samples_b13,
                "desc": "B7 with steal-safe kicker identities (8), 2 goalie anchors — no new5"},
        "B7HN": {"header": HEADER_NEUTRAL_PERSONA,
                 "rules_core": rules_core_prod,
                 "rules_mode": rules_3vs3_prod, "samples": samples_b6,
                 "desc": "B7 samples + neutral header persona (aggressive->neutral)"},
    }
    return variants


# ====================================================================
# A-phase materials
# ====================================================================

# Bare system prompt for A2 (emergence) / A3 (term-vs-coords) — no rules,
# no samples, no persona beyond team/direction. Format anchored with ONE
# concrete neutral example (all-Move, no kick/pass — pure format anchor;
# the "..." placeholder schema caused 62% literal echo garbage in pilot).
BARE_SYS = """You are a soccer AI for the Blue Team. Blue attacks toward X=4.5 (the opponent goal). Blue defends X=-4.5 (the own goal).
FIELD LIMITS: X is between -4.5 and 4.5. Y is between -3.0 and 3.0.
Output ONLY pure, raw JSON. Do NOT wrap the output in markdown code blocks.
VALID ACTIONS:
1. {"action": "Move", "x": float, "y": float}
2. {"action": "Kick"}
3. {"action": "Kick", "target_x": float, "target_y": float}
Output ONLY JSON in exactly this format with all three blue bots, with concrete values instead of the example values:
{"assignments": {"blue_1": {"role": "goalie", "action": "Move", "x": -4.0, "y": 0.0}, "blue_2": {"role": "attacker", "action": "Move", "x": 0.0, "y": 0.0}, "blue_3": {"role": "defender", "action": "Move", "x": 0.0, "y": 1.5}}}"""

A1_TERMS = [
    "last man",
    "shortening the shooting angle",
    "self-pass (kick and run)",
    "through ball",
    "rebound",
    "free man",
    "midfield",
    "goal area",
    "wing",
    "cover",
]

A1_PROMPT = ('In soccer, what does the term "{term}" mean? Describe in 3 sentences '
             'how a small wheeled robot (no hands, 9x6 m field, moves to X,Y '
             'coordinates, kicks the ball in a chosen direction) could execute it.')

# A3: one case per concept. 'term' = jargon instruction, 'coord' = explicit
# coordinate instruction. Both appended to the bare-prompt user turn.
A3_CASES = [
    {"label": "lm_01", "bot": "blue_3",
     "term": "blue_3 stays back as the last man while the other two blue bots attack",
     "coord": "blue_3 holds the position (-2.0, -0.3)",
     "check": {"t": "move_near", "expect": [-2.0, -0.3], "radius": 1.2}},
    {"label": "sa_01", "bot": "blue_2",
     "term": "blue_2 shortens the shooting angle on the red ball carrier",
     "coord": "blue_2 moves to (-3.2, 0.5)",
     "check": {"t": "move_near", "expect": [-3.2, 0.5], "radius": 1.2}},
    {"label": "sp_01", "bot": "blue_2",
     "term": "blue_2 plays the ball into the space ahead and runs onto it",
     "coord": "blue_2 kicks the ball to (2.5, 0.0)",
     "check": {"t": "kick_forward", "min_target_x": 1.5}},
    {"label": "tb_01", "bot": "blue_2",
     "term": "blue_2 plays a through ball into the space behind the red defensive line for blue_3 to run onto",
     "coord": "blue_2 kicks the ball to (3.2, -0.6)",
     "check": {"t": "kick_target_near", "expect": [3.2, -0.6], "radius": 1.2}},
    {"label": "rb_01", "bot": "blue_3",
     "term": "blue_3 gets ready for the rebound after the shot",
     "coord": "blue_3 moves to (3.0, -0.8)",
     "check": {"t": "move_near", "expect": [3.0, -0.8], "radius": 1.2}},
    {"label": "pc_01", "bot": "blue_2",
     "term": "blue_2 passes to the free man blue_3",
     "coord": "blue_2 passes to (3.0, -1.0)",
     "check": {"t": "kick_target_near", "expect": [3.0, -1.0], "radius": 1.2}},
    {"label": "mf_01", "bot": "blue_3",
     "term": "blue_3 holds the midfield",
     "coord": "blue_3 moves to (0.0, 0.0)",
     "check": {"t": "move_near", "expect": [0.0, 0.0], "radius": 1.2}},
    {"label": "ga_01", "bot": "blue_3",
     "term": "blue_3 drops into the goal area to defend",
     "coord": "blue_3 moves to (-3.8, 0.4)",
     "check": {"t": "move_near", "expect": [-3.8, 0.4], "radius": 1.2}},
    {"label": "ws_01", "bot": "blue_3",
     "term": "blue_3 moves to the open wing",
     "coord": "blue_3 moves to (1.0, -2.2)",
     "check": {"t": "target_in_zone", "y_abs_ge": 1.5, "x_ge": 0.0}},
    {"label": "sa_02", "bot": "blue_3",
     "term": "blue_3 covers the lane between the ball and the goal",
     "coord": "blue_3 moves to (-3.5, -0.6)",
     "check": {"t": "move_near", "expect": [-3.5, -0.6], "radius": 1.2}},
]

# A4: persona arm — header line 1 swapped, rest identical
HEADER_NEUTRAL_PERSONA = """You are a soccer AI for the Blue Team.
Output ONLY pure, raw JSON.
Do NOT wrap the output in markdown code blocks. Do NOT include any conversational text.
{{EXPLAIN_INSTRUCTION}}"""


# ====================================================================
# Sample-balance linter
# ====================================================================

def _extract_json_after(text, marker):
    idx = text.find(marker)
    if idx == -1:
        return None
    brace_count = 0
    start = -1
    for i in range(idx + len(marker), len(text)):
        c = text[i]
        if c == "{":
            if brace_count == 0:
                start = i
            brace_count += 1
        elif c == "}":
            brace_count -= 1
            if brace_count == 0:
                try:
                    return json.loads(text[start:i + 1])
                except Exception:
                    return None
    return None


def parse_examples(samples_text):
    """Parse a samples file into [{header, input, output}] triples."""
    exs = []
    lines = samples_text.split("\n")
    current = None
    for ln in lines:
        m = re.match(r"^---\s*EXAMPLE\s+\d+:\s*(.*?)\s*---$", ln)
        if m:
            if current:
                exs.append(current)
            current = {"header": m.group(1), "text": ""}
        elif current is not None:
            current["text"] += ln + "\n"
    if current:
        exs.append(current)
    for e in exs:
        e["input"] = _extract_json_after(e["text"], "INPUT:")
        e["output"] = _extract_json_after(e["text"], "OUTPUT:")
        if e.get("output") and "assignments" in e["output"]:
            e["output"] = e["output"]["assignments"]
    return exs


def lint_samples(samples_text, name):
    """Check sample-set balance. Returns (report_dict, violations_list)."""
    exs = parse_examples(samples_text)
    exs = [e for e in exs if e.get("input") and e.get("output")]
    n = len(exs)
    kickers, roles, ball_y, danger_red, goalie_kicks = {}, {}, [], {}, 0
    ent_counts = []
    for e in exs:
        inp, out = e["input"], e["output"]
        ball = inp.get("soccer_ball", {})
        ball_y.append(ball.get("y", 0.0))
        ent_counts.append(len(inp))
        nearest_red, nd = None, 1e9
        for k, v in inp.items():
            if k.startswith("red"):
                d = math.hypot(v["x"] - ball.get("x", 0), v["y"] - ball.get("y", 0))
                if d < nd:
                    nd, nearest_red = d, k
        if nearest_red:
            danger_red[nearest_red] = danger_red.get(nearest_red, 0) + 1
        for bot, a in out.items():
            act = str(a.get("action", "")).lower()
            role = str(a.get("role", "")).lower()
            roles[(bot, role)] = roles.get((bot, role), 0) + 1
            if act == "kick":
                kickers[bot] = kickers.get(bot, 0) + 1
                if role == "goalie":
                    goalie_kicks += 1
    pos_y = sum(1 for y in ball_y if y > 0.05)
    neg_y = sum(1 for y in ball_y if y < -0.05)
    report = {
        "name": name, "n_examples": n,
        "kickers": kickers, "goalie_kicks": goalie_kicks,
        "roles": {f"{b}:{r}": c for (b, r), c in sorted(roles.items())},
        "ball_y_pos": pos_y, "ball_y_neg": neg_y,
        "danger_red": danger_red,
        "entity_counts": ent_counts,
    }
    violations = []
    if n >= 5:
        for b in ("blue_1", "blue_2", "blue_3"):
            k = kickers.get(b, 0)
            if k > max(2, n // 2):
                violations.append(f"kicker imbalance: {b} kicks {k}/{n}")
            if b != "blue_1" and k == 0:
                violations.append(f"{b} never kicks")
        if abs(pos_y - neg_y) > 2:
            violations.append(f"ball Y bias: {pos_y} pos vs {neg_y} neg")
        dr = [danger_red.get(f"red_{i}", 0) for i in (1, 2, 3)]
        if max(dr) > n // 2:
            violations.append(f"dangerous-red concentration: red_1={dr[0]} red_2={dr[1]} red_3={dr[2]}")
        if any(c != 7 for c in ent_counts):
            violations.append(f"entity count != 7 in some examples: {ent_counts}")
        # role-per-bot stereotyping (non-goalie)
        for b in ("blue_2", "blue_3"):
            att = roles.get((b, "attacker"), 0)
            dfn = roles.get((b, "defender"), 0)
            if max(att, dfn) > n * 0.7:
                violations.append(f"role stereotype: {b} attacker={att} defender={dfn} of {n}")
    return report, violations
