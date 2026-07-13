---
id: 2_PROTOCOLS
title: "Section 2: ROS 2 Protocols, Frames & V5 Engine Nodes"
type: KNOWLEDGE_BASE_POWER_FILE
tags: [ros2, model_states, quaternions, euler, visualizer, teleop, set_entity_state, v5-engine, referee, score, qwen, v6, foul, ball-out, kick-in, hysteresis, last-touch, sideline-warp]
last_modified: 2026-07-13
version: v6_active
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

## V6 Addendum: Referee Foul Detection & Ball-Out

> [!warning] V6 Extension
> The V5 referee (goal detection + out-of-bounds reset) was extended in V6 to support
> SPL-conformant ball-out, foul detection (pushing + blocking without ball), last-touch
> tracking, and structured restart logic. Source: `referee_node.py`, `core/docs/optimization_spec_v6.md`.

### Foul Detection: Pushing

Two **opposing** bots collide away from the ball. All three conditions must be true simultaneously (conjunctive, not independent):

* **Distance:** Bot centers within `0.3m` of each other.
* **Velocity:** Relative approach speed `> 0.5 m/s` (collision course).
* **Ball proximity:** Neither bot within `0.8m` of the ball (not a legitimate play).
* **Same-team exclusion:** Two bots on the same team near each other is NOT a foul — teammates may cluster defensively.

**Rationale:** If either bot is near the ball, the contact is a legitimate tackle, not a foul. The ball-proximity check prevents false positives during normal play. Same-team proximity is normal defensive play.

### Foul Detection: Blocking Without Ball

A bot obstructs an **opponent's** path to the ball without possessing it:

* **Distance:** Blocking bot within `0.5m` of the opponent-to-ball line.
* **Ball proximity:** Blocking bot NOT within `0.8m` of the ball.
* **Obstruction angle:** Bot within `30°` of the direct opponent-to-ball path.
* **Duration:** Blocking must be sustained for `3.0` seconds before a foul is called. Momentary obstruction during maneuvering is not penalized. The timer is per-blocker and resets if the blocker moves away, approaches the ball, or the angle condition breaks.
* **Same-team exclusion:** Blocking is only checked between opponents (blue blocker vs red victim and vice versa). Same-team blocking is not a foul.

**Rationale:** A bot legitimately defending near the ball is not blocking. Only a bot far from the ball that deliberately and persistently obstructs the opponent's access is penalized. The 3-second duration prevents false positives from transient crossings during normal movement.

### Foul Penalty: Sideline Warp (Pushing)

* Pushing offender is warped to `X = -4.0` (blue) or `X = +4.0` (red), `Y = random(-2.0, 2.0)`.
* Foul event published on `/match_state` with `offender`, `victim`, `type`, `position`, `penalty: "sideline_warp"`.
* `reward_node.py` applies a fixed `-1` penalty (10% of the -10..+10 scale).
* Play resumes after `1s` freeze.

### Foul Penalty: Own-Goal Warp (Blocking Without Ball)

* Blocking offender is warped to a random position in their own half towards their own goal:
  * Blue: `X = random(-4.3, -2.0)`, `Y = random(-2.8, 2.8)` (towards X=-4.5 own goal)
  * Red: `X = random(2.0, 4.3)`, `Y = random(-2.8, 2.8)` (towards X=+4.5 own goal)
* Foul event published with `penalty: "own_goal_warp"`.
* Same `-1` reward penalty and `1s` freeze as pushing.
* **Rationale:** Blocking is an obstruction foul, not a collision. Warping towards own goal penalizes the offender by forcing them back into a defensive position, which is a more thematically appropriate penalty than sideline warp.

### General Foul Properties

* **Foul detection is team-agnostic** — applies equally to blue and red bots. `rule_evaluator_red.py` has `AGGRESSION_FACTOR = 0.15` (15% chance per decision to move toward opponent) to generate realistic foul scenarios.
* Both foul types share a 5-second cooldown per offender to prevent repeated triggering.

### Ball-Out Detection

* **Sideline out:** `|ball_y| > 3.0`.
* **Goal-line out (no goal):** `|ball_x| > 4.5` AND `|ball_y| > 0.9` (outside goal width).
* **Debounce:** `5` consecutive frames at 10Hz (0.5s) to prevent flickering at the boundary.
* **Hysteresis:** Prevents oscillation when the ball bounces on the line. Without hysteresis, the referee fires spurious ball-out events every frame.

### Last-Touch Detection

* Tracks closest bot to ball each frame.
* **Hysteresis:** Same bot must be closest for `3` consecutive frames to count as "last toucher".
* On ball-out: `last_toucher` = bot with most frames closest to ball.
* **Restart team:** Opposite of `last_toucher`'s team (sideline out) or defending team (goal-line out without goal).
* **Rationale:** SPL rules require kick-in for the team that did NOT last touch the ball. Without last-touch tracking, the referee cannot determine restart entitlement.

### Restart Logic

* **Ball reset:** Referee calculates restart position and calls `/gazebo/set_entity_state` to place the ball. This is a physical/ROS action — the LLM does NOT handle ball reset.
* **Sideline restart:** Ball placed infield at the exit point; restart team = opposite of last toucher.
* **Goal-line restart (no goal):** Ball placed inside at the line; restart team = defending team.
* **Freeze:** Offending team holds position for `1.0s` before play resumes.
* **Timeout:** `3.0s` auto-transition to "playing" if no restart occurs.
