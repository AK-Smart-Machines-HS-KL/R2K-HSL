---
id: 2_PROTOCOLS
title: "Section 2: ROS 2 Protocols, Frames & V5 Engine Nodes (V6.1)"
type: KNOWLEDGE_BASE_POWER_FILE
tags: [ros2, model_states, quaternions, euler, visualizer, teleop, set_entity_state, v5-engine, referee, score, qwen, v6, v6.1, foul, ball-out, kick-in, hysteresis, last-touch, sideline-warp, set-piece, goal-kick, corner-kick-in, kickoff, own-half-warp, blitting]
last_modified: 2026-07-22
version: v6.2
---
# Section 2: ROS 2 Protocols, Frames & V5 Engine Nodes

> [!abstract] LLM Context Anchor
> **CRITICAL AXIOMS FOR RAG RETRIEVAL:**
> 1. **Ground Truth:** Ingestion is strictly centralized via `/gazebo/model_states`. Do NOT invent or reference local `/odom` topics or TF2 transformation trees.
> 2. **Spatial Flattening:** Small LLMs cannot compute 3D Quaternions. The Tracker strictly drops Pitch, Roll, and Z-axis translation, providing the LLM exclusively with a 2D `[x, y, yaw]` Cartesian matrix.
> 3. **V5 Realtime Pipeline:** The V5 architecture utilizes `referee_node.py`, `score_node.py`, and `state_aggregator.py` to automate rules, goal detection, and resets without human intervention.
> 4. **Decoupled Visualizer:** The `matplotlib` visualizer does NOT use `rclpy` or subscribe to ROS 2 topics. It strictly polls flat JSON states via the file system.

## 1. Unified System Topology

This graph illustrates the flow from Gazebo ground truth, through mathematical spatial reduction and the V5 Engine rule pipeline, into the decoupled file system.

~~~mermaid
graph TD
    subgraph Gazebo_Physics
        G["Gazebo Server"]
        MS["/gazebo/model_states"]
        ResetSrv["/reset_scenario (Service)"]
    end

    subgraph ROS2_V5_Engine_Nodes
        T["tracker_node.py (2D Math)"]
        Ref["referee_node.py (Bounds)"]
        Score["score_node.py (Goals)"]
        Agg["state_aggregator.py"]
    end

    subgraph RAM_Backed_FS_shared_state
        WS[("Aggregated_Worldstate.json")]
    end

    subgraph Optional_Overrides
        Vis["Matplotlib (No rclpy)"]
        Tel["teleop_kicker.py"]
    end

    G -->|Publishes 100Hz| MS
    MS --> T
    T --> Ref
    T --> Score
    T --> Agg
    Ref -->|Status Out of Bounds| Agg
    Ref -->|Calls Reset| ResetSrv
    Score -->|Score Update| Agg
    Agg -->|Atomic Write os.replace| WS

    WS -.->|Async Poll 10Hz| Vis
    Tel -->|Inject cmd_vel| G
    Tel -.->|Phantom Kick Service| G
~~~

## 2. Core Constraints & Data Flow

### A. Ground Truth Ingestion (No TF2)
* **Problem:** Traditional sensor fusion and TF2 frame transformations (`base_link` -> `odom` -> `map`) introduce high CPU overhead and localization drift, degrading the spatial reasoning of an LLM.
* **Constraint:** Bypass sensor fusion entirely. `tracker_node.py` subscribes directly to `/gazebo/model_states` to provide a mathematically perfect "God's-eye view".
* **Limitation:** The array index in `ModelStates` shifts dynamically based on Gazebo spawn order. Dynamic string matching on `msg.name` is required.

### B. Coordinate Frames & Spatial Reductions
* **Problem:** Feeding a 4-dimensional quaternion (`qx, qy, qz, qw`) to `qwen2.5-coder:3b` causes severe hallucinations and token exhaustion.
* **Constraint:** `tracker_node.py` must execute a strict reduction protocol:
  1. Strip Z-axis translation (height).
  2. Discard Roll and Pitch.
  3. Calculate the Quaternion into a single Euler angle (Yaw) in radians `[-pi, pi]`.
* **Limitation:** Aerial ball trajectories (Z-axis) are completely invisible to the LLM.

### C. V5 Realtime Rule Pipeline
* **Automated Match Flow:** To support endless Reinforcement Learning (RL) and LLM scenarios, manual scripts were replaced by a V5 node pipeline. 
* **Referee & Score:** `referee_node.py` detects out-of-bounds events and triggers `/reset_scenario`. `score_node.py` strictly monitors goal lines.
* **Aggregator Constraint:** To provide the LLM with a single atomic read-point, `state_aggregator.py` bundles the coordinate matrix, match status, and scores into one `Aggregated_Worldstate.json`.

