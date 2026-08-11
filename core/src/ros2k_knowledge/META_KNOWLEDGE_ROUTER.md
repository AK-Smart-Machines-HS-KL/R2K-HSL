---
id: META_ROUTER
title: "Semantic Glossary & Routing Matrix (Inverted Index)"
type: KNOWLEDGE_BASE_POWER_FILE
tags: [router, glossary, index, rag, meta, flat-json, phantom-kick, setup_r2k, active_relay, watchdog, hybrid-os, uros_ws, xid-31, mermaid, v6, v6.1, v6.2, v6.3, foul, ball-out, kick-in, momentum, reward-node, batch-evaluator, aggression, set-piece, goal-kick, corner-kick-in, kickoff, own-half-warp, blitting, referee-rulebook, trace-logging, llm-trace, world-trace, r2k-run-id, analyze-trace, kpi, prompt-disentanglement, dump-prompt, strat-artifact, goalie-idle, red-p1-p5, blocking-avoidance, headless-gzserver, docker-env-passthrough, test-non-functional, composite-score, pytest, regression-suite, kpi-targets, skip-slow, dynamic-prompt-injection, content-hash-skip, role-condensation, replay-system, attack-kpis, shots-on-goal, pass-completion, restart-recovery, r2k-explain, match-annotate, replay-trace, c3, inter-lingua, controlled-vocabulary, expert-oracle, coordinate-rule, scenario-generation, analysis-md, c3-playbook, c3-dictionary, c3-testcase-review, vocab-probe, soccer-knowledge, universal-knowledge]
last_modified: 2026-08-11
version: v6.5
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
  * *Constraint:* Makes `current_strategy.json` mtime unreliable as staleness indicator (file may not update for seconds during stable positions — normal, not failure). Phase 5.4 failsafe must check `llm_trace` records, not file mtime. **[2026-08-01]** `temperature: 0.0` is NOT bit-exact across KV-cache states (measured: 118-token pretty vs 91-token compact JSON from identical input, direction flips between runs; q8_0 AND f16) — semantics stable, so the skip is safe, but latency A/B comparisons must control cache state; `prompt_eval_count` is not a cache indicator (`prompt_eval_duration` is).
* **V6.3 Role Condensation [NEW in v6.3]:**
  * *Definition:* Roles reduced from 5 (striker/midfielder/passer/receiver/supporter) to 3 (goalie/attacker/defender). Bridge only checks `role == 'goalie'`; all others were cosmetic labels. `role_diversity` KPI dropped (dead metric, CV=0%).
  * *Constraint:* All fragments and `analyze_trace.py` updated. Pass detection is now position-based (kicker NOT in opponent half = pass), not role-based.
* **V6.3 Replay System [NEW in v6.3]:**
  * *Definition:* `match_annotate.py` (live: pause Gazebo, record comment) + `replay_trace.py` (CLI: step through annotations) + `r2k_visualizer.py --replay` (visual: f/b/SPACE/arrow controls, annotation overlay). No ROS 2 required for replay.
  * *Constraint:* Sim-time (`/clock`) requires `libgazebo_ros_init.so` built into Docker container. Without it, all timestamps are wall-clock (`t_wall`). Annotation navigation (`--nav`) is deprecated — always on in replay mode.
* **V6.3 Attack KPIs [NEW in v6.3]:**
  * *Definition:* 4 new KPIs in `analyze_trace.py`: `shots_on_goal` (Kick in opp half, ball moves toward goal), `shots_on_target` (subset within goal posts), `pass_completion_pct` (different blue bot closest to ball within 2s), `restart_recovery_time_s` (status change → restart-team bot within 0.35m of ball). Joins `llm_trace` actions with `world_trace` ball deltas.
  * *Constraint:* Uses `t_wall` (wall-clock) for timestamps — sim-time is 0.0 in all traces without `libgazebo_ros_init.so`. KPI count is 18 (was 15; +4 attack, +1 goalie_tactical, -1 role_diversity).
