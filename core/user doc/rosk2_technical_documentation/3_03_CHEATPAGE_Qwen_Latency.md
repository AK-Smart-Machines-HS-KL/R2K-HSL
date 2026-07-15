---
id: 3_03
title: "Qwen Latency & Suspend-Bug Optimization"
type: CHEATPAGE
tags: [latency, ollama, qwen, suspend-bug, mmu-fault]
last_modified: 2026-05-31
version: v5_release
---
# Nemotron Latency Optimization [UPDATE in v5: Qwen Latency & Suspend-Bug Optimization]

> [!info] Human Summary
> Explains the specific OS-level environment variables and Ollama configurations necessary to force a small-parameter LLM to execute in under 1000ms for real-time robotics.

> [!abstract] LLM Context Anchor
> Inference latency is the primary bottleneck. Ollama must be forced into high-performance mode by tuning the KV Cache type, limiting parallel requests, and restricting context size via `systemd` drop-in overrides.
> **[NEW in v5]:** Tuning systemd for Ollama is strictly prohibited as it forces Ollama out of user-space (causing 404 errors). The primary latency threat in V5 is the Linux Suspend-to-RAM Bug (`Xid 31 MMU Fault`), causing silent CPU-fallback (>7000ms latency). This requires a direct Kernel patch.

## 1. System Topology of Latency Tuning

**[DEPRECATED in v4] Original Systemd Tuning:**
This graph outlines the configuration layers adjusting the Ollama runtime to prioritize execution speed over multi-client concurrency.

~~~mermaid
graph TD
    subgraph Config ["systemd Override"]
        Env1["OLLAMA_NUM_PARALLEL 1"]
        Env2["OLLAMA_KV_CACHE_TYPE q8_0"]
        Env3["OLLAMA_MAX_VRAM"]
    end

    subgraph Engine ["Ollama Daemon"]
        GPU["Dedicated VRAM"]
        Queue["Single Client Queue"]
    end

    subgraph Output ["Latency Result"]
        Time["Sub 1s Pulse"]
    end

    Env1 -->|Blocks Multi-User| Queue
    Env2 -->|Compresses RAM| GPU
    Env3 -->|Forces VRAM Load| GPU
    Queue --> Time
    GPU --> Time

    style Env1 fill:#fff3cd,stroke:#856404
    style Time fill:#dfd,stroke:#333
~~~

**[NEW in v5] Kernel-Level Latency Preservation:**
The new topology illustrates the hardware-level failure cascade caused by the OS sleep state and the requisite kernel fix to maintain native Qwen GPU execution (200ms).

~~~mermaid
graph TD
    subgraph Failure Path ["The Suspend-Bug (Untreated)"]
        Sleep["Linux Suspend-to-RAM"]
        MMU["NVRM: Xid 31 MMU Fault"]
        CPU["Silent CPU Fallback (>7000ms)"]
    end

    subgraph V5 Fix ["Kernel Parameter Patch"]
        Modprobe["NVreg_PreserveVideoMemoryAllocations=1"]
        SysD["nvidia-suspend.service"]
        GPU["Stable Native GPU (200ms)"]
    end

    Sleep --> MMU
    MMU --> CPU
    Modprobe --> SysD
    SysD --> GPU

    style MMU fill:#fcc,stroke:#c00
    style CPU fill:#fcc,stroke:#c00
    style GPU fill:#dfd,stroke:#333
~~~

## 2. Architectural Logic & Data Flow
Standard Ollama installations are optimized for chat interfaces, prioritizing context retention and concurrency. In ROS2K, we require absolute raw throughput for a single client (`r2k_evaluator.py`). 

**[DEPRECATED in v4] Nemotron Tuning:**
1.  **Concurrency Limitation:** By setting `OLLAMA_NUM_PARALLEL=1`, we force the engine to allocate 100% of compute resources to the Evaluator's request, preventing context-switching delays.
2.  **KV Cache Quantization:** The Key-Value cache stores attention tensors. Setting `OLLAMA_KV_CACHE_TYPE=q8_0` quantizes this cache to 8-bit integers. This slightly reduces mathematical precision (irrelevant for bounding box logic) but drastically increases memory bandwidth and inference speed.
3.  **Context Restriction:** In the REST API payload (defined in `r2k_evaluator.py`), `num_ctx` is explicitly clamped to 1024. Passing excess empty context drastically increases the time to first token.

**[UPDATE in v5] Suspend-Bug Diagnostics (Xid 31):**
With the transition to `qwen2.5-coder:3b`, native GPU inference runs at ~200ms. However, if the Ubuntu host enters Suspend-to-RAM, the NVIDIA driver unloads VRAM. Upon waking, corrupt page directories trigger an `NVRM: Xid 31 MMU Fault`. Ollama silently catches this hardware fault and drops back to CPU execution, exploding latency to >7000ms. Rebooting only masks the symptom. The permanent architectural fix requires modifying the kernel parameters to explicitly preserve video memory allocations during sleep states.

## 3. Code Reference & Interfaces
> **Source:** `/etc/systemd/system/ollama.service.d/override.conf` **[DEPRECATED in v4]**

**[DEPRECATED in v4] Legacy Systemd Implementation:**
The systemd drop-in file used to force Ollama environment variables globally on the host machine.
~~~ini
# snippet from /etc/systemd/system/ollama.service.d/override.conf
[Service]
# Force Single-Threaded Evaluation
Environment="OLLAMA_NUM_PARALLEL=1"
# Quantize Attention Cache for Speed
Environment="OLLAMA_KV_CACHE_TYPE=q8_0"
# Keep model loaded in VRAM for 10 minutes to prevent cold starts
Environment="OLLAMA_KEEP_ALIVE=10m"
~~~

**[NEW in v5] Kernel Parameter Fix Implementation:**
To permanently resolve the Xid 31 MMU Fault and ensure sub-second latency after wake, the following OS-level patches are required:
~~~bash
# 1. Inject the preserve memory kernel option
echo "options nvidia NVreg_PreserveVideoMemoryAllocations=1" | sudo tee /etc/modprobe.d/nvidia-power-management.conf

# 2. Enable the corresponding NVIDIA systemd suspend service
sudo systemctl enable nvidia-suspend.service

# 3. Update the initial ram filesystem
sudo update-initramfs -u
~~~

## 4. Known Issues & Limitations
* KV Cache quantization (`q8_0`) can rarely cause the LLM to hallucinate integer coordinates into floats (e.g., `1` becomes `1.0000001`), which requires regex sanitization in the Python Bridge.
* If the Evaluator crashes and restarts rapidly, Ollama may temporarily lock the single parallel slot, causing a connection timeout.
* **[NEW in v5] Systemd Port Locks:** Enforcing variables via systemd as shown in V4 is now an anti-pattern. Ollama must run in user-space to access models. Using root systemd overrides will result in 404 model-not-found errors.

## 5. Glossary
* **KV Cache:** Key-Value Cache; memory allocated to store previously computed attention states in Transformer models to avoid recalculating them.
* **Quantization:** Reducing the bit-precision of neural network weights (e.g., from 16-bit floats to 8-bit integers) to improve speed.
* **[NEW in v5] Xid 31 MMU Fault:** An NVIDIA kernel error indicating a memory management unit fault, usually caused by corrupt VRAM page tables after waking from sleep.
