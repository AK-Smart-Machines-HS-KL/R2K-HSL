---
id: 4_01
title: "Introduction to Edge Hardware Integration"
type: INTRODUCTION
tags: [sim2real, edge-hardware, esp32, booster-k1, json-rpc, hal]
last_modified: 2026-07-13
version: v6
---
# Introduction to Edge Hardware Integration

> [!info] Human Summary
> This document establishes the baseline principles for Sim2Real transfer in the ROS2K architecture, detailing how the same AI logic controls both virtual Gazebo models and physical hardware like ESP32 differential drives (Yahboom) and Booster K1 bipeds.

> [!abstract] LLM Context Anchor
> The cognitive layer (LLM) is strictly hardware-agnostic. It does not know if a robot is virtual or physical. The `ollama_sandbox_bridge.py` abstracts hardware discrepancies by routing standard vector targets to either Gazebo plugins or physical micro-ROS agents operating strictly on `ROS_DOMAIN_ID=0`.
> **[NEW in v5]:** There are NO Object-Oriented Programming (OOP) Hardware Abstraction Layers (HAL). The bridge dynamically routes payloads based on the `active_relay.json` profile. Standard differential drives receive `geometry_msgs/Twist`, while the Booster K1 receives serialized JSON RPC (API Code 2000/2001) over isolated namespaces like `/bot1/LocoApiTopicReq`.

## 1. System Topology of Sim2Real Routing

**[DEPRECATED in v4] Original Sim2Real Routing:**
This graph illustrates how the execution bridge forks the standardized AI strategy into distinct hardware and simulation pathways based on agent namespace, while universally applying the Phantom Kick to the Gazebo simulation state.

~~~mermaid
graph TD
    subgraph Cognitive ["Cognitive Layer"]
        CS["current_strategy.json"]
    end

    subgraph Execution ["bridge.py"]
        Parse["JSON Parser"]
        PID["Thread Spawner PID"]
        Kick["Phantom Kick Service"]
    end

    subgraph Virtual ["Simulation"]
        G["blue_1 cmd_vel"]
        Ball["soccer_ball State"]
    end

    subgraph Physical ["Edge Hardware"]
        ESP["bot1 Yahboom"]
        K1["k1_bot Booster"]
    end

    CS -->|Polls Tactic| Parse
    Parse -->|action: Move| PID
    Parse -->|action: Kick| Kick
    
    PID -->|Virtual Route| G
    PID -->|Physical Route A| ESP
    PID -->|Physical Route B| K1
    Kick -->|Injects Velocity| Ball

    style CS fill:#f9f,stroke:#333
    style G fill:#dfd,stroke:#333
    style Ball fill:#dfd,stroke:#333
    style ESP fill:#ddd,stroke:#333
    style K1 fill:#ddd,stroke:#333
~~~

**[NEW in v5] Validated V5 Sim2Real Routing:**
The topology reflects the unified bridge script, the dynamic relay profile, and the split between standard Twist topics and K1 proprietary RPC endpoints.

~~~mermaid
graph TD
    subgraph Cognitive ["Cognitive Layer"]
        CS["current_strategy.json"]
        AR["active_relay.json"]
    end

    subgraph Execution ["ollama_sandbox_bridge.py (No OOP HAL)"]
        Parse["JSON Parser"]
        PID["Thread Spawner (def task)"]
        Kick["Phantom Kick Service"]
    end

    subgraph Virtual ["Simulation"]
        G["blue_1 cmd_vel (Twist)"]
        Ball["soccer_ball State"]
    end

    subgraph Physical ["Edge Hardware"]
        ESP["bot1 Yahboom (Twist)"]
        K1["k1_bot Booster (JSON RPC)"]
    end

    CS -->|Polls Tactic| Parse
    AR -->|Polls Profile| Parse
    Parse -->|action: Move| PID
    Parse -->|action: Kick| Kick
    
    PID -->|Virtual Route| G
    PID -->|Physical Route A| ESP
    PID -->|Physical Route B| K1
    Kick -->|Injects Velocity| Ball

    style CS fill:#f9f,stroke:#333
    style AR fill:#f9f,stroke:#333
    style G fill:#dfd,stroke:#333
    style Ball fill:#dfd,stroke:#333
    style ESP fill:#ddd,stroke:#333
    style K1 fill:#ddd,stroke:#333
~~~

## 2. Architectural Logic & Data Flow
**[DEPRECATED in v4] Basic Flow:**
The overarching goal of ROS2K Sim2Real integration is zero-code-change deployment for the LLM. Nemotron generates a target `[X, Y]` coordinate or a `Kick` command. The Bridge handles the abstraction.

