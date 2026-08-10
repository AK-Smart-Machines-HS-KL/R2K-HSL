#!/usr/bin/env python3
"""Phase F probe instrument (C3): structure/content sweep over synthetic world-states.

Complements tools/i3_battery.py (dual TEXT/JSON encoding, fixed fragment dir)
with config-driven prompt structure sweeps:

  - config registry: F0..F3 (structure) + F4 content variants
  - interwoven sample support (ANALYSIS/RULE/ORACLE/ASSISTANT blocks inside
    samples instead of separate global rules/samples)
  - the 9 Phase-F2 text-analysis metrics: parse_success, vocab_compliance,
    rule_following, analysis_quality, oracle_quality, contradiction_score,
    role_coverage, continue_accuracy (determinism across repeats), latency_ms
  - corpus: 'battery' (i3_battery situations) or a JSONL corpus file
    (tests/synthetic_worldstates/corpus.jsonl, built by build_corpus.py)
  - output: results/probe_<tag>_raw.jsonl + results/probe_<tag>_report.md

Usage:
  python3 tools/llm_probe.py --config F0,F1 --repeat 3 --tag f3_structure
  python3 tools/llm_probe.py --config F0 --corpus tests/synthetic_worldstates/corpus.jsonl --tag f3_full
  python3 tools/llm_probe.py --config F3 --model llama3.2:3b --tag 4b_regression
  python3 tools/llm_probe.py --config F4_s1 --content sample_count=1 --tag f4_samples
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__)) + "/.."
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, BASE_DIR + "/ai_tactics")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import r2k_evaluator as ev  # noqa: E402
from i3_battery import (SITUATIONS, call_ollama, parse_output,  # noqa: E402
                        score_result)

RESULTS_DIR = os.path.join(BASE_DIR, "results")
FRAG_DIR = os.path.join(BASE_DIR, "strategy", "fragments")
EXTRA_FRAG_DIR = ""

FIELD_X = 4.5
FIELD_Y = 3.0

ALLOWED_ACTIONS = {"Move", "Kick", "Hold", "Cover"}
ALLOWED_ROLES = {"goalie", "attacker", "defender"}
SOCCER_TERMS = ("ball", "red_", "blue_", "goal", "wing", "center", "pass",
                "defend", "attack", "kick", "cover", "midfield", "line",
                "wing", "zone", "mark", "clear")
CONTRADICTION_PATTERNS = (
    "but also", "while also", "however", "at the same time",
    "on the other hand", "although", "despite", "even though",
    "meanwhile", "yet ", "though", "but not necessarily",
)

MINIMAL_USER_HEADER = (
    "Output exactly one line per blue bot in the INPUT above: "
    "'blue_N move to (X, Y)', 'blue_N kick', or 'blue_N cover the goal line "
    "at (-4.0, Y)'. Never use the same bot twice."
)

EXPLAIN_ORACLE_HEADER = (
    "Start with 'ORACLE: <prediction>', then one line per blue bot."
)
EXPLAIN_ANALYSIS_HEADER = (
    "Start with 'ANALYSIS: <assessment>', then one line per blue bot."
)

# KICK/SPLIT/PASS rules extracted from TEXT_OUTPUT_HEADER (K3 winner) —
# used by the explain-k3h variant to test whether the K3 rules rescue
# kick selection in explain mode.
def _k3_rules_section():
    hdr = ev.TEXT_OUTPUT_HEADER
    idx = hdr.find("\nKICK RULE:")
    return hdr[idx:].strip() if idx >= 0 else ""

CONFIGS = {
    # --- F3 structure sweep -------------------------------------------
    "F0": {
        "label": "F0 baseline: global rules + separate samples",
        "header": "header.txt",
        "rules_core": "rules_core_text.txt",
        "rules_mode": "rules_3vs3.txt",
        "samples_mode": "samples_3vs3.txt",
        "samples_format": "json_blocks",
        "user_header": "full",
    },
    "F1": {
        "label": "F1: minimal global rules + interwoven samples",
        "header": "header.txt",
        "rules_core": "rules_core_min.txt",
        "rules_mode": None,
        "samples_mode": "samples_interwoven_3vs3.txt",
        "samples_format": "text",
        "user_header": "explain_full",
    },
    "F2": {
        "label": "F2 extreme: no global text, only interwoven samples",
        "header": None,
        "rules_core": None,
        "rules_mode": None,
        "samples_mode": "samples_interwoven_3vs3.txt",
        "samples_format": "text",
        "user_header": "explain_full",
    },
    "F3": {
        "label": "F3: axioms-only global + interwoven samples (analysis+oracle)",
        "header": "header.txt",
        "rules_core": "rules_core.txt",
        "rules_mode": None,
        "samples_mode": "samples_interwoven_3vs3.txt",
        "samples_format": "text",
        "user_header": "explain_full",
    },
    # --- F4 content variants (one dimension at a time on F0) ------------
    "F4_s1": {
        "label": "F4: F0 structure, 1 sample",
        "header": "header.txt",
        "rules_core": "rules_core_text.txt",
        "rules_mode": "rules_3vs3.txt",
        "samples_mode": "samples_3vs3_1.txt",
        "samples_format": "json_blocks",
        "user_header": "full",
    },
    "F4_s6": {
        "label": "F4: F0 structure, 6 samples",
        "header": "header.txt",
        "rules_core": "rules_core_text.txt",
        "rules_mode": "rules_3vs3.txt",
        "samples_mode": "samples_3vs3_6.txt",
        "samples_format": "json_blocks",
        "user_header": "full",
    },
    "F4_nok3h": {
        "label": "F4: F0 structure, no K3 rules in header",
        "header": "header.txt",
        "rules_core": "rules_core_text.txt",
        "rules_mode": "rules_3vs3.txt",
        "samples_mode": "samples_3vs3.txt",
        "samples_format": "json_blocks",
        "user_header": "full_nok3h",
    },
    "F4_explain": {
        "label": "F4: F0 structure, explain header (ANALYSIS/ORACLE)",
        "header": "header.txt",
        "rules_core": "rules_core_text.txt",
        "rules_mode": "rules_3vs3.txt",
        "samples_mode": "samples_3vs3.txt",
        "samples_format": "json_blocks",
        "user_header": "explain_full",
    },
}


def read_fragment(name):
    if EXTRA_FRAG_DIR:
        p = os.path.join(EXTRA_FRAG_DIR, name)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                return f.read()
    path = os.path.join(FRAG_DIR, name)
    if not name or not os.path.exists(path):
        return ""
    with open(path, encoding="utf-8") as f:
        return f.read()


def strip_sample_lines(content, markers):
    """Remove lines starting with a marker (e.g. 'ANALYSIS:', 'ORACLE:')
    from interwoven sample text, keeping the rest."""
    out = []
    for line in content.splitlines():
        if any(line.strip().startswith(m + ":") for m in markers):
            continue
        out.append(line)
    return "\n".join(out)


def assemble_system_prompt(cfg, status):
    """Config-driven system prompt. Mirrors r2k_evaluator._assemble_prompt
    for F0 (incl. additive game-phase fragments); structure variants use
    exactly the fragments listed in the config."""
    parts = []
    if cfg.get("header"):
        hdr = read_fragment(cfg["header"]).replace("{{EXPLAIN_INSTRUCTION}}", "")
        if hdr.strip():
            parts.append(hdr)
    if cfg.get("rules_core"):
        rc = read_fragment(cfg["rules_core"])
        if rc.strip():
            parts.append(rc)
    if cfg.get("rules_mode"):
        rm = read_fragment(cfg["rules_mode"])
        if rm.strip():
            parts.append(rm)
    samples = read_fragment(cfg.get("samples_mode") or "")
    if samples.strip():
        if cfg.get("samples_format") == "json_blocks":
            cleaned = ev._clean_text_samples(
                samples, is_explain_style(cfg.get("user_header", "full")))
        else:
            cleaned = samples
        for m in cfg.get("strip", []):
            cleaned = strip_sample_lines(cleaned, m)
        if cleaned.strip():
            parts.append(cleaned)
    return "\n\n".join(p for p in parts if p.strip()).strip()


def build_user_prompt(ents, match_state, user_header):
    world = ev._build_text_world(ents, match_state)
    blue_names = ", ".join(sorted(k for k in ents if k.startswith("blue")))
    if user_header == "full":
        hdr = ev.TEXT_OUTPUT_HEADER
    elif user_header == "full_nok3h":
        hdr = ev.TEXT_OUTPUT_HEADER.split("\nKICK RULE:")[0]
    elif user_header == "minimal":
        hdr = MINIMAL_USER_HEADER
    elif user_header == "explain_full":
        hdr = ev.TEXT_EXPLAIN_INSTRUCTION
    elif user_header == "explain_oracle":
        hdr = EXPLAIN_ORACLE_HEADER
    elif user_header == "explain_analysis":
        hdr = EXPLAIN_ANALYSIS_HEADER
    elif user_header == "explain_k3h":
        hdr = ev.TEXT_EXPLAIN_INSTRUCTION + "\n" + _k3_rules_section()
    else:
        hdr = ""
    return world + f"\n\nCommand: {blue_names}\n\n" + hdr


def is_explain_style(user_header):
    return str(user_header).startswith("explain_")


# --------------------------------------------------------------------------
# F2 metrics
# --------------------------------------------------------------------------

def _text_quality(text, sample_texts):
    """0..1 quality score for an ANALYSIS/ORACLE text field."""
    if not text:
        return 0.0
    if isinstance(text, (dict, list)):
        return 0.0
    text = str(text).strip()
    if not (10 <= len(text) <= 500):
        return 0.3
    if text.startswith("{") or "assignments" in text:
        return 0.0
    if any(text.strip() == s.strip() for s in sample_texts if s):
        return 0.1
    checks = [
        any(t in text.lower() for t in SOCCER_TERMS),
        not text.isupper(),
        len(text.split()) >= 5,
    ]
    return sum(checks) / len(checks)


def vocab_compliance(data, raw):
    """Fraction of assignment actions/roles inside the controlled vocabulary."""
    if not data:
        return 0.0
    assigns = data.get("assignments", {})
    if not assigns:
        return 0.0
    ok = 0
    total = 0
    for name, a in assigns.items():
        if not isinstance(a, dict):
            continue
        total += 1
        action_ok = a.get("action") in ALLOWED_ACTIONS
        role_ok = a.get("role") in ALLOWED_ROLES or "role" not in a
        if action_ok and role_ok:
            ok += 1
    return round(ok / total, 3) if total else 0.0


def rule_following(scoring):
    """0..1 from the scorer's hard gates: in-field, coverage, roles."""
    if not scoring:
        return 0.0
    hard = scoring.get("hard", {})
    diag = scoring.get("diagnostics", {})
    checks = [
        not bool(diag.get("oob")),
        hard.get("coverage", False),
        not bool(diag.get("stale_roles")),
    ]
    return sum(checks) / len(checks)


