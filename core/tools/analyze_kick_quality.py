#!/usr/bin/env python3
"""Analyze LLM trace logs for JSON-mode kick quality.

Reads llm_trace_*.jsonl files, checks each Kick assignment:
1. Wrong-kicker rate: kicker == geometrically closest blue bot?
2. Goalie over-kick: goalie assigned Kick while >2m from ball?
3. Degenerate targets: kick target ≈ ball position?
4. Goalie abandonment: goalie Move target off goal line?

Outputs per-match and aggregate metrics as JSON.
"""

import json
import glob
import sys
import os
import math
import subprocess


def bot_distance(b1, b2):
    return math.sqrt((b1['x'] - b2['x']) ** 2 + (b1['y'] - b2['y']) ** 2)


def closest_blue_to_ball(snapshot):
    ball = snapshot['soccer_ball']
    blues = [k for k in snapshot if k.startswith('blue_')]
    best_label, best_dist = None, float('inf')
    for label in blues:
        d = bot_distance(snapshot[label], ball)
        if d < best_dist:
            best_dist = d
            best_label = label
    return best_label, best_dist


def analyze_trace(path, tag):
    records = []
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    results = {
        'tag': tag,
        'run_id': os.path.basename(path).replace('llm_trace_', '').replace('.jsonl', ''),
        'path': os.path.basename(path),
        'total_llm_calls': len(records),
        'total_kicks': 0,
        'kicker_is_closest_strict': 0,
        'kicker_is_closest_field': 0,
        'goalie_overkick': 0,
        'goalie_kick_total': 0,
        'degenerate_targets': 0,
        'goalie_abandoned_goal': 0,
        'goalie_move_total': 0,
        'no_kicker_match': 0,
        'kicker_distances': [],
    }

    for rec in records:
        try:
            response = json.loads(rec.get('raw_response', '{}'))
        except (json.JSONDecodeError, KeyError):
            continue
        snapshot = rec.get('world_snapshot', {})
        if not snapshot or 'soccer_ball' not in snapshot:
            continue

        assignments = response.get('assignments', {})
        if not assignments:
            continue

        ball = snapshot['soccer_ball']

        closest_strict, closest_dist = closest_blue_to_ball(snapshot)
        blues_list = [k for k in snapshot if k.startswith('blue_')]

        # Field variant: exclude goalie if >3m from ball, take next closest
        if closest_strict == 'blue_1' and closest_dist > 3.0:
            candidates = [(k, bot_distance(snapshot[k], ball)) for k in blues_list if k != 'blue_1']
            closest_field = min(candidates, key=lambda x: x[1])[0] if candidates else closest_strict
        else:
            closest_field = closest_strict

        for label, task in assignments.items():
            if not label.startswith('blue_'):
                continue
            action = task.get('action', '')
            if action == 'Kick':
                results['total_kicks'] += 1
                kicker_pos = snapshot.get(label, {})
                kicker_ball_dist = bot_distance(kicker_pos, ball)

                if label == closest_strict:
                    results['kicker_is_closest_strict'] += 1
                else:
                    results['no_kicker_match'] += 1

                if label == closest_field:
                    results['kicker_is_closest_field'] += 1

                if label == 'blue_1':
                    results['goalie_kick_total'] += 1
                    if kicker_ball_dist > 2.0:
                        results['goalie_overkick'] += 1

                target_x = task.get('target_x')
                target_y = task.get('target_y')
                if target_x is not None and target_y is not None:
                    ball_target_dist = math.sqrt(
                        (target_x - ball['x']) ** 2 +
                        (target_y - ball['y']) ** 2
                    )
                    if ball_target_dist < 0.3:
                        results['degenerate_targets'] += 1

            elif action == 'Move':
                if label == 'blue_1':
                    results['goalie_move_total'] += 1
                    tx = task.get('x', 0)
                    goal_line_dist = abs(tx - (-4.5))
                    if goal_line_dist > 2.0:
                        results['goalie_abandoned_goal'] += 1

    # Derived
    n = results['total_kicks']
    results['kicker_is_closest_strict_pct'] = round(
        results['kicker_is_closest_strict'] / n * 100, 1) if n else 0.0
    results['kicker_is_closest_field_pct'] = round(
        results['kicker_is_closest_field'] / n * 100, 1) if n else 0.0
    results['goalie_overkick_pct'] = round(
        results['goalie_overkick'] / results['goalie_kick_total'] * 100, 1
    ) if results['goalie_kick_total'] else 0.0
    results['degenerate_target_pct'] = round(
        results['degenerate_targets'] / n * 100, 1) if n else 0.0
    results['goalie_abandoned_goal_pct'] = round(
        results['goalie_abandoned_goal'] / results['goalie_move_total'] * 100, 1
    ) if results['goalie_move_total'] else 0.0

    return results


