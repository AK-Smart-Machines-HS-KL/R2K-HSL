#!/bin/bash
# TC-lite isolation eval: R2K_TEAMCAPTAIN=1 R2K_KICK_BEHIND_GATE=0
# (aim-kick + goalie smoothing + idle facing, NO behind gate / offset shrink)
# vs the already-collected base arm (tc_live_base_raw.json, flag off —
# the OFF path in that run had aim-kick active in both arms).
# 21 matches, 7 scenarios x 3, 120s.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CORE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SRC_DIR="$CORE_DIR/src"
LAUNCH="$CORE_DIR/launch_r2k.sh"
ANALYZE="$SRC_DIR/tools/analyze_trace.py"
RESULTS_DIR="$SRC_DIR/results"

SCENARIOS=(3vs3_attack_center 3vs3_attack_wing 3vs3_wing_switch 3vs3_def_transition 3vs3_default 3vs3_high_line 3vs3_defensive_crisis)
REPS=3

RAW="$RESULTS_DIR/tc_live_tclite_raw.json"
echo "[" > "$RAW"
FIRST=1
N=0
for scenario in "${SCENARIOS[@]}"; do
    for rep in $(seq 1 "$REPS"); do
        N=$((N+1))
        echo ""
        echo ">>> [tclite match $N/21] $scenario rep$rep <<<"
        OUTPUT="$(export R2K_TEAMCAPTAIN=1 R2K_KICK_BEHIND_GATE=0; "$LAUNCH" --headless --duration 120 --scenario "$scenario" --relay only_sim_bots 2>&1)" || true
        RUN_ID=$(echo "$OUTPUT" | grep -oP 'Run ID:\s*\K[^\s]+' | head -1)
        if [[ -z "$RUN_ID" ]]; then RUN_ID="${scenario}_strat_aggro_$(date +%Y%m%d_%H%M%S)"; fi
        echo "  Run ID: $RUN_ID"
        KPI_JSON=$(python3 "$ANALYZE" --run-id "$RUN_ID" 2>/dev/null || echo '{}')
        if [[ $FIRST -eq 0 ]]; then echo "," >> "$RAW"; fi
        FIRST=0
        RECORD=$(SCENARIO="$scenario" MATCH_NO="$N" ARM_NAME="tclite" python3 "$SRC_DIR/tools/s1_record_writer.py" <<< "$KPI_JSON")
        echo -n "$RECORD" >> "$RAW"
        echo "$RECORD" | python3 -c "
import sys, json
try:
    d = json.loads(sys.stdin.read())
    print(f'  goals: {d.get(\"goals_for_blue\",0)}B-{d.get(\"goals_for_red\",0)}R  poss: {d.get(\"ball_possession_blue_pct\",0):.0f}%  sog: {d.get(\"shots_on_goal\",0)}  sot: {d.get(\"shots_on_target\",0)}  lat: {d.get(\"latency_p50\",0)}ms')
except Exception:
    print('  (KPI extraction failed)')
"
    done
done
echo "" >> "$RAW"
echo "]" >> "$RAW"
echo "=== TC-lite arm complete: 21 matches -> $RAW ==="
