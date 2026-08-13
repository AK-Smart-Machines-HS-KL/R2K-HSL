#!/bin/bash
# Ensemble batch runner: start Gazebo once, warp-and-resume for all 17 hand-crafted.
#
# Usage:
#   bash tools/ensemble_batch.sh
#   bash tools/ensemble_batch.sh --scenario 3vs3_attack_center  # single scenario
#   bash tools/ensemble_batch.sh --runs 3 --duration 4
#
# Saves ~75% time vs full Gazebo restart per run (85 runs × 25s → 8.5 min).
set -e
cd /home/r-zwei-kickers/R2K-HSL/core

RUNS=5
DURATION=4
SINGLE_SCEN=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --scenario) SINGLE_SCEN="$2"; shift 2 ;;
        --runs) RUNS="$2"; shift 2 ;;
        --duration) DURATION="$2"; shift 2 ;;
        *) echo "Unknown arg: $1"; exit 1 ;;
    esac
done

# Get all 17 hand-crafted scenario names
SCENARIOS=$(ls -d src/scenario/*/ 2>/dev/null | sed 's|src/scenario/||;s|/$||' | grep -vE "^emp_" | sort)

if [ -n "$SINGLE_SCEN" ]; then
    SCENARIOS="$SINGLE_SCEN"
fi

TOTAL=$(echo "$SCENARIOS" | wc -l)
echo "=== Ensemble batch: $TOTAL scenarios × $RUNS runs × ${DURATION}s ==="
echo "Start: $(date)"
echo ""

# Start Gazebo once (no --duration, will be managed by warp_and_run.py)
FIRST_SCEN=$(echo "$SCENARIOS" | head -1)
echo "=== Starting Gazebo with $FIRST_SCEN ==="
./launch_r2k.sh --headless --scenario "$FIRST_SCEN" --relay only_sim_bots &
LAUNCH_PID=$!

# Wait for Gazebo to be ready (nodes started)
echo "Waiting for Gazebo startup..."
sleep 20

# Check if launch is still running
if ! kill -0 $LAUNCH_PID 2>/dev/null; then
    echo "ERROR: launch_r2k.sh died during startup"
    exit 1
fi

echo "Gazebo is running. Starting warp-and-resume runs..."
echo ""

COUNT=0
for SCEN in $SCENARIOS; do
    COUNT=$((COUNT + 1))
    echo "[$COUNT/$TOTAL] $SCEN"
    
    # Run warp_and_run.py inside the Docker container (where ROS2 is available)
    docker exec core_gazebo bash -c "
        source /opt/ros/humble/setup.bash && 
        source /workspace/ros2_ws/install/setup.bash 2>/dev/null &&
        cd /workspace &&
        python3 tools/warp_and_run.py --scenario '$SCEN' --runs $RUNS --duration $DURATION
    " 2>&1 | grep -E "Run|Done|Warping|ERROR|complete" || echo "  (see log for details)"
    echo ""
done

echo "=== Shutting down Gazebo ==="
kill -TERM $LAUNCH_PID 2>/dev/null
sleep 3
kill -9 $LAUNCH_PID 2>/dev/null

echo "=== Complete: $(date) ==="
echo "Total: $TOTAL scenarios × $RUNS runs = $((TOTAL * RUNS)) matches"