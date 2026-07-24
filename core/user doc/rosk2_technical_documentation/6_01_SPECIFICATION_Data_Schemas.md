---
id: 6_01
title: "Data Schemas & Relay Profiles"
type: SPECIFICATION
tags: [json, schemas, relay, worldstate, strategy, rpc, bot1, v5, v6, v6.1, v6.2, qwen, match-state, tactical-score, tactical-reward, trace, eval-results]
last_modified: 2026-07-15
version: v6.2
---
# 6.01 SPECIFICATION: Data Schemas & Relay Profiles

> [!info] Human Summary
> Dieses Dokument spezifiziert die exakten JSON-Datenschemata für die gesamte ROS2K-Umgebung. Es deckt die Zustandssynchronisation (Worldstate), die KI-Ausgabe (Strategies), die Low-Level-Roboterebene (RPC) sowie die Laufzeit-Relay-Profile ab.

> [!abstract] LLM Context Anchor
> Alle Dateischnittstellen des Systems sind strikt typisiert und zustandslos. Der Evaluator und die Bridge (ohne OOP HALs) validieren eingehende Daten gegen diese Schemata, um Parsing-Ausnahmen während des asynchronen 10Hz-Betriebs zu verhindern.
> **[NEW in v5]:** Das `Worldstate.json` Schema wird nun aggregiert (inklusive Score/Match-State). Das KI-Modell (`qwen2.5-coder:3b`) muss zwingend ein absolut flaches Ziel-Schema liefern. Der RPC API-Code 2000 ist nun essenzieller Bestandteil des 0.2s Asynchronous Watchdogs für den Kinematic Freeze.
> **[NEW in v6]:** Drei neue/erweiterte Topics: `/match_state` v6 (fouls, ball-out, set-pieces), `/tactical_score` v6 (momentum), `/tactical_reward` (1Hz reward, -10..+10). Siehe §7 unten.
> **[NEW in v6.1]:** Trace-Dateien (`llm_trace`, `world_trace` JSONL) und `eval_results.json`. Siehe §8 unten.

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

---

## 7. V6+ Topic Schemas (NEW in v6 / v6.1)

### 7.1 `/match_state` V6 Schema (referee_node.py)

```json
{
  "blue": 0,
  "red": 0,
  "status": "playing",
  "ball_out_event": null,
  "restart_team": null,
  "restart_pos": null,
  "last_toucher": null,
  "foul": null
}
```

Gültige Status: `"playing"`, `"goal"`, `"ball_out"`, `"goal_kick"`, `"corner_kick_in"`,
`"foul_penalty"`. Siehe [[2_04_ARCHITECTURE_Engine_Nodes]] und `core/docs/referee_rulebook.md`.

Foul-Objekt (wenn `foul` nicht null):
```json
{
  "type": "pushing",
  "offender": "blue_2",
  "victim": "red_1",
  "position": {"x": -1.5, "y": 0.3},
  "penalty": "sideline_warp"
}
```

Penalty-Werte: `"sideline_warp"` (Pushing), `"own_half_warp"` (Blocking),
`"warp_2m_freeze_5s"` (Ball-Out Sideline).

### 7.2 `/tactical_score` V6 Schema (score_node.py)

```json
{
  "current_numerical_score": -5.24,
  "average_numerical_score": -0.82,
  "momentum_30s": -2.1,
  "momentum_trend": "collapsing",
  "fact_label": "Red attacking",
  "ball_possession_fact": "Red Team"
}
```

Trends: `"ascending"`, `"improving"`, `"stable"`, `"declining"`, `"collapsing"`.

### 7.3 `/tactical_reward` Schema (reward_node.py — NEW in V6)

Published at 1Hz. Two source types:

Decision reward:
```json
{
  "timestamp": 1782986654.74,
  "source": "decision",
  "action_type": "Move",
  "target_x": 2.3, "target_y": -1.1,
  "score_before": -6.5, "score_after": -4.2,
  "reward": 2.3,
  "classification": "positive",
  "bot_id": "blue_1"
}
```

Foul penalty:
```json
{
  "timestamp": 1782986655.10,
  "source": "foul",
  "action_type": "pushing",
  "target_x": null, "target_y": null,
  "score_before": -3.2, "score_after": null,
  "reward": -1.0,
  "classification": "negative",
  "bot_id": "blue_2"
}
```

