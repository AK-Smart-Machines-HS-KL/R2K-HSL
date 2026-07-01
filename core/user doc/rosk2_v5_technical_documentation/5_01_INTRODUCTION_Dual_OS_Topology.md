---
id: 5_01
title: "Dual OS Topology and Orchestration"
type: INTRODUCTION
tags: [docker, orchestration, ubuntu-24, ubuntu-22, hybrid-os, gpu-access, watchdog]
last_modified: 2026-05-31
version: v5_release
---
# Dual OS Topology and Orchestration

> [!info] Human Summary
> This document defines the execution boundaries of the ROS2K environment, explaining the dynamic OS-level split between the Ubuntu 24 host (Dockerized) and the Ubuntu 22 environment (Native) required for ROS 2 Humble compatibility.

> [!abstract] LLM Context Anchor
> The architecture utilizes a specific OS-bridge strategy: the host runs Ubuntu 24 (Noble) without any ROS 2 installation. All robotics middleware resides in an Ubuntu 22 (Jammy) Docker container to satisfy the ROS 2 Humble dependency for Booster K1 and Yahboom hardware.
> **[NEW in v5]:** The system now utilizes a "Hybrid OS Topology". The bootstrap script dynamically evaluates the host operating system. Ubuntu 22.04 executes 100% natively (for 0ms latency), whereas Ubuntu 24.04 encapsulates the environment via Docker Compose. Additionally, X11-Forwarding (`/tmp/.X11-unix`) and dynamic `COMPOSE_PROJECT_NAME` generation ensure GUI passthrough without container collisions.

## 1. System Topology of OS-Level Boundaries

**[DEPRECATED in v4] Original Docker Topology:**
This diagram illustrates the separation of concerns between the Ubuntu 24 host OS and the Ubuntu 22 ROS 2 environment.

~~~mermaid
graph TD
    subgraph Host ["Host OS (Ubuntu 24.04 LTS)"]
        OLL["Ollama AI Server<br>(Natively for Efficiency)"]
        VIS["Live Visualizer<br>(Matplotlib)"]
        GPU["GPU Hardware Access"]
    end

    subgraph Container ["Docker: r2k_unify2_gazebo<br>(Ubuntu 22.04 LTS)"]
        GZ["Gazebo & Physics<br>(GPU Accelerated)"]
        WS["ROS 2 Humble Stack"]
        PY["Python AI Daemons"]
    end

    subgraph Hardware ["Edge Hardware"]
        ESP["Yahboom ESP32"]
        K1["Booster K1"]
    end

    OLL <-->|REST API| PY
    GPU --- GZ
    WS <-->|DDS Domain 0| ESP
    WS <-->|DDS Domain 0| K1

    style Host fill:#f9f,stroke:#333
    style Container fill:#dfd,stroke:#333
    style GPU fill:#bbf,stroke:#333
~~~

**[NEW in v5] Validated Hybrid OS Topology:**
The architecture dynamically routes the execution environment based on the host OS while maintaining shared access to Ollama in User-Space.

~~~mermaid
graph TD
    subgraph Host ["Host OS Evaluator (launch_r2k.sh)"]
        OLL["Ollama qwen2.5-coder:3b<br>(Strictly User-Space)"]
        EVAL{"lsb_release -rs"}
    end

    subgraph U22 ["Ubuntu 22.04 Pathway"]
        N_ROS["Native ROS 2 Humble Stack"]
        N_GZ["Native Gazebo (0ms Latency)"]
    end

    subgraph U24 ["Ubuntu 24.04 Pathway"]
        D_ROS["Docker ROS 2 Humble Stack"]
        D_GZ["Docker Gazebo"]
        X11["X11 Passthrough (/tmp/.X11-unix)"]
    end

    EVAL -->|22.04| U22
    EVAL -->|24.04| U24
    U24 --> X11
    OLL <-->|REST API| U22
    OLL <-->|REST API| U24

    style Host fill:#f9f,stroke:#333
    style U22 fill:#dfd,stroke:#333
    style U24 fill:#bbf,stroke:#333
~~~

## 2. Architectural Logic & Data Flow
**[DEPRECATED in v4] Legacy Orchestration:**
The orchestration logic is driven by specific dependency and performance requirements:
* **OS Disparity**: The host runs Ubuntu 24 to leverage modern kernel features and drivers. However, the Booster K1 and Yahboom ESP32 hardware require ROS 2 Humble, which is officially supported on Ubuntu 22. Docker provides the Jammy environment necessary for these drivers.
* **Host-Native Ollama**: To maximize inference speed, Ollama runs natively on the host OS. This prevents the LLM from being throttled by Docker's resource limits and ensures zero-latency access to the GPU.
* **GPU Passthrough**: Gazebo runs inside the Docker container but leverages the host's GPU via X11 socket forwarding and NVIDIA-container-toolkit to ensure high-frame-rate physics rendering.
* **Auto-Shutdown Monitor**: A host-side monitor tracks the Gazebo process; if the simulation window closes, a full teardown of the Docker stack is triggered.

