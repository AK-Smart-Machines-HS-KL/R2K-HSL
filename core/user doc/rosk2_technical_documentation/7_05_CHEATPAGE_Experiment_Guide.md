---
id: 7_05
title: "Experiment Guide: How to Run and Measure"
type: CHEATPAGE
tags: [experiment, guide, howto, launch, analyze-trace, run-experiment, batch-evaluator, headless, v6, v6.1, v6.2]
last_modified: 2026-07-15
version: v6.2
---
# Experiment Guide: How to Run and Measure

> [!info] Human Summary
> Step-by-step guide for novice team members. Covers: running a single match, inspecting
> KPIs, running an experiment with 3 repeats, comparing results, and running a full batch.
> All commands assume you are in `core/src/` with the venv active (U22) or inside the
> Docker container (U24).

> [!abstract] LLM Context Anchor
> The measurement pipeline is: `launch_r2k.sh` (run) → trace files in `logs/` →
> `analyze_trace.py` (offline KPI computation) → KPI JSON in `results/`. The
> `R2K_RUN_ID` env var correlates everything.

---

## 1. Quick Start: Run a Single Match

```bash
cd core/src

# Run a 120s headless match with the consolidated v6.2 prompt:
./../launch_r2k.sh --headless --duration 120 \
    --scenario 3vs3_attack_center \
    --strategy strat_default \
    --relay only_sim_bots
```

**What happens:**
1. `launch_r2k.sh` exports `R2K_RUN_ID` (e.g. `3vs3_attack_center_strat_default_20260715_143022`)
2. `setup_r2k.py` assembles the prompt from `strategy/fragments/`
3. Gazebo starts in headless mode (`gzserver` only, no GUI)
4. All ROS 2 nodes boot (tracker, referee, score, reward, aggregator, bridge, evaluator)
5. Match runs for 120s, then auto-terminates
6. Console prints: `📋 Run ID: <ID>  (logs: src/logs/*_<ID>.jsonl)`

**Output files:**
- `logs/llm_trace_<run_id>.jsonl` — one line per LLM call
- `logs/world_trace_<run_id>.jsonl` — one line per 10Hz world-state write
- Console log (if redirected): contains the Run ID

> [!tip] With GUI (for debugging)
> Remove `--headless` to launch Gazebo with the visualizer. The visualizer shows
> bot positions, referee decisions, momentum chart, and AI analysis in real time.

---

## 2. Inspect KPIs

After the match finishes:

```bash
cd core/src

# Find the Run ID from the console output or trace file names:
ls logs/*_3vs3_attack_center_strat_default_*.jsonl

# Compute KPIs:
python3 tools/analyze_trace.py --run-id 3vs3_attack_center_strat_default_20260715_143022

# Save KPIs to a file:
python3 tools/analyze_trace.py --run-id <ID> --output results/kpis_<ID>.json
```

**Reading the output:**

```
WORLD KPIs:
  Duration:         129.8s (1299 frames)
  Goals:            Blue 0 : Red 2
  Cluster:          2.1%     ← good (< 10%)
  Goalie Idle:      95.9%   ← bad (structural, see 7_04 §5)
  OOB:              32.1%    ← bad (> 10%, bots leaving field)
  Possession:       50.0%   ← neutral
  Tac Score Avg:    -2.23   ← bad (negative = blue losing)
  Tac Score Final:  -3.9    ← bad

LLM KPIs:
  LLM Calls:        155
  Latency p50:      828ms   ← good (< 1000ms)
  Latency p95:      872ms   ← good (< 2000ms)
  Parse Errors:     0.0%    ← good (< 5%)
  Role Diversity:   4       ← good (> 2)
  Roles:            goalie:155, striker:155, supporter:128, midfielder:27
  Avg Tokens:       76      ← good (< 100)
```

**What to look for:**
- `OOB%` > 10%: bots leaving the field — check `rules_core.txt` for STAY INSIDE FIELD
- `Cluster%` > 10%: bots clumping — check anti-clustering rules
- `Goalie Idle%` > 80%: structural limit, NOT a prompt issue (see [[7_04_SPECIFICATION_Prompt_Architecture]] §5)
- `Parse Error%` > 5%: LLM producing invalid JSON — check sample format
- `Latency p50` > 1000ms: consider `--no-explain` or fewer samples

---

## 3. Run an Experiment (3 Repeats)

For controlled single-variable experiments:

```bash
cd core/src

# Baseline (current fragments, no swap):
bash tools/run_experiment.sh A baseline 120 3vs3_attack_center strat_default --no-explain

# Fragment experiment (swap fragments, run, restore):
bash tools/run_experiment.sh B6a experiments/B6a 120 3vs3_attack_center strat_default --no-explain

# With extra env var (e.g. match_state injection):
bash tools/run_experiment.sh B3 experiments/B3 120 3vs3_attack_center strat_default --no-explain "R2K_INCLUDE_MATCH_STATE=1"
```

**Arguments:** `<exp_name> <exp_dir> [duration] [scenario] [strategy] [explain_flag] [extra_env]`

**What happens (fragment experiment):**
1. Backup current `strategy/fragments/` → `strategy/fragments.backup/`
2. Copy experiment fragments → `strategy/fragments/`
3. Run `dump_prompt.py` → save to `results/B6a_r1_prompt.txt`
4. Run `launch_r2k.sh --headless --duration 120` → trace files in `logs/`
5. Run `analyze_trace.py` → save to `results/kpis_<run_id>.json`
6. Restore baseline fragments
7. Repeat 3× (r1, r2, r3)

**Output files per run:**
- `results/<exp>_r1_prompt.txt` — prompt dump
- `results/<exp>_r1_console.log` — console output
- `results/kpis_<run_id>.json` — KPIs

