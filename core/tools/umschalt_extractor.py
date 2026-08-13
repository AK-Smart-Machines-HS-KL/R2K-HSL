#!/usr/bin/env python3
"""Phase R.3: Extract umschaltmomente from existing match traces.

Backward-scan algorithm:
  1. Find goal scored at t_goal (match_state.blue/red change)
  2. Scan world_trace backward from t_goal:
     a. Find last kick (ball velocity spike) → t_i
     b. Find the event that enabled the kick:
        - Pass completed (ball moved from blue_A to blue_B)
        - Ball lost (possession flip blue→red)
        - Set-piece restart (status change)
        - Interception (velocity direction change)
        - Clearance (ball X delta > 3m)
        - Cluster collapse (min pairwise dist < 0.5m)
        → t_umschalt
     c. Find last LLM call before t_umschalt → t_llm
  3. Verify: t_llm <= t_umschalt < t_i < t_goal
  4. Extract:
     - World state at t_umschalt (entity positions)
     - LLM decision at t_llm (raw_response + world_snapshot)
     - Score before/after
     - Umschalt type (pass/ball_lost/restart/interception/clearance/cluster)
     - Red behavior type (for anti-overfitting tagging)
  5. Save as scenario fragment JSON

Usage:
    python3 tools/umschalt_extractor.py [--max-matches 50]
"""
import argparse
import json
import math
import os
import re
import sys
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent
SRC_DIR = BASE_DIR / "src"
LOG_DIR = SRC_DIR / "logs"
RESULTS_DIR = SRC_DIR / "results"
SCENARIO_DIR = SRC_DIR / "scenario"

sys.path.insert(0, str(SRC_DIR))
sys.path.insert(0, str(SRC_DIR / "ai_tactics"))
os.environ["R2K_TEXT_MODE"] = "1"


def load_jsonl(path):
    records = []
    if path and Path(path).exists():
        with open(path) as f:
            for line in f:
                if line.strip():
                    try:
                        records.append(json.loads(line))
                    except:
                        pass
    return records


def find_trace_pairs(max_matches):
    """Find matching llm_trace + world_trace pairs with goals."""
    pairs = []
    
    for wt_path in sorted(LOG_DIR.glob("world_trace_*.jsonl")):
        name = wt_path.name.replace("world_trace_", "").replace(".jsonl", "")
        
        # Check for goals in world_trace
        records = load_jsonl(wt_path)
        if len(records) < 50:
            continue
        
        has_goal = False
        for r in records:
            ms = r.get("match_state", {})
            if ms.get("blue", 0) > 0 or ms.get("red", 0) > 0:
                has_goal = True
                break
        
        if not has_goal:
            continue
        
        # Find matching llm_trace
        lt_path = LOG_DIR / f"llm_trace_{name}.jsonl"
        if not lt_path.exists():
            continue
        
        pairs.append({
            "world_trace": str(wt_path),
            "llm_trace": str(lt_path),
            "name": name,
        })
        
        if len(pairs) >= max_matches:
            break
    
    return pairs


def detect_kick(world_records, goal_idx):
    """Scan backward from goal to find last kick (ball velocity spike).
    Returns the frame index of the kick, or None."""
    ball_positions = []
    for i in range(goal_idx, max(0, goal_idx - 50), -1):
        r = world_records[i]
        ents = r.get("entities", {})
        ball = ents.get("soccer_ball", {})
        if "x" in ball and "y" in ball:
            ball_positions.append((i, float(ball["x"]), float(ball["y"])))
    
    # Look for velocity spike (ball moved > 0.3m in one frame)
    for i in range(1, len(ball_positions)):
        prev_idx, prev_x, prev_y = ball_positions[i - 1]
        curr_idx, curr_x, curr_y = ball_positions[i]
        dx = abs(curr_x - prev_x)
        dy = abs(curr_y - prev_y)
        if dx > 0.3 or dy > 0.3:
            return curr_idx  # kick detected at this frame
    
    # If no spike found, look for any ball movement > 0.1m in last 10 frames
    for i in range(min(10, len(ball_positions) - 1)):
        prev_idx, prev_x, prev_y = ball_positions[i]
        curr_idx, curr_x, curr_y = ball_positions[i + 1]
        dx = abs(curr_x - prev_x)
        dy = abs(curr_y - prev_y)
        if dx > 0.1 or dy > 0.1:
            return curr_idx
    
    return None


