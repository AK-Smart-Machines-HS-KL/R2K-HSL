#!/usr/bin/env python3
"""Phase I3 battery: JSON min_ents encoding vs C3 text transform.

For ~20 situations (real scenario starting states + edge cases + referee
statuses), probes Ollama with BOTH encodings using the evaluator's actual
assembly logic (_assemble_prompt / _build_text_world / text_parse /
fast_parse). Verifies: transform renders sensibly, token budget, parse
success, latency impact.

Usage:
  python3 tools/i3_battery.py [--situations N] [--model qwen2.5:3b]

Output: results/i3_battery_report.md + raw records results/i3_battery_raw.jsonl
"""

import argparse
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ai_tactics"))

import r2k_evaluator as ev

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
REPORT_PATH = os.path.join(RESULTS_DIR, "i3_battery_report.md")
RAW_PATH = os.path.join(RESULTS_DIR, "i3_battery_raw.jsonl")

SITUATIONS = [
    # (label, status, score_blue, score_red, entities)
    ("kickoff_center", "kickoff", 0, 0, {
        "soccer_ball": {"x": 0.0, "y": 0.0},
        "blue_1": {"x": -0.8, "y": 0.3}, "blue_2": {"x": -2.5, "y": -1.5},
        "blue_3": {"x": -4.0, "y": 0.0},
        "red_1": {"x": 1.0, "y": 0.0}, "red_2": {"x": 2.5, "y": 1.5},
        "red_3": {"x": 4.0, "y": -0.5},
    }),
    ("attack_center", "playing", 0, 0, {
        "soccer_ball": {"x": 2.2, "y": 0.3},
        "blue_1": {"x": 1.8, "y": 0.2}, "blue_2": {"x": -1.0, "y": 1.5},
        "blue_3": {"x": -4.2, "y": 0.0},
        "red_1": {"x": 3.0, "y": 0.0}, "red_2": {"x": 2.5, "y": 2.0},
        "red_3": {"x": 4.2, "y": -0.5},
    }),
    ("defensive_crisis", "playing", 0, 0, {
        "soccer_ball": {"x": -3.1, "y": 0.45},
        "blue_1": {"x": -2.7, "y": 0.3}, "blue_2": {"x": -1.5, "y": -0.6},
        "blue_3": {"x": -4.2, "y": 0.0},
        "red_1": {"x": -3.0, "y": 0.4}, "red_2": {"x": -1.8, "y": 1.2},
        "red_3": {"x": 0.5, "y": -0.5},
    }),
    ("fast_counter", "playing", 1, 0, {
        "soccer_ball": {"x": 1.0, "y": 1.0},
        "blue_1": {"x": -1.8, "y": -0.4}, "blue_2": {"x": -1.5, "y": -2.5},
        "blue_3": {"x": -4.0, "y": 0.0},
        "red_1": {"x": 3.5, "y": 1.5}, "red_2": {"x": 4.2, "y": 2.5},
        "red_3": {"x": 4.0, "y": -2.5},
    }),
    ("goalie_active_ball_near", "playing", 0, 1, {
        "soccer_ball": {"x": -4.0, "y": 1.2},
        "blue_1": {"x": -4.2, "y": 0.5}, "blue_2": {"x": -2.0, "y": 1.5},
        "blue_3": {"x": 0.0, "y": -1.0},
        "red_1": {"x": -3.8, "y": 1.0}, "red_2": {"x": -1.5, "y": 0.0},
        "red_3": {"x": 1.0, "y": 1.5},
    }),
    ("cluster_two_bots", "playing", 0, 0, {
        "soccer_ball": {"x": 3.0, "y": 0.0},
        "blue_1": {"x": 2.8, "y": 0.1}, "blue_2": {"x": 2.9, "y": -0.1},
        "blue_3": {"x": -4.0, "y": 0.0},
        "red_1": {"x": 3.5, "y": 0.5}, "red_2": {"x": 1.0, "y": -1.5},
        "red_3": {"x": 4.2, "y": -0.5},
    }),
    ("boundary_ball_top_right", "playing", 0, 0, {
        "soccer_ball": {"x": 4.4, "y": 2.9},
        "blue_1": {"x": 4.0, "y": 2.0}, "blue_2": {"x": 0.0, "y": 1.0},
        "blue_3": {"x": -4.0, "y": 0.0},
        "red_1": {"x": 4.0, "y": 1.0}, "red_2": {"x": 2.0, "y": 2.5},
        "red_3": {"x": 4.2, "y": -2.0},
    }),
    ("ball_out_red_kickin", "ball_out", 0, 0, {
        "soccer_ball": {"x": 0.0, "y": 3.0},
        "blue_1": {"x": -1.0, "y": 2.0}, "blue_2": {"x": 0.0, "y": 0.0},
        "blue_3": {"x": -4.0, "y": 0.0},
        "red_1": {"x": 1.0, "y": 2.5}, "red_2": {"x": 2.0, "y": 0.0},
        "red_3": {"x": 4.0, "y": -1.0},
    }),
    ("goal_kick_blue", "goal_kick", 1, 1, {
        "soccer_ball": {"x": -3.5, "y": 1.0},
        "blue_1": {"x": -4.0, "y": 1.0}, "blue_2": {"x": -1.0, "y": 0.0},
        "blue_3": {"x": 1.0, "y": -1.5},
        "red_1": {"x": -2.0, "y": 0.5}, "red_2": {"x": 0.5, "y": 1.5},
        "red_3": {"x": 3.0, "y": -0.5},
    }),
    ("corner_kick_in_red", "corner_kick_in", 2, 1, {
        "soccer_ball": {"x": 4.3, "y": 2.8},
        "blue_1": {"x": -4.0, "y": 0.0}, "blue_2": {"x": -1.5, "y": 1.0},
        "blue_3": {"x": 0.0, "y": 2.0},
        "red_1": {"x": 3.0, "y": 2.0}, "red_2": {"x": 2.0, "y": 0.0},
        "red_3": {"x": 4.2, "y": -0.5},
    }),
    ("2vs1_attack", "playing", 0, 0, {
        "soccer_ball": {"x": 1.0, "y": 0.0},
        "blue_1": {"x": 0.5, "y": 1.5}, "blue_2": {"x": 0.5, "y": -1.5},
        "red_1": {"x": 2.0, "y": 0.0},
    }),
    ("1vs1_defend", "playing", 0, 1, {
        "soccer_ball": {"x": -3.5, "y": 0.0},
        "blue_1": {"x": 0.0, "y": 0.0},
        "red_1": {"x": -2.0, "y": 0.0},
    }),
    ("3vs2_extra_blue", "playing", 0, 0, {
        "soccer_ball": {"x": 2.0, "y": -1.0},
        "blue_1": {"x": 1.5, "y": -0.8}, "blue_2": {"x": -2.0, "y": 0.0},
        "blue_3": {"x": -4.0, "y": 1.0},
        "red_1": {"x": 3.0, "y": -1.0}, "red_2": {"x": 1.0, "y": 1.0},
    }),
    ("red_deep_attack", "playing", 1, 2, {
        "soccer_ball": {"x": -2.5, "y": 0.0},
        "blue_1": {"x": 1.5, "y": 0.5}, "blue_2": {"x": 2.0, "y": -1.0},
        "blue_3": {"x": -4.2, "y": 0.0},
        "red_1": {"x": -2.2, "y": -0.2}, "red_2": {"x": -1.0, "y": 1.0},
        "red_3": {"x": 0.5, "y": -0.5},
    }),
    ("midfield_scramble", "playing", 0, 0, {
        "soccer_ball": {"x": 0.0, "y": 0.0},
        "blue_1": {"x": -0.5, "y": 0.2}, "blue_2": {"x": -0.3, "y": -0.4},
        "blue_3": {"x": -4.0, "y": 1.0},
        "red_1": {"x": 0.4, "y": 0.1}, "red_2": {"x": 0.6, "y": -0.3},
        "red_3": {"x": 4.0, "y": -1.0},
    }),
    ("ball_deep_own_zone", "playing", 0, 3, {
        "soccer_ball": {"x": -3.8, "y": -1.5},
        "blue_1": {"x": -3.5, "y": -1.2}, "blue_2": {"x": -1.0, "y": 1.5},
        "blue_3": {"x": -4.2, "y": 0.0},
        "red_1": {"x": -3.6, "y": -1.4}, "red_2": {"x": -2.0, "y": 0.5},
        "red_3": {"x": 0.5, "y": 1.0},
    }),
    ("kickoff_after_goal", "kickoff", 2, 2, {
        "soccer_ball": {"x": 0.0, "y": 0.0},
        "blue_1": {"x": -0.7, "y": 0.2}, "blue_2": {"x": -2.0, "y": 1.5},
        "blue_3": {"x": -4.0, "y": 0.0},
        "red_1": {"x": 1.0, "y": 0.0}, "red_2": {"x": 2.5, "y": -1.5},
        "red_3": {"x": 4.0, "y": 0.5},
    }),
    ("wide_spacing_attack", "playing", 0, 0, {
        "soccer_ball": {"x": 1.0, "y": 1.8},
        "blue_1": {"x": 0.5, "y": 1.6}, "blue_2": {"x": 2.5, "y": -1.5},
        "blue_3": {"x": -4.0, "y": 0.0},
        "red_1": {"x": 2.0, "y": 1.5}, "red_2": {"x": 3.0, "y": 0.0},
        "red_3": {"x": 4.2, "y": -2.0},
    }),
    ("no_blue_near_ball", "playing", 0, 0, {
        "soccer_ball": {"x": 4.0, "y": 2.0},
        "blue_1": {"x": -1.0, "y": 0.0}, "blue_2": {"x": -2.5, "y": -1.5},
        "blue_3": {"x": -4.0, "y": 0.0},
        "red_1": {"x": 3.5, "y": 1.5}, "red_2": {"x": 2.0, "y": 0.5},
        "red_3": {"x": 4.2, "y": -0.5},
    }),
    ("high_line_press", "playing", 0, 0, {
        "soccer_ball": {"x": 1.5, "y": 0.0},
        "blue_1": {"x": 0.5, "y": 0.0}, "blue_2": {"x": 2.0, "y": -1.5},
        "blue_3": {"x": -4.0, "y": 0.0},
        "red_1": {"x": 1.0, "y": 0.5}, "red_2": {"x": 3.0, "y": 1.0},
        "red_3": {"x": 4.2, "y": 0.0},
    }),
]


