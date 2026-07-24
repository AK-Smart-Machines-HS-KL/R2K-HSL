---
id: 4_06
title: "Booster K1 Integration Specification"
type: SPECIFICATION
tags: [json, locoapi, payloads, string-topic, namespace, bot1, active-relay, v5]
last_modified: 2026-05-31
version: v5_release
---
# Booster K1 Integration Specification

> [!info] Human Summary
> Dieses Dokument definiert die exakten String-Payloads, die zur Steuerung der proprietären K1-API über ROS 2 erforderlich sind. Ab Generation V4 sind eine strikte Namespace-Trennung (/bot1/) und dedizierte JSON-Kommandos vorgeschrieben.

> [!abstract] LLM Context Anchor
> Herkömmliche geometry_msgs/Twist Befehle sind für die K1-Hardware wirkungslos. Die Ansteuerung erfordert zwingend serialisierte JSON-Strings auf dem Topic /bot1/LocoApiTopicReq. Dabei regelt API-Code 2000 den Not-Halt und Code 2001 die aktive Fortbewegung.
> **[NEW in v5]:** In der V5-Architektur werden diese Payloads nicht mehr durch OOP Hardware Abstraction Layers (HALs) versteckt. Die zentrale `ollama_sandbox_bridge.py` serialisiert die JSON-Strings direkt, sofern die `active_relay.json` für den aktuellen Namespace (z.B. `/bot1/`) ein proprietäres K1-Profil vorschreibt.

## 1. Namespace Routing Isolation (V4 & V5)

Um Datenkollisionen im ROS 2 DDS-Netzwerk zu vermeiden, kommuniziert die K1-Hardware nicht mehr auf globalen Root-Topics. Sie agiert nun exklusiv in einem eigenen Hardware-Namespace.

* Veraltete API-Spezifikation [DEPRECATED]: /LocoApiTopicReq und /odometer_state
* Neue API-Spezifikation [PRODUCTION]: /bot1/LocoApiTopicReq und /bot1/odometer_state

Die `ollama_sandbox_bridge.py` adressiert gezielt den `/bot1/` Namespace. Dies behebt stille Verbindungsfehler aus asynchronen Simulations- und Hardware-Topics.

## 2. System Topology of K1 Payload Serialization

**[DEPRECATED in v4] Original V4 Serialization Topology:**
Dieses Diagramm illustriert den Datenfluss zur Ansteuerung der K1-API mittels ROS 2 String-Nachrichten im isolierten Namespace.

~~~mermaid
graph TD
    subgraph Bridge ["Python Logic"]
        Dict["Python Dictionary"]
        Ser["json.dumps String"]
    end

    subgraph Topic ["ROS 2 String Bus"]
        Req["/bot1/LocoApiTopicReq"]
    end

    subgraph Hardware ["K1 SDK"]
        Deser["JSON Parse"]
        Exe["Motor API"]
    end

    Dict --> Ser
    Ser -->|String Message| Req
    Req --> Deser
    Deser --> Exe

    style Req fill:#f9f,stroke:#333
    style Ser fill:#dfd,stroke:#333
~~~

**[NEW in v5] Validated V5 Serialization Topology:**
Das Routing wird nun durch das dynamische Relay-Profil bestimmt. Der Watchdog nutzt Code 2000 für den Kinematic Freeze.

~~~mermaid
graph TD
    subgraph Configurations ["JSON Profiles"]
        Relay["active_relay.json"]
    end

    subgraph Bridge ["ollama_sandbox_bridge.py"]
        Parse["Evaluate K1 Profile"]
        Dict["Construct Payload (Code 2001)"]
        Ser["json.dumps String"]
    end

    subgraph Teardown ["launch_r2k.sh Watchdog"]
        Panic["Kinematic Freeze (Code 2000)"]
    end

    subgraph Topic ["ROS 2 String Bus"]
        Req["/bot1/LocoApiTopicReq"]
    end

    subgraph Hardware ["K1 SDK"]
        Exe["Motor API"]
    end

    Relay --> Parse
    Parse --> Dict
    Dict --> Ser
    Ser -->|String Message| Req
    Panic -->|Overrides active motion| Req
    Req --> Exe

    style Req fill:#f9f,stroke:#333
    style Ser fill:#dfd,stroke:#333
    style Panic fill:#fcc,stroke:#c00
~~~

## 3. Architectural Logic & Data Flow

Da der Booster K1 primitive ROS 2 Vektoren nicht nativ verarbeitet, erwartet seine LocoAPI stattdessen JSON-Payloads innerhalb eines `std_msgs/String` Topics.

**[DEPRECATED in v4]:** Die Bridge-Node konstruiert hierfür ein Python-Dictionary mit den relevanten Parametern. Dieses wird als Text serialisiert und auf `/bot1/LocoApiTopicReq` veröffentlicht. So wird die komplexe Bipeden-Steuerung zuverlässig über ein simples Text-Topic im FastDDS-Netzwerk abgewickelt.

**[UPDATE in v5]:** Die `ollama_sandbox_bridge.py` erzeugt diese Dictionaries nun ohne zwischengeschaltete Klassen ("no OOP HALs"). Sobald das Relay-Profil den Bot als `booster_k1` flaggt, übersetzt die zentrale Funktion die LLM-Vektoren in den Code 2001 (Active Locomotion). Beim System-Teardown (0.2s Asynchronous Watchdog) schießt das Bash-Skript explizit einen Code 2000 Payload in das Topic, um den Kinematic Freeze auszulösen und den Bipeden sicher abzusetzen, bevor der DDS-Daemon stirbt.

## 4. Unified JSON Payload Specifications (V4/V5)

Die Bridge übersetzt die vom LLM berechneten Vektoren unmittelbar in diese proprietären JSON-Formate.

### Code 2001: Dynamische Geschwindigkeitssteuerung
Wird genutzt, um die Vektoren (vx, vy, vyaw) aktiv zu steuern.

~~~json
{
  "api_id": 2001,
  "timestamp_ms": 1779222651443,
  "payload": {
    "linear_velocity_x": 0.25,
    "angular_velocity_z": -0.12,
    "duration_ms": 500
  }
}
~~~

### Code 2000: Not-Halt und Bereitschaft (Kinematic Freeze)
Wird für den harten Not-Halt oder den Prep-Mode (mode: 1) während Teardowns und Pausen verwendet.

~~~json
{
  "api_id": 2000,
  "timestamp_ms": 1779222655448,
  "payload": {
    "clear_buffer": true,
    "lock_drive": true
  }
}
~~~

## 5. Known Issues & Limitations

* Deformierte JSON-Strings erzeugen auf Hardware-Ebene keinen ROS 2 Fehler; der Roboter ignoriert den Befehl schlichtweg.
* Die API verfügt über kein Rate-Limiting. Eine Überflutung des Topics `/bot1/LocoApiTopicReq` kann den Locomotion-Rechner zum Absturz bringen.

## 6. Glossary

* LocoAPI: Die interne Fortbewegungsschnittstelle des Booster K1 SDK.
* Serialization: Die Umwandlung von Datenstrukturen in speicher- oder übertragbare Formate (z.B. JSON-Strings).
* **[NEW in v5] Kinematic Freeze (K1):** Das explizite Feuern von API-Code 2000 durch den V5-Watchdog, um den Bipeden vor dem Netzwerk-Kollaps zu sperren.
