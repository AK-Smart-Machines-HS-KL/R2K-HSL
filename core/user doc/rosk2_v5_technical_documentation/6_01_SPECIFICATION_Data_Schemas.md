---
id: 6_01
title: "Data Schemas & Relay Profiles (V5)"
type: SPECIFICATION
tags: [json, schemas, relay, worldstate, strategy, rpc, bot1, v5, qwen]
last_modified: 2026-05-31
version: v5_release
---
# 6.01 SPECIFICATION: Data Schemas & Relay Profiles

> [!info] Human Summary
> Dieses Dokument spezifiziert die exakten JSON-Datenschemata für die gesamte ROS2K-Umgebung. Es deckt die Zustandssynchronisation (Worldstate), die KI-Ausgabe (Strategies), die Low-Level-Roboterebene (RPC) sowie die Laufzeit-Relay-Profile ab.

> [!abstract] LLM Context Anchor
> Alle Dateischnittstellen des Systems sind strikt typisiert und zustandslos. Der Evaluator und die Bridge (ohne OOP HALs) validieren eingehende Daten gegen diese Schemata, um Parsing-Ausnahmen während des asynchronen 10Hz-Betriebs zu verhindern.
> **[NEW in v5]:** Das `Worldstate.json` Schema wird nun aggregiert (inklusive Score/Match-State). Das KI-Modell (`qwen2.5-coder:3b`) muss zwingend ein absolut flaches Ziel-Schema liefern. Der RPC API-Code 2000 ist nun essenzieller Bestandteil des 0.2s Asynchronous Watchdogs für den Kinematic Freeze.

## 1. System Topology of Data Synchronization

**[NEW in v5] Validated V5 Topology:**
Das Update reflektiert den neuen Aggregator und die Beseitigung der OOP HALs in der Bridge.

~~~mermaid
graph TD
    subgraph Perception ["V5 Perception Layer (10Hz)"]
        Agg["state_aggregator.py"] -->|Atomic Swap| WS["1. Aggregated Worldstate Schema"]
    end

    subgraph Cognition ["Cognitive Layer (Asynchronous)"]
        WS -->|Polled by| Eval["r2k_evaluator.py"]
        Eval -->|HTTP POST| LLM["Ollama / Qwen2.5-Coder"]
        LLM -->|Writes current_strategy.json| ST["2. Flat Strategy Schema"]
    end

    subgraph Execution ["V5 Execution Layer (No OOP HAL)"]
        CLI["--relay Flags"] -->|Pre-Flight Compiler| Active["3. active_relay.json"]
        ST -->|Parsed by| Bridge["ollama_sandbox_bridge.py"]
        Active -->|Evaluated by| Bridge
        Bridge -->|Direct RPC Serialization| K1["4. Booster K1 RPC Schema"]
    end
~~~

---

## 2. Core Operational Schemas

### 2.1 Worldstate.json Schema
Dieses Format wird exklusiv von `state_aggregator.py` erzeugt und bündelt die Spiel-Logik mit den Sensordaten. Beachte die flache Hierarchie von `worldstate`, um dem Qwen2.5-Coder das Parsen zu erleichtern.
~~~json
{
  "timestamp_ms": 1779222655448,
  "match_state": "PLAYING",
  "score": {
    "blue_team": 2,
    "red_team": 0
  },
  "worldstate": {
    "ball": {"x": 1.2, "y": 0.0},
    "blue_1": {"x": -0.5, "y": 0.5, "yaw": 1.1},
    "red_1": {"x": 2.5, "y": -1.0, "yaw": -3.14}
  }
}
~~~

### 2.2 current_strategy.json Schema
Um Parsing Paralysis in `ollama_sandbox_bridge.py` abzuwehren, erzwingt der dynamische System-Prompt strikt flache Entitäts-Keys und feste `action` Strings (z.B. "Move" oder "Kick").
~~~json
{
  "assignments": {
    "blue_1": {"action": "Move", "x": 1.5, "y": -0.2},
    "blue_2": {"action": "Kick"}
  }
}
~~~

---

## 3. V5 Hardware Relay Profile Schemas (active_relay.json)

Die CLI-Werte des `--relay` Flags steuern dynamisch das Hardware-Abstraktions-Mapping beim Systemstart. Diese Profile werden durch `setup_r2k.py` kompilativ als einzige Zieldatei `active_relay.json` bereitgestellt und von der zentralen Python-Bridge gelesen.

### 3.1 Profil: only_sim_bots
Routet alle Strategievektoren an die virtuellen Gazebo-Modell-Namespaces.
~~~json
{
  "profile_name": "only_sim_bots",
  "description": "Routes all LLM target vectors to virtual Gazebo agents.",
  "agents": {
    "blue_1": {
      "hardware_type": "sim",
      "cmd_vel_topic": "/blue_1/cmd_vel"
    }
  }
}
~~~

### 3.2 Profil: hardware_mirror
Spiegelt Befehle an die reale Edge-Hardware (Yahboom ESP32 und Booster K1 Bipede).
~~~json
{
  "profile_name": "hardware_mirror",
  "description": "Routes LLM targets to physical hardware in the lab.",
  "agents": {
    "blue_1": {
      "hardware_type": "yahboom",
      "cmd_vel_topic": "/bot1/cmd_vel",
      "multicast_ip": "10.42.0.1"
    },
    "blue_2": {
      "hardware_type": "k1",
      "cmd_vel_topic": "/bot2/LocoApiTopicReq",
      "api_version": "v5"
    }
  }
}
~~~

---

## 4. Low-Level Hardware RPC Payload Schemas (K1 LocoAPI)

Wenn ein Agent als `hardware_type: "k1"` deklariert ist, serialisiert die Bridge die Zielkoordinaten in die folgenden proprietären JSON-String-Payloads.

### Locomotion Command Payload (API Code 2001)
Wird fortlaufend für aktive Fahrbefehle generiert.
~~~json
{
  "api_id": 2001,
  "timestamp_ms": 1779222655448,
  "payload": {
    "linear_velocity_x": 0.25,
    "angular_velocity_z": -0.12,
    "duration_ms": 500
  }
}
~~~

### Standby & Failsafe Payload (API Code 2000)
Wird vom 0.2s Asynchronous Watchdog in `launch_r2k.sh` als Kinematic Freeze an die Hardware gefeuert, noch bevor der ROS 2 Daemon beendet wird.
~~~json
{
  "api_id": 2000,
  "timestamp_ms": 1779222659000,
  "payload": {
    "clear_buffer": true,
    "lock_drive": true
  }
}
~~~

---

## 5. Required Key-Value Pairs Reference

* **hardware_type:** Streng limitiert auf `sim`, `yahboom` oder `k1`. Andere Strings blockieren den Start der Bridge.
* **cmd_vel_topic:** Der absolute ROS 2 Topic-Pfad (Muss zwingend mit einem führenden `/` beginnen).
* **timestamp_ms:** UNIX-Zeitstempel in Millisekunden zur Überwachung von Paket-Latenzen auf Hardware-Ebene.

## 6. Known Issues & Limitations
* **KeyError Crashes:** Wenn ein Szenario gestartet wird, das mehr Agenten deklariert als im aktiven `active_relay.json` Profil definiert sind, stürzt die Bridge mit einem fatalen `KeyError` ab.
* **Silent Dropping:** Die JSON-Schnittstelle zur Hardware validiert keine physikalische Erreichbarkeit. Ist ein Roboter offline, werden die serialisierten Payloads stumm ins DDS-Netzwerk auf Domain 0 verworfen.
