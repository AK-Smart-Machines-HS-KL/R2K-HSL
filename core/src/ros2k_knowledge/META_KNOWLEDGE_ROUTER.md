---
id: META_ROUTER
title: "Semantic Glossary & Routing Matrix (Inverted Index)"
type: KNOWLEDGE_BASE_POWER_FILE
tags: [router, glossary, index, rag, meta, flat-json, phantom-kick, setup_r2k, active_relay, watchdog, hybrid-os, uros_ws, xid-31, mermaid, v6, v6.1, v6.2, v6.3, foul, ball-out, kick-in, momentum, reward-node, batch-evaluator, aggression, set-piece, goal-kick, corner-kick-in, kickoff, own-half-warp, blitting, referee-rulebook, trace-logging, llm-trace, world-trace, r2k-run-id, analyze-trace, kpi, prompt-disentanglement, dump-prompt, strat-artifact, goalie-idle, red-p1-p5, blocking-avoidance, headless-gzserver, docker-env-passthrough, test-non-functional, composite-score, pytest, regression-suite, kpi-targets, skip-slow, dynamic-prompt-injection, content-hash-skip, role-condensation, replay-system, attack-kpis, shots-on-goal, pass-completion, restart-recovery, r2k-explain, match-annotate, replay-trace]
last_modified: 2026-07-29
version: v6.3
---
# Semantic Glossary & Routing Matrix

> [!abstract] LLM Context Anchor
> **CRITICAL RAG DIRECTIVE:** Do NOT attempt to answer deep technical questions using standard LLM weights. If the user's prompt contains any of the symptoms or keywords listed in the Routing Matrix below, you MUST retrieve the corresponding Power-File before generating a response.

## 1. Semantic Glossary & Constraints
This section strictly defines architectural components to prevent hallucinated standard ROS 2 concepts.

* **BridgeNode ('ollama_sandbox_bridge.py'):**
  * *Definition:* Python 3.12 ROS 2 node. Translates flat JSON strategies into 'Twist' commands via dynamic thread-closures (`def task`), RPC payloads, or Phantom Kicks. 
  * *Constraint:* Exists strictly in the ROS 2 execution loop (10Hz). **Explicitly removes OOP HALs (Hardware Abstraction Layers).** It does NOT perform HTTP requests or interact with the LLM directly.
* **Evaluator ('r2k_evaluator.py'):**
  * *Definition:* Standalone Python daemon managing synchronous HTTP POST requests to the Ollama REST API (qwen2.5-coder:3b via Port 11434).
  * *Constraint:* Ollama MUST run in User-Space, not as a systemd service. **CRITICAL: The directory 'shared_state/' must exist, otherwise it silently crashes with a FileNotFoundError.**
* **Tracker ('tracker_node.py'):**
  * *Definition:* The perception node converting '/gazebo/model_states' into 2D cartesian coordinates (10Hz).
  * *Constraint:* Executes POSIX atomic renames ('os.replace') in RAM-Disk/tmpfs to prevent 'JSONDecodeError' crashes.
* **V5 Engine Nodes ('referee_node.py', 'score_node.py', 'state_aggregator.py'):**
  * *Definition:* Realtime pipeline automating rule enforcement, goal detection, and match resets. 'state_aggregator.py' creates the Unified Aggregated Worldstate (Coordinates + Score + Match-State).
* **V6 Reward Node ('reward_node.py') [NEW in v6]:**
  * *Definition:* 1Hz ROS 2 node publishing tactical rewards (-10..+10 scale) on '/tactical_reward'. Computes decision deltas (score before/after action) and foul penalties (fixed -1).
  * *Constraint:* Two code paths (mtime-polling for decisions, '/match_state' subscription for fouls) must not be mixed.
* **V6 Batch Evaluator ('batch_evaluator.py') [NEW in v6, DEPRECATED in v6.2]:**
  * *Definition:* Headless orchestrator for automated scenario evaluation. Designed to subscribe to ROS topics and write 'eval_results.json'.
  * *Constraint:* **KPI collection is broken** (TODO at line 91 — never implemented). The file exists and can launch matches but produces no KPI data. Deprecated in v6.2 — replaced by `tests/test_non_functional.py` (shared regression suite, implemented Phase 2b, 2026-07-25).
