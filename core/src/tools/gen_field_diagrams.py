#!/usr/bin/env python3
"""Generate field diagram PNGs for test scenario packages.

Reads scenario JSON, draws a 2D field with:
- Field boundary (9m × 6m)
- Goal areas (±3.5m X, ±1.0m Y)
- Goal posts (±0.9m Y at goal lines)
- Colorized bots (blue team = blue, red team = red)
- Ball position (white with black outline)
- Bot labels (blue_1, red_2, etc.)

Usage:
    python3 tools/gen_field_diagrams.py --scenario 3vs3_attack_center
    python3 tools/gen_field_diagrams.py --all
    python3 tools/gen_field_diagrams.py --all --output-dir scenario/
"""
import argparse
import json
import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.lines as mlines


FIELD_X_MIN, FIELD_X_MAX = -4.5, 4.5
FIELD_Y_MIN, FIELD_Y_MAX = -3.0, 3.0
GOAL_AREA_X = 3.5
GOAL_AREA_Y = 1.0
GOAL_Y_MIN, GOAL_Y_MAX = -0.9, 0.9
CORNER_X, CORNER_Y = 4.3, 2.8


def draw_field(ax):
    ax.set_xlim(FIELD_X_MIN - 1.0, FIELD_X_MAX + 1.0)
    ax.set_ylim(FIELD_Y_MIN - 1.0, FIELD_Y_MAX + 1.0)
    ax.set_aspect('equal')
    ax.set_facecolor('#2d5a1e')

    ax.plot([FIELD_X_MIN, FIELD_X_MAX, FIELD_X_MAX, FIELD_X_MIN, FIELD_X_MIN],
            [FIELD_Y_MIN, FIELD_Y_MIN, FIELD_Y_MAX, FIELD_Y_MAX, FIELD_Y_MIN],
            'w-', linewidth=2, zorder=1)

    ax.plot([0, 0], [FIELD_Y_MIN, FIELD_Y_MAX], 'w--', linewidth=1, alpha=0.6, zorder=1)
    ax.plot([FIELD_X_MIN, FIELD_X_MAX], [0, 0], 'w--', linewidth=1, alpha=0.6, zorder=1)

    circle = plt.Circle((0, 0), 0.8, fill=False, edgecolor='w', linewidth=1, alpha=0.6, zorder=1)
    ax.add_patch(circle)
    ax.plot(0, 0, 'wo', markersize=3, zorder=1)

    for goal_x, goal_color in [(FIELD_X_MAX, '#e74c3c'), (FIELD_X_MIN, '#3498db')]:
        ax.plot([goal_x, goal_x], [GOAL_Y_MIN, GOAL_Y_MAX],
                color=goal_color, linewidth=4, zorder=2)
        ax.plot(goal_x, GOAL_Y_MIN, 'o', color=goal_color, markersize=8, zorder=3)
        ax.plot(goal_x, GOAL_Y_MAX, 'o', color=goal_color, markersize=8, zorder=3)

    for ga_x in [GOAL_AREA_X, -GOAL_AREA_X]:
        ga_x_outer = ga_x + (0.3 if ga_x > 0 else -0.3)
        ax.plot([ga_x, ga_x], [-GOAL_AREA_Y, GOAL_AREA_Y],
                'w-', linewidth=1, alpha=0.5, zorder=1)
        ax.plot([ga_x, ga_x_outer], [GOAL_AREA_Y, GOAL_AREA_Y],
                'w-', linewidth=1, alpha=0.5, zorder=1)
        ax.plot([ga_x, ga_x_outer], [-GOAL_AREA_Y, -GOAL_AREA_Y],
                'w-', linewidth=1, alpha=0.5, zorder=1)

    ax.plot([FIELD_X_MIN, FIELD_X_MAX], [FIELD_Y_MIN, FIELD_Y_MIN],
            'w-', linewidth=2, zorder=1)
    ax.plot([FIELD_X_MIN, FIELD_X_MAX], [FIELD_Y_MAX, FIELD_Y_MAX],
            'w-', linewidth=2, zorder=1)

    for cx, cy in [(CORNER_X, CORNER_Y), (CORNER_X, -CORNER_Y),
                   (-CORNER_X, CORNER_Y), (-CORNER_X, -CORNER_Y)]:
        ax.plot(cx, cy, 'wx', markersize=6, zorder=2)


