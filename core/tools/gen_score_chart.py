#!/usr/bin/env python3
"""Generate score delta bar charts for scenario analysis.md files.

For each scenario, probes the LLM (or uses cached output) and computes the
tactical_score trajectory for 2-3 LLM latency periods after the decision.
Produces a horizontal bar chart: red (negative) to blue (positive).

Usage:
    python3 tools/gen_score_chart.py --scenario 3vs3_attack_center
    python3 tools/gen_score_chart.py --all
"""
import argparse
import json
import os
import sys
import math
import re
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

BASE_DIR = Path(__file__).parent.parent
SRC_DIR = BASE_DIR / "src"
SCENARIO_DIR = SRC_DIR / "scenario"
LOG_DIR = SRC_DIR / "logs"

sys.path.insert(0, str(SRC_DIR))
sys.path.insert(0, str(SRC_DIR / "ai_tactics"))
os.environ["R2K_TEXT_MODE"] = "1"


def load_world_traces_for_scenario(scenario_name):
    """Find world_trace files matching the scenario and extract score trajectories."""
    traces = sorted(LOG_DIR.glob(f"world_trace_{scenario_name}_*.jsonl"),
                    key=lambda p: p.stat().st_mtime, reverse=True)
    
    if not traces:
        return None
    
    # Use the most recent trace
    scores = []
    with open(traces[0]) as f:
        for line in f:
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except:
                continue
            ts = r.get("tactical_score", {})
            cs = ts.get("current_numerical_score", 0) if isinstance(ts, dict) else 0
            mom = ts.get("momentum_30s", 0) if isinstance(ts, dict) else 0
            ms = r.get("match_state", {})
            scores.append({
                "score": cs,
                "momentum": mom,
                "blue": ms.get("blue", 0),
                "red": ms.get("red", 0),
                "status": ms.get("status", "playing"),
            })
    
    return scores


def compute_score_deltas(scores, n_periods=16, latency_s=0.5):
    """Compute score deltas over n_periods of latency (each ~0.5s).
    
    Pattern: score(t) -> score(t+0.5s) -> score(t+1.0s) -> ... -> score(t+8.0s)
    Each delta = score at end of period minus score at start of period.
    16 periods × 0.5s = 8s (covers full 8s match).
    
    Cuts off at the first goal event (status == "goal") — data after the
    goal freeze is meaningless for regression testing. If no goal occurs
    in 8s, all 16 bars are shown with a "NO GOAL" marker.
    
    The latency_s is the LLM decision cycle (~500ms measured).
    The world_trace is at 10Hz (0.1s per frame).
    """
    if not scores:
        return [], None
    
    frames_per_period = int(latency_s * 10)  # 5 frames per period
    
    # Find the first goal event frame (only within first 80 frames = 8s)
    goal_frame = None
    goal_team = None
    max_frames = n_periods * frames_per_period  # 80 frames = 8s
    for i, s in enumerate(scores[:max_frames]):
        if s.get("status") == "goal":
            goal_frame = i
            # Determine which team scored (compare to previous frame)
            if i > 0:
                prev_blue = scores[i - 1].get("blue", 0)
                prev_red = scores[i - 1].get("red", 0)
                curr_blue = s.get("blue", 0)
                curr_red = s.get("red", 0)
                if curr_blue > prev_blue:
                    goal_team = "blue"
                elif curr_red > prev_red:
                    goal_team = "red"
            break
    
    deltas = []
    for i in range(n_periods):
        start_idx = i * frames_per_period
        end_idx = start_idx + frames_per_period
        if end_idx >= len(scores):
            end_idx = len(scores) - 1
        if start_idx >= len(scores):
            break
        # Cut off at goal event — don't show bars that include the goal frame
        if goal_frame is not None and end_idx >= goal_frame:
            break
        score_before = scores[start_idx]["score"]
        score_after = scores[end_idx]["score"]
        delta = score_after - score_before
        deltas.append({
            "period": i + 1,
            "time_s": (i + 1) * latency_s,
            "score_before": score_before,
            "score_after": score_after,
            "delta": delta,
        })
    
    goal_info = None
    if goal_frame is not None:
        goal_info = {
            "frame": goal_frame,
            "time_s": goal_frame / 10.0,
            "team": goal_team or "unknown",
        }
    
    return deltas, goal_info