* **V6.2 Shared Regression Suite ('tests/test_non_functional.py') [NEW in v6.2]:**
  * *Definition:* Pytest-based regression suite of real 120s Gazebo matches with per-scenario KPI assertions. Two-tier: fast (`--skip-slow`, ~2s, 91 unit tests) and slow (`@pytest.mark.slow`, ~140s per test, real matches). Helpers: `run_match_headless()`, `compute_composite()`, `load_kpi_targets()`, `assert_kpi_in_range()`. Asserts per-scenario `kpi_targets.json` thresholds.
  * *Constraint:* Slow tests require live ROS 2 + Gazebo + Ollama. Fast tests skip gracefully. Thresholds calibrated from the 27-run baseline (Phase 2e, not yet run — current values are spec estimates). `goalie_tactical_pct` (Phase 2a KPI, distinguishes positioning from stuck) is asserted `>= 60%`.
* **V6.1 Referee Rulebook ('core/docs/referee_rulebook.md') [NEW in v6.1]:**
  * *Definition:* Standalone Markdown document (not a RAG power-file, but referenced by the routing matrix). Complete catalog of every referee decision: triggers, consequences, scoring, timing, freeze enforcement, field layout, state machine, and visualizer event labels. Includes 2D field diagrams and mermaid flowcharts.
  * *Constraint:* Read this BEFORE changing any referee rule, threshold, or visualizer label. The rulebook is the single source of truth — the V6 addendum in `2_ROS2_PROTOCOLS_AND_FRAMES.md` is a summary; the rulebook is authoritative.
* **V6.1 Trace Logger [NEW in v6.1]:**
  * *Definition:* Append-only JSONL observability layer. Two files: `logs/llm_trace_<run_id>.jsonl` (one record per LLM call, written by `r2k_evaluator.py`) and `logs/world_trace_<run_id>.jsonl` (one record per 10Hz world-state write, written by `state_aggregator.py`). Non-blocking, wrapped in try/except, never crashes the execution loop.
  * *Constraint:* Trace files are write-only during a run. They are consumed offline by `tools/analyze_trace.py` AFTER the run ends. The `logs/` directory is gitignored and NOT wiped on boot.
* **V6.1 KPI Analyzer ('tools/analyze_trace.py') [NEW in v6.1]:**
  * *Definition:* Offline script that joins `llm_trace` and `world_trace` files by `R2K_RUN_ID`, computes 14 KPIs (goals, cluster_pct, goalie_idle_pct, oob_pct, possession, tactical_score_avg/final, latency p50/p95/max, parse_error_rate, role_diversity, status_distribution, avg_response_tokens), outputs JSON.
  * *Constraint:* Requires the `--run-id` argument matching the `R2K_RUN_ID` env var set by `launch_r2k.sh`. Does NOT require ROS or Ollama — pure offline file analysis.
* **V6.1 Prompt Inspector ('tools/dump_prompt.py') [NEW in v6.1]:**
  * *Definition:* Dry-run script that assembles prompt fragments identically to `setup_r2k.py` WITHOUT requiring ROS or Ollama. Prints the full assembled prompt, per-fragment breakdown, and token estimate.
  * *Constraint:* Use this to verify prompt changes before launching a match. Does NOT write `system_prompt.txt` — it only prints to stdout.
* **V6.1 Run ID ('R2K_RUN_ID') [NEW in v6.1]:**
  * *Definition:* Env var exported by `launch_r2k.sh:82` as `${SCENARIO}_${STRATEGY}_$(date +%Y%m%d_%H%M%S)`. Used as correlation key for trace files. Propagated to Docker containers via `docker exec -e R2K_RUN_ID=...`.
  * *Constraint:* If unset, both `r2k_evaluator.py` and `state_aggregator.py` fall back to `run_{timestamp}` — trace files will not be correlatable with the run's console log.