def contradiction_score(analysis, oracle):
    """0..1 — higher = more contradictive argumentation present."""
    text = " ".join(str(t) for t in (analysis, oracle) if t)
    if not text:
        return 0.0
    hits = sum(1 for p in CONTRADICTION_PATTERNS if p in text.lower())
    return min(hits / 3.0, 1.0)


def compute_f2(raw, data, ents, match_state, scoring, latency_ms, sample_texts):
    """Return the per-probe F2 metric dict (continue_accuracy filled later)."""
    analysis = (data or {}).get("analysis", "") if isinstance(data, dict) else ""
    oracle = (data or {}).get("oracle", "") if isinstance(data, dict) else ""
    n_blue = len([k for k in ents if k.startswith("blue")])
    n_assign = len((data or {}).get("assignments", {})) if data else 0
    return {
        "parse_success": data is not None,
        "vocab_compliance": vocab_compliance(data, raw),
        "rule_following": rule_following(scoring),
        "analysis_quality": _text_quality(analysis, sample_texts),
        "oracle_quality": _text_quality(oracle, sample_texts),
        "contradiction_score": contradiction_score(analysis, oracle),
        "role_coverage": round(n_assign / n_blue, 3) if n_blue else 0.0,
        "continue_accuracy": None,
        "latency_ms": latency_ms,
    }


