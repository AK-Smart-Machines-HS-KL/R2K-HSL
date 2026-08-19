#!/usr/bin/env python3
"""Prompt inspector — dry-run assembly of the system prompt without launching ROS/Ollama.

Replicates setup_r2k.py's assembly logic in read-only mode:
  - Reads scenario JSON to determine blue_bots and mode
  - Assembles fragments in the same order as setup_r2k.py
  - Applies clean_json_samples() for --no-explain / --explain
  - Prints the assembled prompt + per-fragment breakdown + token estimate

Usage:
  python3 tools/dump_prompt.py --scenario 3vs3_attack_center --strategy strat_default --no-explain
  python3 tools/dump_prompt.py --scenario 2vs2_default --strategy strat_aggro --explain
"""
import argparse
import json
import os
import re
import sys


def clean_json_samples(content, explain_active):
    pattern = r'ASSISTANT:\s*'
    matches = list(re.finditer(pattern, content))
    if not matches:
        return content
    output = ""
    last_idx = 0
    for m in matches:
        start_pos = m.start()
        end_pos = m.end()
        output += content[last_idx:start_pos]
        brace_count = 0
        json_start = -1
        json_end = -1
        for idx in range(end_pos, len(content)):
            char = content[idx]
            if char == '{':
                if brace_count == 0:
                    json_start = idx
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    json_end = idx + 1
                    break
        if json_start == -1 or json_end == -1:
            output += content[start_pos:end_pos]
            last_idx = end_pos
            continue
        raw_json = content[json_start:json_end]
        before_text = content[max(0, start_pos - 300):start_pos]
        analysis_val = "Tactical assessment of entity positions and ball trajectory."
        oracle_val = "Predictive optimization of team response to secure match advantage."
        if "DEFENSIVE PASS" in before_text or "CLEARANCE" in before_text:
            analysis_val = "blue_1 clears the ball from the defensive zone towards blue_2."
            oracle_val = "Passing the ball out of danger into the midfield."
        elif "ANTI-CLUSTERING" in before_text:
            analysis_val = "blue_1 attacks the ball while blue_2 drops back to support and avoid clustering."
            oracle_val = "Maintain optimal distance between teammates to control the field."
        elif "BOUNDARY STAGING" in before_text:
            analysis_val = "blue_1 moves to intercept the ball near the boundary while blue_2 guards the goal."
            oracle_val = "Secure the defensive line to prevent any immediate shots on goal."
        try:
            data = json.loads(raw_json)
        except Exception:
            try:
                sanitized = re.sub(r'\n\s*', ' ', raw_json)
                data = json.loads(sanitized)
            except Exception:
                data = {}

        if explain_active:
            new_data = {}
            new_data["analysis"] = data.get("analysis", analysis_val)
            new_data["oracle"] = data.get("oracle", oracle_val)
            if "assignments" in data:
                new_data["assignments"] = data["assignments"]
            else:
                data.pop("analysis", None)
                data.pop("oracle", None)
                new_data["assignments"] = data
            formatted_json = json.dumps(new_data, separators=(',', ': '))
        else:
            if "assignments" in data:
                new_data = {"assignments": data["assignments"]}
            else:
                data.pop("analysis", None)
                data.pop("oracle", None)
                new_data = {"assignments": data}
            formatted_json = json.dumps(new_data, separators=(',', ': '))
        output += "ASSISTANT: " + formatted_json
        last_idx = json_end
    output += content[last_idx:]
    return output


