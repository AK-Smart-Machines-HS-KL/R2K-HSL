#!/usr/bin/env python3
"""A2bot syntax probe: test advanced task syntax against the 7B demo compiler.

Offline (no ROS). Uses the EXACT compiler prompt from r2k_evaluator.py
(_build_compiler_world_lines + _build_compiler_sys_prompt) with the
2vs0_demo world (soccer_ball (1,1), blue_1 (0,0), blue_2 (0,1), START (0,0)).

Usage:
  python3 tools/probe_a2bot_syntax.py --reps 5
  python3 tools/probe_a2bot_syntax.py --reps 1 --only scope1 baseline1   # smoke
"""
import argparse
import json
import math
import os
import sys
import time
from datetime import datetime

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
CORE_DIR = os.path.dirname(TOOLS_DIR)
sys.path.insert(0, os.path.join(CORE_DIR, 'src', 'ai_tactics'))

import requests  # noqa: E402
import r2k_evaluator as ev  # noqa: E402

PROBE_MODEL = "qwen2.5:7b"
PROBE_NUM_PREDICT = 400
PROBE_NUM_CTX = 4096
PROBE_TEMPERATURE = 0.0
PROBE_TIMEOUT_S = 120

FIELD_X_MAX = 4.5
FIELD_Y_MAX = 3.0

COORD_TOLERANCE = 0.05
BALL_APPROACH_TOLERANCE = 0.6

WORLD_ENTS = {
    "soccer_ball": {"x": 1.0, "y": 1.0},
    "blue_1": {"x": 0.0, "y": 0.0},
    "blue_2": {"x": 0.0, "y": 1.0},
}
START_POS = (0.0, 0.0)

BALL_POS = (1.0, 1.0)
KICK_OFFSET = 0.3

# Categories: scope = bot-selection syntax, baseline = known-good control,
# ballrel = ball-relative coords, formation = per-bot lists from one task,
# patrol = repeat loops, robust = negation/edge phrasing.
TASKS = [
    {"id": "scope1", "cat": "scope", "task": "(all) yahbooms goto 2,2",
     "expect": [(2.0, 2.0)]},
    {"id": "scope2", "cat": "scope", "task": "all yahbooms go to (2, 2)",
     "expect": [(2.0, 2.0)]},
    {"id": "scope3", "cat": "scope", "task": "simulated bots only; redo k1 goto 1,1",
     "expect": [(1.0, 1.0)]},
    {"id": "scope4", "cat": "scope", "task": "k1 goto 1,1",
     "expect": [(1.0, 1.0)]},
    {"id": "scope5", "cat": "scope", "task": "blue_2 go to (2,0)",
     "expect": [(2.0, 0.0)]},
    {"id": "scope6", "cat": "scope", "task": "both go to (2, 2)",
     "expect": [(2.0, 2.0)]},
    {"id": "baseline1", "cat": "baseline", "task": "go to (2, 0), then go to (2, 3)",
     "expect": [(2.0, 0.0), (2.0, 3.0)]},
    {"id": "baseline2", "cat": "baseline", "task": "blue_1 go to (2,0)",
     "expect": [(2.0, 0.0)]},
    {"id": "baseline3", "cat": "baseline", "task": "approach the ball into kicking distance",
     "expect": None, "ball_dist": True},
    {"id": "ballrel1", "cat": "ballrel", "task": "go to 0.5m left of the ball",
     "expect": [(BALL_POS[0], BALL_POS[1] + 0.5)]},
    {"id": "ballrel2", "cat": "ballrel", "task": "go to the ball, but stay 1m away from it",
     "expect": None, "ball_dist": 1.0},
    {"id": "formation1", "cat": "formation", "task": "line up at x=2, spread 1m apart",
     "expect": None},
    {"id": "formation2", "cat": "formation", "task": "blue_1 go to (2,2), blue_2 go to (2,-2)",
     "expect": None},
    {"id": "patrol1", "cat": "patrol", "task": "patrol between (1,1) and (2,2) three times",
     "expect": [(1.0, 1.0), (2.0, 2.0)]},
    {"id": "patrol2", "cat": "patrol", "task": "all bots go to the right wing",
     "expect": [(2.0, -2.5)]},
    {"id": "patrol3", "cat": "patrol", "task": "yahbooms draw a circle center (0,0) radius 1m",
     "expect": None},
    {"id": "robust1", "cat": "robust", "task": "simulated bots stay; k1 goto 1,1",
     "expect": [(1.0, 1.0)]},
    {"id": "robust2", "cat": "robust", "task": "everyone except k1 goto 2,2",
     "expect": [(2.0, 2.0)]},
    {"id": "robust3", "cat": "robust", "task": "stop all bots",
     "expect": None, "empty_ok": True},
]

