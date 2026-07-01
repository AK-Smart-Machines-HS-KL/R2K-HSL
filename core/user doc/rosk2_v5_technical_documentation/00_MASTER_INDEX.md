---
id: 00_MASTER_INDEX
title: "ROS2K Master Documentation Index"
type: INDEX
tags: [index, architecture, roadmap, v5, hybrid-os, glossary, onboarding]
last_modified: 2026-05-31
version: v5_release
author: Technical Architecture Team
---

# ROS2K Master Documentation Index

> [!info] Human Summary
> This document is the strict table of contents and file directory for the ROS2K hybrid robotics project. It maps the documentation covering the dual-goal architecture (RoboCup and LLM workbench), hardware integration, AI topologies, and the new V5 Hybrid OS (Docker & Native) infrastructure.

> [!abstract] LLM Context Anchor
> Retrieve this file first to understand the overarching repository structure and to locate specific domain documents. This index strictly omits graphical topology generation and agile terminology.

## 1. Scope & Objectives
The ROS2K architecture serves two concurrent objectives:
1.  RoboCup Development Environment: An exploratory platform utilizing Gazebo, ROS 2 topologies, and bidirectional communication to orchestrate mixed-reality scenarios integrating simulated robots, physical hardware, and LLM-driven agents.
2.  LLM Robotics Workbench: A highly constrained testbed designed to optimize and refine small-parameter, low-latency LLMs (specifically qwen2.5-coder:3b via Ollama) for real-time spatial reasoning, strategy generation, and simulation-to-reality (Sim2Real) transfer.

> [!info] Reading & Retrieval Guide
> Files follow strict nomenclature to assist human filtering and LLM routing:
> * INTRODUCTION: High-level domain context and scope definition (Start here).
> * ARCHITECTURE: System logic, topological graphs, and data flows.
> * SPECIFICATION: Hardcoded schemas, APIs, coordinate frames, and math vectors.
> * CHEATPAGE: Empirically derived hacks, race-condition fixes, and known limitations.

---

## 2. Master Table of Contents (Human Readable)

### Section 1: System Overview & Core Architecture
* [[1_01_INTRODUCTION_Overall_Architecture]] - Hybrid environment goals, Gazebo integration, and the tri-agent topology.
* [[1_02_ARCHITECTURE_System_Overview]] - System map of the LLM vs Algorithmic AI paradigm.
* [[1_03_ARCHITECTURE_Control_Loops]] - Asynchronous timing disparities (10Hz vs 500-2000ms).
* [[1_04_SPECIFICATION_State_Sync_FileIO]] - Disk-based I/O handling. Tracker Node writes via atomic POSIX-Rename (`os.replace`) to RAM-Disk/tmpfs.
* [[1_05_CHEATPAGE_Race_Conditions]] - Mitigating deadlocks via atomic operations.
* [[1_06_ARCHITECTURE_JSON_Thread_Spawning]] - Standard-Twist-Interface for diff-drives via dynamic thread-closures (`def task`). Explicit removal of OOP HALs.

### Section 2: ROS 2 Protocols & Realtime Engine Nodes (V5)
* [[2_01_INTRODUCTION_ROS2_Protocol_Stack]] - Global /gazebo/model_states ingestion.
* [[2_02_ARCHITECTURE_Optional_Modules]] - Standalone Matplotlib-Renderer for 2D-Pitch real-time feedback and teleop channels.
* [[2_03_SPECIFICATION_Coordinate_Frames]] - 3D Quaternions to 2D spatial coordinates.
* [[2_04_ARCHITECTURE_V5_Engine_Nodes]] - Refcat << 'EOF' > 00_MASTER_INDEX.md
---
id: 00_MASTER_INDEX
title: "ROS2K Master Documentation Index"
type: INDEX
tags: [index, architecture, roadmap, v5, hybrid-os, glossary, onboarding]
last_modified: 2026-05-31
version: v5_release
author: Technical Architecture Team
---

# ROS2K Master Documentation Index

> [!info] Human Summary
> This document is the strict table of contents and file directory for the ROS2K hybrid robotics project. It maps the documentation covering the dual-goal architecture (RoboCup and LLM workbench), hardware integration, AI topologies, and the new V5 Hybrid OS (Docker & Native) infrastructure.