If the command is a Move, the Bridge spawns a PID thread. From this point, the architecture relies on ROS 2 namespace mapping. If the target namespace is `/blue_1`, the topic routes to the Gazebo physics plugin. If the namespace is mapped to `/bot1`, it routes over FastDDS UDP multicast to a physical ESP32 Yahboom bot on the local Wi-Fi network. 

If the command is a Kick, the Bridge bypasses the physical hardware entirely. Because the ball only exists in the mixed-reality simulation, the Bridge calculates the physical robot's tracked odometry and triggers the Gazebo `SetEntityState` service to shoot the virtual ball.

**[UPDATE in v5] Dynamic Multi-Payload Routing:**
The logic remains identical for `qwen2.5-coder:3b`, but `ollama_sandbox_bridge.py` now consults `active_relay.json` to determine the required physical payload. For standard diff-drives, it calculates the PID error and publishes a `geometry_msgs/Twist`. For the Booster K1, it constructs a JSON string containing exact API Codes (2000 for Prep, 2001 for Walk) and pushes it to `/bot1/LocoApiTopicReq`. To guarantee physical delivery and bypass Docker FastDDS Shared-Memory blockades on Ubuntu 22.04, the `micro-ROS-agent` is executed natively via `uros_ws`.

## 3. Code Reference & Interfaces
> **Source:** `triple_demo_launch.sh` **[DEPRECATED in v4]**
> **Source:** `launch_r2k.sh` **[NEW in v5]**

**[DEPRECATED in v4] Legacy Launch Script:**
The launch sequence proving the simultaneous operation of virtual (`blue_1`), wheeled physical (`bot1`), and bipedal physical (`k1_bot`) agents on the same host network.
~~~bash
# snippet from triple_demo_launch.sh
echo "🧠 Updating Strategy for TRIPLE bot setup..."
cat << 'JSON_EOF' > ./shared_state/current_strategy.json
{
  "assignments": {
    "bot1": {"action": "Move", "x": 1.0, "y": 0.0},
    "k1_bot": {"action": "Move", "x": 0.0, "y": -1.0},
    "blue_1": {"action": "Kick"}
  }
}
JSON_EOF
~~~

**[NEW in v5] Dynamic Relay Instantiation:**
In V5, hardware integration is orchestrated centrally via CLI flags passed to the Pre-Flight Compiler, injecting the correct relay mapping into the architecture before the Bridge boots.
~~~bash
# snippet from launch_r2k.sh
# Example: Deploying to physical robots instead of simulation
./launch_r2k.sh --scenario 2vs2_default --relay hardware_mirror
~~~

**[NEW in v6] Relay JSON as Single Source of Truth:**
As of v6, `relay/<name>.json` is the single source of truth for hardware topic names. `YAHBOOM_TOPIC`, `K1_TOPIC`, `YAHBOOM_NS` and `K1_NS` are derived from the JSON at launch. No hardcoded `/bot1` or `/Kev1n` references remain in `launch_r2k.sh`.

## 4. Known Issues & Limitations
* Simulation odometry is perfect; physical odometry suffers from wheel slip and battery voltage drops, causing a severe divergence between the LLM's expected reality and the physical result.
* Simultaneous execution of Gazebo and multiple physical agents requires intense network bandwidth, occasionally causing FastDDS packet drops.
* **[NEW in v5] Docker Network Isolation:** On Ubuntu 24.04 (Docker OS mode), FastDDS UDP multicast for hardware Discovery relies entirely on `network_mode: "host"`. If the host firewall blocks UDP port 8888, the micro-ROS agents will fail to appear on the DDS bus.
* **[NEW in v6] Docker uros agent startup delay:** The Docker micro-ROS agent container takes ~3s to become ready after start on Ubuntu 24. A guard `sleep 3` is added in `launch_r2k.sh` to prevent the Yahboom from missing the agent on reconnect.

## 5. Glossary
* **Sim2Real:** The process of training or defining logic in a simulation and transferring it to physical reality.
* **Yahboom:** The vendor name for the physical ESP32-based differential drive robots used in the environment.
* **[NEW in v5] JSON RPC:** Remote Procedure Call formatted as JSON. Used by the Booster K1 API to trigger internal locomotion states.
* **[NEW in v5] `active_relay.json`:** The active configuration file dictating which payload type (Twist vs RPC) the Bridge should generate for a specific namespace.
