# Experiment Matrix — Phase 2 LLM Steering Study

> Bottom-up prompt engineering study for Qwen2.5-Coder:3b.
> Each experiment changes ONE variable, runs 3× 120s, measured against baseline A.

## Research Questions

- **RQ1** — Rules vs. samples: which carries more steering signal for a 3B model?
- **RQ2** — Sample-count plateau: where does adding samples stop helping?
- **RQ3** — Are there structurally different approaches that outperform rules+samples?

## Setup

- **Scenario**: `3vs3_attack_center` (baseline kickoff, even formation)
- **Strategy**: `strat_default`
- **Opponent**: Team red (rule-based, static `rule_evaluator_red.py`)
- **Duration**: 120s per run, 3 repeats per experiment
- **Model**: `qwen2.5-coder:3b`, temperature 0.0, num_ctx 4096

## KPIs

| KPI | Description | Source |
|-----|-------------|--------|
| goals_for_blue | Goals scored by blue (LLM) | world_trace |
| goals_for_red | Goals scored by red (rules) | world_trace |
| tactical_score_avg | Mean average_numerical_score | world_trace |
| tactical_score_final | Last current_numerical_score | world_trace |
| cluster_pct | % frames with 2+ blue bots < 0.5m apart | world_trace |
| goalie_idle_pct | % frames goalie moved < 0.05m | world_trace |
| oob_pct | % frames a blue bot was out of bounds | world_trace |
| ball_possession_blue_pct | % frames closest bot to ball is blue | world_trace |
| latency_p50/p95/max | LLM response latency | llm_trace |
| parse_error_rate | % LLM calls with parse errors | llm_trace |
| role_diversity | Distinct role strings assigned | llm_trace |

## Results

### Baseline A — strat_default, --no-explain (3 samples, current rules)

| Run | Goals B:R | Tac Avg | Tac Final | Cluster% | Goalie Idle% | OOB% | Poss% | Lat p50 | Lat p95 | Parse Err | Roles |
|-----|-----------|---------|-----------|----------|--------------|------|-------|---------|---------|-----------|-------|
| A1  |           |         |           |          |              |      |       |         |         |           |       |
| A2  |           |         |           |          |              |      |       |         |         |           |       |
| A3  |           |         |           |          |              |      |       |         |         |           |       |
| **mean** | | | | | | | | | | | |

### B1 — +2 anti-clustering samples (attacking third)

**Variable**: Added 2 anti-clustering samples near opponent goal to `samples_3vs3.txt`
**Question**: Do more samples fix clustering better than the rule on `rules_3vs3.txt:4`?

| Run | Goals B:R | Tac Avg | Tac Final | Cluster% | Goalie Idle% | OOB% | Poss% | Lat p50 | Lat p95 | Parse Err | Roles |
|-----|-----------|---------|-----------|----------|--------------|------|-------|---------|---------|-----------|-------|
| B1_r1 | | | | | | | | | | | |
| B1_r2 | | | | | | | | | | | |
| B1_r3 | | | | | | | | | | | |
| **mean** | | | | | | | | | | | |

### B2 — Remove "Do not cluster" rule, keep B1 samples

**Variable**: Removed "Do not cluster" from `rules_3vs3.txt`, kept B1's 5 samples
**Question**: Is the rule or the sample doing the work? (RQ1)

| Run | Goals B:R | Tac Avg | Tac Final | Cluster% | Goalie Idle% | OOB% | Poss% | Lat p50 | Lat p95 | Parse Err | Roles |
|-----|-----------|---------|-----------|----------|--------------|------|-------|---------|---------|-----------|-------|
| B2_r1 | | | | | | | | | | | |
| B2_r2 | | | | | | | | | | | |
| B2_r3 | | | | | | | | | | | |
| **mean** | | | | | | | | | | | |

### B3 — Feed match_state to LLM + 1 goal-kick restart sample

**Variable**: `r2k_evaluator.py:87` includes match_state in min_ents + 1 goal-kick restart sample
**Question**: Does game-state awareness improve restart behavior?

| Run | Goals B:R | Tac Avg | Tac Final | Cluster% | Goalie Idle% | OOB% | Poss% | Lat p50 | Lat p95 | Parse Err | Roles |
|-----|-----------|---------|-----------|----------|--------------|------|-------|---------|---------|-----------|-------|
| B3_r1 | | | | | | | | | | | |
| B3_r2 | | | | | | | | | | | |
| B3_r3 | | | | | | | | | | | |
| **mean** | | | | | | | | | | | |

### B4a — Goalie x=-4.0 everywhere

**Variable**: Fixed `samples_3vs3.txt` Example 1 goalie x from -4.5 to -4.0
**Question**: Which goalie constant concedes fewer goals?

