---
id: 00_MASTER_INDEX
title: "ROS2K Master Documentation Index"
type: INDEX
tags: [index, architecture, roadmap, v6, v6.1, v6.2, hybrid-os, glossary, onboarding]
last_modified: 2026-07-15
version: v6.2
author: Technical Architecture Team
---

# ROS2K Master Documentation Index

> [!info] Human Summary
> This document is the strict table of contents and file directory for the ROS2K hybrid
> robotics project. It maps the documentation covering the dual-goal architecture (RoboCup
> and LLM workbench), hardware integration, AI topologies, hybrid OS infrastructure, and the
> v6.2 scoring/referee/tooling system.

> [!abstract] LLM Context Anchor
> Retrieve this file first to understand the overarching repository structure and to locate
> specific domain documents. This index strictly omits graphical topology generation and
> agile terminology.

## 1. Scope & Objectives

The ROS2K architecture serves two concurrent objectives:

1. **RoboCup Development Environment:** An exploratory platform utilizing Gazebo, ROS 2
   topologies, and bidirectional communication to orchestrate mixed-reality scenarios
   integrating simulated robots, physical hardware, and LLM-driven agents.
2. **LLM Robotics Workbench:** A highly constrained testbed designed to optimize and refine
   small-parameter, low-latency LLMs (specifically `qwen2.5-coder:3b` via Ollama) for
   real-time spatial reasoning, strategy generation, and simulation-to-reality transfer.

> [!tip] New to ROS2K? Read in this order:
> 1. [[1_01_INTRODUCTION_Overall_Architecture]] — what is this system?
> 2. [[7_01_INTRODUCTION_Scoring_Referee_Gamestate]] — how does scoring, refereeing, and game state work?
> 3. [[7_02_ARCHITECTURE_World_Model_Components]] — what does the LLM see?
> 4. [[3_01_INTRODUCTION_AI_Teams_Overview]] — who controls the bots?
> 5. [[7_03_CHEATPAGE_Tools_and_Utils]] — how do I run experiments?
> 6. [[7_05_CHEATPAGE_Experiment_Guide]] — step-by-step: run and measure a match

> [!info] File Nomenclature
> Files follow strict naming to assist human filtering and LLM routing:
> * **INTRODUCTION:** High-level domain context and scope definition (Start here).
> * **ARCHITECTURE:** System logic, topological graphs, and data flows.
> * **SPECIFICATION:** Hardcoded schemas, APIs, coordinate frames, and math vectors.
> * **CHEATPAGE:** Empirically derived hacks, race-condition fixes, and known limitations.

---

## 2. Master Table of Contents

### Section 1: System Overview & Core Architecture

* [[1_01_INTRODUCTION_Overall_Architecture]] - Hybrid environment goals, Gazebo integration, and the tri-agent topology.
* [[1_02_ARCHITECTURE_System_Overview]] - System map of the LLM vs Algorithmic AI paradigm.
* [[1_03_ARCHITECTURE_Control_Loops]] - Asynchronous timing disparities (10Hz vs 500-2000ms).
* [[1_04_SPECIFICATION_State_Sync_FileIO]] - Disk-based I/O handling. Tracker Node writes via atomic POSIX-Rename (`os.replace`) to RAM-Disk/tmpfs.
* [[1_05_CHEATPAGE_Race_Conditions]] - Mitigating deadlocks via atomic operations.
* [[1_06_ARCHITECTURE_JSON_Thread_Spawning]] - Standard-Twist-Interface for diff-drives via dynamic thread-closures (`def task`). Explicit removal of OOP HALs.

### Section 2: ROS 2 Protocols & Engine Nodes

* [[2_01_INTRODUCTION_ROS2_Protocol_Stack]] - Global `/gazebo/model_states` ingestion.
* [[2_02_ARCHITECTURE_Optional_Modules]] - Standalone Matplotlib-Renderer for 2D-Pitch real-time feedback and teleop channels.
* [[2_03_SPECIFICATION_Coordinate_Frames]] - 3D Quaternions to 2D spatial coordinates.
* [[2_04_ARCHITECTURE_Engine_Nodes]] - Referee Node (fouls, ball-out, set-pieces), Score Node (momentum, OLS regression), Reward Node (1Hz, -10..+10), and state_aggregator.py (Unified Aggregated Worldstate).

### Section 3: AI Agents & Control Logic

