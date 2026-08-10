#!/bin/bash
# tools/start_ollama.sh — standalone Ollama start helper
# Centralizes all Ollama env vars in one place. Used by launch_r2k.sh and
# for manual starts. See ADR-A06 for the user-space vs systemd rationale.
#
# Usage:
#   bash tools/start_ollama.sh                 # start with defaults
#   bash tools/start_ollama.sh --model qwen2.5:3b   # start + warm up a model
#   bash tools/start_ollama.sh --check-only     # verify, don't start
#
# All env vars below have sensible defaults; override by exporting before
# calling this script (e.g. OLLAMA_FLASH_ATTENTION=0 bash tools/start_ollama.sh).

set -euo pipefail

# ---- Defaults (overridable by caller) ----
export OLLAMA_HOST="${OLLAMA_HOST:-0.0.0.0:11434}"
export OLLAMA_ORIGINS="${OLLAMA_ORIGINS:-*}"
export OLLAMA_FLASH_ATTENTION="${OLLAMA_FLASH_ATTENTION:-1}"
export OLLAMA_KV_CACHE_TYPE="${OLLAMA_KV_CACHE_TYPE:-q8_0}"
export OLLAMA_MODELS="${OLLAMA_MODELS:-$HOME/.ollama/models}"
export OLLAMA_KEEP_ALIVE="${OLLAMA_KEEP_ALIVE:--1}"

OLLAMA_LOCAL="http://127.0.0.1:11434"

# ---- Parse args ----
CHECK_ONLY=false
WARMUP_MODEL=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --check-only) CHECK_ONLY=true; shift ;;
        --model) WARMUP_MODEL="$2"; shift 2 ;;
        *) echo "Unknown arg: $1"; exit 1 ;;
    esac
done

# ---- Preflight ----
if ! command -v ollama >/dev/null 2>&1; then
    echo "❌ 'ollama' is not installed or not in PATH."
    echo "   Install: curl -fsSL https://ollama.com/install.sh | sh"
    exit 1
fi

# ---- Check if already running ----
if curl -s "${OLLAMA_LOCAL}/api/tags" > /dev/null 2>&1; then
    echo "✅ Ollama is already online at ${OLLAMA_LOCAL}"
    # Verify bind address is 0.0.0.0 (not loopback-only)
    if ! curl -s --max-time 2 "http://172.17.0.1:11434/api/tags" > /dev/null 2>&1; then
        echo "⚠️  WARNING: Ollama is reachable on 127.0.0.1 but NOT on 172.17.0.1 (Docker bridge)."
        echo "   Docker containers will not be able to reach it."
        echo "   Fix: kill the current ollama process and re-run this script, or:"
        echo "   sudo systemctl edit ollama → [Service] → Environment=\"OLLAMA_HOST=0.0.0.0\""
    fi
    if [[ -n "$WARMUP_MODEL" ]]; then
        echo "🔥 Warming up model '$WARMUP_MODEL'..."
        curl -s --max-time 120 "${OLLAMA_LOCAL}/api/generate" \
            -d "{\"model\":\"$WARMUP_MODEL\",\"prompt\":\"hi\",\"stream\":false}" > /dev/null 2>&1
        echo "✅ Model '$WARMUP_MODEL' is warm."
    fi
    exit 0
fi

if [[ "$CHECK_ONLY" == "true" ]]; then
    echo "❌ Ollama is not running. (check-only mode — not starting)"
    exit 1
fi

# ---- Start Ollama ----
echo "🚀 Starting Ollama..."
echo "   OLLAMA_HOST=$OLLAMA_HOST"
echo "   OLLAMA_FLASH_ATTENTION=$OLLAMA_FLASH_ATTENTION"
echo "   OLLAMA_KV_CACHE_TYPE=$OLLAMA_KV_CACHE_TYPE"
echo "   OLLAMA_KEEP_ALIVE=$OLLAMA_KEEP_ALIVE"
echo "   OLLAMA_MODELS=$OLLAMA_MODELS"

# Determine log file path — use /tmp to avoid path resolution issues
LOG_FILE="/tmp/r2k_ollama.log"

nohup ollama serve > "$LOG_FILE" 2>&1 &
disown $!

# ---- Wait for bind ----
echo "⏳ Waiting for Ollama to bind..."
for i in $(seq 1 10); do
    if curl -s "${OLLAMA_LOCAL}/api/tags" > /dev/null 2>&1; then
        echo "✅ Ollama is online at ${OLLAMA_LOCAL}"
        break
    fi
    sleep 1
    if [[ $i -eq 10 ]]; then
        echo "❌ Ollama failed to start within 10s. Check $LOG_FILE"
        exit 1
    fi
done

# ---- Verify Docker bridge reachability ----
if ! curl -s --max-time 2 "http://172.17.0.1:11434/api/tags" > /dev/null 2>&1; then
    echo "⚠️  WARNING: Ollama is reachable on 127.0.0.1 but NOT on 172.17.0.1 (Docker bridge)."
    echo "   This is expected if OLLAMA_HOST was not set to 0.0.0.0."
    echo "   Current OLLAMA_HOST=$OLLAMA_HOST"
else
    echo "✅ Ollama reachable on Docker bridge (172.17.0.1:11434)"
fi

# ---- Optional warm-up ----
if [[ -n "$WARMUP_MODEL" ]]; then
    echo "🔥 Warming up model '$WARMUP_MODEL' (cold-boot load, ~30s on first run)..."
    curl -s --max-time 120 "${OLLAMA_LOCAL}/api/generate" \
        -d "{\"model\":\"$WARMUP_MODEL\",\"prompt\":\"hi\",\"stream\":false}" > /dev/null 2>&1
    echo "✅ Model '$WARMUP_MODEL' is warm."
fi