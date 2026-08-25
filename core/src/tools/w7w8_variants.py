#!/usr/bin/env python3
"""W7/W8 experiment: can samples teach nearest-bot kicking?

User question: blue_3 chases from long distance while blue_2 is better
positioned. Measured: 17% of blue_3 kick assignments have blue_2 closer
(8% outright wasted long chases). Root cause: LLM identity anchoring
(blue_3 = striker, 80% of kicks) + F7 (no distance arithmetic).

Arms (prompt-only, production untouched):
  W7  identity rotation: B13 examples with kicker identity rotated so the
      field-kick split is even (blue_2/blue_3 3:3) — tests whether "any field
      bot can be the kicker" transfers via pattern balance.
      CONSTRAINT preserved: with-target kicks stay ONLY on blue_2 (B13's
      steal-safe rule — blue_3-with-target caused defensive steals in S1).
  W8  nearest-bot illustrations: B13 + 2 new examples where the GEOMETRICALLY
      closest bot takes the kick (one blue_2-closest, one blue_3-closest),
      headers stating the distances. Tests Ex2-style role-swap transfer.
  W78 both combined.

Control: B13 (same session — SP finding 6: cross-session canary flips).
"""
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
# Rotated example bodies (W7). Concepts and geometry preserved from B13;
# only kicker identity + positions swapped so the OTHER bot is closest.
# ====================================================================

# ex5r: DEFENDING — was blue_2 kicks; now blue_3 closest and kicks,
# blue_2 covers. Ball/reds identical to ex5.
EX5R = """INPUT: {"soccer_ball": {"x": -2.0, "y": 0.5}, "blue_1": {"x": -4.0, "y": 0.0}, "blue_2": {"x": -1.5, "y": -0.5}, "blue_3": {"x": -2.5, "y": 0.5}, "red_1": {"x": -1.8, "y": 0.6}, "red_2": {"x": -0.5, "y": -1.5}, "red_3": {"x": 0.5, "y": 1.5}}
OUTPUT: {
  "assignments": {
    "blue_1": {"role": "goalie", "action": "Move", "x": -4.0, "y": 0.5},
    "blue_2": {"role": "defender", "action": "Move", "x": -2.5, "y": -0.5},
    "blue_3": {"role": "attacker", "action": "Kick"}
  }
}"""

# new1r: LAST MAN — was blue_2 kicks / blue_3 last man; now blue_3 kicks,
# blue_2 is the last man holding deep.
NEW1R = """INPUT: {"soccer_ball": {"x": 2.0, "y": -0.8}, "blue_1": {"x": -4.0, "y": 0.0}, "blue_2": {"x": -1.5, "y": -0.3}, "blue_3": {"x": 1.8, "y": -0.9}, "red_1": {"x": 1.0, "y": 0.0}, "red_2": {"x": 1.4, "y": -1.7}, "red_3": {"x": 3.0, "y": 1.5}}
OUTPUT: {
  "assignments": {
    "blue_1": {"role": "goalie", "action": "Move", "x": -4.0, "y": -0.4},
    "blue_2": {"role": "defender", "action": "Move", "x": -2.0, "y": -0.4},
    "blue_3": {"role": "attacker", "action": "Kick"}
  }
}"""

# new3br: REBOUND — was blue_3 shoots / blue_2 rebound position; now blue_2
# shoots (plain kick — with-target stays on blue_2 only, so this is safe),
# blue_3 takes the rebound position.
NEW3BR = """INPUT: {"soccer_ball": {"x": 3.8, "y": 0.3}, "blue_1": {"x": -4.0, "y": 0.0}, "blue_2": {"x": 3.6, "y": 0.2}, "blue_3": {"x": 1.5, "y": -1.0}, "red_1": {"x": 4.3, "y": 0.2}, "red_2": {"x": 2.0, "y": 0.8}, "red_3": {"x": 2.5, "y": -1.5}}
OUTPUT: {
  "assignments": {
    "blue_1": {"role": "goalie", "action": "Move", "x": -4.0, "y": 0.2},
    "blue_2": {"role": "attacker", "action": "Kick"},
    "blue_3": {"role": "attacker", "action": "Move", "x": 3.0, "y": -0.8}
  }
}"""

# ====================================================================
# W8: nearest-bot illustration examples (added to B13).
# Headers state the geometry factually (A3: coordinates over prose).
# Plain kicks only (steal-safe: no with-target on blue_3).
# ====================================================================

NB1 = """INPUT: {"soccer_ball": {"x": 0.0, "y": -0.5}, "blue_1": {"x": -4.0, "y": 0.0}, "blue_2": {"x": 0.2, "y": -0.6}, "blue_3": {"x": 3.0, "y": 1.5}, "red_1": {"x": 1.5, "y": 0.0}, "red_2": {"x": 2.5, "y": -1.0}, "red_3": {"x": -2.0, "y": 1.0}}
OUTPUT: {
  "assignments": {
    "blue_1": {"role": "goalie", "action": "Move", "x": -4.0, "y": -0.3},
    "blue_2": {"role": "attacker", "action": "Kick"},
    "blue_3": {"role": "attacker", "action": "Move", "x": 2.0, "y": 0.0}
  }
}"""