* [[3_01_INTRODUCTION_AI_Teams_Overview]] - Team Blue (Cognitive, `qwen2.5-coder:3b`) vs. Team Red (Algorithmic).
* [[3_02_ARCHITECTURE_TeamBlue_LLM]] - REST API payload structures. Direct integration of `qwen2.5-coder:3b` via Ollama REST API (Port 11434). Trace logging, `R2K_INCLUDE_MATCH_STATE`.
* [[3_03_CHEATPAGE_Qwen_Latency]] - Ollama configuration parameters. Must run strictly in User-Space, not as a systemd service.
* [[3_04_SPECIFICATION_TeamBlue_Failsafes]] - LLM physical safety constraints and bounding boxes.
* [[3_05_ARCHITECTURE_TeamRed_Algorithmic]] - Deterministic "Team Red" in Python as control group. V6.1: aggression factor, P1-P5 improvements, set-piece behavior.
* [[3_06_SPECIFICATION_TeamRed_Failsafes]] - Hardcoded engine cutoffs for Team Red.
* [[3_07_CHEATPAGE_AI_Edge_Cases]] - Kinematic hacks, resolving LLM hysteresis, orbital singularities. Goalie idle structural limitation.
* [[3_08_ARCHITECTURE_Dynamic_Prompting]] - Pre-Flight Compiler (`setup_r2k.py`) for dynamic prompt compilation. V6.1: `strat_*.txt` removed, `dump_prompt.py`, fragment override logic.

### Section 4: Edge Hardware Integration & HAL (Sim2Real)

* [[4_01_INTRODUCTION_Edge_Hardware]] - The unified `ollama_sandbox_bridge.py` routing logic.
* [[4_02_ARCHITECTURE_ESP32_microROS]] - Namespace Isolation (`/bot1/`) to strictly separate hardware communication and prevent DDS collisions.
* [[4_03_SPECIFICATION_ESP32_QoS]] - Asymmetrical Quality of Service (BEST_EFFORT vs RELIABLE).
* [[4_04_CHEATPAGE_ESP32_Odometry]] - Implementing Dead Reckoning (t = d / v).
* [[4_05_ARCHITECTURE_BoosterK1_Props]] - Booster K1 proprietary Locomotion-API.
* [[4_06_SPECIFICATION_BoosterK1_Integration]] - JSON RPC Payload API for Booster K1 using API-Codes 2000 (Failsafe/Prep) and 2001 (Active Locomotion).
* [[4_07_CHEATPAGE_BoosterK1_Odometry]] - Physical slip and odometry drops.
* [[4_08_ARCHITECTURE_Native_microROS_U22]] - Native `micro-ROS-agent` compiled in C++ (`uros_ws`) to overcome FastDDS Shared-Memory blockades on Ubuntu 22.04.

### Section 5: Hybrid OS Infrastructure (Docker & Native)

* [[5_01_INTRODUCTION_Dual_OS_Topology]] - Hybrid OS Topology: Ubuntu 22.04 runs 100% natively (0ms latency), Ubuntu 24.04 encapsulated via Docker-Compose. X11-Forwarding (`/tmp/.X11-unix`) for GUI-Passthrough. V6.1: headless Gazebo, Docker env passthrough.
* [[5_02_SPECIFICATION_Docker_Networking]] - Forcing `network_mode: host` and dynamic generation of `COMPOSE_PROJECT_NAME` to prevent container collisions.
* [[5_03_INTRODUCTION_Build_Scratch]] - Workspace compilation (colcon build) and symlinks.
* [[5_04_CHEATPAGE_Nvidia_Xid31_Suspend_Bug]] - Suspend-Bug Diagnostics: Kernel repair for Nvidia VRAM loss (Xid 31 MMU Fault) via `NVreg_PreserveVideoMemoryAllocations=1` and `nvidia-suspend.service`.

### Section 6: Data Schemas & System Lifecycle

* [[6_01_SPECIFICATION_Data_Schemas]] - JSON payload structures for Worldstate, Strategies, relay profiles, `/match_state` v6, `/tactical_score` v6 (momentum), `/tactical_reward`, `eval_results.json`, trace JSONL schemas.
* [[6_02_CHEATPAGE_System_Lifecycle]] - `0.2s Asynchronous Watchdog` replacing "Nuke & Pave". `.bashrc Immunity`. V6.1: `R2K_RUN_ID`, trace file lifecycle, headless teardown.
* [[6_03_CHEATPAGE_CLI_Ergonomics]] - System CLI launch flags (`--headless`, `--duration`, `--explain`, `--no-explain`, `--strategy`), execution parameters, and the complete deprecation of legacy scripts.

### Section 7: Scoring, Referee, World Model & Tools (NEW in v6.2)