### D. Architecture of Optional Modules
* **Visualizer Constraint:** To prevent rendering overhead from throttling the ROS 2 executor, the 2D pitch visualizer uses `matplotlib.pyplot` to blindly poll JSON files. It ignores ROS 2 middleware completely.
* **Teleop Overrides:** Developers use `teleop_kicker.py` to manually hijack a robot's `/cmd_vel`. This script calculates dynamic kick power based on the robot's current speed and triggers the `SetEntityState` service to shoot the ball.

## 3. Critical Code Interfaces

**Quaternion to Euler Reduction (`r2k_world_model/tracker_node.py`):**
~~~python
# snippet from tracker_node.py
def euler_from_quaternion(x, y, z, w):
    t3 = +2.0 * (w * z + x * y)
    t4 = +1.0 - 2.0 * (y * y + z * z)
    return math.atan2(t3, t4) # Returns only Yaw in radians

def extract_2d_pose(pose_msg):
    x = round(pose_msg.position.x, 2)
    y = round(pose_msg.position.y, 2)
    yaw = round(euler_from_quaternion(pose_msg.orientation.x, pose_msg.orientation.y, pose_msg.orientation.z, pose_msg.orientation.w), 2)
    return {"x": x, "y": y, "yaw": yaw} # Drops Z, Roll, Pitch
~~~

**V5 Aggregator Payload (`state_aggregator.py`):**
~~~json
{
  "timestamp_ms": 1779222655448,
  "match_state": "PLAYING",
  "score": {
    "blue_team": 2,
    "red_team": 0
  },
  "worldstate": {
    "ball": {"x": 1.2, "y": 0.0},
    "blue_1": {"x": -0.5, "y": 0.5, "yaw": 1.1}
  }
}
~~~

**Dynamic Teleop Phantom Kick (`teleop_kicker.py`):**
~~~python
# snippet from teleop_kicker.py
# Base power is 3.0 m/s. Add bonus power based on driving speed.
bonus_power = max(0.0, current_linear_speed * 8.0)
total_kick_power = 3.0 + bonus_power

request = SetEntityState.Request()
request.state.name = 'soccer_ball' 
request.state.reference_frame = 'R2K_1' # Kick relative to bot's facing direction
request.state.twist.linear.x = total_kick_power
self.set_state_client.call_async(request)
~~~

---

## V6 Addendum: Referee Foul Detection, Ball-Out & Unified Set-Piece Logic

> [!warning] V6 Extension (updated 2026-07-14)
> The V5 referee (goal detection + out-of-bounds reset) was extended in V6 to support
> SPL-conformant ball-out, foul detection (pushing + blocking without ball), last-touch
> tracking, structured restart logic, and **unified set-piece** (goal kick, corner
> kick-in, kickoff countdown). Source: `referee_node.py`, `core/docs/referee_rulebook.md`.
>
> **Authoritative reference:** `core/docs/referee_rulebook.md` is the complete rulebook
> with 2D diagrams, state machine, and all thresholds. This section is a summary;
> the rulebook is the single source of truth.

### Foul Detection: Pushing

Two **opposing** bots collide away from the ball. All conditions must be true simultaneously:

* **Distance:** Bot centers within `0.3m` of each other (`PUSHING_DISTANCE_THRESHOLD`).
* **Ball proximity:** Neither bot within `0.8m` of the ball (`BALL_PROXIMITY_THRESHOLD`).
* **Same-team exclusion:** Two bots on the same team near each other is NOT a foul.

**Penalty:** Offender warped to own sideline (`X = ±4.0`, random Y). Reward: `-1.0`. Cooldown: 5s per bot.

### Foul Detection: Blocking Without Ball

A bot obstructs an **opponent's** path to the ball without possessing it:

* **Distance:** Blocking bot within `0.5m` of the opponent (`BLOCKING_DISTANCE_THRESHOLD`).
* **Ball proximity:** Blocking bot NOT within `0.8m` of the ball.
* **Obstruction angle:** Bot within `30°` of the direct opponent-to-ball path (`OBSTRUCTION_ANGLE`).
* **Duration:** Blocking must be sustained for `3.0s` (`BLOCKING_MIN_DURATION`) before a foul is called.
* **Same-team exclusion:** Only checked between opponents.

**Penalty:** Offender warped to random position in own half (toward own goal). Penalty label: `own_half_warp` (was `own_goal_warp` — renamed to avoid confusion with actual goals). Reward: `-1.0`. Cooldown: 5s per bot.

### Ball-Out Detection

