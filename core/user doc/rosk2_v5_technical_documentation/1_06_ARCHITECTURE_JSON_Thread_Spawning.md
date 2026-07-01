---
id: 1_06
title: "JSON Parsing & Thread Spawning"
type: ARCHITECTURE
tags: [threading, execution, pid, bridge]
last_modified: 2026-05-31
version: v5_release
---
# JSON Parsing & Thread Spawning

> [!info] Human Summary
> Explains how the architecture translates high-level text strategies from the LLM into raw motor voltages without relying on brittle Object-Oriented hardware abstraction code. 

> [!abstract] LLM Context Anchor
> There is NO Object-Oriented Programming (OOP) Hardware Abstraction Layer (HAL). The `ollama_sandbox_bridge.py` dynamically parses text JSON constraints and uses closure functions (`def task`) on detached OS threads to manage Proportional-Integral-Derivative (PID) motor control.
> **[NEW in v5]:** Physical payloads are now dynamically routed based on `active_relay.json`. Standard differential drives receive standard `geometry_msgs/Twist`, while the Booster K1 receives serialized JSON RPC (API Code 2000/2001) over isolated namespaces (e.g., `/bot1/LocoApiTopicReq`).

## 1. System Topology of Dynamic Thread Execution

**[DEPRECATED in v4] Original Thread Execution Flow:**
This graph displays the thread manager preempting old motor commands and spawning new independent execution closures based on LLM JSON directives.

~~~mermaid
graph TD
    subgraph ThreadManager ["Bridge Node Thread"]
        Poll["Polls Strategy File"]
        Parse["Parses Target XY"]
        Kill["Sets stop_event"]
    end

    subgraph SpawnedProcesses ["Detached Closures"]
        T1["PID Thread A3 Dead"]
        T2["PID Thread A3 Active"]
    end

    G["Gazebo cmd_vel"]

    Poll --> Parse
    Parse --> Kill
    Kill -.->|Preempts| T1
    Parse -->|Spawns New| T2
    T2 -->|Publishes| G

    style T1 fill:#ccc,stroke:#333,stroke-dasharray: 5 5
    style T2 fill:#f9f,stroke:#333
~~~

**[NEW in v5] Multi-Payload Relay Flow:**
The thread spawning logic remains, but the publishing step is now augmented by the relay profiles, supporting dual payload types and namespace isolation.

~~~mermaid
graph TD
    subgraph ThreadManager ["ollama_sandbox_bridge.py Thread"]
        Poll["Polls current_strategy.json"]
        Parse["Parses active_relay.json & XY"]
        Kill["Sets stop_event"]
    end

    subgraph SpawnedProcesses ["Detached Closures"]
        T1["PID Thread (Dead)"]
        T2["PID Thread (Active)"]
    end

    G["Gazebo /bot1/cmd_vel (Twist)"]
    K1["Booster K1 /bot1/LocoApiTopicReq (RPC)"]

    Poll --> Parse
    Parse --> Kill
    Kill -.->|Preempts| T1
    Parse -->|Spawns New| T2
    T2 -->|Publishes Twist| G
    T2 -->|Publishes JSON RPC| K1

    style T1 fill:#ccc,stroke:#333,stroke-dasharray: 5 5
    style T2 fill:#f9f,stroke:#333
~~~

## 2. Architectural Logic & Data Flow
Traditional robotics utilizes rigid C++ HALs encompassing `BaseBotDriver` classes to manage kinematics. ROS2K bypasses this to remain agile.

**[DEPRECATED in v4] Basic Flow:**
The Bridge acts as a thread manager. When the LLM outputs a new JSON assignment (e.g., commanding `blue_3` to coordinate `[1.5, 2.0]`), the Bridge:
1. Checks if a movement thread for `blue_3` already exists.
2. If so, triggers a `threading.Event()` flag, commanding the old thread to publish a `linear.x = 0.0` stop vector and terminate itself.
3. Instantiates a brand new `threading.Thread` targeting a `def task()` closure function, passing the new target coordinates.
4. This detached thread loops infinitely at 10Hz, reading odometry and calculating the angular/linear error to the target, adjusting motor velocity until the waypoint is reached.

**[UPDATE in v5] Multi-Hardware Relay Flow:**
The fundamental closure thread (`def task()`) pattern is retained, but the published payload is dynamic:
* **Sim/Diff-Drive:** The thread calculates the PID error and publishes a standard `geometry_msgs/Twist` message to the isolated namespace.
* **Booster K1 Biped:** The thread constructs a proprietary JSON RPC payload (API Code 2000 for Failsafe/Prep, API Code 2001 for Active Locomotion) and publishes it to `/bot1/LocoApiTopicReq`.
* **Native micro-ROS Bypass:** To prevent Docker from blocking FastDDS Shared-Memory (SHM) transports to ESP32 microcontrollers, Ubuntu 22.04 deployments compile the `micro-ROS-agent` locally in a dedicated `uros_ws` and execute it natively outside of Docker.

## 3. Code Reference & Interfaces
> **Source:** [`ai_tactics/ollama_sandbox_bridge.py`](../src/ai_tactics/ollama_sandbox_bridge.py)

**[DEPRECATED in v4] Legacy Implementation:**
The dynamic preemption and spawning logic within the Bridge polling loop.
~~~python
# snippet from ollama_sandbox_bridge.py
import threading

def move(self, bot_name, target_x, target_y):
    # Preempt existing movement thread for this specific bot
    if bot_name in self.events: 
        self.events[bot_name].set() 
        
    self.events[bot_name] = threading.Event()
    
    # Closure function containing the PID math
    def task(stop_event):
        while not stop_event.is_set():
            # ... PID math execution ...
            time.sleep(0.1)
            
    # Spawn new detached execution layer
    threading.Thread(target=task, args=(self.events[bot_name],), daemon=True).start()
~~~

**[NEW in v5] Payload Generation Context:**
Inside the `task` closure, the script now evaluates the `active_relay.json` profile to dynamically build either a `Twist` object or the required RPC JSON string.

## 4. Known Issues & Limitations
* Orphaned threads can accumulate and throttle CPU overhead if the `stop_event` logic fails to trigger cleanly during rapid JSON file overwrites.
* Global Interpreter Lock (GIL) constraints in Python limit the number of simultaneous active bots before the 10Hz QoS policy begins to degrade.
* **[NEW in v5] FastDDS Docker Blockades:** Running the hardware bridge within Ubuntu 24.04 Docker containers frequently blocks SHM packets, necessitating the native `uros_ws` workaround on Ubuntu 22.04.

## 5. Glossary
* **Detached Thread:** A spawned background OS process that runs independently of the main script's blocking execution flow.
* **PID:** Proportional-Integral-Derivative control; a mathematical feedback mechanism to smoothly calculate motor speed based on current distance to target.
* **Closure Function:** A function defined inside another function that retains access to the outer function's variable scope.
* **[NEW in v5] JSON RPC (API 2000/2001):** The proprietary payload format required to trigger the Booster K1's internal locomotion state machine.
* **[NEW in v5] `uros_ws`:** The isolated workspace used to compile the native `micro-ROS-agent` on Ubuntu 22.04.
