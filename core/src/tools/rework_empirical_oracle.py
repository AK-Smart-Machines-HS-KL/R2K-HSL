#!/usr/bin/env python3
"""T2: Deterministic rework of 33 empirical scenario analysis.md files.

Generates proper Scope/Expert/Oracle from entity positions + umschalt type.
No external LLM needed — tactical analysis is computed from geometry.

Usage:
  python3 tools/rework_empirical_oracle.py
  python3 tools/rework_empirical_oracle.py --only emp_empirical-proven_ball_won_000
"""
import argparse
import json
import math
import os
import re
import glob

BASE_DIR = os.path.dirname(os.path.abspath(__file__)) + "/.."
SCENARIO_DIR = os.path.join(BASE_DIR, "scenario")
UMSCHALT_FILE = os.path.join(BASE_DIR, "results", "umschaltmomente.jsonl")
FIELD_X, FIELD_Y = 4.5, 3.0


def load_umschalt_descs():
    """Load umschalt descriptions from umschaltmomente.jsonl.
    Returns list of dicts with name, umschalt_type, tag, umschalt_description."""
    if not os.path.exists(UMSCHALT_FILE):
        return []
    descs = []
    with open(UMSCHALT_FILE) as f:
        for line in f:
            if line.strip():
                try:
                    d = json.loads(line)
                    descs.append(d)
                except Exception:
                    pass
    return descs


def find_umschalt_desc(descs, source_match, utype, tag):
    """Find the umschalt description matching source, type, and tag."""
    for d in descs:
        if (source_match in d.get("name", "")
                and d.get("umschalt_type") == utype
                and d.get("tag") == tag):
            return d.get("umschalt_description", utype)
    return utype


def dist(e1, e2):
    return math.hypot(e1["x"] - e2["x"], e1["y"] - e2["y"])


def ball_zone(ball):
    if ball["x"] > 2.0:
        return "deep in the opponent half"
    elif ball["x"] > 0.5:
        return "in the opponent half"
    elif ball["x"] > -0.5:
        return "near the halfway line"
    elif ball["x"] > -2.0:
        return "in Blue's own half"
    else:
        return "deep in Blue's own half, near Blue's goal"


def nearest(entities, ball, prefix):
    cands = {k: v for k, v in entities.items() if k.startswith(prefix)}
    if not cands:
        return None, 999
    best = min(cands.items(), key=lambda kv: dist(kv[1], ball))
    return best[0], dist(best[1], ball)


def all_dists(entities, ball, prefix):
    return sorted(
        (round(dist(v, ball), 2), k)
        for k, v in entities.items()
        if k.startswith(prefix))


def min_pairwise_blue(blues):
    coords = [(k, v["x"], v["y"]) for k, v in blues.items()]
    if len(coords) < 2:
        return 999
    md = 999
    pair = None
    for i, (n1, x1, y1) in enumerate(coords):
        for n2, x2, y2 in coords[i + 1:]:
            d = math.hypot(x1 - x2, y1 - y2)
            if d < md:
                md = d
                pair = (n1, n2)
    return md, pair


def gen_expert(ents, umschalt_type, tag):
    ball = ents["soccer_ball"]
    blues = {k: v for k, v in ents.items() if k.startswith("blue")}
    reds = {k: v for k, v in ents.items() if k.startswith("red")}

    near_b_name, near_b_d = nearest(ents, ball, "blue")
    near_r_name, near_r_d = nearest(ents, ball, "red")
    possession = "BLUE" if near_b_d <= near_r_d else "RED"

    parts = []
    parts.append(f"Ball at ({ball['x']:.1f}, {ball['y']:.1f}), {ball_zone(ball)}.")

    bd = all_dists(ents, ball, "blue")
    rd = all_dists(ents, ball, "red")
    parts.append(
        f"Closest blue: {near_b_name} ({near_b_d:.1f}m). "
        f"Closest red: {near_r_name} ({near_r_d:.1f}m). "
        f"Possession: {possession}."
    )

    if umschalt_type == "cluster":
        md, pair = min_pairwise_blue(blues)
        if md < 1.0 and pair:
            parts.append(
                f"Blue clustering: {pair[0]} and {pair[1]} are {md:.1f}m apart — "
                f"tactical congestion limiting options."
            )

    if tag == "empirical-proven":
        outcome = "Blue scored — this was a successful transition."
    else:
        outcome = "Red scored — this was a defensive failure for Blue."

    nums_near = sum(1 for d, _ in bd if d < 2.0)
    reds_near = sum(1 for d, _ in rd if d < 2.0)
    if nums_near > reds_near and possession == "BLUE":
        parts.append(
            f"Blue has a numbers advantage near the ball "
            f"({nums_near} blue vs {reds_near} red within 2m)."
        )
    elif reds_near > nums_near and possession == "RED":
        parts.append(
            f"Red has a numbers advantage near the ball "
            f"({reds_near} red vs {nums_near} blue within 2m) — "
            f"Blue is outnumbered defensively."
        )

    goalie = blues.get("blue_1", {})
    goalie_d = dist(goalie, ball)
    if goalie_d > 3.0 and ball["x"] < -2.0:
        parts.append(
            f"Blue goalie (blue_1 at ({goalie['x']:.1f}, {goalie['y']:.1f})) "
            f"is {goalie_d:.1f}m from the ball — far from the action."
        )

    parts.append(f"Umschalt type: {umschalt_type}. {outcome}")
    return " ".join(parts)


