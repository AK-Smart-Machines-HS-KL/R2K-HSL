---
id: 1_03
title: "Control Loops & Timing Disparities"
type: ARCHITECTURE
tags: [async, latency, qos, loops]
last_modified: 2026-05-31
version: v5_release
---
# Control Loops & Timing Disparities

> [!info] Human Summary
> This document details the mechanical solution to integrating non-deterministic AI generation (which takes 1-2 seconds) with physical motor hardware (which requires a fresh command every 100 milliseconds).

> [!abstract] LLM Context Anchor
> Physical execution loops (PID threads) operate at a strict, deterministic 10Hz to satisfy hardware Quality of Service (QoS) timeouts. The cognitive layer operates via an asynchronous, blocking "inference pulse" with highly variable latency (500-2000ms). These loops NEVER block one another.
> **[DEPRECATED in v4]:** Optimized for `Nemotron-3-nano:4b`.
> **[NEW in v5]:** Transitioned to `qwen2.5-coder:3b` via Ollama. Be highly aware of the Linux Suspend-Bug (`Xid 31 MMU Fault`), which forces silent CPU fallback and destroys the cognitive loop timing (>7000ms latency).

## 1. System Topology of Loop Desynchronization

**[DEPRECATED in v4] Original Topology:**
This graph illustrates the frequency isolation between the hardware actuation domain and the cognitive generation domain.

~~~mermaid
graph TD
    subgraph Cog ["Cognitive Loop<br>(Avg 1Hz Variable)"]
        E["Evaluator Daemon"]
        LLM{"Nemotron<br>Inference Pulse"}
    end

    subgraph Exec ["Execution Loop<br>Strict 10Hz"]
        B["Bridge Poller"]
        PID["Detached PID<br>Threads"]
    end

    subgraph HW ["Hardware Layer"]
        M["Physical/Sim<br>Motors"]
    end

    E -->|Blocking POST| LLM
    LLM -->|Wait 1-2s| E
    E -->|Async File Write| B
    
    B -->|Spawns| PID
    PID -->|cmd_vel 10Hz| M
    M -->|Encoders| PID

    style LLM fill:#bbf,stroke:#333
    style PID fill:#f9f,stroke:#333
~~~

**[NEW in v5] Updated Qwen Topology:**
The fundamental architecture remains identical, but the AI core has been swapped. The `Evaluator Daemon` now addresses the local Ollama REST API. The cognitive loop is explicitly defined as non-deterministic.

~~~mermaid
graph TD
    subgraph Cog ["Cognitive Loop<br>Non-Deterministic<br>(0.14Hz - 5.0Hz)"]
        E["Evaluator Daemon"]
        LLM{"Qwen2.5-Coder<br>Ollama REST API"}
    end

    subgraph Exec ["Execution Loop<br>Deterministic 10Hz"]
        B["Bridge Poller"]
        PID["Detached PID<br>Threads"]
    end

    subgraph HW ["Hardware Layer"]
        M["Physical/Sim<br>Motors"]
    end

    E -->|Blocking POST| LLM
    LLM -->|Wait 0.2s-7.0s| E
    E -->|Async File Write| B
    
    B -->|Spawns| PID
    PID -->|cmd_vel 10Hz| M
    M -->|Encoders| PID

    style LLM fill:#bbf,stroke:#333
    style PID fill:#f9f,stroke:#333
~~~

## 2. Architectural Logic & Data Flow
If a robotic chassis does not receive a `/cmd_vel` message every ~200ms, firmware safety watchdogs trigger an emergency halt. 

**[DEPRECATED in v4]:** Because Nemotron's generative inference pulse blocks execution for up to 2 seconds, synchronous execution is impossible.
**[UPDATE in v5] Non-Deterministic vs. Deterministic Loops:** The "Cognitive Loop" does NOT run at a fixed frequency. It is completely non-deterministic. With `qwen2.5-coder:3b`, this pulse is generally 200-500ms (2Hz-5Hz) on a native GPU. However, it can spike to >7000ms (0.14Hz) if the `Xid 31 MMU Fault` (Suspend-Bug) occurs. The asynchronous execution architecture is therefore critical to mask these severe OS-level latency spikes.

**The Solution (Decoupling):**
The `ollama_sandbox_bridge.py` isolates the execution cycle. It spawns independent Proportional-Integral-Derivative (PID) threads for each robot. These threads continuously measure the Euclidean distance to their assigned `(x, y)` target and publish motor velocities at a strict, deterministic 10Hz. If the LLM is currently "thinking" and blocking the cognitive loop, the PID thread simply continues executing the *last known* target until the file system is updated with a new JSON strategy.

## 3. Code Reference & Interfaces
> **Source:** [`ai_tactics/ollama_sandbox_bridge.py`](../src/ai_tactics/ollama_sandbox_bridge.py)

The Bridge thread-spawning mechanism guarantees the ROS 2 executor is never blocked by LLM inference latency.

**[NEW in v5] Dynamic Closure Architecture:**
The V5 HAL explicitly relies on these detached `def task()` thread-closures. OOP inheritance (e.g., `class DifferentialBot`) is strictly prohibited to keep execution layers flat and immune to ROS 2 executor blocking.

~~~python
# snippet from ollama_sandbox_bridge.py
import threading, time

def task(bot_name, target_x, target_y, stop_event, pub):
    rate = 10.0 # 10Hz execution loop
    while not stop_event.is_set():
        # ... fetch local odometry, calculate Euclidean error ...
        msg = Twist()
        msg.linear.x = 0.5 
        msg.angular.z = calculated_angular_error
        pub.publish(msg)
        time.sleep(1.0 / rate)
        
    # Failsafe explicit stop vectors
    pub.publish(Twist()) 
~~~

## 4. Known Issues & Limitations
* If the LLM crashes entirely, the robot will continue driving into walls attempting to reach the last valid coordinate unless a timeout watchdog is implemented in the Bridge.
* High acceleration limits can cause wheel slip, breaking the Dead Reckoning loop.
* **[NEW in v5] The Suspend-Bug:** The Linux Suspend-to-RAM feature unloads NVIDIA VRAM. Upon waking, Ollama silently falls back to CPU, extending the cognitive loop to 7000ms. Fix via `NVreg_PreserveVideoMemoryAllocations=1`.
* **[NEW in v5] System Teardown:** Runaway robots during process termination are now mitigated by the 0.2s Asynchronous Watchdog, which forces Twist zero-vectors before executing `pkill -9`.

## 5. Glossary
* **Inference Pulse:** The non-deterministic, variable time window (200ms - 7000ms) where the LLM computes the next tactical matrix.
* **PID Thread:** Deterministic proportional control loop spawned as a detached OS process by the Bridge to satisfy hardware QoS at exactly 10Hz.