| Run | Goals B:R | Tac Avg | Tac Final | Cluster% | Goalie Idle% | OOB% | Poss% | Lat p50 | Lat p95 | Parse Err | Roles |
|-----|-----------|---------|-----------|----------|--------------|------|-------|---------|---------|-----------|-------|
| B4a_r1 | | | | | | | | | | | |
| B4a_r2 | | | | | | | | | | | |
| B4a_r3 | | | | | | | | | | | |
| **mean** | | | | | | | | | | | |

### B4b — Goalie x=-4.5 everywhere

**Variable**: Fixed `rules_core.txt:21` goalie x from -4.0 to -4.5
**Question**: (complement of B4a)

| Run | Goals B:R | Tac Avg | Tac Final | Cluster% | Goalie Idle% | OOB% | Poss% | Lat p50 | Lat p95 | Parse Err | Roles |
|-----|-----------|---------|-----------|----------|--------------|------|-------|---------|---------|-----------|-------|
| B4b_r1 | | | | | | | | | | | |
| B4b_r2 | | | | | | | | | | | |
| B4b_r3 | | | | | | | | | | | |
| **mean** | | | | | | | | | | | |

### B5 — --explain (600 tokens)

**Variable**: `--explain` flag (600 token cap, includes analysis+oracle keys)
**Question**: Is reasoning worth the latency cost?

| Run | Goals B:R | Tac Avg | Tac Final | Cluster% | Goalie Idle% | OOB% | Poss% | Lat p50 | Lat p95 | Parse Err | Roles |
|-----|-----------|---------|-----------|----------|--------------|------|-------|---------|---------|-----------|-------|
| B5_r1 | | | | | | | | | | | |
| B5_r2 | | | | | | | | | | | |
| B5_r3 | | | | | | | | | | | |
| **mean** | | | | | | | | | | | |

### B6a — 1 sample only

**Variable**: Only Example 1 in `samples_3vs3.txt` (dropped examples 2+3)
**Question**: Sample-count plateau (RQ2)

| Run | Goals B:R | Tac Avg | Tac Final | Cluster% | Goalie Idle% | OOB% | Poss% | Lat p50 | Lat p95 | Parse Err | Roles |
|-----|-----------|---------|-----------|----------|--------------|------|-------|---------|---------|-----------|-------|
| B6a_r1 | | | | | | | | | | | |
| B6a_r2 | | | | | | | | | | | |
| B6a_r3 | | | | | | | | | | | |
| **mean** | | | | | | | | | | | |

### B6b — 6 samples

**Variable**: 6 samples in `samples_3vs3.txt` (baseline 3 + 3 new)
**Question**: Sample-count plateau (RQ2)

| Run | Goals B:R | Tac Avg | Tac Final | Cluster% | Goalie Idle% | OOB% | Poss% | Lat p50 | Lat p95 | Parse Err | Roles |
|-----|-----------|---------|-----------|----------|--------------|------|-------|---------|---------|-----------|-------|
| B6b_r1 | | | | | | | | | | | |
| B6b_r2 | | | | | | | | | | | |
| B6b_r3 | | | | | | | | | | | |
| **mean** | | | | | | | | | | | |

### B7a — Rules-only, zero samples

**Variable**: Empty `samples_3vs3.txt` (rules only, no few-shot)
**Question**: Rules vs. samples signal strength (RQ1)

| Run | Goals B:R | Tac Avg | Tac Final | Cluster% | Goalie Idle% | OOB% | Poss% | Lat p50 | Lat p95 | Parse Err | Roles |
|-----|-----------|---------|-----------|----------|--------------|------|-------|---------|---------|-----------|-------|
| B7a_r1 | | | | | | | | | | | |
| B7a_r2 | | | | | | | | | | | |
| B7a_r3 | | | | | | | | | | | |
| **mean** | | | | | | | | | | | |

### B7b — Samples-only, empty rules_3vs3

**Variable**: Empty `rules_3vs3.txt` (samples only, `rules_core.txt` still present)
**Question**: (complement of B7a)

| Run | Goals B:R | Tac Avg | Tac Final | Cluster% | Goalie Idle% | OOB% | Poss% | Lat p50 | Lat p95 | Parse Err | Roles |
|-----|-----------|---------|-----------|----------|--------------|------|-------|---------|---------|-----------|-------|
| B7b_r1 | | | | | | | | | | | |
| B7b_r2 | | | | | | | | | | | |
| B7b_r3 | | | | | | | | | | | |
| **mean** | | | | | | | | | | | |

## Conclusions

(To be filled after all experiments complete)

### RQ1: Rules vs. samples
- B7a (rules-only) vs B7b (samples-only) vs A (both): ...

### RQ2: Sample-count plateau
- B6a (1) vs A (3) vs B6b (6): ...

### RQ3: Alternatives
- B5 (explain mode) vs A: ...
- B3 (match_state awareness) vs A: ...