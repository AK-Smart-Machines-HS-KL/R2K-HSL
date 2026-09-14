#!/bin/bash
# overnight_regression.sh — full regression + match battery + behavior analysis
# (2026-09-13, budget: over night). Produces a markdown report under
# docs/reference/benchmarks/ and per-run KPI JSONs under src/results/kpis_<run_id>/.
#
# Usage:  nohup ./tools/overnight_regression.sh > /tmp/opencode/overnight.log 2>&1 &
set -u
CORE=$(cd "$(dirname "$0")/.." && pwd)
SRC="$CORE/src"
STAMP=$(date +%Y%m%d_%H%M%S)
REPORT="$CORE/docs/reference/benchmarks/overnight_$STAMP.md"
BRANCH=$(git -C "$CORE" rev-parse --abbrev-ref HEAD 2>/dev/null)
SHA=$(git -C "$CORE" rev-parse --short HEAD 2>/dev/null)

sec() { echo; echo "## $1"; }
hr()  { echo; echo '---'; }

echo "# Overnight regression report — $STAMP" > "$REPORT"
echo "*Host: $(hostname) — branch: ${BRANCH:-?} @ ${SHA:-?}* — scenario focus: 3vs3_default" >> "$REPORT"

# ---------------------------------------------------------------- 0. teardown
sec "0. Teardown (clean slate)"
pkill -9 -f "r2k_evaluator|ollama_sandbox_bridge|gzserver|gzclient" 2>/dev/null
docker compose -f "$SRC/docker-compose.yml" down -t 5 2>/dev/null | tail -1
docker rm -f uros_agent 2>/dev/null | tail -1
sleep 3
echo "teardown done (Ollama left running: $(curl -s -m 2 http://localhost:11434/api/tags >/dev/null && echo yes || echo NO))"
echo "(Ollama status: $(curl -s -m 2 http://localhost:11434/api/tags >/dev/null && echo up || echo DOWN))" >> "$REPORT"

# ---------------------------------------------------------------- 1. fast tier
sec "1. Fast tier"
cd "$SRC"
FAST_OUT=$(python3 -m pytest tests/ --skip-slow -q \
  --ignore=tests/test_adaptive_horizon.py \
  --ignore=tests/test_chart_specs.py 2>&1 | tail -3)
echo '```' >> "$REPORT"; echo "$FAST_OUT" >> "$REPORT"; echo '```' >> "$REPORT"
echo "$FAST_OUT"

