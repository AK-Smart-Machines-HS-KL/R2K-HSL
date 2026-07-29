#!/usr/bin/env python3
"""Replay Trace — post-match annotation review with LLM decision + game impact.

Loads annotations + llm_trace + world_trace for a given run, then for each
annotation shows: the LLM decision before it, the game state at that moment,
and the ball trajectory / events in the 5 seconds after it.

Usage:
  python3 tools/replay_trace.py --run-id <R2K_RUN_ID>
  python3 tools/replay_trace.py --run-id <R2K_RUN_ID> --all  # dump to markdown
  python3 tools/replay_trace.py --run-id <R2K_RUN_ID> --forward 10  # 10s forward scan
"""

import json
import os
import sys
import bisect
import math
from pathlib import Path
from collections import Counter

BASE_DIR = Path(__file__).parent.parent
LOG_DIR = BASE_DIR / "logs"
FORWARD_SECS_DEFAULT = 5.0
FORWARD_INTERVAL = 0.5  # print ball position every 0.5s in the forward scan


def load_jsonl(path):
    if not path.exists():
        return []
    records = []
    with open(path) as f:
        for line in f:
            try:
                records.append(json.loads(line))
            except Exception:
                pass
    return records


def find_run_id():
    """Default to the last game: newest world_trace_* file (annotations not required)."""
    files = sorted(
        [f for f in os.listdir(str(LOG_DIR)) if f.startswith("world_trace_")],
        key=lambda f: os.path.getmtime(str(LOG_DIR / f)),
        reverse=True,
    )
    if not files:
        return None
    return files[0].replace("world_trace_", "").replace(".jsonl", "")


def binary_search_le(times, target):
    """Find the largest index i where times[i] <= target."""
    idx = bisect.bisect_right(times, target) - 1
    return idx if idx >= 0 else -1


def binary_search_ge(times, target):
    """Find the smallest index i where times[i] >= target."""
    idx = bisect.bisect_left(times, target)
    return idx if idx < len(times) else -1


def closest_bot_to_ball(entities):
    ball = entities.get("soccer_ball", {})
    bx, by = ball.get("x", 0), ball.get("y", 0)
    closest = None
    min_dist = float("inf")
    for name, pos in entities.items():
        if "ball" in name:
            continue
        d = math.hypot(pos.get("x", 0) - bx, pos.get("y", 0) - by)
        if d < min_dist:
            min_dist = d
            closest = name
    return closest, min_dist


def format_positions(entities, indent=4):
    lines = []
    for name in sorted(entities.keys()):
        pos = entities[name]
        if isinstance(pos, dict):
            lines.append(f"{' ' * indent}{name}: ({pos.get('x', 0):.1f}, {pos.get('y', 0):.1f})")
    return "\n".join(lines)


