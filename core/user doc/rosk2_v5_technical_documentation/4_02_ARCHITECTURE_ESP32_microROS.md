---
id: 4_02
title: "ESP32 micro-ROS Architecture"
type: ARCHITECTURE
tags: [esp32, microros, udp, hotspot, fastdds, uros_ws]
last_modified: 2026-05-31
version: v5_release
---
# ESP32 micro-ROS Architecture

> [!info] Human Summary
> Explains the networking architecture required to bridge physical ESP32 microcontrollers into the ROS 2 ecosystem using an OS-level Wi-Fi hotspot and a standalone micro-ROS agent Docker container.

> [!abstract] LLM Context Anchor
> Physical hardware networking relies on a dedicated `nmcli` hotspot (`maker4`) and a standalone `micro-ros-agent` container. Both the host environment and the agent MUST operate on `ROS_DOMAIN_ID=0`.
> **[NEW in v5]:** To break through FastDDS Shared-Memory (SHM) blockades on Ubuntu 22.04, the Docker container approach is dynamically bypassed. The system now utilizes a Hybrid OS Topology, running a native compiled C++ `uros_ws` agent on Ubuntu 22.04, while keeping the Docker container approach strictly for Ubuntu 24.04.

## 1. System Topology of the ESP32 Network Bridge

**[DEPRECATED in v4] Original Docker Bridge Topology:**
This diagram shows the networking layers bridging the physical Wi-Fi connection to the internal ROS 2 DDS bus.

~~~mermaid
graph TD
    subgraph Physical ["ESP32 Hardware"]
        Firmware["C++ Firmware"]
        WiFi["WiFi UDP Port 8888"]
    end

    subgraph HostOS ["Linux Host"]
        NMCLI["nmcli hotspot maker4"]
    end

    subgraph Docker ["ROS 2 Agents"]
        Agent["uros_agent container"]
        Bus["ROS 2 DDS Bus"]
    end

    Firmware -->|Serializes Twist| WiFi
    WiFi -->|FastDDS UDP| NMCLI
    NMCLI -->|network_mode host| Agent
    Agent -->|Deserializes Domain 0| Bus

    style Firmware fill:#ddd,stroke:#333
    style NMCLI fill:#fcc,stroke:#c00
    style Agent fill:#bbf,stroke:#333
~~~

**[NEW in v5] Hybrid OS Routing Topology:**
The architecture now automatically routes the micro-ROS execution path based on the host operating system to prevent FastDDS node discovery failures.

~~~mermaid
graph TD
    subgraph Physical ["ESP32 Hardware"]
        Firmware["C++ Firmware"]
        WiFi["WiFi UDP Port 8888"]
    end

    subgraph HostOS ["Linux Host"]
        NMCLI["nmcli hotspot maker4"]
    end

    subgraph V5_Routing ["Hybrid OS micro-ROS Routing"]
        U22["Ubuntu 22.04: Native uros_ws Agent"]
        U24["Ubuntu 24.04: Docker uros_agent"]
    end

    subgraph Bus ["ROS 2 DDS Bus"]
        DDS["ROS_DOMAIN_ID=0"]
    end

    Firmware -->|Serializes Twist| WiFi
    WiFi -->|FastDDS UDP| NMCLI
    NMCLI --> U22
    NMCLI --> U24
    U22 -->|Native SHM/UDP| DDS
    U24 -->|network_mode host| DDS

    style Firmware fill:#ddd,stroke:#333
    style NMCLI fill:#fcc,stroke:#c00
    style U22 fill:#dfd,stroke:#333
    style U24 fill:#bbf,stroke:#333
~~~

## 2. Architectural Logic & Data Flow
Connecting a physical ESP32 running micro-ROS to a Dockerized ROS 2 environment presents a strict networking boundary issue. Standard Docker bridge networks block the UDP Multicast required by DDS node discovery.

