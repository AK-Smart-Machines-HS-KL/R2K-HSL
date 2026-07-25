---
id: 4_EDGE
title: "Section 4: Edge Hardware Integration (Sim2Real) (V6.2)"
type: KNOWLEDGE_BASE_POWER_FILE
tags: [esp32, booster-k1, sim2real, qos, rpc, micro-ros, set_entity_state, hardware-relay, api-2000, bot1-namespace, dead-reckoning, gazebo-pause-detection, heartbeat, nmcli, foot-slip, uros_ws, watchdog]
last_modified: 2026-07-25
version: v6.2
---
# Section 4: Edge Hardware Integration (Sim2Real)

> [!abstract] LLM Context Anchor
> **CRITICAL AXIOMS FOR RAG RETRIEVAL:**
> 1. **Dynamic Hardware Abstraction (V5):** Hardware mapping is dynamically resolved via `active_relay.json`. The Bridge checks the `hardware_type` to translate agnostic LLM (X/Y) output into standard `Twist` or proprietary `RpcReqMsg` **without relying on OOP HALs**.
> 2. **Namespace Isolation:** Physical robots NO LONGER operate on global root topics. The Booster K1 and Yahboom bots are strictly isolated into hardware namespaces (e.g., `/bot1/LocoApiTopicReq`) to prevent data collisions.
> 3. **Booster K1 API Protocols:** The biped NEVER uses standard `Twist` streams. It requires serialized JSON strings: API Code 2001 for locomotion (`vx, vy, vyaw`) and API Code 2000 for emergency stops/prep-mode.
> 4. **[NEW in v5] Native micro-ROS & Host Networking:** Physical micro-ROS components rely on a host-level Wi-Fi hotspot (`nmcli hotspot maker4`). To prevent FastDDS Shared-Memory (SHM) blockades on Ubuntu 22.04, the `micro-ROS-agent` is natively compiled and executed via `uros_ws` rather than Docker.
> 5. **Network Stability & QoS:** Parallel DDS Warmup (max 10s) using `BEST_EFFORT` polling (e.g., `/bot1/battery`) is required to stabilize UDP routes before injecting `RELIABLE` motor commands.
> 6. **Kinematics & Dead Reckoning:** When optical encoders fail, physical bots use time-based Dead Reckoning (t = d / v) with redundant stop vectors (x3). To prevent Sim2Real drift from biped foot slip, K1 angular velocity is hard-clamped to 0.4 rad/s.
> 7. **[NEW in v5] Sim2Real Failsafes & Watchdog:** The bridge monitors the `/clock` topic to instantly freeze physical hardware upon Gazebo pause. During script teardown, the **0.2s Asynchronous Watchdog** explicitly fires `Twist 0.0` and `API 2000` stop commands (Kinematic Freeze) to prevent "Last Command Hold" runaways before executing `pkill -9`.

## 1. Unified System Topology

This graph illustrates the comprehensive V5 Sim2Real translation layer, native networking, and failsafe execution paths. (Adhering to strict Mermaid rendering constraints).

~~~mermaid
graph TD
    subgraph Linux_Host_OS
        CLI["launch_r2k.sh"]
        Setup["setup_r2k.py (Relay JSON)"]
        Hotspot["nmcli Wi-Fi (maker4)"]
    end

    subgraph V5_Hybrid_Network
        Bridge["Execution Bridge (No OOP HAL)"]
        Heartbeat["/clock Monitor"]
        Agent["Native uros_ws Agent (Ubuntu 22.04)"]
        G["Gazebo Physics"]
    end

    subgraph Physical_Edge
        Yahboom["Yahboom ESP32<br>/bot1/cmd_vel"]
        K1["Booster K1<br>/bot1/LocoApiTopicReq"]
    end

    CLI --> Setup
    Setup -->|"active_relay.json"| Bridge
    CLI -->|"Spawns"| Hotspot
    CLI -->|"Spawns"| Agent
    Hotspot -->|"UDP 8888"| Agent
    
    G -.->|"100Hz Heartbeat"| Heartbeat
    Heartbeat -->|"If Timeout"| Bridge
    
    Bridge -->|"virtual"| G
    Bridge -->|"yahboom - Dead Reckoning"| Agent
    Bridge -->|"k1 - JSON RPC"| Agent
    Agent --> Yahboom
    Agent --> K1
~~~

## 2. Core Constraints & Data Flow

### A. Dynamic Hardware Abstraction (Relay Profiles)
* **Problem:** Hardcoding hardware routes breaks modularity when testing purely in simulation.
* **Constraint:** The Bridge dynamically reads `active_relay.json` (e.g., `only_sim_bots`, `hardware_mirror`). It parses the LLM's generic X/Y coordinates and utilizes the `hardware_type` key to serialize the correct protocol, keeping the LLM completely hardware-agnostic. Phantom Kicks are always routed virtually via `/gazebo/set_entity_state`, bypassing physical mesh collisions entirely.

