#!/usr/bin/env python3
"""Generate augmented probe corpus for overnight sample sweep.

Produces ~231 scenarios in 10 categories with ground-truth labels for
precision/recall measurement. Output: tests/synthetic_worldstates/corpus_overnight.jsonl

Categories:
  goalie_kick_own_half   — goalie closest + ball in own half → should Kick
  pass_teammate_open     — attacker has ball + teammate open in opp half → should pass
  should_not_goalie_kick — goalie closest but ball in opp half → should Move, not Kick
  should_not_pass        — attacker has ball but all teammates marked → should Kick at goal
  normal_attack          — attacker closest in opp half, no pass opp → should Kick at goal
  defending_deep         — ball in own half, non-goalie closest → challenge
  goal_kick_status       — status=goal_kick
  kickoff_status         — status=kickoff
  ball_out_status        — status=ball_out
  foul_penalty_status    — status=foul_penalty
  corner_kick_in_status  — status=corner_kick_in

Each scenario has:
  label, category, status, score_blue, score_red, entities, expected (dict of expected behaviors)
"""
import json
import math
import os
import random

random.seed(42)

OUTPUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tests", "synthetic_worldstates", "corpus_overnight.jsonl")


def dist(a, b):
    return ((a["x"] - b["x"]) ** 2 + (a["y"] - b["y"]) ** 2) ** 0.5


def make_scenario(label, category, status, entities, expected):
    return {
        "label": label,
        "category": category,
        "status": status,
        "score_blue": 0,
        "score_red": 0,
        "entities": entities,
        "expected": expected,
    }


def gen_goalie_kick_own_half(n=20):
    """Goalie (blue_1) closest to ball, ball in own half (X < 0). Should Kick."""
    scenarios = []
    for i in range(n):
        bx = random.uniform(-4.3, -2.5)
        by = random.uniform(-2.5, 2.5)
        # Place blue_1 behind the ball (towards own goal) at 0.4-0.8m distance
        # This is the Ex6 zone where goalie clearance fires (NOT the Ex2
        # role-swap zone at <0.3m). Clamp to field bounds.
        angle = random.uniform(math.pi * 0.7, math.pi * 1.3)  # mostly backward
        dist_b1 = random.uniform(0.4, 0.8)
        b1x = max(-4.4, min(4.4, bx + math.cos(angle) * dist_b1))
        b1y = max(-2.9, min(2.9, by + math.sin(angle) * dist_b1))
        b2x = random.uniform(0.5, 2.5)
        b2y = random.uniform(-2.0, 2.0)
        b3x = random.uniform(1.5, 3.5)
        b3y = random.uniform(-2.0, 2.0)
        r1x = bx + random.uniform(-0.5, 0.5)
        r1y = by + random.uniform(-0.5, 0.5)
        r2x = random.uniform(-1.0, 1.0)
        r2y = random.uniform(-2.0, 2.0)
        r3x = random.uniform(1.5, 4.0)
        r3y = random.uniform(-2.0, 2.0)

        entities = {
            "soccer_ball": {"x": round(bx, 1), "y": round(by, 1)},
            "blue_1": {"x": round(b1x, 1), "y": round(b1y, 1)},
            "blue_2": {"x": round(b2x, 1), "y": round(b2y, 1)},
            "blue_3": {"x": round(b3x, 1), "y": round(b3y, 1)},
            "red_1": {"x": round(r1x, 1), "y": round(r1y, 1)},
            "red_2": {"x": round(r2x, 1), "y": round(r2y, 1)},
            "red_3": {"x": round(r3x, 1), "y": round(r3y, 1)},
        }
        # Verify blue_1 is closest
        ball = entities["soccer_ball"]
        d1 = dist(ball, entities["blue_1"])
        d2 = dist(ball, entities["blue_2"])
        d3 = dist(ball, entities["blue_3"])
        assert d1 < d2 and d1 < d3, f"{label}: blue_1 not closest ({d1:.2f} vs {d2:.2f}, {d3:.2f})"

        scenarios.append(make_scenario(
            f"goalie_kick_{i+1:02d}", "goalie_kick_own_half", "playing", entities,
            {"goalie_should_kick": True, "pass_should_occur": False}
        ))
    return scenarios