# --------------------------------------------------------------------------
# Runner
# --------------------------------------------------------------------------

def run_probe(cfg, label, ents, match_state, model, sample_texts):
    status = match_state.get("status", "playing")
    explain = is_explain_style(cfg.get("user_header", "full"))
    sys_prompt = assemble_system_prompt(cfg, status)
    user_prompt = build_user_prompt(ents, match_state,
                                    cfg.get("user_header", "full"))
    tokens_limit = 600 if explain else 200
    raw, latency_ms = call_ollama(user_prompt, sys_prompt, tokens_limit, model)
    data, code, strict_data, strict_code = parse_output(raw, True, True)
    scoring = score_result(data["assignments"], ents, status) if data else None
    f2 = compute_f2(raw, data, ents, match_state, scoring, latency_ms,
                    sample_texts)
    return {
        "config": cfg.get("_name", "?"),
        "situation": label,
        "status": status,
        "sys_prompt_chars": len(sys_prompt),
        "user_prompt_chars": len(user_prompt),
        "latency_ms": latency_ms,
        "parse_code": code,
        "strict_code": strict_code,
        "score": scoring["score"] if scoring else 0.0,
        "hard_pass": bool(scoring["hard_pass"]) if scoring else False,
        "assignments": data.get("assignments") if data else None,
        "f2": f2,
        "raw_response": raw[:2000],
    }


