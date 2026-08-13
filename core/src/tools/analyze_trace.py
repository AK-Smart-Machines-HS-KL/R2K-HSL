#!/usr/bin/env python3
"""Measurement script — computes KPIs from LLM and world-state trace logs.

Reads:
  logs/llm_trace_<run_id>.jsonl   (one line per LLM call)
  logs/world_trace_<run_id>.jsonl  (one line per world-state write, ~10Hz)

Computes:
  goals_for_blue / goals_for_red   — score increments
  cluster_frames                    — frames where min pairwise blue-bot dist < 0.5m
  goalie_idle_frames                — frames where goalie moved < 0.05m
  goalie_tactical_pct               — % frames goalie in tactically useful position
  oob_frames_blue                   — blue bot outside field bounds
   ball_possession_blue_pct          — % frames closest bot to ball is blue
   latency_p50/p95/max               — from latency_ms
   parse_error_rate                  — % calls with parse_code > 0
   avg_response_tokens               — len(raw_response)/4
  shots_on_goal [2.5]               — Kick actions (kicker in opp half, ball ≤2m)
                                     where ball moves toward opp goal after kick
  shots_on_target [2.5]             — subset where ball Y at x=4.5 within ±1.3m
  pass_completion_pct [2.5]         — % Pass actions where different blue bot
                                     closest to ball within 2s
  restart_recovery_time_s [2.5]     — mean time from status!=playing to
                                     restart-team bot within 0.3m of ball

Usage:
  python3 tools/analyze_trace.py --run-id test_001
  python3 tools/analyze_trace.py --run-id test_001 --output results/
  python3 tools/analyze_trace.py --run-id test_001 --plot
  python3 tools/analyze_trace.py --stats-a "results/kpis_C6_current_*.json" --stats-b "results/kpis_C6_3sample_*.json"
"""
import argparse
import bisect
import glob
import json
import math
import os
import re
import statistics
import sys
from collections import Counter

FIELD_X_MIN, FIELD_X_MAX = -4.5, 4.5
FIELD_Y_MIN, FIELD_Y_MAX = -3.0, 3.0
CLUSTER_THRESHOLD = 0.5
GOALIE_IDLE_THRESHOLD = 0.05
OOB_MARGIN = 0.1  # bots slightly outside count as OOB

# Goalie tactical position thresholds (Phase 2a). Must match bridge constants.
GOALIE_NEAR_GOAL_DIST = 1.0
GOALIE_FAR_GOAL_DIST  = 4.0
GOALIE_LINE_X = -4.3
GOALIE_NEAR_X_MIN = -4.5
GOALIE_NEAR_X_MAX = -3.5
GOALIE_Y_TOL = 0.8

# Attack/passing/restart KPI thresholds (Phase 2.5a)
OPP_GOAL_X = 4.5            # opponent goal line
GOAL_HALF_WIDTH = 1.3       # goal posts at y = ±1.3
SHOT_KICKER_OPP_HALF = 0.0  # kicker x > 0 = in opponent half
SHOT_BALL_NEAR_KICKER = 2.0 # ball within 2m of kicker at kick time
SHOT_BALL_VX_THRESHOLD = 0.5 # ball x-velocity (m/s) > this = "toward opp goal"
SHOT_FOLLOW_FRAMES = 5      # frames (0.5s) after kick to check ball movement
PASS_FOLLOW_FRAMES = 20     # frames (2s) after pass to check receiver touch
RESTART_TOUCH_DIST = 0.35    # restart-team bot within this of ball = recovery
                            # (0.35 not 0.3 to account for tracker noise —
                            # the referee uses 0.3m for early termination, but
                            # the tracker rounds to 0.1m precision)
SHOT_EXTRAPOLATE_FRAMES = 10 # frames (1s) to extrapolate ball trajectory for on-target


def load_jsonl(path):
    records = []
    if not os.path.exists(path):
        return records
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def extract_assignments(raw_response):
    """Extract assignments dict from raw LLM response."""
    try:
        start = raw_response.find('{')
        end = raw_response.rfind('}')
        if start == -1 or end == -1:
            return {}
        json_str = raw_response[start:end + 1]
        json_str = re.sub(r',\s*\}', '}', json_str)
        json_str = re.sub(r',\s*\]', ']', json_str)
        data = json.loads(json_str)
        return data.get("assignments", data)
    except Exception:
        return {}


