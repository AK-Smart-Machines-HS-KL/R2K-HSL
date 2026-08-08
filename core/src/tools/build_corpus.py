#!/usr/bin/env python3
"""Build tests/synthetic_worldstates/corpus.jsonl for Phase F.

Corpus = battery situations (i3_battery.SITUATIONS) + diverse frames
extracted from world_trace files + hand-crafted edge cases.

Usage:
  python3 tools/build_corpus.py [--out tests/synthetic_worldstates/corpus.jsonl]
"""

import argparse
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__)) + "/.."
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from i3_battery import SITUATIONS  # noqa: E402

LOGS_DIR = os.path.join(BASE_DIR, "logs")
TRACE_FILES = [
    "logs/world_trace_3vs3_attack_center_*.jsonl",
    "logs/world_trace_3vs3_high_line_*.jsonl",
    "logs/world_trace_3vs3_def_transition_*.jsonl",
    "logs/world_trace_3vs3_defensive_crisis_*.jsonl",
    "logs/world_trace_3vs3_fast_counter_*.jsonl",
    "logs/world_trace_3vs3_pressing_trap_*.jsonl",
]

# Hand-crafted edge cases: (label, status, score_blue, score_red, entities)
EDGE_CASES = [
    ("edge_ball_in_flight_attack", "playing", 0, 0, {
        "soccer_ball": {"x": 3.8, "y": 1.2},
        "blue_1": {"x": 2.0, "y": 0.3}, "blue_2": {"x": -1.5, "y": 1.0},
        "blue_3": {"x": -4.2, "y": 0.0},
        "red_1": {"x": 4.0, "y": 0.8}, "red_2": {"x": 0.5, "y": 1.5},
        "red_3": {"x": 4.2, "y": -1.0},
    }),
    ("edge_ball_on_own_goal_line", "playing", 0, 1, {
        "soccer_ball": {"x": -4.4, "y": 0.2},
        "blue_1": {"x": -4.0, "y": 0.2}, "blue_2": {"x": -2.0, "y": 0.8},
        "blue_3": {"x": -1.0, "y": -1.0},
        "red_1": {"x": -3.9, "y": 0.1}, "red_2": {"x": -2.5, "y": 0.0},
        "red_3": {"x": 1.0, "y": 1.0},
    }),
    ("edge_ball_corner_own", "playing", 0, 0, {
        "soccer_ball": {"x": -4.3, "y": -2.9},
        "blue_1": {"x": -3.8, "y": -2.0}, "blue_2": {"x": -2.0, "y": -0.5},
        "blue_3": {"x": -4.2, "y": 0.0},
        "red_1": {"x": -4.0, "y": -2.5}, "red_2": {"x": -1.5, "y": 1.0},
        "red_3": {"x": 1.0, "y": 0.0},
    }),
    ("edge_all_bots_own_half", "playing", 0, 0, {
        "soccer_ball": {"x": -0.5, "y": -1.5},
        "blue_1": {"x": -3.5, "y": -1.0}, "blue_2": {"x": -4.0, "y": 1.0},
        "blue_3": {"x": -4.2, "y": 0.0},
        "red_1": {"x": -1.0, "y": -1.5}, "red_2": {"x": -2.5, "y": 0.5},
        "red_3": {"x": -1.0, "y": 1.5},
    }),
    ("edge_goalie_displaced", "playing", 0, 2, {
        "soccer_ball": {"x": -3.0, "y": 2.0},
        "blue_1": {"x": 1.5, "y": 1.5}, "blue_2": {"x": -2.0, "y": 0.0},
        "blue_3": {"x": -1.0, "y": 2.2},
        "red_1": {"x": -3.2, "y": 1.8}, "red_2": {"x": -1.0, "y": 1.0},
        "red_3": {"x": 1.0, "y": -1.0},
    }),
    ("edge_ball_behind_goalie", "playing", 0, 1, {
        "soccer_ball": {"x": -4.2, "y": -1.8},
        "blue_1": {"x": -4.4, "y": -0.8}, "blue_2": {"x": -2.5, "y": -1.5},
        "blue_3": {"x": -3.5, "y": 0.5},
        "red_1": {"x": -4.0, "y": -1.6}, "red_2": {"x": -1.5, "y": 0.0},
        "red_3": {"x": 0.5, "y": 1.5},
    }),
    ("edge_kickoff_all_near_center", "kickoff", 1, 1, {
        "soccer_ball": {"x": 0.0, "y": 0.0},
        "blue_1": {"x": -0.6, "y": 0.3}, "blue_2": {"x": -1.2, "y": 0.8},
        "blue_3": {"x": -1.0, "y": -1.0},
        "red_1": {"x": 0.8, "y": 0.1}, "red_2": {"x": 1.5, "y": 1.0},
        "red_3": {"x": 1.0, "y": -1.0},
    }),
    ("edge_ball_rolling_to_sideline", "playing", 0, 0, {
        "soccer_ball": {"x": 1.5, "y": 2.9},
        "blue_1": {"x": 1.2, "y": 2.0}, "blue_2": {"x": 0.0, "y": 1.0},
        "blue_3": {"x": -4.0, "y": 0.0},
        "red_1": {"x": 1.8, "y": 2.6}, "red_2": {"x": 2.5, "y": 1.0},
        "red_3": {"x": 4.2, "y": 0.0},
    }),
    ("edge_score_pressure_0_3", "playing", 0, 3, {
        "soccer_ball": {"x": 3.0, "y": 0.5},
        "blue_1": {"x": 2.5, "y": 0.4}, "blue_2": {"x": 0.5, "y": 1.2},
        "blue_3": {"x": -4.2, "y": 0.0},
        "red_1": {"x": 3.5, "y": 0.2}, "red_2": {"x": 1.0, "y": 0.8},
        "red_3": {"x": 4.2, "y": -0.5},
    }),
    ("edge_red_numbers_advantage_deep", "playing", 1, 0, {
        "soccer_ball": {"x": -2.8, "y": 1.0},
        "blue_1": {"x": -2.5, "y": 0.8}, "blue_2": {"x": -1.0, "y": 1.5},
        "blue_3": {"x": -4.2, "y": 0.0},
        "red_1": {"x": -2.6, "y": 1.2}, "red_2": {"x": -3.5, "y": 0.5},
        "red_3": {"x": -3.0, "y": -0.5},
    }),
]


