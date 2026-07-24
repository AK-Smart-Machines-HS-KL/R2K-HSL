---
id: 4_07
title: "Booster K1 Odometry Known Issues"
type: CHEATPAGE
tags: [odometry, slip, biped, debugging, v5-roadmap]
last_modified: 2026-05-31
version: v5_release
---
# Booster K1 Odometry Known Issues

> [!info] Human Summary
> A troubleshooting guide documenting the severe physical limitations and odometry drift issues encountered when executing sharp LLM spatial strategies on the biped.

> [!abstract] LLM Context Anchor
> Bipedal odometry drops are a known, unresolved hardware constraint. Sharp angular commands cause physical foot slip, permanently severing the LLM's tracked coordinate space from the robot's physical location.
> **[NEW in v5]:** This remains a critical blocker for Sim2Real transfer in the V5 architecture. Resolving the K1 physical slip is officially tracked under Epic 2 (Core Enhancements). Until visual odometry is implemented, the static angular clamp in `ollama_sandbox_bridge.py` must remain active.

## 1. System Topology of Physical Odometry Drift

**[DEPRECATED in v4] Original Topology:**
This graph conceptualizes the Sim2Real localization gap caused by bipedal mechanical slip.

~~~mermaid
graph TD
    subgraph Commanded ["Bridge Node"]
        Cmd["High Angular Vel"]
    end

    subgraph Physical ["K1 Hardware"]
        Motors["Leg Actuation"]
        Slip["Foot Slippage Friction Loss"]
    end

    subgraph Telemetry ["ROS 2 Odom"]
        Report["Reports 90deg Turn"]
        Reality["Actually 45deg Turn"]
    end

    Cmd --> Motors
    Motors --> Slip
    Motors -->|Internal Math| Report
    Slip -->|Physical Truth| Reality

    style Slip fill:#fcc,stroke:#c00
    style Reality fill:#fff3cd,stroke:#856404
~~~

**[NEW in v5] Validated V5 Topology:**
The mechanics of the slip remain identical, but the execution layer is explicitly defined as the unified V5 Python bridge without OOP HALs.

~~~mermaid
graph TD
    subgraph Commanded ["ollama_sandbox_bridge.py"]
        Cmd["High Angular Vel Payload (Code 2001)"]
    end

    subgraph Physical ["K1 Hardware"]
        Motors["Leg Actuation"]
        Slip["Foot Slippage Friction Loss"]
    end

    subgraph Telemetry ["ROS 2 Odom"]
        Report["Reports 90deg Turn"]
        Reality["Actually 45deg Turn"]
    end

    Cmd --> Motors
    Motors --> Slip
    Motors -->|Internal Math| Report
    Slip -->|Physical Truth| Reality

    style Slip fill:#fcc,stroke:#c00
    style Reality fill:#fff3cd,stroke:#856404
~~~

## 2. Architectural Logic & Data Flow
**[DEPRECATED in v4] Legacy Flow:**
When a differential drive robot turns, its wheels maintain relatively consistent contact with the ground. When a biped turns, it must lift and swing its feet. 

If the LLM generates a strategy requiring a rapid 180-degree intercept, the Bridge will command a high angular velocity. The K1 will execute an aggressive trotting turn. However, due to low foot-friction on smooth laboratory surfaces, the physical feet slip during the swing phase. The internal IMU and leg kinematics calculate that the robot turned 90 degrees (and publishes this internally), but in physical reality, the chassis only rotated 45 degrees.

Because the system relies on dead reckoning or local odometry in the physical world, this slip permanently corrupts the robot's position relative to the global coordinates expected by the LLM.

**[UPDATE in v5]:** The underlying physics problem remains unchanged. Even though the LLM is now `qwen2.5-coder:3b`, it still expects perfect coordinate execution. The odometry drops result in severe hysteresis where the LLM believes the biped is facing the ball, but the physical robot is actually pointing away.

## 3. Code Reference & Interfaces
> **Source:** `ollama_sandbox_bridge.py`

The conceptual hack used to artificially limit bipedal rotational acceleration to preserve odometry integrity.
~~~python
# snippet representing angular constraints in ollama_sandbox_bridge.py
def execute_biped_pid(target_yaw, current_yaw, pub):
    angular_error = target_yaw - current_yaw
    
    # Static clamp to prevent physical foot slip on the K1
    MAX_BIPED_ANGULAR = 0.4
    
    safe_angular = max(-MAX_BIPED_ANGULAR, min(angular_error, MAX_BIPED_ANGULAR))
    
    # Send safe_angular to serialization pipeline...
~~~

## 4. Known Issues & Limitations
* Clamping angular velocity to `0.4` drastically increases the time required for the biped to turn and face the ball, making it tactically inferior to the wheeled bots during mixed reality matches.
* External visual odometry (e.g., AprilTags or Vicon) is strictly required to resolve this Sim2Real gap permanently (Epic 2 Roadmap).

## 5. Glossary
* **Foot Slip:** Loss of traction between the robot's end-effector and the ground, invalidating internal kinematic calculations.
* **IMU (Inertial Measurement Unit):** An electronic device that measures a body's specific force and angular rate, prone to integral drift over time.