NB2 = """INPUT: {"soccer_ball": {"x": 1.0, "y": 0.6}, "blue_1": {"x": -4.0, "y": 0.1}, "blue_2": {"x": -1.5, "y": 1.8}, "blue_3": {"x": 1.2, "y": 0.7}, "red_1": {"x": 2.5, "y": 0.5}, "red_2": {"x": 0.0, "y": -1.5}, "red_3": {"x": 3.5, "y": -1.0}}
OUTPUT: {
  "assignments": {
    "blue_1": {"role": "goalie", "action": "Move", "x": -4.0, "y": 0.3},
    "blue_2": {"role": "defender", "action": "Move", "x": 0.5, "y": 0.0},
    "blue_3": {"role": "attacker", "action": "Kick"}
  }
}"""

HEADERS_ROT = {
    "ex5r": "ALL BOTS BEHIND THE BALL (DEFENDING)",
    "new1r": "LAST MAN HOLDS DEEP WHILE TWO ATTACK",
    "new3br": "REBOUND POSITIONING AFTER A SHOT",
}

HEADERS_NB = {
    "nb1": "NEAREST BOT TAKES THE KICK (blue_2 at 0.5m from ball, blue_3 at 3.5m)",
    "nb2": "NEAREST BOT TAKES THE KICK (blue_3 at 0.3m from ball, blue_2 at 3.3m)",
}


def get_w7w8_variants():
    """Return dict: variant key -> {header, rules_core, rules_mode, samples}."""
    import s1_variants as V

    header_prod = read_frag("header.txt")
    rules_core_prod = read_frag("rules_core.txt")
    rules_3vs3_prod = read_frag("rules_3vs3.txt")

    # B13 bodies from the production-identical composition
    b13_keys = V.SAMPLES_B13_KEYS  # ex1, ex2, ex5, ex6, ex7, new1, new2b, new3b

    def compose(keys, extra_map=None, extra_headers=None):
        chunks = []
        for i, k in enumerate(keys, 1):
            hdr = (extra_headers or {}).get(k) or V.HEADERS_NEUTRAL.get(k, k)
            body = (extra_map or {}).get(k) or V.EX_BODIES[k]
            chunks.append(f"--- EXAMPLE {i}: {hdr} ---\n{body}")
        return "\n".join(chunks)

    # W7: rotate ex5 -> ex5r, new1 -> new1r, new3b -> new3br
    w7_keys = ["ex1", "ex2", "ex5r", "ex6", "ex7", "new1r", "new2b", "new3br"]
    w7_bodies = {"ex5r": EX5R, "new1r": NEW1R, "new3br": NEW3BR}
    w7_headers = {k: HEADERS_ROT.get(k, V.HEADERS_NEUTRAL.get(k, k)) for k in w7_keys}
    samples_w7 = compose(w7_keys, w7_bodies, w7_headers)

    # W8: B13 + nb1 + nb2 (10 examples; goalie ratio 2/10 — dose risk noted)
    w8_keys = b13_keys + ["nb1", "nb2"]
    w8_bodies = {"nb1": NB1, "nb2": NB2}
    w8_headers = {k: HEADERS_NB.get(k, V.HEADERS_NEUTRAL.get(k, k)) for k in w8_keys}
    samples_w8 = compose(w8_keys, w8_bodies, w8_headers)

    # W78: rotation + illustrations (10 examples)
    w78_keys = w7_keys + ["nb1", "nb2"]
    w78_bodies = {**w7_bodies, "nb1": NB1, "nb2": NB2}
    w78_headers = {**w7_headers, **{k: HEADERS_NB.get(k, V.HEADERS_NEUTRAL.get(k, k)) for k in w78_keys}}
    samples_w78 = compose(w78_keys, w78_bodies, w78_headers)

    return {
        "W7": {"header": header_prod, "rules_core": rules_core_prod,
               "rules_mode": rules_3vs3_prod, "samples": samples_w7,
               "desc": "identity rotation: field-kick split blue_2/blue_3 = 3:3"},
        "W8": {"header": header_prod, "rules_core": rules_core_prod,
               "rules_mode": rules_3vs3_prod, "samples": samples_w8,
               "desc": "B13 + 2 nearest-bot illustrations (10 examples)"},
        "W78": {"header": header_prod, "rules_core": rules_core_prod,
                "rules_mode": rules_3vs3_prod, "samples": samples_w78,
                "desc": "rotation + nearest-bot illustrations (10 examples)"},
    }