def load_corpus(path):
    if not path or path == "battery":
        return [{"label": l, "status": s, "score_blue": sb, "score_red": sr,
                 "entities": e} for l, s, sb, sr, e in SITUATIONS]
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def sample_texts_from_cfg(cfg):
    """Extract ANALYSIS/ORACLE/EXPERT lines from the config's samples to
    detect verbatim parrot-copies."""
    txt = read_fragment(cfg.get("samples_mode") or "")
    if not txt:
        return []
    return [ln.strip() for ln in txt.splitlines()
            if re.match(r"^\s*(ANALYSIS|ORACLE|EXPERT)\s*:", ln)]


def write_raw(path, records):
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def _normalize_assignments(assignments):
    """Canonical form for semantic determinism comparison."""
    if not assignments:
        return None
    try:
        return json.dumps(
            {k: {kk: round(vv, 1) if isinstance(vv, float) else vv
                 for kk, vv in sorted(v.items()) if kk != "role"}
             for k, v in sorted(assignments.items())},
            sort_keys=True)
    except (TypeError, ValueError):
        return None


def compute_continue_accuracy(records):
    """Semantic determinism across repeats (temp 0.0): identical parsed
    assignments for the same (config, situation) across its repeats -> 1.0.
    Raw-text equality is NOT used — token streams vary across KV-cache
    states (measured 2026-08-01) while semantics stay stable."""
    by_key = {}
    for r in records:
        by_key.setdefault((r["config"], r["situation"]), []).append(r)
    for recs in by_key.values():
        if len(recs) < 2:
            continue
        base = _normalize_assignments(recs[0].get("assignments"))
        if base is None:
            continue
        acc = all(_normalize_assignments(r.get("assignments")) == base
                  for r in recs[1:])
        for r in recs:
            r["f2"]["continue_accuracy"] = 1.0 if acc else 0.0
    for r in records:
        if r["f2"]["continue_accuracy"] is None:
            r["f2"]["continue_accuracy"] = 1.0


