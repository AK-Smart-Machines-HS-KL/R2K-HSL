---
id: 7_03
title: "Tools & Utils: Experimentation Infrastructure"
type: CHEATPAGE
tags: [tools, utils, analyze-trace, dump-prompt, swap-fragments, run-experiment, batch-evaluator, r2k-run-id, headless, v6, v6.1, v6.2]
last_modified: 2026-07-15
version: v6.2
---
# Tools & Utils: Experimentation Infrastructure

> [!info] Human Summary
> The `tools/` directory contains the experimentation and measurement infrastructure
> built in v6.1. These scripts let you inspect prompts, run experiments, measure KPIs,
> and orchestrate batch evaluations — all without manual data collection.

> [!abstract] LLM Context Anchor
> All tools are offline (no ROS 2, no Ollama needed for inspection) or semi-online
> (launch `launch_r2k.sh` as subprocess). The `R2K_RUN_ID` env var is the correlation
> key that links trace files, KPI JSONs, and console logs across the pipeline.

---

## 1. Tool Inventory

| Tool | Type | Needs ROS? | Needs Ollama? | Purpose |
|------|------|-----------|---------------|---------|
| `tools/dump_prompt.py` | Offline inspector | No | No | Assemble and print prompt fragments |
| `tools/analyze_trace.py` | Offline analyzer | No | No | Compute 15 KPIs from trace files |
| `tools/swap_fragments.sh` | Experiment helper | No (swap) / Yes (run) | Yes (run) | Swap experiment fragments, run, restore |
| `tools/run_experiment.sh` | Experiment runner | Yes | Yes | Run 3 repeats with auto-analysis |
| `ai_tactics/batch_evaluator.py` | Batch orchestrator (deprecated) | Yes | Yes | Replaced by `test_non_functional.py` (§6.5) |
| `tests/test_non_functional.py` | Regression suite | Yes | Yes | Two-tier pytest: slow tests assert per-scenario KPI thresholds |

All tools live in `core/src/tools/` except `batch_evaluator.py` which is in
`core/src/ai_tactics/`.

---

## 2. `dump_prompt.py` — Dry-Run Prompt Inspector

Assembles prompt fragments identically to `setup_r2k.py` but prints to stdout instead
of writing `system_prompt.txt`. Use this to verify prompt changes before launching a
match.

**Usage:**
```bash
cd core/src
python3 tools/dump_prompt.py --scenario 3vs3_attack_center --strategy strat_default --no-explain
python3 tools/dump_prompt.py --scenario 2vs2_default --strategy strat_aggro --explain
python3 tools/dump_prompt.py --fragments-dir experiments/B6a/fragments --scenario 3vs3_attack_center --strategy strat_default --no-explain
```

**Output:**
- Full assembled prompt (ready to copy-paste into an LLM for testing)
- Per-fragment breakdown (filename, line count, char count)
- Token estimate (approximate)
- Fragment override info (which strategy-specific file replaced which mode file)

> [!tip] Use `--fragments-dir` to inspect experiment-specific prompts without swapping files.

---

## 3. `analyze_trace.py` — Offline KPI Analyzer

> [!example] What does a typical experiment look like?
> You change one variable (e.g. swap `samples_3vs3.txt` to use only 1 sample instead of 3),
> run 3 × 120s matches headless, then analyze the trace files. The KPI JSON tells you:
>
> - **Did blue score more?** `goals_for_blue` vs `goals_for_red` — if blue went from 0.7 to
>   1.7 goals per game, the change helped.
> - **Are bots still leaving the field?** `oob_pct` — if it dropped from 30% to 16%, the
>   STAY INSIDE rule is working.
> - **Are bots still clumping?** `cluster_pct` — if it dropped from 15% to 2.6%, the
>   single-sample change improved spacing.
> - **Did the LLM get slower?** `latency_p50` — if it dropped from 827ms to 742ms, fewer
>   tokens = faster inference.
> - **Is the LLM producing valid JSON?** `parse_error_rate` — if it's 0%, the prompt format
>   is clean. If it spikes, the sample format is broken.
> - **What roles does the LLM assign?** `roles` — if you see `{"striker": 155, "goalie":
>   155, "supporter": 128}`, the LLM is consistently assigning all three roles. If
>   `role_diversity` drops to 1, the LLM is stuck in a degenerate pattern.
> - **How much of the game was interrupted?** `status_distribution` — if `foul_penalty`
>   appears in 59 of 1299 frames, fouls are happening regularly. If `ball_out` appears in
>   150 frames, the ball is leaving the field often.
>
> **The insight you get:** By comparing KPIs across experiments (e.g. B6a 1-sample vs
> baseline A 3-sample), you learn which prompt variables matter and which don't. The
> B-study showed that 1 sample (B6a) produced the best scorer (1.7 goals/game) and the
> lowest latency (742ms) — a counterintuitive finding that more samples ≠ better behavior
> for a 3B model.

