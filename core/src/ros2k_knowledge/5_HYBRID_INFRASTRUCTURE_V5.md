---
id: 5_HYBRID
title: "Section 5: Hybrid OS Infrastructure & Deployment (V6.1)"
type: KNOWLEDGE_BASE_POWER_FILE
tags: [hybrid-os, docker, ubuntu-24, ubuntu-22, host-mode, fastdds, x11, xid-31, suspend-bug, compose-project-name, v6.1, headless-gzserver, docker-env-passthrough]
last_modified: 2026-07-22
version: v6.2
---
# Section 5: Hybrid OS Infrastructure & Deployment (V5)

> [!abstract] LLM Context Anchor
> **CRITICAL AXIOMS FOR RAG RETRIEVAL:**
> 1. **Hybrid OS Topology:** The architecture dynamically scales based on the Host OS (`lsb_release -rs`). Ubuntu 22.04 runs 100% natively (0ms latency, native `uros_ws`). Ubuntu 24.04 encapsulates the ROS 2 environment via Docker-Compose but keeps the code on the host.
> 2. **Xid 31 Suspend Bug:** If Ollama drops to CPU-only inference (>7000ms latency), it is NOT a systemd or soft-kill issue. It is the Linux Suspend-to-RAM bug corrupting the NVIDIA VRAM. Fixed via `NVreg_PreserveVideoMemoryAllocations=1`.
> 3. **Dynamic Container Naming:** To prevent collisions between multiple parallel ROS2K instances on Ubuntu 24, the script dynamically exports `COMPOSE_PROJECT_NAME=$(basename "$PWD")`.
> 4. **X11 Forwarding:** The Docker container requires explicit X11 socket forwarding (`/tmp/.X11-unix`) and `xhost +local:root` to permit Gazebo hardware-accelerated GUI rendering.
> 5. **Networking Constraint:** Ubuntu 24 Docker containers MUST use `network_mode: "host"` to bypass NAT isolation, enabling FastDDS UDP multicast discovery on Domain 0.

## 1. Unified System Topology (V5)

This graph illustrates the OS boundaries, the Hybrid execution paths (Native vs. Docker), GPU passthrough, and FastDDS networking. (Adhering to strict Mermaid rendering constraints).

~~~mermaid
graph TD
    subgraph Host_OS_Environment
        OLL["qwen2.5-coder:3b (User-Space)"]
        H_SRC["Workspace Root (./)"]
        GPU["GPU & /dev/dri"]
        Watchdog["0.2s Watchdog"]
    end

    subgraph Ubuntu_22_Native_Path
        Nat_GZ["Native Gazebo (0ms Latenz)"]
        Nat_uROS["Native uros_ws (C++)"]
    end

    subgraph Ubuntu_24_Docker_Path
        Doc_GZ["Docker Gazebo (X11 Passthrough)"]
        Doc_WS["ros2_ws (Symlinked)"]
    end

    subgraph Physical_Edge_Network
        UDP["FastDDS UDP Multicast (Domain 0)"]
        ESP["ESP32 / Booster K1"]
    end

    H_SRC -.->|"Relative Bind Mount"| Doc_WS
    GPU ---|"NVreg_PreserveVideoMemoryAllocations=1"| OLL
    GPU ---|"X11 Forwarding"| Doc_GZ
    GPU --- Nat_GZ

    OLL <-->|"REST API"| Nat_GZ
    OLL <-->|"REST API (OLLAMA_HOST=0.0.0.0)"| Doc_GZ

    Nat_uROS <-->|"Direct UDP"| UDP
    Doc_WS <-->|"network_mode: host"| UDP
    UDP <-->|"Discovery"| ESP
~~~

## 2. Core Constraints & Data Flow

### A. Hybrid OS Topology & Execution
* **Problem:** ROS 2 Humble requires Ubuntu 22.04. Forcing Ubuntu 22.04 users into Docker creates unnecessary I/O overhead and FastDDS SHM blockades. However, Ubuntu 24.04 cannot install Humble natively.
* **Constraint:** The script `launch_r2k.sh` evaluates the OS at runtime.
  * **Ubuntu 22.04:** Bypasses Docker completely. Compiles and runs everything natively using `apt` and Python virtual environments for raw metal performance.
  * **Ubuntu 24.04:** Injects the current directory into a container via `docker compose up`.

### B. The Nvidia Xid 31 Suspend Bug
* **Problem:** After the host wakes up from Suspend-to-RAM, Ollama inference suddenly skyrockets from ~200ms to >7000ms. The LLM silently falls back to CPU because the VRAM Page Directories were corrupted during sleep (`NVRM: Xid 31 MMU Fault`).
* **Constraint:** Do NOT attempt to fix this by rebooting or patching Python scripts. The host kernel MUST be repaired by enabling the NVIDIA memory preservation module and activating `nvidia-suspend.service`.

