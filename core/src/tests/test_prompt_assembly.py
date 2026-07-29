#!/usr/bin/env python3
"""Test cases for system prompt assembly and LLM output validation."""

import json
import glob
import os
import re
import pytest
from pathlib import Path

SRC_DIR = Path(__file__).parent.parent
LOG_DIR = SRC_DIR / "logs"


def test_oracle_is_string_in_trace():
    """Oracle field in llm_trace must be a string (text prediction),
    not a dict/list (JSON strategy dump). Catches the bug where Qwen 3B
    fills oracle with assignments JSON instead of a predictive sentence."""
    trace_files = sorted(glob.glob(str(LOG_DIR / "llm_trace_*.jsonl")),
                        key=os.path.getmtime, reverse=True)
    if not trace_files:
        pytest.skip("No llm_trace files found")
    with open(trace_files[0]) as f:
        for line in f:
            rec = json.loads(line)
            raw = rec.get('raw_response', '').strip()
            if raw.startswith('```'):
                raw = raw.split('\n', 1)[-1].rsplit('```', 1)[0].strip()
            start = raw.find('{')
            end = raw.rfind('}')
            if start == -1 or end == -1:
                continue
            try:
                data = json.loads(raw[start:end + 1])
            except Exception:
                continue
            if 'oracle' in data:
                assert isinstance(data['oracle'], str), \
                    f"oracle is {type(data['oracle']).__name__}, expected str: {data['oracle']}"
            if 'analysis' in data:
                assert isinstance(data['analysis'], str), \
                    f"analysis is {type(data['analysis']).__name__}, expected str: {data['analysis']}"