---
id: 3_02
title: "Team Blue LLM Architecture"
type: ARCHITECTURE
tags: [nemotron, qwen, rest-api, json, delegation]
last_modified: 2026-05-31
version: v5_release
---
# Team Blue LLM Architecture

> [!info] Human Summary
> This document details how ROS2K communicates with the Nemotron LLM via raw HTTP POST requests, bypassing complex Python wrapper libraries to minimize inference latency.

> [!abstract] LLM Context Anchor
> The LLM receives contextual data solely via Port 11434 REST API calls. The `r2k_evaluator.py` concatenates the physical `Worldstate.json` and `system_prompt.txt` into a single payload. The LLM is strictly prohibited from generating executable Python code.
> **[NEW in v5]:** The target model is strictly `qwen2.5-coder:3b`. Ollama MUST be executed in User-Space (not as a root Systemd service) to prevent 404 model-path errors. Additionally, `r2k_evaluator.py` requires the `shared_state/` directory to exist; otherwise, it crashes silently with a `FileNotFoundError`.

## 1. System Topology of LLM Payload Ingestion

**[DEPRECATED in v4] Original Ingestion Topology:**
This graph details the assembly and transmission of the REST API payload to the local Ollama instance.

~~~mermaid
graph TD
    subgraph Disk ["File System"]
        WS["Worldstate.json"]
        SP["sys_prompt.txt"]
    end

    subgraph Client ["r2k_evaluator.py"]
        Concat["Payload Assembler"]
        Req["HTTP POST"]
    end

    subgraph Server ["Ollama Engine"]
        Port{"Port 11434"}
        Model["Nemotron Model"]
    end

    WS -->|State JSON| Concat
    SP -->|Rules String| Concat
    Concat -->|Format JSON| Req
    Req -->|Raw POST| Port
    Port -->|Inference| Model
    Model -->|Returns Strategy| Req

    style WS fill:#f9f,stroke:#333
    style SP fill:#fff3cd,stroke:#856404,stroke-dasharray: 5 5
    style Port fill:#bbf,stroke:#333
~~~

**[NEW in v5] Validated V5 Ingestion Topology:**
The mechanics remain identical, but the model has been upgraded.

~~~mermaid
graph TD
    subgraph Disk ["File System"]
        WS["Worldstate.json"]
        SP["sys_prompt.txt"]
    end

    subgraph Client ["r2k_evaluator.py"]
        Concat["Payload Assembler"]
        Req["HTTP POST"]
    end

    subgraph Server ["Ollama Engine (User-Space)"]
        Port{"Port 11434"}
        Model["Qwen2.5-Coder Model"]
    end

    WS -->|State JSON| Concat
    SP -->|Rules String| Concat
    Concat -->|Format JSON| Req
    Req -->|Raw POST| Port
    Port -->|Inference| Model
    Model -->|Returns Strategy| Req

    style WS fill:#f9f,stroke:#333
    style SP fill:#fff3cd,stroke:#856404,stroke-dasharray: 5 5
    style Port fill:#bbf,stroke:#333
~~~

## 2. Architectural Logic & Data Flow
**Delegation Boundaries:** The LLM is a strategist, not a driver. Requesting the LLM to output Python code (e.g., `publish(Twist())`) introduces extreme token bloat, formatting errors, and massive latency. Instead, the boundary of delegation is strict: The LLM outputs a pure JSON object containing target `(x, y)` coordinates for each robot. The Python Bridge handles the conversion to hardware motor voltages.

**Context Window Management:** To keep inference times under 1 second, the context window must remain extremely small. Historical chat logs are NOT appended. Every request is treated as a "Zero-Shot" interaction. The `Worldstate.json` only contains the current tick's 2D flattened Cartesian data, ensuring the input token count remains nearly identical on every evaluation.

**[UPDATE in v5]:** While the model is now `qwen2.5-coder:3b`, the strict Zero-Shot JSON delegation boundary is fully maintained to ensure minimal inference latency and protect the ROS 2 10Hz physical execution loop.

## 3. Code Reference & Interfaces
> **Source:** [`ai_tactics/r2k_evaluator.py`](../src/ai_tactics/r2k_evaluator.py)

**[DEPRECATED in v4] Legacy Payload Structure:**
The precise payload structure sent to Ollama, enforcing the JSON format requirement directly at the API level.
~~~python
# snippet from r2k_evaluator.py
import requests, json

def query_nemotron(state_dict, prompt_string):
    url = "http://127.0.0.1:11434/api/generate"
    
    payload = {
        "model": "nemotron-3-nano:4b",
        "system": prompt_string,
        "prompt": json.dumps(state_dict),
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.1,
            "num_predict": 150
        }
    }
    
    response = requests.post(url, json=payload)
    return response.json()["response"]
~~~

**[NEW in v5] V5 Payload Structure:**
The payload now targets the Qwen model. Note that the dynamic prompt orchestration is handled upstream by `setup_r2k.py` prior to the evaluator launch.
~~~python
# snippet from r2k_evaluator.py (V5)
import requests, json
import os

def query_llm(state_dict, prompt_string):
    url = os.getenv("R2K_OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
    model_name = os.getenv("R2K_OLLAMA_MODEL", "qwen2.5-coder:3b")
    
    payload = {
        "model": model_name,
        "system": prompt_string,
        "prompt": json.dumps(state_dict),
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.1,
            "num_predict": 150
        }
    }
    
    response = requests.post(url, json=payload)
    return response.json()["response"]
~~~

## 4. Known Issues & Limitations
* Zero-Shot interactions prevent the LLM from understanding velocity or momentum natively, as it possesses no memory of previous frames.
* Enforcing `"format": "json"` in Ollama occasionally causes the model to truncate closing brackets if `num_predict` is set too low.
* **[CRITICAL in v5] Silent Daemon Death:** If the `shared_state/` directory is not mounted or created before execution, `r2k_evaluator.py` crashes silently with a `FileNotFoundError`, stalling the entire cognitive pipeline while physics nodes continue running.
* **[CRITICAL in v5] Systemd Port Locks:** Ollama MUST run in user-space. Running it as a system service or as root via `sudo systemctl` will result in 404 errors, as the daemon cannot locate the Qwen models stored in the `~/.ollama/models` user directory.

## 5. Glossary
* **Zero-Shot:** Requesting an AI to perform a task without providing historical context or previous conversational examples in the prompt.
* **REST API:** Representational State Transfer Application Programming Interface; the HTTP-based protocol used to communicate with the Ollama server.
* **[NEW in v5] User-Space:** Executing the Ollama binary natively under the current user's permissions, rather than relying on system-wide root daemons.