def compute_attack_kpis(world_records, llm_records):
    """Phase 2.5a — 4 attack/passing/restart KPIs.

    Joins llm_trace (Kick/Pass actions + world_snapshot at decision time) with
    world_trace (ball position deltas after the action) to measure soccer behavior
    that the existing KPIs (goals, possession) cannot detect.

    Returns dict with: shots_on_goal, shots_on_target, pass_completion_pct,
    restart_recovery_time_s, pass_attempts, restart_events.
    """
    if not world_records or not llm_records:
        return {
            "shots_on_goal": 0, "shots_on_target": 0,
            "pass_attempts": 0, "pass_completion_pct": 0.0,
            "restart_events": 0, "restart_recovery_time_s": 0.0,
        }

    # Build a time-indexed list of world frames for the post-action lookup.
    # world_records are ~10Hz (0.1s apart); llm_records have a `t` timestamp.
    # Use t_wall (wall-clock) as the common timeline — sim-time (t) is 0.0
    # in existing traces (libgazebo_ros_init.so not yet rebuilt into container).
    world_times = [r.get("t_wall", r.get("t", 0)) for r in world_records]

    def find_world_frame_after(t, n_frames):
        """Return the index of the first world frame at or after time t, plus
        the next n_frames indices. Returns (start_idx, [idx_list])."""
        # Binary search for the first frame with t >= target
        lo, hi = 0, len(world_times)
        while lo < hi:
            mid = (lo + hi) // 2
            if world_times[mid] < t:
                lo = mid + 1
            else:
                hi = mid
        start = lo
        indices = list(range(start, min(start + n_frames, len(world_records))))
        return start, indices

    # === shots_on_goal + shots_on_target ===
    shots_on_goal = 0
    shots_on_target = 0
    for llm_rec in llm_records:
        assignments = extract_assignments(llm_rec.get("raw_response", ""))
        snapshot = llm_rec.get("world_snapshot", {})
        ball_snap = snapshot.get("soccer_ball", {})
        if not ball_snap:
            continue
        call_t = llm_rec.get("t", 0)
        for bot_name, task in assignments.items():
            if not isinstance(task, dict):
                continue
            if task.get("action") != "Kick":
                continue
            if "blue" not in bot_name:
                continue
            kicker_snap = snapshot.get(bot_name, {})
            kx = kicker_snap.get("x", 0)
            # Shot: kicker in opponent half, ball near kicker
            if kx <= SHOT_KICKER_OPP_HALF:
                continue
            ball_dist = math.hypot(ball_snap.get("x", 0) - kx,
                                   ball_snap.get("y", 0) - kicker_snap.get("y", 0))
            if ball_dist > SHOT_BALL_NEAR_KICKER:
                continue
            # Look at ball position in the SHOT_FOLLOW_FRAMES after the call
            _, follow_idxs = find_world_frame_after(call_t, SHOT_FOLLOW_FRAMES)
            if not follow_idxs:
                continue
            # Ball velocity: compare first follow frame to the snapshot
            # (the snapshot is ~800ms stale; the first follow frame is ~current)
            first_frame = world_records[follow_idxs[0]]
            ball_after = first_frame.get("entities", {}).get("soccer_ball", {})
            if not ball_after:
                continue
            dt = world_times[follow_idxs[0]] - call_t
            if dt <= 0:
                dt = 0.1
            vx = (ball_after.get("x", 0) - ball_snap.get("x", 0)) / dt
            if vx <= SHOT_BALL_VX_THRESHOLD:
                continue
            # Ball moved toward opponent goal → it's a shot on goal
            shots_on_goal += 1
            # On target: extrapolate ball Y at x=OPP_GOAL_X
            ball_x = ball_after.get("x", 0)
            ball_y = ball_after.get("y", 0)
            # Use velocity from the follow window (first to last follow frame)
            if len(follow_idxs) >= 2:
                last_frame = world_records[follow_idxs[-1]]
                ball_last = last_frame.get("entities", {}).get("soccer_ball", {})
                dt_window = world_times[follow_idxs[-1]] - world_times[follow_idxs[0]]
                if dt_window > 0:
                    vx = (ball_last.get("x", 0) - ball_x) / dt_window
                    vy = (ball_last.get("y", 0) - ball_y) / dt_window
            if vx > 0:
                t_to_goal = (OPP_GOAL_X - ball_x) / vx
                y_at_goal = ball_y + vy * t_to_goal
                if abs(y_at_goal) <= GOAL_HALF_WIDTH:
                    shots_on_target += 1

    # === pass_completion_pct ===
    pass_attempts = 0
    pass_completions = 0
    for llm_rec in llm_records:
        assignments = extract_assignments(llm_rec.get("raw_response", ""))
        snapshot = llm_rec.get("world_snapshot", {})
        call_t = llm_rec.get("t", 0)
        for bot_name, task in assignments.items():
            if not isinstance(task, dict):
                continue
            if task.get("action") != "Kick":
                continue
            if "blue" not in bot_name:
                continue
            kicker_snap = snapshot.get(bot_name, {})
            # Position-based pass detection: a Kick by a blue bot NOT in the
            # opponent half is a pass attempt (not a shot). Role-independent —
            # works with any role naming scheme (3-role: goalie/attacker/defender).
            if kicker_snap.get("x", 0) > SHOT_KICKER_OPP_HALF:
                continue  # in opponent half → likely a shot, not a pass
            pass_attempts += 1
            # Check if a DIFFERENT blue bot is closest to ball within 2s
            _, follow_idxs = find_world_frame_after(call_t, PASS_FOLLOW_FRAMES)
            for idx in follow_idxs:
                frame = world_records[idx]
                ents = frame.get("entities", {})
                ball = ents.get("soccer_ball", {})
                if not ball:
                    continue
                bx, by = ball.get("x", 0), ball.get("y", 0)
                min_dist = float('inf')
                closest_bot = None
                for bname, bpos in ents.items():
                    if "blue" not in bname:
                        continue
                    d = math.hypot(bpos.get("x", 0) - bx, bpos.get("y", 0) - by)
                    if d < min_dist:
                        min_dist = d
                        closest_bot = bname
                if closest_bot and closest_bot != bot_name:
                    pass_completions += 1
                    break  # one completion per pass attempt

    pass_completion_pct = round(pass_completions / max(pass_attempts, 1) * 100, 1) if pass_attempts > 0 else 0.0

    # === restart_recovery_time_s ===
    restart_events = 0
    restart_recovery_times = []
    prev_status = "playing"
    for i, rec in enumerate(world_records):
        match_state = rec.get("match_state", {})
        status = match_state.get("status", "playing")
        # Detect transition into a non-playing status
        if prev_status == "playing" and status != "playing":
            restart_team = match_state.get("restart_team")
            if not restart_team:
                prev_status = status
                continue
            # Forward-scan for first frame where a restart-team bot is within
            # RESTART_TOUCH_DIST of the ball
            ents = rec.get("entities", {})
            ball = ents.get("soccer_ball", {})
            if not ball:
                prev_status = status
                continue
            bx, by = ball.get("x", 0), ball.get("y", 0)
            t_start = rec.get("t_wall", rec.get("t", 0))
            for j in range(i, len(world_records)):
                frame = world_records[j]
                fents = frame.get("entities", {})
                fball = fents.get("soccer_ball", {})
                if not fball:
                    continue
                fbx, fby = fball.get("x", 0), fball.get("y", 0)
                for bname, bpos in fents.items():
                    if restart_team not in bname:
                        continue
                    d = math.hypot(bpos.get("x", 0) - fbx, bpos.get("y", 0) - fby)
                    if d <= RESTART_TOUCH_DIST:
                        restart_events += 1
                        restart_recovery_times.append(frame.get("t_wall", frame.get("t", 0)) - t_start)
                        break
                else:
                    continue
                break  # found recovery for this restart
        prev_status = status

    restart_recovery_time_s = round(statistics.mean(restart_recovery_times), 2) if restart_recovery_times else 0.0

    return {
        "shots_on_goal": shots_on_goal,
        "shots_on_target": shots_on_target,
        "pass_attempts": pass_attempts,
        "pass_completion_pct": pass_completion_pct,
        "restart_events": restart_events,
        "restart_recovery_time_s": restart_recovery_time_s,
    }