* **Prompt Compiler ('setup_r2k.py'):**
  * *Definition:* A pre-flight script that dynamically compiles the system prompt and hardware relay-mapping ('active_relay.json') based on '--relay' CLI flags before boot.
* **0.2s Asynchronous Watchdog:**
  * *Definition:* A fast-polling loop in 'launch_r2k.sh' that detects UI closure.
  * *Constraint:* Replaces old "Nuke & Pave" scripts. Fires asynchronous Kinematic Freeze (Twist-zeroes / API 2000) and executes 'pkill -9' (SIGKILL) on Ollama and ROS 2 processes to prevent RCLError tracebacks and zombie ports.
* **V6.3 Dynamic Prompt Injection [NEW in v6.3]:**
  * *Definition:* Evaluator assembles system prompt at runtime from fragment files, based on `match_state.status`. At `status="ball_out"`, `rules_ball_out.txt` is added additively. Ollama is stateless (sends `system` per call), so prompt can change between calls. Cached by `(status, mode)` tuple.
  * *Constraint:* Game-phase fragments are ADDITIVE to mode fragments (not replacements). `system_prompt.txt` written by `setup_r2k.py` at boot is now only for `dump_prompt.py` dry-runs — evaluator reads fragments directly at runtime.
* **V6.3 Content-Hash Skip [NEW in v6.3]:**
  * *Definition:* Evaluator hashes entity positions (`min_ents` JSON) and skips LLM call if identical to previous call. At `temperature: 0.0`, identical input → identical output. Saves 64% of calls per match (171→62). Effective latency ~684ms (was ~1328ms).
  * *Constraint:* Makes `current_strategy.json` mtime unreliable as staleness indicator (file may not update for seconds during stable positions — normal, not failure). Phase 5.4 failsafe must check `llm_trace` records, not file mtime.
* **V6.3 Role Condensation [NEW in v6.3]:**
  * *Definition:* Roles reduced from 5 (striker/midfielder/passer/receiver/supporter) to 3 (goalie/attacker/defender). Bridge only checks `role == 'goalie'`; all others were cosmetic labels. `role_diversity` KPI dropped (dead metric, CV=0%).
  * *Constraint:* All fragments and `analyze_trace.py` updated. Pass detection is now position-based (kicker NOT in opponent half = pass), not role-based.
* **V6.3 Replay System [NEW in v6.3]:**
  * *Definition:* `match_annotate.py` (live: pause Gazebo, record comment) + `replay_trace.py` (CLI: step through annotations) + `r2k_visualizer.py --replay` (visual: f/b/SPACE/arrow controls, annotation overlay). No ROS 2 required for replay.
  * *Constraint:* Sim-time (`/clock`) requires `libgazebo_ros_init.so` built into Docker container. Without it, all timestamps are wall-clock (`t_wall`). Annotation navigation (`--nav`) is deprecated — always on in replay mode.
* **V6.3 Attack KPIs [NEW in v6.3]:**
  * *Definition:* 4 new KPIs in `analyze_trace.py`: `shots_on_goal` (Kick in opp half, ball moves toward goal), `shots_on_target` (subset within goal posts), `pass_completion_pct` (different blue bot closest to ball within 2s), `restart_recovery_time_s` (status change → restart-team bot within 0.35m of ball). Joins `llm_trace` actions with `world_trace` ball deltas.
  * *Constraint:* Uses `t_wall` (wall-clock) for timestamps — sim-time is 0.0 in all traces without `libgazebo_ros_init.so`. KPI count is 18 (was 15; +4 attack, +1 goalie_tactical, -1 role_diversity).
