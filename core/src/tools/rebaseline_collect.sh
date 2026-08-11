#!/bin/bash
# Throwaway measurement harness — Phase 2 baseline data collection.
# Runs 3 matches per scenario for 5 slow-suite scenarios, collects KPIs.
# Usage: bash tools/rebaseline_collect.sh
# Output: results/v65_rebaseline_raw.json + results/kpis_<run_id>/*.json
set -euo pipefail
CORE_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
SRC_DIR="$CORE_DIR/src"
cd "$CORE_DIR"

SCENARIOS=("3vs3_attack_center" "3vs3_default" "3vs3_high_line" "3vs3_long_shot" "3vs3_contain_delay")
RUNS_PER_SCENARIO=3
DURATION=120
RAW_JSON="$SRC_DIR/results/v65_rebaseline_raw.json"
PYTHON=${PYTHON:-python3}

echo "[" > "$RAW_JSON"
FIRST_ENTRY=1

for scenario in "${SCENARIOS[@]}"; do
  echo "=========================================="
  echo "Scenario: $scenario (${RUNS_PER_SCENARIO} runs x ${DURATION}s)"
  echo "=========================================="
  for run in $(seq 1 $RUNS_PER_SCENARIO); do
    echo "--- Run $run/$RUNS_PER_SCENARIO ---"
    LOG_FILE="$SRC_DIR/results/rebaseline_${scenario}_run${run}.log"
    # Run match headless
    ./launch_r2k.sh --scenario "$scenario" --relay only_sim_bots --headless --duration "$DURATION" > "$LOG_FILE" 2>&1 || {
      echo "FAIL: launch_r2k.sh exited non-zero for $scenario run $run"
      continue
    }
    # Extract run ID
    run_id=$(grep "Run ID:" "$LOG_FILE" | head -1 | sed 's/.*Run ID: //' | awk '{print $1}')
    if [ -z "$run_id" ]; then
      echo "FAIL: no Run ID found in $LOG_FILE"
      continue
    fi
    echo "Run ID: $run_id"
    # Analyze trace
    out_dir="$SRC_DIR/results/kpis_${run_id}"
    mkdir -p "$out_dir"
    $PYTHON "$SRC_DIR/tools/analyze_trace.py" --run-id "$run_id" --output "$out_dir" > "$out_dir/analyze.log" 2>&1 || {
      echo "FAIL: analyze_trace.py for $run_id"
      continue
    }
    kpi_file=$(ls "$out_dir"/*.json 2>/dev/null | head -1)
    if [ -z "$kpi_file" ]; then
      echo "FAIL: no KPI json in $out_dir"
      continue
    fi
    echo "KPIs: $kpi_file"
    # Append to raw json (merge world_kpis + llm_kpis + scenario + run_id)
    $PYTHON -c "
import json, sys
with open('$kpi_file') as f:
    d = json.load(f)
merged = {**d.get('world_kpis', {}), **d.get('llm_kpis', {})}
merged['_scenario'] = '$scenario'
merged['_run_id'] = '$run_id'
merged['_run'] = $run
print(json.dumps(merged))
" >> "$RAW_JSON"
    # Trailing comma handling
    if [ "$FIRST_ENTRY" = "1" ]; then
      FIRST_ENTRY=0
    fi
    echo "," >> "$RAW_JSON"
    echo "OK: $scenario run $run complete"
  done
done

# Finalize JSON (remove last trailing comma, close array)
sed -i '/^,$/{ # if line is exactly ","
  $d       # delete if last line
}' "$RAW_JSON"
echo "]" >> "$RAW_JSON"
echo ""
echo "=========================================="
echo "Phase 2 complete. Raw data: $RAW_JSON"
echo "=========================================="
$PYTHON -c "
import json
with open('$RAW_JSON') as f:
    raw = f.read()
# Fix trailing comma before ]
raw = raw.replace(',\n]', '\n]').replace(',]', ']')
data = json.loads(raw)
from collections import defaultdict
by_scn = defaultdict(list)
for d in data:
    by_scn[d['_scenario']].append(d)
print(f'Total samples: {len(data)}')
for scn, runs in sorted(by_scn.items()):
    print(f'  {scn}: {len(runs)} runs')
"