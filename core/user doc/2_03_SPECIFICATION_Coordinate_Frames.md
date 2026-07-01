---
id: 2_03
title: "Coordinate Frames and Spatial Reductions"
type: SPECIFICATION
tags: [math, quaternions, euler, spatial-reasoning]
last_modified: 2026-05-31
version: v5_release
---
# Coordinate Frames and Spatial Reductions

> [!info] Human Summary
> Explains the mathematical pipeline used to reduce complex 3D physical data (quaternions and Z-axis depth) into a simple 2D spatial matrix that the LLM can reason about effectively.

> [!abstract] LLM Context Anchor
> Small-parameter LLMs (like Nemotron:4b) cannot reliably compute 3D Quaternions. The Tracker strictly flattens all orientation into a 1D Euler Yaw (radians) and drops Pitch, Roll, and Z-axis translation. The LLM only receives `[x, y, yaw]` keys.
> **[NEW in v5]:** The constraint remains mathematically identical for `qwen2.5-coder:3b`. The reduction math is now executed by the compiled `tracker_node.py` rather than the legacy standalone script.

## 1. System Topology of Spatial Flattening

**[DEPRECATED in v4] Original Flattening Topology:**
This graph illustrates the mathematical conversion pipeline stripping unnecessary dimensionality before feeding data into the LLM context window.

~~~mermaid
graph TD
    subgraph Input ["Gazebo ModelStates"]
        P["Pos X Y Z"]
        Q["Quat Qx Qy Qz Qw"]
    end

    subgraph Math ["tracker.py Reductions"]
        XY["Extract X and Y"]
        DropZ["Discard Z Axis"]
        Yaw["Euler Yaw Calc"]
    end

    subgraph Output ["LLM Context"]
        JSON["JSON x y yaw"]
    end

    P --> XY
    P --> DropZ
    Q --> Yaw
    XY --> JSON
    Yaw --> JSON

    style JSON fill:#f9f,stroke:#333
~~~

**[NEW in v5] Validated V5 Topology:**
The pipeline targets the exact same reduction steps, but correctly attributes the processing to the new ROS 2 engine node.

~~~mermaid
graph TD
    subgraph Input ["Gazebo ModelStates"]
        P["Pos X Y Z"]
        Q["Quat Qx Qy Qz Qw"]
    end

    subgraph Math ["tracker_node.py Reductions"]
        XY["Extract X and Y"]
        DropZ["Discard Z Axis"]
        Yaw["Euler Yaw Calc"]
    end

    subgraph Output ["LLM Context / state_aggregator.py"]
        JSON["JSON x y yaw"]
    end

    P --> XY
    P --> DropZ
    Q --> Yaw
    XY --> JSON
    Yaw --> JSON

    style JSON fill:#f9f,stroke:#333
~~~

## 2. Architectural Logic & Data Flow
LLMs process spatial reasoning using tokens, not floating-point arithmetic engines. Providing a 4-billion-parameter LLM with a 4-dimensional quaternion (`qx`, `qy`, `qz`, `qw`) to calculate relative heading results in severe hallucinations and token exhaustion.

**[DEPRECATED in v4]:** To mitigate this, `tracker.py` executes a mathematical reduction protocol. 
**[UPDATE in v5]:** To mitigate this, `tracker_node.py` executes the identical mathematical reduction protocol for the new `qwen2.5-coder:3b` model.

1.  **Translation Drop:** The Z-axis (height) is stripped completely. The playing field is strictly assumed to be a 2D Cartesian plane.
2.  **Orientation Reduction:** Roll and Pitch are discarded (assuming the robots remain upright). The Quaternion is calculated into a single Euler angle (Yaw), mapped in radians `[-pi, pi]`.

This reduction compresses the payload footprint by over 60%, drastically accelerating the Nemotron inference pulse and increasing spatial accuracy. **[UPDATE in v5: drastically accelerates the Qwen inference pulse before the data is handed over to the aggregator.]**

## 3. Code Reference & Interfaces
> **Source:** [`r2k_world_model/tracker.py`](../src/r2k_world_model/tracker.py) **[DEPRECATED in v4]**
> **Source:** [`ros2_ws/src/r2k_world_model/r2k_world_model/tracker_node.py`](../ros2_ws/src/r2k_world_model/r2k_world_model/tracker_node.py) **[NEW in v5]**

**[DEPRECATED in v4] Legacy Implementation:**
The explicit math function converting quaternion messages into LLM-friendly 2D coordinates.
~~~python
# snippet from tracker.py
import math

def euler_from_quaternion(x, y, z, w):
    # Convert a quaternion into euler angles (roll, pitch, yaw)
    t3 = +2.0 * (w * z + x * y)
    t4 = +1.0 - 2.0 * (y * y + z * z)
    yaw_z = math.atan2(t3, t4)
    return yaw_z # We only return Yaw in radians

def extract_2d_pose(pose_msg):
    # Strip Z translation
    x = round(pose_msg.position.x, 2)
    y = round(pose_msg.position.y, 2)
    
    # Strip Roll and Pitch, calculate Yaw
    q = pose_msg.orientation
    yaw = round(euler_from_quaternion(q.x, q.y, q.z, q.w), 2)
    
    return {"x": x, "y": y, "yaw": yaw}
~~~

**[NEW in v5] V5 Node Implementation:**
The mathematical reduction logic remains structurally identical to the Python snippet above, but is now integrated directly into the compiled ROS 2 `tracker_node.py` class before being published downstream to the aggregator.

## 4. Known Issues & Limitations
* If a physical robot falls over or a simulated robot flips, the Euler Yaw calculation becomes mathematically meaningless and the LLM strategy will fail until the model is reset upright.
* Aerial ball trajectories (e.g., a chip shot in soccer) cannot be reasoned about by the LLM, as it only perceives the ball's shadow on the X/Y plane.

## 5. Glossary
* **Quaternion:** A 4-element mathematical vector used by physics engines to calculate 3D rotation without encountering gimbal lock.
* **Euler Angles:** Roll, Pitch, and Yaw. The standard 3-axis human-readable representation of orientation.
* **Yaw:** Rotation around the vertical Z-axis (i.e., the compass heading of the robot on the 2D pitch).