* **V6.3 `R2K_EXPLAIN` env var [NEW in v6.3]:**
  * *Definition:* Env var set by `launch_r2k.sh` (`--explain` → `1`, `--no-explain` → `0`). Evaluator replaces `{{EXPLAIN_INSTRUCTION}}` in `header.txt` based on this var. Fixes explain-mode broken by Phase 2.5b dynamic injection (which bypassed `setup_r2k.py`'s `clean_json_samples()`).
  * *Constraint:* `r2k_evaluator.py` duplicates `clean_json_samples()` (~70 lines) from `setup_r2k.py` — needed at runtime to inject default analysis/oracle strings into samples. Without this, Qwen 3B fills oracle with JSON strategy data.

## 2. Routing Matrix (Inverted Index)
If the user query involves [SYMPTOM / KEYWORD], explicitly retrieve and reference [POWER-FILE]:

| User Symptom / Concept / Keyword | Target Power-File to Retrieve |
| :--- | :--- |
| 'JSONDecodeError', file read collisions, race conditions, atomic rename, 'os.replace', dynamic thread-closures, 'def task()', NO OOP HALs, preemption | **'1_CORE_ARCHITECTURE_AND_SYNC.md'** |
| Quaternions, 3D to 2D math, '/gazebo/model_states', Matplotlib-Renderer, Referee Node, Score Node, Unified Aggregated Worldstate, 'state_aggregator.py' | **'2_ROS2_PROTOCOLS_AND_FRAMES.md'** |
| Flat JSON schema, Parsing Paralysis, Phantom Kick, Algorithmic Staging, Qwen-3B, Port 11434, User-Space Ollama, Rule-based State Machine | **'3_AI_LOGIC_AND_EDGE_CASES.md'** |
| Namespace-Isolation ('/bot1/'), Booster K1, API-Codes 2000/2001, ESP32, physical slip, QoS 'BEST_EFFORT', Native 'uros_ws', .bashrc Immunity | **'4_EDGE_HARDWARE_SIM2REAL.md'** |
| Hybrid OS Topology, Ubuntu 22 Native vs 24 Docker, X11-Forwarding, COMPOSE_PROJECT_NAME, Xid 31 MMU Fault, Suspend-Bug, NVreg_PreserveVideoMemoryAllocations=1 | **'5_HYBRID_INFRASTRUCTURE_V5.md'** |
| 'active_relay.json', 0.2s Asynchronous Watchdog, 'pkill -9', SIGKILL, Kinematic Freeze, '--relay' flags, CLI Ergonomics | **'6_DATA_SCHEMAS_AND_LIFECYCLE.md'** |
| **[V6]** Foul detection, pushing, blocking without ball, ball-out, last-touch, hysteresis, sideline warp, restart logic, '/match_state' foul schema, referee thresholds (0.3m, 0.5m/s, 30 degrees), set-piece, goal kick, corner kick-in, kickoff, `own_half_warp`, `SET_PIECE_COUNTDOWN`, unified set-piece, visualizer blitting, `init_figure`, `update_figure` | **'2_ROS2_PROTOCOLS_AND_FRAMES.md' §V6 Addendum** |
| **[V6]** Kick-in, prompt-switching, 'match_state.status', prompt-injection, team-red kick-in behavior, momentum, OLS regression, reward_node, 1Hz reward, foul penalty -1, 'AGGRESSION_FACTOR', red aggression, kick-in prompt iteration, red freeze compliance, hysteresis, flickering, anti-clustering red | **'3_AI_LOGIC_AND_EDGE_CASES.md' §V6 Addendum** |
| **[V6]** '/tactical_score' momentum schema, '/tactical_reward' schema, 'eval_results.json', batch_evaluator CLI, '--scenarios', '--strategies', '--models', '--runs', '--duration', '--output', composite score, KPI, '/match_state' goal_kick, '/match_state' corner_kick_in, foul penalty values | **'6_DATA_SCHEMAS_AND_LIFECYCLE.md' §V6 Addendum** |
| **[V6.1]** Referee rulebook, complete decision catalog, set-piece positions, field diagram, 2D graphics, state machine, scoring, reward system, freeze enforcement, K1 limitation, `referee_rulebook.md` | **'core/docs/referee_rulebook.md'** (standalone doc) |
| **[V6.1]** `llm_trace`, `world_trace`, trace logging, `R2K_RUN_ID`, `analyze_trace.py`, KPI measurement, latency p50/p95, parse_error_rate, role_diversity, cluster_pct, goalie_idle_pct, oob_pct, ball possession, observability layer, third decoupled channel | **'6_DATA_SCHEMAS_AND_LIFECYCLE.md' §V6.1 Addendum** + **'1_CORE_ARCHITECTURE_AND_SYNC.md' §V6.1 Addendum** |
| **[V6.1]** `strat_*.txt` removal, prompt disentanglement, `dump_prompt.py`, sample-override, strategy-specific samples, fragment assembly order, `R2K_INCLUDE_MATCH_STATE`, match_state injection, goalie idle structural limitation, bridge PD controller, red P1-P5, red boundary clamp, red blocking avoidance, red freeze bug, `restart_team` freeze check | **'3_AI_LOGIC_AND_EDGE_CASES.md' §V6.1 Addendum** |
| **[V6.1]** Headless Gazebo, `gzserver` only, `--headless` flag, `headless:=true`, Docker env passthrough, `R2K_RUN_ID` Docker, `R2K_OLLAMA_MODEL` Docker, `docker exec -e` | **'5_HYBRID_INFRASTRUCTURE_V5.md' §V6.1 Addendum** |
| **[V6.2]** `test_non_functional`, `pytest`, `--skip-slow`, regression suite, slow marker, fast tier, slow tier, composite score, `compute_composite`, `goal_diff_norm`, `tac_score_norm`, `possession_norm`, `latency_factor`, `kpi_targets.json`, per-scenario thresholds, `run_match_headless`, `goalie_tactical_pct` | **'6_DATA_SCHEMAS_AND_LIFECYCLE.md' §V6.2 Addendum** |
| **[V6.2]** Docker colcon rebuild, `numpy/ndarrayobject.h` not found, stale build cache, `rm -rf build install`, rosidl CMake numpy fallback, `docker compose up -d`, `docker exec colcon build` | **'5_HYBRID_INFRASTRUCTURE_V5.md' §V6.2 Addendum** |
| **[V6.3]** Dynamic prompt injection, `rules_ball_out.txt`, `rules_goal_kick.txt`, `rules_corner_kick_in.txt`, `rules_kickoff.txt`, game-phase fragments, `_assemble_prompt`, `sys_prompt_hash`, `R2K_EXPLAIN`, explain-mode fix, `{{EXPLAIN_INSTRUCTION}}`, content-hash skip, 64% fewer calls, effective latency 684ms, `min_ents` hash, role condensation, 5→3 roles, goalie/attacker/defender, `role_diversity` dropped, replay system, `match_annotate.py`, `replay_trace.py`, `--replay`, `--nav`, annotation overlay, `--live`, arrow-key seek | **'3_AI_LOGIC_AND_EDGE_CASES.md' §V6.3 Addendum** + **'6_DATA_SCHEMAS_AND_LIFECYCLE.md' §V6.3 Addendum** |
| **[V6.3]** Attack KPIs, `shots_on_goal`, `shots_on_target`, `pass_completion_pct`, `restart_recovery_time_s`, 18 KPIs, v6.3 baseline, `kpis_baseline_v63`, `R2K_EXPLAIN` env var, `R2K_RUN_LABEL` | **'6_DATA_SCHEMAS_AND_LIFECYCLE.md' §V6.3 Addendum** |

## 3. Mermaid Rendering Constraints
> **CRITICAL DIRECTIVE FOR LLMs:** To prevent fatal parsing errors in our documentation renderer, all Mermaid `graph TD` diagrams MUST strictly adhere to the following syntax limitations. DO NOT use advanced brackets.

* **Rule 1: Subgraph IDs must be flat.** Use purely alphanumeric IDs with underscores. Do NOT use spaces, and do NOT use brackets `[]` to label subgraphs.
  * *FATAL ERROR:* `subgraph S_V5 [V5 Engine Nodes]`
  * *CORRECT:* `subgraph V5_Engine_Nodes`
* **Rule 2: Quote all Node Strings.** Any node containing special characters (slashes, parentheses, dots, hyphens) MUST be wrapped in double quotes. Using shape-brackets like `[/.../]` will crash the lexical parser if it interprets it as a shape command.
  * *FATAL ERROR:* `MS[/gazebo/model_states]`
  * *CORRECT:* `MS["/gazebo/model_states"]`
