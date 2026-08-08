#!/bin/bash
# T3: Run 33 empirical scenarios x 8s Gazebo headless, sequential.
# Generates world_trace files for score-chart regeneration.
set -e
cd /home/r-zwei-kickers/R2K-HSL/core

SCENARIOS=$(ls -d src/scenario/emp_*/ | sed 's|src/scenario/||;s|/||' | sort)
TOTAL=$(echo "$SCENARIOS" | wc -l)
COUNT=0
FAILED=""
LOG=/tmp/t3_batch.log

echo "=== T3: $TOTAL empirical scenarios x 8s Gazebo (sequential) ==="
echo "Start: $(date)"
echo ""

for SCEN in $SCENARIOS; do
    COUNT=$((COUNT + 1))
    echo -n "[$COUNT/$TOTAL] $SCEN ... "
    
    if ./launch_r2k.sh --headless --duration 8 --scenario "$SCEN" --relay only_sim_bots > "$LOG" 2>&1; then
        echo "OK"
    else
        echo "FAIL"
        FAILED="$FAILED $SCEN"
    fi
    
    # Verify world_trace was produced
    TRACE=$(ls -t src/logs/world_trace_${SCEN}_*.jsonl 2>/dev/null | head -1)
    if [ -z "$TRACE" ]; then
        echo "  WARNING: no world_trace produced"
    fi
done

echo ""
echo "=== T3 Complete: $(date) ==="
echo "Total: $TOTAL | Failed:${FAILED:- none}"
if [ -n "$FAILED" ]; then
    echo "Failed scenarios:$FAILED"
fi