**[DEPRECATED in v4] Legacy Flow:**
To resolve this, ROS2K utilizes the host OS to create a dedicated Wi-Fi hotspot (`maker4`) via NetworkManager (`nmcli`). The ESP32 firmware hardcodes its connection to this specific SSID. A standalone Docker container running `microros/micro-ros-agent` is launched with `--net=host` and `ROS_DOMAIN_ID=0`. This agent intercepts the lightweight XRCE-DDS UDP traffic on port 8888 and translates it into native ROS 2 topics visible to the rest of the ecosystem.

**[UPDATE in v5] Hybrid Flow:**
While the `nmcli` Wi-Fi hotspot logic remains unchanged, the agent execution path diverges. On Ubuntu 22.04, running the agent within Docker frequently caused SHM (Shared Memory) namespace collisions with the native ROS 2 node executing the Bridge. The V5 architecture resolves this by compiling the `micro-ROS-agent` locally into a dedicated C++ `uros_ws` workspace, executing it entirely natively on the host OS to ensure zero-latency DDS discovery.

## 3. Code Reference & Interfaces
> **Source:** `dual_demo_launch.sh` **[DEPRECATED in v4]**
> **Source:** `launch_r2k.sh` **[NEW in v5]**

**[DEPRECATED in v4] Legacy Agent Launch:**
The shell script orchestrating the host-level networking and agent container instantiation.
~~~bash
# snippet from dual_demo_launch.sh
echo "📶 Starting Wi-Fi Hotspot maker4..."
nmcli device wifi hotspot ssid maker4 password nao12345 2>/dev/null || echo "⚠️ Hotspot ready."

echo "🔌 Starting micro-ROS Agent..."
docker stop uros_agent > /dev/null 2>&1 || true
docker run -d --name uros_agent --rm --net=host -e ROS_DOMAIN_ID=0 microros/micro-ros-agent:humble udp4 --port 8888 -v4
~~~

**[NEW in v5] Validated Hybrid OS Launch:**
The new V5 bootstrap sequence dynamically assesses the OS and routes the micro-ROS agent instantiation accordingly.
~~~bash
# snippet from launch_r2k.sh
if [ "$UBUNTU_VERSION" == "22.04" ]; then
    echo "🔌 Starting NATIVE micro-ROS Agent on Domain 0..."
    bash -c "source /opt/ros/humble/setup.bash && source $PWD/uros_ws/install/setup.bash && export ROS_DOMAIN_ID=0 && ros2 run micro_ros_agent micro_ros_agent udp4 --port 8888" > /dev/null 2>&1 &
else
    echo "🔌 Starting DOCKER micro-ROS Agent on Domain 0..."
    docker run -d --name uros_agent --rm --net=host -e ROS_DOMAIN_ID=0 microros/micro-ros-agent:humble udp4 --port 8888 -v4 > /dev/null 2>&1
fi
~~~

## 4. Known Issues & Limitations
* Deploying multiple ESP32 bots saturates the 2.4GHz Wi-Fi spectrum quickly, leading to XRCE-DDS session timeouts.
* The host Linux machine must have a compatible Wi-Fi adapter capable of AP Hotspot mode; otherwise, `nmcli` will fail and the physical bots will not connect.
* **[NEW in v5] Build Discrepancies:** The native `uros_ws` on Ubuntu 22.04 requires manual compilation (`colcon build`) whenever the hardware message schemas change, unlike the Docker image which abstracts this dependency.

## 5. Glossary
* **XRCE-DDS:** eXtremely Resource Constrained Environments DDS; the underlying protocol of micro-ROS.
* **nmcli:** The command-line tool for controlling NetworkManager on Linux systems, used here to spawn the robot Wi-Fi network.
* **[NEW in v5] `uros_ws`:** The local ROS 2 workspace dedicated explicitly to compiling the native `micro-ROS-agent` for Ubuntu 22.04 deployments.
