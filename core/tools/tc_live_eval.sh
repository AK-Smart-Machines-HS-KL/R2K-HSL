#!/bin/bash
# TeamCaptain Slice 1 live eval: flag ON vs OFF (fresh B13 baseline).
# 21 matches per arm (7 scenarios x 3), 120s each. Same bridge file both arms —
# only the R2K_TEAMCAPTAIN env flag differs (passed through launch_r2k.sh).
#
# Usage: nohup bash tools/tc_live_eval.sh > src/results/tc_live_eval.log 2>&1 & disown

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CORE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SRC_DIR="$CORE_DIR/src"
LAUNCH="$CORE_DIR/launch_r2k.sh"
ANALYZE="$SRC_DIR/tools/analyze_trace.py"
RESULTS_DIR="$SRC_DIR/results"

SCENARIOS=(3vs3_attack_center 3vs3_attack_wing 3vs3_wing_switch 3vs3_def_transition 3vs3_default 3vs3_high_line 3vs3_defensive_crisis)
REPS=3

run_arm() {
    local ARM="$1"      # "tc" or "base"
    local FLAG="$2"     # "1" or "0"
    local RAW="$RESULTS_DIR/tc_live_${ARM}_raw.json"
    echo "[" > "$RAW"
    local FIRST=1
    local N=0
    for scenario in "${SCENARIOS[@]}"; do
        for rep in $(seq 1 "$REPS"); do
            N=$((N+1))
            echo ""
            echo ">>> [$ARM match $N/21] $scenario rep$rep <<<"
            OUTPUT="$(export R2K_TEAMCAPTAIN="$FLAG"; "$LAUNCH" --headless --duration 120 --scenario "$scenario" --relay only_sim_bots 2>&1)" || true
            RUN_ID=$(echo "$OUTPUT" | grep -oP 'Run ID:\s*\K[^\s]+' | head -1)
            if [[ -z "$RUN_ID" ]]; then
                RUN_ID="${scenario}_strat_aggro_$(date +%Y%m%d_%H%M%S)"
            fi
            echo "  Run ID: $RUN_ID"
            KPI_JSON=$(python3 "$ANALYZE" --run-id "$RUN_ID" 2>/dev/null || echo '{}')
            if [[ $FIRST -eq 0 ]]; then echo "," >> "$RAW"; fi
            FIRST=0
            RECORD=$(SCENARIO="$scenario" MATCH_NO="$N" ARM_NAME="$ARM" python3 "$SRC_DIR/tools/s1_record_writer.py" <<< "$KPI_JSON")
            echo -n "$RECORD" >> "$RAW"
            echo "$RECORD" | python3 -c "
import sys, json
try:
    d = json.loads(sys.stdin.read())
    print(f'  goals: {d.get(\"goals_for_blue\",0)}B-{d.get(\"goals_for_red\",0)}R  poss: {d.get(\"ball_possession_blue_pct\",0):.0f}%  sog: {d.get(\"shots_on_goal\",0)}  sot: {d.get(\"shots_on_target\",0)}  lat: {d.get(\"latency_p50\",0)}ms  goalie: {d.get(\"goalie_tactical_pct\",0):.0f}%  parse: {d.get(\"parse_error_rate\",0):.1f}%')
except Exception:
    print('  (KPI extraction failed)')
"
        done
    done
    echo "" >> "$RAW"
    echo "]" >> "$RAW"
    echo "=== Arm $ARM complete: 21 matches -> $RAW ==="
}

echo "=== TeamCaptain Slice 1 live eval — $(date) ==="
echo "Arms: tc (R2K_TEAMCAPTAIN=1) vs base (flag off), 21 matches each"

# Arm 1: TeamCaptain ON
run_arm "tc" "1"

# Arm 2: baseline OFF
run_arm "base" "0"

echo ""
echo "==============================================="
echo "EVAL COMPLETE — 42 matches"
echo "TC results:    $RESULTS_DIR/tc_live_tc_raw.json"
echo "Baseline:      $RESULTS_DIR/tc_live_base_raw.json"
echo "==============================================="
