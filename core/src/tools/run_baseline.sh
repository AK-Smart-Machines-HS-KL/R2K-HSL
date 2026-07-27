#!/bin/bash
# Phase 2e: 27-run baseline (9 scenarios × 3 runs × 120s)
# Usage: bash tools/run_baseline.sh
# Output: results/kpis_baseline_*.json + results/baseline_summary.md
set +e  # don't exit on error — launch_r2k.sh may return non-zero on watchdog kill

cd "$(dirname "$0")/.."  # cd to core/src/
CORE_DIR="$(cd .. && pwd)"  # core/ (where launch_r2k.sh lives)
SCENARIOS="3vs3_attack_center 3vs3_attack_wing 3vs3_defensive_crisis \
           3vs3_fast_counter 3vs3_pressing_trap 3vs3_long_shot \
           3vs3_contain_delay 3vs3_def_transition 3vs3_high_line"
RUNS=3
DURATION=120
RESULTS_DIR="$(pwd)/results"
mkdir -p "$RESULTS_DIR"

echo "=========================================================="
echo "🚀 Phase 2e: 27-Run Baseline"
echo "   9 scenarios × $RUNS runs × ${DURATION}s = 27 runs (~45min)"
echo "=========================================================="
echo ""

START_TIME=$(date +%s)
TOTAL=0
PASS=0

for scenario in $SCENARIOS; do
    for run in $(seq 1 $RUNS); do
        TOTAL=$((TOTAL + 1))
        ELAPSED=$(($(date +%s) - START_TIME))
        echo "[$TOTAL/27] (${ELAPSED}s elapsed) $scenario run $run..."

        LOG_FILE="$RESULTS_DIR/baseline_${scenario}_r${run}.log"
        # Restart container between runs (teardown does docker compose down).
        export PROJECT_NAME="core"
        export COMPOSE_PROJECT_NAME="core"
        (cd "$RESULTS_DIR/../.." && docker compose -f src/docker-compose.yml up -d) 2>/dev/null || true; sleep 3
        # Run launch_r2k.sh from core/ (where it expects to be run).
        cd "$CORE_DIR"
        ./launch_r2k.sh --headless --duration $DURATION \
            --scenario "$scenario" \
            --strategy strat_aggro \
            --relay only_sim_bots --no-explain > "$LOG_FILE" 2>&1
        cd "$(dirname "$0")/.."  # back to core/src/

        RUN_ID=$(grep -oP 'Run ID: \K\S+' "$LOG_FILE" 2>/dev/null || echo "")
        if [ -z "$RUN_ID" ]; then
            echo "  ❌ No Run ID found — skipping KPI extraction"
            continue
        fi

        KPI_FILE="$RESULTS_DIR/kpis_baseline_${scenario}_r${run}.json"
        python3 tools/analyze_trace.py --run-id "$RUN_ID" \
            --output "$RESULTS_DIR/kpis_baseline_${scenario}_r${run}" 2>/dev/null && \
            mv "$RESULTS_DIR/kpis_baseline_${scenario}_r${run}/kpis_${RUN_ID}.json" "$KPI_FILE" 2>/dev/null && \
            rm -rf "$RESULTS_DIR/kpis_baseline_${scenario}_r${run}" || true

        if [ -f "$KPI_FILE" ]; then
            PASS=$((PASS + 1))
            echo "  ✅ KPIs saved: $KPI_FILE"
        else
            echo "  ⚠️ KPI file not found at $KPI_FILE"
        fi
    done
done

ELAPSED=$(($(date +%s) - START_TIME))
echo ""
echo "=========================================================="
echo "✅ Baseline complete: $PASS/$TOTAL runs produced KPIs (${ELAPSED}s)"
echo "=========================================================="

# Generate summary
python3 -c "
import json, glob, os
from collections import defaultdict

results_dir = '$RESULTS_DIR'
kpi_files = sorted(glob.glob(os.path.join(results_dir, 'kpis_baseline_*.json')))
print(f'Found {len(kpi_files)} KPI files')

by_scenario = defaultdict(list)
for f in kpi_files:
    # Extract scenario name from filename: kpis_baseline_<scenario>_r<N>.json
    base = os.path.basename(f).replace('kpis_baseline_', '').replace('.json', '')
    parts = base.rsplit('_r', 1)
    scenario = parts[0] if len(parts) == 2 else base
    with open(f) as fh:
        data = json.load(fh)
    by_scenario[scenario].append(data)

print()
print('| Scenario | Runs | Goals B:R | Composite | OOB% | Cluster% | Goalie Idle% | Tac Score Avg | Possession% | Latency p50 |')
print('|----------|------|-----------|-----------|------|----------|-------------|---------------|-------------|-------------|')

for scenario in sorted(by_scenario.keys()):
    runs = by_scenario[scenario]
    n = len(runs)
    goals_b = sum(r.get('world_kpis',{}).get('goals_for_blue',0) for r in runs)
    goals_r = sum(r.get('world_kpis',{}).get('goals_for_red',0) for r in runs)
    composites = []
    oobs = []
    clusters = []
    goalies = []
    tacs = []
    poss = []
    lats = []
    for r in runs:
        w = r.get('world_kpis',{})
        l = r.get('llm_kpis',{})
        gd = w.get('goals_for_blue',0) - w.get('goals_for_red',0)
        ts = w.get('tactical_score_avg',-10)
        ps = w.get('ball_possession_blue_pct',0)
        lt = l.get('latency_p50',3000)
        comp = 0.4*max(0,min(1,gd/10)) + 0.3*max(0,min(1,(ts+10)/20)) + 0.2*max(0,min(1,ps/100)) + 0.1*max(0,1-lt/3000)
        composites.append(comp)
        oobs.append(w.get('oob_pct',0))
        clusters.append(w.get('cluster_pct',0))
        goalies.append(w.get('goalie_idle_pct',0))
        tacs.append(w.get('tactical_score_avg',0))
        poss.append(w.get('ball_possession_blue_pct',0))
        lats.append(l.get('latency_p50',0))

    avg = lambda x: round(sum(x)/len(x), 2) if x else 0
    print(f'| {scenario} | {n} | {goals_b}:{goals_r} | {avg(composites)} | {avg(oobs)}% | {avg(clusters)}% | {avg(goalies)}% | {avg(tacs)} | {avg(poss)}% | {avg(lats)}ms |')

print()
print('Summary saved to $RESULTS_DIR/baseline_summary.md')
" 2>&1 | tee "$RESULTS_DIR/baseline_summary.md"