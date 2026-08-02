#!/bin/bash
# run_baselines.sh — Solid baselines for C3 evaluation
# Runs C1 (enrich) and C1+C9 (enrich+predict) on all 9 scenarios
# n=17 per scenario per config = 306 runs total (~12h)
#
# Usage: setsid bash tools/run_baselines.sh > results/baselines.log 2>&1 &

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC_DIR="$(dirname "$SCRIPT_DIR")"
CORE_DIR="$(cd "$SRC_DIR/.." && pwd)"

SCENARIOS=(
  3vs3_attack_center
  3vs3_attack_wing
  3vs3_contain_delay
  3vs3_def_transition
  3vs3_defensive_crisis
  3vs3_fast_counter
  3vs3_high_line
  3vs3_long_shot
  3vs3_pressing_trap
)

N=17
TOTAL=$(( ${#SCENARIOS[@]} * N * 2 ))
COMPLETED=0

echo "=========================================================="
echo "Solid Baselines for C3 Evaluation"
echo "  Configs: C1 (enrich) + C1+C9 (enrich+predict)"
echo "  Scenarios: ${#SCENARIOS[@]}"
echo "  Runs per scenario per config: $N"
echo "  Total runs: $TOTAL"
echo "  Estimated time: ~12h"
echo "  Started: $(date)"
echo "=========================================================="

for scenario in "${SCENARIOS[@]}"; do
  # --- C1: Enrichment only ---
  echo ""
  echo "[$((COMPLETED+1))/$TOTAL] C1: $scenario (n=$N)"
  export R2K_ENRICH_STATE=1
  unset R2K_PREDICT_HORIZON_MS
  for run in $(seq 1 $N); do
    LABEL="C1_${scenario}_r${run}"
    bash "$SCRIPT_DIR/run_c_series.sh" "$LABEL" "$LABEL" 1 "$scenario" 2>/dev/null
    COMPLETED=$((COMPLETED + 1))
    echo "  [${COMPLETED}/${TOTAL}] ${LABEL} done"
  done
  unset R2K_ENRICH_STATE

  # --- C1+C9: Enrichment + Prediction ---
  echo "[$((COMPLETED+1))/$TOTAL] C1+C9: $scenario (n=$N)"
  export R2K_ENRICH_STATE=1
  export R2K_PREDICT_HORIZON_MS=746
  for run in $(seq 1 $N); do
    LABEL="C1C9_${scenario}_r${run}"
    bash "$SCRIPT_DIR/run_c_series.sh" "$LABEL" "$LABEL" 1 "$scenario" 2>/dev/null
    COMPLETED=$((COMPLETED + 1))
    echo "  [${COMPLETED}/${TOTAL}] ${LABEL} done"
  done
  unset R2K_ENRICH_STATE
  unset R2K_PREDICT_HORIZON_MS
done

echo ""
echo "=========================================================="
echo "ALL BASELINES COMPLETE"
echo "  Total runs: $COMPLETED"
echo "  Finished: $(date)"
echo "=========================================================="