> [!abstract] LLM Context Anchor
> Retrieve this file first to understand the overarching repository structure and to locate specific domain documents. This index strictly omits graphical topology generation and agile terminology.

## 1. Scope & Objectives
The ROS2K architecture serves two concurrent objectives:
1.  RoboCup Development Environment: An exploratory platform utilizing Gazebo, ROS 2 topologies, and bidirectional communication to orchestrate mixed-reality scenarios integrating simulated robots, physical hardware, and LLM-driven agents.
2.  LLM Robotics Workbench: A highly constrained testbed designed to optimize and refine small-parameter, low-latency LLMs (specifically qwen2.5-coder:3b via Ollama) for real-time spatial reasoning, strategy generation, and simulation-to-reality (Sim2Real) transfer.

> [!info] Reading & Retrieval Guide
> Files follow strict nomenclature to assist human filtering and LLM routing:
> * INTRODUCTION: High-level domain context and scope definition (Start here).
> * ARCHITECTURE: System logic, topological graphs, and data flows.
> * SPECIFICATION: Hardcoded schemas, APIs, coordinate frames, and math vectors.
> * CHEATPAGE: Empirically derived hacks, race-condition fixes, and known limitations.

---

## 2. Master Table of Contents (Human Readable)

### Section 1: System Overview & Core Architecture
* [[1_01_INTRODUCTION_Overall_Architecture]] - Hybrid environment goals, Gazebo integration, and the tri-agent topology.
* [[1_02_ARCHITECTURE_System_Overview]] - System map of the LLM vs Algorithmic AI paradigm.
* [[1_03_ARCHITECTURE_Control_Loops]] - Asynchronous timing disparities (10Hz vs 500-2000ms).
* [[1_04_SPECIFICATION_State_Sync_FileIO]] - Disk-based I/O handling. Tracker Node writes via atomic POSIX-Rename (`os.replace`) to RAM-Disk/tmpfs.
* [[1_05_CHEATPAGE_Race_Conditions]] - Mitigating deadlocks via atomic operations.
* [[1_06_ARCHITECTURE_JSON_Thread_Spawning]] - Standard-Twist-Interface for diff-drives via dynamic thread-closures (`def task`). Explicit removal of OOP HALs.

### Section 2: ROS 2 Protocols & Realtime Engine Nodes (V5)
* [[2_01_INTRODUCTION_ROS2_Protocol_Stack]] - Global /gazebo/model_states ingestion.
* [[2_02_ARCHITECTURE_Optional_Modules]] - Standalone Matplotlib-Renderer for 2D-Pitch real-time feedback and teleop channels.
* [[2_03_SPECIFICATION_Coordinate_Frames]] - 3D Quaternions to 2D spatial coordinates.
* [[2_04_ARCHITECTURE_V5_Engine_Nodes]] - Referee Node (Bounds/Resets), Score Node (Torlinien/Match-Score), and state_aggregator.py (Unified Aggregated Worldstate).

### Section 3: AI Agents & Control Logic
* [[3_01_INTRODUCTION_AI_Teams_Overview]] - Team Blue (Cognitive) vs. Team Red (Algorithmic).
* [[3_02_ARCHITECTURE_TeamBlue_LLM]] - REST API payload structures. Direct integration of `qwen2.5-coder:3b` via Ollama REST API (Port 11434).
* [[3_03_CHEATPAGE_Qwen_Latency]] - Ollama configuration parameters. Must run strictly in User-Space, not as a systemd service.
* [[3_04_SPECIFICATION_TeamBlue_Failsafes]] - LLM physical safety constraints and bounding boxes.
* [[3_05_ARCHITECTURE_TeamRed_Algorithmic]] - Deterministic "Team Red" in Python as control group (Rule-based State Machine).
* [[3_06_SPECIFICATION_TeamRed_Failsafes]] - Hardcoded engine cutoffs for Team Red.
* [[3_07_CHEATPAGE_AI_Edge_Cases]] - Kinematic hacks, resolving LLM hysteresis, orbital singularities.
* [[3_08_ARCHITECTURE_Dynamic_Prompting]] - Pre-Flight Compiler (`setup_r2k.py`) for dynamic prompt compilation and Relay-Mapping before boot.

