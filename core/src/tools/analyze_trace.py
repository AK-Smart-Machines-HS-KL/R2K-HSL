#!/usr/bin/env python3
"""Measurement script — computes KPIs from LLM and world-state trace logs.

Reads:
  logs/llm_trace_<run_id>.jsonl   (one line per LLM call)
  logs/world_trace_<run_id>.jsonl  (one line per world-state write, ~10Hz)

Computes:
  goals_for_blue / goals_for_red   — score increments
  cluster_frames                    — frames where min pairwise blue-bot dist < 0.5m
  goalie_idle_frames                — frames where goalie moved < 0.05m
  oob_frames_blue                   — blue bot outside field bounds
  ball_possession_blue_pct          — % frames closest bot to ball is blue
  role_diversity                    — distinct role strings in LLM responses
  latency_p50/p95/max               — from latency_ms
  parse_error_rate                  — % calls with parse_code > 0
  avg_response_tokens               — len(raw_response)/4

Usage:
  python3 tools/analyze_trace.py --run-id test_001
  python3 tools/analyze_trace.py --run-id test_001 --output results/
  python3 tools/analyze_trace.py --run-id test_001 --plot
"""
import argparse
import json
import math
import os
import statistics
import sys
from collections import Counter

FIELD_X_MIN, FIELD_X_MAX = -4.5, 4.5
FIELD_Y_MIN, FIELD_Y_MAX = -3.0, 3.0
CLUSTER_THRESHOLD = 0.5
GOALIE_IDLE_THRESHOLD = 0.05
OOB_MARGIN = 0.1  # bots slightly outside count as OOB


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
    """Extract role strings from raw LLM response."""
    try:
        start = raw_response.find('{')
        end = raw_response.rfind('}')
        if start == -1 or end == -1:
            return {}
        json_str = raw_response[start:end + 1]
        json_str = __import__('re').sub(r',\s*\}', '}', json_str)
        json_str = __import__('re').sub(r',\s*\]', ']', json_str)
        data = json.loads(json_str)
        return data.get("assignments", data)
    except Exception:
        return {}


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
            "parse_error_rate": 0.0, "role_diversity": 0, "avg_response_tokens": 0,
            "roles": {},
        }

    latencies = [r.get("latency_ms", 0) for r in llm_records]
    parse_errors = sum(1 for r in llm_records if r.get("parse_code", 0) > 0)
    response_tokens = [len(r.get("raw_response", "")) / 4 for r in llm_records]

    # Role diversity
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
        "role_diversity": len(role_counter),
        "roles": dict(role_counter.most_common(20)),
        "avg_response_tokens": round(statistics.mean(response_tokens), 0) if response_tokens else 0,
        "explain_mode": llm_records[0].get("explain", None),
        "model": llm_records[0].get("model", "unknown"),
    }


def main():
    parser = argparse.ArgumentParser(description="Analyze LLM + world trace logs")
    parser.add_argument('--run-id', type=str, required=True,
                        help='Run ID (matches R2K_RUN_ID used during launch)')
    parser.add_argument('--log-dir', type=str, default=None,
                        help='Override log directory (default: ../logs relative to this script)')
    parser.add_argument('--output', type=str, default=None,
                        help='Output JSON file (default: print to stdout)')
    parser.add_argument('--plot', action='store_true',
                        help='Generate matplotlib plots (latency histogram, score timeline)')
    args = parser.parse_args()

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
    print(f"LLM calls:       {llm_kpis.get('llm_calls', 0)}")
    print(f"Latency p50:     {llm_kpis.get('latency_p50', 0)}ms")
    print(f"Latency p95:     {llm_kpis.get('latency_p95', 0)}ms")
    print(f"Latency max:     {llm_kpis.get('latency_max', 0)}ms")
    print(f"Parse errors:    {llm_kpis.get('parse_error_rate', 0)}%")
    print(f"Role diversity:  {llm_kpis.get('role_diversity', 0)} distinct roles")
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


if __name__ == "__main__":
    main()