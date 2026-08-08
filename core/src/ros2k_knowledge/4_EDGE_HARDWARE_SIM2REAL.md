---
id: 4_EDGE
title: "Section 4: Edge Hardware Integration (Sim2Real) (V6.2)"
type: KNOWLEDGE_BASE_POWER_FILE
tags: [esp32, booster-k1, sim2real, qos, rpc, micro-ros, set_entity_state, hardware-relay, api-2000, bot1-namespace, dead-reckoning, gazebo-pause-detection, heartbeat, nmcli, foot-slip, uros_ws, watchdog]
last_modified: 2026-08-05
version: v6.4
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

## V6.4 Addendum — Hardware Capability Matrix and K1 Kick Pitfalls

### Per-bot capability matrix

The relay JSON is many-to-many: a single relay can map blue_1=virtual,
blue_2=yahboom, blue_3=k1. RoboCup rules forbid mixed teams in tournaments,
but ROS2K testing/demos use mixed hardware.

| Capability | K1 (biped) | Yahboom (cam variant) | Yahboom (standard) | Trailer | Gazebo (sim) |
|---|---|---|---|---|---|
| Kick | Yes (kShoot 2024, autonomous chase) | Yes (metal push, untested, short range) | Yes (metal push, untested) | No | Yes (phantom kick) |
| Move sideways | Yes | No (diff-drive) | No (diff-drive) | No | Yes |
| Rotate in place | Yes | Yes | Yes | No (fixed axle) | Yes |
| Head rotate | Yes (kRotateHead 2004) | Yes (pan-tilt servo, lousy) | No | No | Yes (if modeled) |
| Trajectory replay | Yes (kReplayTrajectory 2028) | No | No | No | No |
| Odometry | Yes (IMU + encoders) | Yes (wheel-spin, drifts) | Yes (wheel-spin, drifts) | Yes (wheel-spin, drifts) | Yes (ground truth) |
| Fall risk | HIGH | No | No | No | No |
| Servo heating | HIGH | No | No | No | No |
| Visual ball tracking | Yes (camera on head) | Unreliable (pan-tilt, lousy) | No | No | Yes (if modeled) |
| Arrival angle control | Yes (can rotate at end) | Yes | Yes | No | Yes |

### K1 kick pitfalls (critical for real matches)

The K1's kick skills are **autonomous** — the K1 takes over and chases the
ball until kick distance is reached:

- `kShoot` (api_id 2024): autonomous shot toward goal
- `kVisualKick` (api_id 2038): autonomous kick using visual tracking

**Problem:** if the ball moves away (kicked by self, kicked by opponent, or
deflected), the K1 follows indefinitely. The bot is stuck in a chase loop
and cannot receive new assignments. This is a game-stopper.

**Solution (v7):** any bot's camera (K1 head cam primarily — Yahboom cam is
unreliable) detects ball velocity/direction change. Published as a ROS2 topic
(`/ball/motion_change`). TeamCaptain (or bridge) receives this and sends
`kChangeMode` (api_id 2000) to abort the autonomous kick skill. The bot is
then free for the next LLM assignment. No thresholds, no hysteresis —
"ball velocity changed → abort chase."

### K1 head rotation (api_id 2004)

The K1 SDK provides `kRotateHead` (api_id 2004) with parameters:
- `pitch` (float): head pitch angle
- `yaw` (float): head yaw angle (±180°)

This is independent from body locomotion (api_id 2001). The bridge can
publish head rotation commands without affecting cmd_vel / RPC 2001.
Failsafe: api_id 2000 (kChangeMode) resets head to forward position.

### K1 trajectory replay (api_id 2027/2028)

- `kRecordTrajectory` (2027): enables/disables recording of the K1's motion
  to a file on the K1's filesystem
- `kReplayTrajectory` (2028): replays a recorded trajectory from a file path
  (string parameter: `traj_file_path`)

The trajectory file format is K1-internal (likely joint angles, not Cartesian
waypoints). Cannot easily author trajectory files at runtime from (X, Y)
end-points. Pre-recording with kRecordTrajectory is the practical approach.
Future use: pre-record standard motions (walk-to-goal, walk-to-corner) and
replay by name. See ADR-A07 (TeamCaptain) for integration plan.

### Yahboom variants

- **Standard:** fixed camera, no pan-tilt, differential drive (cmd_vel)
- **Cam variant:** pan-tilt camera on top of front (servo-based, lousy
  quality — cannot rely upon for critical tracking). Can rotate head
  independently from body via servo control. Same diff-drive locomotion.
- **Kick:** both types can push the ball with the metal front bumper.
  Untested in real matches. Expected short range (~0.5m). No autonomous
  chase — the Yahboom just drives forward into the ball.

### Trailer motion model

Non-holonomic (car-like): cannot strafe, cannot rotate in place. All paths
are arc-based (drive + turn simultaneously, like a car). The path executor
(v7, TeamCaptain) needs a different interpolation for trailers vs holonomic
bots (K1, sim). No kick, no camera, no head rotation.

### Bridge changes (v6.4)

- `R2K_GOALIE_BLEND=0` (default): disables angle-block mode. Goalie stays
  at X=-4.0 with damped Y. LLM controls when goalie advances.
- Anti-collision: non-kicker bot pushed 1m away from kicker when within 0.5m
- Kick direction override: blue_1 (goalie) always kicks toward +X
- PD gain boost: lin_x = 1.2 (was 0.8) when distance > 1.0m
- `GOALIE_DEADBAND_PCT`: 0.022 → 0.015 (tighter Y tracking)