Reads `llm_trace` and `world_trace` JSONL files for a given run ID, joins them by
timestamp, and computes 14 KPIs.

**Usage:**
```bash
cd core/src
python3 tools/analyze_trace.py --run-id 3vs3_attack_center_strat_default_20260715_122720
python3 tools/analyze_trace.py --run-id <ID> --output results/kpis_<ID>.json
python3 tools/analyze_trace.py --run-id <ID> --plot   # generates latency histogram + score timeline
```

**Prerequisite:** The run must have produced trace files in `logs/`. The `--run-id`
must match the `R2K_RUN_ID` env var from the run.

**Output (JSON):**
```json
{
  "run_id": "3vs3_attack_center_strat_default_20260715_122720",
  "world_kpis": {
    "goals_for_blue": 0,
    "goals_for_red": 2,
    "cluster_pct": 2.1,
    "goalie_idle_pct": 95.9,
    "oob_pct": 32.1,
    "ball_possession_blue_pct": 50.0,
    "tactical_score_avg": -2.23,
    "tactical_score_final": -3.9,
    "status_distribution": {"playing": 892, "foul_penalty": 59, "ball_out": 150, "goal": 100}
  },
  "llm_kpis": {
    "llm_calls": 155,
    "latency_p50": 828,
    "latency_p95": 872,
    "parse_error_rate": 0.0,
    "role_diversity": 4,
    "roles": {"goalie": 155, "striker": 155, "supporter": 128, "midfielder": 27},
    "avg_response_tokens": 76
  }
}
```

### 3.1 KPI Reference

**World KPIs** (from `world_trace`):

| KPI | Calculation | Good |
|-----|-------------|-----|
| `goals_for_blue/red` | Score delta count | blue > red |
| `cluster_pct` | % frames min pairwise blue distance < 1.5m | < 10% |
| `goalie_idle_pct` | % frames goalie moved < 0.1m | < 80% (structural limit) |
| `goalie_tactical_pct` | % frames goalie in tactically useful position (V6.2 Phase 2a) | >= 60% |
| `oob_pct` | % frames any blue bot > 0.5m outside bounds | < 10% |
| `ball_possession_blue_pct` | % frames closest bot to ball is blue | > 50% |
| `tactical_score_avg` | Mean `average_numerical_score` | > -1.0 |
| `tactical_score_final` | Last `current_numerical_score` | > -2.0 |
| `status_distribution` | Counter of `match_state.status` | — |
| `duration_s` | Time span first→last record | — |

**LLM KPIs** (from `llm_trace`):

| KPI | Calculation | Good |
|-----|-------------|-----|
| `latency_p50` | 50th percentile latency | < 1000ms |
| `latency_p95` | 95th percentile | < 2000ms |
| `parse_error_rate` | % calls with `parse_code > 0` | < 5% |
| `role_diversity` | Distinct role strings | > 2 |
| `roles` | Counter of role names | — |
| `avg_response_tokens` | Mean `len(raw_response) / 4` | < 100 |

---

## 4. `swap_fragments.sh` — Experiment Fragment Swapper

Copies an experiment's `fragments/` directory into `strategy/fragments/`, runs a
match, then restores the baseline fragments. Used for single-variable prompt
experiments.

**Usage:**
```bash
cd core/src
bash tools/swap_fragments.sh experiments/B6a B6a_r1 120 3vs3_attack_center strat_default --no-explain
```

**Arguments:** `<experiment_dir> <run_label> [duration] [scenario] [strategy] [explain_flag]`

**Flow:**
1. Backup current `strategy/fragments/` → `strategy/fragments.backup/`
2. Copy experiment's `fragments/` → `strategy/fragments/`
3. Run `dump_prompt.py` → save to `results/<run_label>_prompt.txt`
4. Run `launch_r2k.sh --headless --duration N`
5. Run `analyze_trace.py` → save to `results/kpis_<run_id>.json`
6. Restore baseline fragments