Klassifikation: `> +1.0` positive, `-1.0..+1.0` neutral, `< -1.0` negative.

### 7.4 Worldstate.json V6.1 Schema (state_aggregator.py)

Das V5-Schema wurde erweitert. `match_state` ist nun ein Objekt (kein String mehr), und
`tactical_score` + `tactical_reward` wurden hinzugefügt:

```json
{
  "timestamp_ms": 1779222655448,
  "entities": {
    "soccer_ball": {"x": 1.2, "y": 0.0},
    "blue_1": {"x": -0.5, "y": 0.5, "yaw": 1.1},
    "red_1": {"x": 2.5, "y": -1.0, "yaw": -3.14}
  },
  "match_state": {"blue": 0, "red": 0, "status": "playing", "restart_team": null, "foul": null},
  "tactical_score": {"current_numerical_score": -0.5, "momentum_30s": 0.3, "momentum_trend": "stable"},
  "tactical_reward": {"reward": 2.3, "classification": "positive", "bot_id": "blue_1"}
}
```

> [!warning] LLM sees stripped version
> By default `r2k_evaluator.py:88` strips the worldstate to entity X/Y coordinates only.
> `match_state`, `tactical_score`, and `tactical_reward` are NOT sent to the LLM unless
> `R2K_INCLUDE_MATCH_STATE=1` is set. See [[7_02_ARCHITECTURE_World_Model_Components]].

---

## 8. V6.1 Trace & Eval Schemas (NEW in v6.1)

### 8.1 `llm_trace_<run_id>.jsonl` (r2k_evaluator.py)

Eine JSON-Zeile pro LLM-Call. In `logs/` (gitignored).

```json
{
  "t": 1782986654.74,
  "world_snapshot": {"blue_1": {"x": -1.5, "y": 0.3}, "soccer_ball": {"x": 0.0, "y": 0.1}},
  "sys_prompt_hash": "a3f1b2c8d9e01234",
  "raw_response": "{\"assignments\":{...}}",
  "parse_code": 0,
  "latency_ms": 827,
  "model": "qwen2.5-coder:3b",
  "num_predict": 150,
  "explain": false
}
```

`parse_code`: 0 = clean JSON, 1 = trailing comma fix, 2 = assignments extraction, 3 = parse failure.

### 8.2 `world_trace_<run_id>.jsonl` (state_aggregator.py)

Eine JSON-Zeile pro 10Hz World-State-Write. In `logs/` (gitignored).

```json
{
  "t": 1782986654.74,
  "entities": {"blue_1": {"x": -1.5, "y": 0.3}, "red_1": {"x": 2.1, "y": -0.2}, "soccer_ball": {"x": 0.0, "y": 0.1}},
  "match_state": {"blue": 0, "red": 0, "status": "playing", "restart_team": null, "foul": null},
  "tactical_score": {"current_numerical_score": -0.5, "average_numerical_score": -0.2, "momentum_30s": 0.3, "momentum_trend": "stable"}
}
```

### 8.3 `eval_results.json` (batch_evaluator.py)

Eine Datei pro Batch-Lauf. In `results/`. (Hinweis: KPI-Collection ist aktuell kaputt —
v6.2 Phase 2b wird es fixen.)

```json
{
  "meta": {
    "version": "v6.2",
    "timestamp": "20260715_143022",
    "duration_per_run": 120,
    "runs_per_config": 3,
    "models": ["qwen2.5-coder:3b"],
    "strategies": ["strat_default"],
    "scenarios": ["3vs3_attack_center"]
  },
  "results": {
    "3vs3_attack_center": {
      "strat_default": {
        "qwen2.5-coder:3b": {
          "runs": [{"run_id": "...", "world_kpis": {...}, "llm_kpis": {...}}]
        }
      }
    }
  }
}
```

### 8.4 KPI JSON (tools/analyze_trace.py)

Eine Datei pro Run. In `results/kpis_<run_id>.json`. Siehe [[7_03_CHEATPAGE_Tools_and_Utils]]
für die 14 KPI-Definitionen.