### Section 4: Edge Hardware Integration & HAL (V5 Sim2Real)
* [[4_01_INTRODUCTION_Edge_Hardware]] - The unified `ollama_sandbox_bridge.py` routing logic.
* [[4_02_ARCHITECTURE_ESP32_microROS]] - Namespace Isolation (`/bot1/`) to strictly separate hardware communication and prevent DDS collisions.
* [[4_03_SPECIFICATION_ESP32_QoS]] - Asymmetrical Quality of Service (BEST_EFFORT vs RELIABLE).
* [[4_04_CHEATPAGE_ESP32_Odometry]] - Implementing Dead Reckoning (t = d / v).
* [[4_05_ARCHITECTURE_BoosterK1_Props]] - Booster K1 proprietary Locomotion-API.
* [[4_06_SPECIFICATION_BoosterK1_Integration]] - JSON RPC Payload API for Booster K1 using API-Codes 2000 (Failsafe/Prep) and 2001 (Active Locomotion).
* [[4_07_CHEATPAGE_BoosterK1_Odometry]] - Physical slip and odometry drops.
* [[4_08_ARCHITECTURE_Native_microROS_U22]] - Native `micro-ROS-agent` compiled in C++ (`uros_ws`) to overcome FastDDS Shared-Memory blockades on Ubuntu 22.04.

### Section 5: Hybrid OS Infrastructure (Docker & Native)
* [[5_01_INTRODUCTION_Dual_OS_Topology]] - Hybrid OS Topology: Ubuntu 22.04 runs 100% natively (0ms latency), Ubuntu 24.04 encapsulated via Docker-Compose. X11-Forwarding (`/tmp/.X11-unix`) for GUI-Passthrough.
* [[5_02_SPECIFICATION_Docker_Networking]] - Forcing `network_mode: host` and dynamic generation of `COMPOSE_PROJECT_NAME` to prevent container collisions.
* [[5_03_INTRODUCTION_Build_Scratch]] - Workspace compilation (colcon build) and symlinks.
* [[5_04_CHEATPAGE_Nvidia_Xid31_Suspend_Bug]] - Suspend-Bug Diagnostics: Kernel repair for Nvidia VRAM loss (Xid 31 MMU Fault) via `NVreg_PreserveVideoMemoryAllocations=1` and `nvidia-suspend.service`.

### Section 6: Data Schemas & System Lifecycle
* [[6_01_SPECIFICATION_Data_Schemas]] - JSON payload structures for Worldstate, Strategies, and dynamic Relay-Profiles (`active_relay.json`) controlled via `--relay` flags.
* [[6_02_CHEATPAGE_System_Lifecycle]] - `0.2s Asynchronous Watchdog` replacing "Nuke & Pave" (fires Kinematic Freeze Twist-zeroes and kills via `pkill -9`). `.bashrc Immunity` enforcing `ROS_DOMAIN_ID=0` and `rmw_fastrtps_cpp`.
* [[6_03_CHEATPAGE_CLI_Ergonomics]] - System CLI launch flags, execution parameters, and the complete deprecation of legacy scripts.

---

## 3. Gemini Custom Agent (RAG Knowledge Base)
This project maintains a highly condensed, RAG-optimized documentation set specifically designed for LLM-based coding assistants (Gems/Custom GPTs). These files bundle the detailed human chapters above into semantic "Power Files" with strict constraints to prevent hallucination.

* META_KNOWLEDGE_ROUTER.md - Semantic Glossary and Inverted Index for RAG routing.
* 1_CORE_ARCHITECTURE_AND_SYNC.md
* 2_ROS2_PROTOCOLS_AND_FRAMES.md
* 3_AI_LOGIC_AND_EDGE_CASES.md
* 4_EDGE_HARDWARE_SIM2REAL.md
* 5_HYBRID_INFRASTRUCTURE_V5.md
* 6_DATA_SCHEMAS_AND_LIFECYCLE.md

---