**[UPDATE in v5] Hybrid Orchestration & Watchdog:**
The legacy logic applies exclusively when running on Ubuntu 24.04.
* **Hybrid OS Topology**: If `launch_r2k.sh` detects Ubuntu 22.04, it completely bypasses Docker. All nodes, including the `micro-ROS-agent` (via `uros_ws`), are compiled and executed natively on the host. If Ubuntu 24.04 is detected, it encapsulates the ROS 2 workspace in Docker Compose.
* **Dynamic Naming & X11**: For Docker targets, the script dynamically exports `COMPOSE_PROJECT_NAME` based on the current directory to prevent container collisions when running multiple instances. It also explicitly mounts `/tmp/.X11-unix` to pass the host GUI directly to Gazebo.
* **0.2s Asynchronous Watchdog**: The legacy "Auto-Shutdown Monitor" and "Nuke & Pave" scripts have been replaced. A fast-polling loop (0.2s) detects the closure of the Gazebo UI. Instantly, it fires asynchronous Twist zero-vectors (Kinematic Freeze) to the physical hardware, followed by a hard `pkill -9` (`SIGKILL`) of the ROS 2 and Ollama processes to prevent Zombie processes and RCLError tracebacks.

## 3. Code Reference & Interfaces
> **Source:** [`launch_r2k_phase_b.sh`](../src/launch_r2k_phase_b.sh) **[DEPRECATED in v4]**
> **Source:** [`launch_r2k.sh`](../launch_r2k.sh) **[NEW in v5]**

**[DEPRECATED in v4] Legacy Launch Script:**
The shell script orchestrating the sequence of Native and Dockerized components.
~~~bash
# snippet from launch_r2k_phase_b.sh
# 1. Start Ollama natively on Ubuntu 24 Host
export OLLAMA_HOST=0.0.0.0
nohup ollama serve > ollama.log 2>&1 &

# 2. Boot Ubuntu 22 Docker Stack
xhost +local:root
docker compose up -d --remove-orphans

# 3. Injecting Humble-specific nodes
DOCKER_CMD="docker exec -d r2k_unify2_gazebo bash -c"
$DOCKER_CMD "source /opt/ros/humble/setup.bash && ros2 run r2k_world_model tracker"
~~~

**[NEW in v5] Hybrid Boot & Watchdog Orchestration:**
The updated core logic deciding the execution path and the Watchdog teardown trap.
~~~bash
# snippet from launch_r2k.sh
UBUNTU_VERSION=$(lsb_release -rs)
export COMPOSE_PROJECT_NAME=$(basename "$PWD")

if [ "$UBUNTU_VERSION" == "22.04" ]; then
    echo "🚀 Ubuntu 22.04 detected. Starting NATIVE ROS 2 workspace..."
    # Native sourcing and execution...
else
    echo "🐳 Ubuntu 24.04 detected. Starting DOCKER ROS 2 workspace..."
    xhost +local:root
    docker compose up -d --remove-orphans
    # Docker exec execution...
fi

# The 0.2s Asynchronous Watchdog
while kill -0 $GAZEBO_PID 2>/dev/null; do
    sleep 0.2
done

echo "🛑 UI closed! Firing Kinematic Freeze and terminating system..."
# Fire Code 2000 / Twist 0.0 here
pkill -9 ollama
pkill -9 -f "ros2"
~~~

## 4. Known Issues & Limitations
* Lack of ROS 2 on the host means debugging topics natively (e.g., `ros2 topic list`) is impossible; all CLI commands must be wrapped in `docker exec`.
* NVIDIA driver versions on the Ubuntu 24 host must be strictly compatible with the library versions inside the Ubuntu 22 container.
* **[NEW in v5] Ollama Daemon Locks:** Ollama MUST run in user-space. If launched via systemd, the 0.2s Watchdog cannot execute `pkill -9 ollama`, leading to Zombie processes locking port 11434 and consuming VRAM.

## 5. Glossary
* **Humble Hawksbill**: The ROS 2 distribution targeted for Ubuntu 22.04, critical for project hardware compatibility.
* **X11 Passthrough**: The method of allowing a container to display 3D graphics on the host's monitor.
* **[NEW in v5] Hybrid OS Topology**: The architectural pattern of maintaining a unified codebase that executes natively on older, supported OS versions and within containers on newer OS versions.
* **[NEW in v5] 0.2s Asynchronous Watchdog**: The aggressive teardown trap in `launch_r2k.sh` responsible for the Kinematic Freeze and Zombie-process prevention.
