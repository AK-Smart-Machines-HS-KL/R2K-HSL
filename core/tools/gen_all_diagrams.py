#!/usr/bin/env python3
"""Regenerate field diagrams for ALL scenarios with Qwen's instructions
overlaid as yellow dotted arrows (matching the visualizer style).

For scenarios with "OUTPUT TO BRIDGE" in analysis.md, parse from there.
For scenarios without it, probe Qwen live and use the output.

Usage:
    python3 tools/gen_h1_diagrams.py --all
    python3 tools/gen_h1_diagrams.py --scenario 3vs3_attack_center
"""
import argparse
import json
import os
import re
import sys
import requests
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

BASE_DIR = Path(__file__).parent.parent
SRC_DIR = BASE_DIR / "src"
SCENARIO_DIR = SRC_DIR / "scenario"

sys.path.insert(0, str(SRC_DIR / "tools"))
from gen_field_diagrams import draw_field, draw_entities, FIELD_X_MIN, FIELD_X_MAX, FIELD_Y_MIN, FIELD_Y_MAX

sys.path.insert(0, str(SRC_DIR))
sys.path.insert(0, str(SRC_DIR / "ai_tactics"))
os.environ["R2K_TEXT_MODE"] = "1"

ORACLE_LINE_RE = re.compile(
    r'blue_(\d+)\s*:?\s*(?:move\s+to\s+\(?\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\)?'
    r'|cover\s+the\s+goal\s+line\s+at\s+\(?\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\)?'
    r'|hold\s+position'
    r'|kick'
    r'|mark\s+red_\d+)',
    re.IGNORECASE
)


def parse_output_from_analysis(analysis_path):
    """Extract bot→target mappings from the OUTPUT TO BRIDGE section."""
    if not analysis_path.exists():
        return {}
    text = open(analysis_path).read()

    # Find the OUTPUT TO BRIDGE section
    output_start = text.find('### OUTPUT TO BRIDGE')
    if output_start == -1:
        output_start = text.find('## Oracle')
        if output_start == -1:
            return {}

    # Find end
    rest = text[output_start:]
    end_markers = ['### RECOMMENDED', '### EXPERT', '\n---\n', '## User Feedback', '## GLM-5.2',
                   '## Oracle (strategic)', '## Score', '![score']
    oracle_text = rest
    for marker in end_markers:
        idx = rest.find(marker)
        if idx != -1:
            oracle_text = rest[:idx]
            break

    targets = {}
    for line in oracle_text.splitlines():
        line = line.strip()
        if not line or line.startswith('#') or line.startswith('OUTPUT'):
            continue
        m = ORACLE_LINE_RE.search(line)
        if m:
            bot_id = int(m.group(1))
            bot_name = f'blue_{bot_id}'
            if m.group(2) is not None and m.group(3) is not None:
                targets[bot_name] = {'x': float(m.group(2)), 'y': float(m.group(3)), 'action': 'Move'}
            elif m.group(4) is not None and m.group(5) is not None:
                targets[bot_name] = {'x': float(m.group(4)), 'y': float(m.group(5)), 'action': 'Cover'}
            elif 'kick' in line.lower():
                targets[bot_name] = {'action': 'Kick'}
            elif 'hold' in line.lower():
                targets[bot_name] = {'action': 'Hold'}
            elif 'mark' in line.lower():
                targets[bot_name] = {'action': 'Mark'}

    return targets


def probe_qwen_for_output(scenario_name):
    """Probe Qwen for the scenario and return parsed targets."""
    import r2k_evaluator as ev
    ev._active_mode = '3vs3'
    ev._prompt_cache.clear()
    sys_prompt = ev._get_sys_prompt('playing')
    header = ev._read_fragment('header_k3.txt')

    sj_path = SCENARIO_DIR / scenario_name / "scenario.json"
    if not sj_path.exists():
        sj_path = SCENARIO_DIR / f"{scenario_name}.json"
    with open(sj_path) as f:
        sj = json.load(f)
    ents = sj['entities']
    world_text = ev._build_text_world(ents, {'status': 'playing', 'blue': 0, 'red': 0})
    blue_names = ', '.join(sorted(k for k in ents if k.startswith('blue')))
    user_prompt = world_text + f'\n\nCommand: {blue_names}\n\n' + header

    payload = {
        'model': 'qwen2.5:3b', 'prompt': user_prompt, 'system': sys_prompt,
        'stream': False, 'keep_alive': '1h',
        'options': {'temperature': 0.0, 'num_predict': 200, 'num_ctx': 4096, 'stop': ['<|im_end|>']}
    }
    resp = requests.post('http://127.0.0.1:11434/api/generate', json=payload, timeout=60)
    raw = resp.json().get('response', '')

    targets = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        m = ORACLE_LINE_RE.search(line)
        if m:
            bot_id = int(m.group(1))
            bot_name = f'blue_{bot_id}'
            if m.group(2) is not None and m.group(3) is not None:
                targets[bot_name] = {'x': float(m.group(2)), 'y': float(m.group(3)), 'action': 'Move'}
            elif m.group(4) is not None and m.group(5) is not None:
                targets[bot_name] = {'x': float(m.group(4)), 'y': float(m.group(5)), 'action': 'Cover'}
            elif 'kick' in line.lower():
                targets[bot_name] = {'action': 'Kick'}
            elif 'hold' in line.lower():
                targets[bot_name] = {'action': 'Hold'}
            elif 'mark' in line.lower():
                targets[bot_name] = {'action': 'Mark'}

    return targets, raw


