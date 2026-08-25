#!/bin/bash
# S1 live validation: B13 vs V1 (production samples) — 10 matches per arm.
# Mixed durations: goalie_instant_kick @60s, others @120s.
# Arm order: V1 first (untouched fragments), then swap to B13.
# On normal completion B13 stays applied (decision deferred); on crash the
# trap restores V1. V1 backup: samples_3vs3_v1_backup.txt (always kept).
#
# Usage: nohup bash tools/s1_live_eval.sh > src/results/s1_live_eval.log 2>&1 & disown

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CORE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SRC_DIR="$CORE_DIR/src"
LAUNCH="$CORE_DIR/launch_r2k.sh"
FRAG_DIR="$SRC_DIR/strategy/fragments"
ANALYZE="$SRC_DIR/tools/analyze_trace.py"
RESULTS_DIR="$SRC_DIR/results"

SAMPLES="$FRAG_DIR/samples_3vs3.txt"
STAGING="$FRAG_DIR/samples_3vs3_b13_staging.txt"
BACKUP="$FRAG_DIR/samples_3vs3_v1_backup.txt"

V1_SHA1="ff9359a882656acdedf1a1ab6265bb83ee01e494"

restore_v1() {
    if [[ -f "$BACKUP" ]]; then
        cp "$BACKUP" "$SAMPLES"
        echo "[trap] restored V1 samples from backup"
    fi
}
trap restore_v1 ERR

# Match plan: scenario:duration pairs (10 matches per arm)
MATCHES=(
    "goalie_instant_kick:60"
    "goalie_instant_kick:60"
    "3vs3_default:120"
    "3vs3_default:120"
    "3vs3_default:120"
    "3vs3_defensive_crisis:120"
    "3vs3_defensive_crisis:120"
    "3vs3_defensive_crisis:120"
    "3vs3_attack_center:120"
    "3vs3_attack_center:120"
)

# --- Verify fragment state, create backup ---
CUR_SHA1=$(sha1sum "$SAMPLES" | cut -d' ' -f1)
if [[ "$CUR_SHA1" != "$V1_SHA1" ]]; then
    echo "[FATAL] samples_3vs3.txt is not the expected V1 state ($CUR_SHA1)"
    echo "        Expected: $V1_SHA1. Aborting — no matches run."
    exit 1
fi
cp "$SAMPLES" "$BACKUP"
echo "[ok] V1 backup written to samples_3vs3_v1_backup.txt"

# --- Warmup ---
echo -n "[warmup] loading qwen2.5:3b... "
curl -s -X POST http://127.0.0.1:11434/api/generate \
    -H "Content-Type: application/json" \
    -d '{"model":"qwen2.5:3b","prompt":"hello","stream":false,"options":{"num_predict":1}}' \
    -o /dev/null
echo "done"

run_arm() {
    local ARM="$1"
    local RAW="$RESULTS_DIR/s1_live_${ARM}_raw.json"
    echo "[" > "$RAW"
    local FIRST=1
    local N=0
    for spec in "${MATCHES[@]}"; do
        SCENARIO="${spec%%:*}"
        DURATION="${spec##*:}"
        N=$((N+1))
        echo ""
        echo ">>> [$ARM match $N/${#MATCHES[@]}] $SCENARIO ${DURATION}s <<<"

        OUTPUT="$("$LAUNCH" --headless --duration "$DURATION" --scenario "$SCENARIO" --relay only_sim_bots 2>&1)" || true
        RUN_ID=$(echo "$OUTPUT" | grep -oP 'Run ID:\s*\K[^\s]+' | head -1)
        if [[ -z "$RUN_ID" ]]; then
            RUN_ID=$(echo "$OUTPUT" | grep -oP 'R2K_RUN_ID=\K[^\s]+' | head -1)
        fi
        if [[ -z "$RUN_ID" ]]; then
            RUN_ID="${SCENARIO}_strat_aggro_$(date +%Y%m%d_%H%M%S)"
        fi
        echo "  Run ID: $RUN_ID"

        KPI_JSON=$(python3 "$ANALYZE" --run-id "$RUN_ID" 2>/dev/null || echo '{}')

        if [[ $FIRST -eq 0 ]]; then
            echo "," >> "$RAW"
        fi
        FIRST=0
        RECORD=$(SCENARIO="$SCENARIO" MATCH_NO="$N" ARM_NAME="$ARM" python3 "$SRC_DIR/tools/s1_record_writer.py" <<< "$KPI_JSON")
        echo -n "$RECORD" >> "$RAW"

        echo "$RECORD" | python3 -c "
import sys, json
try:
    d = json.loads(sys.stdin.read())
    print(f'  goals: {d.get(\"goals_for_blue\",0)}B-{d.get(\"goals_for_red\",0)}R  '
          f'poss: {d.get(\"ball_possession_blue_pct\",0):.0f}%  '
          f'lat_p50: {d.get(\"latency_p50\",0)}ms  '
          f'goalie: {d.get(\"goalie_tactical_pct\",0):.0f}%  '
          f'pass: {d.get(\"pass_completion_pct\",0):.0f}%  '
          f'parse_err: {d.get(\"parse_error_rate\",0):.1f}%')
except Exception:
    print('  (KPI extraction failed)')
"
    done
    echo "" >> "$RAW"
    echo "]" >> "$RAW"
    echo ""
    echo "=== Arm $ARM complete: ${#MATCHES[@]} matches -> $RAW ==="
}

# --- Arm 1: V1 (current production fragments) ---
echo "==============================================="
echo "ARM 1/2: V1 (production samples)"
echo "==============================================="
run_arm "v1"

# --- Swap to B13 ---
echo ""
echo "[swap] applying B13 samples"
cp "$STAGING" "$SAMPLES"
SWAP_SHA1=$(sha1sum "$SAMPLES" | cut -d' ' -f1)
echo "[swap] samples_3vs3.txt sha1: $SWAP_SHA1"

# --- Arm 2: B13 ---
echo "==============================================="
echo "ARM 2/2: B13 (steal-safe kicker identities)"
echo "==============================================="
run_arm "b13"

# --- Normal completion: B13 stays applied (decision deferred) ---
echo ""
echo "==============================================="
echo "EVAL COMPLETE — 20 matches"
echo "V1 results: $RESULTS_DIR/s1_live_v1_raw.json"
echo "B13 results: $RESULTS_DIR/s1_live_b13_raw.json"
echo "B13 remains applied to samples_3vs3.txt (decision deferred)."
echo "V1 backup: $BACKUP"
echo "==============================================="