* **Sideline out:** `|ball_y| > 3.0`.
* **Goal-line out (no goal):** `|ball_x| > 4.5` AND `|ball_y| > 0.9` (outside goal posts).
* **Debounce:** `5` consecutive frames to prevent flickering at the boundary.

### Last-Touch Detection

* Tracks closest bot to ball each frame.
* **Hysteresis:** Same bot must be closest for `3` consecutive frames within `0.8m` to count as "last toucher".
* **No decay:** Once `last_toucher` is set, it persists indefinitely — the counter only resets when a *different* bot becomes closest. A bot that kicks the ball and moves away remains the last toucher.
* **No-toucher fallback removed:** The no-toucher neutral restart code was dead code — `last_toucher` is always set after the first few seconds of play and never cleared. See `referee_node.py:361-369`.

### Sideline Ball-Out Penalty

* **Offender:** `last_toucher` (bot responsible for kicking ball out).
* **Offender penalty:** Warped 2m inward from the sideline (`BALL_OUT_WARP_DISTANCE`).
* **Team penalty:** Entire offending team frozen for `5.0s` (`BALL_OUT_FREEZE_TIME`).
* **Ball:** Placed on the sideline where it exited, stationary.
* **Restart:** Opposing team gets the kick-in. Reward: `-0.5` (reduced penalty).
* **Status:** `ball_out` (3.0s timeout via `BALL_OUT_TIMEOUT`).

### Goal-Line Ball-Out → Unified Set Piece

Goal-line outs (ball crosses X=±4.5, wide of posts, no goal) are classified into two set-piece types via `_start_set_piece()`:

**Scenario A — Goal Kick** (attacker kicked over defender's goal line):
* Ball placed at nearer corner of goal area: `(±3.5, ±1.0)` (`GOAL_AREA_X`, `GOAL_AREA_Y`).
* Defending team gets the goal kick.
* Attacking team (offender) frozen 5s, opponents within 1.5m warped 2m away.
* Status: `goal_kick` (5.0s countdown via `SET_PIECE_COUNTDOWN`).

**Scenario B — Corner Kick-In** (defender kicked over own goal line):
* Ball placed at corner flag: `(±4.3, ±2.8)`.
* Attacking team gets the corner kick-in.
* Defending team (offender) frozen 5s, opponents within 1.5m warped 2m away.
* Status: `corner_kick_in` (5.0s countdown).

### Kickoff (after goal)

* Ball reset to center `(0, 0)`, all bots warped to kickoff positions.
* **Scoring team** frozen for 5.0s (was: conceding team frozen 3.0s — changed in V6.1).
* `restart_team` set to conceding team (opposite of scoring team) for early-termination check.
* Conceding team takes the kickoff.
* Status: `goal` (5.0s countdown).

### Early Restart Termination (V6.1)

The freeze ends immediately if the **restart team's** bot comes within `0.3m` of the ball — the 5s countdown is a maximum, not a fixed duration.

* Checked every frame in `pos_callback` after `_track_last_toucher`.
* Only the restart team's touch triggers early termination — opponent (frozen team) touches do NOT.
* `_end_restart()` clears `frozen_bots` immediately and transitions to `playing`.
* Threshold: 0.3m (matches `PUSHING_DISTANCE_THRESHOLD`).
* Applies to ALL restart types: `goal`, `ball_out`, `goal_kick`, `corner_kick_in`.

### Unified Restart Pattern

All three restart types (kickoff, goal kick, corner kick-in) follow `_start_set_piece()`:
1. Place ball at restart position.
2. Warp opponent bots within `1.5m` (`SET_PIECE_WARP_RADIUS`) radially away `2.0m` (`WARP_AWAY_DISTANCE`).
3. Freeze offending/opponent team for `5.0s` (`SET_PIECE_COUNTDOWN`).
4. Set status and start 5.0s countdown.
5. Countdown expires OR restart team touches ball → `BALL FREE` → status = `playing`.

### Visualizer Blitting (V6.1)

* `r2k_visualizer.py` was refactored from `fig.clf()` full-rebuild per frame to **blitted artist updates**.
* `init_figure()` creates all 22 artists (pitch, scatters, text, arrows, panels) ONCE.
* `update_figure()` updates existing artist data via `set_offsets()`, `set_text()`, `set_position()`, `set_visible()`.
* Frame time: ~200-500ms → ~10-30ms (~2-5 FPS → ~30+ FPS).
* `draw_empty_pitch()` removed (no longer needed).
* `plt.pause(0.04)` → `plt.pause(0.01)`, `rclpy.spin_once(timeout_sec=0.01)` → `timeout_sec=0.001`.