def generate_bar_chart(deltas, output_path, scenario_name, latency_s=0.5,
                         goal_info=None, umschalt_desc=None):
    """Generate a horizontal bar chart showing score deltas.
    
    goal_info: dict with time_s and team, or None. If set, marks the goal
    event at the actual y-position (time after umschalt). If None and
    deltas has 16 bars (full 8s), shows "NO GOAL" with umschalt description.
    
    Y-axis is always full 0-8s range (17 labels: t=0, 0.5s, ..., 8.0s)
    so all charts have the same scale.
    """
    if not deltas:
        fig, ax = plt.subplots(1, 1, figsize=(6, 2))
        fig.patch.set_facecolor('#1a1a1a')
        ax.set_facecolor('#1a1a1a')
        ax.text(0.5, 0.5, "No score data available", ha='center', va='center',
                color='white', fontsize=10, transform=ax.transAxes)
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_color('#555555')
        plt.tight_layout()
        fig.savefig(str(output_path), dpi=150, bbox_inches='tight',
                    facecolor=fig.get_facecolor())
        plt.close(fig)
        return

    fig, ax = plt.subplots(1, 1, figsize=(6, 4.5))
    fig.patch.set_facecolor('#1a1a1a')
    ax.set_facecolor('#1a1a1a')

    # Build full y-axis: t=0 + 16 time points (0.5s to 8.0s), always 17 labels
    full_labels = ["t=0 (Umschalt)"]
    full_values = [0]
    full_colors = ['#555555']

    # Map deltas to their y-position (index 1-16)
    delta_by_period = {d['period']: d for d in deltas}

    for period in range(1, 17):
        time_s = period * latency_s
        full_labels.append(f"{time_s:.1f}s")
        if period in delta_by_period:
            d = delta_by_period[period]
            full_values.append(d["delta"])
            full_colors.append('#3498db' if d["delta"] >= 0 else '#e74c3c')
        else:
            # No data (after goal cutoff) — empty bar at 0
            full_values.append(0)
            full_colors.append('#333333')

    bars = ax.barh(full_labels, full_values, color=full_colors, height=0.6)

    # Label deltas (skip t=0 marker and empty bars)
    for i, (bar, val) in enumerate(zip(bars, full_values)):
        if i == 0 or val == 0:
            continue
        x_pos = bar.get_width()
        label_x = x_pos + (0.15 if x_pos >= 0 else -0.15)
        ax.text(label_x, bar.get_y() + bar.get_height() / 2,
                f"{val:+.2f}", va='center', ha='left' if x_pos >= 0 else 'right',
                color='white', fontsize=8, fontweight='bold')

    ax.axvline(x=0, color='white', linewidth=0.5, alpha=0.5)

    ax.set_xlabel("Score delta (red = negative, blue = positive)", color='white', fontsize=8)
    ax.set_ylabel("Time after umschalt", color='white', fontsize=8)
    ax.set_title(f"{scenario_name} — tactical score delta",
                 color='white', fontsize=10, pad=8)

    ax.tick_params(colors='white', labelsize=8)
    for spine in ax.spines.values():
        spine.set_color('#555555')

    ax.set_xlim(-10.0, 10.0)

    # Mark goal event at actual y-position, or NO GOAL with umschalt description
    if goal_info:
        goal_time = goal_info['time_s']
        goal_team = goal_info['team']
        goal_label = f"GOAL: {goal_team} at t={goal_time:.1f}s"
        goal_color = '#3498db' if goal_team == 'blue' else '#e74c3c'
        # Convert goal time to y-position (same as bar index: time_s/latency_s + 1)
        goal_y = goal_time / latency_s + 1
        ax.axhline(y=goal_y, color=goal_color, linewidth=2, linestyle='--', alpha=0.7)
        ax.text(9.5, goal_y, goal_label, color=goal_color, fontsize=8,
                fontweight='bold', va='center', ha='right',
                bbox=dict(boxstyle='round,pad=0.2', fc='black', ec=goal_color, alpha=0.8))
    elif len(deltas) == 16:
        desc_str = f" — {umschalt_desc}" if umschalt_desc else ""
        no_goal_label = f"NO GOAL in 8s{desc_str}"
        ax.text(9.5, 16.5, no_goal_label, color='#ffeb3b', fontsize=8,
                fontweight='bold', va='center', ha='right',
                bbox=dict(boxstyle='round,pad=0.2', fc='black', ec='#ffeb3b', alpha=0.8))
    
    plt.tight_layout()
    fig.savefig(str(output_path), dpi=150, bbox_inches='tight',
                facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  Generated: {output_path}")


def load_all_traces_for_scenario(scenario_name, max_duration_s=None):
    """Load ALL world_trace files for a scenario (newest first), return list of score lists.
    If max_duration_s is set, cap each run at that duration (in seconds from first frame)."""
    traces = sorted(LOG_DIR.glob(f"world_trace_{scenario_name}_*.jsonl"),
                    key=lambda p: p.stat().st_mtime, reverse=True)
    all_runs = []
    for trace_path in traces:
        scores = []
        t0 = None
        with open(trace_path) as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    r = json.loads(line)
                except:
                    continue
                if t0 is None:
                    t0 = r.get("t_wall", 0)
                elapsed = r.get("t_wall", 0) - t0
                if max_duration_s is not None and elapsed > max_duration_s:
                    break
                ts = r.get("tactical_score", {})
                cs = ts.get("current_numerical_score", 0) if isinstance(ts, dict) else 0
                ms = r.get("match_state", {})
                scores.append({
                    "score": cs,
                    "blue": ms.get("blue", 0),
                    "red": ms.get("red", 0),
                    "status": ms.get("status", "playing"),
                })
        if scores:
            all_runs.append(scores)
    return all_runs


def find_goal_time(scores):
    """Find the first goal event frame, return (frame_idx, team) or (None, None)."""
    for i, s in enumerate(scores):
        if s["status"] == "goal":
            team = None
            if i > 0:
                if s["blue"] > scores[i - 1]["blue"]:
                    team = "blue"
                elif s["red"] > scores[i - 1]["red"]:
                    team = "red"
            return i, team
    return None, None


def generate_ensemble_chart(runs, output_path, scenario_name, n_runs=5,
                             duration_s=4.0, interval_s=1.0):
    """Generate ensemble forecast chart: shaded band (min-max) + mean dotted line.
    
    X-axis = time (0 to duration_s), Y-axis = tactical score [-10, +10].
    At each interval_s time point, plot the score from each run, shade the
    min-max range, and draw the mean as a dotted line.
    
    No individual run labels — just the mean line and shaded band.
    The scoring formula is displayed at the bottom of the chart.
    
    If a goal is scored in a run, that run is cut off at the goal frame.
    If no runs have data, show placeholder.
    """
    if not runs:
        fig, ax = plt.subplots(1, 1, figsize=(6, 3))
        fig.patch.set_facecolor('#1a1a1a')
        ax.set_facecolor('#1a1a1a')
        ax.text(0.5, 0.5, "No trace data available", ha='center', va='center',
                color='white', fontsize=10, transform=ax.transAxes)
        ax.set_xticks([])
        ax.set_yticks([])
        plt.tight_layout()
        fig.savefig(str(output_path), dpi=150, bbox_inches='tight',
                    facecolor=fig.get_facecolor())
        plt.close(fig)
        return

    used_runs = runs[:n_runs]
    frames_per_interval = int(interval_s * 10)  # 10 frames per 1.0s
    n_intervals = int(duration_s / interval_s)  # 4 intervals for 4s
    time_points = [i * interval_s for i in range(n_intervals + 1)]  # 0, 1, 2, 3, 4

    # For each time point, collect scores from each run (cut off at goal)
    # Skip frame 0 (startup race condition) — use frame 1 as t=0
    run_data = []
    for run_scores in used_runs:
        goal_frame, goal_team = find_goal_time(run_scores)
        goal_time_s = goal_frame / 10.0 if goal_frame is not None else None
        run_data.append((run_scores, goal_time_s, goal_team))

    # At each time point, get score from each run (or None if past goal/trace end)
    # Use frame 1 as t=0 (skip frame 0 race condition)
    at_time = []
    for t_idx in range(n_intervals + 1):
        frame_idx = t_idx * frames_per_interval + 1  # +1 to skip frame 0
        point_scores = []
        for run_scores, goal_time_s, _ in run_data:
            # Clamp to last available frame so t=4s shows data
            clamped_idx = min(frame_idx, len(run_scores) - 1)
            if goal_time_s is not None and clamped_idx >= goal_time_s * 10:
                point_scores.append(None)
            else:
                point_scores.append(run_scores[clamped_idx]["score"])
        at_time.append(point_scores)

    # Compute min, max, mean at each time point (ignoring None)
    mins, maxs, means = [], [], []
    for point_scores in at_time:
        valid = [v for v in point_scores if v is not None]
        if valid:
            mins.append(min(valid))
            maxs.append(max(valid))
            means.append(sum(valid) / len(valid))
        else:
            mins.append(None)
            maxs.append(None)
            means.append(None)

    # Plot
    fig, ax = plt.subplots(1, 1, figsize=(7, 4.5))
    fig.patch.set_facecolor('#1a1a1a')
    ax.set_facecolor('#1a1a1a')

    # Shaded band (min-max)
    valid_times = [t for t, m in zip(time_points, mins) if m is not None]
    valid_mins = [m for m in mins if m is not None]
    valid_maxs = [m for m in maxs if m is not None]
    if valid_times:
        ax.fill_between(valid_times, valid_mins, valid_maxs,
                         color='#3498db', alpha=0.2)

    # Mean dotted line (labeled "mean")
    valid_means = [m for m in means if m is not None]
    if valid_times and valid_means:
        ax.plot(valid_times, valid_means, 'o--', color='#3498db',
                linewidth=1.5, markersize=6, label="mean")

    # Goal markers (vertical line for each run that scored)
    for run_idx, (run_scores, goal_time_s, goal_team) in enumerate(run_data):
        if goal_time_s is not None and goal_time_s <= duration_s:
            color = '#3498db' if goal_team == 'blue' else '#e74c3c'
            ax.axvline(x=goal_time_s, color=color, linewidth=1.5,
                       linestyle='--', alpha=0.5)
            ax.text(goal_time_s + 0.05, 9.0, f"GOAL {goal_team}",
                    color=color, fontsize=7, fontweight='bold', rotation=90,
                    va='top', ha='left')

    # If no goals in any run, mark NO GOAL
    any_goal = any(gt is not None and gt <= duration_s
                    for _, gt, _ in run_data)
    if not any_goal and len(used_runs) > 0:
        ax.text(duration_s - 0.1, -9.0, "NO GOAL in 4s", color='#ffeb3b',
                fontsize=8, fontweight='bold', va='bottom', ha='right',
                bbox=dict(boxstyle='round,pad=0.2', fc='black', ec='#ffeb3b', alpha=0.8))

    # Align t=0 with y-axis (no gap)
    ax.set_xlim(0, duration_s)
    ax.set_ylim(-10.5, 10.5)
    ax.set_xlabel("Time after LLM decision (s)", color='white', fontsize=9)
    ax.set_ylabel("Tactical score [-10, +10]", color='white', fontsize=9)
    ax.set_title(f"{scenario_name} — Score forecast (4sec, 5 runs)",
                 color='white', fontsize=10, pad=8)

    ax.set_xticks(time_points)
    ax.tick_params(colors='white', labelsize=8)
    ax.axhline(y=0, color='white', linewidth=0.3, alpha=0.3)
    for spine in ax.spines.values():
        spine.set_color('#555555')

    # Legend: only "mean"
    ax.legend(loc='upper right', fontsize=8, facecolor='#1a1a1a', edgecolor='#555555',
              labelcolor='white', framealpha=0.8)

    # Scoring formula at the bottom of the chart
    formula = ("score = ball_x × 1.5 + possession(±2.0) - cluster(< 0.5m: -2.0, < 1.0m: -1.0) "
               "- lane_open(-3.0) + blockers(≥2: +1.0), clamped [-10, +10]")
    fig.text(0.5, 0.01, formula, ha='center', va='bottom', color='#888888',
             fontsize=6, style='italic', wrap=True)

    plt.tight_layout(rect=[0, 0.06, 1, 1])
    fig.savefig(str(output_path), dpi=150, bbox_inches='tight',
                facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  Generated: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate score delta bar charts")
    parser.add_argument("--scenario", type=str, help="Scenario name")
    parser.add_argument("--all", action="store_true", help="Generate for all scenarios")
    parser.add_argument("--all-empirical", action="store_true", help="Generate for empirical scenarios only")
    parser.add_argument("--ensemble", action="store_true",
                        help="Ensemble forecast chart (hand-crafted: 3 runs, shaded band + mean)")
    args = parser.parse_args()
    
    if args.all:
        scenarios = sorted([d.name for d in SCENARIO_DIR.iterdir()
                           if d.is_dir() and (d / "scenario.json").exists()])
    elif args.all_empirical:
        scenarios = sorted([d.name for d in SCENARIO_DIR.iterdir()
                           if d.is_dir() and (d / "scenario.json").exists()
                           and d.name.startswith("emp_")])
    else:
        scenarios = [args.scenario]
    
    for scen in scenarios:
        if args.ensemble:
            all_runs = load_all_traces_for_scenario(scen, max_duration_s=4.0)
            output_path = SCENARIO_DIR / scen / "score_chart.png"
            generate_ensemble_chart(all_runs, output_path, scen, duration_s=4.0)
        else:
            scores = load_world_traces_for_scenario(scen)
            deltas, goal_info = compute_score_deltas(scores, n_periods=16, latency_s=0.5)
            # Read umschalt description from analysis.md for NO GOAL label
            umschalt_desc = None
            am_path = SCENARIO_DIR / scen / "analysis.md"
            if am_path.exists():
                am_text = am_path.read_text(encoding="utf-8")
                m = re.search(r"Umschalt type:\s*\S+\s*—\s*(.+)", am_text)
                if m:
                    umschalt_desc = m.group(1).strip()
            output_path = SCENARIO_DIR / scen / "score_chart.png"
            generate_bar_chart(deltas, output_path, scen, latency_s=0.5,
                               goal_info=goal_info, umschalt_desc=umschalt_desc)


if __name__ == "__main__":
    main()