* [[7_01_INTRODUCTION_Scoring_Referee_Gamestate]] - Unified overview: scoring (momentum, reward), referee (fouls, set-pieces, kickoff), game state (`/match_state` schema, restart logic). How they interact. Link to `referee_rulebook.md`.
* [[7_02_ARCHITECTURE_World_Model_Components]] - The perception-cognition-execution pipeline. What the LLM sees vs what exists. Trace logging as observability layer. Future: Kalman filter, predictive model.
* [[7_03_CHEATPAGE_Tools_and_Utils]] - The `tools/` directory: `dump_prompt.py`, `analyze_trace.py`, `swap_fragments.sh`, `run_experiment.sh`. `batch_evaluator.py`. `R2K_RUN_ID` lifecycle.
* [[7_04_SPECIFICATION_Prompt_Architecture]] - Fragment assembly, override logic, B-study findings, consolidated v6.2 prompt, goalie idle limitation, dynamic prompt selection roadmap.
* [[7_05_CHEATPAGE_Experiment_Guide]] - Step-by-step: run a single match, inspect KPIs, run an experiment, compare runs, run a batch. Example commands. Where files go.

---

## 3. RAG Knowledge Base

This project maintains a highly condensed, RAG-optimized documentation set specifically
designed for LLM-based coding assistants. These files bundle the detailed human chapters
above into semantic "Power Files" with strict constraints to prevent hallucination.

All RAG files are at `core/src/ros2k_knowledge/` and are at version `v6.1`:

* `META_KNOWLEDGE_ROUTER.md` - Semantic Glossary and Inverted Index for RAG routing.
* `1_CORE_ARCHITECTURE_AND_SYNC.md` - Architecture, tmpfs, threading, trace logging (V6.1)
* `2_ROS2_PROTOCOLS_AND_FRAMES.md` - ROS 2 protocols, referee, fouls, set-pieces, blitting (V6.1)
* `3_AI_LOGIC_AND_EDGE_CASES.md` - AI logic, prompt study, red P1-P5, goalie idle (V6.1)
* `4_EDGE_HARDWARE_SIM2REAL.md` - Hardware integration, K1, ESP32 (V5, unchanged)
* `5_HYBRID_INFRASTRUCTURE_V5.md` - Hybrid OS, Docker, headless Gazebo (V6.1)
* `6_DATA_SCHEMAS_AND_LIFECYCLE.md` - Schemas, trace files, KPIs, `R2K_RUN_ID` (V6.1)

---

## 4. Glossary

* **`qwen2.5-coder:3b`**: The active LLM model, served locally via Ollama on port 11434.
  Runs strictly in User-Space (not systemd) to allow the watchdog to `pkill -9` it.
* **`r2k_evaluator.py`**: Standalone Python daemon polling `Worldstate.json` mtime,
  managing blocking HTTP POST requests to Ollama, and writing `current_strategy.json`.
  V6.1: also writes `llm_trace_<run_id>.jsonl`. Requires `shared_state/` directory.
* **`ollama_sandbox_bridge.py` (Bridge)**: Central ROS 2 node reading
  `current_strategy.json` and `active_relay.json`, dynamically translating LLM vectors
  into `Twist` messages or K1 RPC payloads via thread-closures (`def task`). No OOP HALs.
* **`setup_r2k.py`**: Pre-Flight Compiler that stitches prompt fragments from
  `strategy/fragments/` and generates `active_relay.json`. V6.1: no longer writes
  `strat_*.txt` build artifacts (gitignored).
* **`referee_node.py`**: Automated referee enforcing fouls (pushing, blocking), ball-out
  detection, set-pieces (goal kick, corner kick-in, kickoff with 5s countdown), and early
  restart termination. See `core/docs/referee_rulebook.md` for the complete rulebook.
* **`score_node.py`**: Goal detection + tactical scoring. V6: momentum via OLS regression
  on `deque(maxlen=300)` (30s at 10Hz). Publishes `/tactical_score`.
* **`reward_node.py`**: 1Hz reward node (-10..+10 scale, foul penalty -1). Publishes
  `/tactical_reward`.
* **`state_aggregator.py`**: Bündelt Koordinaten, Match-State, Score und Reward in die
  zentrale `Worldstate.json` (via atomarem `os.replace`). V6.1: also writes
  `world_trace_<run_id>.jsonl`.
* **`R2K_RUN_ID`**: Env var exported by `launch_r2k.sh` as
  `${SCENARIO}_${STRATEGY}_$(date)`. Correlates trace files across evaluator and aggregator.
* **`tools/analyze_trace.py`**: Offline KPI analyzer. Reads `llm_trace` + `world_trace`
  JSONL files, computes 14 KPIs (goals, cluster%, OOB%, latency p50/p95, etc.).
* **`tools/dump_prompt.py`**: Dry-run prompt inspector. Assembles fragments identically
  to `setup_r2k.py` without requiring ROS or Ollama.
