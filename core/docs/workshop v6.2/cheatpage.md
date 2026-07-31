---
title: "ROS2K v6.3 Workshop — Cheat Page"
type: CHEATPAGE
tags: [workshop, cheatpage, reference, v6.2, v6.3, kpi, testing, scenarios]
last_modified: 2026-07-29
---

# ROS2K v6.3 — Student Cheat Page

> Print this page. It contains every command, KPI, and scenario you need
> during the workshop. All commands run from `~/R2K-HSL/core`.

---

## 1. Launch flags (`launch_r2k.sh`)

| Flag | Default | Explanation |
|------|---------|-------------|
| `--scenario <name>` | `2vs2_default` | Which match setup to load (bot positions, field). 17 scenarios available — see §4. |
| `--strategy <name>` | `strat_aggro` | Which prompt fragments the blue LLM uses. `strat_aggro` = pressing, `strat_default` = balanced, `strat_recover` = defensive. |
| `--model <name>` | `qwen2.5-coder:3b` | Ollama model. Must be pre-pulled (`ollama pull <name>`). Larger = smarter but slower. |
| `--relay <name>` | `only_sim_bots` | Hardware mapping. `only_sim_bots` = all Gazebo. `hardware_mirror` = real Yahboom + K1. |
| `--explain` | off | LLM outputs `analysis` + `oracle` + `assignments` (600 tokens). Good for debugging reasoning, but +44% latency. |
| `--no-explain` | on | LLM outputs ONLY `assignments` (150 tokens). Faster. Default for experiments. |
| `--headless` | off | Gazebo without GUI (`gzserver` only). ~30% faster. Use for batch experiments and automated runs. |
| `--duration <s>` | 0 (manual) | Auto-terminate after N seconds. `60` = quick test, `120` = B-study-compatible. 0 = run until CTRL+C or window close. |
| `--analyze` | off | Opens annotator terminal after container starts. Press ENTER to pause Gazebo, type a comment, ENTER to resume. Annotations saved for post-match replay. |

**Typical workshop command:**
```bash
./launch_r2k.sh --scenario 3vs3_attack_center --relay only_sim_bots
```

---

## 2. Testing (pytest)

Two-tier test system: **fast** (unit tests, ~2s) and **slow** (real 120s Gazebo
matches with KPI assertions, ~140s per test). 92 tests total (91 fast + 11 slow).

| Test file | Tests | What it covers |
|-----------|-------|----------------|
| `test_foul_detection.py` | 7 | Pushing (dist 0.3m, vel 0.5m/s), blocking (dist 0.5m, angle 30deg), hysteresis (N frames), ball proximity exemption, sideline Y range, foul cooldown |
| `test_integration_smoke.py` | 7 | End-to-end: scenario launches, momentum produces values, reward produces values, foul detection works, headless+duration, strategy files exist, launch script flags. **Skips if no ROS2.** |
| `test_kickoff_and_ballout.py` | 28 | Sideline warp (top/bottom), goal-line warp (blue/red), warp always inside field, kickoff scoring-team freeze (blue/red), ball reset to center, freeze time = 5s, no-toucher neutral restart, toucher penalty, pushing/blocking/ball-out penalty values, frozen bots get zero Twist, expired bots removed, goal detection (within posts, wide, edge, in-field) |
| `test_momentum.py` | 8 | OLS slope positive/negative, minimum samples (10), clamping ±10, flat scores, trend classification (ascending/collapsing) |
| `test_non_functional.py` | 11 (slow) | Real 120s Gazebo matches with per-scenario KPI assertions (composite score, OOB, cluster, goalie, attack KPIs). **Requires live ROS2 + Gazebo + Ollama.** `@pytest.mark.slow` marker. |
| `test_prompt_assembly.py` | 1 | Validates oracle/analysis fields in llm_trace are strings, not JSON dicts. |
| `test_referee.py` | 7 | Pushing foul, blocking without ball, no foul with ball, sideline warp, ball-out sideline, goal-line out (no goal), last-touch tracking |
| `test_reward.py` | 7 | Positive reward, negative reward (foul), 1Hz update rate, scale clamping ±10, neutral classification, foul penalty schema, decision timeout |
| `test_set_piece.py` | 27 | Goal kick ball placement (4 corners), corner kick-in placement (4 corners), goal-line out classification (attacker vs defender, blue vs red), no-toucher neutral fallback, warp radius (bot within 1.5m warped 2m radially), warp direction, kickoff/goal_kick/corner countdown = 5s, scoring team frozen, status types distinct |

### How to run tests

```bash
# Fast tier (unit tests only, ~2s) — run after every code change:
python3 -m pytest tests/ --skip-slow -v

# Full suite (unit + slow, ~21min) — run before commit:
python3 -m pytest tests/ -v -s

# Single slow test (real 120s Gazebo match + KPI assertions):
python3 -m pytest tests/test_non_functional.py::test_attack_center_latency -v -s

# Single unit test file:
python3 -m pytest tests/test_foul_detection.py -v -s
```