* **V6.3 `R2K_EXPLAIN` env var [NEW in v6.3, UPDATED v6.5 2026-08-11]:**
  * *Definition:* Env var set by `launch_r2k.sh` (`--explain` → `1`, `--no-explain` → `0`). Evaluator replaces `{{EXPLAIN_INSTRUCTION}}` in `header.txt` based on this var. Fixes explain-mode broken by Phase 2.5b dynamic injection (which bypassed `setup_r2k.py`'s `clean_json_samples()`).
  * *Constraint:* `r2k_evaluator.py` duplicates `clean_json_samples()` (~70 lines) from `setup_r2k.py` — needed at runtime to inject default analysis/oracle strings into samples. Without this, Qwen 3B fills oracle with JSON strategy data.
  * *V6.5 UPDATE (2026-08-11):* `_clean_text_samples` and `_clean_json_samples` regex updated to accept `(?:ASSISTANT|OUTPUT):` marker — v6.5 `samples_3vs3.txt` uses `OUTPUT:` instead of `ASSISTANT:` (all other sample files still use `ASSISTANT:`). The old `ASSISTANT:`-only regex silently passed raw `OUTPUT:` blocks unconverted. This was a latent bug present during the 100-match U24 benchmark — the LLM coped (imitated the raw format), but the cleaned format (canonical `ASSISTANT:` label, default analysis/oracle injection) was not applied. Post-fix re-validation required on U24.
  * *TEXT_MODE default:* `R2K_TEXT_MODE` env var defaults to `"0"` (JSON mode). `launch_r2k.sh` never sets `R2K_TEXT_MODE` — all production runs use JSON mode. TEXT_MODE is exercised only by the fast test suite (`test_text_mode.py`).
* **C3 Inter-Lingua ('7_C3_INTER_LINGUA.md') [NEW in v6.3, C3 Phase 1]:**
  * *Definition:* Controlled-vocabulary paradigm replacing role-based prompting. The LLM outputs situation-triggered position verbs with explicit coordinates; NO derived role labels ("striker"/"passer" removed — model inherits static human-soccer semantics that contradict dynamic definitions). No rule-based bridge mapper (corrected framing 2026-07-31).
  * *Constraint:* Every positional/negational verb in model-facing text MUST carry explicit X,Y — probe-verified (E-series: bot placed ON ball without coords; F-series: "stays back" → moved FORWARD). Referee/restart/foul mechanics are referee-owned; LLM gets passive awareness only.
* **Expert/Oracle Sections ('analysis.md') [NEW in v6.3]:**
  * *Definition:* The two sections of every scenario `analysis.md`. Expert = analyse the game state (facts, geometry, angles, reachability, NUMBERS — NO imperatives, all entities get X,Y). Oracle = things recommended to do (per-bot commands, every positional verb carries explicit X,Y).
  * *Constraint:* **Expert FIRST, Oracle second** — fixed order across all 10 files (corrected 2026-08-01). `analysis.md` is NOT injected into the real ROS2K prompt (prompt = fragments only); it drives the human walkthrough + 3B validation probe.
* **Coordinate Rule (C3) [NEW in v6.3]:**
  * *Definition:* Probe-verified rule (E/F/G series, 2026-08-01): coordinate-free positional prose actively misleads qwen2.5:3b — E1 placed blue_2 ON the ball for "open space on the wing", F1 inverted "stays back". With explicit X,Y the model copies targets correctly. Expert adds nothing when oracle has coords (G1==G2); expert-only reasons but fuzzy (G3). Hybrid = quality ceiling.
  * *Constraint:* Zone nouns need explicit bounds ("own half" only usable as "X from -4.5 to 0"; "opponent half" broken). Validation query format: system = soccer-analyst output-only-3-lines; prompt = world entities verbatim + "Tactical instruction: <Oracle>"; Ollama `qwen2.5:3b`, temperature 0.0, num_predict 600.
* **Universal Soccer Knowledge ('8_C3_SOCCER_KNOWLEDGE.md') [NEW in v6.3, C3 Layer 1]:**
  * *Definition:* Distilled human soccer coaching knowledge (from the 2026-08-01 TC-01..TC-06 walkthrough dialogue), structured for a LARGE generating LLM that writes new scenario packages (Expert + Oracle). Three layers: 1 = model-agnostic soccer principles (control/spacing/angle, attacking, defending, transition — each with Check/Express/Source), 2 = ROS2K specifics (physics, referee, execution — SHORT, subject to change), 3 = inter-lingua mapping (short — refers to `7_C3_INTER_LINGUA.md` + dictionary).
  * *Constraint:* Universal axioms must NOT be repeated verbatim inside per-scenario text (testcase review §2.2). Session lessons are INTEGRATED into the entries (not a separate changelog): every positional verb carries X,Y; short oracles are fine WITH coords; recommended actions must be executable from the actual `scenario.json` starting state; hybrid (Expert facts + Oracle coords) is the quality ceiling.

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
| **[V6.3]** Dynamic prompt injection, `rules_ball_out.txt`, `rules_goal_kick.txt`, `rules_corner_kick_in.txt`, `rules_kickoff.txt`, game-phase fragments, `_assemble_prompt`, `sys_prompt_hash`, `R2K_EXPLAIN`, explain-mode fix, `{{EXPLAIN_INSTRUCTION}}`, content-hash skip, 64% fewer calls, effective latency 684ms, `min_ents` hash, role condensation, 5→3 roles, goalie/attacker/defender, `role_diversity` dropped, replay system, `match_annotate.py`, `replay_trace.py`, `--replay`, `--nav`, annotation overlay, `--live`, arrow-key seek, `OUTPUT:` marker bug, `_clean_text_samples`, `_clean_json_samples`, `R2K_TEXT_MODE`, TEXT_MODE default, `samples_3vs3.txt` | **'3_AI_LOGIC_AND_EDGE_CASES.md' §V6.3 Addendum** + **'6_DATA_SCHEMAS_AND_LIFECYCLE.md' §V6.3 Addendum** |
| **[V6.3]** Attack KPIs, `shots_on_goal`, `shots_on_target`, `pass_completion_pct`, `restart_recovery_time_s`, 18 KPIs, v6.3 baseline, `kpis_baseline_v63`, `R2K_EXPLAIN` env var, `R2K_RUN_LABEL` | **'6_DATA_SCHEMAS_AND_LIFECYCLE.md' §V6.3 Addendum** |
| **[C3]** Inter-lingua, controlled vocabulary, position verbs, derived role labels (striker/passer/supporter), C2_striker_rule, role semantics contradiction, qwen2.5:3b, soccer reasoning patterns P1-P10, anti-patterns A1-A5, referee-owned restarts (kick-in, corner, goal-kick, foul), field ground truth (9×6, goal ±0.9, goal area ±3.5/±1.0), vocab probe, `vocab_probe.py`, `vocab_probe_log.md`, phase1_probes, dictionary vocabulary, D-series borderline verdicts | **'7_C3_INTER_LINGUA.md'** |
| **[C3]** Expert vs Oracle semantics, `analysis.md` section order (Expert first, Oracle second), coordinate rule, E/F/G series probe evidence, scenario package structure (`scenario.json`/`field_diagram.png`/`analysis.md`/`kpi_targets.json`), scenario generation playbook, `c3_scenario_generation_playbook.md`, `c3_vocabulary_dictionary.md`, `c3_testcase_review.md`, TC walkthrough, validation protocol, `gen_field_diagrams.py`, `3vs3_attack_center`, `3vs3_attack_wing`, `3vs3_defensive_crisis`, `3vs3_fast_counter`, `3vs3_pressing_trap` | **'7_C3_INTER_LINGUA.md'** + **'core/docs/c3_scenario_generation_playbook.md'** |
| **[C3]** Universal soccer knowledge, coaching heuristics, control the center, spacing, shooting angle, pass into space, rebound readiness, wing play, numbers advantage, zone defend, lane/dribble denial, deep cover, press escape, cover gap obligation, free time, out-of-reach ignorable, scenario generation for large LLMs, Expert/Oracle authoring | **'8_C3_SOCCER_KNOWLEDGE.md'** |
| **[V6.4]** Clustering root cause, relative positioning, `R2K_GOALIE_BLEND=0`, anti-collision, kick direction override, PD gain boost, score function refined (cluster penalty, lane openness), per-bot kick capability matrix, K1 kick chase, meta-knowledge axiom, demo/calibration mode | **'8_C3_SOCCER_KNOWLEDGE.md' §6** + **'1_CORE_ARCHITECTURE_AND_SYNC.md' §V6.4** |
| **[V6.4]** TeamCaptain, watchdog, augmented world model, path executor, ADR-A07, CPU-only ROS2 node, optimized_path.json, downward compatible, K1 kick abort, ball motion change | **'1_CORE_ARCHITECTURE_AND_SYNC.md' §V6.4** + **'core/docs/adr/ADR-A07-team-captain-architecture.md'** |
| **[V6.4]** K1 kick pitfalls, kShoot autonomous chase, kVisualKick, kChangeMode abort, kRotateHead (api_id 2004), kReplayTrajectory (2028), Yahboom pan-tilt cam, Yahboom metal push kick, trailer non-holonomic, hardware capability matrix | **'4_EDGE_HARDWARE_SIM2REAL.md' §V6.4** |
| **[V6.4]** Empirical scenarios, umschaltmomente, 74 to 33 reduction, 8s regression test, analysis.md format, Oracle ground truth, score chart, `header_k3.txt`, `rules_foul_penalty.txt` | **'6_DATA_SCHEMAS_AND_LIFECYCLE.md' §V6.4** + **'8_C3_SOCCER_KNOWLEDGE.md' §6** |
| **[V6.4]** `start_ollama.sh`, `ORIGINAL_DIR`, path bug after `cd src`, `/tmp/r2k_ollama.log`, `prompt_utils.py`, `header_k3.txt` fragment | **'1_CORE_ARCHITECTURE_AND_SYNC.md' §V6.4** |

## 3. Mermaid Rendering Constraints
> **CRITICAL DIRECTIVE FOR LLMs:** To prevent fatal parsing errors in our documentation renderer, all Mermaid `graph TD` diagrams MUST strictly adhere to the following syntax limitations. DO NOT use advanced brackets.

* **Rule 1: Subgraph IDs must be flat.** Use purely alphanumeric IDs with underscores. Do NOT use spaces, and do NOT use brackets `[]` to label subgraphs.
  * *FATAL ERROR:* `subgraph S_V5 [V5 Engine Nodes]`
  * *CORRECT:* `subgraph V5_Engine_Nodes`
* **Rule 2: Quote all Node Strings.** Any node containing special characters (slashes, parentheses, dots, hyphens) MUST be wrapped in double quotes. Using shape-brackets like `[/.../]` will crash the lexical parser if it interprets it as a shape command.
  * *FATAL ERROR:* `MS[/gazebo/model_states]`
  * *CORRECT:* `MS["/gazebo/model_states"]`
