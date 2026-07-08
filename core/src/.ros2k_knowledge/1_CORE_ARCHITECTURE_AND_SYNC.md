---
id: 1_CORE
title: "Section 1: System Overview, Core Architecture & State Sync (V5)"
type: KNOWLEDGE_BASE_POWER_FILE
tags: [architecture, tmpfs, threading, race-conditions, decoupled-multiplexing, os.replace, qwen, state-aggregator, v5]
last_modified: 2026-05-31
version: v5_release
---
# Section 1: System Overview, Core Architecture & State Sync

> [!abstract] LLM Context Anchor
> **CRITICAL AXIOMS FOR RAG RETRIEVAL:**
> 1. **Ground Truth:** ROS2K strictly ingests `/gazebo/model_states`. NEVER assume the use of individual `/odom` topics or TF2 transform trees for basic spatial awareness.
> 2. **Hardware Abstraction:** There are NO Object-Oriented C++ HALs or class inheritances (e.g., `BaseBotDriver`). The Bridge uses dynamic threaded closures (`def task`) for PID control.
> 3. **Concurrency:** The LLM operates via decoupled File-System polling (`tmpfs`) to prevent blocking the 10Hz physical execution loops. ROS 2 nodes NEVER make blocking HTTP calls. **CRITICAL: The directory `shared_state/` must exist, otherwise `r2k_evaluator.py` silently crashes with a FileNotFoundError.**
> 4. **Race Conditions:** Avoided strictly via POSIX atomic renames (`os.replace`). Standard file-locking (`fcntl`) is prohibited.

## 1. Unified System Topology (V5)

Dieses Diagramm definiert die strikten Isolationsgrenzen zwischen der hochfrequenten ROS 2 Middleware, dem RAM-gestützten Dateisystem und der asynchronen kognitiven Engine.

~~~mermaid
graph TD
    subgraph S_ROS ["ROS 2 Middleware (10Hz)"]
        G["Gazebo Engine"]
        T["tracker_node.py"]
        Red["rule_evaluator_red.py"]
        B["ollama_sandbox_bridge.py PID Threads"]
        Agg["state_aggregator.py"]
    end

    subgraph S_FS ["RAM-Backed tmpfs (shared_state/)"]
        WS[("Aggregated_Worldstate.json")]
        CS[("current_strategy.json")]
    end

    subgraph S_AI ["Cognitive Layer (Asynchronous)"]
        E["r2k_evaluator.py"]
        LLM{"Qwen2.5-Coder:3B (Port 11434)"}
    end

    G -->|model_states| T
    G -->|model_states| Red
    T -->|Raw Coords| Agg
    Agg -->|Atomic os.replace| WS
    WS -->|Async Poll| E
    E -->|Blocking POST| LLM
    LLM -->|Flat Strategy Schema| E
    E -->|Atomic Write| CS
    CS -->|Polls 10Hz| B
    B -->|cmd_vel & RPC Payloads| G
    Red -->|cmd_vel & Phantom Kick| G
~~~

## 2. Core Constraints & Data Flow

### A. Tri-Agent Topology
* **Team Red (Algorithmic):** Deterministische Python-Zustandsautomaten (`rule_evaluator_red.py`), die die räumliche Distanz verzögerungsfrei auswerten. Diese umgehen das LLM vollständig und nutzen algorithmisches Staging sowie den Phantom Kick (`/gazebo/set_entity_state`).
* **Team Blue (Cognitive):** Gesteuert durch `r2k_evaluator.py`, welches räumliches Denken über das lokale `qwen2.5-coder:3b` Modell ausführt und die flache JSON-Ausgabe schreibt. Ollama muss hierbei zwingend im User-Space laufen.
* **Perception Rules:** `tracker_node.py` abonniert `/gazebo/model_states` und glättet 3D-Quaternionen in 2D-Matrizen. Der **`state_aggregator.py`** bündelt diese Daten anschließend mit Score- und Match-State und schreibt den Unified Aggregated Worldstate auf die Festplatte.

