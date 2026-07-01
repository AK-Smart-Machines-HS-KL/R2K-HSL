---
id: 3_06
title: "Team Red Failsafes and Engine Cutoffs"
type: SPECIFICATION
tags: [safety, hardcodes, velocity-clamps, team-red]
last_modified: 2026-05-31
version: v5_release
---
# Team Red Failsafes and Engine Cutoffs

> [!info] Human Summary
> Details the hardcoded velocity limits and boundary shutoffs built into the Team Red algorithmic architecture to prevent Gazebo physics engine explosions.

> [!abstract] LLM Context Anchor
> Unlike Team Blue, Team Red's safety constraints do not rely on natural language prompts. They are enforced via strict Python variable clamping (`min/max`) applied to the `geometry_msgs/Twist` fields directly before publication.
> **[NEW in v5]:** In V5, the execution node `rule_evaluator_red.py` is located in the root directory to maintain a flat process hierarchy. The safety logic remains the deterministic backbone of the system, ensuring that even if Team Red's state machine logic enters an invalid path, the hardware limits remain physically enforced.

## 1. System Topology of Velocity Clamping

**[DEPRECATED in v4] Original Topology:**
This graph shows the hardware cutoff logic that intercepts the state machine's output before it reaches the ROS 2 network.

~~~mermaid
graph TD
    subgraph StateMachine ["rule_eval_red.py"]
        Logic["Action Logic"]
        msgX["msg.linear.x = 5.0"]
    end

    subgraph HardwareFailsafe ["Safety Interceptor"]
        ClampX["Clamp X to 1.5"]
        ClampZ["Clamp Z to 2.0"]
        Bounds["Check Arena Bounds"]
    end

    subgraph Topic ["ROS 2 Bus"]
        Pub["Publish cmd_vel"]
    end

    Logic --> msgX
    msgX --> ClampX
    msgX --> ClampZ
    ClampX --> Bounds
    ClampZ --> Bounds
    Bounds --> Pub

    style HardwareFailsafe fill:#f9f,stroke:#333
~~~

**[NEW in v5] Validated V5 Topology:**
The logic flow is identical to the V4 architecture, confirming that V5 maintainers have retained the robust deterministic clamping baseline.

~~~mermaid
graph TD
    subgraph StateMachine ["rule_evaluator_red.py"]
        Logic["Action Logic"]
        msgX["msg.linear.x = 5.0"]
    end

    subgraph HardwareFailsafe ["Safety Interceptor"]
        ClampX["Clamp X to 1.5"]
        ClampZ["Clamp Z to 2.0"]
        Bounds["Check Arena Bounds"]
    end

    subgraph Topic ["ROS 2 Bus"]
        Pub["Publish cmd_vel"]
    end

    Logic --> msgX
    msgX --> ClampX
    msgX --> ClampZ
    ClampX --> Bounds
    ClampZ --> Bounds
    Bounds --> Pub

    style HardwareFailsafe fill:#f9f,stroke:#333
~~~

## 2. Architectural Logic & Data Flow
Due to the high-frequency iteration of the Euclidean state machine, proportional control errors can command impossible physics (e.g., requesting a wheel velocity of 50 m/s). In Gazebo, extreme velocity commands result in physics engine instability, causing the robots to glitch through the floor or launch into the sky.

To stabilize the simulation and mirror physical hardware limitations, `rule_evaluator_red.py` intercepts the finalized `Twist` message right before `self.cmd_vel_pub.publish(msg)`. It applies a hard max/min clamp to `linear.x` and `angular.z`. Furthermore, if the robot's current telemetry indicates it has crossed the physical edge of the arena, an explicit stop vector (all zeros) is published to kill the motor immediately.

## 3. Code Reference & Interfaces
> **Source:** [`r2k_algorithmic/rule_evaluator_red.py`](../src/r2k_algorithmic/rule_evaluator_red.py) **[DEPRECATED in v4]**
> **Source:** [`rule_evaluator_red.py`](../rule_evaluator_red.py) **[NEW in v5]**

The final clamping and bounds-checking logic executed before message transmission.
~~~python
# snippet from rule_evaluator_red.py
def enforce_safety_and_publish(self, msg, current_pose):
    # Velocity Clamps (Simulating physical motor limits)
    MAX_LINEAR = 1.5
    MAX_ANGULAR = 2.0
    
    msg.linear.x = max(-MAX_LINEAR, min(msg.linear.x, MAX_LINEAR))
    msg.angular.z = max(-MAX_ANGULAR, min(msg.angular.z, MAX_ANGULAR))
    
    # Out of Bounds Engine Cutoff
    if abs(current_pose.x) > 4.5 or abs(current_pose.y) > 3.0:
        msg.linear.x = 0.0
        msg.angular.z = 0.0
        self.get_logger().warn("Red agent out of bounds. Motors killed.")
        
    self.cmd_vel_pub.publish(msg)
~~~

## 4. Known Issues & Limitations
* Clamping proportional control loops statically can cause sluggish maneuvering; an acceleration curve (jerk limit) would be more realistic than a static top-speed clamp.
* The engine cutoff requires the robot to *already* be out of bounds, meaning part of the chassis may collide with arena walls before the motors are killed.

## 5. Glossary
* **Engine Cutoff:** An emergency logic block that overrides all current commands with zero-velocity vectors to prevent damage.
* **Twist Message:** The standard ROS 2 message type (`geometry_msgs/Twist`) used to dictate linear and angular velocity in 3D space.