def gen_pass_teammate_open(n=20):
    """Attacker (blue_2) has ball in opp half, teammate (blue_3) open. Should pass."""
    scenarios = []
    for i in range(n):
        bx = random.uniform(0.5, 3.5)
        by = random.uniform(-2.0, 2.0)
        b2x = bx + random.uniform(-0.2, 0.2)
        b2y = by + random.uniform(-0.2, 0.2)
        # blue_3 open in opp half, no red within 1.5m
        b3x = random.uniform(1.5, 4.0)
        b3y = random.uniform(-2.5, 2.5)
        # Place red bots away from blue_3
        r1x = random.uniform(-1.0, 2.0)
        r1y = random.uniform(-2.0, 2.0)
        r2x = random.uniform(-2.0, 0.0)
        r2y = random.uniform(-2.0, 2.0)
        r3x = random.uniform(2.0, 4.5)
        r3y = random.uniform(-2.0, 2.0)
        # Ensure red_3 is >1.5m from blue_3
        b3 = {"x": b3x, "y": b3y}
        r3 = {"x": r3x, "y": r3y}
        if dist(b3, r3) < 2.0:
            r3y = b3y + 2.5 if b3y < 0 else b3y - 2.5
            r3y = max(-2.5, min(2.5, r3y))

        entities = {
            "soccer_ball": {"x": round(bx, 1), "y": round(by, 1)},
            "blue_1": {"x": -4.0, "y": round(random.uniform(-0.5, 0.5), 1)},
            "blue_2": {"x": round(b2x, 1), "y": round(b2y, 1)},
            "blue_3": {"x": round(b3x, 1), "y": round(b3y, 1)},
            "red_1": {"x": round(r1x, 1), "y": round(r1y, 1)},
            "red_2": {"x": round(r2x, 1), "y": round(r2y, 1)},
            "red_3": {"x": round(r3x, 1), "y": round(r3y, 1)},
        }
        ball = entities["soccer_ball"]
        d2 = dist(ball, entities["blue_2"])
        # blue_2 should be closest blue to ball
        d3 = dist(ball, entities["blue_3"])
        assert d2 < d3, f"{label}: blue_2 not closest ({d2:.2f} vs {d3:.2f})"

        scenarios.append(make_scenario(
            f"pass_open_{i+1:02d}", "pass_teammate_open", "playing", entities,
            {"goalie_should_kick": False, "pass_should_occur": True}
        ))
    return scenarios


def gen_should_not_goalie_kick(n=15):
    """Goalie closest but ball in opp half. Goalie should Move, NOT Kick."""
    scenarios = []
    for i in range(n):
        bx = random.uniform(1.0, 3.5)
        by = random.uniform(-2.0, 2.0)
        # blue_1 somehow closest (pushed forward), but ball is in opp half
        b1x = bx - random.uniform(0.2, 0.8)
        b1y = by + random.uniform(-0.3, 0.3)
        b2x = random.uniform(-2.0, 0.0)
        b2y = random.uniform(-2.0, 2.0)
        b3x = random.uniform(-1.0, 1.0)
        b3y = random.uniform(-2.0, 2.0)

        entities = {
            "soccer_ball": {"x": round(bx, 1), "y": round(by, 1)},
            "blue_1": {"x": round(b1x, 1), "y": round(b1y, 1)},
            "blue_2": {"x": round(b2x, 1), "y": round(b2y, 1)},
            "blue_3": {"x": round(b3x, 1), "y": round(b3y, 1)},
            "red_1": {"x": round(bx + 0.5, 1), "y": round(by, 1)},
            "red_2": {"x": round(random.uniform(2.0, 4.0), 1), "y": round(random.uniform(-2.0, 2.0), 1)},
            "red_3": {"x": round(random.uniform(3.0, 4.5), 1), "y": round(random.uniform(-2.0, 2.0), 1)},
        }
        ball = entities["soccer_ball"]
        d1 = dist(ball, entities["blue_1"])
        d2 = dist(ball, entities["blue_2"])
        assert d1 < d2, f"{label}: blue_1 not closest"

        scenarios.append(make_scenario(
            f"no_goalie_kick_{i+1:02d}", "should_not_goalie_kick", "playing", entities,
            {"goalie_should_kick": False, "pass_should_occur": False}
        ))
    return scenarios