### B. Decoupled Multiplexing & tmpfs (File I/O)
* **Das Problem:** Maßgeschneiderte ROS 2 Nachrichtentypen erzwingen eine starre Kompilierung und binden die LLM-Skripte in den ROS 2 Abhängigkeitsbaum ein.
* **Die Lösung:** Das System tauscht Zustände über zustandslose JSON-Dateien im Ordner `shared_state/` aus.
* **Hardware-Sicherheit:** Diese Dateien werden auf einer RAM-gestützten `tmpfs`-Partition gespeichert. Dies eliminiert physische Festplattenlatenzen und den Verschleiß von SSDs während der 10Hz-Schreibzyklen.

### C. Timing Disparities & Dynamic Thread Spawning
* **Das Problem:** Firmware-Sicherheits-Watchdogs (wie beim ESP32 oder K1) benötigen alle ~200ms (10Hz) neue `/cmd_vel` oder RPC Motor-Pulse, andernfalls wird ein Nothalt ausgelöst. Die LLM-Inferenz blockiert die Ausführung jedoch für 500-2000ms.
* **Die Lösung (Keine OOP HALs):** Die `ollama_sandbox_bridge.py` parst dynamisch die JSON-Zielkoordinaten und verwaltet die Proportional-Integral-Derivative (PID) Motorsteuerung über losgelöste Python-Threads (`def task`).
* **Preemption:** Wenn ein neues Ziel empfangen wird, setzt die Bridge ein `threading.Event()`-Flag, um den alten Thread zu beenden (wobei ein Stopp-Vektor mit Nullgeschwindigkeit gesendet wird), und startet eine neue Closure-Funktion für das neue Ziel. Der ROS 2 Executor wird durch die LLM-Latenz niemals blockiert.

### D. Race Condition Mitigation (Atomic Swaps)
* **Das Problem:** Asynchrones Lesen durch den Evaluator während des 10Hz-Schreibzyklus des Aggregators führt zu abgeschnittenen JSON-Strings und fatalen `JSONDecodeError`-Abstürzen.
* **Die Lösung:** `state_aggregator.py` schreibt seine Daten in eine `Worldstate.json.tmp` Datei. Sobald der Datei-Handle geschlossen ist, führt er einen POSIX-kompatiblen `rename` (`os.replace`) durch, um die primäre JSON-Datei zu überschreiben. Unter Linux ist dies ein atomarer Swap des Verzeichniseintrags, wodurch Leser immer nur eine vollständig valide Datei sehen.

## 3. Critical Code Interfaces

**Atomic File Swap (`state_aggregator.py` / `tracker_node.py`):**
~~~python
# snippet representing atomic writes in the perception layer
import json, os

temp_path = "shared_state/Worldstate.json.tmp"
final_path = "shared_state/Worldstate.json"

try:
    with open(temp_path, 'w') as f:
        json.dump(aggregated_state, f)
    os.replace(temp_path, final_path)
except Exception as e:
    self.get_logger().error(f"Write failure: {e}")
~~~

**Dynamic Thread Spawning (`ai_tactics/ollama_sandbox_bridge.py`):**
~~~python
# snippet representing execution preemption without OOP HALs
import threading, time

if bot_name in self.events: 
    self.events[bot_name].set() 
    
self.events[bot_name] = threading.Event()

def task(stop_event):
    while not stop_event.is_set():
        # Execute PID loop and publish Twist/RPC
        time.sleep(0.1)
        
threading.Thread(target=task, args=(self.events[bot_name],), daemon=True).start()
~~~

**Blocking LLM HTTP Request (`ai_tactics/r2k_evaluator.py`):**
~~~python
# snippet representing the V5 Qwen2.5-Coder REST request
import requests, json

response = requests.post("http://127.0.0.1:11434/api/generate", json={
    "model": "qwen2.5-coder:3b",
    "prompt": json.dumps(world_data["worldstate"]),
    "stream": False,
    "format": "json"
})
~~~
