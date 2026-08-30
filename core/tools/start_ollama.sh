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
ENSURE=false
WARMUP_MODEL=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --check-only) CHECK_ONLY=true; shift ;;
        --ensure) ENSURE=true; shift ;;
        --model) WARMUP_MODEL="$2"; shift 2 ;;
        *) echo "Unknown arg: $1"; exit 1 ;;
    esac
done

# ---- Preflight ----
if ! command -v ollama >/dev/null 2>&1; then
    if [[ "$ENSURE" == "true" ]]; then
        echo "❌ 'ollama' is not installed — cannot auto-start. Cloud models remain usable." >&2
        echo "   Install: curl -fsSL https://ollama.com/install.sh | sh" >&2
        exit 0
    fi
    echo "❌ 'ollama' is not installed or not in PATH."
    echo "   Install: curl -fsSL https://ollama.com/install.sh | sh"
    exit 1
fi

# ---- Check if already running ----
if curl -s "${OLLAMA_LOCAL}/api/tags" > /dev/null 2>&1; then
    # Bridge health: reachable from Docker containers (172.17.0.1)?
    BRIDGE_OK=false
    if curl -s --max-time 2 "http://172.17.0.1:11434/api/tags" > /dev/null 2>&1; then
        BRIDGE_OK=true
    fi
    if [[ "$ENSURE" == "true" ]]; then
        # Silent fast path for shell wrappers — only surface actionable problems.
        if [[ "$BRIDGE_OK" == "true" ]]; then
            exit 0
        fi
        echo "⚠️  Ollama is running but NOT reachable on 172.17.0.1 (Docker bridge) — containers cannot reach it." >&2
        echo "   Fix: kill the current ollama process and re-run this script, or:" >&2
        echo "   sudo systemctl edit ollama → [Service] → Environment=\"OLLAMA_HOST=0.0.0.0\"" >&2
        exit 0
    fi
    echo "✅ Ollama is already online at ${OLLAMA_LOCAL}"
    if [[ "$BRIDGE_OK" != "true" ]]; then
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
if [[ "$ENSURE" != "true" ]]; then
    echo "🚀 Starting Ollama..."
    echo "   OLLAMA_HOST=$OLLAMA_HOST"
    echo "   OLLAMA_FLASH_ATTENTION=$OLLAMA_FLASH_ATTENTION"
    echo "   OLLAMA_KV_CACHE_TYPE=$OLLAMA_KV_CACHE_TYPE"
    echo "   OLLAMA_KEEP_ALIVE=$OLLAMA_KEEP_ALIVE"
    echo "   OLLAMA_MODELS=$OLLAMA_MODELS"
fi

# Determine log file path — use /tmp to avoid path resolution issues
LOG_FILE="/tmp/r2k_ollama.log"

nohup ollama serve > "$LOG_FILE" 2>&1 &
disown $!

# ---- Wait for bind ----
if [[ "$ENSURE" != "true" ]]; then
    echo "⏳ Waiting for Ollama to bind..."
fi
for i in $(seq 1 10); do
    if curl -s "${OLLAMA_LOCAL}/api/tags" > /dev/null 2>&1; then
        if [[ "$ENSURE" == "true" ]]; then
            echo "⚠️  Ollama was down — started (ROS2K procedure, log: $LOG_FILE)"
            if ! curl -s --max-time 2 "http://172.17.0.1:11434/api/tags" > /dev/null 2>&1; then
                echo "⚠️  WARNING: not reachable on 172.17.0.1 (Docker bridge) — containers cannot reach it." >&2
            fi
        else
            echo "✅ Ollama is online at ${OLLAMA_LOCAL}"
        fi
        break
    fi
    sleep 1
    if [[ $i -eq 10 ]]; then
        if [[ "$ENSURE" == "true" ]]; then
            echo "❌ Ollama failed to start within 10s (log: $LOG_FILE). Cloud models remain usable." >&2
            exit 0
        fi
        echo "❌ Ollama failed to start within 10s. Check $LOG_FILE"
        exit 1
    fi
done

# ---- Verify Docker bridge reachability ----
if [[ "$ENSURE" != "true" ]]; then
    if ! curl -s --max-time 2 "http://172.17.0.1:11434/api/tags" > /dev/null 2>&1; then
        echo "⚠️  WARNING: Ollama is reachable on 127.0.0.1 but NOT on 172.17.0.1 (Docker bridge)."
        echo "   This is expected if OLLAMA_HOST was not set to 0.0.0.0."
        echo "   Current OLLAMA_HOST=$OLLAMA_HOST"
    else
        echo "✅ Ollama reachable on Docker bridge (172.17.0.1:11434)"
    fi
fi

# ---- Optional warm-up ----
if [[ -n "$WARMUP_MODEL" ]]; then
    echo "🔥 Warming up model '$WARMUP_MODEL' (cold-boot load, ~30s on first run)..."
    curl -s --max-time 120 "${OLLAMA_LOCAL}/api/generate" \
        -d "{\"model\":\"$WARMUP_MODEL\",\"prompt\":\"hi\",\"stream\":false}" > /dev/null 2>&1
    echo "✅ Model '$WARMUP_MODEL' is warm."
fi