def gen_should_not_pass(n=15):
    """Attacker has ball but all teammates marked. Should Kick at goal, NOT pass."""
    scenarios = []
    for i in range(n):
        bx = random.uniform(0.5, 3.0)
        by = random.uniform(-1.5, 1.5)
        b2x = bx + random.uniform(-0.2, 0.2)
        b2y = by + random.uniform(-0.2, 0.2)
        # blue_3 in opp half but covered by red (< 1.0m away)
        b3x = random.uniform(1.5, 3.5)
        b3y = random.uniform(-2.0, 2.0)
        r1x = b3x + random.uniform(-0.5, 0.5)
        r1y = b3y + random.uniform(-0.5, 0.5)

        entities = {
            "soccer_ball": {"x": round(bx, 1), "y": round(by, 1)},
            "blue_1": {"x": -4.0, "y": round(random.uniform(-0.5, 0.5), 1)},
            "blue_2": {"x": round(b2x, 1), "y": round(b2y, 1)},
            "blue_3": {"x": round(b3x, 1), "y": round(b3y, 1)},
            "red_1": {"x": round(r1x, 1), "y": round(r1y, 1)},
            "red_2": {"x": round(random.uniform(-1.0, 1.0), 1), "y": round(random.uniform(-2.0, 2.0), 1)},
            "red_3": {"x": round(random.uniform(3.0, 4.5), 1), "y": round(random.uniform(-2.0, 2.0), 1)},
        }
        # Verify blue_3 is covered by red_1
        d = dist(entities["blue_3"], entities["red_1"])
        assert d < 1.5, f"{label}: blue_3 not covered ({d:.2f})"

        scenarios.append(make_scenario(
            f"no_pass_{i+1:02d}", "should_not_pass", "playing", entities,
            {"goalie_should_kick": False, "pass_should_occur": False}
        ))
    return scenarios


def gen_normal_attack(n=15):
    """Attacker closest to ball in opp half, no special pass opportunity."""
    scenarios = []
    for i in range(n):
        bx = random.uniform(0.5, 3.5)
        by = random.uniform(-2.0, 2.0)
        b2x = bx + random.uniform(-0.3, 0.3)
        b2y = by + random.uniform(-0.3, 0.3)
        b3x = random.uniform(-1.0, 1.0)
        b3y = random.uniform(-2.0, 2.0)

        entities = {
            "soccer_ball": {"x": round(bx, 1), "y": round(by, 1)},
            "blue_1": {"x": -4.0, "y": round(random.uniform(-0.5, 0.5), 1)},
            "blue_2": {"x": round(b2x, 1), "y": round(b2y, 1)},
            "blue_3": {"x": round(b3x, 1), "y": round(b3y, 1)},
            "red_1": {"x": round(random.uniform(2.0, 4.0), 1), "y": round(random.uniform(-2.0, 2.0), 1)},
            "red_2": {"x": round(random.uniform(1.0, 3.5), 1), "y": round(random.uniform(-2.0, 2.0), 1)},
            "red_3": {"x": round(random.uniform(3.0, 4.5), 1), "y": round(random.uniform(-2.0, 2.0), 1)},
        }
        scenarios.append(make_scenario(
            f"normal_attack_{i+1:02d}", "normal_attack", "playing", entities,
            {"goalie_should_kick": False, "pass_should_occur": False}
        ))
    return scenarios


def gen_defending_deep(n=15):
    """Ball in own half, non-goalie (blue_2) closest. Should challenge."""
    scenarios = []
    for i in range(n):
        bx = random.uniform(-3.5, -1.0)
        by = random.uniform(-2.0, 2.0)
        b2x = bx + random.uniform(-0.3, 0.3)
        b2y = by + random.uniform(-0.3, 0.3)

        entities = {
            "soccer_ball": {"x": round(bx, 1), "y": round(by, 1)},
            "blue_1": {"x": -4.0, "y": round(random.uniform(-0.5, 0.5), 1)},
            "blue_2": {"x": round(b2x, 1), "y": round(b2y, 1)},
            "blue_3": {"x": round(random.uniform(0.0, 2.0), 1), "y": round(random.uniform(-2.0, 2.0), 1)},
            "red_1": {"x": round(bx + random.uniform(-0.5, 0.5), 1), "y": round(by + random.uniform(-0.5, 0.5), 1)},
            "red_2": {"x": round(random.uniform(-1.0, 1.0), 1), "y": round(random.uniform(-2.0, 2.0), 1)},
            "red_3": {"x": round(random.uniform(1.5, 4.0), 1), "y": round(random.uniform(-2.0, 2.0), 1)},
        }
        ball = entities["soccer_ball"]
        d1 = dist(ball, entities["blue_1"])
        d2 = dist(ball, entities["blue_2"])
        assert d2 < d1, f"{label}: blue_2 not closest to ball"

        scenarios.append(make_scenario(
            f"defending_{i+1:02d}", "defending_deep", "playing", entities,
            {"goalie_should_kick": False, "pass_should_occur": False}
        ))
    return scenarios