## 4. Glossary
* tracker_node.py: A continuous ROS 2 Python node that subscribes to Gazebo telemetry and converts quaternions into 2D cartesian data written to Worldstate.json at 10Hz.
* r2k_evaluator.py: A synchronous daemon polling the aggregated world state that manages blocking HTTP POST requests directly to the Ollama REST API. (Requires `shared_state/` directory to prevent `FileNotFoundError`).
* ollama_sandbox_bridge.py (Bridge): The central ROS 2 node that reads current_strategy.json and active_relay.json, dynamically translating LLM vectors into standardized Twist messages or proprietary JSON RPC Payloads without relying on OOP HALs.
* setup_r2k.py: The Pre-Flight Compiler that dynamically stitches prompts together and handles the routing logic by generating the `active_relay.json` profile.
* 0.2s Asynchronous Watchdog: Replaces the old Nuke & Pave (`kill_r2k.sh`). A fast-polling mechanism that detects UI closure, fires asynchronous Twist-zero vectors (Kinematic Freeze), and terminates the system via SIGKILL (`pkill -9`) to prevent RCLError tracebacks and zombie processes.
* Kinematic Freeze: The failsafe process of publishing explicit zero-velocity vectors or API Code 2000 standby commands to physical hardware right before system teardown, preventing runaway robots.
* .bashrc Immunity: The hardcoded initialization of `ROS_DOMAIN_ID=0` and `rmw_fastrtps_cpp` in the `launch_r2k.sh` script to block DDS collisions caused by faulty user environment variables.

---

## 5. Q&A: Architectural Design Decisions

Q: How does the system handle the extreme speed disparity between hardware constraints and LLM generation?
A: By decoupling the architecture into two asynchronous domains. The execution layer (ollama_sandbox_bridge.py) spawns detached 10Hz PID closures that maintain constant hardware Quality of Service (QoS) heartbeats. Simultaneously, the perception layer (r2k_evaluator.py) waits for the 500-2000ms inference pulse without blocking the physical motor loops.

Q: How is the physical hardware addressed natively?
A: Hardware is mapped dynamically via `--relay` profiles passed to the CLI. Standard Differential Drive robots receive standard `geometry_msgs/Twist`, whereas proprietary systems like the Booster K1 receive serialized JSON strings over isolated namespaces (`/bot1/LocoApiTopicReq`). In V5, Ubuntu 22.04 utilizes a native `micro-ROS-agent` compiled in `uros_ws` to bypass FastDDS Docker limitations.

Q: How is Team Red controlled?
A: Team Red acts as the baseline control group. It is driven by `rule_evaluator_red.py`, which is a deterministic algorithmic state machine. It has been upgraded with Algorithmic Staging (calculating waypoints 0.6m behind the ball) and triggers the same Phantom Kick (`/gazebo/set_entity_state`) as Team Blue, operating instantaneously without the LLM.

---

## 6. Future Work & Roadmap (WIP)

### Epic 1: Architectural Refactoring
* Task 1.1: Document and transfer all hardcoded launch files into version control.
* Task 1.2: Expand Section 2 Documentation to fully detail the new V5 engine nodes (referee_node, score_node, state_aggregator).

### Epic 2: Core Enhancements
* Sim2Real Hardware Bridging: Resolve the inherent localization gap between Gazebo's absolute ModelStates and physical camera tracking systems.
* Booster K1 Odometry: Investigate and patch physical slip and odometry drops occurring on the biped during sharp rotational commands.
* LLM Overfitting Prevention: Develop scripts to auto-generate diverse Worldstate.json starting matrices to prevent qwen2.5-coder:3b from overfitting to fixed spawn coordinates.
EOFeree Node (Bounds/Resets), Score Node (Torlinien/Match-Score), and state_aggregator.py (Unified Aggregated Worldstate).