def compute_world_kpis(world_records):
    if not world_records:
        return {
            "frames": 0, "goals_for_blue": 0, "goals_for_red": 0,
            "cluster_frames": 0, "goalie_idle_frames": 0, "oob_frames_blue": 0,
            "ball_possession_blue_pct": 0.0, "duration_s": 0.0,
            "status_distribution": {},
        }

    goals_blue = 0
    goals_red = 0
    prev_blue_score = 0
    prev_red_score = 0
    cluster_frames = 0
    oob_frames = 0
    blue_closest_frames = 0
    frames_with_bots = 0
    status_counter = Counter()

    prev_goalie_pos = None
    goalie_idle_frames = 0
    goalie_frames = 0
    goalie_tactical_frames = 0

    tactical_score_avg_sum = 0.0
    tactical_score_avg_count = 0
    tactical_score_final = 0.0

    t_first = world_records[0].get("t", 0)
    t_last = world_records[-1].get("t", 0)

    for rec in world_records:
        entities = rec.get("entities", {})
        match_state = rec.get("match_state", {})

        # Score tracking
        blue_score = match_state.get("blue", 0)
        red_score = match_state.get("red", 0)
        if blue_score > prev_blue_score:
            goals_blue += blue_score - prev_blue_score
        if red_score > prev_red_score:
            goals_red += red_score - prev_red_score
        prev_blue_score = blue_score
        prev_red_score = red_score

        # Status distribution
        status = match_state.get("status", "playing")
        status_counter[status] += 1

        # Tactical score tracking
        tac_score = rec.get("tactical_score", {})
        avg_score = tac_score.get("average_numerical_score")
        if avg_score is not None:
            tactical_score_avg_sum += avg_score
            tactical_score_avg_count += 1
        cur_score = tac_score.get("current_numerical_score")
        if cur_score is not None:
            tactical_score_final = cur_score

        # Entity positions
        blue_bots = {k: v for k, v in entities.items() if "blue" in k}
        red_bots = {k: v for k, v in entities.items() if "red" in k}
        ball = entities.get("soccer_ball")

        if not blue_bots:
            continue
        frames_with_bots += 1

        # Cluster detection: min pairwise distance among blue bots
        blue_positions = list(blue_bots.values())
        min_pairwise = float('inf')
        for i in range(len(blue_positions)):
            for j in range(i + 1, len(blue_positions)):
                p1, p2 = blue_positions[i], blue_positions[j]
                d = math.hypot(p1.get("x", 0) - p2.get("x", 0),
                               p1.get("y", 0) - p2.get("y", 0))
                if d < min_pairwise:
                    min_pairwise = d
        if min_pairwise < CLUSTER_THRESHOLD:
            cluster_frames += 1

        # Out-of-bounds detection
        for bot_name, pos in blue_bots.items():
            x, y = pos.get("x", 0), pos.get("y", 0)
            if x < FIELD_X_MIN - OOB_MARGIN or x > FIELD_X_MAX + OOB_MARGIN or \
               y < FIELD_Y_MIN - OOB_MARGIN or y > FIELD_Y_MAX + OOB_MARGIN:
                oob_frames += 1
                break  # one OOB bot per frame counts as 1

        # Ball possession: closest bot to ball
        if ball:
            ball_x, ball_y = ball.get("x", 0), ball.get("y", 0)
            min_dist = float('inf')
            closest_is_blue = False
            for bot_name, pos in {**blue_bots, **red_bots}.items():
                d = math.hypot(pos.get("x", 0) - ball_x, pos.get("y", 0) - ball_y)
                if d < min_dist:
                    min_dist = d
                    closest_is_blue = "blue" in bot_name
            if closest_is_blue:
                blue_closest_frames += 1

        # Goalie idle detection: find the bot with "goalie" role from last LLM assignment
        # We approximate: the blue bot closest to own goal (x=-4.5) is likely the goalie
        goalie_candidate = None
        goalie_min_x = float('inf')
        for bot_name, pos in blue_bots.items():
            x = pos.get("x", 0)
            if x < goalie_min_x:
                goalie_min_x = x
                goalie_candidate = bot_name
        if goalie_candidate and prev_goalie_pos:
            gx = blue_bots[goalie_candidate].get("x", 0)
            gy = blue_bots[goalie_candidate].get("y", 0)
            dx = gx - prev_goalie_pos[0]
            dy = gy - prev_goalie_pos[1]
            if math.hypot(dx, dy) < GOALIE_IDLE_THRESHOLD:
                goalie_idle_frames += 1
            goalie_frames += 1

            # Goalie tactical position check (Phase 2a):
            # Ball far  -> goalie should be forward (angle-block), X > GOALIE_LINE_X
            # Ball near -> goalie should be near goal line, X in [-4.5, -3.5], Y tracks ball
            if ball:
                ball_dist_to_goal = math.hypot(ball.get("x", 0) - FIELD_X_MIN,
                                                ball.get("y", 0))
                if ball_dist_to_goal >= GOALIE_FAR_GOAL_DIST:
                    # Far zone: goalie should not be parked at the line
                    if gx > GOALIE_LINE_X + 0.2:
                        goalie_tactical_frames += 1
                elif ball_dist_to_goal <= GOALIE_NEAR_GOAL_DIST:
                    # Near zone: goalie near goal line and Y within tolerance of ball Y
                    expected_y = max(-1.5, min(1.5, ball.get("y", 0) * 0.5))
                    if GOALIE_NEAR_X_MIN <= gx <= GOALIE_NEAR_X_MAX and \
                       abs(gy - expected_y) <= GOALIE_Y_TOL:
                        goalie_tactical_frames += 1
                else:
                    # Mid zone: accept either position (transition area)
                    goalie_tactical_frames += 1
        if goalie_candidate:
            gx = blue_bots[goalie_candidate].get("x", 0)
            gy = blue_bots[goalie_candidate].get("y", 0)
            prev_goalie_pos = (gx, gy)

    return {
        "frames": len(world_records),
        "frames_with_bots": frames_with_bots,
        "duration_s": round(t_last - t_first, 1),
        "goals_for_blue": goals_blue,
        "goals_for_red": goals_red,
        "cluster_frames": cluster_frames,
        "cluster_pct": round(cluster_frames / max(frames_with_bots, 1) * 100, 1),
        "goalie_idle_frames": goalie_idle_frames,
        "goalie_idle_pct": round(goalie_idle_frames / max(goalie_frames, 1) * 100, 1),
        "goalie_tactical_pct": round(goalie_tactical_frames / max(goalie_frames, 1) * 100, 1),
        "oob_frames_blue": oob_frames,
        "oob_pct": round(oob_frames / max(frames_with_bots, 1) * 100, 1),
        "ball_possession_blue_pct": round(blue_closest_frames / max(frames_with_bots, 1) * 100, 1),
        "tactical_score_avg": round(tactical_score_avg_sum / max(tactical_score_avg_count, 1), 2),
        "tactical_score_final": round(tactical_score_final, 2),
        "status_distribution": dict(status_counter),
    }