### B. ESP32 micro-ROS & Native Host Networking (V5)
* **Problem:** Standard Docker bridge networks block the UDP Multicast required by XRCE-DDS node discovery for ESP32 hardware. Furthermore, running the agent in Docker on Ubuntu 22.04 blocks FastDDS Shared-Memory (SHM).
* **Constraint:** The launch script uses `nmcli` on the Linux host to create a dedicated Wi-Fi hotspot (`maker4`). On Ubuntu 22.04, the system completely bypasses Docker for micro-ROS, utilizing the natively compiled `uros_ws` agent with `.bashrc Immunity` (`ROS_DOMAIN_ID=0`).

### C. Booster K1 Locomotion API (Codes 2000/2001)
* **Problem:** Bipeds require complex gait state machines (Stand to Trot) and cannot natively ingest ROS 2 primitive vectors.
* **Constraint:** The Bridge serializes strict JSON payloads wrapped in `std_msgs/String` on the isolated `/bot1/LocoApiTopicReq` namespace.
  * **Code 2001 (Velocity Control):** Dynamic velocity control providing `vx`, `vy`, and `vyaw` (linear-x, linear-y, angular-z).
  * **Code 2000 (State Control):** Hard Emergency Stop & Prep-Mode (`mode: 1`). Executed during teardowns, pauses, or attack maneuvers.

### D. Network Stability & Asymmetrical QoS
* **Problem:** Immediately blasting `RELIABLE` motor commands to a booting ESP32 causes buffer overflows because DDS routes take time to establish.
* **Constraint:** The `launch_r2k.sh` script executes a **Parallel DDS Warmup** (max 10s) using `BEST_EFFORT` polling (e.g., `/bot1/battery`). This safely forces the network stack to validate the path to the physical agent before `RELIABLE` commands are permitted.

### E. Physical Kinematics: Dead Reckoning & Foot Slip
* **Problem:** Optical wheel encoders fail, Wi-Fi UDP packets drop, and biped feet slip on smooth floors during sharp turns, corrupting physical odometry and causing severe Sim2Real drift.
* **Constraint 1 (Dead Reckoning):** ROS2K utilizes time-based Dead Reckoning (t = d / v) for blind physical execution. To prevent infinite spins upon packet loss, all execution threads conclude with an explicit stop vector (`linear.x = 0.0`) published three times redundantly.
* **Constraint 2 (Angular Clamp):** To mitigate bipedal foot slip, the K1's rotational acceleration is artificially hard-clamped to a maximum of 0.4 rad/s in the Bridge.

### F. Gazebo Pause Detection & V5 Watchdog Teardown
* **Problem:** Physical robots do not stop if Gazebo is paused in the GUI, and they retain their last PWM signal (Last Command Hold) if the system is shut down improperly.
* **Constraint 1 (Heartbeat):** The Bridge subscribes to `/clock`. If updates cease for >0.4 seconds (and `clock_ever_received` is true), it instantly broadcasts stop commands to all hardware.
* **Constraint 2 (Watchdog Teardown):** The outdated bash `cleanup()` trap was replaced by the **0.2s Asynchronous Watchdog** in `launch_r2k.sh`. When the UI closes, the watchdog instantly injects physical stop vectors and K1 Prep-Mode commands (Kinematic Freeze) before purging the environment with `pkill -9`.

## 3. Critical Code Interfaces

**Asymmetrical QoS Warmup (`launch_r2k.sh`):**
~~~bash
# BEST_EFFORT forces network routing safely without overflowing ESP32 buffers
ros2 topic echo --once --qos-reliability best_effort /bot1/battery
~~~

**Booster K1 Velocity Control (API 2001 Payload):**
~~~json
{
  "api_id": 2001,
  "timestamp_ms": 1779222651443,
  "payload": {
    "vx": 0.25,
    "vy": 0.0,
    "vyaw": -0.12,
    "duration_ms": 500
  }
}
~~~

**Bipedal Foot-Slip Angular Clamp (`ollama_sandbox_bridge.py`):**
~~~python
# Static clamp to prevent physical foot slip on the K1
MAX_BIPED_ANGULAR = 0.4
safe_angular = max(-MAX_BIPED_ANGULAR, min(angular_error, MAX_BIPED_ANGULAR))
~~~

**Gazebo Pause Detection (`ollama_sandbox_bridge.py`):**
~~~python
def monitor_heartbeat(self):
    if self.clock_ever_received and (time.time() - self.last_clock_time > 0.4):
        self.get_logger().warn("Simulation PAUSED. Freezing physical hardware!")
        self.publish_emergency_stops()
~~~
