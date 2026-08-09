#!/usr/bin/env python3
"""Phase W: Second-model monitor POC (Option B).

After Qwen produces a decision, Llama reviews it. If Llama disagrees
(missing bots, OOB, wrong direction), the monitor flags it.

Two modes:
  --review: Llama reviews Qwen's output, outputs "approve" or "corrected"
  --compare: Both models independently produce output, compare

Usage:
  python3 tools/phase_w_monitor.py --corpus tests/synthetic_worldstates/corpus_scenarios.jsonl \
    --only w1_goalie_abandonment,w2_clustering_trap,w3_wrong_direction_kick,w4_unmarked_attacker,w5_boundary_violation,w6_passivity_trap \
    --repeat 5 --tag pw_monitor
"""
import argparse
import json
import os
import sys
import time
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__)) + "/.."
SRC_DIR = os.path.join(BASE_DIR, "src")
sys.path.insert(0, SRC_DIR)
sys.path.insert(0, os.path.join(SRC_DIR, "tools"))
sys.path.insert(0, os.path.join(SRC_DIR, "ai_tactics"))

from i3_battery import call_ollama, parse_output, score_result

RESULTS_DIR = os.path.join(SRC_DIR, "results")
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
PRIMARY_MODEL = "qwen2.5:3b"
MONITOR_MODEL = "llama3.2:3b"

REVIEW_SYSTEM = """You are a soccer tactical monitor. You review a robot soccer decision.
You check for these errors:
1. Missing bots: all 3 blue bots must be assigned (blue_1, blue_2, blue_3)
2. Out of bounds: all positions must be within X: -4.5 to 4.5, Y: -3.0 to 3.0
3. Goalie abandonment: blue_1 (goalie) should stay near X=-4.0

If the decision has NO errors, output exactly: APPROVE
If the decision HAS errors, output the corrected decision (3 lines, one per blue bot):
blue_N move to (X, Y)
blue_N kick
blue_N hold"""


def call_model(model, system, prompt, timeout=60):
    payload = json.dumps({
        "model": model,
        "system": system,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.0, "num_predict": 200},
    }).encode()
    req = urllib.request.Request(OLLAMA_URL, data=payload,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read())
    return data.get("response", "")


