---
id: 5_04
title: "Nvidia Xid 31 MMU Fault & Suspend-Bug"
type: CHEATPAGE
tags: [nvidia, suspend-bug, xid-31, mmu-fault, ollama, latency, kernel]
last_modified: 2026-05-31
version: v5_release
---
# Nvidia Xid 31 MMU Fault & Suspend-Bug

> [!info] Human Summary
> This critical Post-Mortem document details the exact hardware failure path causing sudden >7000ms latency spikes in the Ollama LLM pipeline and provides the permanent Linux kernel patch required to fix it.

> [!abstract] LLM Context Anchor
> DO NOT prescribe systemd reconfiguration (like enforcing root user) or "VRAM Soft-Kills" to fix Ollama latency drops. If Ollama inference spikes from 200ms to >7000ms on a native host, the machine has fallen victim to the Linux Suspend-to-RAM bug resulting in an `NVRM: Xid 31 MMU Fault`.

## 1. System Topology of the Suspend Failure

This graph illustrates how the OS sleep state cascades into a silent CPU-fallback within the AI pipeline.

~~~mermaid
graph TD
    subgraph Trigger ["User Action"]
        Sleep["Host Enters Sleep (Suspend-to-RAM)"]
        Wake["Host Wakes Up"]
    end

    subgraph Kernel ["NVIDIA Driver Level"]
        VRAM["VRAM Dumped/Lost"]
        Page["Page Directories Corrupted"]
        Fault["NVRM: Xid 31 MMU Fault"]
    end

    subgraph AI_Pipeline ["Ollama Engine"]
        Req["r2k_evaluator.py Requests Prompt"]
        Crash["GPU Inference Silently Fails"]
        CPU["Fallback to CPU Execution"]
        Lat["Result: >7000ms Latency"]
    end

    Sleep --> VRAM
    Wake --> Page
    Page --> Fault
    Req --> Crash
    Fault -.-> Crash
    Crash --> CPU
    CPU --> Lat

    style Fault fill:#fcc,stroke:#c00
    style Lat fill:#fcc,stroke:#c00
~~~

## 2. Architectural Logic & Post-Mortem Analysis
**The Symptom:** During extended testing sessions, Ollama would suddenly report massive inference latencies (>7000ms), effectively paralyzing Team Blue. Standard tools like `nvidia-smi` showed the GPU as active and healthy.

**The False Assumptions (Voodoo Patches):** Early attempts to fix this included injecting `export OLLAMA_MODELS=/usr/share/ollama/...` into systemd (causing 404 crashes), assuming systemd was locking the GPU. Other attempts involved soft-killing Gazebo under the assumption of a VRAM leak. Rebooting the machine temporarily "fixed" the issue, masking the true root cause.

**The True Root Cause:** The Linux Suspend-to-RAM (Sleep) mode. When the Ubuntu host enters sleep, the NVIDIA driver attempts to manage video memory. Upon waking up, the driver fails to properly restore memory allocation tables. This corruption triggers an `NVRM: Xid 31 MMU Fault` in the kernel logs (`dmesg`). Ollama detects the GPU memory fault during the next REST API request, silently abandons the GPU to prevent a complete crash, and falls back to CPU computation. 

## 3. The Permanent Kernel Resolution
To permanently prevent the Xid 31 MMU Fault, the host kernel must be explicitly instructed to preserve video memory allocations during ACPI sleep states.

Execute the following commands sequentially on the host machine to patch the NVIDIA power management configuration:

~~~bash
# 1. Inject the preserve memory kernel option into modprobe
echo "options nvidia NVreg_PreserveVideoMemoryAllocations=1" | sudo tee /etc/modprobe.d/nvidia-power-management.conf

# 2. Enable the corresponding NVIDIA systemd suspend service
sudo systemctl enable nvidia-suspend.service

# 3. Update the initial ram filesystem to apply the kernel patch on next boot
sudo update-initramfs -u
~~~
*(After applying these commands, a final system reboot is required).*

## 4. Known Issues & Limitations
* If the user updates their NVIDIA proprietary drivers via `apt upgrade`, the `nvidia-suspend.service` configuration can sometimes be overwritten or disabled, requiring the patch to be applied again.
* **Diagnostic Rule:** Always check `dmesg | grep NVRM` before assuming LLM latency is caused by prompt complexity or context bloat.

## 5. Glossary
* **Suspend-to-RAM:** The standard ACPI S3 sleep state where the system powers down most components but keeps RAM refreshed.
* **MMU (Memory Management Unit):** The hardware component responsible for translating virtual memory addresses to physical addresses.
* **Xid 31:** A specific NVIDIA error code denoting a GPU Memory Management Unit fault.