def main():
    parser = argparse.ArgumentParser(description="Prompt inspector (dry-run)")
    parser.add_argument('--scenario', type=str, default='2vs2_default')
    parser.add_argument('--strategy', type=str, default='strat_aggro')
    parser.add_argument('--explain', action='store_true', dest='explain', default=True)
    parser.add_argument('--no-explain', action='store_false', dest='explain')
    parser.add_argument('--demo', action='store_true', help='Demo/calibration mode — overrides mode to "demo"')
    parser.add_argument('--fragments-dir', type=str, default=None,
                        help='Override fragments directory (default: strategy/fragments)')
    args = parser.parse_args()

    src_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.dirname(src_dir)
    frag_path = args.fragments_dir or os.path.join(src_dir, "strategy", "fragments")

    scene_file = None
    for candidate in [
        os.path.join(src_dir, f"scenario/{args.scenario}/scenario.json"),
        os.path.join(src_dir, f"scenario/{args.scenario}.json"),
        os.path.join(src_dir, f"scenarios/{args.scenario}.json"),
    ]:
        if os.path.exists(candidate):
            scene_file = candidate
            break
    if not scene_file:
        print(f"ERROR: Scenario '{args.scenario}' not found in scenario/ or scenarios/", file=sys.stderr)
        sys.exit(1)

    with open(scene_file, 'r') as f:
        data = json.load(f)
    blue_bots = sorted([k for k in data.get('entities', {}).keys() if 'blue' in k])

    mode = data.get('mode') or (args.scenario.split('_')[0] if '_' in args.scenario else "3vs3")
    if args.demo:
        mode = "demo"
    clean_strat = args.strategy.replace('strat_', '')

    prompt_lines = [f"ACT_ON_BOTS: {', '.join(blue_bots)}", f"MODE: {mode}\n"]

    core_file = "rules_demo_core.txt" if mode == "demo" else "rules_core.txt"
    files = ["header.txt", core_file]
    rules_strat = f"rules_{clean_strat}.txt"
    rules_mode = f"rules_{mode}.txt"
    if os.path.exists(os.path.join(frag_path, rules_strat)):
        files.append(rules_strat)
    else:
        files.append(rules_mode)

    samples_strat = f"samples_{clean_strat}.txt"
    samples_mode = f"samples_{mode}.txt"
    if os.path.exists(os.path.join(frag_path, samples_strat)):
        files.append(samples_strat)
    else:
        files.append(samples_mode)

    breakdown = []
    for comp in files:
        c_path = os.path.join(frag_path, comp)
        if not os.path.exists(c_path):
            print(f"  WARNING: Missing fragment: {comp}", file=sys.stderr)
            continue
        with open(c_path, 'r') as f:
            content = f.read()
        if comp == "header.txt":
            instr = "- Include 'analysis' and 'oracle' keys." if args.explain else "- Output ONLY the 'assignments' key."
            content = content.replace("{{EXPLAIN_INSTRUCTION}}", instr)
        if "samples" in comp:
            content = clean_json_samples(content, args.explain)
        prompt_lines.append(f"### {comp.upper()} ###")
        prompt_lines.append(content + "\n")
        line_count = content.count('\n') + 1
        breakdown.append((comp, line_count, len(content)))

    final_prompt = '\n'.join(prompt_lines).strip()

    print("=" * 70)
    print("PROMPT INSPECTOR — dry-run assembly")
    print("=" * 70)
    print(f"Scenario:    {args.scenario}  (file: {os.path.basename(scene_file)})")
    print(f"Strategy:    {args.strategy}  (clean: {clean_strat})")
    print(f"Mode:        {mode}")
    print(f"Blue bots:   {blue_bots}")
    print(f"Explain:     {args.explain}")
    print(f"Fragments:   {frag_path}")
    print("-" * 70)
    print("FRAGMENT BREAKDOWN:")
    for name, lines, chars in breakdown:
        print(f"  {name:30s}  {lines:4d} lines  {chars:5d} chars")
    total_lines = sum(b[1] for b in breakdown)
    total_chars = sum(b[2] for b in breakdown)
    print(f"  {'TOTAL':30s}  {total_lines:4d} lines  {total_chars:5d} chars")
    print("-" * 70)
    print(f"ASSEMBLED PROMPT: {len(final_prompt)} chars  (~{len(final_prompt)//4} tokens)")
    print("=" * 70)
    print()
    print(final_prompt)
    print()
    print("=" * 70)
    print("END OF PROMPT")


if __name__ == "__main__":
    main()