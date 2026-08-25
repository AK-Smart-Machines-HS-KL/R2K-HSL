#!/usr/bin/env python3
"""S1: strategy vocabulary & expression-channel probe.

Text-only (no Gazebo, no production file changes). Phases:
  a1  term definition probe (conversational, manual verdicts)
  a2  emergence probe (bare system prompt, concept states, behavioral checks)
  a3  term-vs-coords instruction probe (bare system prompt + instruction)
  a4  persona probe (aggressive vs neutral header, defensive corpus)
  b   expression-channel sweep (8 variants x 28 situations x reps)
  lint  sample-balance linter on production/B2/B6/minimal sample sets

Usage:
  python3 tools/probe_s1.py lint
  python3 tools/probe_s1.py a1
  python3 tools/probe_s1.py a2 --reps 3
  python3 tools/probe_s1.py a3 --reps 3
  python3 tools/probe_s1.py a4 --reps 3
  python3 tools/probe_s1.py b --reps 3 --variants B0,B1,B1z,B2,B3,B4,B5,B6
"""
import argparse
import json
import math
import os
import sys
import time
import urllib.request
from collections import defaultdict

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.join(TOOLS_DIR, "..")
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "ai_tactics"))
sys.path.insert(0, TOOLS_DIR)

import r2k_evaluator as ev  # noqa: E402
import s1_variants as V  # noqa: E402

