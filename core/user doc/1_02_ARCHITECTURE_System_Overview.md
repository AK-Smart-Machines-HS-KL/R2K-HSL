---
id: 1_02
title: "System Overview"
type: ARCHITECTURE
tags: [nodes, topology, decoupled, multiplexing]
last_modified: 2026-05-31
version: v5_release
---
# System Overview

> [!info] Human Summary
> This document maps the core ROS 2 nodes and standalone Python daemons driving the architecture. It details how physical telemetry is extracted from Gazebo and routed through decoupled file-system multiplexing to the LLM and Algorithmic AI.

> [!abstract] LLM Context Anchor
> Ground truth is exclusively ingested via `/gazebo/model_states`, never individual `/odom` topics. The visualizer relies on `matplotlib` by polling `Worldstate.json`, completely ignoring ROS 2 topic subscriptions.
> **[NEW in v5]:** The `shared_state/` folder MUST exist on the filesystem to prevent silent `FileNotFoundError` crashes during decoupled file-system multiplexing.

## 1. System Topology of Core Node Multiplexing

**[DEPRECATED in v4] Global Topic Topology:**
This graph defines the strict isolation boundary between the high-frequency ROS 2 middleware and the asynchronous cognitive reasoning engine.

~~~mermaid
graph TD
    subgraph ROS ["ROS 2 Middleware"]
        G["Gazebo<br>Engine"]
        T["tracker.py<br>ROS Node"]
        Red["rule_evaluator_red.py<br>ROS Node"]
        B["ollama_sandbox_bridge.py<br>Threader"]
    end

    subgraph FS ["File System"]
        WS[("Worldstate.json")]
        CS[("current_<br>strategy.json")]
    end

    subgraph Cog ["Cognitive Layer"]
        E["r2k_evaluator.py<br>Daemon"]
        LLM{"Ollama REST<br>Port 11434"}
    end

    G -->|model_states| T
    G -->|model_states| Red
    T -->|Write| WS
    WS -->|Read| E
    E -->|POST Context| LLM
    LLM -->|Strategy| E
    E -->|Write| CS
    CS -->|Poll 10Hz| B
    B -->|cmd_vel & Phantom Kick| G
    Red -->|cmd_vel & Phantom Kick| G

    style WS fill:#f9f,stroke:#333
    style CS fill:#f9f,stroke:#333
    style LLM fill:#bbf,stroke:#333
    style Red fill:#fcc,stroke:#c00
~~~

**[NEW in v5] Namespace Isolation & Dynamic Routing:**
The topology has been upgraded. Hardware communication is now strictly isolated via namespaces (e.g., `/bot1/`) to prevent DDS-DDS collisions. Furthermore, dynamic routing is governed by `active_relay.json` applied during startup via `--relay` CLI flags.

## 2. Architectural Logic & Data Flow
The system avoids traditional rigid C++ message passing between the AI and the hardware. 
1.  **[DEPRECATED in v4]:** `tracker.py` subscribes to the global `/gazebo/model_states`, flattens the 3D quaternions into 2D planar arrays, and dumps this to `Worldstate.json`.
    **[UPDATE in v5]:** State generation is now augmented by the `state_aggregator.py`, which unifies spatial coordinates, match score, and game state into a centralized JSON payload.
2.  **[DEPRECATED in v4]:** `r2k_evaluator.py` continuously polls this file. Upon state change, it crafts a synchronous REST POST payload to `http://172.17.0.1:11434/api/generate` combining the JSON data and `system_prompt.txt`. It writes the LLM output to `current_strategy.json` targeting `nemotron-3-nano:4b`.
    **[UPDATE in v5]:** The evaluator now directly targets `qwen2.5-coder:3b` via Ollama REST API (Port 11434) running in user-space, avoiding the Linux suspend-bug latency (Xid 31 MMU Fault).
3.  **[DEPRECATED in v4]:** `ollama_sandbox_bridge.py` polls `current_strategy.json` at 10Hz, parsing the JSON to spawn threaded execution routines publishing `/cmd_vel` to specific namespaces, or dispatching `/gazebo/set_entity_state` service calls.
    **[UPDATE in v5]:** The execution routines (HAL) utilize dynamic thread-closures (`def task()`) exclusively, rejecting OOP inheritance. Physical payloads use standard Twist for diff-drives or serialized JSON RPC (API Code 2000/2001) for the Booster K1.

## 3. Code Reference & Interfaces
> **Source:** [`ai_tactics/r2k_evaluator.py`](../src/ai_tactics/r2k_evaluator.py)

**[DEPRECATED in v4] Legacy Evaluator Logic:**
The Evaluator bypasses standard ROS 2 `rclpy` constraints to function purely as a synchronous, blocking HTTP client fetching the latest `Worldstate.json`.
~~~python
# snippet from r2k_evaluator.py
import requests, json

def poll_and_evaluate():
    with open("shared_state/Worldstate.json", 'r') as f:
        world_data = json.load(f)
        
    response = requests.post("http://127.0.0.1:11434/api/generate", json={
        "model": "nemotron-3-nano:4b",
        "prompt": json.dumps(world_data["entities"]),
        "stream": False,
        "format": "json"
    })
    
    with open("shared_state/current_strategy.json", 'w') as f:
        f.write(response.json()["response"])
~~~

**[NEW in v5] File I/O Safety Protocol:**
The above synchronous logic remains conceptually similar, but writing to the state files now mandates POSIX atomic renames (`os.replace`) to prevent `JSONDecodeError` during concurrent reads between the ROS 2 Bridge and the LLM Evaluator.

## 4. Known Issues & Limitations
* Lack of a dedicated `/reset_scenario` ROS 2 service prevents seamless automated Reinforcement Learning (RL) pipelines.
* The Matplotlib visualizer script must be manually restarted if `Worldstate.json` inode formatting breaks.
* **[DEPRECATED in v4]:** The Nuke & Pave script (`kill_r2k.sh`) was required to forcefully clear zombie processes.
* **[NEW in v5] System Teardown:** Replaced by the 0.2s Asynchronous Watchdog. It detects UI closure, fires Kinematic Freeze (Twist zero-vectors), and strictly terminates the process tree via `SIGKILL` (`pkill -9`) to prevent `RCLError` tracebacks.

## 5. Glossary
* **Decoupled Multiplexing:** Exchanging state arrays via RAM-backed disk files rather than ROS 2 pub/sub memory buses to isolate process crashes.
* **`tracker.py`:** The singular ROS 2 perception node translating Gazebo reality into LLM-readable JSON constraints.
* **[NEW in v5] `state_aggregator.py`:** The V5 engine node responsible for unifying spatial data and match scores into the Worldstate.
* **[NEW in v5] Relay Profiles:** Configuration files (e.g., `active_relay.json`) that dynamically map ROS 2 Twist commands to either simulated environments or physical hardware isolation namespaces.