SCOPE_TOKENS = ("blue_1", "blue_2", "k1", "yahboom", "sim", "all", "both")


def strip_fences(raw):
    if raw.startswith("```"):
        parts = raw.split("```")
        if len(parts) > 1:
            raw = parts[1]
        return raw.strip().lstrip("json\n").strip()
    return raw.strip()


def call_compiler(task_text, model, ollama_url):
    world_lines = ev._build_compiler_world_lines(WORLD_ENTS, START_POS)
    sys_prompt = ev._build_compiler_sys_prompt(world_lines, START_POS)
    payload = {
        "model": model,
        "prompt": f"Task: {task_text}\n\nOutput the JSON waypoint list.",
        "system": sys_prompt,
        "stream": False,
        "keep_alive": "30m",
        "options": {"temperature": PROBE_TEMPERATURE, "num_predict": PROBE_NUM_PREDICT,
                    "num_ctx": PROBE_NUM_CTX, "stop": ["<|im_end|>"]},
    }
    if "glm" in model:
        payload["think"] = False
    start = time.time()
    resp = requests.post(ollama_url, json=payload, timeout=PROBE_TIMEOUT_S)
    raw = resp.json().get("response", "").strip()
    return raw, time.time() - start


def score_one(task, raw):
    res = {
        "parse_ok": False, "schema_ok": False, "n_wp": 0,
        "first_wp_error": None, "seq_errors": None, "ball_dist": None,
        "oob": False, "scope_signal": [], "labels": [],
    }
    cleaned = strip_fences(raw)
    try:
        data = json.loads(cleaned)
        res["parse_ok"] = True
    except Exception:
        return res
    wps = data.get("waypoints", data) if isinstance(data, dict) else data
    if not isinstance(wps, list) or len(wps) == 0:
        res["empty_ok_hit"] = bool(task.get("empty_ok")) and cleaned == ""
        return res
    res["schema_ok"] = True
    res["n_wp"] = len(wps)
    pts = []
    for w in wps:
        try:
            pts.append((float(w["x"]), float(w["y"])))
            res["labels"].append(w.get("label", "?"))
        except (KeyError, TypeError, ValueError):
            pass
    res["oob"] = any(abs(x) > FIELD_X_MAX or abs(y) > FIELD_Y_MAX for x, y in pts)

    extra_keys = [k for k in data if isinstance(data, dict) and k != "waypoints"] if isinstance(data, dict) else []
    blob = json.dumps(data).lower()
    res["scope_signal"] = [t for t in SCOPE_TOKENS if t in blob] + [f"key:{k}" for k in extra_keys]

    if task.get("ball_dist") is True:
        if pts:
            res["ball_dist"] = min(math.hypot(x - BALL_POS[0], y - BALL_POS[1]) for x, y in pts)
    elif task.get("ball_dist"):
        want = task["ball_dist"]
        if pts:
            res["ball_dist"] = min(abs(math.hypot(x - BALL_POS[0], y - BALL_POS[1]) - want) for x, y in pts)
    elif task["expect"]:
        exp = task["expect"]
        if pts:
            res["first_wp_error"] = math.hypot(pts[0][0] - exp[0][0], pts[0][1] - exp[0][1])
        seq_errs = []
        for ex, ey in exp:
            if pts:
                d = min(math.hypot(px - ex, py - ey) for px, py in pts)
                seq_errs.append(round(d, 3))
        res["seq_errors"] = seq_errs
    return res


def aggregate(task, results):
    n = len(results)
    agg = {
        "id": task["id"], "cat": task["cat"], "task": task["task"],
        "parse_rate": sum(1 for r in results if r["parse_ok"]) / n,
        "schema_rate": sum(1 for r in results if r["schema_ok"]) / n,
        "first_wp_error": None, "ball_dist": None, "oob_rate": 0.0,
        "scope_tokens": sorted({t for r in results for t in r["scope_signal"]}),
        "labels": sorted({l for r in results for l in r["labels"]}),
        "n_wp_values": sorted({r["n_wp"] for r in results}),
    }
    errs = [r["first_wp_error"] for r in results if r["first_wp_error"] is not None]
    if errs:
        agg["first_wp_error"] = round(sum(errs) / len(errs), 3)
    bd = [r["ball_dist"] for r in results if r["ball_dist"] is not None]
    if bd:
        agg["ball_dist"] = round(sum(bd) / len(bd), 3)
    agg["oob_rate"] = sum(1 for r in results if r["oob"]) / n
    return agg