def load_corpus(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def build_world_text(ents, match_state):
    lines = ["World state:"]
    for name in sorted(ents.keys()):
        e = ents[name]
        lines.append(f"  {name}: ({e.get('x', 0):.2f}, {e.get('y', 0):.2f})")
    return "\n".join(lines)


def run_monitor_probe(corpus, n_repeats, tag):
    """For each scenario: Qwen produces decision, Llama reviews it."""
    records = []

    for sit in corpus:
        ents = sit["entities"]
        match_state = {"status": sit.get("status", "playing"),
                       "blue": sit.get("score_blue", 0),
                       "red": sit.get("score_red", 0)}
        label = sit["label"]
        world_text = build_world_text(ents, match_state)

        # Get Qwen's system prompt from the evaluator
        import r2k_evaluator as ev
        ev._active_mode = "3vs3"
        ev._prompt_cache.clear()
        sys_prompt = ev._get_sys_prompt("playing")
        header = ev._read_fragment("header_k3.txt")
        blue_names = ", ".join(sorted(k for k in ents if k.startswith("blue")))
        user_prompt = world_text + f"\n\nCommand: {blue_names}\n\n" + header

        for rep in range(n_repeats):
            t0 = time.time()

            # Step 1: Qwen produces decision
            qwen_raw, qwen_lat = call_ollama(user_prompt, sys_prompt, 200, PRIMARY_MODEL)
            qwen_data, _, _, _ = parse_output(qwen_raw, True, True)
            qwen_assignments = qwen_data.get("assignments", {}) if qwen_data else {}

            # Step 2: Llama reviews Qwen's decision
            review_prompt = (
                f"{world_text}\n\n"
                f"Qwen's decision:\n{qwen_raw.strip()}\n\n"
                f"Review this decision. Output APPROVE or corrected 3-line decision."
            )
            monitor_raw = call_model(MONITOR_MODEL, REVIEW_SYSTEM, review_prompt)
            monitor_lat = time.time() - t0

            # Step 3: Parse monitor response
            approved = "APPROVE" in monitor_raw.upper().strip()[:10]

            # If monitor corrected, parse the corrected decision
            corrected_data = None
            if not approved:
                corrected_data, _, _, _ = parse_output(monitor_raw, True, True)
                corrected_assignments = corrected_data.get("assignments", {}) if corrected_data else {}
            else:
                corrected_assignments = {}

            # Score both
            qwen_scoring = score_result(qwen_assignments, ents, match_state.get("status", "playing")) if qwen_assignments else None
            monitor_scoring = score_result(corrected_assignments, ents, match_state.get("status", "playing")) if corrected_assignments else None

            qwen_hard = bool(qwen_scoring["hard_pass"]) if qwen_scoring else False
            monitor_hard = bool(monitor_scoring["hard_pass"]) if monitor_scoring else False

            records.append({
                "scenario": label,
                "repeat": rep + 1,
                "qwen_hard_pass": qwen_hard,
                "qwen_n_bots": len(qwen_assignments),
                "qwen_raw": qwen_raw[:300],
                "monitor_approved": approved,
                "monitor_corrected_hard_pass": monitor_hard,
                "monitor_corrected_n_bots": len(corrected_assignments),
                "monitor_raw": monitor_raw[:300],
                "qwen_latency_ms": qwen_lat,
                "total_latency_ms": round(monitor_lat * 1000),
            })

            status = "APPROVE" if approved else ("CORRECTED" + (" (better)" if monitor_hard and not qwen_hard else ""))
            print(f"  [{label} r{rep+1}] Qwen={'PASS' if qwen_hard else 'FAIL'}({len(qwen_assignments)}b) Monitor={status} total={monitor_lat:.1f}s")

    # Write results
    os.makedirs(RESULTS_DIR, exist_ok=True)
    raw_path = os.path.join(RESULTS_DIR, f"probe_{tag}_raw.jsonl")
    with open(raw_path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    # Summary
    total = len(records)
    qwen_pass = sum(1 for r in records if r["qwen_hard_pass"])
    approved = sum(1 for r in records if r["monitor_approved"])
    corrected = total - approved
    corrected_better = sum(1 for r in records if not r["monitor_approved"] and r["monitor_corrected_hard_pass"] and not r["qwen_hard_pass"])
    qwen_fail_but_monitor_fixes = sum(1 for r in records if not r["qwen_hard_pass"] and r["monitor_corrected_hard_pass"])
    avg_total_lat = sum(r["total_latency_ms"] for r in records) / total if total else 0

    report = f"""# Phase W Monitor POC Report ({time.strftime('%Y-%m-%d %H:%M')})

Primary: {PRIMARY_MODEL} | Monitor: {MONITOR_MODEL} | Probes: {total}

## Summary

| Metric | Value |
|---|---|
| Qwen hard-pass (alone) | {qwen_pass}/{total} ({qwen_pass/total:.0%}) |
| Monitor approved | {approved}/{total} ({approved/total:.0%}) |
| Monitor corrected | {corrected}/{total} ({corrected/total:.0%}) |
| Corrections that fixed Qwen's failure | {qwen_fail_but_monitor_fixes}/{corrected} |
| Avg total latency (Qwen + monitor) | {avg_total_lat:.0f}ms |
| Qwen latency alone (for comparison) | {sum(r['qwen_latency_ms'] for r in records)/total:.0f}ms |

## Per-scenario breakdown

| Scenario | Qwen pass | Approved | Corrected | Fixed? |
|---|---|---|---|---|
"""
    scenarios = sorted(set(r["scenario"] for r in records))
    for s in scenarios:
        s_recs = [r for r in records if r["scenario"] == s]
        qp = sum(1 for r in s_recs if r["qwen_hard_pass"])
        ap = sum(1 for r in s_recs if r["monitor_approved"])
        cp = len(s_recs) - ap
        fixed = sum(1 for r in s_recs if not r["qwen_hard_pass"] and r["monitor_corrected_hard_pass"])
        report += f"| {s} | {qp}/{len(s_recs)} | {ap}/{len(s_recs)} | {cp} | {fixed} |\n"

    report_path = os.path.join(RESULTS_DIR, f"probe_{tag}_report.md")
    with open(report_path, "w") as f:
        f.write(report)

    print(f"\nRaw: {raw_path}")
    print(f"Report: {report_path}")
    print(f"\nQwen alone: {qwen_pass}/{total} ({qwen_pass/total:.0%})")
    print(f"Monitor corrected: {corrected}/{total}, of which {qwen_fail_but_monitor_fixes} fixed Qwen's failure")
    print(f"Latency: Qwen alone {sum(r['qwen_latency_ms'] for r in records)/total:.0f}ms, with monitor {avg_total_lat:.0f}ms")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--only", default="")
    ap.add_argument("--repeat", type=int, default=5)
    ap.add_argument("--tag", default="pw_monitor")
    args = ap.parse_args()

    corpus = load_corpus(args.corpus)
    if args.only:
        only = set(args.only.split(","))
        corpus = [s for s in corpus if s["label"] in only]

    print(f"Phase W monitor POC: {len(corpus)} scenarios × {args.repeat} repeats")
    print(f"Primary: {PRIMARY_MODEL}, Monitor: {MONITOR_MODEL}")
    print()
    run_monitor_probe(corpus, args.repeat, args.tag)


if __name__ == "__main__":
    main()