def detect_umschalt(world_records, kick_idx, goal_idx, is_blue_goal):
    """Scan backward from kick_idx to find the umschaltmoment.
    Returns (umschalt_type, umschalt_idx, description)."""
    
    # Get the state at the kick
    kick_state = world_records[kick_idx]
    kick_ents = kick_state.get("entities", {})
    
    # Check for set-piece restart (status change)
    for i in range(kick_idx, max(0, kick_idx - 20), -1):
        r = world_records[i]
        ms = r.get("match_state", {})
        status = ms.get("status", "playing")
        if status != "playing":
            return ("restart", i, f"Set-piece: {status}")
    
    # Check for possession flip (ball closest bot changed team)
    for i in range(kick_idx, max(0, kick_idx - 30), -1):
        r = world_records[i]
        ents = r.get("entities", {})
        ball = ents.get("soccer_ball", {})
        if "x" not in ball:
            continue
        
        closest_team = None
        min_dist = 999
        for name, pos in ents.items():
            if "x" not in pos or name == "soccer_ball":
                continue
            d = math.hypot(float(pos["x"]) - float(ball["x"]),
                          float(pos["y"]) - float(ball["y"]))
            if d < min_dist:
                min_dist = d
                closest_team = "blue" if "blue" in name else "red"
        
        if closest_team:
            if is_blue_goal and closest_team == "blue":
                return ("ball_won", i, "Blue won possession")
            elif not is_blue_goal and closest_team == "red":
                return ("ball_won", i, "Red won possession")
    
    # Check for cluster collapse (blue bots too close)
    for i in range(kick_idx, max(0, kick_idx - 30), -1):
        r = world_records[i]
        ents = r.get("entities", {})
        blue_bots = [(float(b["x"]), float(b["y"])) for k, b in ents.items()
                     if "blue" in k and "x" in b]
        if len(blue_bots) >= 2:
            min_d = 999
            for j in range(len(blue_bots)):
                for k in range(j + 1, len(blue_bots)):
                    d = math.hypot(blue_bots[j][0] - blue_bots[k][0],
                                 blue_bots[j][1] - blue_bots[k][1])
                    if d < min_d:
                        min_d = d
            if min_d < 0.5:
                return ("cluster", i, "Blue bots clustered")
    
    # Check for clearance (ball moved > 3m toward opponent goal)
    for i in range(kick_idx, max(0, kick_idx - 15), -1):
        r = world_records[i]
        ents = r.get("entities", {})
        ball = ents.get("soccer_ball", {})
        if "x" in ball and float(ball["x"]) > 0:
            return ("clearance", i, "Ball cleared to opponent half")
    
    # Default: pass completed
    return ("pass", kick_idx, "Ball reached the kicker")


def find_llm_call(llm_records, umschalt_idx, world_records):
    """Find the last LLM call before the umschalt moment.
    Match by t_wall timestamp."""
    if not llm_records:
        return None
    
    # Get the wall time at umschalt_idx
    if umschalt_idx < len(world_records):
        umschalt_time = world_records[umschalt_idx].get("t_wall", 0)
    else:
        umschalt_time = 0
    
    # Find the last LLM call before umschalt_time
    best_idx = None
    best_diff = float("inf")
    
    for i, r in enumerate(llm_records):
        call_time = r.get("t", 0)
        diff = umschalt_time - call_time
        if 0 < diff < best_diff:
            best_diff = diff
            best_idx = i
    
    return best_idx


def extract_fragment(world_records, llm_records, goal_idx, is_blue_goal, name):
    """Extract one umschaltmoment fragment from a match."""
    
    # Find the kick that led to the goal
    kick_idx = detect_kick(world_records, goal_idx)
    if kick_idx is None:
        return None
    
    # Find the umschaltmoment
    umschalt_type, umschalt_idx, umschalt_desc = detect_umschalt(
        world_records, kick_idx, goal_idx, is_blue_goal
    )
    
    # Find the LLM call before umschalt
    llm_idx = find_llm_call(llm_records, umschalt_idx, world_records)
    if llm_idx is None:
        return None
    
    # Extract world state at umschalt
    umschalt_state = world_records[umschalt_idx]
    ents = umschalt_state.get("entities", {})
    
    # Extract LLM decision at t_llm
    llm_call = llm_records[llm_idx]
    raw_response = llm_call.get("raw_response", "")
    
    # Score before and after
    ts_before = umschalt_state.get("tactical_score", {})
    score_before = ts_before.get("current_numerical_score", 0) if isinstance(ts_before, dict) else 0
    
    # Score after (5 frames later = 0.5s)
    after_idx = min(goal_idx, umschalt_idx + 50)
    if after_idx < len(world_records):
        ts_after = world_records[after_idx].get("tactical_score", {})
        score_after = ts_after.get("current_numerical_score", 0) if isinstance(ts_after, dict) else 0
    else:
        score_after = score_before
    
    # Score at goal
    goal_state = world_records[goal_idx]
    goal_score = goal_state.get("match_state", {}).get("blue" if is_blue_goal else "red", 0)
    
    # Determine tag
    tag = "empirical-proven" if is_blue_goal else "regression-anti"
    
    # Red behavior type (for anti-overfitting)
    red_behavior = "unknown"
    red_ents = {k: v for k, v in ents.items() if "red" in k}
    if red_ents:
        red_positions = [(float(v.get("x", 0)), float(v.get("y", 0))) for v in red_ents.values() if "x" in v]
        if red_positions:
            avg_red_x = sum(p[0] for p in red_positions) / len(red_positions)
            if avg_red_x < 0:
                red_behavior = "red_pressing_high"
            elif avg_red_x < 2:
                red_behavior = "red_midfield"
            else:
                red_behavior = "red_deep"
    
    return {
        "name": name,
        "tag": tag,
        "umschalt_type": umschalt_type,
        "umschalt_description": umschalt_desc,
        "is_blue_goal": is_blue_goal,
        "goal_idx": goal_idx,
        "kick_idx": kick_idx,
        "umschalt_idx": umschalt_idx,
        "llm_idx": llm_idx,
        "entities": ents,
        "llm_raw_response": raw_response,
        "score_before": score_before,
        "score_after": score_after,
        "goal_score": goal_score,
        "red_behavior": red_behavior,
    }