SCENARIO_DIR = os.path.join(BASE_DIR, "scenario")
SYNTH_DIR = os.path.join(BASE_DIR, "tests", "synthetic_worldstates")


def walk_scenario_dirs(empirical_only=False, handcrafted_only=False):
    """Walk scenario/*/scenario.json, return list of corpus entries.
    Skips dirs without scenario.json or without soccer_ball entity."""
    import glob as _glob
    entries = []
    for sj in sorted(_glob.glob(os.path.join(SCENARIO_DIR, "*", "scenario.json"))):
        name = os.path.basename(os.path.dirname(sj))
        is_emp = name.startswith("emp_")
        if empirical_only and not is_emp:
            continue
        if handcrafted_only and is_emp:
            continue
        try:
            with open(sj, encoding="utf-8") as f:
                s = json.load(f)
        except Exception:
            continue
        ents = s.get("entities", {})
        if "soccer_ball" not in ents:
            continue
        entries.append({
            "label": name,
            "status": "playing",
            "score_blue": 0,
            "score_red": 0,
            "entities": ents,
        })
    return entries


def load_trace_frames(paths, per_file=10, max_total=45):
    """Sample frames evenly from trace files, dedupe near-identical states."""
    seen = set()
    frames = []
    import glob
    files = []
    for p in paths:
        files.extend(sorted(glob.glob(os.path.join(BASE_DIR, p))))
    for fp in files[:8]:
        try:
            recs = [json.loads(l) for l in open(fp, encoding="utf-8")
                    if l.strip()]
        except Exception:
            continue
        if not recs:
            continue
        n = min(per_file, len(recs))
        idxs = {int(i * (len(recs) - 1) / (n - 1)) for i in range(n)} if n > 1 \
            else {0}
        for i in sorted(idxs):
            r = recs[i]
            ents = r.get("entities", {})
            if "soccer_ball" not in ents or len(ents) < 5:
                continue
            key = tuple(sorted(
                (k, round(v["x"], 1), round(v["y"], 1))
                for k, v in ents.items() if isinstance(v, dict)
                and "x" in v and "y" in v))
            if key in seen:
                continue
            seen.add(key)
            ms = r.get("match_state", {})
            frames.append({
                "label": f"trace_{os.path.basename(fp)[:20]}_{i}",
                "status": ms.get("status", "playing"),
                "score_blue": ms.get("blue", 0),
                "score_red": ms.get("red", 0),
                "entities": ents,
            })
            if len(frames) >= max_total:
                return frames
    return frames


def main():
    ap = argparse.ArgumentParser(description="Build Phase F synthetic corpus")
    ap.add_argument("--out", default=os.path.join(SYNTH_DIR, "corpus.jsonl"))
    ap.add_argument("--scenarios", action="store_true",
                    help="also write corpus_scenarios.jsonl (all 50), "
                         "corpus_handcrafted_17.jsonl, corpus_empirical_33.jsonl")
    args = ap.parse_args()

    corpus = []
    for i, (label, status, sb, sr, ents) in enumerate(SITUATIONS, 1):
        corpus.append({"label": f"battery_{label}", "status": status,
                       "score_blue": sb, "score_red": sr, "entities": ents})
    for label, status, sb, sr, ents in EDGE_CASES:
        corpus.append({"label": label, "status": status,
                       "score_blue": sb, "score_red": sr, "entities": ents})
    frames = load_trace_frames(TRACE_FILES)
    corpus.extend(frames)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for s in corpus:
            f.write(json.dumps(s) + "\n")
    from collections import Counter
    statuses = Counter(s["status"] for s in corpus)
    print(f"Corpus: {len(corpus)} states "
          f"(battery {len(SITUATIONS)}, edge {len(EDGE_CASES)}, "
          f"trace {len(frames)})")
    print(f"Statuses: {dict(statuses)}")
    print(f"Written: {args.out}")

    if args.scenarios:
        all_scen = walk_scenario_dirs()
        hc = walk_scenario_dirs(handcrafted_only=True)
        emp = walk_scenario_dirs(empirical_only=True)
        for suffix, data in (
            ("corpus_scenarios.jsonl", all_scen),
            ("corpus_handcrafted_17.jsonl", hc),
            ("corpus_empirical_33.jsonl", emp),
        ):
            path = os.path.join(SYNTH_DIR, suffix)
            with open(path, "w", encoding="utf-8") as f:
                for s in data:
                    f.write(json.dumps(s) + "\n")
            print(f"Written: {path} ({len(data)} scenarios)")


if __name__ == "__main__":
    main()
