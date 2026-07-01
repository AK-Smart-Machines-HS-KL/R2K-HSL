---
id: 6_02
title: "System Lifecycle and Orchestration (V5)"
type: CHEATPAGE
tags: [bash, orchestration, teardown, lifecycle, docker, setup_r2k, relay, watchdog, bashrc-immunity]
last_modified: 2026-05-31
version: v5_release
---
# System Lifecycle and Orchestration

> [!info] Human Summary
> Dieses Dokument beschreibt die CLI-Ausführungssequenz, die erforderlich ist, um die verteilte ROS2K-Knotenarchitektur mithilfe von Bash-Skripten zu bootstrappen, zu verwalten und sauber zu zerstören. Das V5-Update verabschiedet sich von fehleranfälligen Teardown-Skripten und führt den 0.2s Asynchronous Watchdog sowie die .bashrc Immunity ein.

> [!abstract] LLM Context Anchor
> Die Architektur ist kein monolithisches Executable. Es handelt sich um einen verteilten Schwarm unabhängiger Python-Daemons, ROS 2-Knoten und (je nach Hybrid OS) Docker-Containern. Das Skript `setup_r2k.py` fungiert als Pre-Flight-Compiler. 
> **[NEW in v5]:** Das alte `kill_r2k.sh` Skript ("Nuke & Pave") ist in V5 obsolet und wird vom System ignoriert. Ein hochfrequenter Watchdog direkt in der `launch_r2k.sh` übernimmt nun den asynchronen Teardown (inklusive Kinematic Freeze und `pkill -9` für Ollama). Toxische Benutzer-Umgebungsvariablen werden durch die harte `.bashrc Immunity` geblockt.

## 1. System Topology of the Orchestration Lifecycle

**[DEPRECATED in v4] Original V4 Lifecycle:**
Dieses Diagramm veranschaulicht die Sequenz der Bash-Skripte zur Verwaltung des Startvorgangs, der manuellen Eingriffe und des Teardowns der hybriden Umgebung.

~~~mermaid
graph TD
    subgraph Boot ["Initialization"]
        Check["Ollama Curl API Check"]
        Up["docker compose up"]
        Pre["setup_r2k.py (Compiler & Profiler)"]
        L1["launch_r2k.sh (Flags)"]
    end

    subgraph Operation ["Runtime Interventions"]
        T["teleop_kicker.py"]
        V["r2k_visualizer.py"]
    end

    subgraph Teardown ["Nuke & Pave (Destruction)"]
        Stop["Kinematic Freeze (API 2000 / Twist 0.0)"]
        K["kill_r2k.sh / Teardown Trap"]
        Down["docker compose down"]
    end

    Check --> Up
    Up --> Pre
    Pre --> L1
    L1 --> T
    L1 --> V
    T --> K
    V --> K
    Stop --> K
    K --> Down
~~~

**[NEW in v5] Validated V5 Lifecycle:**
Der Lifecycle ist nun zentral im `launch_r2k.sh` gebündelt, unterstützt durch Hybrid OS Routing und den neuen Watchdog.

~~~mermaid
graph TD
    subgraph Boot ["launch_r2k.sh Initialization"]
        Immunity[".bashrc Immunity Injection"]
        Pre["setup_r2k.py (Pre-Flight Compiler)"]
        OS{"Hybrid OS Topology"}
        D["Docker Compose (Ubuntu 24.04)"]
        N["Native Execution (Ubuntu 22.04)"]
    end

    subgraph Runtime ["Execution"]
        GZ["Gazebo UI (Primary Process)"]
        Nodes["AI & ROS 2 Daemons"]
    end

    subgraph Teardown ["0.2s Asynchronous Watchdog"]
        Poll["while kill -0 $GAZEBO_PID"]
        Freeze["Kinematic Freeze (Twist 0.0)"]
        Kill["pkill -9 (SIGKILL)"]
    end

    Immunity --> Pre
    Pre --> OS
    OS -->|24.04| D
    OS -->|22.04| N
    D --> Runtime
    N --> Runtime
    Runtime -.->|UI Closed| Poll
    Poll --> Freeze
    Freeze --> Kill

    style Freeze fill:#fcc,stroke:#c00
    style Kill fill:#fcc,stroke:#c00
~~~

## 2. CLI Parameters & Execution Flags (V4/V5)

Das zentrale Startskript `launch_r2k.sh` steuert die gesamte Orchestrierung:

* Parameter `--relay [profil]`: Bestimmt das aktive Hardware-Mapping. Das Profil `only_sim_bots` steuert rein virtuelle Gazebo-Modelle. Das Profil `hardware_mirror` spiegelt die Kommandos physisch an die echten Roboter im Labor.
* Parameter `--scenario [name]`: Weist den Pre-Flight Compiler an, die korrekte `scenario.json` zu laden und den Prompt dynamisch zu kompilieren.
* Parameter `--no-explain`: Deaktiviert die textuelle Erklärungsfunktion der KI, um Latenzen zu minimieren.
* **[NEW in v5] `.bashrc Immunity`:** Keine Eingabe nötig. Das System erzwingt intern hart `export ROS_DOMAIN_ID=0` und `export RMW_IMPLEMENTATION=rmw_fastrtps_cpp`, um DDS-Kollisionen durch kaputte User-Profile zu verhindern.