### C. Docker Collision & Dynamic Naming
* **Problem:** Running multiple variations of the repository (e.g., `ros2k_sim` and `ros2k_lab`) on the same Ubuntu 24 host causes Docker to silently overwrite containers because the default compose project name is derived statically.
* **Constraint:** The boot script forces `export COMPOSE_PROJECT_NAME=$(basename "$PWD")`. This guarantees container namespace isolation based on the physical folder name.

### D. Workspace Migration Hygiene (The colcon Trap)
* **Problem:** The ROS 2 build flag `--symlink-install` permanently bakes absolute host file paths into the `install/` directory. If the folder is renamed, symlinks break silently.
* **Constraint:** When migrating workspaces, a blind copy is fatal. The `build/`, `install/`, and `log/` folders MUST be deleted, followed by a fresh `colcon build`.

## 3. Critical Code Interfaces

**Nvidia Xid 31 Kernel Repair (Host OS Execution):**
~~~bash
# 1. Force VRAM preservation during sleep
echo "options nvidia NVreg_PreserveVideoMemoryAllocations=1" | sudo tee /etc/modprobe.d/nvidia-power-management.conf
# 2. Enable the systemd hooks
sudo systemctl enable nvidia-suspend.service
sudo update-initramfs -u
~~~

**Dynamic Volume Mounts & Passthrough (`docker-compose.yml`):**
~~~yaml
# snippet representing Ubuntu 24.04 hardware passthrough
services:
  ros2k_core:
    image: ros2k_humble_base:v5
    network_mode: "host"
    devices:
      - /dev/dri:/dev/dri
    environment:
      - DISPLAY=$DISPLAY
      - LIBGL_ALWAYS_SOFTWARE=1
    volumes:
      - .:/root/ros2k_ws:rw
      - /tmp/.X11-unix:/tmp/.X11-unix:rw
~~~

**Hybrid OS Boot Logic (`launch_r2k.sh`):**
~~~bash
# snippet from the V5 boot sequence
UBUNTU_VERSION=$(lsb_release -rs)
export COMPOSE_PROJECT_NAME=$(basename "$PWD")
export OLLAMA_HOST=0.0.0.0

if [ "$UBUNTU_VERSION" == "22.04" ]; then
    echo "Native Ubuntu 22.04 detected. Bypassing Docker..."
    source install/setup.bash
    # Execute natively
else
    echo "Ubuntu 24.04 detected. Starting Hybrid Docker Stack..."
    xhost +local:root
    docker compose up -d
fi
~~~

---

## V6.1 Addendum: Headless Gazebo & Docker Env Passthrough

> [!warning] V6.1 Extension
> V6.1 adds headless Gazebo mode (gzserver only) for batch evaluation and propagates `R2K_RUN_ID`
> into Docker containers for trace logging correlation. Source: `launch_r2k.sh`,
> `ros2_ws/src/r2k_scenario_spawner/launch/soccer_match.launch.py`.

### Headless Gazebo (gzserver only)

* `soccer_match.launch.py` now declares a `headless` launch argument (default `false`).
* When `headless:=true`, only `gzserver` is launched — no `gzclient` GUI. This eliminates rendering overhead for batch evaluation.
* `launch_r2k.sh:188` passes `headless:=true` when `--headless` flag is set (native path).
* `launch_r2k.sh:299` passes `headless:=true` for Docker path.
* Expected: 30-50% faster physics-only simulation vs. full GUI rendering.
* The watchdog still works: it polls for `gazebo|gzserver|ruby` PID, so headless runs are torn down correctly on CTRL+C or duration timeout.

### Docker Env Passthrough

* `launch_r2k.sh:82` exports `R2K_RUN_ID` on the host.
* Native path: child processes inherit the env var automatically.
* Docker path: `R2K_RUN_ID` is explicitly passed via `docker exec -d -e R2K_RUN_ID="$R2K_RUN_ID"` to `state_aggregator.py` (`launch_r2k.sh:357`) and `r2k_evaluator.py` (`launch_r2k.sh:362`).
* Without this explicit passthrough, Docker containers do NOT inherit host env vars by default, and trace files would be named with the fallback `run_{timestamp}` instead of the correlated run ID.
* `R2K_OLLAMA_MODEL` and `R2K_OLLAMA_URL` are also passed through (`launch_r2k.sh:362`) to allow per-run model selection.