---

## 3. KPIs (18 metrics from `analyze_trace.py`)

`analyze_trace.py` joins `llm_trace` + `world_trace` by `R2K_RUN_ID` and
computes 18 KPIs. Run after a match:

```bash
python3 tools/analyze_trace.py --run-id <ID>
python3 tools/analyze_trace.py --run-id <ID> --output results/  # save JSON instead of stdout
```

| KPI | Source | Target | What it measures |
|-----|--------|--------|------------------|
| `goals_for_blue` | world_trace | > `goals_for_red` | Blue goals scored (score delta count) |
| `goals_for_red` | world_trace | < `goals_for_blue` | Red goals scored |
| `tactical_score_avg` | world_trace | > -1.0 | Mean `average_numerical_score` over the match |
| `tactical_score_final` | world_trace | > -2.0 | Last `current_numerical_score` (end-of-match state) |
| `cluster_pct` | world_trace | < 10% | % frames where min pairwise blue distance < 1.5m (bots bunching up) |
| `goalie_idle_pct` | world_trace | < 70% (after Phase 2a) | % frames goalie moved < 0.1m (currently ~95% — structural limit) |
| `goalie_tactical_pct` | world_trace | > 60% | % frames goalie is at a tactically correct position (vs stuck). Phase 2a KPI. |
| `oob_pct` | world_trace | < 10% | % frames any blue bot > 0.5m outside field bounds (out-of-bounds) |
| `ball_possession_blue_pct` | world_trace | > 50% | % frames where closest bot to ball is blue |
| `shots_on_goal` | llm+world | higher is better | Kick actions where kicker in opp half AND ball moves toward opp goal. Phase 2.5a. |
| `shots_on_target` | llm+world | higher is better | Subset of shots_on_goal where ball Y at x=4.5 is within goal posts (±1.3m). |
| `pass_completion_pct` | llm+world | higher is better | % Pass actions where a different blue bot is closest to ball within 2s. |
| `restart_recovery_time_s` | world_trace | < 4.0s | Mean time from status change to restart-team bot within 0.35m of ball. |
| `latency_p50` | llm_trace | < 1000ms | 50th percentile LLM response time (median). ~684ms with content-hash skip. |
| `latency_p95` | llm_trace | < 2000ms | 95th percentile (tail latency) |
| `latency_max` | llm_trace | — | Worst-case single LLM call (watch for cold-boot spikes) |
| `parse_error_rate` | llm_trace | < 5% | % LLM calls with `parse_code > 0` (malformed/truncated JSON) |
| `status_distribution` | world_trace | — | Counter of `match_state.status` values (playing, ball_out, kickoff, etc.) |

**Composite score** (weighted blend, single number for comparison):

```
composite = 0.4 × goal_diff_norm + 0.3 × tac_score_norm + 0.2 × possession + 0.1 × latency_factor
```

- `goal_diff_norm`: `(goals_blue - goals_red)` normalized to 0..1
- `tac_score_norm`: `tactical_score_avg` mapped from -10..+10 to 0..1
- `possession`: `ball_possession_blue_pct / 100`
- `latency_factor`: `max(0, 1 - latency_p50 / 2000)`

A composite of 0.5+ is a good run. Baseline (B-study A) was ~0.55.

---

## 4. Test scenarios (10 tactical scenarios)

Each scenario has a `scenario/{name}/` folder with `field_diagram.png`,
`analysis.md` (oracle + expert), and `kpi_targets.json`.

### Primary scenarios (3vs3)

| # | Scenario | Oracle (what blue should do) | Key KPI targets | What to watch |
|---|----------|------------------------------|-----------------|---------------|
| 1 | `3vs3_attack_center` | Exploit central gap between red bots. Quick central passing. | composite 0.4–1.0 · OOB <10% · cluster <10% · possession 40–100% | Role switches as ball moves. Goalie stays at X=-4.0. |
| 2 | `3vs3_attack_wing` | Drive down sideline, cross to center. Stretch red defense. | composite 0.35–1.0 · OOB <15% · cluster <12% | Sideline OOB — STAY INSIDE rule critical on wing. |
| 3 | `3vs3_contain_delay` | Zone-defend, block passing lanes. Force red into mistakes. | composite 0.3–0.75 · possession 25–70% · goals 0–5 | Defensive solidity. Low possession is expected. |
| 4 | `3vs3_defensive_crisis` | Emergency clear — kick ball away from own goal. Survive. | composite 0.25–0.8 · goalie_idle <60% · cluster <15% | Score volatility. Goalie should be very active. |
| 5 | `3vs3_def_transition` | Fall back, re-form defensive line, then counter-press. | composite 0.3–0.85 · cluster <15% · possession 30–80% | Role diversity spike (rapid role switching). Chaos. |
| 6 | `3vs3_fast_counter` | Exploit open space with speed. Push forward fast. | composite 0.4–1.0 · OOB <12% · possession 40–100% | Deep Move targets (X > 2.0). Minimal role switches. |
| 7 | `3vs3_high_line` | High defensive line, sweeper goalie. Compress the game. | composite 0.35–0.95 · goalie_idle <50% · possession 40–100% | Breakaways — if red gets behind, goalie must intercept. |
| 8 | `3vs3_long_shot` | Exploit distance — shoot when red goalie is out of position. | composite 0.35–0.9 · goals 0–8 | Kick assignments at X > 0.5, \|Y\| < 1.5. Low accuracy. |
| 9 | `3vs3_pressing_trap` | Escape the press. Maintain spacing, don't cluster. Short safe passes. | composite 0.3–0.8 · cluster <15% · OOB <15% | cluster_pct spike — if two bots converge, the press wins. |