def assign_roles(near_b_name, b1="blue_1", b2="blue_2", b3="blue_3"):
    """Assign 3 roles: active (nearest), goalie, support. No duplicates.
    If nearest IS blue_1 (goalie), goalie role goes to another bot."""
    all_bots = [b1, b2, b3]
    active = near_b_name
    if active == b1:
        goalie = b2
        support = b3
    else:
        goalie = b1
        support = [b for b in all_bots if b != active and b != b1][0]
    return active, goalie, support


def gen_oracle(ents, umschalt_type, tag):
    ball = ents["soccer_ball"]
    blues = {k: v for k, v in ents.items() if k.startswith("blue")}
    reds = {k: v for k, v in ents.items() if k.startswith("red")}

    near_b_name, near_b_d = nearest(ents, ball, "blue")
    near_r_name, near_r_d = nearest(ents, ball, "red")
    possession = "BLUE" if near_b_d <= near_r_d else "RED"

    ball_in_opp = ball["x"] > 0.5
    ball_in_own = ball["x"] < -2.0
    ball_deep_opp = ball["x"] > 3.0
    ball_deep_own = ball["x"] < -3.5

    b1 = "blue_1"
    b2 = "blue_2"
    b3 = "blue_3"
    goalie_y = max(-0.9, min(0.9, ball["y"]))

    if tag == "empirical-proven":
        if possession == "BLUE" and ball_deep_opp:
            reason = (
                "To capitalize on the turnover in the opponent half: "
                f"the nearest blue ({near_b_name}) kicks on goal, "
                "another blue provides a passing option by moving to open space, "
                "and the goalie covers the goal line for counter-attack safety."
            )
            kicker, goalie, support = assign_roles(near_b_name)

            support_x = max(-1.0, min(1.0, ball["x"] - 2.0))
            support_y = max(-2.0, min(2.0, -ball["y"] * 0.5))
            if abs(support_y) < 0.5:
                support_y = 1.5 if ball["y"] > 0 else -1.5

            code = (
                f"{kicker} kick\n"
                f"{support} move to ({support_x:.1f}, {support_y:.1f})\n"
                f"{goalie} cover the goal line at (-4.0, {goalie_y:.1f})"
            )
            return reason, code

        elif possession == "RED" and ball_deep_opp:
            reason = (
                "To regain possession deep in the opponent half: "
                f"the nearest blue ({near_b_name}) presses the ball carrier, "
                "another blue cuts off the passing lane, "
                "and the goalie holds the goal line."
            )
            presser, goalie, blocker = assign_roles(near_b_name)

            blk_x = max(0.0, min(3.0, ball["x"] - 1.5))
            blk_y = max(-2.0, min(2.0, -ball["y"]))

            code = (
                f"{presser} move to ({ball['x']:.1f}, {ball['y']:.1f})\n"
                f"{blocker} move to ({blk_x:.1f}, {blk_y:.1f})\n"
                f"{goalie} cover the goal line at (-4.0, {goalie_y:.1f})"
            )
            return reason, code

        elif possession == "BLUE" and not ball_deep_opp:
            reason = (
                "To maintain possession and build an attack: "
                f"the nearest blue ({near_b_name}) advances the ball, "
                "another blue offers a forward passing option, "
                "and the goalie secures the goal line."
            )
            carrier, goalie, support = assign_roles(near_b_name)

            adv_x = max(0.5, min(4.0, ball["x"] + 1.0))
            adv_y = max(-2.0, min(2.0, ball["y"]))
            sup_x = max(0.0, min(3.0, ball["x"] + 0.5))
            sup_y = max(-2.5, min(2.5, ball["y"] - 1.0))
            if abs(sup_y - adv_y) < 0.8:
                sup_y = adv_y + 1.5 if adv_y < 0 else adv_y - 1.5

            code = (
                f"{carrier} move to ({adv_x:.1f}, {adv_y:.1f})\n"
                f"{support} move to ({sup_x:.1f}, {sup_y:.1f})\n"
                f"{goalie} cover the goal line at (-4.0, {goalie_y:.1f})"
            )
            return reason, code

    else:
        if possession == "RED" and ball_deep_own:
            near_r_dist = near_r_d
            if near_r_dist < 1.0:
                reason = (
                    "To prevent a goal: Red is within "
                    f"{near_r_dist:.1f}m of the ball deep in Blue's half. "
                    f"The nearest blue ({near_b_name}) must kick the ball "
                    "clear immediately, another blue covers the goal line, "
                    "and the third blue blocks the passing lane to the shooter."
                )
                clearer, goalie, blocker = assign_roles(near_b_name)

                blk_x = max(-4.0, min(-1.0, ball["x"] + 0.5))
                blk_y = max(-2.5, min(2.5, -ball["y"]))

                code = (
                    f"{clearer} kick\n"
                    f"{blocker} move to ({blk_x:.1f}, {blk_y:.1f})\n"
                    f"{goalie} cover the goal line at (-4.0, {goalie_y:.1f})"
                )
                return reason, code
            else:
                reason = (
                    f"To recover defensive shape: Red has possession deep in "
                    f"Blue's half but the nearest red is {near_r_dist:.1f}m away. "
                    f"The nearest blue ({near_b_name}) challenges for the ball, "
                    "another blue covers the goal line, "
                    "and the third blue marks the passing lane."
                )
                challenger, goalie, marker = assign_roles(near_b_name)

                mark_x = max(-3.5, min(0.0, ball["x"] + 1.0))
                mark_y = max(-2.5, min(2.5, ball["y"] * 0.5))

                code = (
                    f"{challenger} move to ({ball['x']:.1f}, {ball['y']:.1f})\n"
                    f"{marker} move to ({mark_x:.1f}, {mark_y:.1f})\n"
                    f"{goalie} cover the goal line at (-4.0, {goalie_y:.1f})"
                )
                return reason, code

        elif possession == "BLUE" and ball_deep_own:
            reason = (
                "To escape the dangerous position: Blue has the ball deep in "
                f"own half. The nearest blue ({near_b_name}) clears the ball "
                "upfield immediately, another blue drops to cover the goal line, "
                "and the third blue moves to midfield to receive the clearance."
            )
            clearer, goalie, target = assign_roles(near_b_name)

            tgt_x = max(0.5, min(2.5, ball["x"] + 4.0))
            tgt_y = max(-2.0, min(2.0, -ball["y"]))

            code = (
                f"{clearer} kick\n"
                f"{target} move to ({tgt_x:.1f}, {tgt_y:.1f})\n"
                f"{goalie} cover the goal line at (-4.0, {goalie_y:.1f})"
            )
            return reason, code

        elif umschalt_type == "cluster":
            md, pair = min_pairwise_blue(blues)
            reason = (
                "To break the cluster: two blue bots are within "
                f"{md:.1f}m of each other. The nearest blue to the ball "
                f"({near_b_name}) challenges for possession, the clustered "
                "partner spreads wide to open space, and the goalie "
                "secures the goal line."
            )
            challenger, goalie, spreader = assign_roles(near_b_name)

            spread_x = max(-2.0, min(2.0, ball["x"] + 2.0))
            spread_y = max(-2.5, min(2.5, -ball["y"] + 1.5))
            if abs(spread_y) < 0.5:
                spread_y = 2.0

            code = (
                f"{challenger} move to ({ball['x']:.1f}, {ball['y']:.1f})\n"
                f"{spreader} move to ({spread_x:.1f}, {spread_y:.1f})\n"
                f"{goalie} cover the goal line at (-4.0, {goalie_y:.1f})"
            )
            return reason, code

        else:
            near_r_name2, near_r_d2 = nearest(ents, ball, "red")
            reason = (
                f"To stabilize after the {umschalt_type}: the nearest blue "
                f"({near_b_name}) presses the ball, another blue provides "
                "defensive cover, and the goalie holds the goal line."
            )
            presser, goalie, cover = assign_roles(near_b_name)

            cov_x = max(-3.0, min(0.0, ball["x"] + 1.0))
            cov_y = max(-2.5, min(2.5, -ball["y"]))

            code = (
                f"{presser} move to ({ball['x']:.1f}, {ball['y']:.1f})\n"
                f"{cover} move to ({cov_x:.1f}, {cov_y:.1f})\n"
                f"{goalie} cover the goal line at (-4.0, {goalie_y:.1f})"
            )
            return reason, code

    reason = (
        f"To respond to the {umschalt_type}: the nearest blue presses the "
        "ball, another blue provides support, and the goalie covers the goal line."
    )
    presser, goalie, support = assign_roles(near_b_name)

    sup_x = max(-2.0, min(2.0, ball["x"] - 1.0))
    sup_y = max(-2.5, min(2.5, ball["y"]))

    code = (
        f"{presser} move to ({ball['x']:.1f}, {ball['y']:.1f})\n"
        f"{support} move to ({sup_x:.1f}, {sup_y:.1f})\n"
        f"{goalie} cover the goal line at (-4.0, {goalie_y:.1f})"
    )
    return reason, code


