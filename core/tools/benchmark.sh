#!/bin/bash
# General-purpose benchmark harness for ROS2K soccer matches.
# Runs N Gazebo matches per scenario, extracts KPIs via analyze_trace.py,
# outputs consolidated JSON. Supersedes rebaseline_collect.sh.
#
# Usage:
#   bash tools/benchmark.sh --model qwen2.5:3b --runs 10 --tag pre_v7
#   bash tools/benchmark.sh --model qwen2.5:3b --runs 3 --scenarios 5 --tag quick
#   bash tools/benchmark.sh --help

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CORE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SRC_DIR="$CORE_DIR/src"
LAUNCH="$CORE_DIR/launch_r2k.sh"
RESULTS_DIR="$SRC_DIR/results"
ANALYZE="$SRC_DIR/tools/analyze_trace.py"

mkdir -p "$RESULTS_DIR"

# Defaults
MODEL="${R2K_OLLAMA_MODEL:-qwen2.5:3b}"
RUNS=10
DURATION=120
SCENARIOS="all"
TAG="benchmark"
NO_WARM=0
RANDOM_DRAW=0
SCENARIO_LIST=(
    3vs3_default 3vs3_attack_center 3vs3_attack_wing 3vs3_defensive_crisis
    3vs3_def_transition 3vs3_fast_counter 3vs3_high_line 3vs3_overload
    3vs3_pressing_trap 3vs3_wing_switch
)

usage() {
    cat <<EOF
Usage: $0 [OPTIONS]

Options:
  --model MODEL        Ollama model name (default: qwen2.5:3b)
  --runs N             Runs per scenario (default: 10)
  --duration SECS      Match duration in seconds (default: 120)
  --scenarios N|all    Number of scenarios (default: all = ${#SCENARIO_LIST[@]})
  --tag TAG            Output tag (default: benchmark)
  --random             Random scenario draw per match (true random, no seed,
                       with replacement — counts per scenario will be uneven)
  --no-warm            Skip model warmup
  --help               Show this help
EOF
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --model) MODEL="$2"; shift 2 ;;
        --runs) RUNS="$2"; shift 2 ;;
        --duration) DURATION="$2"; shift 2 ;;
        --scenarios) SCENARIOS="$2"; shift 2 ;;
        --tag) TAG="$2"; shift 2 ;;
        --random) RANDOM_DRAW=1; shift ;;
        --no-warm) NO_WARM=1; shift ;;
        --help) usage ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

if [[ "$SCENARIOS" != "all" ]]; then
    N="$SCENARIOS"
    SCENARIO_LIST=("${SCENARIO_LIST[@]:0:N}")
fi

