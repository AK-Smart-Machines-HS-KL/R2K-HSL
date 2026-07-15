---
id: 1_05
title: "Mitigating Race Conditions"
type: CHEATPAGE
tags: [hacks, race-conditions, posix, file-locking]
last_modified: 2026-05-31
version: v5_release
---
# Mitigating Race Conditions

> [!info] Human Summary
> Details the critical file-system hack used to prevent JSON read/write collisions between high-frequency physics writers and asynchronous AI readers.

> [!abstract] LLM Context Anchor
> File deadlocks are bypassed using POSIX atomic renames (`os.replace`). Standard file-locking (`fcntl`) is strictly prohibited as it forces the ROS 2 physical loop to block waiting for AI file handles to release.
> **[NEW in v5]:** Write operations are now strictly centralized. The tracker node no longer writes directly to disk; this is handled entirely by `state_aggregator.py`.

## 1. System Topology of Atomic File Renaming

**[DEPRECATED in v4] Original Tracker Flow:**
This graph breaks down the operational sequence of the POSIX atomic rename hack to prevent `JSONDecodeError` crashes.

~~~mermaid
graph TD
    subgraph WriteSequence ["Tracker Flow"]
        Mem["Dict in RAM"]
        Tmp[("Worldstate.json.tmp")]
        Final[("Worldstate.json")]
    end

    subgraph ReadSequence ["Evaluator Flow"]
        E["r2k_evaluator.py"]
    end

    Mem -->|IO Dump| Tmp
    Tmp -->|os.replace Swap| Final
    Final -->|Safe Read| E

    style Tmp fill:#ddd,stroke:#333,stroke-dasharray: 5 5
    style Final fill:#f9f,stroke:#333
~~~

**[NEW in v5] Aggregator Flow:**
The sequence remains mechanically identical, but the writer entity is now the unified V5 Engine node.

~~~mermaid
graph TD
    subgraph WriteSequence ["state_aggregator.py Flow"]
        Mem["Unified Dict in RAM"]
        Tmp[("Worldstate.json.tmp")]
        Final[("Worldstate.json")]
    end

    subgraph ReadSequence ["Evaluator Flow"]
        E["r2k_evaluator.py"]
    end

    Mem -->|IO Dump| Tmp
    Tmp -->|os.replace Swap| Final
    Final -->|Safe Read| E

    style Tmp fill:#ddd,stroke:#333,stroke-dasharray: 5 5
    style Final fill:#f9f,stroke:#333
~~~

## 2. Architectural Logic & Data Flow
**[DEPRECATED in v4] The Problem:** `tracker.py` writes physics data at 10Hz. `r2k_evaluator.py` polls this data asynchronously. Statistically, the Evaluator will inevitably attempt to read `Worldstate.json` at the exact microsecond the Tracker is half-way through writing the string buffer to disk. This yields a truncated JSON string and a fatal `JSONDecodeError`. Standard OS file-locking creates unacceptable latency for the 10Hz physics loop.

**[UPDATE in v5] The Problem:** Same as above, but `state_aggregator.py` is now responsible for the 10Hz write cycles.

**The Solution:** The Tracker **[UPDATE in v5: now state_aggregator.py]** writes its JSON dump to a `.tmp` file (`Worldstate.json.tmp`). Once the OS buffer flushes and the file handle closes, it executes a POSIX `rename` operation to overwrite the primary `Worldstate.json`. Under the Linux kernel, `rename` is an atomic directory entry swap. The Evaluator will thus only ever encounter the *old* complete file or the *new* complete file—never a partial write.

## 3. Code Reference & Interfaces
> **Source:** [`r2k_world_model/tracker.py`](../src/r2k_world_model/tracker.py) **[DEPRECATED in v4]**
> **Source:** [`state_aggregator.py`](../state_aggregator.py) **[NEW in v5]**

**[DEPRECATED in v4] Legacy Implementation:**
The atomic write-and-swap logic executed during the `/gazebo/model_states` subscription callback.
~~~python
# snippet from tracker.py
import json, os

def listener_callback(self, msg):
    world_state = {"entities": extract_entities(msg)}
    
    temp_path = "shared_state/Worldstate.json.tmp"
    final_path = "shared_state/Worldstate.json"
    
    try:
        # Write to temporary file first
        with open(temp_path, 'w') as f:
            json.dump(world_state, f)
            
        # Execute atomic kernel rename
        os.replace(temp_path, final_path)
    except Exception as e:
        self.get_logger().error(f"Write failure: {e}")
~~~

**[NEW in v5] Centralized Aggregator Implementation:**
The exact same POSIX atomic logic is now executed within `state_aggregator.py`, preventing race conditions across the newly unified JSON payload.

## 4. Known Issues & Limitations
* This hack relies explicitly on POSIX compliant file systems. Deploying this architecture on native Windows (non-WSL) will result in file access violation errors during `os.replace`.
* **[CRITICAL in v5]:** If the `shared_state/` directory does not exist prior to launch, `open(temp_path, 'w')` fails immediately, causing a silent `FileNotFoundError` daemon crash instead of creating the necessary folder.

## 5. Glossary
* **Atomic Operation:** An operation that runs completely independently of any other processes and cannot be interrupted mid-execution.
* **POSIX:** Portable Operating System Interface standards ensuring atomic directory manipulation on Linux/macOS.