def draw_entities(ax, entities):
    for name, pos in entities.items():
        x, y = pos.get('x', 0), pos.get('y', 0)

        if 'ball' in name.lower():
            ax.plot(x, y, 'wo', markersize=10, zorder=5, markeredgecolor='k', markeredgewidth=1)
            ax.annotate('ball', (x, y), textcoords="offset points", xytext=(8, 8),
                        fontsize=7, color='white', zorder=6)
        elif 'blue' in name:
            ax.plot(x, y, 'o', color='#3498db', markersize=12, zorder=5,
                    markeredgecolor='white', markeredgewidth=1.5)
            ax.annotate(name, (x, y), textcoords="offset points", xytext=(0, -15),
                        fontsize=7, color='white', ha='center', zorder=6,
                        fontweight='bold')
        elif 'red' in name:
            ax.plot(x, y, 'o', color='#e74c3c', markersize=12, zorder=5,
                    markeredgecolor='white', markeredgewidth=1.5)
            ax.annotate(name, (x, y), textcoords="offset points", xytext=(0, -15),
                        fontsize=7, color='white', ha='center', zorder=6,
                        fontweight='bold')


def generate_diagram(scenario_json_path, output_path):
    with open(scenario_json_path) as f:
        data = json.load(f)

    scenario_name = data.get('scenario_name', data.get('label', 'unknown'))
    tactical = data.get('tactical_situation', data.get('tactical_situation', ''))
    entities = data.get('entities', {})

    fig, ax = plt.subplots(1, 1, figsize=(8, 6))
    fig.patch.set_facecolor('#1a1a1a')

    draw_field(ax)
    draw_entities(ax, entities)

    ax.set_title(f'{scenario_name}', color='white', fontsize=14, fontweight='bold', pad=10)
    if tactical:
        ax.text(0.5, -0.08, tactical, transform=ax.transAxes, ha='center',
                fontsize=8, color='#aaaaaa', style='italic')

    ax.tick_params(colors='white', labelsize=7)
    for spine in ax.spines.values():
        spine.set_color('#555555')

    ax.set_xlabel('X (m)', color='white', fontsize=8)
    ax.set_ylabel('Y (m)', color='white', fontsize=8)

    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches='tight',
                facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f'  Generated: {output_path}')


def find_scenario_json(scenario_name, scenario_dir):
    p = Path(scenario_dir)
    candidates = [
        p / scenario_name / 'scenario.json',
        p / f'{scenario_name}.json',
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def main():
    parser = argparse.ArgumentParser(description='Generate field diagram PNGs for scenarios')
    parser.add_argument('--scenario', type=str, help='Scenario name (e.g. 3vs3_attack_center)')
    parser.add_argument('--all', action='store_true', help='Generate for all scenarios')
    parser.add_argument('--output-dir', type=str, default='.', help='Output directory')
    parser.add_argument('--scenario-dir', type=str, default='scenario', help='Scenario directory')
    args = parser.parse_args()

    if not args.scenario and not args.all:
        parser.error('Specify --scenario <name> or --all')

    if args.all:
        sdir = Path(args.scenario_dir)
        scenarios = []
        for pkg in sorted(sdir.iterdir()):
            if pkg.is_dir() and (pkg / 'scenario.json').exists():
                scenarios.append(pkg.name)
        for f in sorted(sdir.glob('*.json')):
            if f.name != 'README.md' and not f.name.startswith('.'):
                scenarios.append(f.stem)
        scenarios = list(dict.fromkeys(scenarios))
    else:
        scenarios = [args.scenario]

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for sname in scenarios:
        sj = find_scenario_json(sname, args.scenario_dir)
        if not sj:
            print(f'  SKIP: {sname} (no scenario.json found)')
            continue

        if args.all:
            pkg_dir = out_dir / sname
            pkg_dir.mkdir(parents=True, exist_ok=True)
            out_path = pkg_dir / 'field_diagram.png'
        else:
            out_path = out_dir / f'{sname}_field_diagram.png'

        generate_diagram(str(sj), str(out_path))


if __name__ == '__main__':
    main()