TOTAL=$((${#SCENARIO_LIST[@]} * RUNS))
RAW="$RESULTS_DIR/${TAG}_raw.json"

echo "=== R2K Benchmark ==="
echo "Model:      $MODEL"
echo "Scenarios:  ${#SCENARIO_LIST[@]} (${SCENARIO_LIST[*]})"
echo "Runs/scn:   $RUNS"
echo "Duration:   ${DURATION}s"
echo "Total:      $TOTAL matches"
echo "Output:     $RAW"
echo ""

# Warmup: load model into VRAM
if [[ "$NO_WARM" -eq 0 ]]; then
    echo -n "Warming up $MODEL... "
    curl -s -X POST http://127.0.0.1:11434/api/generate \
        -H "Content-Type: application/json" \
        -d "{\"model\":\"$MODEL\",\"prompt\":\"hello\",\"stream\":false,\"options\":{\"num_predict\":1}}" \
        -o /dev/null
    echo "done"
fi

echo "[" > "$RAW"
FIRST=1

play_match() {
    # Uses globals: scenario, run, MATCH_LABEL, RAW, FIRST
    echo ""
    echo ">>> [$MATCH_LABEL] $scenario <<<"

    # Capture the run_id from the launch output
    OUTPUT="$("$LAUNCH" --headless --duration "$DURATION" --scenario "$scenario" --relay only_sim_bots 2>&1)" || true
    RUN_ID=$(echo "$OUTPUT" | grep -oP 'Run ID:\s*\K[^\s]+' | head -1)
    if [[ -z "$RUN_ID" ]]; then
        RUN_ID=$(echo "$OUTPUT" | grep -oP 'R2K_RUN_ID=\K[^\s]+' | head -1)
    fi
    if [[ -z "$RUN_ID" ]]; then
        RUN_ID="${scenario}_strat_aggro_$(date +%Y%m%d_%H%M%S)"
    fi
    echo "  Run ID: $RUN_ID"

    # Extract KPIs — analyze_trace.py outputs a wrapper with nested
    # world_kpis + llm_kpis; merge them into a flat dict
    KPI_JSON=$(python3 "$ANALYZE" --run-id "$RUN_ID" 2>/dev/null || echo '{}')

    # Write to consolidated JSON
    if [[ $FIRST -eq 0 ]]; then
        echo "," >> "$RAW"
    fi
    FIRST=0
    RECORD=$(python3 -c "
import sys, json
try:
    raw = '''$KPI_JSON'''
    # analyze_trace may output multi-part JSON; parse first object
    decoder = json.JSONDecoder()
    idx = 0
    first = None
    while idx < len(raw):
        s = raw[idx:].lstrip()
        if not s: break
        idx = len(raw) - len(s)
        try:
            obj, end = decoder.raw_decode(raw, idx)
            if first is None: first = obj
            idx = end
        except:
            idx += 1
    d = {}
    if first:
        d = {**first.get('world_kpis', {}), **first.get('llm_kpis', {})}
    d['_scenario'] = '$scenario'
    d['_run'] = $run
    d['_tag'] = '$TAG'
    print(json.dumps(d))
except Exception as e:
    print(json.dumps({'_scenario': '$scenario', '_run': $run, '_error': str(e)[:80]}))
")
    echo -n "$RECORD" >> "$RAW"

    # Brief KPI summary
    echo "$KPI_JSON" | python3 -c "
import sys, json
try:
    raw = sys.stdin.read()
    decoder = json.JSONDecoder()
    idx = 0
    first = None
    while idx < len(raw):
        s = raw[idx:].lstrip()
        if not s: break
        idx = len(raw) - len(s)
        try:
            obj, end = decoder.raw_decode(raw, idx)
            if first is None: first = obj
            idx = end
        except:
            idx += 1
    d = {}
    if first:
        d = {**first.get('world_kpis', {}), **first.get('llm_kpis', {})}
    print(f'  goals: {d.get(\"goals_for_blue\",0)}B-{d.get(\"goals_for_red\",0)}R  '
          f'poss: {d.get(\"ball_possession_blue_pct\",0):.0f}%  '
          f'lat_p50: {d.get(\"latency_p50\",0)}ms  '
          f'goalie: {d.get(\"goalie_tactical_pct\",0):.0f}%  '
          f'pass: {d.get(\"pass_completion_pct\",0):.0f}%  '
          f'parse_err: {d.get(\"parse_error_rate\",0):.1f}%')
except: print('  (KPI extraction failed)')
"
}

if [[ "$RANDOM_DRAW" -eq 1 ]]; then
    POOL="${SCENARIO_LIST[*]}"
    echo "Mode:      RANDOM DRAW per match (true random, OS entropy, with replacement)"
    for ((m=1; m<=TOTAL; m++)); do
        scenario=$(python3 -c "import random; print(random.choice('$POOL'.split()))")
        run=$m
        MATCH_LABEL="match $m/$TOTAL random"
        play_match
    done
else
    for scenario in "${SCENARIO_LIST[@]}"; do
        for run in $(seq 1 "$RUNS"); do
            MATCH_LABEL="$scenario run $run/$RUNS"
            play_match
        done
    done
fi

echo "" >> "$RAW"
echo "]" >> "$RAW"

echo ""
echo "=== Benchmark complete: $TOTAL matches ==="
echo "Results: $RAW"
