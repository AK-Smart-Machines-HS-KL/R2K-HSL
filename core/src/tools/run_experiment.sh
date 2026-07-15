#!/bin/bash
# run_experiment.sh — run a single experiment (3 repeats × 120s)
#
# Usage:
#   ./tools/run_experiment.sh <exp_name> <exp_dir> [duration] [scenario] [strategy] [explain_flag] [extra_env]
#
# Examples:
#   ./tools/run_experiment.sh A baseline 120 3vs3_attack_center strat_default --no-explain
#   ./tools/run_experiment.sh B3 experiments/B3 120 3vs3_attack_center strat_default --no-explain "R2K_INCLUDE_MATCH_STATE=1"

set -e

EXP_NAME="$1"
EXP_DIR="$2"
DURATION="${3:-120}"
SCENARIO="${4:-3vs3_attack_center}"
STRATEGY="${5:-strat_default}"
EXPLAIN_FLAG="${6:---no-explain}"
EXTRA_ENV="${7:-}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC_DIR="$(dirname "$SCRIPT_DIR")"

if [ -z "$EXP_NAME" ] || [ -z "$EXP_DIR" ]; then
    echo "Usage: $0 <exp_name> <exp_dir> [duration] [scenario] [strategy] [explain_flag] [extra_env]"
    exit 1
fi

echo ""
echo "############################################################"
echo "# EXPERIMENT: $EXP_NAME"
echo "# Duration: $DURATION s × 3 repeats"
echo "# Scenario: $SCENARIO  Strategy: $STRATEGY  $EXPLAIN_FLAG"
if [ -n "$EXTRA_ENV" ]; then echo "# Extra env: $EXTRA_ENV"; fi
echo "############################################################"

for rep in 1 2 3; do
    RUN_LABEL="${EXP_NAME}_r${rep}"
    echo ""
    echo ">>> Repeat $rep/3: $RUN_LABEL"

    # Apply extra env var if specified
    if [ -n "$EXTRA_ENV" ]; then
        export $EXTRA_ENV
    fi

    # Use swap_fragments.sh for fragment-based experiments,
    # or run directly for baseline (no fragment swap needed)
    if [ "$EXP_DIR" = "baseline" ] || [ "$EXP_DIR" = "experiments/baseline" ]; then
        # Baseline: run directly with current fragments (already restored)
        cd "$SRC_DIR"
        python3 tools/dump_prompt.py --scenario "$SCENARIO" --strategy "$STRATEGY" $EXPLAIN_FLAG > "results/${RUN_LABEL}_prompt.txt" 2>&1 || true
        cd "$SRC_DIR/.."
        ./launch_r2k.sh --headless --duration "$DURATION" --scenario "$SCENARIO" --strategy "$STRATEGY" $EXPLAIN_FLAG 2>&1 | tee "src/results/${RUN_LABEL}_console.log"
        RUN_ID=$(grep -oP 'Run ID: \K\S+' "src/results/${RUN_LABEL}_console.log" | head -1)
        if [ -n "$RUN_ID" ]; then
            cd "$SRC_DIR"
            python3 tools/analyze_trace.py --run-id "$RUN_ID" --output results/ 2>&1 | tee "results/${RUN_LABEL}_summary.txt"
        fi
    else
        # Experiment: swap fragments, run, restore
        cd "$SRC_DIR"
        bash tools/swap_fragments.sh "$EXP_DIR" "$RUN_LABEL" "$DURATION" "$SCENARIO" "$STRATEGY" "$EXPLAIN_FLAG"
    fi

    # Unset extra env
    if [ -n "$EXTRA_ENV" ]; then
        unset $(echo "$EXTRA_ENV" | cut -d= -f1)
    fi

    echo ">>> Repeat $rep complete: $RUN_LABEL"
done

echo ""
echo "############################################################"
echo "# EXPERIMENT $EXP_NAME COMPLETE (3 repeats)"
echo "############################################################"