#!/usr/bin/env python3
"""A/B test: KV prefix-cache behavior of two prompt layouts.

Layout A (current):  user turn = <world JSON> + CRITICAL instruction
Layout B (moved):    user turn = CRITICAL instruction + <world JSON>  (world at the very end)

Both layouts share byte-identical system prompt and instruction text across
calls; only the world-state JSON differs (call 1 vs call 2). Measures Ollama's
prompt_eval_count/duration, eval_count/duration from the /api/generate response.

Usage: python3 experiments/cache_layout_ab.py [--model qwen2.5:3b]
"""
import json
import glob
import os
import sys
import time
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ai_tactics"))
import requests

import r2k_evaluator as ev  # reuse real fragment assembly (_get_sys_prompt)

CRITICAL = "CRITICAL: Output ONLY valid JSON. Output ONLY the 'assignments' key. End immediately after closing bracket."

SYNTHETIC_WORLD_A = {
    "soccer_ball": {"x": -2.7, "y": 2.3},
    "blue_1": {"x": -3.0, "y": 1.5},
    "blue_2": {"x": -3.0, "y": 0.0},
    "blue_3": {"x": -3.0, "y": -1.5},
    "red_1": {"x": -2.5, "y": 2.0},
    "red_2": {"x": -1.0, "y": 2.5},
    "red_3": {"x": 0.5, "y": 0.0},
}
SYNTHETIC_WORLD_B = {
    "soccer_ball": {"x": -1.4, "y": 1.9},
    "blue_1": {"x": -2.6, "y": 1.2},
    "blue_2": {"x": -2.9, "y": 0.1},
    "blue_3": {"x": -3.0, "y": -1.4},
    "red_1": {"x": -2.1, "y": 1.8},
    "red_2": {"x": -0.4, "y": 2.3},
    "red_3": {"x": 0.8, "y": 0.2},
}


def load_real_worlds(log_dir):
    """Take two consecutive world snapshots from the newest llm_trace file."""
    traces = sorted(glob.glob(os.path.join(log_dir, "llm_trace_*.jsonl")))
    if not traces:
        return None, None
    snaps = []
    with open(traces[-1]) as f:
        for line in f:
            try:
                rec = json.loads(line)
            except Exception:
                continue
            ws = rec.get("world_snapshot")
            if ws and "soccer_ball" in ws and ws not in snaps:
                snaps.append(ws)
                if len(snaps) == 2:
                    break
    return (snaps[0], snaps[1]) if len(snaps) == 2 else (None, None)


def make_prompt(layout, world):
    world_json = json.dumps(world)
    if layout == "A":
        return world_json + "\n\n" + CRITICAL
    else:
        return CRITICAL + "\n\n" + world_json


def call(payload):
    t0 = time.time()
    resp = requests.post(ev.OLLAMA_URL, json=payload, timeout=120.0)
    wall_ms = int((time.time() - t0) * 1000)
    d = resp.json()
    return {
        "wall_ms": wall_ms,
        "prompt_eval_count": d.get("prompt_eval_count"),
        "prompt_eval_duration_ms": round(d.get("prompt_eval_duration", 0) / 1e6, 1),
        "eval_count": d.get("eval_count"),
        "eval_duration_ms": round(d.get("eval_duration", 0) / 1e6, 1),
        "load_duration_ms": round(d.get("load_duration", 0) / 1e6, 1),
        "total_duration_ms": round(d.get("total_duration", 0) / 1e6, 1),
        "response": (d.get("response") or "")[:80],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen2.5:3b")
    ap.add_argument("--num-predict", type=int, default=150)
    ap.add_argument("--log-dir", default=os.path.join(ev.BASE_DIR, "logs"))
    args = ap.parse_args()

    sys_prompt = ev._get_sys_prompt("playing")
    print(f"system prompt: {len(sys_prompt)} chars, hash {ev._get_sys_prompt('playing') and __import__('hashlib').sha1(sys_prompt.encode()).hexdigest()[:16]}")
    print(f"model: {args.model}, num_predict: {args.num_predict}, OLLAMA_URL: {ev.OLLAMA_URL}")

    world_a, world_b = load_real_worlds(args.log_dir)
    if world_a is None:
        print("(no trace worlds found — using synthetic snapshots)")
        world_a, world_b = SYNTHETIC_WORLD_A, SYNTHETIC_WORLD_B
    print(f"world A: {json.dumps(world_a)[:100]}...")
    print(f"world B: {json.dumps(world_b)[:100]}...")

    base = {
        "model": args.model,
        "stream": False,
        "keep_alive": "1h",
        "options": {
            "temperature": 0.0,
            "num_predict": args.num_predict,
            "num_ctx": 4096,
            "stop": ["<|im_end|>", "<|endoftext|>"],
        },
    }

    # Warm-up: load model + populate system-prefix cache (excluded from report).
    call({**base, "system": sys_prompt, "prompt": make_prompt("A", world_a)})
    time.sleep(0.5)

    results = {}
    for layout, label in (("A", "A: world JSON first (current)"), ("B", "B: world JSON last (moved)")):
        results[layout] = {}
        for i, world in enumerate((world_a, world_b), start=1):
            payload = {**base, "system": sys_prompt, "prompt": make_prompt(layout, world)}
            results[layout][i] = call(payload)
            time.sleep(0.3)
        print()

    hdr = f"{'':6s} {'wall_ms':>8s} {'p_eval_cnt':>10s} {'p_eval_ms':>9s} {'eval_cnt':>8s} {'eval_ms':>8s} {'load_ms':>8s}"
    print(hdr)
    print("-" * len(hdr))
    for layout, label in (("A", "A: world JSON first (current)"), ("B", "B: world JSON last (moved)")):
        for i in (1, 2):
            r = results[layout][i]
            print(f"{label[:3]} call{i} {r['wall_ms']:>8d} {r['prompt_eval_count']:>10d} {r['prompt_eval_duration_ms']:>9.1f} {r['eval_count']:>8d} {r['eval_duration_ms']:>8.1f} {r['load_duration_ms']:>8.1f}")
    print("-" * len(hdr))
    a1, a2 = results["A"][1], results["A"][2]
    b1, b2 = results["B"][1], results["B"][2]
    print(f"\nA: p_eval tokens call1={a1['prompt_eval_count']} call2={a2['prompt_eval_count']}  (delta {a2['prompt_eval_count'] - a1['prompt_eval_count']:+d})")
    print(f"B: p_eval tokens call1={b1['prompt_eval_count']} call2={b2['prompt_eval_count']}  (delta {b2['prompt_eval_count'] - b1['prompt_eval_count']:+d})")
    print(f"A p_eval_ms call2: {a2['prompt_eval_duration_ms']}   B p_eval_ms call2: {b2['prompt_eval_duration_ms']}")
    print(f"A wall call2: {a2['wall_ms']}ms   B wall call2: {b2['wall_ms']}ms")
    out = os.path.join(ev.BASE_DIR, "results", "cache_layout_ab.json")
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nresults → {out}")


if __name__ == "__main__":
    main()
