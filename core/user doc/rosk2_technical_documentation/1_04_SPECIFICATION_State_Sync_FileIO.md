---
id: 1_04
title: "State Sync & File I/O"
type: SPECIFICATION
tags: [json, file-io, disk, decoupling]
last_modified: 2026-05-31
version: v5_release
---
# State Sync & File I/O

> [!info] Human Summary
> Explains why ROS2K eschews traditional ROS 2 Custom Messages in favor of writing text-based JSON dictionaries directly to a RAM-backed disk for inter-process communication.

> [!abstract] LLM Context Anchor
> File I/O polling via `tmpfs` is the primary decoupled multiplexing strategy. Custom ROS 2 `msg` types are strictly avoided for AI payload transfer to maintain absolute modularity between Python versions and libraries.
> **[NEW in v5]:** The `shared_state/` folder MUST exist on the host filesystem. If missing, `r2k_evaluator.py` crashes silently with `FileNotFoundError`. All write operations must use POSIX atomic renames (`os.replace`) to prevent read collisions.

## 1. System Topology of RAM-Backed File I/O

**[DEPRECATED in v4] Original Topology:**
This graph demonstrates the exact file paths and access modes utilized to decouple the ROS 2 stack from the AI evaluation loop.

~~~mermaid
graph TD
    subgraph Memory ["RAM Disk tmpfs"]
        WS[("Worldstate.json")]
        CS[("current_strategy.json")]
    end

    T["tracker.py"] -->|Atomic Write| WS
    E["r2k_evaluator.py"] -->|Read Poll| WS
    E -->|Atomic Write| CS
    B["ollama_sandbox_bridge.py"] -->|Read Poll| CS

    style WS fill:#f9f,stroke:#333
    style CS fill:#f9f,stroke:#333
~~~

**[NEW in v5] Aggregated Topology:**
The pipeline now incorporates the `state_aggregator.py` to unify disparate metrics before writing to the RAM disk, and enforces the fully qualified node names.

~~~mermaid
graph TD
    subgraph Memory ["RAM Disk tmpfs"]
        WS[("Worldstate.json")]
        CS[("current_strategy.json")]
    end

    T["tracker_node.py / referee_node.py"] -->|Publish| SA["state_aggregator.py"]
    SA -->|POSIX Atomic Rename| WS
    E["r2k_evaluator.py"] -->|Read Poll| WS
    E -->|POSIX Atomic Rename| CS
    B["ollama_sandbox_bridge.py"] -->|Read Poll| CS

    style WS fill:#f9f,stroke:#333
    style CS fill:#f9f,stroke:#333
~~~

## 2. Architectural Logic & Data Flow
Utilizing custom ROS 2 message definitions requires rigid `colcon build` compilation, strict type safety, and forces the LLM evaluation scripts into the ROS 2 dependency tree. 

**[DEPRECATED in v4]:** By pushing the parsed 2D coordinate matrix into `Worldstate.json` and the LLM's tactical output into `current_strategy.json`, the architecture achieves extreme modularity. 
**[UPDATE in v5]:** State generation is now centralized. The `state_aggregator.py` bundles the coordinate matrix from the tracker with the match score and game state into a unified JSON payload before writing to the disk.

The `r2k_evaluator.py` can crash, be live-edited, or swapped from Nemotron to OpenAI without dropping a single Gazebo physics frame or requiring a ROS 2 workspace rebuild. Storing these files in a RAM-backed `tmpfs` eliminates physical disk latency and SSD wear-leveling concerns during the 10Hz write cycles.

**[NEW in v5] POSIX Atomic Rename (`os.replace`):** To prevent `JSONDecodeError` collisions when the asynchronous Execution Loop reads exactly as the Cognitive Loop writes, all file modifications must target a `.tmp` file first, followed by a hardware-level atomic rename to `.json`.

## 3. Code Reference & Interfaces
> **Source:** [`docker-compose.yml`](../src/docker-compose.yml)

The `tmpfs` mounting logic within the infrastructure configuration ensures zero I/O blocking.
~~~yaml
# snippet from docker-compose.yml
services:
  ros2k_core:
    image: ros2k_humble_base:latest
    network_mode: "host"
    volumes:
      - ./src:/root/ros2k_unify2
    tmpfs:
      # Mount the shared_state directory strictly into RAM
      - /root/ros2k_unify2/shared_state:rw,noexec,nosuid,size=64m
~~~

## 4. Known Issues & Limitations
* Docker container restarts wipe the `tmpfs` contents, erasing the last known state.
* Excessive payload string sizes can cause RAM allocation faults if log histories are appended instead of overwritten.
* **[CRITICAL in v5]:** The `shared_state/` directory MUST exist on the host filesystem prior to launching. If it is missing, `tmpfs` mounting fails or background daemons die silently with a `FileNotFoundError`.

## 5. Glossary
* **`tmpfs`:** A temporary file storage facility on Unix-like operating systems that resides purely in memory.
* **Decoupled Multiplexing:** The architectural pattern of connecting disparate system processes via standardized text files rather than in-memory message buses.
* **[NEW in v5] Atomic Rename:** The use of `os.replace()` to swap file pointers at the OS-level, ensuring thread-safe reads without locking mechanisms.