---

## 5. `run_experiment.sh` — Experiment Runner (3 Repeats)

Runs an experiment 3 times with auto-analysis. For baseline runs (no fragment swap),
use directly; for fragment experiments, delegates to `swap_fragments.sh`.

**Usage:**
```bash
cd core/src
# Baseline run (current fragments):
bash tools/run_experiment.sh A baseline 120 3vs3_attack_center strat_default --no-explain

# Fragment experiment:
bash tools/run_experiment.sh B6a experiments/B6a 120 3vs3_attack_center strat_default --no-explain

# With extra env var (e.g. match_state injection):
bash tools/run_experiment.sh B3 experiments/B3 120 3vs3_attack_center strat_default --no-explain "R2K_INCLUDE_MATCH_STATE=1"
```

**Arguments:** `<exp_name> <exp_dir> [duration] [scenario] [strategy] [explain_flag] [extra_env]`

**Output:** 3 KPI JSON files in `results/`, 3 console logs, 3 prompt dumps.

---

## 6. `batch_evaluator.py` — Headless Batch Orchestrator

Runs multiple match configurations sequentially. Currently broken (KPI collection
TODO — see v6.2 Phase 2b).

**Usage:**
```bash
cd core/src
python3 ai_tactics/batch_evaluator.py \
    --scenarios 3vs3_attack_center,3vs3_defensive_crisis \
    --strategies strat_default \
    --models qwen2.5-coder:3b \
    --runs 3 \
    --duration 120 \
    --output eval_results_baseline_v6.2.json
```

**CLI flags:**

| Flag | Default | Description |
|------|---------|-------------|
| `--scenarios` | required | Comma-separated scenario names |
| `--strategies` | required | Comma-separated strategy names |
| `--models` | required | Comma-separated Ollama model names |
| `--runs` | 5 | Runs per configuration |
| `--duration` | 60 | Seconds per run |
| `--output` | auto | Output filename (default: `eval_results_<timestamp>.json`) |

> [!warning] Deprecated in v6.2 — replaced by `test_non_functional.py`
> `batch_evaluator.py:91` has `# TODO: Subscribe to ROS topics during run`. The KPI
> collection was never implemented. The file is deprecated in v6.2 — replaced by
> `tests/test_non_functional.py` (shared regression suite, §6.5 below). The CLI
> and schema above document the intended structure for reference.

---

## 6.5. `test_non_functional.py` — Shared Regression Suite (Phase 2b)

The shared regression suite runs real headless Gazebo matches and asserts per-scenario
KPI thresholds. It replaces the deprecated `batch_evaluator.py`.

> [!info] What is a pytest marker?
> A pytest marker is a label you attach to a test function to categorize it.
> It's metadata — it doesn't change what the test does, but lets you select,
> skip, or filter tests by their markers.
>
> Example:
> ```python
> @pytest.mark.slow
> def test_attack_center_performance():
>     ...
> ```
>
> `@pytest.mark.slow` tags the function with `slow`. The marker is registered
> in `pytest.ini`:
> ```ini
> [pytest]
> markers =
>     slow: marks tests as slow (run real Gazebo matches, ~140s each)
> ```
>
> Then `--skip-slow` (implemented in `conftest.py`) reads that marker and skips
> all tests carrying it. That's the entire two-tier mechanism — a marker is
> pure metadata for selection and filtering, not a test condition or assertion.

### Two-Tier Test System

| Tier | Command | What runs | Time |
|------|---------|----------|------|
| **Fast** | `pytest tests/ --skip-slow` | 91 unit tests (rule logic, parsing, set-piece math) | ~2s |
| **Slow** | `pytest tests/ -v -s` | 91 unit + slow tests (real 120s Gazebo matches) | ~10min |

* Run **fast** after every code change (~2s feedback loop).
* Run **slow** before commit (~10min, catches regressions).
* Single slow test: `pytest tests/test_non_functional.py::test_attack_center_latency -v -s`

### Composite Score Formula (spec §5.2)

