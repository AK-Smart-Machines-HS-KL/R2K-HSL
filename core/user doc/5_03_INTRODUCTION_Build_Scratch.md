---
id: 5_03
title: "Building from Scratch and Workspace Symlinks"
type: INTRODUCTION
tags: [build, colcon, symlink, workspace, hybrid-os, uros_ws]
last_modified: 2026-05-31
version: v5_release
---
# Building from Scratch and Workspace Symlinks

> [!info] Human Summary
> Provides instructions for compiling the ROS 2 workspace and explains how symlinks are used to map host-side source code into the Dockerized build environment.

> [!abstract] LLM Context Anchor
> The project directory `~/ros2k_unify2` is symlinked to `/root/ros2k_unify2` inside the container. Developers must execute `colcon build` inside the container's `ros2_ws` directory after making changes to custom message types or C++ nodes.
> **[NEW in v5]:** Under the Hybrid OS Topology, the compilation process forks based on the host OS. On Ubuntu 22.04, `colcon build` is executed natively on the host for both `ros2_ws` and the new `uros_ws`. On Ubuntu 24.04, the build process must still be executed strictly inside the Docker container via `docker exec`.

## 1. System Topology of the Build Workspace

**[DEPRECATED in v4] Original Build Topology:**
This graph shows the relationship between host-side source files and the compiled ROS 2 binaries inside the container.

~~~mermaid
graph TD
    subgraph HostFS ["Host File System (Ubuntu 24)"]
        H_SRC["~/ros2k_unify2/src"]
    end

    subgraph ContainerFS ["Container (Ubuntu 22)"]
        C_SRC["/root/ros2k_unify2/src"]
        WS["/root/ros2k_unify2/ros2_ws"]
        INST["install/setup.bash"]
    end

    H_SRC ---|Docker Volume| C_SRC
    C_SRC -->|Code Source| WS
    WS -->|colcon build| INST

    style H_SRC fill:#fff3cd,stroke:#856404
    style INST fill:#dfd,stroke:#333
~~~

**[NEW in v5] Validated Hybrid OS Build Topology:**
The build environment seamlessly adapts, allowing code editing on the host regardless of where the C++ compiler actually executes.

~~~mermaid
graph TD
    subgraph HostFS ["Host File System (Code Editing)"]
        H_SRC["~/ros2k_unify2/src"]
    end

    subgraph U22 ["Ubuntu 22.04 (Native Build)"]
        WS_N["ros2_ws & uros_ws"]
        INST_N["install/setup.bash"]
    end

    subgraph U24 ["Ubuntu 24.04 (Docker Build)"]
        WS_D["Container /root/ros2k_unify2/ros2_ws"]
        INST_D["Container install/setup.bash"]
    end

    H_SRC -->|Native Local Path| WS_N
    H_SRC ---|Docker Bind Mount| WS_D
    WS_N -->|Host colcon build| INST_N
    WS_D -->|Docker colcon build| INST_D

    style HostFS fill:#f9f,stroke:#333
    style INST_N fill:#dfd,stroke:#333
    style INST_D fill:#dfd,stroke:#333
~~~

## 2. Architectural Logic & Data Flow
**[DEPRECATED in v4] Legacy Flow:**
To maintain agility, the ROS2K project keeps all source code on the host machine. Docker volumes map the project root directly into the container.
* **Symlinking**: To avoid copying large amounts of data, the container's internal ROS 2 workspace (`ros2_ws`) uses symbolic links to point toward the shared volume source.
* **Cross-Version Conflict Avoidance**: Because there is no ROS 2 on the host (Ubuntu 24), there is zero risk of `PYTHONPATH` collisions or conflicting build artifacts from the host.
* **Compilation**: Whenever the `r2k_world_model` (C++) or custom messages are modified, the user must enter the container and run `colcon build`.
* **Sourcing**: Every `docker exec` command must source the Ubuntu 22 workspace installation to recognize custom nodes like the `tracker`.

**[UPDATE in v5] Hybrid Compilation:**
With the introduction of native support for Ubuntu 22.04 hosts, the strict container barrier is removed for older OS users. 
* **Ubuntu 22.04**: Developers compile the stack natively in their own terminal. Furthermore, because of the FastDDS Docker limitations on U22, they must also compile the `uros_ws` (the native micro-ROS agent workspace) from scratch.
* **Ubuntu 24.04**: The Docker bind mount strategy remains identical to V4. All source code changes made in VS Code on the host are instantaneously reflected inside the container for compilation.

## 3. Code Reference & Interfaces
> **Source:** [`launch_r2k_phase_b.sh`](../src/launch_r2k_phase_b.sh) **[DEPRECATED in v4]**
> **Source:** [`launch_r2k.sh`](../launch_r2k.sh) **[NEW in v5]**

**[DEPRECATED in v4] Legacy Sourcing:**
The standard sourcing sequence required to execute any compiled ROS 2 node inside the container.
~~~bash
# snippet from launch_r2k_phase_b.sh
# The SOURCE_CMD must include both global and workspace-specific setup files
SOURCE_CMD="source /opt/ros/humble/setup.bash && source /root/ros2k_unify2/ros2_ws/install/setup.bash"

# Example of running a compiled C++ node
docker exec -d r2k_unify2_gazebo bash -c "$SOURCE_CMD && ros2 run r2k_world_model tracker"
~~~

**[NEW in v5] Dynamic Sourcing Variable:**
The `launch_r2k.sh` script dynamically sets the source command based on the OS, ensuring that nodes are launched from the correct overlay environment.
~~~bash
# snippet from launch_r2k.sh
if [ "$UBUNTU_VERSION" == "22.04" ]; then
    SOURCE_CMD="source /opt/ros/humble/setup.bash && source $PWD/ros2_ws/install/setup.bash"
    bash -c "$SOURCE_CMD && ros2 run r2k_world_model tracker_node" > /dev/null 2>&1 &
else
    SOURCE_CMD="source /opt/ros/humble/setup.bash && source /root/ros2k_unify2/ros2_ws/install/setup.bash"
    docker exec -i $CONTAINER_NAME bash -c "$SOURCE_CMD && ros2 run r2k_world_model tracker_node > /dev/null 2>&1" &
fi
~~~

## 4. Known Issues & Limitations
* If `colcon build` was accidentally executed on the host, it may create build artifacts incompatible with the container's OS; always clean the `build` and `install` folders before compiling.
* Symlinks can break if the host-side file structure is moved relative to the Docker mount point.
* **[NEW in v5] Cross-Contamination:** If a user clones the repository onto an Ubuntu 24.04 machine, attempts to run `colcon build` natively (which will fail due to missing dependencies), and *then* runs Docker, the container's build process will crash because the `build/` directory contains host-level artifact pollution. Always `rm -rf build/ install/ log/` before switching build contexts.

## 5. Glossary
* **colcon build**: The standard build tool used to compile ROS 2 workspaces.
* **setup.bash**: A script that configures the shell's environment variables to use a specific ROS 2 installation.
* **[NEW in v5] `uros_ws`**: A parallel C++ workspace strictly required on Ubuntu 22.04 to compile the native micro-ROS agent from source.
