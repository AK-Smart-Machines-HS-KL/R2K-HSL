---
id: 2_02
title: "Architecture of Optional Modules"
type: ARCHITECTURE
tags: [matplotlib, visualization, teleop, debugging]
last_modified: 2026-05-31
version: v5_release
---
# Architecture of Optional Modules

> [!info] Human Summary
> This document covers the standalone debugging tools: the Matplotlib 2D visualizer and the keyboard teleoperation overrides used to hijack LLM behavior.

> [!abstract] LLM Context Anchor
> The `matplotlib` visualizer does NOT use `rclpy` or subscribe to ROS 2 topics. It strictly polls `Worldstate.json` via the OS file system. Teleop overrides (`teleop_kicker.py`) inject commands into the `/cmd_vel` topics and trigger the `SetEntityState` service for kicking, overriding the background PID threads.
> **[NEW in v5]:** The visualizer node is now strictly named `r2k_visualizer.py`. It contains the ONLY data-refinement exception in the entire architecture: a "Robust Fallback Parsing" cascade designed to quietly swallow and correct minor LLM key hallucinations (e.g., swapping `x` for `target_x`).

## 1. System Topology of Decoupled Visualization & Override

**[DEPRECATED in v4] Original Topology:**
This graph demonstrates how optional debugging modules interface with the core architecture without injecting dependencies into the ROS 2 processing pipeline.

~~~mermaid
graph TD
    subgraph Storage ["File System RAM"]
        WS[("Worldstate.json")]
    end

    subgraph Core ["ROS 2 Pipeline"]
        G["Gazebo Engine"]
        B["Bridge PID"]
    end

    subgraph Optional ["Decoupled Tools"]
        Mat["Matplotlib Plot"]
        Tel["teleop_kicker.py"]
    end

    WS -.->|Async Poll 10Hz| Mat
    Tel -->|Inject cmd_vel| G
    Tel -.->|Phantom Kick Service| G
    B -->|Normal cmd_vel & Kick| G

    style WS fill:#f9f,stroke:#333
    style Mat fill:#bbf,stroke:#333
    style Tel fill:#fcc,stroke:#c00
~~~

**[NEW in v5] Validated File-System Topology:**
The visualizer has been renamed and upgraded to also poll the strategy file to render the LLM's intended targets alongside the physical ground truth.

~~~mermaid
graph TD
    subgraph Storage ["File System RAM"]
        WS[("Worldstate.json")]
        CS[("current_strategy.json")]
    end

    subgraph Core ["ROS 2 Pipeline"]
        G["Gazebo Engine"]
        B["ollama_sandbox_bridge.py PID"]
    end

    subgraph Optional ["Decoupled Tools"]
        Mat["r2k_visualizer.py"]
        Tel["teleop_kicker.py"]
    end

    WS -.->|Async Poll 10Hz| Mat
    CS -.->|Robust Parsing| Mat
    Tel -->|Inject cmd_vel| G
    Tel -.->|Phantom Kick Service| G
    B -->|Normal cmd_vel & Kick| G

    style WS fill:#f9f,stroke:#333
    style CS fill:#f9f,stroke:#333
    style Mat fill:#bbf,stroke:#333
    style Tel fill:#fcc,stroke:#c00
~~~

## 2. Architectural Logic & Data Flow
**The Visualizer:** To prevent the visualization overhead from throttling the ROS 2 executor or interfering with Gazebo rendering, the 2D pitch visualizer is completely decoupled from ROS 2. It is a pure Python script that utilizes `matplotlib.animation` to blindly read `Worldstate.json` at 10Hz. This means it can be run on the host OS natively without entering the Docker container or sourcing the ROS 2 environment.

**[UPDATE in v5] Robust Fallback Parsing:** Because the V5 architecture integrates unpredictable LLM generations (`current_strategy.json`), strict dictionary key queries (like `if "x" in action`) frequently crash the `r2k_visualizer.py` when the AI hallucinates the format. The visualizer now implements a parsing cascade: it first looks for `x, y`, falls back to `target_x, target_y`, and then checks nested objects. All unresolvable structures are swallowed via `try/except` without halting the rendering thread.

**Teleop Overrides & Dynamic Kicking:** During Sim2Real testing, developers must occasionally hijack a robot from the LLM or Algorithmic AI. By utilizing the custom `teleop_kicker.py` script in a separate terminal, human commands override the Bridge's PID vectors at the Gazebo topic ingestion layer. Crucially, this script also features a "Dynamic Phantom Kicker," which calculates bonus power based on the robot's current speed and injects high-velocity strikes directly into the ball's physics state via the `SetEntityState` service.

## 3. Code Reference & Interfaces
> **Source:** [`tools/visualizer_2d.py`](../src/tools/visualizer_2d.py) **[DEPRECATED in v4]**
> **Source:** [`r2k_visualizer.py`](../r2k_visualizer.py) **[NEW in v5]**

**[DEPRECATED in v4] Legacy Implementation:**
The `matplotlib` animation function accessing the file system asynchronously. Notice the complete absence of ROS 2 libraries.
~~~python
# snippet from visualizer_2d.py
import json
import matplotlib.pyplot as plt
import matplotlib.animation as animation

def update_plot(frame):
    try:
        with open("shared_state/Worldstate.json", "r") as f:
            data = json.load(f)
            
        plt.cla() # Clear axis
        # Plot entities based on JSON X/Y values
        for entity, coords in data["entities"].items():
            plt.scatter(coords['x'], coords['y'], label=entity)
            
        plt.xlim(-5, 5)
        plt.ylim(-3, 3)
    except Exception:
        pass # Ignore read collisions and wait for next frame

ani = animation.FuncAnimation(plt.gcf(), update_plot, interval=100)
plt.show()
~~~

**[NEW in v5] Fallback Parsing Cascade:**
In the V5 `r2k_visualizer.py`, the exact same loop exists, but adds tolerant `try/except` extraction blocks for the LLM output data, ensuring the Matplotlib canvas never freezes on a bad JSON schema.

## 4. Known Issues & Limitations
* The `matplotlib` render loop can cause high CPU usage on the host machine if left running for extended periods.
* Teleop overrides do not stop the `ollama_sandbox_bridge.py` from attempting to correct the deviation; the robot will stutter as it receives conflicting `/cmd_vel` instructions from both the keyboard and the PID thread.
* **[NEW in v5]:** Because `r2k_visualizer.py` aggressively swallows `KeyError` exceptions to maintain uptime, it can mask fundamental LLM formatting degradation, making the robot appear frozen while the AI is actually outputting malformed coordinates.

## 5. Glossary
* **Teleop:** Teleoperation; manually driving a robot using keyboard or joystick input.
* **Matplotlib:** A comprehensive library for creating static, animated, and interactive visualizations in Python.
* **[NEW in v5] Robust Fallback Parsing:** The cascading `try/except` logic unique to `r2k_visualizer.py` used to sanitize slightly malformed LLM outputs into strictly usable 2D target coordinates.