* **`batch_evaluator.py`**: Headless batch orchestrator for systematic evaluation across
  scenarios, strategies, and models.
* **0.2s Asynchronous Watchdog**: Replaces old `kill_r2k.sh`. Fast-polling loop detecting
  UI closure, fires Kinematic Freeze (Twist-zero / API 2000), then `pkill -9`.
* **Kinematic Freeze**: Failsafe publishing zero-velocity vectors or API 2000 standby
  commands before teardown, preventing runaway robots.
* **`.bashrc Immunity**: Hardcoded `ROS_DOMAIN_ID=0` and `rmw_fastrtps_cpp` in
  `launch_r2k.sh` to block DDS collisions from user environment variables.
* **Momentum**: 30s rolling-window OLS regression of tactical score. Published as
  `momentum_30s` (clamped -10..+10) and `momentum_trend` (ascending/improving/stable/
  declining/collapsing) on `/tactical_score`.
* **Set-piece**: Unified restart pattern for goal kicks, corner kick-ins, and kickoffs.
  Ball placement, opponent warp (1.5m → 2m away), 5s countdown, early termination on
  restart-team ball touch (0.3m).
* **`AGGRESSION_FACTOR`**: 15% chance per red decision to move toward an opponent
  instead of the ball. Generates realistic foul scenarios for testing.

---

## 5. Q&A: Architectural Design Decisions

**Q: How does scoring work?**
A: Three nodes contribute. `score_node.py` tracks goals and computes a tactical score
(positive = blue advantage) plus momentum (30s OLS trend). `reward_node.py` publishes
1Hz rewards (-10..+10) based on decision deltas and foul penalties. `referee_node.py`
detects goals, fouls, and ball-out events. See [[7_01_INTRODUCTION_Scoring_Referee_Gamestate]].

**Q: What does the LLM see?**
A: By default, `r2k_evaluator.py` strips the worldstate to X/Y coordinates of entities
only — no match_state, no score, no momentum. The env var `R2K_INCLUDE_MATCH_STATE=1`
optionally injects referee status and restart_team. See [[7_02_ARCHITECTURE_World_Model_Components]].

**Q: How are prompts assembled?**
A: `setup_r2k.py` stitches fragments from `strategy/fragments/` at boot:
`header.txt` → `rules_core.txt` → `rules_{strategy}.txt` (or `rules_{mode}.txt`) →
`samples_{strategy}.txt` (or `samples_{mode}.txt`). Strategy-specific fragments override
mode fragments. `strat_*.txt` build artifacts are removed (gitignored). See
[[7_04_SPECIFICATION_Prompt_Architecture]].

**Q: How do I run an experiment?**
A: `./launch_r2k.sh --headless --duration 120 --scenario 3vs3_attack_center --strategy strat_default`,
then `python3 tools/analyze_trace.py --run-id <R2K_RUN_ID>`. See
[[7_05_CHEATPAGE_Experiment_Guide]] for step-by-step.

**Q: How does the system handle the speed disparity between hardware (10Hz) and LLM (~800ms)?**
A: By decoupling into two asynchronous domains. The bridge spawns 10Hz PID closures
maintaining hardware QoS. The evaluator waits for LLM inference without blocking motor
loops. State sync via atomic `os.replace` on tmpfs.

**Q: How is Team Red controlled?**
A: Team Red is driven by `rule_evaluator_red.py`, a deterministic state machine with
algorithmic staging (0.6m behind ball), smoothstep hysteresis, and V6.1 improvements
(aggression 0.15, boundary clamp, blocking avoidance, freeze compliance). It bypasses
the LLM entirely.

---

## 6. Future Work & Roadmap

See `core/docs/optimization_spec_v6.2.md` §5 Phase 5 for the full research roadmap:

* **5.1 Kalman Filter World Model** — smooth noisy tracking, derive velocity estimates
* **5.2 Predictive World Model** — forward-simulate by N ms to compensate LLM latency
* **5.3 Deviation Watchdog** — detect model drift, simulation instabilities
* **5.4 Failsafe Fallback** — rule-based blue behavior if LLM fails
* **5.5 Dynamic Prompt Selection** — gamestate-aware fragment switching
* **5.6 Optimization GUI** — Streamlit/W&B-style experiment dashboard
* **5.7 Sim-to-Real Transfer** — validate sim-trained prompts on K1/Yahboom hardware
* **5.8 Opponent Adaptation** — curriculum learning via adaptive red aggression
* **5.9 Temporal Reasoning** — include N history frames in LLM prompt
* **5.10 Active Learning Loop** — auto-generate scenarios for worst failure modes