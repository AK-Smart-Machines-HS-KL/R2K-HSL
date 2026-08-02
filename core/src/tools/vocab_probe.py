#!/usr/bin/env python3
"""Phase 1 vocabulary probing tool.

Thin wrapper around the Ollama API for conversational vocabulary discovery.
Appends every probe (prompt + response + latency) to results/vocab_probe_log.md.

Phase-1 only. Phase F uses the batch instrument tools/llm_probe.py instead.

Usage:
  python3 tools/vocab_probe.py --prompt "List soccer words you know"
  python3 tools/vocab_probe.py --series A1 --prompt "..." [--system "..."]
  python3 tools/vocab_probe.py --batch <jsonl>   # run a probe battery file

Batch file format (JSONL), one probe per line:
  {"series": "A1", "prompt": "...", "system": "..." (optional)}
"""

import argparse
import json
import os
import sys
import time
import urllib.request

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
MODEL = os.getenv("R2K_OLLAMA_MODEL", "qwen2.5:3b")
RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
LOG_PATH = os.path.join(RESULTS_DIR, "vocab_probe_log.md")

DEFAULT_SYSTEM = (
    "You are a soccer analyst. Answer in natural English. "
    "Be concise and specific. Do not output JSON unless asked."
)


def call_ollama(prompt, system=None, num_predict=600):
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "system": system if system else DEFAULT_SYSTEM,
        "stream": False,
        "temperature": 0.0,
        "num_predict": num_predict,
        "keep_alive": "1h",
    }
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=150) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    latency_ms = round((time.time() - t0) * 1000)
    return body.get("response", "").strip(), latency_ms


def append_log(series, prompt, system, response, latency_ms):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"\n### {series}\n")
        if system:
            f.write(f"- **system:** {system}\n")
        f.write(f"- **prompt:** {prompt}\n")
        f.write(f"- **latency:** {latency_ms} ms\n")
        f.write(f"- **response:**\n\n{response}\n")
        f.write("\n---\n")


def run_one(probe, index=None, total=None):
    series = probe.get("series", f"probe_{index}")
    prompt = probe["prompt"]
    system = probe.get("system")
    label = f"[{index}/{total}] " if index else ""
    print(f"{label}{series}: {prompt[:80]!r} ...")
    try:
        response, latency_ms = call_ollama(prompt, system)
    except Exception as e:
        print(f"  ERROR: {e}")
        append_log(series, prompt, system, f"ERROR: {e}", 0)
        return
    append_log(series, prompt, system, response, latency_ms)
    print(f"  ({latency_ms} ms) {response[:120]!r}")


def main():
    ap = argparse.ArgumentParser(description="Phase 1 vocabulary probe tool")
    ap.add_argument("--prompt", help="single probe prompt")
    ap.add_argument("--series", default="probe", help="series label for single probe")
    ap.add_argument("--system", help="override system prompt")
    ap.add_argument("--batch", help="JSONL batch file of probes")
    args = ap.parse_args()

    os.makedirs(RESULTS_DIR, exist_ok=True)
    if not os.path.exists(LOG_PATH):
        with open(LOG_PATH, "w", encoding="utf-8") as f:
            f.write(f"# Vocabulary Probe Log (model: {MODEL})\n")
            f.write(f"Probes: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

    if args.batch:
        with open(args.batch, encoding="utf-8") as f:
            probes = [json.loads(line) for line in f if line.strip()]
        for i, probe in enumerate(probes, 1):
            run_one(probe, i, len(probes))
        print(f"\nDone. {len(probes)} probes appended to {LOG_PATH}")
    elif args.prompt:
        run_one({"series": args.series, "prompt": args.prompt,
                 "system": args.system}, 1, 1)
        print(f"\nDone. Log: {LOG_PATH}")
    else:
        ap.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