```
composite = 0.4 * goal_diff_norm + 0.3 * tac_score_norm
          + 0.2 * possession_norm + 0.1 * latency_factor

where:
  goal_diff_norm   = clamp((goals_for_blue - goals_for_red) / 10, 0, 1)
  tac_score_norm    = clamp((tactical_score_avg + 10) / 20, 0, 1)
  possession_norm   = ball_possession_blue_pct / 100
  latency_factor    = max(0, 1 - latency_p50 / 3000)
```

* Range: [0, 1]. Higher is better.
* Computed by `compute_composite()` in `test_non_functional.py`.

### Per-Scenario `kpi_targets.json`

Each scenario package (`scenario/<name>/`) contains a `kpi_targets.json` with
acceptable KPI ranges:

```json
{
  "scenario_name": "3vs3_attack_center",
  "composite_score": { "min": 0.4, "max": 1.0, "note": "baseline scenario" },
  "oob_pct": { "min": 0.0, "max": 10.0, "note": "STAY INSIDE rule" },
  "cluster_pct": { "min": 0.0, "max": 10.0, "note": "anti-clustering samples" },
  "goalie_idle_pct": { "min": 0.0, "max": 70.0, "note": "after Phase 2a fix" },
  "latency_p50": { "min": 0, "max": 1000, "note": "qwen2.5-coder:3b on GPU" },
  "ball_possession_blue_pct": { "min": 40.0, "max": 100.0, "note": "even scenario" },
  "goals_for_blue": { "min": 0, "max": 10, "note": "directional, high variance" }
}
```

The test asserts each KPI is within its scenario's `[min, max]` range. Thresholds
are calibrated from the 27-run baseline (Phase 2e, not yet run — current values
are estimates from the spec).

### Current Test Scenarios

* `3vs3_attack_center` — baseline midfield (TC-01). Tests composite, OOB, cluster, goalie, latency.
* `3vs3_default` — same positions, legacy v5 filename. Tests composite, OOB, cluster, goalie.
* Phase 2f will add the 3 worst-performing scenarios from the baseline.

### `goalie_tactical_pct` KPI (Phase 2a, new in v6.2)

Distinguishes "goalie is tactically positioning" from "goalie is stuck." Ball far
from goal → goalie should be forward (angle-block). Ball near → goalie near goal
line + tracking Y. The test asserts `goalie_tactical_pct >= 60%`.

---

## 7. `R2K_RUN_ID` — Run Correlation Key

`launch_r2k.sh:82` exports:
```bash
export R2K_RUN_ID="${SCENARIO}_${STRATEGY}_$(date +%Y%m%d_%H%M%S)"
```

This env var propagates to:
- `r2k_evaluator.py` → names `llm_trace_<run_id>.jsonl`
- `state_aggregator.py` → names `world_trace_<run_id>.jsonl`
- Docker containers via `docker exec -e R2K_RUN_ID=...`
- Console log: `📋 Run ID: <ID>  (logs: src/logs/*_<ID>.jsonl)`

**If unset:** both nodes fall back to `run_{timestamp}` — trace files won't be
correlatable with the run's console log.

**Finding the run ID after a run:**
```bash
# From the console log:
grep "Run ID:" results/<run_label>_console.log

# Or from the trace file names:
ls logs/*_3vs3_attack_center_strat_default_*.jsonl
```

---

## 8. File Locations

| Directory | Contents | Gitignored? |
|-----------|----------|-------------|
| `src/tools/` | Tool scripts | No |
| `src/results/` | KPI JSONs, console logs, prompt dumps | No |
| `src/logs/` | Trace JSONL files | **Yes** |
| `src/experiments/` | Experiment fragment directories | No |
| `src/strategy/fragments/` | Active prompt fragments | No |
| `src/shared_state/` | Runtime state (Worldstate.json, current_strategy.json) | No (scaffolding) |

---

## 9. Related Documentation

| Topic | Document |
|-------|----------|
| Step-by-step experiment guide | [[7_05_CHEATPAGE_Experiment_Guide]] |
| Prompt architecture | [[7_04_SPECIFICATION_Prompt_Architecture]] |
| CLI flags | [[6_03_CHEATPAGE_CLI_Ergonomics]] |
| Data schemas (trace files) | [[6_01_SPECIFICATION_Data_Schemas]] |
| RAG: Tools & trace logging | `ros2k_knowledge/6_DATA_SCHEMAS_AND_LIFECYCLE.md` §V6.1 Addendum |