def draw_qwen_arrows(ax, entities, qwen_targets):
    """Draw yellow dotted arrows from each blue bot to its Qwen-commanded target.
    No text labels on the arrows — just the dotted line and target circle.
    Kick = triangle marker, Hold = square, no text annotations."""
    arrow_count = 0
    for bot_name, target in qwen_targets.items():
        if bot_name not in entities:
            continue
        start = entities[bot_name]
        sx, sy = float(start.get('x', 0)), float(start.get('y', 0))

        if 'x' not in target or 'y' not in target:
            if target.get('action') == 'Kick':
                ax.plot(sx, sy, marker='v', color='#ffeb3b', markersize=10,
                        zorder=7, markeredgecolor='black', markeredgewidth=0.5)
            elif target.get('action') == 'Hold':
                ax.plot(sx, sy, marker='s', color='#ffeb3b', markersize=8,
                        zorder=7, markeredgecolor='black', markeredgewidth=0.5)
            continue

        tx, ty = target['x'], target['y']
        ax.annotate('', xy=(tx, ty), xytext=(sx, sy),
                    arrowprops=dict(arrowstyle='->', color='#ffeb3b', linestyle=':',
                                   linewidth=2.0, shrinkA=12, shrinkB=8),
                    zorder=7)
        ax.plot(tx, ty, 'o', color='#ffeb3b', markersize=8,
                markerfacecolor='none', markeredgewidth=2, zorder=7)
        arrow_count += 1

    return arrow_count


def generate_diagram_with_arrows(scenario_dir, qwen_targets=None, qwen_raw=None):
    """Generate a field diagram with Qwen arrows overlaid."""
    scenario_path = scenario_dir / "scenario.json"
    output_path = scenario_dir / "field_diagram.png"

    with open(scenario_path) as f:
        data = json.load(f)

    scenario_name = data.get('scenario_name', scenario_dir.name)
    tactical = data.get('tactical_situation', '')
    entities = data.get('entities', {})

    fig, ax = plt.subplots(1, 1, figsize=(12, 8))
    fig.patch.set_facecolor('#1a1a1a')

    draw_field(ax)
    draw_entities(ax, entities)

    # Field margins are set in draw_field (±0.5) — don't override here
    # so the field fills most of the figure (90% width, 86% height)

    n_arrows = 0
    if qwen_targets:
        n_arrows = draw_qwen_arrows(ax, entities, qwen_targets)
    elif qwen_raw:
        # Parse from raw text
        targets = {}
        for line in qwen_raw.splitlines():
            line = line.strip()
            if not line:
                continue
            m = ORACLE_LINE_RE.search(line)
            if m:
                bot_id = int(m.group(1))
                bot_name = f'blue_{bot_id}'
                if m.group(2) is not None and m.group(3) is not None:
                    targets[bot_name] = {'x': float(m.group(2)), 'y': float(m.group(3)), 'action': 'Move'}
                elif m.group(4) is not None and m.group(5) is not None:
                    targets[bot_name] = {'x': float(m.group(4)), 'y': float(m.group(5)), 'action': 'Cover'}
                elif 'kick' in line.lower():
                    targets[bot_name] = {'action': 'Kick'}
                elif 'hold' in line.lower():
                    targets[bot_name] = {'action': 'Hold'}
                elif 'mark' in line.lower():
                    targets[bot_name] = {'action': 'Mark'}
        n_arrows = draw_qwen_arrows(ax, entities, targets)

    ax.set_title(f'{scenario_name} — Qwen Oracle (yellow dotted arrows)',
                 color='white', fontsize=13, fontweight='bold', pad=10)
    if tactical:
        ax.text(0.5, -0.08, tactical, transform=ax.transAxes, ha='center',
                fontsize=8, color='#aaaaaa', style='italic')

    ax.tick_params(colors='white', labelsize=7)
    for spine in ax.spines.values():
        spine.set_color('#555555')

    ax.set_xlabel('X (m)', color='white', fontsize=8)
    ax.set_ylabel('Y (m)', color='white', fontsize=8)

    plt.tight_layout()
    fig.savefig(str(output_path), dpi=150, bbox_inches='tight',
                facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f'  {scenario_name}: {n_arrows} arrows → {output_path.name}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", type=str)
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()

    parser.add_argument("--all-empirical", action="store_true", help="Generate for empirical scenarios only")
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
        sdir = SCENARIO_DIR / scen
        if not sdir.exists():
            print(f'  SKIP: {scen}')
            continue

        # Try to parse from analysis.md first
        targets = parse_output_from_analysis(sdir / "analysis.md")

        if targets:
            generate_diagram_with_arrows(sdir, qwen_targets=targets)
        else:
            # Probe Qwen live
            print(f'  Probing Qwen for {scen}...')
            targets, raw = probe_qwen_for_output(scen)
            if targets:
                generate_diagram_with_arrows(sdir, qwen_targets=targets)
            else:
                print(f'  SKIP: no targets found for {scen}')


if __name__ == "__main__":
    main()