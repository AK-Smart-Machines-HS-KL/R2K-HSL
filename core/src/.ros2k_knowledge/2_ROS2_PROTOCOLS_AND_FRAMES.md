---
id: 2_PROTOCOLS
title: "Section 2: ROS 2 Protocols, Frames & V5 Engine Nodes"
type: KNOWLEDGE_BASE_POWER_FILE
tags: [ros2, model_states, quaternions, euler, visualizer, teleop, set_entity_state, v5-engine, referee, score, qwen]
last_modified: 2026-05-31
version: v5_release
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
