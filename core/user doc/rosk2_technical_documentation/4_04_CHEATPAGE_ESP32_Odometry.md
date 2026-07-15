---
id: 4_04
title: "ESP32 Odometry & Dead Reckoning"
type: CHEATPAGE
tags: [odometry, dead-reckoning, kinematics, hacks, kinematic-freeze]
last_modified: 2026-05-31
version: v5_release
---
# ESP32 Odometry & Dead Reckoning

> [!info] Human Summary
> Explains the mathematical hacks used to estimate physical robot positions when absolute camera tracking fails, and details the explicit stop-vector commands used to prevent hardware from running endlessly.

> [!abstract] LLM Context Anchor
> Physical hardware lacks absolute global coordinates. The Bridge defaults to Dead Reckoning (Koppelnavigation) via `t = d / v`. To prevent infinite motor execution upon thread death, explicit zero-velocity vectors must be published redundantly.
> **[NEW in v5]:** The redundant stop-vector concept is now elevated to a system-wide failsafe. The `0.2s Asynchronous Watchdog` in `launch_r2k.sh` fires an instantaneous "Kinematic Freeze" (all-zero Twist vectors) before terminating the ROS 2 network, ensuring hardware halts even if the Python bridge crashes.

## 1. System Topology of Dead Reckoning Execution

**[DEPRECATED in v4] Original Thread Topology:**
This diagram shows the time-based mathematical loop used when real-time wheel encoder feedback is deemed untrustworthy.

~~~mermaid
graph TD
    subgraph LLM ["JSON Tactic"]
        Target["Move 1.0m Forward"]
    end

    subgraph Bridge ["Dead Reckoning Thread"]
        Math["Calculate Time"]
        Pub["Publish linear 0.5"]
        Sleep["time.sleep Time"]
        Stop["Publish Zeros x3"]
    end

    subgraph Hardware ["ESP32 Motors"]
        Act["Execute Blind"]
    end

    Target --> Math
    Math --> Pub
    Pub --> Sleep
    Sleep --> Stop
    Pub --> Act
    Stop -->|Emergency Halt| Act

    style Stop fill:#fcc,stroke:#c00
~~~

**[NEW in v5] Validated V5 Execution Topology:**
The local thread topology remains identical within `ollama_sandbox_bridge.py`, but is now backed by the OS-level Watchdog for guaranteed termination.

~~~mermaid
graph TD
    subgraph AI ["qwen2.5-coder:3b"]
        Target["Move 1.0m Forward"]
    end

    subgraph Bridge ["ollama_sandbox_bridge.py Thread"]
        Math["Calculate Time"]
        Pub["Publish linear 0.5"]
        Sleep["time.sleep Time"]
        Stop["Publish Zeros x3"]
    end

    subgraph OS_Level ["launch_r2k.sh Watchdog"]
        Panic["0.2s UI Polling"]
        Freeze["Kinematic Freeze (Twist 0.0)"]
    end

    subgraph Hardware ["Yahboom ESP32"]
        Act["Execute Blind"]
    end

    Target --> Math
    Math --> Pub
    Pub --> Sleep
    Sleep --> Stop
    Pub --> Act
    Stop -->|Local Halt| Act
    Panic -->|On UI Close| Freeze
    Freeze -->|Global Halt Override| Act

    style Stop fill:#fcc,stroke:#c00
    style Freeze fill:#fcc,stroke:#c00
~~~

## 2. Architectural Logic & Data Flow
**[DEPRECATED in v4] Legacy Flow:**
When transitioning from Gazebo to cheap ESP32 hardware, optical wheel encoders often drop ticks, rendering local `/odom` useless for precise PID feedback. 

To bypass this, ROS2K falls back on **Dead Reckoning**. If the LLM commands a move of 1.0 meters, the Bridge assigns a static velocity (e.g., `0.5 m/s`). It calculates the execution time (`t = 1.0 / 0.5 = 2.0 seconds`). The thread publishes the velocity, sleeps for 2.0 seconds blindly, and then executes a stop sequence.
**The Infinite Spin Failsafe:** If a UDP packet containing a stop vector is lost over the Wi-Fi hotspot, the ESP32 will continue driving forever. The Bridge mitigates this by publishing an explicit array of stop vectors (`linear.x = 0.0`) three times in rapid succession at the end of every dynamic task.

**[UPDATE in v5] V5 Hardware Reality:**
The `qwen2.5-coder:3b` AI expects precise coordinate execution. However, `ollama_sandbox_bridge.py` still relies strictly on this blind `t = d / v` calculation for standard diff-drives. If the local 3x stop loop fails due to a FastDDS packet drop, the physical robot will run away. The V5 architecture delegates ultimate safety to the `launch_r2k.sh` Watchdog, which bypasses the Python bridge entirely and uses raw `ros2 topic pub` commands to enforce the Kinematic Freeze.

## 3. Code Reference & Interfaces
> **Source:** `ollama_sandbox_bridge.py`

The conceptual blind timing execution loop and the redundant failsafe stop arrays.
~~~python
# snippet representing dead reckoning logic in the bridge
import time
from geometry_msgs.msg import Twist

def execute_dead_reckoning(distance_m, speed_ms, pub):
    duration = distance_m / speed_ms
    
    msg = Twist()
    msg.linear.x = speed_ms
    pub.publish(msg)
    
    # Blind wait execution
    time.sleep(duration)
    
    # Redundant Failsafe: Prevent infinite spin on packet loss
    stop_msg = Twist()
    stop_msg.linear.x = 0.0
    stop_msg.angular.z = 0.0
    
    for _ in range(3):
        pub.publish(stop_msg)
        time.sleep(0.05)
~~~

## 4. Known Issues & Limitations
* Dead Reckoning cannot account for physical wheel slip on smooth surfaces. After 3-4 consecutive blind maneuvers, the physical robot's actual position will drift significantly from the LLM's tracked state.
* Battery voltage drops alter the physical top speed, making the `t = d / v` calculation increasingly inaccurate over a long session.
* **[NEW in v5] Watchdog Race Condition:** If the ROS 2 DDS daemon (FastRTPS) crashes simultaneously with the UI, the Watchdog's `ros2 topic pub` Kinematic Freeze command will fail to transmit, requiring manual physical intervention.

## 5. Glossary
* **Dead Reckoning (Koppelnavigation):** Estimating current position based upon a previously determined position, incorporating known estimated speeds over elapsed time.
* **Stop Vector:** A `geometry_msgs/Twist` message where all linear and angular axes are explicitly set to `0.0`.
* **[NEW in v5] Kinematic Freeze:** The V5 architectural failsafe that explicitly publishes zero-velocity limits to all active relay profiles immediately prior to shutting down the environment.
