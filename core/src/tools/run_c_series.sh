#!/bin/bash
# run_c_series.sh — run N repeats of a single scenario for C-series experiments
# Usage: bash tools/run_c_series.sh <exp_name> <prefix> <runs> [scenario] [fragments_dir]
#   exp_name: experiment label (C6_current, C6_3sample, C1, C5, etc.)
#   prefix: KPI output prefix
#   runs: number of repeats
#   scenario: scenario name (default: 3vs3_attack_center)
#   fragments_dir: if set, swap fragments from this dir before running
set +e

EXP_NAME="$1"
PREFIX="$2"
RUNS="${3:-5}"
SCENARIO="${4:-3vs3_attack_center}"
FRAGMENTS_DIR="${5:-}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC_DIR="$(dirname "$SCRIPT_DIR")"
CORE_DIR="$(cd "$SRC_DIR/.." && pwd)"
RESULTS_DIR="$SRC_DIR/results"
CONTAINER_NAME="core_gazebo"
FRAGMENTS_PATH="$SRC_DIR/strategy/fragments"
BACKUP_DIR="$SRC_DIR/.fragments_backup"

echo "=========================================================="
echo "C-SERIES: $EXP_NAME ($RUNS runs × $SCENARIO)"
echo "Prefix: $PREFIX"
[ -n "$FRAGMENTS_DIR" ] && echo "Fragments: $FRAGMENTS_DIR"
echo "=========================================================="

# Swap fragments if requested
if [ -n "$FRAGMENTS_DIR" ]; then
    if [ ! -d "$FRAGMENTS_DIR" ]; then
        echo "ERROR: fragments dir not found: $FRAGMENTS_DIR"
        exit 1
    fi
    echo "Swapping fragments from $FRAGMENTS_DIR..."
    mkdir -p "$BACKUP_DIR"
    cp "$FRAGMENTS_PATH"/*.txt "$BACKUP_DIR/" 2>/dev/null
    cp "$FRAGMENTS_DIR"/*.txt "$FRAGMENTS_PATH/" 2>/dev/null
fi

START_TIME=$(date +%s)
TOTAL=0

wait_for_container() {
    local max_wait=60
    local waited=0
    while docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^${CONTAINER_NAME}$"; do
        if [ $waited -ge 15 ]; then
            (cd "$CORE_DIR" && docker compose -f src/docker-compose.yml down) 2>/dev/null
            sleep 2
            break
        fi
        sleep 1
        waited=$((waited + 1))
    done
    (cd "$CORE_DIR" && docker compose -f src/docker-compose.yml up -d) 2>/dev/null || true
    waited=0
    while [ $waited -lt $max_wait ]; do
        if docker exec "$CONTAINER_NAME" bash -c "source /opt/ros/humble/setup.bash && ros2 topic list >/dev/null 2>&1" 2>/dev/null; then
            return 0
        fi
        sleep 1
        waited=$((waited + 1))
    done
    return 1
}

for run in $(seq 1 $RUNS); do
    TOTAL=$((TOTAL + 1))
    ELAPSED=$(($(date +%s) - START_TIME))
    echo "[$TOTAL/$RUNS] (${ELAPSED}s elapsed) run $run..."

    export PROJECT_NAME="core"
    export COMPOSE_PROJECT_NAME="core"
    if ! wait_for_container; then
        echo "  ❌ Container not ready — skipping run"
        continue
    fi
    cd "$CORE_DIR"
    ./launch_r2k.sh --headless --duration 120 --scenario "$SCENARIO" --strategy strat_aggro --relay only_sim_bots --no-explain 2>/dev/null
    cd "$SRC_DIR"

    # Analyze the latest trace
    LATEST=$(ls -t logs/world_trace_${SCENARIO}_strat_aggro_*.jsonl 2>/dev/null | head -1)
    if [ -n "$LATEST" ]; then
        RID=$(echo "$LATEST" | sed 's/logs\/world_trace_//;s/.jsonl//')
        python3 tools/analyze_trace.py --run-id "$RID" --output "$RESULTS_DIR" >/dev/null 2>&1
        # Rename to add prefix
        if [ -f "$RESULTS_DIR/kpis_${RID}.json" ]; then
            mv "$RESULTS_DIR/kpis_${RID}.json" "$RESULTS_DIR/kpis_${PREFIX}_r${run}.json"
            echo "  ✅ kpis_${PREFIX}_r${run}.json"
        fi
    else
        echo "  ❌ No trace file found"
    fi
done

# Restore fragments if swapped
if [ -n "$FRAGMENTS_DIR" ] && [ -d "$BACKUP_DIR" ]; then
    echo "Restoring original fragments..."
    cp "$BACKUP_DIR"/*.txt "$FRAGMENTS_PATH/" 2>/dev/null
    rm -rf "$BACKUP_DIR"
fi

ELAPSED=$(($(date +%s) - START_TIME))
echo "=========================================================="
echo "DONE: $EXP_NAME — $RUNS runs in ${ELAPSED}s"
echo "Output: results/kpis_${PREFIX}_r*.json"
echo "=========================================================="