## 3. Architectural Logic & Data Flow

ROS 2 Systeme, die asynchrone Daemons nutzen, sind extrem anfällig für Zombie-Prozesse. Wenn die Gazebo-Simulation geschlossen wird, fangen Python-Threads das Signal oft nicht auf.

**[DEPRECATED in v4] Nuke & Pave:** Vor der Zerstörung der Container sendete das System explizite Stop-Befehle, danach jagte das Skript `kill_r2k.sh` Prozesse per `pkill`. Dies blockierte oft die Bash-EXIT-Trap und hinterließ Port 11434 belegt.

**[UPDATE in v5] The 0.2s Asynchronous Watchdog:** Das System verzichtet auf externe Cleanup-Skripte. Stattdessen startet `launch_r2k.sh` Gazebo im Hintergrund und fängt die Prozess-ID (`$!`). Eine `while`-Schleife pollt diese ID alle 0,2 Sekunden. Sobald der Nutzer das GUI-Fenster schließt (die ID verschwindet), feuert der Watchdog asynchron und absolut sofortig den *Kinematic Freeze* an alle Hardware-Topics. Direkt danach führt er ein hartes `pkill -9` auf `ollama` und alle `ros2`-Prozesse aus. Das harte `SIGKILL` (-9) verhindert nervige `RCLError` Tracebacks im Terminal und garantiert, dass keine Zombie-Prozesse VRAM oder Ports blockieren.

## 4. Code Reference & Interfaces

> **Source:** `kill_r2k.sh` **[DEPRECATED in v5 - Legacy File]**
> **Source:** `launch_r2k.sh` **[NEW in v5]**

**[NEW in v5] Watchdog & Immunity Sequence:**
Auszug aus dem neuen V5 Master-Launch-Skript.
~~~bash
# snippet from launch_r2k.sh
# 1. .bashrc Immunity
export ROS_DOMAIN_ID=0
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export OLLAMA_HOST=0.0.0.0

# ... Boot Sequence ...

GAZEBO_PID=$!

# 2. 0.2s Asynchronous Watchdog
echo "👁️  Watchdog active. Close the Gazebo window to terminate the system safely."
while kill -0 $GAZEBO_PID 2>/dev/null; do
    sleep 0.2
done

echo "🛑 UI closed! Firing Kinematic Freeze..."
# Last Command Hold Fix
ros2 topic pub --once /bot1/cmd_vel geometry_msgs/Twist '{linear: {x: 0.0}}' >/dev/null 2>&1
ros2 topic pub --once /bot1/LocoApiTopicReq std_msgs/String "{data: '{\"api_id\": 2000}'}" >/dev/null 2>&1

echo "🧹 Executing SIGKILL Teardown..."
pkill -9 -f "ros2"
pkill -9 ollama
echo "✅ Teardown complete. Ports released."
~~~

## 5. Known Issues & Limitations

* **Watchdog Race Condition:** Wenn der ROS 2 DDS Daemon (FastRTPS) oder der Host-Netzwerk-Stack genau im selben Millisekunden-Fenster abstürzt wie die UI, kann der Watchdog den `Twist 0.0` (Kinematic Freeze) nicht mehr auf das lokale Netzwerk senden. Die Hardware würde dann bis zur manuellen Abschaltung weiterfahren (Runaway).
* **Matplotlib Namespace Bug:** Standard-Deinstallationen beheben hartnäckige 3D-Axes-Warnungen in `r2k_visualizer.py` nicht. Dies erfordert weiterhin ein physisches Löschen verwaister `mpl_toolkits` Ordner via `rm -rf`.

## 6. Glossary

* **Zombie Process:** Ein Prozess, der seine Ausführung beendet hat, aber immer noch Systemressourcen (VRAM, Ports) bindet. Ollama ist hierfür extrem anfällig (Port 11434).
* **Kinematic Freeze:** Das explizite Feuern von Stop-Vektoren (Twist 0.0 oder API Code 2000) an die physische Hardware direkt vor dem Netzwerk-Teardown.
* **[NEW in v5] .bashrc Immunity:** Das Designprinzip, bei dem Boot-Skripte alle relevanten Netzwerk- und ROS-Pfade hart überschreiben, um fehlerhafte User-Umgebungen auszusperren.
* **[NEW in v5] 0.2s Asynchronous Watchdog:** Die hochfrequente Polling-Schleife, die das veraltete `kill_r2k.sh` Skript abgelöst hat.