# ---------------------------------------------------------------- 2. battery
sec "2. Sim battery"
cd "$CORE"
BAT_OUT=$(python3 -c "
import sys; sys.path.insert(0, 'tools')
import calib_test
ok, total, _ = calib_test.run_sim_battery()
print(f'{ok}/{total}')" 2>&1 | tail -1)
echo "SIM BATTERY: $BAT_OUT" | tee -a "$REPORT"

# ---------------------------------------------------------------- 3. slow tier
sec "3. Slow tier (test_non_functional — real 120s matches, KPI assertions)"
cd "$SRC"
SLOW_OUT=$(python3 -m pytest tests/test_non_functional.py -v 2>&1 | grep -E "PASSED|FAILED|ERROR|SKIPPED|passed|failed" | tail -20)
echo '```' >> "$REPORT"; echo "$SLOW_OUT" >> "$REPORT"; echo '```' >> "$REPORT"
echo "$SLOW_OUT"

# ---------------------------------------------------------------- 4. match battery
sec "4. 3vs3_default match battery (4 × 120 s headless) + behavior analysis"
MATCH_ANALYSIS="$REPORT"
for i in 1 2 3 4; do
  echo "=== match $i/4 ==="
  LAUNCH_OUT=$(cd "$CORE" && timeout 300 ./launch_r2k.sh --scenario 3vs3_default --relay sim_only --headless --duration 120 2>&1)
  RUN_ID=$(echo "$LAUNCH_OUT" | grep "Run ID:" | head -1 | sed 's/.*Run ID://; s/[[:space:]].*//' | tr -d '[:space:]')
  if [ -z "$RUN_ID" ]; then
    echo "  RUN $i: LAUNCH FAILED (no Run ID)" | tee -a "$MATCH_ANALYSIS"
    echo '```' >> "$MATCH_ANALYSIS"; echo "${LAUNCH_OUT: -800}" >> "$MATCH_ANALYSIS"; echo '```' >> "$MATCH_ANALYSIS"
    continue
  fi
  sleep 3   # let trace flush
  KPI_DIR="$SRC/results/kpis_$RUN_ID"
  python3 "$SRC/tools/analyze_trace.py" --run-id "$RUN_ID" --output "$KPI_DIR" >/dev/null 2>&1
  echo "  RUN $i: $RUN_ID"
  # per-run KPI extract (the headline numbers)
  KPI_JSON=$(ls "$KPI_DIR"/*.json 2>/dev/null | head -1)
  if [ -n "$KPI_JSON" ]; then
    python3 - "$KPI_JSON" << 'PYEOF' | tee -a "$MATCH_ANALYSIS"
import json, sys
d = json.load(open(sys.argv[1]))
def g(k): return d.get(k, 'n/a')
print(f"  KPIs: possession {g('ball_possession_blue_pct')}% | cluster {g('cluster_pct')}% | "
      f"goalie_tactical {g('goalie_tactical_pct')}% | oob {g('oob_pct')}% | "
      f"shots {g('shots_on_goal')}/{g('shots_on_target')} | goals {g('goals_for_blue')} | "
      f"composite {g('composite_score')}")
PYEOF
  fi
  # kick-target + goalie-wander analysis (not an analyze_trace KPI)
  LLMF="$SRC/logs/llm_trace_3vs3_default_strat_aggro_$RUN_ID.jsonl"
  WTF="$SRC/logs/world_trace_3vs3_default_strat_aggro_$RUN_ID.jsonl"
  python3 - "$LLMF" "$WTF" << 'PYEOF' | tee -a "$MATCH_ANALYSIS"
import json, re, sys, math
from collections import Counter
llm, wt = sys.argv[1], sys.argv[2]
try:
    recs = [json.loads(l) for l in open(llm)]
except FileNotFoundError:
    print("  (no llm trace)"); sys.exit()
kt = Counter(); kicks = 0; goalie_x = []
try:
    wrecs = [json.loads(l) for l in open(wt)]
    for r in wrecs:
        e = r.get('entities', {})
        b = e.get('blue_1')
        if b: goalie_x.append(abs(b['x']))
except FileNotFoundError:
    wrecs = []
for r in recs:
    for m in re.finditer(r'\{[^{}]*"action":\s*"Kick"[^{}]*\}', r.get('raw_response','')):
        kicks += 1
        t = re.search(r'"target_x":\s*([-\d.]+)', m.group(0))
        if t:
            x = float(t.group(1))
            kt['goal-side' if x > 2 else 'center' if x > -2 else 'own-side'] += 1
        else:
            kt['no-target'] += 1
print(f"  kicks {kicks}: {dict(kt)}")
if goalie_x:
    print(f"  goalie |x| range {min(goalie_x):.2f}..{max(goalie_x):.2f} m "
          f"(wander <2m: {sum(1 for x in goalie_x if x < 2)/len(goalie_x)*100:.0f}% of samples)")
PYEOF
  # teardown between matches (the launcher auto-tears down after --duration,
  # but be explicit to avoid port races)
  pkill -9 -f "r2k_evaluator|ollama_sandbox_bridge|gzserver" 2>/dev/null
  docker compose -f "$SRC/docker-compose.yml" down -t 5 2>/dev/null | tail -1 >/dev/null
  sleep 5
done

hr
echo "# End of report — $(date +%H:%M:%S)" >> "$REPORT"
echo "REPORT: $REPORT"
