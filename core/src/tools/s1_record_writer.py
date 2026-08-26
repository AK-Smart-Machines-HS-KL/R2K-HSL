#!/usr/bin/env python3
"""Record writer for s1_live_eval.sh — merges analyze_trace.py multi-part
JSON output into one flat record. Reads KPI JSON from stdin, env vars for
scenario/match/arm. Prints one JSON record to stdout (always valid JSON)."""
import json
import os
import sys


def main():
    scenario = os.environ.get("SCENARIO", "?")
    try:
        match_no = int(os.environ.get("MATCH_NO", "0"))
    except ValueError:
        match_no = 0
    arm = os.environ.get("ARM_NAME", "?")
    raw = sys.stdin.read()
    first = None
    try:
        decoder = json.JSONDecoder()
        idx = 0
        while idx < len(raw):
            s = raw[idx:].lstrip()
            if not s:
                break
            idx = len(raw) - len(s)
            try:
                obj, end = decoder.raw_decode(raw, idx)
                if first is None:
                    first = obj
                idx = end
            except json.JSONDecodeError:
                idx += 1
    except Exception:
        first = None
    d = {}
    if first:
        d = {**first.get("world_kpis", {}), **first.get("llm_kpis", {})}
    d["_scenario"] = scenario
    d["_match"] = match_no
    d["_arm"] = arm
    if first is None and raw.strip():
        d["_error"] = "kpi_parse_failed"
    print(json.dumps(d))


if __name__ == "__main__":
    main()
