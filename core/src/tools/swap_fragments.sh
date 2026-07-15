#!/bin/bash
# swap_fragments.sh — swap experiment fragments into strategy/fragments/, run a match, restore.
#
# Usage:
#   ./tools/swap_fragments.sh <experiment_dir> <run_label> [duration]
#   ./tools/swap_fragments.sh experiments/B1 B1_r1 120
#
# This script:
#   1. Copies the experiment's fragments/ into strategy/fragments/
#   2. Dumps the assembled prompt to results/<run_label>_prompt.txt
#   3. Runs launch_r2k.sh --headless --duration <N>
#   4. Runs analyze_trace.py and saves KPIs to results/<run_label>.json
#   5. Restores the baseline fragments
#
# Requires: R2K_RUN_ID is set by launch_r2k.sh automatically.

set -e

EXPERIMENT_DIR="$1"
RUN_LABEL="$2"
DURATION="${3:-120}"
SCENARIO="${4:-3vs3_attack_center}"
STRATEGY="${5:-strat_default}"
EXPLAIN_FLAG="${6:---no-explain}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC_DIR="$(dirname "$SCRIPT_DIR")"
BASELINE_DIR="$SRC_DIR/experiments/baseline"
FRAGMENTS_DIR="$SRC_DIR/strategy/fragments"

if [ -z "$EXPERIMENT_DIR" ] || [ -z "$RUN_LABEL" ]; then
    echo "Usage: $0 <experiment_dir> <run_label> [duration] [scenario] [strategy] [explain_flag]"
    echo "Example: $0 experiments/B1 B1_r1 120 3vs3_attack_center strat_default --no-explain"
    exit 1
fi

# Resolve absolute path
EXPERIMENT_DIR="$(cd "$EXPERIMENT_DIR" && pwd)"
EXPERIMENT_FRAGMENTS="$EXPERIMENT_DIR/fragments"

if [ ! -d "$EXPERIMENT_FRAGMENTS" ]; then
    echo "ERROR: $EXPERIMENT_FRAGMENTS not found"
    exit 1
fi

echo "=========================================================="
echo "EXPERIMENT: $RUN_LABEL"
echo "  Experiment dir: $EXPERIMENT_DIR"
echo "  Duration:       ${DURATION}s"
echo "  Scenario:       $SCENARIO"
echo "  Strategy:       $STRATEGY"
echo "  Explain:        $EXPLAIN_FLAG"
echo "=========================================================="

# Step 1: Swap experiment fragments in
echo ">>> Swapping experiment fragments into strategy/fragments/..."
cp "$EXPERIMENT_FRAGMENTS"/* "$FRAGMENTS_DIR/"

# Step 2: Dump the assembled prompt for reproducibility
echo ">>> Dumping assembled prompt..."
cd "$SRC_DIR"
python3 tools/dump_prompt.py --scenario "$SCENARIO" --strategy "$STRATEGY" $EXPLAIN_FLAG > "results/${RUN_LABEL}_prompt.txt" 2>&1 || true

# Step 3: Run the match
echo ">>> Launching match..."
cd "$SRC_DIR/.."
./launch_r2k.sh --headless --duration "$DURATION" --scenario "$SCENARIO" --strategy "$STRATEGY" $EXPLAIN_FLAG 2>&1 | tee "src/results/${RUN_LABEL}_console.log"

# Extract run ID from the console output
RUN_ID=$(grep -oP 'Run ID: \K\S+' "src/results/${RUN_LABEL}_console.log" | head -1)
if [ -z "$RUN_ID" ]; then
    echo "WARNING: Could not extract R2K_RUN_ID from console log. Trying latest log files..."
    RUN_ID=$(ls -t src/logs/llm_trace_*.jsonl 2>/dev/null | head -1 | sed 's/.*llm_trace_//;s/.jsonl//')
fi

echo ">>> Run ID: $RUN_ID"

# Step 4: Analyze traces
echo ">>> Analyzing traces..."
cd "$SRC_DIR"
if [ -n "$RUN_ID" ] && [ -f "logs/llm_trace_${RUN_ID}.jsonl" ]; then
    python3 tools/analyze_trace.py --run-id "$RUN_ID" --output results/ 2>&1 | tee "results/${RUN_LABEL}_summary.txt"
else
    echo "ERROR: No trace files found for run ID '$RUN_ID'"
    echo "  Looking for: logs/llm_trace_${RUN_ID}.jsonl"
fi

# Step 5: Restore baseline fragments
echo ">>> Restoring baseline fragments..."
cp "$BASELINE_DIR"/* "$FRAGMENTS_DIR/"
echo "=========================================================="
echo "EXPERIMENT COMPLETE: $RUN_LABEL"
echo "  Results: results/${RUN_LABEL}_prompt.txt"
echo "           results/${RUN_LABEL}_console.log"
echo "           results/${RUN_LABEL}_summary.txt"
echo "           results/kpis_${RUN_ID}.json"
echo "=========================================================="