---

## 4. Compare KPIs Across Runs

```bash
cd core/src

# List all KPI files for an experiment:
ls results/kpis_*B6a*.json   # won't work — KPIs are named by run_id, not exp_name

# Better: find by timestamp range or console log:
grep "Run ID:" results/B6a_r*_console.log
# → Run ID: 3vs3_attack_center_strat_default_20260715_122720
# → Run ID: 3vs3_attack_center_strat_default_20260715_122943
# → Run ID: 3vs3_attack_center_strat_default_20260715_123207

# Print KPIs for each:
for id in $(grep -oP 'Run ID: \K\S+' results/B6a_r*_console.log); do
    echo "=== $id ==="
    python3 tools/analyze_trace.py --run-id "$id" 2>/dev/null | head -20
done
```

**Or read KPI JSONs directly:**
```bash
# Quick comparison of goals and OOB across all runs:
for f in results/kpis_*.json; do
    python3 -c "
import json, sys
d = json.load(open('$f'))
w = d['world_kpis']
print(f\"{d['run_id'][:40]:40s}  B{w['goals_for_blue']}:R{w['goals_for_red']}  OOB={w['oob_pct']}%  Clu={w['cluster_pct']}%  Lat={d['llm_kpis']['latency_p50']}ms\")
"
done
```

---

## 5. Run a Full Batch

> [!warning] batch_evaluator.py KPI collection is broken (v6.2 Phase 2b)
> The batch evaluator runs matches but doesn't yet collect KPIs. Use the manual
> approach below until Phase 2b is complete.

**Manual batch (works now):**
```bash
cd core/src

# Run 9 scenarios × 1 strategy × 3 runs = 27 runs:
for scenario in 3vs3_attack_center 3vs3_attack_wing 3vs3_defensive_crisis \
               3vs3_fast_counter 3vs3_pressing_trap 3vs3_long_shot \
               3vs3_contain_delay 3vs3_def_transition 3vs3_high_line; do
    for run in 1 2 3; do
        echo "=== $scenario run $run ==="
        ./../launch_r2k.sh --headless --duration 120 \
            --scenario "$scenario" \
            --strategy strat_default \
            --relay only_sim_bots 2>&1 | tee "results/baseline_${scenario}_r${run}.log"
        # Extract Run ID and compute KPIs:
        RUN_ID=$(grep -oP 'Run ID: \K\S+' "results/baseline_${scenario}_r${run}.log")
        python3 tools/analyze_trace.py --run-id "$RUN_ID" \
            --output "results/kpis_baseline_${scenario}_r${run}.json" 2>/dev/null
    done
done
```

**Batch evaluator (after Phase 2b fix):**
```bash
cd core/src
python3 ai_tactics/batch_evaluator.py \
    --scenarios 3vs3_attack_center,3vs3_defensive_crisis,3vs3_fast_counter \
    --strategies strat_default \
    --models qwen2.5-coder:3b \
    --runs 3 \
    --duration 120 \
    --output eval_results_baseline_v6.2.json
```

---

## 6. Where Files Go

| File | Location | Named by | Gitignored? |
|------|----------|---------|-------------|
| LLM trace | `src/logs/llm_trace_<run_id>.jsonl` | `R2K_RUN_ID` | Yes |
| World trace | `src/logs/world_trace_<run_id>.jsonl` | `R2K_RUN_ID` | Yes |
| KPI JSON | `src/results/kpis_<run_id>.json` | `R2K_RUN_ID` | No |
| Console log | `src/results/<label>_console.log` | experiment label | No |
| Prompt dump | `src/results/<label>_prompt.txt` | experiment label | No |
| Batch results | `src/results/eval_results_<name>.json` | `--output` flag | No |
| Runtime state | `src/shared_state/Worldstate.json` | fixed | No (scaffolding) |
| Active prompt | `src/ai_tactics/system_prompt.txt` | fixed (transient) | No (regenerated) |

> [!tip] Trace files accumulate
> `logs/` is NOT wiped on boot. Old trace files accumulate. Clean manually:
> `rm src/logs/*.jsonl`

---

## 7. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `No trace files found for run-id` | Wrong run ID or `logs/` empty | Check `ls logs/*.jsonl`, verify Run ID from console log |
| KPIs show 0 frames | Match didn't start (Gazebo failed) | Check console log for Gazebo errors |
| `FileNotFoundError: shared_state/` | Directory missing | `mkdir -p src/shared_state/` |
| OOB% = 100% | Bots spawned outside field | Check scenario JSON entity positions |
| Latency p50 > 2000ms | Ollama on CPU (Xid 31) or model too large | Check `nvidia-smi`, see [[5_04_CHEATPAGE_Nvidia_Xid31_Suspend_Bug]] |
| Parse error rate > 50% | Prompt format broken | Run `dump_prompt.py` to inspect |
| No goals in 120s | Normal for baseline (0.7:1.0 avg) | Try different scenario or strategy |

---

## 8. Related Documentation

| Topic | Document |
|-------|----------|
| Tools reference | [[7_03_CHEATPAGE_Tools_and_Utils]] |
| Prompt architecture | [[7_04_SPECIFICATION_Prompt_Architecture]] |
| CLI flags | [[6_03_CHEATPAGE_CLI_Ergonomics]] |
| Scoring & referee | [[7_01_INTRODUCTION_Scoring_Referee_Gamestate]] |
| World model | [[7_02_ARCHITECTURE_World_Model_Components]] |
| Optimization spec | `core/docs/optimization_spec_v6.2.md` |
| Experiment matrix (B-study) | `src/results/experiment_matrix.md` |