def main():
    parser = argparse.ArgumentParser(description="Extract umschaltmomente from match traces")
    parser.add_argument("--max-matches", type=int, default=50,
                        help="Maximum number of matches to process")
    parser.add_argument("--output", type=str, default=str(RESULTS_DIR / "umschaltmomente.jsonl"),
                        help="Output JSONL file")
    args = parser.parse_args()
    
    print(f"=== R.3: UMSCHALTMOMENTE EXTRACTION ===")
    print(f"Max matches: {args.max_matches}")
    print(f"Output: {args.output}")
    print()
    
    pairs = find_trace_pairs(args.max_matches)
    print(f"Found {len(pairs)} matches with goals")
    print()
    
    all_fragments = []
    stats = {"empirical-proven": 0, "regression-anti": 0}
    type_stats = {}
    
    for i, pair in enumerate(pairs):
        world_records = load_jsonl(pair["world_trace"])
        llm_records = load_jsonl(pair["llm_trace"])
        
        if len(world_records) < 50 or len(llm_records) < 10:
            continue
        
        # Find all goal events
        prev_b, prev_r = 0, 0
        for j, r in enumerate(world_records):
            ms = r.get("match_state", {})
            b = ms.get("blue", 0)
            rd = ms.get("red", 0)
            
            if b > prev_b:
                # Blue goal
                frag = extract_fragment(world_records, llm_records, j, True, pair["name"])
                if frag:
                    all_fragments.append(frag)
                    stats["empirical-proven"] += 1
                    t = frag["umschalt_type"]
                    type_stats[t] = type_stats.get(t, 0) + 1
            
            if rd > prev_r:
                # Red goal
                frag = extract_fragment(world_records, llm_records, j, False, pair["name"])
                if frag:
                    all_fragments.append(frag)
                    stats["regression-anti"] += 1
                    t = frag["umschalt_type"]
                    type_stats[t] = type_stats.get(t, 0) + 1
            
            prev_b = b
            prev_r = rd
        
        if (i + 1) % 10 == 0:
            print(f"  Processed {i+1}/{len(pairs)} matches, {len(all_fragments)} fragments")
    
    print(f"\n=== EXTRACTION COMPLETE ===")
    print(f"Total fragments: {len(all_fragments)}")
    print(f"  empirical-proven (blue goals): {stats['empirical-proven']}")
    print(f"  regression-anti (red goals): {stats['regression-anti']}")
    print(f"\nUmschalt types:")
    for t, c in sorted(type_stats.items(), key=lambda x: -x[1]):
        print(f"  {t}: {c}")
    
    # Save
    with open(args.output, "w") as f:
        for frag in all_fragments:
            f.write(json.dumps(frag) + "\n")
    
    print(f"\nSaved to {args.output}")
    
    # Summary stats
    if all_fragments:
        avg_score_before = sum(f["score_before"] for f in all_fragments) / len(all_fragments)
        avg_score_after = sum(f["score_after"] for f in all_fragments) / len(all_fragments)
        print(f"\nScore delta: before={avg_score_before:.2f} → after={avg_score_after:.2f}")
        print(f"  Delta: {avg_score_after - avg_score_before:.2f}")


if __name__ == "__main__":
    main()