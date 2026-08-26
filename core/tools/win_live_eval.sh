#!/bin/bash
# WIN experiment live decider (Phase 4): challenger vs FRESH B13 baseline.
# 21 matches per arm (7 scenarios x 3 reps x 120s, round-robin order).
# Arm order: B13 baseline first (current disk state), then challenger swap.
# Trap + normal completion restore B13 (post-run commitment: revert to B13
# unless the challenger WINS the live decider).
#
# Usage:
#   nohup bash tools/win_live_eval.sh <challenger_tag> <challenger_samples_file> \
#       > src/results/win_live_eval.log 2>&1 & disown

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CORE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SRC_DIR="$CORE_DIR/src"
LAUNCH="$CORE_DIR/launch_r2k.sh"
FRAG_DIR="$SRC_DIR/strategy/fragments"
ANALYZE="$SRC_DIR/tools/analyze_trace.py"
RESULTS_DIR="$SRC_DIR/results"

SAMPLES="$FRAG_DIR/samples_3vs3.txt"

if [[ $# -ne 2 ]]; then
    echo "Usage: $0 <challenger_tag> <challenger_samples_file>"
    exit 1
fi
CHAL_TAG="$1"
CHAL_FILE="$2"

if [[ ! -f "$CHAL_FILE" ]]; then
    echo "[FATAL] challenger samples file not found: $CHAL_FILE"
    exit 1
fi

B13_SHA1="44795270bf98832aff114d2a38371c8a2726e494"
BASELINE_SNAP="$FRAG_DIR/samples_3vs3_b13_snapshot.txt"

restore_b13() {
    if [[ -f "$BASELINE_SNAP" ]]; then
        cp "$BASELINE_SNAP" "$SAMPLES"
        echo "[trap] restored B13 samples from snapshot"
    fi
}
trap restore_b13 ERR

# Match plan: 7 scenarios x 3 reps, round-robin, all 120s (21 per arm)
SCENARIOS=(3vs3_attack_center 3vs3_attack_wing 3vs3_wing_switch 3vs3_def_transition 3vs3_default 3vs3_high_line 3vs3_defensive_crisis)
MATCHES=()
for ROUND in 1 2 3; do
    for S in "${SCENARIOS[@]}"; do
        MATCHES+=("${S}:120")
    done
done

# --- Verify fragment state, snapshot baseline ---
CUR_SHA1=$(sha1sum "$SAMPLES" | cut -d' ' -f1)
if [[ "$CUR_SHA1" != "$B13_SHA1" ]]; then
    echo "[FATAL] samples_3vs3.txt is not the expected B13 state ($CUR_SHA1)"
    echo "        Expected: $B13_SHA1. Aborting — no matches run."
    exit 1
fi
cp "$SAMPLES" "$BASELINE_SNAP"
echo "[ok] B13 baseline snapshot written"

# --- Warmup ---
echo -n "[warmup] loading qwen2.5:3b... "
curl -s -X POST http://127.0.0.1:11434/api/generate \
    -H "Content-Type: application/json" \
    -d '{"model":"qwen2.5:3b","prompt":"hello","stream":false,"options":{"num_predict":1}}' \
    -o /dev/null
echo "done"

run_arm() {
    local ARM="$1"
    local RAW="$RESULTS_DIR/win_live_${ARM}_raw.json"
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

# --- Arm 1: FRESH B13 baseline (current disk state) ---
echo "==============================================="
echo "ARM 1/2: B13 (fresh baseline)"
echo "==============================================="
run_arm "b13fresh"

# --- Swap to challenger ---
echo ""
echo "[swap] applying challenger samples ($CHAL_TAG from $CHAL_FILE)"
cp "$CHAL_FILE" "$SAMPLES"
SWAP_SHA1=$(sha1sum "$SAMPLES" | cut -d' ' -f1)
echo "[swap] samples_3vs3.txt sha1: $SWAP_SHA1"

# --- Arm 2: challenger ---
echo "==============================================="
echo "ARM 2/2: $CHAL_TAG (challenger)"
echo "==============================================="
run_arm "$CHAL_TAG"

# --- Restore B13 (post-run commitment) ---
cp "$BASELINE_SNAP" "$SAMPLES"
echo ""
echo "==============================================="
echo "DECIDER COMPLETE — $((2 * ${#MATCHES[@]})) matches"
echo "B13 fresh baseline: $RESULTS_DIR/win_live_b13fresh_raw.json"
echo "Challenger ($CHAL_TAG): $RESULTS_DIR/win_live_${CHAL_TAG}_raw.json"
echo "B13 restored to samples_3vs3.txt"
echo "==============================================="
