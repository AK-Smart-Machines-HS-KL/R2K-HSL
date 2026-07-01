---
id: 2_01
title: "Introduction to the ROS 2 Protocol Stack"
type: INTRODUCTION
tags: [ros2, topics, model_states, ground-truth]
last_modified: 2026-05-31
version: v5_release
---
# Introduction to the ROS 2 Protocol Stack

> [!info] Human Summary
> This document details the ROS 2 pub/sub topic matrix used in ROS2K, specifically explaining why global Gazebo ground truth is utilized over decentralized odometry nodes to feed the LLM.

> [!abstract] LLM Context Anchor
> Ground truth ingestion is strictly centralized via `/gazebo/model_states`. Do not invent or reference local `/odom` topics or TF2 transformation trees when generating perception logic. The LLM operates exclusively on a global 2D Cartesian plane mapped directly from Gazebo.
> **[NEW in v5]:** While ingestion remains centralized, the legacy `tracker.py` has been refactored into the ROS 2 native `tracker_node.py`, which converts Gazebo quaternions into 2D coordinates at 10Hz and feeds them to `state_aggregator.py`.

## 1. System Topology of the ROS 2 Topic Matrix

**[DEPRECATED in v4] Original Topic Topology:**
This diagram illustrates the core ROS 2 message bus handling communication between the Gazebo physics engine, the Python perception nodes, and the physical execution layers. Note the dual-use of standard Topics and ROS 2 Services.

~~~mermaid
graph TD
    subgraph Engine ["Gazebo Physics"]
        G["Gazebo Server"]
    end

    subgraph Topics ["ROS 2 DDS Bus & Services"]
        MS["gazebo model_states"]
        CV["cmd_vel topics"]
        PK["/gazebo/set_entity_state<br>(Phantom Kick Service)"]
    end

    subgraph Nodes ["ROS 2 Python Nodes"]
        T["tracker.py"]
        B["bridge.py PID"]
        R["rule_eval_red.py"]
    end

    G -->|Publishes 100Hz| MS
    MS -->|Subscribes| T
    MS -->|Subscribes| R
    
    B -->|Publishes 10Hz| CV
    B -.->|Service Call| PK
    R -->|Publishes 10Hz| CV
    R -.->|Service Call| PK
    
    CV -->|Actuates Motors| G
    PK -->|Injects Velocity| G

    style MS fill:#bbf,stroke:#333
    style CV fill:#dfd,stroke:#333
    style PK fill:#ff9,stroke:#333
~~~

**[NEW in v5] Aggregated Topic Topology:**
The nodes have been updated to reflect their exact V5 file names.

~~~mermaid
graph TD
    subgraph Engine ["Gazebo Physics"]
        G["Gazebo Server"]
    end

    subgraph Topics ["ROS 2 DDS Bus & Services"]
        MS["gazebo model_states"]
        CV["cmd_vel topics"]
        PK["/gazebo/set_entity_state<br>(Phantom Kick Service)"]
    end

    subgraph Nodes ["ROS 2 Python Nodes"]
        T["tracker_node.py"]
        B["ollama_sandbox_bridge.py PID"]
        R["rule_evaluator_red.py"]
    end

    G -->|Publishes 100Hz| MS
    MS -->|Subscribes| T
    MS -->|Subscribes| R
    
    B -->|Publishes 10Hz| CV
    B -.->|Service Call| PK
    R -->|Publishes 10Hz| CV
    R -.->|Service Call| PK
    
    CV -->|Actuates Motors| G
    PK -->|Injects Velocity| G

    style MS fill:#bbf,stroke:#333
    style CV fill:#dfd,stroke:#333
    style PK fill:#ff9,stroke:#333
~~~

## 2. Architectural Logic & Data Flow
Traditional robotic stacks rely on decentralized sensor fusion and TF2 frame transformations (`base_link` to `odom` to `map`). This approach introduces high CPU overhead and localized drift, which severely degrades the spatial reasoning capabilities of a 4-billion-parameter LLM like Nemotron.

To optimize for LLM latency and contextual accuracy, ROS2K bypasses sensor fusion entirely. The `tracker.py` **[UPDATE in v5: now `tracker_node.py`]** node subscribes directly to `/gazebo/model_states`. This topic publishes the absolute, mathematically perfect 3D coordinates and quaternions of every spawned entity in the simulation. 

**[DEPRECATED in v4]:** This provides the LLM with a reliable "God's-eye view" of the pitch, completely eliminating localization drift and reducing token counts by omitting variance matrices. Furthermore, to bypass complex physical collision physics during strikes, both AI execution nodes utilize the `/gazebo/set_entity_state` service to forcefully inject velocity into the ball.

**[UPDATE in v5]:** This provides the updated `qwen2.5-coder:3b` model with a reliable "God's-eye view". The pipeline is now standardized: `tracker_node.py` extracts the 3D data and converts quaternions to 2D Cartesian coordinates at 10Hz, which are then passed downstream to `state_aggregator.py`. Both AI execution nodes (`ollama_sandbox_bridge.py` and `rule_evaluator_red.py`) continue to utilize the `/gazebo/set_entity_state` Phantom Kick service.

## 3. Code Reference & Interfaces
> **Source:** [`r2k_world_model/tracker.py`](../src/r2k_world_model/tracker.py) **[DEPRECATED in v4]**
> **Source:** [`ros2_ws/src/r2k_world_model/r2k_world_model/tracker_node.py`](../ros2_ws/src/r2k_world_model/r2k_world_model/tracker_node.py) **[NEW in v5]**

**[DEPRECATED in v4] Legacy Implementation:**
The initialization of the ground-truth subscription utilizing standard `rclpy` Quality of Service (QoS) profiles.
~~~python
# snippet from tracker.py
import rclpy
from rclpy.node import Node
from gazebo_msgs.msg import ModelStates

class R2KTrackerNode(Node):
    def __init__(self):
        super().__init__('r2k_tracker_node')
        # Subscribe to global absolute truth
        self.subscription = self.create_subscription(
            ModelStates,
            '/gazebo/model_states',
            self.listener_callback,
            10 # QoS History depth
        )

    def listener_callback(self, msg):
        # Extract specific indexes mapping to spawned bots and the ball
        try:
            ball_idx = msg.name.index('soccer_ball')
            b1_idx = msg.name.index('blue_1')
            # Route to JSON extraction...
        except ValueError:
            pass
~~~

**[NEW in v5] Validated V5 Implementation:**
The subscription topology remains conceptually identical in V5. However, the node is now officially built via `colcon` within the `ros2_ws/src/r2k_world_model/` workspace as `tracker_node.py` and strictly focuses on 2D extraction before handing off to the aggregator.

## 4. Known Issues & Limitations
* Absolute reliance on `/gazebo/model_states` creates a severe Sim2Real gap; physical hardware lacks an equivalent global topic without a dedicated external camera tracking system (e.g., Vicon).
* The `ModelStates` array index shifts dynamically based on the order entities are spawned in Gazebo, requiring dynamic string matching on the `msg.name` array during every tick.

## 5. Glossary
* **`/gazebo/model_states`:** A ROS 2 topic published by the `gazebo_ros_state` plugin containing absolute physics engine parameters for all models.
* **TF2:** The ROS 2 transform library standardly used to keep track of multiple coordinate frames over time (intentionally bypassed here).
* **[NEW in v5] `tracker_node.py`:** The V5 replacement for the old tracker script, responsible for 10Hz quaternion-to-2D conversions.