def call_ollama(prompt, system, num_predict, model):
    payload = {
        "model": model,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "temperature": 0.0,
        "num_predict": num_predict,
        "keep_alive": "1h",
    }
    req = urllib.request.Request(
        f"{os.getenv('OLLAMA_URL', 'http://127.0.0.1:11434')}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=150) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    latency_ms = round((time.time() - t0) * 1000)
    return body.get("response", "").strip(), latency_ms


def run_encoding(label, ents, match_state, model):
    """Run one situation in the given TEXT_MODE and return result dict."""
    status = match_state.get("status", "playing")
    is_explain = os.getenv("R2K_EXPLAIN", "0") == "1"
    ev._prompt_cache.clear()

    if ev.TEXT_MODE:
        user_prompt = ev._build_text_world(ents, match_state)
        blue_names = ", ".join(sorted(k for k in ents if k.startswith("blue")))
        user_prompt += f"\n\nCommand: {blue_names}\n\n" + (
            ev.TEXT_EXPLAIN_INSTRUCTION if is_explain else ev._text_output_header(len([k for k in ents if k.startswith("blue")])))
        tokens_limit = 600 if is_explain else 200
    else:
        min_ents = {k: {"x": round(v["x"], 1), "y": round(v["y"], 1)} for k, v in ents.items()}
        user_prompt = json.dumps(min_ents) + "\n\nCRITICAL: Output ONLY valid JSON. " + (
            "Include 'analysis', 'oracle', and 'assignments' keys." if is_explain
            else "Output ONLY the 'assignments' key."
        ) + " End immediately after closing bracket."
        tokens_limit = 600 if is_explain else 150

    sys_prompt = ev._get_sys_prompt(status)
    raw, latency_ms = call_ollama(user_prompt, sys_prompt, tokens_limit, model)

    if ev.TEXT_MODE:
        data, code = ev.text_parse(raw)
        if data is None:
            data, json_err = ev.fast_parse(raw)
            code = (10 + json_err) if data is not None else 99
    else:
        data, code = ev.fast_parse(raw)

    n_blue = len([k for k in ents if k.startswith("blue")])
    n_assign = len(data.get("assignments", {})) if data else 0
    return {
        "encoding": "text" if ev.TEXT_MODE else "json",
        "situation": label,
        "status": status,
        "sys_prompt_chars": len(sys_prompt),
        "user_prompt_chars": len(user_prompt),
        "user_prompt_tokens_est": len(user_prompt.split()),
        "latency_ms": latency_ms,
        "parse_code": code,
        "parse_success": data is not None,
        "n_blue": n_blue,
        "n_assign": n_assign,
        "full_coverage": data is not None and n_assign == n_blue,
        "raw_response": raw[:500],
    }


def main():
    ap = argparse.ArgumentParser(description="Phase I3 battery: JSON vs text encoding")
    ap.add_argument("--situations", type=int, default=len(SITUATIONS))
    ap.add_argument("--model", default=os.getenv("R2K_OLLAMA_MODEL", "qwen2.5:3b"))
    args = ap.parse_args()

    os.makedirs(RESULTS_DIR, exist_ok=True)
    situations = SITUATIONS[:args.situations]
    results = []

    for i, (label, status, b, r, ents) in enumerate(situations, 1):
        ms = {"status": status, "blue": b, "red": r}
        for text_mode in (False, True):
            ev.TEXT_MODE = text_mode
            res = run_encoding(label, ents, ms, args.model)
            res["score"] = f"{b}:{r}"
            results.append(res)
            tag = "TEXT" if text_mode else "JSON"
            print(f"[{i}/{len(situations)}] {label} {tag}: "
                  f"parse={'OK' if res['parse_success'] else 'FAIL'}({res['parse_code']}) "
                  f"covers={res['full_coverage']} {res['n_assign']}/{res['n_blue']} "
                  f"tok={res['user_prompt_tokens_est']} lat={res['latency_ms']}ms")

    with open(RAW_PATH, "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    # Report
    with open(REPORT_PATH, "w") as f:
        f.write(f"# Phase I3 Battery Report ({time.strftime('%Y-%m-%d %H:%M')})\n\n")
        f.write(f"Model: `{args.model}` | Situations: {len(situations)} | "
                f"Probes: {len(results)} | Explain: {os.getenv('R2K_EXPLAIN', '0')}\n\n")
        f.write("## Per-situation results\n\n")
        f.write("| Situation | Status | Encoding | Parse | Code | Coverage | Tokens (user) | Latency ms |\n")
        f.write("|---|---|---|---|---|---|---|---:|\n")
        for r in results:
            f.write(f"| {r['situation']} | {r['status']} | {r['encoding']} | "
                    f"{'OK' if r['parse_success'] else 'FAIL'} | {r['parse_code']} | "
                    f"{r['n_assign']}/{r['n_blue']} | {r['user_prompt_tokens_est']} | {r['latency_ms']} |\n")

        f.write("\n## Summary\n\n")
        for enc in ("json", "text"):
            subset = [r for r in results if r["encoding"] == enc]
            ok = [r for r in subset if r["parse_success"]]
            cov = [r for r in subset if r["full_coverage"]]
            lat = [r["latency_ms"] for r in subset]
            f.write(f"**{enc.upper()}:** {len(ok)}/{len(subset)} parse OK, "
                    f"{len(cov)}/{len(subset)} full coverage, "
                    f"latency p50 {sorted(lat)[len(lat)//2]}ms, "
                    f"mean user-prompt tokens {sum(r['user_prompt_tokens_est'] for r in subset)//len(subset)}\n")

        f.write("\n## Failures (raw responses)\n\n")
        for r in results:
            if not r["parse_success"]:
                f.write(f"### {r['situation']} [{r['encoding']}]\n\n`{r['raw_response']}`\n\n")

    print(f"\nDone. Report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