def gen_scope(umschalt_type, tag, ball):
    if tag == "empirical-proven":
        if ball["x"] > 3.0:
            return (
                f"Blue won a {umschalt_type} deep in the opponent half — "
                "test whether Blue capitalizes on the turnover and scores."
            )
        elif ball["x"] < -3.0:
            return (
                f"Blue won a {umschalt_type} in own half — "
                "test whether Blue transitions from defense to attack successfully."
            )
        else:
            return (
                f"Blue won a {umschalt_type} in midfield — "
                "test whether Blue maintains possession and builds an attack."
            )
    else:
        if ball["x"] < -3.0:
            return (
                f"Red won a {umschalt_type} deep in Blue's half — "
                "test whether Blue can recover defensively and prevent the concession."
            )
        else:
            return (
                f"Red won a {umschalt_type} — "
                "test whether Blue can regain defensive shape and prevent a goal."
            )


def rework_one(scenario_dir):
    name = os.path.basename(scenario_dir.rstrip("/"))
    sj = os.path.join(scenario_dir, "scenario.json")
    am = os.path.join(scenario_dir, "analysis.md")

    with open(sj) as f:
        s = json.load(f)
    ents = s["entities"]

    with open(am) as f:
        old_md = f.read()

    source_match = ""
    m = re.search(r"Original match:\s*(.+)", old_md)
    if m:
        source_match = m.group(1).strip()

    cluster_info = ""
    m = re.search(r"Cluster:\s*(.+)", old_md)
    if m:
        cluster_info = m.group(1).strip()

    umschalt_desc = ""
    ts = s.get("tactical_situation", "")
    utype = ts.replace("Umschalt: ", "").split(" (")[0]

    tag = "empirical-proven" if "empirical-proven" in name else "regression-anti"
    outcome = "blue scored" if tag == "empirical-proven" else "red scored"

    descs = load_umschalt_descs()
    umschalt_desc = find_umschalt_desc(descs, source_match, utype, tag)

    qwen_section = ""
    m = re.search(r"## Qwen's decision.*?\n(.*?)(?=\n## |\Z)", old_md, re.DOTALL)
    if m:
        qwen_section = m.group(1).strip()

    metrics_section = ""
    m = re.search(r"## Regression metrics.*?\n(.*?)(?=\n## |\Z)", old_md, re.DOTALL)
    if m:
        metrics_section = m.group(1).strip()

    test_section = ""
    m = re.search(r"## Test specification.*?\n(.*?)(?:\Z)", old_md, re.DOTALL)
    if m:
        test_section = m.group(1).strip()

    ball = ents["soccer_ball"]
    scope = gen_scope(utype, tag, ball)
    expert = gen_expert(ents, utype, tag)
    oracle_prose, oracle_code = gen_oracle(ents, utype, tag)

    output_lines = []
    for line in oracle_code.strip().split("\n"):
        line = line.strip()
        if line:
            output_lines.append(line.replace("cover the goal line at", "move to"))
    output_bridge = "\n".join(output_lines)

    new_md = f"""# {name}

![field diagram](field_diagram.png)

## Source
- Original match: {source_match}
- Umschalt type: {utype} — {umschalt_desc}
- Tag: {tag} ({outcome})
- Cluster: {cluster_info}

## Scope
{scope}

## Expert (Analysis)
{expert}

## Oracle (Strategy)
{oracle_prose}

```
{oracle_code}
```

## Output to bridge

```
{output_bridge}
```

## Qwen's decision at t_umschalt

{qwen_section}

## Regression metrics
{metrics_section}

## Score delta

![score chart](score_chart.png)

## Test specification
{test_section}
"""

    with open(am, "w") as f:
        f.write(new_md)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="comma-separated scenario names")
    args = ap.parse_args()

    dirs = sorted(glob.glob(os.path.join(SCENARIO_DIR, "emp_*/")))
    if args.only:
        only = set(args.only.split(","))
        dirs = [d for d in dirs if os.path.basename(d.rstrip("/")) in only]

    print(f"Reworking {len(dirs)} empirical scenarios")
    ok = 0
    for d in dirs:
        name = os.path.basename(d.rstrip("/"))
        try:
            rework_one(d)
            print(f"  OK {name}")
            ok += 1
        except Exception as e:
            print(f"  FAIL {name}: {e}")
    print(f"\nDone: {ok}/{len(dirs)} OK")


if __name__ == "__main__":
    main()