### Section 3: AI Agents & Control Logic
* [[3_01_INTRODUCTION_AI_Teams_Overview]] - Team Blue (Cognitive) vs. Team Red (Algorithmic).
* [[3_02_ARCHITECTURE_TeamBlue_LLM]] - REST API payload structures. Direct integration of `qwen2.5-coder:3b` via Ollama REST API (Port 11434).
* [[3_03_CHEATPAGE_Qwen_Latency]] - Ollama configuration parameters. Must run strictly in User-Space, not as a systemd service.
* [[3_04_SPECIFICATION_TeamBlue_Failsafes]] - LLM physical safety constraints and bounding boxes.
* [[3_05_ARCHITECTURE_TeamRed_Algorithmic]] - Deterministic "Team Red" in Python as control group (Rule-based State Machine).
* [[3_06_SPECIFICATION_TeamRed_Failsafes]] - Hardcoded engine cutoffs for Team Red.
* [[3_07_CHEATPAGE_AI_Edge_Cases]] - Kinematic hacks, resolving LLM hysteresis, orbital singularities.
* [[3_08_ARCHITECTURE_Dynamic_Prompting]] - Pre-Flight Compiler (`setup_r2k.py`) for dynamic prompt compilation and Relay-Mapping before boot.

### Section 4: Edge Hardware Integration & HAL (V5 Sim2Real)
* [[4_01_INTRODUCTION_Edge_Hardware]] - The unified `ollama_sandbox_bridge.py` routing logic.
* [[4_02_ARCHITECTURE_ESP32_microROS]] - Namespace Isolation (`/bot1/`) to strictly separate hardware communication and prevent DDS collisions.
* [[4_03_SPECIFICATION_ESP32_QoS]] - Asymmetrical Quality of Service (BEST_EFFORT vs RELIABLE).
* [[4_04_CHEATPAGE_ESP32_Odometry]] - Implementing Dead Reckoning (t = d / v).
* [[4_05_ARCHITECTURE_BoosterK1_Props]] - Booster K1 proprietary Locomotion-API.
* [[4_06_SPECIFICATION_BoosterK1_Integration]] - JSON RPC Payload API for Booster K1 using API-Codes 2000 (Failsafe/Prep) and 2001 (Active Locomotion).
* [[4_07_CHEATPAGE_BoosterK1_Odometry]] - Physical slip and odometry drops.
* [[4_08_ARCHITECTURE_Native_microROS_U22]] - Native `micro-ROS-agent` compiled in C++ (`uros_ws`) to overcome FastDDS Shared-Memory blockades on Ubuntu 22.04.

### Section 5: Hybrid OS Infrastructure (Docker & Native)
* [[5_01_INTRODUCTION_Dual_OS_Topology]] - Hybrid OS Topology: Ubuntu 22.04 runs 100% natively (0ms latency), Ubuntu 24.04 encapsulated via Docker-Compose. X11-Forwarding (`/tmp/.X11-unix`) for GUI-Passthrough.
* [[5_02_SPECIFICATION_Docker_Networking]] - Forcing `network_mode: host` and dynamic generation of `COMPOSE_PROJECT_NAME` to prevent container collisions.
* [[5_03_INTRODUCTION_Build_Scratch]] - Workspace compilation (colcon build) and symlinks.
* [[5_04_CHEATPAGE_Nvidia_Xid31_Suspend_Bug]] - Suspend-Bug Diagnostics: Kernel repair for Nvidia VRAM loss (Xid 31 MMU Fault) via `NVreg_PreserveVideoMemoryAllocations=1` and `nvidia-suspend.service`.

### Section 6: Data Schemas & System Lifecycle
* [[6_01_SPECIFICATION_Data_Schemas]] - JSON payload structures for Worldstate, Strategies, and dynamic Relay-Profiles (`active_relay.json`) controlled via `--relay` flags.
* [[6_02_CHEATPAGE_System_Lifecycle]] - `0.2s Asynchronous Watchdog` replacing "Nuke & Pave" (fires Kinematic Freeze Twist-zeroes and kills via `pkill -9`). `.bashrc Immunity` enforcing `ROS_DOMAIN_ID=0` and `rmw_fastrtps_cpp`.
* [[6_03_CHEATPAGE_CLI_Ergonomics]] - System CLI launch flags, execution parameters, and the complete deprecation of legacy scripts.

---

## 3. Gemini Custom Agent (RAG Knowledge Base)
This project maintains a highly condensed, RAG-optimized documentation set specifically designed for LLM-based coding assistants (Gems/Custom GPTs). These files bundle the detailed human chapters above into semantic "Power Files" with strict constraints to prevent hallucination.