def gen_status_scenarios(status, n=10):
    """Generate status-specific scenarios."""
    scenarios = []
    for i in range(n):
        if status == "goal_kick":
            bx = random.uniform(-4.0, -2.5)
            by = random.uniform(-2.0, 2.0)
            b1x = bx + random.uniform(-0.3, 0.1)
        elif status == "kickoff":
            bx, by = 0.0, 0.0
            b1x = -4.0
        elif status == "ball_out":
            bx = random.uniform(-3.0, 3.0)
            by = random.choice([-2.9, 2.9])
            b1x = -4.0
        elif status == "foul_penalty":
            bx = random.uniform(-3.0, -1.0)
            by = random.uniform(-1.5, 1.5)
            b1x = -4.0
        elif status == "corner_kick_in":
            bx = random.choice([-4.3, 4.3])
            by = random.choice([-2.8, 2.8])
            b1x = -4.0
        else:
            bx, by = 0.0, 0.0
            b1x = -4.0

        entities = {
            "soccer_ball": {"x": round(bx, 1), "y": round(by, 1)},
            "blue_1": {"x": round(b1x, 1), "y": round(random.uniform(-0.5, 0.5), 1)},
            "blue_2": {"x": round(random.uniform(-2.0, 0.0), 1), "y": round(random.uniform(-2.0, 2.0), 1)},
            "blue_3": {"x": round(random.uniform(0.0, 2.0), 1), "y": round(random.uniform(-2.0, 2.0), 1)},
            "red_1": {"x": round(random.uniform(1.0, 4.0), 1), "y": round(random.uniform(-2.0, 2.0), 1)},
            "red_2": {"x": round(random.uniform(2.0, 4.5), 1), "y": round(random.uniform(-2.0, 2.0), 1)},
            "red_3": {"x": round(random.uniform(3.0, 4.5), 1), "y": round(random.uniform(-2.0, 2.0), 1)},
        }
        scenarios.append(make_scenario(
            f"{status}_{i+1:02d}", f"{status}_status", status, entities,
            {"goalie_should_kick": status == "goal_kick", "pass_should_occur": False}
        ))
    return scenarios


def main():
    all_scenarios = []
    all_scenarios += gen_goalie_kick_own_half(20)
    all_scenarios += gen_pass_teammate_open(20)
    all_scenarios += gen_should_not_goalie_kick(15)
    all_scenarios += gen_should_not_pass(15)
    all_scenarios += gen_normal_attack(15)
    all_scenarios += gen_defending_deep(15)
    all_scenarios += gen_status_scenarios("goal_kick", 10)
    all_scenarios += gen_status_scenarios("kickoff", 10)
    all_scenarios += gen_status_scenarios("ball_out", 10)
    all_scenarios += gen_status_scenarios("foul_penalty", 10)
    all_scenarios += gen_status_scenarios("corner_kick_in", 10)

    # Also load existing 81-scenario corpus (without category labels)
    existing_path = os.path.join(os.path.dirname(OUTPUT), "corpus.jsonl")
    if os.path.exists(existing_path):
        with open(existing_path) as f:
            for line in f:
                if line.strip():
                    item = json.loads(line)
                    item.setdefault("category", "existing")
                    item.setdefault("expected", {"goalie_should_kick": None, "pass_should_occur": None})
                    all_scenarios.append(item)

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w") as f:
        for s in all_scenarios:
            f.write(json.dumps(s) + "\n")

    from collections import Counter
    cats = Counter(s["category"] for s in all_scenarios)
    print(f"Generated {len(all_scenarios)} scenarios → {OUTPUT}")
    for cat, count in sorted(cats.items()):
        print(f"  {cat:<25} {count:>3}")


if __name__ == "__main__":
    main()
