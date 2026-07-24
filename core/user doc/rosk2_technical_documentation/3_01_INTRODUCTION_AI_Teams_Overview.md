---
id: 3_01
title: "Introduction to AI Teams Overview"
type: INTRODUCTION
tags: [ai, team-blue, team-red, paradigm, v6, v6.1, v6.2]
last_modified: 2026-07-15
version: v6.2
---
# Introduction to AI Teams Overview

> [!info] Human Summary
> This document introduces the dual-brain paradigm of ROS2K. It contrasts Team Blue, which relies on a Large Language Model for spatial reasoning, with Team Red, which uses traditional deterministic algorithms.

> [!abstract] LLM Context Anchor
> ROS2K explicitly segments AI into two paradigms. Team Blue uses asynchronous JSON file multiplexing. Team Red bypasses file I/O entirely, acting as a synchronous, low-latency ROS 2 node. BOTH teams now share parity in utilizing the `/gazebo/set_entity_state` service for Phantom Kicking.
> **[NEW in v5]:** Team Blue has been upgraded to `qwen2.5-coder:3b` via Ollama REST API. Team Red serves as the deterministic Python control group relying on a Rule-based State Machine.
> **[NEW in v6.1]:** Team Red adds `AGGRESSION_FACTOR=0.15` (realistic foul scenarios), smoothstep hysteresis, boundary clamp (±1.0m restart / ±0.5m normal), blocking avoidance (P4), and freeze compliance via `restart_team` check. Team Blue adds trace logging (llm_trace). See [[3_05_ARCHITECTURE_TeamRed_Algorithmic]] and [[7_04_SPECIFICATION_Prompt_Architecture]].

## 1. System Topology of the Dual-Brain Paradigm

**[DEPRECATED in v4] Original Paradigm Topology:**
This diagram illustrates the architectural divergence between the cognitive and algorithmic control paths.

~~~mermaid
graph TD
    subgraph Physics ["Gazebo Simulation"]
        G["model_states"]
    end

    subgraph Blue ["Team Blue Cognitive"]
        WS["Worldstate.json"]
        LLM["Nemotron LLM"]
        Bridge["Execution Bridge"]
    end

    subgraph Red ["Team Red Algorithmic"]
        RedNode["rule_eval_red.py"]
    end

    G -->|Atomic Write| WS
    WS -->|Polls| LLM
    LLM -->|Strategy| Bridge
    
    G -->|Direct Sub| RedNode
    
    Bridge -->|Blue cmd_vel & Kick| G
    RedNode -->|Red cmd_vel & Kick| G

    style WS fill:#f9f,stroke:#333
~~~

**[NEW in v5] Validated V5 Paradigm Topology:**
The topology reflects the new AI core and correct script names according to the system specification.

~~~mermaid
graph TD
    subgraph Physics ["Gazebo Simulation"]
        G["model_states"]
    end

    subgraph Blue ["Team Blue Cognitive"]
        WS["Worldstate.json"]
        LLM["Qwen2.5-Coder LLM"]
        Bridge["ollama_sandbox_bridge.py"]
    end

    subgraph Red ["Team Red Algorithmic"]
        RedNode["rule_evaluator_red.py"]
    end

    G -->|Atomic Write| WS
    WS -->|Polls| LLM
    LLM -->|Strategy| Bridge
    
    G -->|Direct Sub| RedNode
    
    Bridge -->|Blue cmd_vel & Kick| G
    RedNode -->|Red cmd_vel & Kick| G

    style WS fill:#f9f,stroke:#333
~~~

## 2. Architectural Logic & Data Flow
**[DEPRECATED in v4] Team Blue (Cognitive):** Operates on a ~1Hz cycle due to LLM inference latency. It passes non-deterministic JSON targeting matrices (e.g., flat coordinate assignments and Kick overrides) to the Bridge. This abstraction mimics high-level human tactical thought.

**[UPDATE in v5] Team Blue (Cognitive):** Operates on a non-deterministic inference cycle (typically 2Hz to 5Hz, but potentially dropping to 0.14Hz if the Linux Suspend-Bug forces a silent CPU-fallback). It targets the local `qwen2.5-coder:3b` model, passing JSON targeting matrices to the Bridge.

**Team Red (Algorithmic):** Operates on a strict, ultra-low latency 10Hz cycle. It is a traditional ROS 2 node that subscribes directly to `/gazebo/model_states`. It calculates Euclidean distances instantaneously to execute two-phase "Algorithmic Staging" and publishes high-speed Twist messages and Phantom Kick service calls.

## 3. Code Reference & Interfaces
> **Source:** [`launch_r2k.sh`](../src/launch_r2k.sh)

**[DEPRECATED in v4] Legacy Launch Sequence:**
The bootstrap script demonstrating the structural separation of the two teams during runtime.
~~~bash
# snippet from launch_r2k.sh

# Team Red: Launches directly into the ROS 2 executor pool
ros2 run r2k_algorithmic rule_evaluator_red &

# Team Blue: Requires the standalone Evaluator daemon and the Bridge
python3 ai_tactics/r2k_evaluator.py &
ros2 run ai_tactics ollama_sandbox_bridge &
~~~

**[NEW in v5] Validated Launch Sequence:**
In V5, nodes are directly invoked as standalone Python processes to ensure flat process hierarchies and exact namespace resolution.
~~~bash
# snippet from launch_r2k.sh (V5)

# Team Red: Deterministic rule-based Python daemon
python3 rule_evaluator_red.py > /dev/null 2>&1 &

# Team Blue: Evaluator and Sandbox Bridge
python3 ai_tactics/r2k_evaluator.py &
python3 ai_tactics/ollama_sandbox_bridge.py > /dev/null 2>&1 &
~~~

## 4. Glossary
* **Dual-Brain Paradigm:** The architectural split between non-deterministic, language-based routing and deterministic, math-based routing.
* **[NEW in v5] Algorithmic Baseline:** Team Red acting as the mathematical control group against the LLM's non-deterministic tactical outputs.