* META_KNOWLEDGE_ROUTER.md - Semantic Glossary and Inverted Index for RAG routing.
* 1_CORE_ARCHITECTURE_AND_SYNC.md
* 2_ROS2_PROTOCOLS_AND_FRAMES.md
* 3_AI_LOGIC_AND_EDGE_CASES.md
* 4_EDGE_HARDWARE_SIM2REAL.md
* 5_HYBRID_INFRASTRUCTURE_V5.md
* 6_DATA_SCHEMAS_AND_LIFECYCLE.md

---

## 4. Glossary
* tracker_node.py: A continuous ROS 2 Python node that subscribes to Gazebo telemetry and converts quaternions into 2D cartesian data written to Worldstate.json at 10Hz.
* r2k_evaluator.py: A synchronous daemon polling the aggregated world state that manages blocking HTTP POST requests directly to the Ollama REST API. (Requires `shared_state/` directory to prevent `FileNotFoundError`).
* ollama_sandbox_bridge.py (Bridge): The central ROS 2 node that reads current_strategy.json and active_relay.json, dynamically translating LLM vectors into standardized Twist messages or proprietary JSON RPC Payloads without relying on OOP HALs.
* setup_r2k.py: The Pre-Flight Compiler that dynamically stitches prompts together and handles the routing logic by generating the `active_relay.json` profile.
* 0.2s Asynchronous Watchdog: Replaces the old Nuke & Pave (`kill_r2k.sh`). A fast-polling mechanism that detects UI closure, fires asynchronous Twist-zero vectors (Kinematic Freeze), and terminates the system via SIGKILL (`pkill -9`) to prevent RCLError tracebacks and zombie processes.
* Kinematic Freeze: The failsafe process of publishing explicit zero-velocity vectors or API Code 2000 standby commands to physical hardware right before system teardown, preventing runaway robots.
* .bashrc Immunity: The hardcoded initialization of `ROS_DOMAIN_ID=0` and `rmw_fastrtps_cpp` in the `launch_r2k.sh` script to block DDS collisions caused by faulty user environment variables.

---

## 5. Q&A: Architectural Design Decisions

Q: How does the system handle the extreme speed disparity between hardware constraints and LLM generation?
A: By decoupling the architecture into two asynchronous domains. The execution layer (ollama_sandbox_bridge.py) spawns detached 10Hz PID closures that maintain constant hardware Quality of Service (QoS) heartbeats. Simultaneously, the perception layer (r2k_evaluator.py) waits for the 500-2000ms inference pulse without blocking the physical motor loops.

Q: How is the physical hardware addressed natively?
A: Hardware is mapped dynamically via `--relay` profiles passed to the CLI. Standard Differential Drive robots receive standard `geometry_msgs/Twist`, whereas proprietary systems like the Booster K1 receive serialized JSON strings over isolated namespaces (`/bot1/LocoApiTopicReq`). In V5, Ubuntu 22.04 utilizes a native `micro-ROS-agent` compiled in `uros_ws` to bypass FastDDS Docker limitations.

Q: How is Team Red controlled?
A: Team Red acts as the baseline control group. It is driven by `rule_evaluator_red.py`, which is a deterministic algorithmic state machine. It has been upgraded with Algorithmic Staging (calculating waypoints 0.6m behind the ball) and triggers the same Phantom Kick (`/gazebo/set_entity_state`) as Team Blue, operating instantaneously without the LLM.

---

## 6. Future Work & Roadmap (WIP)

### Epic 1: Architectural Refactoring
* Task 1.1: Document and transfer all hardcoded launch files into version control.
* Task 1.2: Expand Section 2 Documentation to fully detail the new V5 engine nodes (referee_node, score_node, state_aggregator).

### Epic 2: Core Enhancements
* Sim2Real Hardware Bridging: Resolve the inherent localization gap between Gazebo's absolute ModelStates and physical camera tracking systems.
* Booster K1 Odometry: Investigate and patch physical slip and odometry drops occurring on the biped during sharp rotational commands.
* LLM Overfitting Prevention: Develop scripts to auto-generate diverse Worldstate.json starting matrices to prevent qwen2.5-coder:3b from overfitting to fixed spawn coordinates.
