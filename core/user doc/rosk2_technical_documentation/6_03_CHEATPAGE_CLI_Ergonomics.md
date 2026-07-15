---
id: 6_03
title: "Cheatpage: CLI Ergonomics, Launch Flags & System-Orchestration"
type: CHEATPAGE
tags: [cli, flags, launch, terminal, hybrid-os, bashrc-immunity, watchdog, v6, v6.1, v6.2, headless, duration, explain, r2k-run-id]
last_modified: 2026-07-15
version: v6.2
---
# Cheatpage: CLI Ergonomics & Launch Flags

> [!info] Human Summary
> Die zentrale Anlaufstelle für die Systemsteuerung. Dieses Dokument definiert die CLI-Flags von `launch_r2k.sh`, das Verhalten des 0.2s Watchdogs und die Sicherheitsmechanismen der .bashrc Immunity.

> [!abstract] LLM Context Anchor
> Das System hat Standalone-Skripte zugunsten einer zentralisierten, CLI-gesteuerten Parameterübergabe in `launch_r2k.sh` verabschiedet. Es gibt keine manuelle Orchestrierung einzelner Daemons mehr; alles wird durch das Pre-Flight-Compiler-Pattern (`setup_r2k.py`) gesteuert.
> **[NEW in v5]:** Die CLI-Umgebung orchestriert nun dynamisch die Hybrid OS Topology (Ubuntu 22.04 Nativ vs. 24.04 Docker) und immunisiert die Shell gegen störende Benutzer-Konfigurationen.

## 1. Das CLI-Steuerungsmenü (`launch_r2k.sh`)

Das Startskript ist der alleinige Entrypoint. Alle Parameter werden an `setup_r2k.py` zur dynamischen Kompilation weitergereicht.

* `--relay [profile]`: Selects the relay profile. `launch_r2k.sh` automatically reads `src/relay/<profile>.json` as single source of truth. Topic names, hardware namespaces and sync flags are derived from the JSON at startup. No manual sync between script and config required.
    * `only_sim_bots`: Routes all agents to Gazebo (default).
    * `hardware_mirror`: Activates physical mirroring (Yahboom/K1).
    * Any future `relay/<name>.json` file is supported automatically.
* `--scenario [name]`: Wählt die Szenario-JSON; löst die dynamische Prompt-Kompilierung für `qwen2.5-coder:3b` aus.
* `--no-explain`: Deaktiviert den textuellen Reasoning-Output der KI, um die Latenz der 10Hz-Pipeline zu minimieren.
* `--explain`: Aktiviert Reasoning-Output (analysis+oracle keys, 600 token cap). Standardmäßig deaktiviert.
* `--headless`: Startet nur `gzserver` (kein Gazebo-GUI). Für Batch-Evaluation. Siehe [[7_03_CHEATPAGE_Tools_and_Utils]].
* `--duration [N]`: Match-Dauer in Sekunden. Auto-Terminierung nach Ablauf.
* `--strategy [name]`: Wählt die Strategie (z.B. `strat_default`, `strat_aggro`, `strat_recover`). Bestimmt welche Fragment-Overrides gelten.
* `--model [name]`: Wählt das Ollama-Modell (Standard: `qwen2.5-coder:3b`).
* `--debug`: Aktiviert verbale Logs der `ollama_sandbox_bridge.py` und des `state_aggregator.py`.
* **`R2K_RUN_ID`**: Automatisch exportiert als `${SCENARIO}_${STRATEGY}_<timestamp>`. Korreliert Trace-Dateien. Siehe [[7_03_CHEATPAGE_Tools_and_Utils]].

## 2. V5-Sicherheitsmechanismen (Autonom)

Diese Mechanismen erfordern keine manuellen Flags, sind aber essenziell für den Betrieb:

* **[NEW] .bashrc Immunity:** Beim Aufruf von `launch_r2k.sh` werden Umgebungsvariablen wie `ROS_DOMAIN_ID` oder `RMW_IMPLEMENTATION` hart mit den V5-Standardwerten (`0` und `rmw_fastrtps_cpp`) überschrieben. Dies verhindert, dass lokale Shell-Konfigurationen die Hardware-Discovery der ESP32-Bots blind machen.
* **[NEW] Hybrid OS Detection:** Das Skript ermittelt mittels `lsb_release -rs` die Ubuntu-Version. Auf **Ubuntu 22.04** wird die Infrastruktur *nativ* (via `uros_ws`) aufgebaut; auf **Ubuntu 24.04** wird `docker compose` mit dem korrekt generierten `COMPOSE_PROJECT_NAME` initiiert.
* **[NEW] 0.2s Asynchronous Watchdog:** Sobald der Prozess gestartet ist, überwacht eine Polling-Schleife die Gazebo-PID. Bei UI-Schließung feuert der Watchdog asynchron den `Kinematic Freeze` (Twist 0.0 & API Code 2000), gefolgt von `pkill -9` für alle `ros2` und `ollama` Prozesse.

## 3. Ausgemusterte POC-Skripte & Legacy-Handling

**[UPDATE in v5] Aufräumaktion:**
Das System nutzt `launch_r2k.sh` als einzigen Entrypoint. Die ehemals existierenden Proof-of-Concept-Skripte sind obsolet:
* `launch_triple_demo.sh` -> Ersetzt durch `--relay hardware_mirror`.
* `kill_r2k.sh` ("Nuke & Pave") -> Liegt im Root, wird aber **nicht mehr aktiv ausgeführt**. Der Watchdog übernimmt das Teardown-Management prozesssicher und ohne RCLError-Tracebacks.

## 4. Häufige Fehler & CLI-Ergonomie
* **Fehler "Port 11434 in use":** Tritt auf, wenn Ollama als Zombie-Prozess weiterläuft. 
    * *Lösung:* Die V5-Architektur verhindert dies durch den Watchdog, sofern die Gazebo-UI nicht gewaltsam (z.B. durch `kill -9` der Shell selbst) beendet wurde. Sollte es dennoch auftreten: `pkill -9 ollama`.
* **Fehler "ROS Namespace Collision":** Tritt auf, wenn zwei Instanzen mit gleichem Pfad gestartet werden.
    * *Lösung:* Das V5-Skript setzt `COMPOSE_PROJECT_NAME=$(basename "$PWD")`. Stelle sicher, dass die Arbeitsverzeichnisse der Instanzen eindeutige Namen tragen.
* **"cannot change mount namespace":** Tritt bei korrupten Snap-Schnittstellen auf Ubuntu 24 auf.
    * *Lösung:* `sudo /usr/lib/snapd/snap-discard-ns <app>` ausführen.

## 5. Hardware Sync Stability Notes [NEW in v6]

* **Hotspot reuse (maker4):** If the maker4 hotspot is already active when `launch_r2k.sh` starts, it will not be restarted. This prevents breaking the WLAN connection of already-connected hardware (e.g. K1). The hotspot is only started fresh if not yet active.
* **uros agent race condition (Ubuntu 24):** The Docker micro-ROS agent container needs ~3s to become ready after start. A `sleep 3` is added after container launch to avoid the Yahboom reconnect missing the agent on relaunch.
