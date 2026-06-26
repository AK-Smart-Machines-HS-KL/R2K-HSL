---
id: 5_02
title: "Docker Networking and FastDDS"
type: SPECIFICATION
tags: [networking, fastdds, multicast, host-mode, compose-project-name]
last_modified: 2026-05-31
version: v5_release
---
# Docker Networking and FastDDS

> [!info] Human Summary
> Explains why the ROS2K environment requires `network_mode: host` to bypass standard Docker network isolation and enable the UDP Multicast required by physical robots.

> [!abstract] LLM Context Anchor
> To permit FastDDS discovery between the Docker container and physical ESP32/K1 hardware, the stack MUST utilize the host network. Standard Docker bridge networks (172.x.x.x) block the necessary UDP multicast packets.
> **[NEW in v5]:** In the Ubuntu 24.04 Docker Hybrid OS configuration, `network_mode: host` remains mandatory. However, because this bypasses Docker's internal network resolution, running multiple ROS2K instances previously caused container name collisions. V5 resolves this by dynamically exporting `COMPOSE_PROJECT_NAME` based on the active directory.

## 1. System Topology of FastDDS Multicast

**[DEPRECATED in v4] Original Networking Topology:**
This graph illustrates how the host network mode allows the Docker container to "see" physical hardware on the local Wi-Fi network.

~~~mermaid
graph TD
    subgraph HostNet ["Host Network Interface"]
        UDP["UDP Multicast Port 7400+"]
    end

    subgraph Docker ["Container (network_mode: host)"]
        ROS["ROS 2 Humble Stack"]
    end

    subgraph Edge ["Physical Hardware"]
        ESP["Yahboom (Domain 0)"]
        K1["Booster (Domain 0)"]
    end

    ROS <-->|Unrestricted UDP| UDP
    UDP <-->|Direct Discovery| ESP
    UDP <-->|Direct Discovery| K1

    style HostNet fill:#f9f,stroke:#333
    style Docker fill:#dfd,stroke:#333
~~~

**[NEW in v5] Validated V5 Networking Topology:**
The topology now includes the dynamic namespace isolation preventing container collision on Ubuntu 24.04 hosts.

~~~mermaid
graph TD
    subgraph Host ["Ubuntu 24.04 Host"]
        Dir["Directory Name Extraction"]
        Export["export COMPOSE_PROJECT_NAME"]
        UDP["UDP Multicast Port 7400+"]
    end

    subgraph Docker ["Dynamic Compose Stack"]
        ROS["ROS 2 Humble Stack (network_mode: host)"]
    end

    subgraph Edge ["Physical Edge Network"]
        ESP["Yahboom (Domain 0)"]
        K1["Booster (Domain 0)"]
    end

    Dir --> Export
    Export -->|Prefixes Container Name| ROS
    ROS <-->|Unrestricted UDP| UDP
    UDP <-->|Direct Discovery| ESP
    UDP <-->|Direct Discovery| K1

    style Host fill:#f9f,stroke:#333
    style Docker fill:#dfd,stroke:#333
~~~

## 2. Architectural Logic & Data Flow
**[DEPRECATED in v4] Legacy Flow:**
ROS 2 Humble uses FastDDS as its default middleware. FastDDS relies on the Simple Discovery Protocol (SDP), which uses UDP Multicast to find other nodes on the network.
1. **Isolation Problem**: By default, Docker places containers in a virtual bridge network. This bridge acts as a NAT layer that does not forward multicast packets from the physical Wi-Fi adapter into the container.
2. **The Host Solution**: By setting `network_mode: host` in the `docker-compose.yml`, the container shares the host's IP address and network namespaces.
3. **micro-ROS Synchronicity**: This allows the `micro-ros-agent` to communicate with the physical ESP32 bots using the standard ROS 2 Domain ID 0.

**[UPDATE in v5] Dynamic Project Isolation:**
While the host networking requirements remain identically strict for Ubuntu 24.04 deployments, the reliance on `network_mode: host` severely limits container isolation. If a user spawned two separate test environments (e.g., in `~/ros2k_test1` and `~/ros2k_test2`), Docker would attempt to overwrite the containers. `launch_r2k.sh` now extracts the current basename of the working directory and forces it into the `COMPOSE_PROJECT_NAME` environment variable, ensuring that `docker compose up` provisions uniquely named containers while still sharing the host's UDP ports.

## 3. Code Reference & Interfaces
> **Source:** [`launch_triple_demo.sh`](../src/launch_triple_demo.sh) **[DEPRECATED in v4]**
> **Source:** [`launch_r2k.sh`](../launch_r2k.sh) **[NEW in v5]**

**[DEPRECATED in v4] Legacy Docker Launch:**
The launch sequence proving the reliance on the host network for micro-ROS agent operations.
~~~bash
# snippet from launch_triple_demo.sh
echo "🔌 Starting micro-ROS Agent on Domain 0..."
# Force --net=host to allow physical hardware discovery
docker run -d --name uros_agent --rm --net=host -e ROS_DOMAIN_ID=0 microros/micro-ros-agent:humble udp4 --port 8888
~~~

**[NEW in v5] Dynamic Compose Instantiation:**
~~~bash
# snippet from launch_r2k.sh
export COMPOSE_PROJECT_NAME=$(basename "$PWD")
echo "🐳 Ubuntu 24.04 detected. Starting DOCKER ROS 2 workspace: $COMPOSE_PROJECT_NAME..."

xhost +local:root
docker compose up -d --remove-orphans
~~~

## 4. Known Issues & Limitations
* Running in host mode means the container can conflict with services already running on the host OS.
* Ubuntu 24 firewall settings (UFW) may need explicit rules to allow incoming UDP traffic from the ESP32 on port 8888.

## 5. Glossary
* **FastDDS**: A high-performance Data Distribution Service implementation used by ROS 2.
* **UDP Multicast**: A communication pattern where data is sent to a group of destination computers simultaneously.
* **[NEW in v5] `COMPOSE_PROJECT_NAME`**: An environment variable that instructs Docker Compose to prepend a specific string to all containers created by the active `docker-compose.yml`.
