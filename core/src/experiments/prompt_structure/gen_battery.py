#!/usr/bin/env python3
"""Generate the prompt-structure probe batteries (V_A/V_B/V_C) for all scenarios.

Reads scenario/<name>/scenario.json (entities) and analysis.md (Expert+Oracle),
writes experiments/prompt_structure/v{A,B,C}_*.jsonl. One probe per scenario.
No Gazebo, no ROS — text-only Ollama probes.
"""

import json
import os
import re

SCEN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scenario")
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))

SCENARIOS = [
    "2vs2_default",
    "2vs2_goalie_pass",
    "3vs3_attack_center",
    "3vs3_attack_wing",
    "3vs3_contain_delay",
    "3vs3_defensive_crisis",
    "3vs3_def_transition",
    "3vs3_fast_counter",
    "3vs3_high_line",
    "3vs3_long_shot",
    "3vs3_pressing_trap",
]

ESSENCE = {
    "2vs2_default": "Red attacks: red_1 is on the ball with a free pass to red_2. Blue_1 and blue_2 are clustered; the near-post lane and the passing lane to red_2 are open.",
    "2vs2_goalie_pass": "The blue goalie has uncontested possession, red_1 is pressing, nobody guards red's goal, blue_2 is the open outlet.",
    "3vs3_attack_center": "Red's goalie is off-center at Y=0.5, red's defenders stand wide on the wings, the middle is open — blue has a numbers advantage in the center.",
    "3vs3_attack_wing": "Blue_1's shooting angle is too narrow (ball sits between blue_1 and the goal), red_2 will move in to block, blue_2 is too far back to receive a pass into space.",
    "3vs3_contain_delay": "Blue's formation is sound; red_1 can dribble wing or center, red_2/red_3 cluster, red's goal is free, blue_1 is the deepest bot.",
    "3vs3_defensive_crisis": "Red_1 is on the ball in front of blue's goal; blue_1 is the only bot positioned to intercept; blue_3's lane is blocked by red_2.",
    "3vs3_def_transition": "Blue just lost the ball; blue_3 contests red_1 (legal tackle, both within reach); red_2/red_3 are out of reach; blue_2 has free right-wing space.",
    "3vs3_fast_counter": "Blue_1 has free time on the ball (red_1 too far to contest); red_2/red_3 are upfield and out of reach; the left wing is open.",
    "3vs3_high_line": "Blue's back line is deep at X=-3.0; blue_1 sits off the ball-to-near-post axis; blue_2 covers neither red_2 nor red_3.",
    "3vs3_long_shot": "Possession is contested (blue_1 0.38 m, red_2 0.67 m); the goal mouth is bracketed by red_1 (short post) and red_3 (long post); blue_2 cannot assist in time.",
    "3vs3_pressing_trap": "Blue_1 is pressed by red_1/red_2, red_3 covers the upper lane, blue_2 sits behind the press, and no blue bot covers the own goal area.",
}


def read_sections(name):
    p = os.path.join(SCEN_DIR, name, "analysis.md")
    with open(p, encoding="utf-8") as f:
        text = f.read()
    expert = text.split("## Expert (technical)")[1].split("## Oracle (strategic)")[0].strip()
    oracle = text.split("## Oracle (strategic)")[1].strip()
    oracle = re.sub(r"^#.*$", "", oracle, flags=re.M).strip()
    oracle_lines = []
    for ln in oracle.splitlines():
        ln = ln.strip().lstrip("- ").strip()
        if ln:
            oracle_lines.append(re.sub(r"^\*\*(blue_\d+):\*\*\s*", r"\1: ", ln))
    return expert, "\n".join(oracle_lines)


def world_line(name):
    with open(os.path.join(SCEN_DIR, name, "scenario.json"), encoding="utf-8") as f:
        data = json.load(f)
    ents = data["entities"]
    order = ["soccer_ball"] + [k for k in ents if k.startswith("blue")] + [k for k in ents if k.startswith("red")]
    parts = []
    for k in order:
        e = ents[k]
        if k == "soccer_ball":
            parts.append(f"ball at ({e['x']}, {e['y']})")
        else:
            parts.append(f"{k} at ({e['x']}, {e['y']})")
    n_blue = sum(1 for k in ents if k.startswith("blue"))
    n_red = sum(1 for k in ents if k.startswith("red"))
    return ", ".join(parts), n_blue, n_red


def fmt(n_blue, n_red):
    word = "two" if n_blue == 2 else "three"
    fmt_s = ", ".join(f"blue_{i}: (X, Y)" for i in range(1, n_blue + 1))
    return fmt_s, word


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    out = {"vA": [], "vB": [], "vC": []}
    for name in SCENARIOS:
        expert, oracle = read_sections(name)
        world, n_blue, n_red = world_line(name)
        fmat, word = fmt(n_blue, n_red)

        sysA = (
            "You are a soccer analyst. Given a world state and a tactical instruction, "
            f"output target X,Y positions for each blue bot. Format: {fmat}. "
            f"Output only the {word} lines."
        )
        sysBC = (
            "You are a soccer analyst. Given a world state, a tactical analysis, and a tactical instruction, "
            f"output target X,Y positions for each blue bot. Format: {fmat}. "
            f"Output only the {word} lines."
        )
        body = f"World state: {world}.\n\n"
        promptA = body + f"Tactical instruction: {oracle}\n\nOutput the {word} target positions."
        promptB = body + f"Tactical analysis: {expert}\n\nTactical instruction: {oracle}\n\nOutput the {word} target positions."
        promptC = body + f"Tactical analysis: {ESSENCE[name]}\n\nTactical instruction: {oracle}\n\nOutput the {word} target positions."

        out["vA"].append({"series": f"PS_A_{name}", "system": sysA, "prompt": promptA})
        out["vB"].append({"series": f"PS_B_{name}", "system": sysBC, "prompt": promptB})
        out["vC"].append({"series": f"PS_C_{name}", "system": sysBC, "prompt": promptC})

    for key, probes in out.items():
        path = os.path.join(OUT_DIR, f"{key}.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            for p in probes:
                f.write(json.dumps(p, ensure_ascii=False) + "\n")
        print(f"{path}: {len(probes)} probes")


if __name__ == "__main__":
    main()
