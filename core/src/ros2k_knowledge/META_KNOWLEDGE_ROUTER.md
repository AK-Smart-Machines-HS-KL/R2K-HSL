---
id: META_ROUTER
title: "Semantic Glossary & Routing Matrix (Inverted Index)"
type: KNOWLEDGE_BASE_POWER_FILE
tags: [router, glossary, index, rag, meta, flat-json, phantom-kick, setup_r2k, active_relay, watchdog, hybrid-os, uros_ws, xid-31, mermaid, v6, v6.1, foul, ball-out, kick-in, momentum, reward-node, batch-evaluator, aggression, set-piece, goal-kick, corner-kick-in, kickoff, own-half-warp, blitting, referee-rulebook, trace-logging, llm-trace, world-trace, r2k-run-id, analyze-trace, kpi, prompt-disentanglement, dump-prompt, strat-artifact, goalie-idle, red-p1-p5, blocking-avoidance, headless-gzserver, docker-env-passthrough]
last_modified: 2026-07-15
version: v6.1
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
* **V6 Batch Evaluator ('batch_evaluator.py') [NEW in v6]:**
  * *Definition:* Headless orchestrator for automated scenario evaluation. Subscribes to '/tactical_score', '/tactical_reward', '/match_state', '/world_positions' and writes 'eval_results.json'.
  * *Constraint:* Must NOT kill 'ollama' on teardown — only ROS nodes and Gazebo.
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

## 3. Mermaid Rendering Constraints
> **CRITICAL DIRECTIVE FOR LLMs:** To prevent fatal parsing errors in our documentation renderer, all Mermaid `graph TD` diagrams MUST strictly adhere to the following syntax limitations. DO NOT use advanced brackets.

* **Rule 1: Subgraph IDs must be flat.** Use purely alphanumeric IDs with underscores. Do NOT use spaces, and do NOT use brackets `[]` to label subgraphs.
  * *FATAL ERROR:* `subgraph S_V5 [V5 Engine Nodes]`
  * *CORRECT:* `subgraph V5_Engine_Nodes`
* **Rule 2: Quote all Node Strings.** Any node containing special characters (slashes, parentheses, dots, hyphens) MUST be wrapped in double quotes. Using shape-brackets like `[/.../]` will crash the lexical parser if it interprets it as a shape command.
  * *FATAL ERROR:* `MS[/gazebo/model_states]`
  * *CORRECT:* `MS["/gazebo/model_states"]`