def compute_llm_kpis(llm_records):
    if not llm_records:
        return {
            "llm_calls": 0, "latency_p50": 0, "latency_p95": 0, "latency_max": 0,
            "parse_error_rate": 0.0, "avg_response_tokens": 0,
            "roles": {},
        }

    latencies = [r.get("latency_ms", 0) for r in llm_records]
    parse_errors = sum(1 for r in llm_records if r.get("parse_code", 0) > 0)
    response_tokens = [len(r.get("raw_response", "")) / 4 for r in llm_records]

    # Role counter (diagnostic only — role_diversity dropped as dead metric,
    # CV=0% across 27 v6.3 baseline runs. See kpi_regression_analysis_2026-07-27.md)
    role_counter = Counter()
    for r in llm_records:
        assignments = extract_assignments(r.get("raw_response", ""))
        for bot, task in assignments.items():
            if isinstance(task, dict) and "role" in task:
                role_counter[task["role"]] += 1

    latencies_sorted = sorted(latencies)
    n = len(latencies_sorted)

    return {
        "llm_calls": n,
        "latency_p50": latencies_sorted[n // 2] if n > 0 else 0,
        "latency_p95": latencies_sorted[int(n * 0.95)] if n > 0 else 0,
        "latency_max": max(latencies) if latencies else 0,
        "latency_mean": round(statistics.mean(latencies), 0) if latencies else 0,
        "parse_error_rate": round(parse_errors / n * 100, 1),
        "roles": dict(role_counter.most_common(20)),
        "avg_response_tokens": round(statistics.mean(response_tokens), 0) if response_tokens else 0,
        "explain_mode": llm_records[0].get("explain", None),
        "model": llm_records[0].get("model", "unknown"),
    }


def main():
    parser = argparse.ArgumentParser(description="Analyze LLM + world trace logs")
    parser.add_argument('--run-id', type=str, default=None,
                        help='Run ID (matches R2K_RUN_ID used during launch)')
    parser.add_argument('--log-dir', type=str, default=None,
                        help='Override log directory (default: ../logs relative to this script)')
    parser.add_argument('--output', type=str, default=None,
                        help='Output JSON file (default: print to stdout)')
    parser.add_argument('--plot', action='store_true',
                        help='Generate matplotlib plots (latency histogram, score timeline)')
    parser.add_argument('--stats-a', type=str, default=None,
                        help='Glob pattern for group A KPI JSONs (for --stats comparison mode)')
    parser.add_argument('--stats-b', type=str, default=None,
                        help='Glob pattern for group B KPI JSONs (for --stats comparison mode)')
    args = parser.parse_args()

    # Stats comparison mode: compare two groups of KPI JSONs
    if args.stats_a and args.stats_b:
        stats_comparison(args)
        return

    if args.stats_a or args.stats_b:
        print("ERROR: --stats requires both --stats-a and --stats-b", file=sys.stderr)
        sys.exit(1)

    if not args.run_id:
        print("ERROR: --run-id is required (or use --stats-a + --stats-b for comparison mode)", file=sys.stderr)
        sys.exit(1)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.dirname(script_dir)
    log_dir = args.log_dir or os.path.join(src_dir, "logs")

    llm_path = os.path.join(log_dir, f"llm_trace_{args.run_id}.jsonl")
    world_path = os.path.join(log_dir, f"world_trace_{args.run_id}.jsonl")

    llm_records = load_jsonl(llm_path)
    world_records = load_jsonl(world_path)

    if not llm_records and not world_records:
        print(f"ERROR: No trace files found for run-id '{args.run_id}' in {log_dir}", file=sys.stderr)
        print(f"  Expected: {llm_path}", file=sys.stderr)
        print(f"  Expected: {world_path}", file=sys.stderr)
        sys.exit(1)

    world_kpis = compute_world_kpis(world_records)
    llm_kpis = compute_llm_kpis(llm_records)
    attack_kpis = compute_attack_kpis(world_records, llm_records)
    # Merge attack KPIs into world_kpis for backward-compatible output structure
    world_kpis.update(attack_kpis)

    result = {
        "run_id": args.run_id,
        "llm_trace_file": llm_path,
        "world_trace_file": world_path,
        "world_kpis": world_kpis,
        "llm_kpis": llm_kpis,
    }

    output_json = json.dumps(result, indent=2)

    if args.output:
        os.makedirs(args.output, exist_ok=True)
        out_path = os.path.join(args.output, f"kpis_{args.run_id}.json")
        with open(out_path, 'w') as f:
            f.write(output_json)
        print(f"KPIs written to {out_path}")
    else:
        print(output_json)

    # Human-readable summary
    print("\n" + "=" * 60)
    print(f"KPI SUMMARY — {args.run_id}")
    print("=" * 60)
    print(f"Duration:        {world_kpis.get('duration_s', 0)}s  ({world_kpis.get('frames', 0)} frames)")
    print(f"Goals:           Blue {world_kpis.get('goals_for_blue', 0)} : {world_kpis.get('goals_for_red', 0)} Red")
    print(f"Tactical score:  avg={world_kpis.get('tactical_score_avg', 0):.2f}  final={world_kpis.get('tactical_score_final', 0):.2f}")
    print(f"Possession:      {world_kpis.get('ball_possession_blue_pct', 0)}% blue")
    print(f"Cluster frames:  {world_kpis.get('cluster_frames', 0)} ({world_kpis.get('cluster_pct', 0)}%)")
    print(f"Goalie idle:     {world_kpis.get('goalie_idle_frames', 0)} ({world_kpis.get('goalie_idle_pct', 0)}%)")
    print(f"OOB frames:      {world_kpis.get('oob_frames_blue', 0)} ({world_kpis.get('oob_pct', 0)}%)")
    print(f"Status dist:     {world_kpis.get('status_distribution', {})}")
    print("-" * 60)
    print(f"Shots on goal:   {world_kpis.get('shots_on_goal', 0)} (on target: {world_kpis.get('shots_on_target', 0)})")
    print(f"Pass attempts:   {world_kpis.get('pass_attempts', 0)} ({world_kpis.get('pass_completion_pct', 0)}% completed)")
    print(f"Restart events:  {world_kpis.get('restart_events', 0)} (mean recovery: {world_kpis.get('restart_recovery_time_s', 0)}s)")
    print("-" * 60)
    print(f"LLM calls:       {llm_kpis.get('llm_calls', 0)}")
    print(f"Latency p50:     {llm_kpis.get('latency_p50', 0)}ms")
    print(f"Latency p95:     {llm_kpis.get('latency_p95', 0)}ms")
    print(f"Latency max:     {llm_kpis.get('latency_max', 0)}ms")
    print(f"Parse errors:    {llm_kpis.get('parse_error_rate', 0)}%")
    print(f"Roles:           {llm_kpis.get('roles', {})}")
    print("=" * 60)

    if args.plot:
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt

            plot_dir = args.output or os.path.join(src_dir, "results")
            os.makedirs(plot_dir, exist_ok=True)

            # Latency histogram
            if latencies := [r.get("latency_ms", 0) for r in llm_records]:
                fig, ax = plt.subplots(figsize=(8, 4))
                ax.hist(latencies, bins=30, edgecolor='black', alpha=0.7)
                ax.set_xlabel('Latency (ms)')
                ax.set_ylabel('Count')
                ax.set_title(f'LLM Latency — {args.run_id}')
                ax.axvline(llm_kpis["latency_p50"], color='green', linestyle='--', label=f'p50={llm_kpis["latency_p50"]}ms')
                ax.axvline(llm_kpis["latency_p95"], color='red', linestyle='--', label=f'p95={llm_kpis["latency_p95"]}ms')
                ax.legend()
                plot_path = os.path.join(plot_dir, f"latency_{args.run_id}.png")
                fig.savefig(plot_path, dpi=100, bbox_inches='tight')
                plt.close(fig)
                print(f"Plot saved: {plot_path}")

            # Score timeline
            if world_records:
                times = [r.get("t", 0) - world_records[0].get("t", 0) for r in world_records]
                blue_scores = [r.get("match_state", {}).get("blue", 0) for r in world_records]
                red_scores = [r.get("match_state", {}).get("red", 0) for r in world_records]
                fig, ax = plt.subplots(figsize=(8, 3))
                ax.plot(times, blue_scores, 'b-', label='Blue', linewidth=2)
                ax.plot(times, red_scores, 'r-', label='Red', linewidth=2)
                ax.set_xlabel('Time (s)')
                ax.set_ylabel('Score')
                ax.set_title(f'Match Score — {args.run_id}')
                ax.legend()
                ax.grid(True, alpha=0.3)
                plot_path = os.path.join(plot_dir, f"score_{args.run_id}.png")
                fig.savefig(plot_path, dpi=100, bbox_inches='tight')
                plt.close(fig)
                print(f"Plot saved: {plot_path}")

        except ImportError:
            print("matplotlib not available, skipping plots", file=sys.stderr)


# --- C6: Statistical comparison of two experiment groups ---

STAT_KPIS = [
    ("goals_for_blue", "world_kpis", "int"),
    ("goals_for_red", "world_kpis", "int"),
    ("cluster_pct", "world_kpis", "float"),
    ("oob_pct", "world_kpis", "float"),
    ("goalie_idle_pct", "world_kpis", "float"),
    ("goalie_tactical_pct", "world_kpis", "float"),
    ("ball_possession_blue_pct", "world_kpis", "float"),
    ("tactical_score_avg", "world_kpis", "float"),
    ("shots_on_goal", "world_kpis", "int"),
    ("shots_on_target", "world_kpis", "int"),
    ("pass_completion_pct", "world_kpis", "float"),
    ("restart_recovery_time_s", "world_kpis", "float"),
    ("latency_p50", "llm_kpis", "int"),
    ("parse_error_rate", "llm_kpis", "float"),
]


def _mann_whitney_u(x, y):
    """Mann-Whitney U test (two-sided). Returns (U, p_value). No scipy needed."""
    nx, ny = len(x), len(y)
    if nx < 2 or ny < 2:
        return None, None
    combined = sorted([(v, i) for i, v in enumerate(x + y)])
    ranks = [0.0] * (nx + ny)
    i = 0
    while i < len(combined):
        j = i
        while j < len(combined) and combined[j][0] == combined[i][0]:
            j += 1
        avg_rank = (i + j + 1) / 2.0
        for k in range(i, j):
            ranks[combined[k][1]] = avg_rank
        i = j
    R_x = sum(ranks[:nx])
    U_x = R_x - nx * (nx + 1) / 2.0
    U_y = nx * ny - U_x
    U = min(U_x, U_y)
    # Normal approximation (valid for nx, ny >= ~8)
    mu = nx * ny / 2.0
    sigma = math.sqrt(nx * ny * (nx + ny + 1) / 12.0)
    if sigma == 0:
        return U, None
    z = (U - mu) / sigma
    # Two-sided p from standard normal
    p = 2.0 * (1.0 - 0.5 * (1.0 + math.erf(abs(z) / math.sqrt(2.0))))
    return U, p


def _load_kpi_group(pattern):
    """Load all KPI JSON files matching a glob pattern."""
    files = sorted(glob.glob(pattern))
    if not files:
        return {}, []
    values = {}
    for f in files:
        with open(f) as fh:
            data = json.load(fh)
        for kpi_name, section, _ in STAT_KPIS:
            val = data.get(section, {}).get(kpi_name, None)
            if val is not None:
                values.setdefault(kpi_name, []).append(float(val))
    return values, files


def stats_comparison(args):
    """Compare two groups of KPI JSONs: mean, std, 95% CI, Mann-Whitney U."""
    group_a_vals, group_a_files = _load_kpi_group(args.stats_a)
    group_b_vals, group_b_files = _load_kpi_group(args.stats_b)

    if not group_a_files:
        print(f"ERROR: No KPI files found for --stats-a pattern: {args.stats_a}", file=sys.stderr)
        sys.exit(1)
    if not group_b_files:
        print(f"ERROR: No KPI files found for --stats-b pattern: {args.stats_b}", file=sys.stderr)
        sys.exit(1)

    print("\n" + "=" * 80)
    print("STATISTICAL COMPARISON")
    print("=" * 80)
    print(f"Group A: {len(group_a_files)} runs  (pattern: {args.stats_a})")
    print(f"Group B: {len(group_b_files)} runs  (pattern: {args.stats_b})")
    print("=" * 80)
    print(f"{'KPI':<25s} {'A mean±std':>18s} {'B mean±std':>18s} {'Δ':>8s} {'p (M-W U)':>10s} {'sig':>5s}")
    print("-" * 80)

    for kpi_name, section, _ in STAT_KPIS:
        a = group_a_vals.get(kpi_name, [])
        b = group_b_vals.get(kpi_name, [])
        if not a or not b:
            print(f"{kpi_name:<25s} {'(no data)':>18s} {'(no data)':>18s}")
            continue
        a_mean = statistics.mean(a)
        b_mean = statistics.mean(b)
        a_std = statistics.stdev(a) if len(a) > 1 else 0.0
        b_std = statistics.stdev(b) if len(b) > 1 else 0.0
        delta = b_mean - a_mean
        # 95% CI (t-distribution approximated by z=1.96 for n>=10, z=2.45 for n=5)
        z = 1.96 if min(len(a), len(b)) >= 10 else 2.776  # t(4)=2.776
        a_ci = z * a_std / math.sqrt(len(a)) if a_std > 0 else 0.0
        b_ci = z * b_std / math.sqrt(len(b)) if b_std > 0 else 0.0
        U, p = _mann_whitney_u(a, b)
        sig = ""
        if p is not None:
            if p < 0.01:
                sig = "**"
            elif p < 0.05:
                sig = "*"
        p_str = f"{p:.4f}" if p is not None else "n/a"
        print(f"{kpi_name:<25s} {a_mean:>8.2f}±{a_std:<5.2f} {b_mean:>8.2f}±{b_std:<5.2f} "
              f"{delta:>+8.2f} {p_str:>10s} {sig:>5s}")

    print("-" * 80)
    print("sig: ** = p<0.01, * = p<0.05. Mann-Whitney U (two-sided, normal approx).")
    print(f"CI: 95% (z={'1.96' if min(len(group_a_files), len(group_b_files)) >= 10 else '2.776'})")
    print("=" * 80)


if __name__ == "__main__":
    main()