def main():
    log_dir = os.path.join(
        os.path.dirname(__file__) or '.',
        '..', 'src', 'logs'
    )
    results_dir = os.path.join(
        os.path.dirname(__file__) or '.',
        '..', 'src', 'results'
    )
    os.makedirs(results_dir, exist_ok=True)
    all_results = {}

    arms = []

    # Arm A: specific run IDs from file
    arm_a_ids_file = '/tmp/arm_a_run_ids.txt'
    if os.path.exists(arm_a_ids_file):
        with open(arm_a_ids_file) as f:
            arm_a_ids = [line.strip() for line in f if line.strip()]
        arm_a_paths = []
        for rid in arm_a_ids:
            p = os.path.join(log_dir, f'llm_trace_{rid}.jsonl')
            if os.path.exists(p):
                arm_a_paths.append(p)
            else:
                print(f'WARN: Arm A trace not found: {p}')
        arms.append(('Arm A (random draw)', 'arm_a', arm_a_paths))
    else:
        print(f'WARN: No Arm A run IDs file at {arm_a_ids_file}')

    # Arm B: jit scenario traces (glob by timestamp)
    arm_b_paths = sorted(glob.glob(os.path.join(log_dir, 'llm_trace_jit_*.jsonl')))
    if arm_b_paths:
        arms.append(('Arm B (jittered)', 'arm_b', arm_b_paths))
    else:
        print('No Arm B (jit) traces found')

    for arm_label, arm_tag, paths in arms:
        print(f'\n=== {arm_label}: {len(paths)} traces ===')
        arm_results = []
        for path in paths:
            r = analyze_trace(path, arm_tag)
            arm_results.append(r)
            print(f'  {r["run_id"]}: {r["total_kicks"]} kicks, '
                  f'strict={r["kicker_is_closest_strict_pct"]}%, '
                  f'field={r["kicker_is_closest_field_pct"]}%, '
                  f'goalie_overkick={r["goalie_overkick_pct"]}%, '
                  f'degenerate={r["degenerate_target_pct"]}%')

        n_kicks = sum(r['total_kicks'] for r in arm_results)
        n_calls = sum(r['total_llm_calls'] for r in arm_results)
        n_goalie_kicks = sum(r['goalie_kick_total'] for r in arm_results)
        n_goalie_moves = sum(r['goalie_move_total'] for r in arm_results)

        # Pooled weighted averages
        strict_pct = round(sum(r['kicker_is_closest_strict'] for r in arm_results) / n_kicks * 100, 1) if n_kicks else 0.0
        field_pct = round(sum(r['kicker_is_closest_field'] for r in arm_results) / n_kicks * 100, 1) if n_kicks else 0.0
        goalie_overkick_pct = round(sum(r['goalie_overkick'] for r in arm_results) / n_goalie_kicks * 100, 1) if n_goalie_kicks else 0.0
        degenerate_pct = round(sum(r['degenerate_targets'] for r in arm_results) / n_kicks * 100, 1) if n_kicks else 0.0
        abandon_pct = round(sum(r['goalie_abandoned_goal'] for r in arm_results) / n_goalie_moves * 100, 1) if n_goalie_moves else 0.0

        all_results[arm_tag] = {
            'label': arm_label,
            'matches': len(arm_results),
            'total_llm_calls': n_calls,
            'total_kicks': n_kicks,
            'kicker_is_closest_strict_pct': strict_pct,
            'kicker_is_closest_field_pct': field_pct,
            'goalie_overkick_pct': goalie_overkick_pct,
            'degenerate_target_pct': degenerate_pct,
            'goalie_abandoned_goal_pct': abandon_pct,
            'per_match': arm_results,
        }

        # Goals and possession from analyze_trace.py
        goals_b, goals_r, poss, lat = 0, 0, 0.0, 0
        for r in arm_results:
            rid = r['run_id']
            try:
                kpi_raw = subprocess.check_output(
                    [sys.executable, os.path.join(results_dir, '..', 'tools', 'analyze_trace.py'),
                     '--run-id', rid],
                    timeout=10, stderr=subprocess.DEVNULL
                ).decode()
                decoder = json.JSONDecoder()
                obj, _ = decoder.raw_decode(kpi_raw)
                wk = obj.get('world_kpis', {})
                goals_b += wk.get('goals_for_blue', 0)
                goals_r += wk.get('goals_for_red', 0)
                poss += wk.get('ball_possession_blue_pct', 0)
            except Exception:
                pass
        all_results[arm_tag]['goals_blue'] = goals_b
        all_results[arm_tag]['goals_red'] = goals_r
        all_results[arm_tag]['possession_avg'] = round(poss / len(arm_results), 1) if arm_results else 0.0

        print(f'\n  **[Aggregate]** {n_kicks} kicks across {len(arm_results)} matches')
        print(f'  Strict match:  {strict_pct}%')
        print(f'  Field match:   {field_pct}%')
        print(f'  Goalie over-kick: {goalie_overkick_pct}% (of {n_goalie_kicks} goalie kicks)')
        print(f'  Degenerate targets: {degenerate_pct}%')
        print(f'  Goalie abandoned goal: {abandon_pct}% (of {n_goalie_moves} goalie moves)')
        print(f'  Score: {goals_b}B {goals_r}R  Poss: {poss / len(arm_results):.1f}%')

    # Save report
    for arm_tag, data in all_results.items():
        report_path = os.path.join(results_dir, f'jsonq_analysis_{arm_tag}.json')
        serializable = {k: v for k, v in data.items() if k != 'per_match'}
        serializable['per_match'] = [
            {k: v for k, v in m.items() if k != 'kicker_distances'}
            for m in data.get('per_match', [])
        ]
        with open(report_path, 'w') as f:
            json.dump(serializable, f, indent=2)
        print(f'\nReport saved: {report_path}')


if __name__ == '__main__':
    main()