def verdict_for(agg):
    if agg["cat"] == "formation":
        return "manual"
    if agg["cat"] == "scope":
        ok = agg["parse_rate"] == 1.0 and agg["first_wp_error"] is not None \
            and agg["first_wp_error"] <= COORD_TOLERANCE
        return "coords_ok_no_scope" if ok else "fail"
    if agg["cat"] == "baseline":
        if agg["id"] == "baseline3":
            return "ok" if agg["ball_dist"] is not None and agg["ball_dist"] <= BALL_APPROACH_TOLERANCE else "fail"
        ok = agg["parse_rate"] == 1.0 and agg["first_wp_error"] is not None \
            and agg["first_wp_error"] <= COORD_TOLERANCE
        return "ok" if ok else "fail"
    if agg["cat"] == "ballrel":
        tol = BALL_APPROACH_TOLERANCE if agg["id"] == "ballrel1" else 0.2
        val = agg["first_wp_error"] if agg["first_wp_error"] is not None else agg["ball_dist"]
        return "ok" if val is not None and val <= tol else "fail"
    if agg["cat"] == "patrol":
        return "ok" if agg["parse_rate"] >= 0.8 and not agg["oob_rate"] else "fail"
    if agg["cat"] == "robust":
        if agg["id"] == "robust3":
            produced = any(v > 0 for v in agg["n_wp_values"])
            return "DANGER_compiled" if produced else "refused_ok"
        return "ok" if agg["parse_rate"] >= 0.8 else "fail"
    return "?"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=5)
    ap.add_argument("--model", default=PROBE_MODEL)
    ap.add_argument("--host", default="http://127.0.0.1:11434")
    ap.add_argument("--out", default=os.path.join(CORE_DIR, "docs", "reference", "benchmarks",
                                                  "a2bot_syntax_probe.md"))
    ap.add_argument("--only", nargs="*", default=None, help="task ids to run (default all)")
    args = ap.parse_args()

    tasks = TASKS if not args.only else [t for t in TASKS if t["id"] in args.only]
    ollama_url = args.host.rstrip("/") + "/api/generate"
    raw_path = os.path.join(CORE_DIR, "src", "logs", f"a2bot_syntax_probe_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl")

    results = []
    with open(raw_path, "w") as rf:
        for task in tasks:
            print(f"=== {task['id']}: \"{task['task']}\" x{args.reps}", flush=True)
            for i in range(args.reps):
                raw, latency = call_compiler(task["task"], args.model, ollama_url)
                s = score_one(task, raw)
                rec = {"id": task["id"], "rep": i, "latency_s": round(latency, 2),
                       "raw": raw, **s}
                results.append(rec)
                rf.write(json.dumps(rec) + "\n")
                rf.flush()
                flag = "OK " if (s["parse_ok"] and s["schema_ok"]) else "ERR"
                err = s["first_wp_error"] if s["first_wp_error"] is not None else s["ball_dist"]
                print(f"  rep{i} {flag} n_wp={s['n_wp']} err={err if err is None else round(err, 3)} "
                      f"lat={latency:.1f}s", flush=True)

    aggs = [aggregate(t, [r for r in results if r["id"] == t["id"]]) for t in tasks]
    for a in aggs:
        a["verdict"] = verdict_for(a)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write("# A2bot Syntax Probe — 7B compiler\n\n")
        f.write(f"- Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"- Model: `{args.model}` · temperature {PROBE_TEMPERATURE} · "
                f"num_predict {PROBE_NUM_PREDICT} · reps {args.reps} per task\n")
        f.write("- Prompt: verbatim `_compile_demo_task` system prompt "
                "(single source of truth via `_build_compiler_sys_prompt`)\n")
        f.write("- World: 2vs0_demo (ball (1,1), blue_1 (0,0), blue_2 (0,1), START (0,0))\n")
        f.write(f"- Raw records: `{os.path.relpath(raw_path, CORE_DIR)}` (gitignored logs/)\n\n")
        f.write("## Summary table\n\n")
        f.write("| id | cat | task | parse | 1st-wp err | ball dist | n_wp | scope tokens | verdict |\n")
        f.write("|---|---|---|---|---|---|---|---|---|\n")
        for a in aggs:
            f.write(f"| {a['id']} | {a['cat']} | `{a['task']}` "
                    f"| {a['parse_rate']:.0%} "
                    f"| {a['first_wp_error'] if a['first_wp_error'] is not None else '—'} "
                    f"| {a['ball_dist'] if a['ball_dist'] is not None else '—'} "
                    f"| {a['n_wp_values']} "
                    f"| {', '.join(a['scope_tokens']) or '—'} "
                    f"| {a['verdict']} |\n")
        f.write("\n## Raw aggregates\n\n```json\n")
        f.write(json.dumps(aggs, indent=2))
        f.write("\n```\n")
    print(f"\nReport: {args.out}\nRaw:    {raw_path}", flush=True)


if __name__ == "__main__":
    main()
