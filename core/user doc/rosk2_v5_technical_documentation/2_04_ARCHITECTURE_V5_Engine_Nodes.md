---
id: 2_04
title: "V5 Engine Nodes: Referee, Score & Aggregator"
type: ARCHITECTURE
tags: [v4, v5, referee, score, state-aggregator, pipeline, automated-training]
last_modified: 2026-05-31
version: v5_release
---
# 2.04 ARCHITECTURE: V5 Engine Nodes (Referee, Score, Aggregator)

> [!info] Human Summary
> Dieses Dokument beschreibt die neuen ROS 2 Echtzeit-Knoten der V4-Architektur. Diese Knoten automatisieren den Spielablauf (Regelüberwachung, Punktestand, Resets), sodass das System ohne menschliches Eingreifen Endlos-Szenarien für LLM-Tests oder Reinforcement Learning (RL) durchführen kann.

> [!abstract] LLM Context Anchor
> Das System verlässt sich für den Spielablauf nicht mehr auf manuelle Kicker-Skripte. Der `referee_node.py` überwacht Spielfeldgrenzen, der `score_node.py` registriert Tore, und der `state_aggregator.py` bündelt diese Metadaten mit dem Gazebo-Worldstate zu einer einheitlichen JSON-Sicht für den LLM-Evaluator.
> **[NEW in v5]:** Die V5-Architektur konsolidiert diese Pipeline vollständig. Die Ausgabe erfolgt streng über einen atomaren POSIX-Rename (`Worldstate.json.tmp` -> `Worldstate.json`). 

## 1. System Topology of the Engine Pipeline

**[DEPRECATED in v4] Original V4 Engine Topology:**
Dieses Diagramm veranschaulicht, wie die drei neuen Knoten miteinander interagieren.

~~~mermaid
graph TD
    subgraph Physics ["Gazebo Environment"]
        Gazebo["/gazebo/model_states"]
        ResetSrv["/reset_scenario (ROS Service)"]
    end

    subgraph V4 Engine Nodes ["Realtime Rule Pipeline"]
        Tracker["tracker_node.py (2D Math)"]
        Referee["referee_node.py (Bounds Check)"]
        Score["score_node.py (Goal Check)"]
        Aggregator["state_aggregator.py (Merger)"]
    end

    subgraph Output ["Perception Layer"]
        OutJSON["Worldstate.json"]
    end

    Gazebo --> Tracker
    Tracker --> Referee
    Tracker --> Score
    
    Referee -->|Calls| ResetSrv
    Referee -->|Status Out of Bounds| Aggregator
    Score -->|Score Update| Aggregator
    Tracker -->|Coordinates| Aggregator

    Aggregator -->|Write| OutJSON
~~~

**[NEW in v5] Validated V5 Engine Topology:**
Die Architektur bleibt bestehen, implementiert aber den strengen, transaktionalen Schreibprozess über die temporäre Datei, um Race Conditions mit dem LLM-Reader zu verhindern.

~~~mermaid
graph TD
    subgraph Physics ["Gazebo Environment"]
        Gazebo["/gazebo/model_states"]
        ResetSrv["/reset_scenario (ROS Service)"]
    end

    subgraph V5 Engine Nodes ["Realtime Rule Pipeline"]
        Tracker["tracker_node.py (2D Math)"]
        Referee["referee_node.py (Bounds Check)"]
        Score["score_node.py (Goal Check)"]
        Aggregator["state_aggregator.py (Merger)"]
    end

    subgraph Output ["Perception Layer"]
        TmpJSON["Worldstate.json.tmp"]
        OutJSON["Worldstate.json"]
    end

    Gazebo --> Tracker
    Tracker --> Referee
    Tracker --> Score
    
    Referee -->|Calls| ResetSrv
    Referee -->|Status Out of Bounds| Aggregator
    Score -->|Score Update| Aggregator
    Tracker -->|Coordinates| Aggregator

    Aggregator -->|POSIX os.replace| TmpJSON
    TmpJSON -->|Atomic Swap| OutJSON
~~~

## 2. The Referee Node (referee_node.py)
Der Referee-Knoten fungiert als automatischer Schiedsrichter.

* Out-of-Bounds Detection: Verlässt der Ball das definierte Spielfeld, stoppt der Referee das Match.
* Reset Mechanism: Ruft den ROS 2 Service `/reset_scenario` auf, um alle Modelle an die Startkoordinaten zurückzusetzen.
* Match States: Publiziert den Spielzustand (PLAYING, PAUSED, RESETTING).

## 3. The Score Node (score_node.py)
Dieser Knoten ist exklusiv für die Torlinien-Überwachung und die Punktestände verantwortlich.

* Goal Detection: Überwacht X/Y-Koordinaten des Balls auf Torraum-Durchbruch.
* State Persistence: Punktestand wird über das Topic `/v4/match_score` kommuniziert.
* **[UPDATE in v5]:** Der ermittelte Punktestand wird zur Bündelung nun nativ an `state_aggregator.py` weitergegeben.

## 4. The State Aggregator (state_aggregator.py)
**[DEPRECATED in v4]:** Bündelt Koordinaten, Punktestand und Spielstatus in eine einzige, flache JSON-Datei (`Worldstate.json`) im tmpfs, um dem LLM ein atomares Gesamtbild zu liefern.

**[UPDATE in v5]:** Bündelt Koordinaten, Punktestand und Spielstatus nativ in die zentrale `Worldstate.json` (via atomarem Rename von `Worldstate.json.tmp`) im `shared_state/` tmpfs. Fehlt der Ordner `shared_state/` beim Systemstart, führt dies unwiderruflich zu einem lautlosen `FileNotFoundError` in den Evaluator-Daemons.

### Example Output: Worldstate.json
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
    "blue_1": {"x": -0.5, "y": 0.5, "yaw": 1.1}
  }
}
~~~

## 5. Known Issues & Limitations
* Service Deadlocks: Bei Gazebo-Überlast kann der Service-Call des Referee Nodes in einen Timeout laufen.
* Ghost Goals: Bei sehr hohen Ballgeschwindigkeiten (>10 m/s) können zwischen zwei 10Hz-Ticks Kollisionen mit der Torlinie übersprungen werden.