### Secondary scenario (2vs2)

| # | Scenario | Oracle | Key KPI targets | What to watch |
|---|----------|--------|-----------------|---------------|
| 10 | `2vs2_default` | One attacks, one defends. Role clarity critical — no third bot to cover. | composite 0.35–0.9 · latency <800ms · cluster <15% | High role diversity (striker switches frequently). Simpler decision space — good for prompt iteration. |

### Running a specific scenario

```bash
# Quick 60s test
./launch_r2k.sh --headless --duration 60 --scenario 3vs3_pressing_trap --relay only_sim_bots

# Full match with visualizer
./launch_r2k.sh --scenario 3vs3_attack_center --relay only_sim_bots

# With reasoning output (for oracle/expert comparison)
./launch_r2k.sh --headless --duration 60 --scenario 3vs3_fast_counter --relay only_sim_bots --explain
```

---

## 5. Quick-test recipes

| What | Command |
|------|---------|
| Warm up Ollama (avoid dead blue team) | `curl -s http://127.0.0.1:11434/api/generate -d '{"model":"qwen2.5-coder:3b","prompt":"hi","stream":false}' > /dev/null` |
| 30s smoke test (headless) | `./launch_r2k.sh --headless --duration 30` |
| Full match with visualizer | `./launch_r2k.sh --scenario 3vs3_attack_center` |
| Inspect prompt without ROS | `python3 tools/dump_prompt.py --scenario 3vs3_attack_center --no-explain` |
| Analyze last run's KPIs | `python3 tools/analyze_trace.py --run-id <ID>` |
| Analyze + plots | `python3 tools/analyze_trace.py --run-id <ID> --plot` |
| Baseline experiment (3×120s) | `./tools/run_experiment.sh A baseline 120 3vs3_attack_center strat_default --no-explain` |
| Run all unit tests | `python3 -m pytest tests/ -v` |
| Run single test file | `python3 -m pytest tests/test_set_piece.py -v -s` |
| Check GPU + Ollama | `nvidia-smi` (look for ~2-4GB VRAM) |
| Find your run ID | `ls logs/llm_trace_*.jsonl` (filename = run ID) |

---

## 6. File locations (where things live)

| What | Path | Notes |
|------|------|-------|
| Launch script | `core/launch_r2k.sh` | Single entrypoint for all runs |
| Python nodes | `core/src/*.py` | referee, score, reward, aggregator, red, bridge, evaluator, visualizer |
| Prompt fragments | `core/src/strategy/fragments/*.txt` | Edit these — `setup_r2k.py` assembles them at boot |
| Scenarios (flat) | `core/src/scenario/*.json` | Bot positions, field setup |
| Scenario packages | `core/src/scenario/{name}/` | `scenario.json` + `field_diagram.png` + `analysis.md` + `kpi_targets.json` |
| Relay profiles | `core/src/relay/*.json` | Hardware mapping |
| Trace logs | `core/src/logs/*_*.jsonl` | `llm_trace` (per LLM call) + `world_trace` (per 10Hz tick). Gitignored. |
| Tools | `core/src/tools/*.py` | `analyze_trace`, `dump_prompt`, `gen_field_diagrams`, `run_experiment`, `swap_fragments`, `match_annotate`, `replay_trace` |
| Tests | `core/src/tests/test_*.py` | 9 files, 92 tests (91 fast + 11 slow) |
| Knowledge base | `core/src/ros2k_knowledge/*.md` | 7 power-files + router. opencode reads these automatically. |
| Referee rulebook | `core/docs/referee_rulebook.md` | Complete decision catalog — read before changing any rule |
| Optimization spec | `core/docs/optimization_spec_v6.3.md` | Phases 0-5, experiment catalog, KPI definitions |
| Replay | `python3 r2k_visualizer.py --replay` | Visual replay of saved matches (no ROS2 needed). `--live` for live mode. |