def agg_metric(records, key):
    vals = [r["f2"][key] for r in records if r["f2"][key] is not None]
    if not vals:
        return 0.0
    if key == "latency_ms":
        vals.sort()
        return vals[len(vals) // 2]
    return round(sum(vals) / len(vals), 3)


def write_report(path, records, model, configs):
    compute_continue_accuracy(records)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# Phase F Probe Report ({time.strftime('%Y-%m-%d %H:%M')})\n\n")
        f.write(f"Model: `{model}` | Probes: {len(records)}\n\n")
        f.write("## Per-config aggregate (mean over situations and repeats)\n\n")
        f.write("| Config | hard% | parse% | score | vocab | ruleF | analysisQ | oracleQ | "
                "contrad | cov | continue | lat p50 |\n")
        f.write("|---|---|---|---|---|---|---|---|---|---|---|---|\n")
        for cname in configs:
            recs = [r for r in records if r["config"] == cname]
            if not recs:
                continue
            hard = sum(1 for r in recs if r["hard_pass"]) / len(recs)
            f.write(
                f"| {cname} | {hard:.0%} | {agg_metric(recs, 'parse_success'):.0%} | "
                f"{sum(r['score'] for r in recs) / len(recs):.1f} | "
                f"{agg_metric(recs, 'vocab_compliance'):.2f} | "
                f"{agg_metric(recs, 'rule_following'):.2f} | "
                f"{agg_metric(recs, 'analysis_quality'):.2f} | "
                f"{agg_metric(recs, 'oracle_quality'):.2f} | "
                f"{agg_metric(recs, 'contradiction_score'):.2f} | "
                f"{agg_metric(recs, 'role_coverage'):.2f} | "
                f"{agg_metric(recs, 'continue_accuracy'):.0%} | "
                f"{agg_metric(recs, 'latency_ms')}ms |\n")
        f.write("\n## Worst situations per config (hard-fail rate)\n\n")
        for cname in configs:
            recs = [r for r in records if r["config"] == cname]
            if not recs:
                continue
            per_sit = {}
            for r in recs:
                per_sit.setdefault(r["situation"], []).append(r)
            worst = sorted(
                ((s, sum(1 for r in rr if not r["hard_pass"]) / len(rr))
                 for s, rr in per_sit.items()), key=lambda x: -x[1])[:5]
            f.write(f"- **{cname}:** " +
                    ", ".join(f"{s} ({rate:.0%})" for s, rate in worst) + "\n")
        f.write("\n## Raw samples (one per config, first probe)\n\n")
        for cname in configs:
            recs = [r for r in records if r["config"] == cname]
            if not recs:
                continue
            f.write(f"### {cname} — {recs[0]['situation']}\n\n")
            f.write(f"```\n{recs[0]['raw_response'][:800]}\n```\n\n")


def main():
    ap = argparse.ArgumentParser(description="Phase F probe instrument")
    ap.add_argument("--config", default="F0",
                    help="comma-separated config names from CONFIGS")
    ap.add_argument("--corpus", default="battery",
                    help="JSONL corpus file or 'battery' (i3 situations)")
    ap.add_argument("--frag-dir", default="",
                    help="experiment fragments dir; files missing there "
                         "fall back to strategy/fragments/")
    ap.add_argument("--model", default=os.getenv("R2K_OLLAMA_MODEL", "qwen2.5:3b"))
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--tag", default="probe", help="output tag")
    ap.add_argument("--only", default="", help="comma-separated situation labels")
    ap.add_argument("--list-configs", action="store_true")
    args = ap.parse_args()

    if args.list_configs:
        for n, c in CONFIGS.items():
            print(f"{n}: {c['label']}")
        return

    configs = [c.strip() for c in args.config.split(",") if c.strip()]
    for c in configs:
        if c not in CONFIGS:
            print(f"Unknown config {c!r}. Known: {', '.join(CONFIGS)}")
            sys.exit(1)
    global EXTRA_FRAG_DIR
    EXTRA_FRAG_DIR = args.frag_dir

    corpus = load_corpus(args.corpus)
    if args.only:
        only = set(x.strip() for x in args.only.split(","))
        corpus = [s for s in corpus if s["label"] in only]

    total = len(corpus) * len(configs) * args.repeat
    print(f"Configs: {configs} | Situations: {len(corpus)} | "
          f"Repeats: {args.repeat} | Probes: {total} "
          f"(est. {total * 0.9 / 60:.1f} min at ~0.9s/probe)")
    os.makedirs(RESULTS_DIR, exist_ok=True)
    t0 = time.time()
    n = 0
    records = []
    for cname in configs:
        cfg = dict(CONFIGS[cname])
        cfg["_name"] = cname
        sample_texts = sample_texts_from_cfg(cfg)
        for sit in corpus:
            ents = sit["entities"]
            match_state = {"blue": sit.get("score_blue", 0),
                           "red": sit.get("score_red", 0),
                           "status": sit.get("status", "playing")}
            for rep in range(args.repeat):
                n += 1
                r = run_probe(cfg, sit["label"], ents, match_state,
                              args.model, sample_texts)
                records.append(r)
                tag = f"[{n}/{total}] {cname} {sit['label']} r{rep + 1}"
                print(f"{tag}: code={r['parse_code']} score={r['score']} "
                      f"lat={r['latency_ms']}ms "
                      f"({time.strftime('%H:%M:%S')})")
    elapsed = time.time() - t0
    raw_path = os.path.join(RESULTS_DIR, f"probe_{args.tag}_raw.jsonl")
    report_path = os.path.join(RESULTS_DIR, f"probe_{args.tag}_report.md")
    write_raw(raw_path, records)
    write_report(report_path, records, args.model, configs)
    print(f"\nDone: {len(records)} probes in {elapsed / 60:.1f} min")
    print(f"Raw: {raw_path}\nReport: {report_path}")


if __name__ == "__main__":
    main()