def show_annotation(annot, llm_recs, world_recs, world_times, llm_times, forward_secs, t_norm):
    """Show one annotation with LLM decision, game state, and forward ball trajectory.
    t_norm: annotation timestamp normalized to seconds-from-match-start (t_wall - t0).
    """
    idx = annot["annotation_index"]
    comment = annot.get("comment", "(no comment)")
    score = annot.get("score", {})
    status = annot.get("status", "?")

    print(f"\n{'=' * 70}")
    print(f"=== Annotation {idx + 1} — t={t_norm:.1f}s ===")
    print(f"{'=' * 70}")
    print(f'Comment: "{comment}"')
    print()

    # --- LLM decision before annotation ---
    llm_idx = binary_search_le(llm_times, t_norm) if llm_times else -1
    if llm_idx >= 0 and llm_idx < len(llm_recs):
        rec = llm_recs[llm_idx]
        llm_t = llm_times[llm_idx]
        delta = t_norm - llm_t if t_norm >= llm_t else 0
        raw = rec.get("raw_response", "").strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        start = raw.find("{")
        end = raw.rfind("}")
        assignments = {}
        analysis = ""
        oracle = ""
        if start >= 0 and end >= 0:
            try:
                data = json.loads(raw[start:end + 1])
                assignments = data.get("assignments", {})
                analysis = data.get("analysis", "")
                oracle = data.get("oracle", "")
            except Exception:
                pass

        print(f"  LLM decision at t={llm_t:.1f}s ({delta:.1f}s before annotation):")
        if analysis:
            print(f"    [STRATEGY] {analysis}")
        if oracle:
            print(f"    [ORACLE]   {oracle}")
        for bot, action in assignments.items():
            print(f"    {bot}: {json.dumps(action)}")
        print(f"    Latency: {rec.get('latency_ms', '?')}ms | "
              f"Explain: {rec.get('explain', '?')} | "
              f"Parse: {rec.get('parse_code', '?')}")
    else:
        print("  LLM decision: (none found before this annotation)")
    print()

    # --- Game state at annotation ---
    print(f"  Game state at t={t_norm:.1f}s:")
    print(f"    Score: Blue {score.get('blue', 0)} : {score.get('red', 0)} Red | Status: {status}")
    snapshot = annot.get("snapshot", {})
    print(format_positions(snapshot))
    print()

    # --- Forward scan: ball trajectory + events ---
    print(f"  Ball trajectory after annotation ({forward_secs:.0f}s forward):")
    w_idx = binary_search_ge(world_times, t_norm)
    if w_idx < 0:
        print("    (no world_trace data after this point)")
    else:
        prev_score = score.copy()
        prev_status = status
        scan_end = t_norm + forward_secs
        last_printed_t = t_norm
        ball_moved = False

        while w_idx < len(world_recs) and world_times[w_idx] <= scan_end:
            w = world_recs[w_idx]
            wt = world_times[w_idx]
            ents = w.get("entities", {})
            mstate = w.get("match_state", {})
            ball = ents.get("soccer_ball", {})

            # Print at intervals or on events
            if wt - last_printed_t >= FORWARD_INTERVAL or wt == t_norm:
                closest, dist = closest_bot_to_ball(ents)
                print(f"    t={wt:.1f}s: ball at ({ball.get('x', 0):.1f}, {ball.get('y', 0):.1f}) "
                      f"→ {closest} closest ({dist:.1f}m)")
                last_printed_t = wt
                if ball.get("x", 0) != 0 or ball.get("y", 0) != 0:
                    ball_moved = True

            # Detect score change
            cur_score = {"blue": mstate.get("blue", 0), "red": mstate.get("red", 0)}
            if cur_score != prev_score:
                who = "Blue" if cur_score["blue"] > prev_score["blue"] else "Red"
                print(f"    ⚽ t={wt:.1f}s: GOAL! {who} scores "
                      f"(Blue {cur_score['blue']} : {cur_score['red']} Red)")
                prev_score = cur_score

            # Detect status change
            cur_status = mstate.get("status", "playing")
            if cur_status != prev_status:
                print(f"    🔄 t={wt:.1f}s: Status changed {prev_status} → {cur_status}")
                prev_status = cur_status

            w_idx += 1

        if not ball_moved:
            print("    (ball did not move — game may have been paused)")

    print()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Replay Trace — post-match annotation review")
    parser.add_argument("--run-id", default=None, help="R2K_RUN_ID (auto-detected if omitted)")
    parser.add_argument("--forward", type=float, default=FORWARD_SECS_DEFAULT,
                        help=f"Seconds to scan forward after each annotation (default: {FORWARD_SECS_DEFAULT})")
    parser.add_argument("--all", action="store_true",
                        help="Dump all annotations to markdown instead of interactive mode")
    args = parser.parse_args()

    run_id = args.run_id or find_run_id()
    if not run_id:
        print("❌ Could not determine R2K_RUN_ID. Use --run-id or run from a directory with annotations.")
        sys.exit(1)

    annot_path = LOG_DIR / f"annotations_{run_id}.jsonl"
    llm_path = LOG_DIR / f"llm_trace_{run_id}.jsonl"
    world_path = LOG_DIR / f"world_trace_{run_id}.jsonl"

    annotations = load_jsonl(annot_path)
    llm_recs = load_jsonl(llm_path)
    world_recs = load_jsonl(world_path)

    print(f"Run ID: {run_id}")
    print(f"Annotations: {len(annotations)} ({annot_path})")
    print(f"LLM trace:   {len(llm_recs)} records ({llm_path})")
    print(f"World trace: {len(world_recs)} records ({world_path})")

    if not annotations:
        print("\n❌ No annotations found for this run.")
        sys.exit(1)

    if not world_recs:
        print("\n❌ No world_trace found — cannot compute timeline.")
        sys.exit(1)

    # Normalize all timestamps to "seconds from first world_trace record".
    # Use t_wall (wall-clock) as the common timeline — sim-time (t) is 0.0
    # in all existing traces (libgazebo_ros_init.so not yet rebuilt into
    # the Docker container, so /clock never published).
    t0 = world_recs[0].get("t_wall", world_recs[0].get("t", 0))
    world_times = [r.get("t_wall", r.get("t", 0)) - t0 for r in world_recs]
    llm_times = [r.get("t", 0) - t0 for r in llm_recs]  # llm_trace "t" is wall-clock
    annot_times = [a.get("t_wall", 0) - t0 for a in annotations]

    if args.all:
        # Dump all to stdout (can be piped to markdown)
        for i, annot in enumerate(annotations):
            show_annotation(annot, llm_recs, world_recs, world_times, llm_times,
                            args.forward, annot_times[i])
    else:
        # Interactive mode
        for i, annot in enumerate(annotations):
            show_annotation(annot, llm_recs, world_recs, world_times, llm_times,
                            args.forward, annot_times[i])
            if i < len(annotations) - 1:
                try:
                    resp = input("[ENTER for next annotation, q to quit] ")
                    if resp.strip().lower() == "q":
                        break
                except (KeyboardInterrupt, EOFError):
                    break
        print(f"\n✅ Reviewed {i + 1}/{len(annotations)} annotations.")


if __name__ == "__main__":
    main()