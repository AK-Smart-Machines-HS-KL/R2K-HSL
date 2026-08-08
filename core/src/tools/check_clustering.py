#!/usr/bin/env python3
"""Phase 3 clustering regression check.

Post-processes probe_p3_struct_raw.jsonl: computes pairwise blue target
distances per record, asserts min target dist >= 1.0m in >= 80% of records.
Standalone — does not modify llm_probe.py.

Usage:
  python3 tools/check_clustering.py results/probe_p3_struct_raw.jsonl
  python3 tools/check_clustering.py results/probe_p3_struct_raw.jsonl --split
"""
import argparse
import json
import math
import os
import sys
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.abspath(__file__)) + "/.."
SPACING_MIN_M = 1.0
THRESHOLD_PCT = 0.80


def min_pairwise_dist(targets):
    """targets: {name: (x, y)} of Move actions. Returns min pairwise dist."""
    coords = list(targets.values())
    if len(coords) < 2:
        return None
    return min(
        math.hypot(cx - dx, cy - dy)
        for i, (cx, cy) in enumerate(coords)
        for dx, dy in coords[i + 1:]
    )


def check_record(rec):
    """Returns (scenario, min_dist, n_move_targets, pass_bool)."""
    a = rec.get("assignments") or {}
    targets = {
        n: (v["x"], v["y"])
        for n, v in a.items()
        if v.get("action") == "Move" and "x" in v and "y" in v
    }
    md = min_pairwise_dist(targets)
    passed = md is not None and md >= SPACING_MIN_M
    return rec.get("situation", "?"), md, len(targets), passed


def report(records, label="all"):
    total = len(records)
    if total == 0:
        print(f"\n[{label}] No records.")
        return 0.0
    n_pass = sum(1 for r in records if r[3])
    pct = n_pass / total
    print(f"\n[{label}] {n_pass}/{total} records pass min-dist >= {SPACING_MIN_M}m "
          f"({pct:.1%}) — threshold {THRESHOLD_PCT:.0%}")
    if pct < THRESHOLD_PCT:
        print(f"  ❌ BELOW threshold")
    else:
        print(f"  ✅ meets threshold")
    # Per-scenario breakdown
    by_scen = defaultdict(list)
    for sc, md, n, p in records:
        by_scen[sc].append((md, n, p))
    worst = []
    for sc, recs in by_scen.items():
        fail_rate = sum(1 for _, _, p in recs if not p) / len(recs)
        if fail_rate > 0:
            worst.append((sc, fail_rate, len(recs)))
    worst.sort(key=lambda x: -x[1])
    if worst:
        print(f"  Scenarios with clustering failures (top 10):")
        for sc, rate, n in worst[:10]:
            print(f"    {sc}: {rate:.0%} fail ({n} records)")
    else:
        print(f"  No clustering failures — all scenarios pass.")
    return pct


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("raw", help="probe_*_raw.jsonl file")
    ap.add_argument("--split", action="store_true",
                    help="report hand-crafted vs empirical separately")
    args = ap.parse_args()

    with open(args.raw, encoding="utf-8") as f:
        records = [check_record(json.loads(l)) for l in f if l.strip()]

    all_pct = report(records, "all 50")

    if args.split:
        hc = [r for r in records if not r[0].startswith("emp_")]
        emp = [r for r in records if r[0].startswith("emp_")]
        report(hc, "hand-crafted 17")
        report(emp, "empirical 33")

    print()
    if all_pct >= THRESHOLD_PCT:
        print(f"VERDICT: ✅ clustering regression check PASSED ({all_pct:.1%} >= {THRESHOLD_PCT:.0%})")
        sys.exit(0)
    else:
        print(f"VERDICT: ❌ clustering regression check FAILED ({all_pct:.1%} < {THRESHOLD_PCT:.0%})")
        sys.exit(1)


if __name__ == "__main__":
    main()