OLLAMA_URL = os.getenv("R2K_OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
MODEL = os.getenv("R2K_OLLAMA_MODEL", "qwen2.5:3b")
RESULTS_DIR = os.path.join(BASE_DIR, "results")
CORPUS_PATH = os.path.join(BASE_DIR, "tests", "synthetic_worldstates", "corpus_s1.jsonl")
os.makedirs(RESULTS_DIR, exist_ok=True)

OWN_GOAL = (-4.5, 0.0)


def call_ollama(prompt, system, num_predict=150):
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "keep_alive": "1h",
        "options": {
            "temperature": 0.0,
            "num_predict": num_predict,
            "num_ctx": 4096,
            "stop": ["<|im_end|>", "<|endoftext|>"],
        },
    }
    t0 = time.time()
    body = json.dumps(payload).encode()
    req = urllib.request.Request(OLLAMA_URL, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = json.loads(resp.read())
    lat_ms = int((time.time() - t0) * 1000)
    timings = {k: data.get(k) for k in ("prompt_eval_count", "eval_count")}
    return data.get("response", ""), lat_ms, timings


def load_corpus():
    with open(CORPUS_PATH) as f:
        return [json.loads(l) for l in f if l.strip()]


def build_user_prompt(ents, instruction=None):
    """Replicates the production JSON-mode user prompt (r2k_evaluator.py:868)."""
    min_ents = {k: {"x": round(v["x"], 1), "y": round(v["y"], 1)} for k, v in ents.items()}
    req_keys = "Output ONLY the 'assignments' key."
    instr = f"\n\nTactical instruction: {instruction}" if instruction else ""
    return (json.dumps(min_ents) + instr +
            f"\n\nCRITICAL: Output ONLY valid JSON. {req_keys} End immediately after closing bracket.")


def assemble_variant(vdef):
    """Replicates ev._assemble_prompt for status=playing, mode=3vs3, JSON, no-explain."""
    hdr = vdef["header"].replace("{{EXPLAIN_INSTRUCTION}}", "- Output ONLY the 'assignments' key.")
    parts = [hdr, vdef["rules_core"], vdef["rules_mode"]]
    cleaned = ev._clean_json_samples(vdef["samples"], False)
    parts.append(cleaned)
    return "\n\n".join(p for p in parts if p.strip()).strip()


def parse_assignments(raw):
    data, err = ev.fast_parse(raw)
    if data and "assignments" not in data:
        data = {"assignments": data}
    if data and not isinstance(data.get("assignments", None), dict):
        return None, err
    return data, err


def point_seg_dist(p, a, b):
    ax, ay = a
    bx, by = b
    px, py = p
    dx, dy = bx - ax, by - ay
    seg2 = dx * dx + dy * dy
    if seg2 == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / seg2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def eval_pred(pred, asn, ents):
    t = pred["t"]
    bot = pred.get("bot")
    a = asn.get(bot)
    if a is None or not isinstance(a, dict):
        return False
    action = str(a.get("action", "")).lower()
    role = str(a.get("role", "")).lower()
    if t == "bot_kicks":
        return action == "kick"
    if t == "goalie_kick":
        return role == "goalie" and action == "kick"
    if t == "deep_bot_stays":
        if action == "kick":
            return False
        if "x" in a:
            try:
                return float(a["x"]) <= -3.5
            except (TypeError, ValueError):
                return False
        return True
    if t == "move_target_x_le":
        if action == "kick" or "x" not in a:
            return False
        try:
            return float(a["x"]) <= pred["value"]
        except (TypeError, ValueError):
            return False
    if t == "move_target_x_ge":
        if action == "kick" or "x" not in a:
            return False
        try:
            return float(a["x"]) >= pred["value"]
        except (TypeError, ValueError):
            return False
    if t == "no_kick_target_behind":
        if action != "kick":
            return False
        if "target_x" not in a:
            return True  # plain kick aims at opponent goal (forward)
        try:
            return float(a["target_x"]) >= float(ents[bot]["x"])
        except (TypeError, ValueError):
            return False
    if t == "kick_target_x_ge":
        if action != "kick":
            return False
        if "target_x" in a:
            try:
                return float(a["target_x"]) >= pred["value"]
            except (TypeError, ValueError):
                return False
        return bool(pred.get("plain_ok"))
    if t == "target_in_zone":
        if action == "kick" or "x" not in a:
            return False
        try:
            x, y = float(a["x"]), float(a.get("y", 0.0))
        except (TypeError, ValueError):
            return False
        if "x_ge" in pred and x < pred["x_ge"]:
            return False
        if "x_le" in pred and x > pred["x_le"]:
            return False
        if "y_abs_ge" in pred and abs(y) < pred["y_abs_ge"]:
            return False
        if "y_abs_le" in pred and abs(y) > pred["y_abs_le"]:
            return False
        return True
    if t == "between_ball_and_own_goal":
        if action == "kick" or "x" not in a:
            return False
        b = ents.get("soccer_ball", {})
        try:
            p = (float(a["x"]), float(a.get("y", 0.0)))
        except (TypeError, ValueError):
            return False
        return point_seg_dist(p, (b.get("x", 0), b.get("y", 0)), OWN_GOAL) <= pred["max_dist"]
    if t == "pass_to":
        if action != "kick" or "target_x" not in a:
            return False
        try:
            return math.hypot(float(a["target_x"]) - pred["near"][0],
                              float(a["target_y"]) - pred["near"][1]) <= pred["radius"]
        except (TypeError, ValueError):
            return False
    if t == "move_near":
        if action == "kick" or "x" not in a:
            return False
        try:
            return math.hypot(float(a["x"]) - pred["expect"][0],
                              float(a.get("y", 0.0)) - pred["expect"][1]) <= pred["radius"]
        except (TypeError, ValueError):
            return False
    if t == "kick_target_near":
        if action != "kick" or "target_x" not in a:
            return False
        try:
            return math.hypot(float(a["target_x"]) - pred["expect"][0],
                              float(a["target_y"]) - pred["expect"][1]) <= pred["radius"]
        except (TypeError, ValueError):
            return False
    if t == "kick_forward":
        if action != "kick":
            return False
        if "target_x" not in a:
            return True
        try:
            return float(a["target_x"]) >= pred["min_target_x"]
        except (TypeError, ValueError):
            return False
    return False


def eval_situation(item, asn):
    """Evaluate all expected predicates. Returns dict pred-index -> bool."""
    return [eval_pred(p, asn, item["entities"]) for p in item.get("expected", [])]


def goalie_kick_count(asn):
    return sum(1 for b, a in asn.items()
               if isinstance(a, dict) and str(a.get("role", "")).lower() == "goalie"
               and str(a.get("action", "")).lower() == "kick")


def forward_bias(asn):
    xs = [float(a["x"]) for a in asn.values()
          if isinstance(a, dict) and str(a.get("role", "")).lower() != "goalie" and "x" in a]
    return sum(xs) / len(xs) if xs else None


def distractor():
    call_ollama("What is 17 * 23? Answer with the number only.", "You are a calculator.", 20)


def pct(a, b):
    return f"{100 * a / b:.0f}%" if b else "-"


# ====================================================================
# Phase runners
# ====================================================================

def run_a1():
    records = []
    for term in V.A1_TERMS:
        prompt = V.A1_PROMPT.format(term=term)
        raw, lat, tim = call_ollama(prompt, "You are a concise soccer rules expert.", 400)
        records.append({"phase": "a1", "term": term, "latency_ms": lat, "response": raw})
        print(f"\n=== {term} ({lat}ms) ===\n{raw.strip()[:600]}")
    path = os.path.join(RESULTS_DIR, "probe_s1_a1_raw.jsonl")
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    print(f"\nSaved {len(records)} records -> {path}")
    print("Verdicts: classify each response manually (known/partial/no).")


def run_a2(reps):
    corpus = {c["label"]: c for c in load_corpus()}
    a2_labels = ["lm_01", "sa_01", "sp_01", "tb_01", "rb_01", "ws_01", "gs_01", "pc_01", "mf_01", "ga_01"]
    records = []
    distractor()
    first = True
    for rep in range(reps):
        for label in a2_labels:
            item = corpus[label]
            raw, lat, tim = call_ollama(build_user_prompt(item["entities"]), V.BARE_SYS)
            if first:
                first = False
                continue  # discard first call (fresh-prefill KV-cache control)
            data, err = parse_assignments(raw)
            rec = {"phase": "a2", "label": label, "category": item["category"], "rep": rep,
                   "latency_ms": lat, "parse_ok": bool(data), "parse_code": err if data is None else 0,
                   "raw_preview": raw[:250]}
            if data:
                asn = data.get("assignments", {})
                preds = eval_situation(item, asn)
                rec["preds"] = preds
                rec["goalie_kicks"] = goalie_kick_count(asn)
                rec["assignments"] = asn
            records.append(rec)
    path = os.path.join(RESULTS_DIR, "probe_s1_a2_raw.jsonl")
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    # report
    print(f"\n=== A2 emergence (bare prompt, no rules/samples) — {len(records)} calls ===")
    ok = [r for r in records if r["parse_ok"]]
    print(f"Parse OK: {pct(len(ok), len(records))}")
    by_cat = defaultdict(lambda: [0, 0])
    for r in ok:
        for p in r.get("preds", []):
            by_cat[r["category"]][1] += 1
            by_cat[r["category"]][0] += 1 if p else 0
    print(f"{'category':<20} {'pred pass':>12}")
    for c, (a, b) in sorted(by_cat.items()):
        print(f"{c:<20} {pct(a, b):>12}")
    lats = sorted(r["latency_ms"] for r in records)
    print(f"Latency p50: {lats[len(lats)//2]}ms")
    print(f"Raw: {path}")


def run_a3(reps):
    corpus = {c["label"]: c for c in load_corpus()}
    records = []
    distractor()
    first = True
    for rep in range(reps):
        for case in V.A3_CASES:
            item = corpus[case["label"]]
            for phrasing in ("term", "coord"):
                instr = case[phrasing]
                raw, lat, tim = call_ollama(build_user_prompt(item["entities"], instr), V.BARE_SYS)
                if first:
                    first = False
                    continue
                data, err = parse_assignments(raw)
                rec = {"phase": "a3", "label": case["label"], "phrasing": phrasing, "rep": rep,
                       "latency_ms": lat, "parse_ok": bool(data),
                       "parse_code": err if data is None else 0, "raw_preview": raw[:250]}
                if data:
                    asn = data.get("assignments", {})
                    rec["match"] = eval_pred({**case["check"], "bot": case["bot"]}, asn, item["entities"])
                    rec["assignments"] = asn
                records.append(rec)
    path = os.path.join(RESULTS_DIR, "probe_s1_a3_raw.jsonl")
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    print(f"\n=== A3 term vs coords — {len(records)} calls ===")
    ok = [r for r in records if r["parse_ok"]]
    print(f"Parse OK: {pct(len(ok), len(records))}")
    by = defaultdict(lambda: [0, 0])
    for r in ok:
        by[(r["label"], r["phrasing"])][1] += 1
        by[(r["label"], r["phrasing"])][0] += 1 if r.get("match") else 0
    print(f"{'label':<8} {'term':>6} {'coord':>6}")
    for label in sorted({l for (l, _) in by}):
        t_a, t_b = by.get((label, "term"), [0, 0])
        c_a, c_b = by.get((label, "coord"), [0, 0])
        print(f"{label:<8} {pct(t_a, t_b):>6} {pct(c_a, c_b):>6}")
    print(f"Raw: {path}")


def run_a4(reps):
    corpus = {c["label"]: c for c in load_corpus()}
    a4_labels = ["lm_01", "lm_02", "lm_03", "sa_01", "sa_02", "sa_03", "gs_01", "gs_02", "gs_03"]
    variants = V.get_variants()
    b0 = variants["B0"]
    headers = {"aggressive": b0["header"], "neutral": V.HEADER_NEUTRAL_PERSONA}
    records = []
    for hdr_name, hdr in headers.items():
        vdef = {"header": hdr, "rules_core": b0["rules_core"],
                "rules_mode": b0["rules_mode"], "samples": b0["samples"]}
        sys_prompt = assemble_variant(vdef)
        distractor()
        first = True
        for rep in range(reps):
            for label in a4_labels:
                item = corpus[label]
                raw, lat, tim = call_ollama(build_user_prompt(item["entities"]), sys_prompt)
                if first:
                    first = False
                    continue
                data, err = parse_assignments(raw)
                rec = {"phase": "a4", "header": hdr_name, "label": label, "rep": rep,
                       "latency_ms": lat, "parse_ok": bool(data)}
                if data:
                    asn = data.get("assignments", {})
                    rec["preds"] = eval_situation(item, asn)
                    rec["forward_bias"] = forward_bias(asn)
                    rec["assignments"] = asn
                records.append(rec)
    path = os.path.join(RESULTS_DIR, "probe_s1_a4_raw.jsonl")
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    print(f"\n=== A4 persona (aggressive vs neutral header) ===")
    for hdr_name in headers:
        rs = [r for r in records if r["header"] == hdr_name and r["parse_ok"]]
        by_cat = defaultdict(lambda: [0, 0])
        fbs = []
        for r in rs:
            by_cat[corpus[r["label"]]["category"]][1] += len(r.get("preds", []))
            by_cat[corpus[r["label"]]["category"]][0] += sum(r.get("preds", []))
            if r.get("forward_bias") is not None:
                fbs.append(r["forward_bias"])
        print(f"\n--- {hdr_name} (n={len(rs)}) ---")
        for c, (a, b) in sorted(by_cat.items()):
            print(f"  {c:<15} pred pass {pct(a, b)}")
        if fbs:
            print(f"  forward bias (mean non-goalie target_x): {sum(fbs)/len(fbs):.2f}")
    print(f"Raw: {path}")


def run_b(reps, variant_keys):
    corpus = load_corpus()
    import sp_variants as SP
    import win_variants as WIN
    import w7w8_variants as W78V
    variants = {**V.get_variants(), **SP.get_sp_variants(), **WIN.get_win_variants(),
                **W78V.get_w7w8_variants()}
    path = os.path.join(RESULTS_DIR, "probe_s1_b_raw.jsonl")
    # Merge with existing records (dedup by variant) so partial runs append
    records = []
    if os.path.exists(path):
        with open(path) as f:
            for l in f:
                if l.strip():
                    r = json.loads(l)
                    if r.get("variant") not in variant_keys:
                        records.append(r)
    for vkey in variant_keys:
        vdef = variants[vkey]
        sys_prompt = assemble_variant(vdef)
        n_sys_tokens = len(sys_prompt) // 4  # rough token estimate
        distractor()
        first = True
        for rep in range(reps):
            for item in corpus:
                raw, lat, tim = call_ollama(build_user_prompt(item["entities"]), sys_prompt)
                if first:
                    first = False
                    continue
                data, err = parse_assignments(raw)
                rec = {"phase": "b", "variant": vkey, "label": item["label"],
                       "category": item["category"], "rep": rep,
                       "latency_ms": lat, "prompt_eval_count": tim.get("prompt_eval_count"),
                       "parse_ok": bool(data), "parse_code": err if data is None else 0}
                if data:
                    asn = data.get("assignments", {})
                    rec["preds"] = eval_situation(item, asn)
                    rec["goalie_kicks"] = goalie_kick_count(asn)
                    rec["forward_bias"] = forward_bias(asn)
                    rec["assignments"] = asn
                    # W7/W8 metric: is the LLM's kicker the geometrically
                    # closest blue bot? (goalie exception: goalie closest +
                    # goalie kicks also counts in field_closest)
                    kick_bots = [b for b, a in asn.items()
                                 if isinstance(a, dict) and str(a.get("action", "")).lower() == "kick"]
                    if kick_bots:
                        ents = item["entities"]
                        ball = ents.get("soccer_ball", {})
                        dists = {b: math.hypot(ents[b]["x"] - ball["x"], ents[b]["y"] - ball["y"])
                                 for b in ("blue_1", "blue_2", "blue_3") if b in ents}
                        if dists:
                            closest = min(dists, key=dists.get)
                            rec["closest_kick"] = (kick_bots[0] == closest)
                            field_d = {b: d for b, d in dists.items() if b != "blue_1"}
                            field_closest = min(field_d, key=field_d.get) if field_d else None
                            rec["field_closest_kick"] = (
                                kick_bots[0] == field_closest
                                or (kick_bots[0] == "blue_1" and closest == "blue_1"))
                records.append(rec)
        n = sum(1 for r in records if r["variant"] == vkey)
        print(f"[{vkey}] done ({n} records)")
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    report_b(records, corpus, variants, variant_keys)
    print(f"Raw: {path}")


def report_b(records, corpus, variants, variant_keys):
    print(f"\n{'='*80}\n=== B expression-channel sweep — {len(records)} calls ===")
    cat_of = {c["label"]: c["category"] for c in corpus}
    print(f"\n{'variant':<5} {'desc':<55} {'parse':>6} {'lat_p50':>8} {'pec':>6} {'ff_gk':>6} {'fwdb':>6}")
    base_pec = None
    for vkey in variant_keys:
        vr = [r for r in records if r["variant"] == vkey]
        ok = [r for r in vr if r["parse_ok"]]
        lats = sorted(r["latency_ms"] for r in vr)
        pecs = [r["prompt_eval_count"] for r in vr if r.get("prompt_eval_count")]
        pec = int(sum(pecs) / len(pecs)) if pecs else 0
        if vkey == "B0" and pec:
            base_pec = pec
        ff = [r for r in ok if cat_of[r["label"]] != "goalie_kick_control" and r.get("goalie_kicks", 0) > 0]
        fbs = [r["forward_bias"] for r in ok if r.get("forward_bias") is not None]
        desc = variants[vkey]["desc"][:53]
        print(f"{vkey:<5} {desc:<55} {pct(len(ok), len(vr)):>6} {lats[len(lats)//2]:>7}ms {pec:>6} "
              f"{pct(len(ff), len(ok)):>6} {sum(fbs)/len(fbs):>6.2f}")
    print("\nPer-category predicate pass rate (all predicates pooled):")
    cats = sorted({cat_of[r["label"]] for r in records})
    header = f"{'variant':<5}" + "".join(f"{c[:9]:>11}" for c in cats)
    print(header)
    for vkey in variant_keys:
        ok = [r for r in records if r["variant"] == vkey and r["parse_ok"]]
        row = f"{vkey:<5}"
        for c in cats:
            rs = [r for r in ok if cat_of[r["label"]] == c]
            tot = sum(len(r.get("preds", [])) for r in rs)
            passed = sum(sum(r.get("preds", [])) for r in rs)
            row += f"{pct(passed, tot):>11}"
        print(row)
    # W7/W8 metric: closest-bot-kick rate (does the LLM assign the Kick to
    # the geometrically closest blue bot?)
    ck_any = [r for r in records if r.get("closest_kick") is not None]
    if ck_any:
        print("\nClosest-bot-kick rate (kicker == geometrically closest blue bot):")
        print(f"{'variant':<6}{'strict(all 3)':>14}{'field(b2/b3)':>13}   n")
        for vkey in variant_keys:
            ok = [r for r in records if r["variant"] == vkey and r.get("closest_kick") is not None]
            if not ok:
                continue
            strict = sum(1 for r in ok if r["closest_kick"])
            field = sum(1 for r in ok if r.get("field_closest_kick"))
            print(f"{vkey:<6}{100*strict/len(ok):>13.0f}%{100*field/len(ok):>12.0f}%   {len(ok)}")
    # Flip rate (temp-0 nondeterminism): situations where preds differ across reps
    print("\nFlip rate (situations with differing predicate outcomes across reps):")
    for vkey in variant_keys:
        ok = [r for r in records if r["variant"] == vkey and r["parse_ok"]]
        by_label = defaultdict(list)
        for r in ok:
            by_label[r["label"]].append(tuple(r.get("preds", [])))
        flips = sum(1 for v in by_label.values() if len(set(v)) > 1)
        print(f"  {vkey:<5} {flips}/{len(by_label)} situations flip")


def run_lint():
    variants = V.get_variants()
    sets = {
        "production_V1": variants["B0"]["samples"],
        "B2_replaced": variants["B2"]["samples"],
        "B6_grown": variants["B6"]["samples"],
        "B1z_minimal": variants["B1z"]["samples"],
        "B9_reversed_pass": variants["B9"]["samples"],
        "B9g_goalie_anchor": variants["B9g"]["samples"],
        "B10_both_fixes": variants["B10"]["samples"],
        "B11_steal_isolation": variants["B11"]["samples"],
        "B12_synthesis": variants["B12"]["samples"],
    }
    all_viol = {}
    for name, text in sets.items():
        rep, viol = V.lint_samples(text, name)
        all_viol[name] = viol
        print(f"\n=== {name} (n={rep['n_examples']}) ===")
        print(f"  kickers:        {rep['kickers']}  (goalie-kick examples: {rep['goalie_kicks']})")
        print(f"  roles:          {rep['roles']}")
        print(f"  ball Y:         {rep['ball_y_pos']} pos / {rep['ball_y_neg']} neg")
        print(f"  dangerous red:  {rep['danger_red']}")
        print(f"  entity counts:  {rep['entity_counts']}")
        if viol:
            print(f"  VIOLATIONS: {viol}")
        else:
            print("  no violations")
    return all_viol


# ====================================================================
# SP phase: sequence probe (drift + freeze) — spinning-fix arms
# ====================================================================

def _seq_base_situations():
    """10 base situations for the sequence probe: ball positions spread
    over the field, 3 blue bots in plausible spots, 3 red bots."""
    bases = [
        ("sq_01", {"x": 0.0, "y": 0.0}, {"blue_1": (-4.0, 0.0), "blue_2": (-1.0, 0.5), "blue_3": (-2.0, -1.0)}),
        ("sq_02", {"x": 1.5, "y": 0.8}, {"blue_1": (-4.0, 0.1), "blue_2": (1.0, 0.9), "blue_3": (-1.5, -0.5)}),
        ("sq_03", {"x": -2.0, "y": -0.6}, {"blue_1": (-4.0, -0.2), "blue_2": (-2.5, -0.5), "blue_3": (0.0, 1.0)}),
        ("sq_04", {"x": 3.0, "y": 1.2}, {"blue_1": (-4.0, 0.2), "blue_2": (2.5, 1.0), "blue_3": (-1.0, 0.0)}),
        ("sq_05", {"x": -3.2, "y": 1.0}, {"blue_1": (-4.0, 0.5), "blue_2": (-1.0, 0.0), "blue_3": (0.5, -1.5)}),
        ("sq_06", {"x": 0.5, "y": -1.8}, {"blue_1": (-4.0, -0.3), "blue_2": (0.0, -1.5), "blue_3": (-2.0, 0.5)}),
        ("sq_07", {"x": 2.2, "y": -0.4}, {"blue_1": (-4.0, 0.0), "blue_2": (2.0, -0.3), "blue_3": (-0.5, 1.2)}),
        ("sq_08", {"x": -1.2, "y": 2.0}, {"blue_1": (-4.0, 0.4), "blue_2": (-1.5, 1.8), "blue_3": (1.0, -0.5)}),
        ("sq_09", {"x": 3.8, "y": -1.0}, {"blue_1": (-4.0, -0.1), "blue_2": (3.5, -0.8), "blue_3": (1.0, 0.5)}),
        ("sq_10", {"x": -0.5, "y": 0.3}, {"blue_1": (-4.0, 0.0), "blue_2": (-0.8, 0.4), "blue_3": (1.5, -1.0)}),
    ]
    out = []
    for label, ball, blues in bases:
        ents = {"soccer_ball": dict(ball)}
        for b, (x, y) in blues.items():
            ents[b] = {"x": x, "y": y}
        # static red bots (mirrored plausible formation)
        ents["red_1"] = {"x": round(-ball["x"] * 0.5 + 2.0, 1), "y": round(-ball["y"] * 0.3, 1)}
        ents["red_2"] = {"x": 3.0, "y": 1.5}
        ents["red_3"] = {"x": 2.5, "y": -1.5}
        out.append((label, ents))
    return out


def _bot_step(ents, targets, step_m=0.3):
    """Move each blue bot `step_m` toward its target (or keep on Hold/Kick)."""
    new = {k: dict(v) for k, v in ents.items()}
    for bot, a in targets.items():
        if not isinstance(a, dict):
            continue
        action = str(a.get("action", "")).lower()
        if action != "move":
            continue  # Hold: stays; Kick: no target motion modeled
        try:
            tx, ty = float(a["x"]), float(a["y"])
        except (KeyError, TypeError, ValueError):
            continue
        bx, by = ents[bot]["x"], ents[bot]["y"]
        dx, dy = tx - bx, ty - by
        d = math.hypot(dx, dy)
        if d < 1e-6:
            continue
        move = min(step_m, d)
        new[bot] = {"x": round(bx + dx / d * move, 2), "y": round(by + dy / d * move, 2)}
    return new


def _targets_of(asn):
    """Normalize parsed assignments to {bot: {action, x, y, ...}}."""
    out = {}
    for bot, a in (asn or {}).items():
        if isinstance(a, dict):
            out[bot] = a
    return out


def _hold_rate(records):
    n = 0
    holds = 0
    for r in records:
        for a in (r.get("targets") or {}).values():
            n += 1
            if str(a.get("action", "")).lower() == "hold":
                holds += 1
    return holds / n if n else 0.0


def run_sp(variant_keys, steps=5, reps=1, out_name="probe_sp_seq_raw.jsonl"):
    """Sequence probe: drift + freeze tests per variant.

    Drift test: ball moves 0.2m/state toward +X; bots step toward their
    previous targets. Measures per-step target displacement (non-kicker
    Move bots) and heading swing (angle between successive motion vectors).
    Freeze test: ball static, bots AT their previous targets. Measures
    target reproduction (identical targets => content-hash skip live).
    """
    import sp_variants as SP
    import win_variants as WIN
    variants = {**V.get_variants(), **SP.get_sp_variants(), **WIN.get_win_variants()}
    if "SP3" in variant_keys and "SP3" not in variants:
        raise SystemExit("SP3 must be built after round 1 via get_sp3_variants()")
    records = []
    results = {}
    for vkey in variant_keys:
        vdef = variants[vkey]
        sys_prompt = assemble_variant(vdef)
        drift_recs, freeze_recs = [], []
        distractor()
        first = True
        for rep in range(reps):
            for label, ents0 in _seq_base_situations():
                # ---- drift test ----
                ents = {k: dict(v) for k, v in ents0.items()}
                prev_targets = None
                prev_motion = {}
                for step in range(steps):
                    raw, lat, tim = call_ollama(build_user_prompt(ents), sys_prompt)
                    if first:
                        first = False
                        # re-do this call (discard) — fall through using its parse anyway
                    data, err = parse_assignments(raw)
                    tgts = _targets_of(data.get("assignments")) if data else {}
                    rec = {"variant": vkey, "test": "drift", "label": label,
                           "rep": rep, "step": step, "latency_ms": lat,
                           "parse_ok": bool(data), "targets": tgts}
                    if data:
                        # metrics vs previous targets
                        disp, swings = [], []
                        for bot, a in tgts.items():
                            if str(a.get("action", "")).lower() != "move":
                                continue
                            pa = (prev_targets or {}).get(bot)
                            if pa and str(pa.get("action", "")).lower() == "move":
                                d = math.hypot(float(a["x"]) - float(pa["x"]),
                                               float(a["y"]) - float(pa["y"]))
                                disp.append(d)
                                # heading swing: angle between target-step vectors
                                v1 = (float(pa["x"]) - ents[bot]["x"], float(pa["y"]) - ents[bot]["y"])
                                v2 = (float(a["x"]) - ents[bot]["x"], float(a["y"]) - ents[bot]["y"])
                                n1 = math.hypot(*v1); n2 = math.hypot(*v2)
                                if n1 > 1e-6 and n2 > 1e-6:
                                    cosang = max(-1.0, min(1.0, (v1[0]*v2[0]+v1[1]*v2[1])/(n1*n2)))
                                    swings.append(math.degrees(math.acos(cosang)))
                        if disp:
                            rec["target_disp"] = sum(disp) / len(disp)
                        if swings:
                            rec["heading_swing"] = sum(swings) / len(swings)
                    drift_recs.append(rec)
                    prev_targets = tgts
                    # advance world: ball drifts +0.2m X, bots step toward targets
                    ball = ents["soccer_ball"]
                    ents = {k: dict(v) for k, v in ents.items()}
                    ents["soccer_ball"] = {"x": round(min(4.4, ball["x"] + 0.2), 2),
                                           "y": ball["y"]}
                    ents = _bot_step(ents, tgts)
                # ---- freeze test ----
                ents = {k: dict(v) for k, v in ents0.items()}
                prev_targets = None
                for step in range(steps):
                    raw, lat, tim = call_ollama(build_user_prompt(ents), sys_prompt)
                    data, err = parse_assignments(raw)
                    tgts = _targets_of(data.get("assignments")) if data else {}
                    rec = {"variant": vkey, "test": "freeze", "label": label,
                           "rep": rep, "step": step, "latency_ms": lat,
                           "parse_ok": bool(data), "targets": tgts}
                    if data and prev_targets is not None:
                        moved = []
                        for bot, a in tgts.items():
                            if str(a.get("action", "")).lower() != "move":
                                continue
                            pa = prev_targets.get(bot)
                            if pa and str(pa.get("action", "")).lower() == "move":
                                moved.append(math.hypot(float(a["x"]) - float(pa["x"]),
                                                        float(a["y"]) - float(pa["y"])))
                        if moved:
                            rec["freeze_drift"] = sum(moved) / len(moved)
                        else:
                            rec["freeze_drift"] = 0.0
                    elif data:
                        rec["freeze_drift"] = 0.0
                    freeze_recs.append(rec)
                    prev_targets = tgts
                    # bots move fully onto their targets (settle)
                    ents = _bot_step(ents, tgts, step_m=99.0)
        results[vkey] = (drift_recs, freeze_recs)
        records.extend(drift_recs + freeze_recs)
        print(f"[{vkey}] done ({len(drift_recs)} drift + {len(freeze_recs)} freeze records)")
    path = os.path.join(RESULTS_DIR, out_name)
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    report_sp(results, variant_keys)
    print(f"Raw: {path}")


def report_sp(results, variant_keys):
    print(f"\n{'='*84}\n=== SP sequence probe ===")
    print(f"\n{'variant':<6} {'desc':<44} {'driftDisp':>9} {'headSwing':>9} {'freezeDr':>9} {'holdRate':>8}")
    for vkey in variant_keys:
        import sp_variants as SP
        import win_variants as WIN
        variants = {**V.get_variants(), **SP.get_sp_variants(), **WIN.get_win_variants()}
        drift, freeze = results[vkey]
        d_ok = [r for r in drift if r["parse_ok"]]
        f_ok = [r for r in freeze if r["parse_ok"]]
        disp = [r["target_disp"] for r in d_ok if "target_disp" in r]
        swing = [r["heading_swing"] for r in d_ok if "heading_swing" in r]
        fdrift = [r["freeze_drift"] for r in f_ok if "freeze_drift" in r]
        hr = _hold_rate(drift + freeze)
        desc = variants[vkey]["desc"][:42]
        print(f"{vkey:<6} {desc:<44} "
              f"{(sum(disp)/len(disp) if disp else 0):>8.2f}m "
              f"{(sum(swing)/len(swing) if swing else 0):>8.1f}° "
              f"{(sum(fdrift)/len(fdrift) if fdrift else 0):>8.2f}m "
              f"{100*hr:>7.0f}%")
    print("\nPass criteria (vs SP0): driftDisp ≤50% · headSwing ≥50% reduction · freezeDrift ≈0 · holdRate sane")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("phase", choices=["a1", "a2", "a3", "a4", "b", "lint", "sp"])
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--variants", default="B0,B1,B1z,B2,B3,B4,B5,B6")
    ap.add_argument("--steps", type=int, default=5)
    ap.add_argument("--out", default=None,
                    help="output filename for sp phase (default: probe_sp_seq_raw.jsonl)")
    args = ap.parse_args()
    if args.phase == "a1":
        run_a1()
    elif args.phase == "a2":
        run_a2(args.reps)
    elif args.phase == "a3":
        run_a3(args.reps)
    elif args.phase == "a4":
        run_a4(args.reps)
    elif args.phase == "b":
        run_b(args.reps, [v.strip() for v in args.variants.split(",") if v.strip()])
    elif args.phase == "lint":
        run_lint()
    elif args.phase == "sp":
        run_sp([v.strip() for v in args.variants.split(",") if v.strip()],
               steps=args.steps, reps=args.reps,
               out_name=args.out or "probe_sp_seq_raw.jsonl")


if __name__ == "__main__":
    main()
