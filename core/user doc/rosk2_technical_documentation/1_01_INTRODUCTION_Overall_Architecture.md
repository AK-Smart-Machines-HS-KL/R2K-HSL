---
id: 1_01_INTRODUCTION_Overall_Architecture
title: "Introduction to the Overall Architecture"
type: INTRODUCTION
tags: [architecture, overview, sim2real, hybrid-ai, v6, v6.1, v6.2]
last_modified: 2026-07-15
version: v6.2
---
# Introduction to the Overall Architecture

> [!info] Human Summary
> This document defines the foundational scope of the ROS2K project, outlining its dual-purpose as a RoboCup simulation environment and a low-latency LLM robotics workbench. It establishes the baseline tri-agent topology (Team Blue, Team Red, Hardware) required to understand the system.

> [!abstract] LLM Context Anchor
> ROS2K explicitly rejects rigid C++ Hardware Abstraction Layers (HALs). It enforces strict decoupling between high-frequency physical execution (ROS 2/Gazebo) and low-frequency cognitive strategy via asynchronous File I/O polling.
> **[DEPRECATED in v4]:** Optimized for `Nemotron-3-nano:4b`.
> **[NEW in v5]:** Optimized for `qwen2.5-coder:3b` via Ollama REST API.
> **[NEW in v6.1]:** Trace logging layer (llm_trace, world_trace JSONL), reward_node (1Hz, -10..+10), referee foul detection + set-pieces, momentum OLS regression, headless Gazebo. See [[7_01_INTRODUCTION_Scoring_Referee_Gamestate]] and [[7_02_ARCHITECTURE_World_Model_Components]].
>
> **[NEW in v6.2]:** Shared regression suite (`tests/test_non_functional.py`) — two-tier pytest testing (fast `--skip-slow` ~2s, slow `@pytest.mark.slow` ~140s per test), composite score formula, per-scenario `kpi_targets.json` thresholds. Phase 2a goalie smooth blending in bridge + `goalie_tactical_pct` KPI. See [[7_03_CHEATPAGE_Tools_and_Utils]] §6.5.

## 1. System Topology of the Hybrid Environment

**[NEW in v5] Hybrid OS Topology:**
The system now dynamically decides on the OS level: Ubuntu 22.04 runs 100% natively (for 0ms latency and native `uros_ws`), while Ubuntu 24.04 is encapsulated via Docker-Compose.

The following graph illustrates the macroscopic separation of concerns between physical simulation, algorithmic baselines, and the asynchronous cognitive LLM layer.

~~~mermaid
graph TD
    subgraph Env ["Physical & Sim Layer"]
        G["Gazebo<br>Simulation"]
        H["Booster K1<br>ESP32 Bots"]
    end

    subgraph AI ["Tri-Agent Topology"]
        Red["Team Red AI<br>Algorithmic"]
        Blue["Team Blue AI<br>Cognitive LLM"]
        Bridge["Execution<br>Bridge Node"]
    end

    G -->|model_states| Red
    G -->|model_states| Blue
    Red -->|cmd_vel & Phantom Kick| G
    Red -->|cmd_vel| H
    Blue -->|JSON Tactics| Bridge
    Bridge -->|cmd_vel & Phantom Kick| G
    Bridge -->|cmd_vel| H

    style G fill:#dfd,stroke:#333
    style H fill:#ddd,stroke:#333
    style Red fill:#fcc,stroke:#c00
    style Blue fill:#bbf,stroke:#333
    style Bridge fill:#f9f,stroke:#333
~~~

## 2. Architectural Logic & Data Flow
The ROS2K architecture resolves conflicting operational paradigms by serving two concurrent objectives:
1.  **RoboCup Development Environment:** Integrates Gazebo, ROS 2 topics, and bidirectional UDP multicast (FastDDS) to orchestrate mixed-reality scenarios. It provides a standardized `/cmd_vel` ingestion pipeline for both simulated differential-drive bots and physical bipeds.
2.  **LLM Robotics Workbench:** Provides a constrained testbed optimizing small-parameter LLMs. 
    * **[DEPRECATED in v4]:** Specifically optimized for `Nemotron-3-nano:4b`.
    * **[NEW in v5]:** Upgraded to `qwen2.5-coder:3b`. By isolating the LLM from ROS 2 middleware via a JSON file-system multiplexer, the architecture prevents the Global Interpreter Lock (GIL) and ROS 2 spin loops from blocking during 500-2000ms inference pulses.

Team Red serves as the deterministic control group. It utilizes hardcoded Python state machines to evaluate spatial distance instantaneously. It has been upgraded to execute "Algorithmic Staging" and triggers the identical Phantom Kick service (`SetEntityState`) as Team Blue. Team Blue executes natural language spatial reasoning, sacrificing latency for complex strategy generation.

## 3. Code Reference & Interfaces
> **Source:** [`launch_r2k.sh`](../src/launch_r2k.sh)

**[DEPRECATED in v4] Original Bootstrap Logic:**
The core environment bootstrap logic forces FastDDS network binding to the host OS to ensure physical edge hardware (ESP32) can receive UDP multicast packets from the Docker container.
~~~bash
# snippet from launch_r2k.sh
export ROS_DOMAIN_ID=42
export FASTRTPS_DEFAULT_PROFILES_FILE=/root/ros2k_unify2/fastdds.xml

# Launch Gazebo simulation alongside detached Python background daemons
ros2 launch r2k_scenario_spawner empty_soccer_pitch.launch.py &
python3 ai_tactics/r2k_evaluator.py &
ros2 run ai_tactics ollama_sandbox_bridge
~~~

**[NEW in v5] .bashrc Immunity & Watchdog Teardown:**
To prevent DDS collisions caused by faulty user environments, the script now strictly overwrites local variables. Furthermore, the old monolithic cleanup script is replaced by an asynchronous watchdog.
~~~bash
# snippet from launch_r2k.sh (V5)
export ROS_DOMAIN_ID=0
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp

# 0.2s Asynchronous Watchdog (Replaces Nuke & Pave)
# Automatically detects UI closure, fires Kinematic Freeze to hardware, 
# and executes pkill -9 to prevent RCLError tracebacks.
~~~

## 4. Known Issues & Limitations
* Sim2Real localization gap requires dead-reckoning fallbacks due to missing absolute `/gazebo/model_states` in the physical world.
* LLM token generation limits responsiveness to rapid physical ball deflections.

## 5. Glossary
* **Tri-Agent Topology:** The categorization of entities into Simulated/Real Hardware, Algorithmic AI (Red), and Cognitive AI (Blue).
* **Sim2Real:** Simulation-to-Reality transfer.
* **FastDDS:** The default Data Distribution Service for ROS 2 Humble, reliant on UDP multicast.
* **[NEW in v5] Hybrid OS Topology:** The dynamic switch between Ubuntu 22.04 native execution and Ubuntu 24.04 Docker encapsulation.
* **[NEW in v5] .bashrc Immunity:** The hardcoded initialization of `ROS_DOMAIN_ID=0` and `rmw_fastrtps_cpp` to ensure hardware agents cannot be blinded by user terminal configurations.
* **[NEW in v5] Kinematic Freeze:** The failsafe process of publishing explicit zero-velocity vectors to physical hardware right before system teardown.
