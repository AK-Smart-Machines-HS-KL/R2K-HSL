---
id: 4_08
title: "Native micro-ROS Agent (Ubuntu 22.04)"
type: ARCHITECTURE
tags: [microros, fastdds, ubuntu-22.04, hybrid-os, shm-blockade, uros_ws]
last_modified: 2026-05-31
version: v5_release
---
# Native micro-ROS Agent (Ubuntu 22.04)

> [!info] Human Summary
> Explains the necessity and architecture of the natively compiled `micro-ROS-agent` within `uros_ws`. This setup bypasses the FastDDS Shared-Memory blockades present when running Docker containers on an Ubuntu 22.04 ROS 2 Humble host.

> [!abstract] LLM Context Anchor
> To prevent FastDDS namespace collisions and silent packet drops on Ubuntu 22.04, the Docker approach is completely abandoned. The micro-ROS agent is compiled from C++ source in the local `uros_ws` workspace and executed natively, guaranteeing 0ms latency and pure ROS_DOMAIN_ID=0 synchronization.

## 1. System Topology of the FastDDS SHM Blockade

This graph illustrates why the V4 Docker approach fails on an Ubuntu 22.04 host and how the V5 native compilation resolves it.

~~~mermaid
graph TD
    subgraph V4_Failure ["Docker Approach (Fails on U22)"]
        D_Agent["uros_agent (Docker)"]
        D_Host["Bridge Node (Native)"]
        D_Wall{"FastDDS SHM Segment Collision"}
        D_Agent -.->|Blocked| D_Wall
        D_Host -.->|Blocked| D_Wall
    end

    subgraph V5_Success ["Native Approach (uros_ws)"]
        N_Agent["micro_ros_agent (Native U22)"]
        N_Host["Bridge Node (Native U22)"]
        N_Bus["ROS 2 DDS Bus (Domain 0)"]
        N_Agent -->|Native SHM/UDP| N_Bus
        N_Host -->|Native SHM/UDP| N_Bus
    end

    style D_Wall fill:#fcc,stroke:#c00
    style N_Bus fill:#dfd,stroke:#333
~~~

## 2. Architectural Logic & Data Flow
**The Problem:** In V4, the system universally relied on a Dockerized `micro-ROS-agent`. On Ubuntu 24.04, where ROS 2 Humble cannot run natively, this is fine because *all* nodes run inside Docker. However, on Ubuntu 22.04, developers run the Python nodes natively. When a native ROS 2 FastDDS node attempts to discover a node running inside a Docker container using `network_mode: host`, FastDDS often prioritizes Shared Memory (SHM) transport over UDP. Because the Docker container has an isolated `/dev/shm` namespace, the memory segments collide, and topics silently fail to route.

**The V5 Solution:** To eliminate this architectural flaw, ROS2K implements a Hybrid OS Topology. If the bootstrap script detects `Ubuntu 22.04`, it completely bypasses the Docker container. Instead, it sources a locally compiled C++ workspace (`uros_ws`), which builds the `micro_ros_agent` from source. By running the agent natively on the host OS, it shares the exact same SHM namespace as the Python execution nodes, ensuring absolute reliability and ultra-low latency for Edge Hardware.

## 3. Code Reference & Interfaces
> **Source:** `launch_r2k.sh`

The Hybrid OS routing logic evaluating the underlying OS before spawning the agent.
~~~bash
# snippet from launch_r2k.sh
UBUNTU_VERSION=$(lsb_release -rs)

if [ "$UBUNTU_VERSION" == "22.04" ]; then
    echo "🔌 Starting NATIVE micro-ROS Agent on Domain 0 (SHM Bypass)..."
    bash -c "source /opt/ros/humble/setup.bash && source $PWD/uros_ws/install/setup.bash && export ROS_DOMAIN_ID=0 && ros2 run micro_ros_agent micro_ros_agent udp4 --port 8888" > /dev/null 2>&1 &
else
    echo "🔌 Starting DOCKER micro-ROS Agent on Domain 0..."
    docker run -d --name uros_agent --rm --net=host -e ROS_DOMAIN_ID=0 microros/micro-ros-agent:humble udp4 --port 8888 -v4 > /dev/null 2>&1
fi
~~~

## 4. Known Issues & Limitations
* Building the `uros_ws` requires pulling heavy C++ dependencies and XRCE-DDS libraries onto the host machine, breaking the "pure python" elegance of the repository.
* Every time a custom message type is added or modified in the ROS 2 environment, the `uros_ws` must be fully recompiled (`colcon build`) to ensure the native agent recognizes the new serialized schemas.

## 5. Glossary
* **FastDDS:** The default middleware implementation for ROS 2 Humble.
* **SHM (Shared Memory):** A transport mechanism where nodes on the same host write directly to RAM instead of the network stack, drastically increasing speed but requiring unified OS namespaces.
* **`uros_ws`:** The V5 dedicated local ROS 2 workspace containing the micro-ROS C++ agent source code.
