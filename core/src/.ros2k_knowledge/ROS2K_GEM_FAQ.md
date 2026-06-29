---
title: "ROS2K Architecture Mentor - System FAQ (V5)"
type: DOCUMENTATION
tags: [faq, onboarding, gem-capabilities, q-and-a, ros2, relay, booster-k1, watchdog, hybrid-os, qwen]
last_modified: 2026-06-03
version: v5_release
---
# ROS2K Architecture Mentor: FAQ & Capabilities

Dieses Dokument demonstriert die Fähigkeiten des KI-gestützten ROS2K-Mentors. Die Anfragen sind nach Nutzer-Intention klassifiziert: **[Neugierig]** (Onboarding & Grundlagen), **[Team Mitglied]** (Architektur-Verständnis & Use Cases) und **[Weiterentwicklung]** (Skalierung & Performance).

---

### Q1 [Neugierig]: Wie starte ich das System und welche Optionen bietet das `--help` Menü?
**User:** "Wie steuere ich das System beim Start und was machen die Parameter aus dem `--help` Menü?"

**Gem:** Das Skript `launch_r2k.sh` ist der einzige Entrypoint des Systems[cite: 12]. Das `--help` Menü listet folgende Parameter zur Steuerung auf[cite: 12]:
* `--relay [profile]`: Bestimmt das Hardware-Routing[cite: 12]. Nutze z.B. `only_sim_bots` für reine Simulation oder `hardware_mirror` für physische Labor-Hardware[cite: 12].
* `--scenario [name]`: Wählt das Spielfeld-Szenario (z.B. `1vs1_defend`) und veranlasst `setup_r2k.py`, den System-Prompt dynamisch zu kompilieren[cite: 12].
* `--no-explain`: Unterdrückt den textuellen Reasoning-Output der KI, um Latenz zu sparen und sofortige Aktionen zu erzwingen[cite: 12].
* `--debug`: Aktiviert verbale Logs in der `ollama_sandbox_bridge.py` und im `state_aggregator.py` zur Fehlersuche[cite: 12].
Im Hintergrund aktiviert das Skript völlig autonom die `.bashrc Immunity`, prüft das Host-OS und startet den 0.2s Asynchronous Watchdog[cite: 12].

---

### Q2 [Neugierig]: Was ist ROS2K und wie funktioniert das System grundlegend?
**User:** "Ich bin neu im Projekt. Kannst du mir einfach erklären, wie die KI und die Roboter zusammenhängen?"

**Gem:** ROS2K ist eine Testumgebung, in der ein KI-Sprachmodell (LLM) physische und simulierte Roboter steuert[cite: 15]. Das System ist extrem simpel gehalten und besteht im Kern aus reinen Python-Skripten[cite: 15]. Das LLM 'liest' eine Textdatei mit den aktuellen Koordinaten, entscheidet über den nächsten Zug und schreibt einen Text zurück[cite: 15]. Unsere Python-Skripte übersetzen diesen Text dann in einfache Motorbefehle für die Roboter[cite: 15].

~~~mermaid
graph TD
    AI["KI Modell Ollama (Qwen2.5)"]
    Py["Python Skripte (Keine OOP HALs)"]
    Bot["Gazebo Simulation und Hardware"]

    AI -->|"Liest und Schreibt Text"| Py
    Py -->|"Sendet Motorbefehle"| Bot
~~~

---

### Q3 [Neugierig]: Nutzt die KI normale ROS 2 Odometrie für die Orientierung?
**User:** "Wie orientiert sich die KI? Bekommt sie klassische ROS 2 Sensordaten oder Koordinatentransformationen gefüttert?"

**Gem:** Nein, wir umgehen klassische Sensordaten-Fusion komplett[cite: 15]. Kleine LLMs scheitern oft an der Mathematik von 3D-Quarternionen[cite: 15]. Unser Wahrnehmungs-Knoten (`tracker_node.py`) liest die globale Wahrheit direkt aus Gazebo (`/gazebo/model_states`)[cite: 15]. Er entfernt die Z-Achse (Höhe), verwirft Pitch und Roll und rechnet alles in ein flaches 2D-Raster (X, Y, Yaw) um[cite: 15]. Der `state_aggregator.py` bündelt dies und das LLM erhält eine perfekt flache 2D-Sichtweise auf das Spielfeld[cite: 15].

---

### Q4 [Team Mitglied]: Was sind die typischen Use Cases und wie starte ich sie?
**User:** "Wie wechsle ich zwischen reinen Simulationstests und echten Hardware-Tests?"

**Gem:** Das gesamte System wird über einen einzigen Einstiegspunkt gesteuert: das Skript `launch_r2k.sh`[cite: 15]. Du definierst den Use Case rein über Kommandozeilen-Flags[cite: 15].
* **Use Case 1 (Reine Simulation):** Für das Testen neuer LLM-Prompts im Simulator[cite: 15].
  `./launch_r2k.sh --scenario 2vs2_default --relay only_sim_bots`[cite: 15]
* **Use Case 2 (Sim2Real Hardware Test):** Wenn physische Roboter auf dem Feld stehen, die exakt das tun sollen, was in der Simulation passiert[cite: 15].
  `./launch_r2k.sh --scenario 1vs1_defend --relay hardware_mirror`[cite: 15]

---

### Q5 [Team Mitglied]: Wie routet das System Befehle an Simulation vs. echte Hardware?
**User:** "Woher weiß die Ausführungs-Bridge, ob ein Roboter virtuell oder physisch auf dem Feld steht?"

**Gem:** Das wird durch das dynamische **Hardware Relay System** gelöst[cite: 15]. Das Startskript kompiliert eine flüchtige Konfigurationsdatei namens `active_relay.json`[cite: 15]. Die Ausführungs-Bridge (`ollama_sandbox_bridge.py`) ist komplett zustandslos und nutzt **keine OOP HALs** (Hardware Abstraction Layers)[cite: 15]. Die Bridge liest einfach den `hardware_type` und startet dynamische Thread-Closures (`def task`), um generische X/Y-Koordinaten in Standard-ROS-Nachrichten oder proprietäre K1-Payloads zu übersetzen[cite: 15].

---

### Q6 [Team Mitglied]: Warum reagiert der Booster K1 nicht auf normale Fahrbefehle?
**User:** "Ich versuche, den physischen Booster K1 Bipeden über normale ROS 2 `cmd_vel` (Twist) Nachrichten zu steuern, aber er bewegt sich nicht."

**Gem:** Der K1 ignoriert Standard-Twist-Nachrichten[cite: 15]. Die Bridge serialisiert die LLM-Befehle stattdessen in spezifische JSON-Strings und sendet sie an das isolierte Hardware-Topic `/bot1/LocoApiTopicReq`[cite: 15]. Wir nutzen API-Code `2001` für die aktive Bewegung und Code `2000` für den Not-Halt (Kinematic Freeze)[cite: 15].

---

### Q7 [Team Mitglied]: Warum stehen die Roboter still, obwohl die KI Ausgaben generiert?
**User:** "Die KI generiert strategisch sinnvolle Züge, aber die Roboter bewegen sich nicht."

**Gem:** Das ist oft ein Schema-Problem (Parsing Paralysis)[cite: 15]. Unsere Python-Skripte erwarten zwingend ein **absolut flaches** JSON-Format für das `qwen2.5-coder:3b` Modell[cite: 15]. Wenn die KI komplexe Verschachtelungen nutzt, stürzt die Ausführung ab[cite: 15]. Der dynamische Prompt-Compiler (`setup_r2k.py`) muss zwingend exakte, flache Few-Shot-Beispiele übergeben[cite: 15].

---

### Q8 [Team Mitglied]: Wie verhindert das System Kollisionen beim Lesen der Textdateien?
**User:** "Die Positionsdaten werden mit 10Hz in die Textdatei geschrieben, während die KI asynchron darauf zugreift. Warum crasht das System nicht beim gleichzeitigen Lesen/Schreiben?"

**Gem:** Wir nutzen einen POSIX-Trick auf Dateisystemebene im `shared_state/` Ordner[cite: 15]. Der Aggregator schreibt die![[DOCUMENTATION]] Daten zunächst in eine temporäre Datei (`Worldstate.json.tmp`)[cite: 15]. Erst wenn der Schreibvorgang abgeschlossen ist, wird die Datei über den Befehl `os.replace` atomar umbenannt[cite: 15].

~~~mermaid
graph LR
    TMP["Worldstate.json.tmp"] -->|"Atomic Swap (os.replace)"| FIN["Aggregated_Worldstate.json"]
    FIN -->|"Sicheres asynchrones Lesen"| EVAL["r2k_evaluator.py"]
~~~

---

### Q9 [Weiterentwicklung]: Wie funktioniert die Hybrid OS Topology in V5?
**User:** "Wie gehen wir mit der Abhängigkeit von Ubuntu 22 (ROS Humble) um, wenn wir auf Ubuntu 24 Hosts arbeiten?"

**Gem:** Die `launch_r2k.sh` nutzt eine dynamische **Hybrid OS Topology**[cite: 15]. Sie liest `lsb_release -rs` aus[cite: 15]:
* **Auf Ubuntu 22.04:** Startet das System 100% nativ[cite: 15]. Der `micro-ROS-agent` wird lokal im `uros_ws` kompiliert, um FastDDS Shared-Memory (SHM) Blockaden zu umgehen (0ms Latenz)[cite: 15].
* **Auf Ubuntu 24.04:** Das System kapselt ROS 2 in Docker-Compose, nutzt X11-Forwarding für Gazebo und weist Containern dynamisch Namen via `COMPOSE_PROJECT_NAME` zu, um Kollisionen zu verhindern[cite: 15].

---

### Q10 [Weiterentwicklung]: Wie drücken wir die LLM-Latenz und umgehen Port-Locks?
**User:** "Die KI braucht zu lange. Kann ich Ollama als systemd-Dienst optimieren?"

**Gem:** **NEIN! In V5 darf Ollama NICHT als systemd-Dienst laufen**[cite: 15]. Ollama muss im User-Space laufen[cite: 15]. Um die Latenz zu drücken, exportierst du vor dem Start in deiner Shell[cite: 15]:
`export OLLAMA_NUM_PARALLEL=1` und `export OLLAMA_KV_CACHE_TYPE=q8_0`[cite: 15].
Dadurch kann unser neuer **0.2s Asynchronous Watchdog** beim Schließen der UI ein hartes `pkill -9 ollama` ausführen, um Zombie-Prozesse und Port 11434-Locks (RCLError Tracebacks) absolut zuverlässig zu vernichten[cite: 15].

---

### Q11 [Weiterentwicklung]: Warum nutzt die KI plötzlich die CPU statt der GPU?
**User:** "Nachdem mein Rechner im Standby war, springt die Ollama-Latenz von 200ms auf über 7000ms. Was passiert da?"

**Gem:** Das ist der berüchtigte **Nvidia Xid 31 Suspend-Bug**[cite: 15]. Wenn Linux in den Suspend-to-RAM geht, verliert der Treiber die Page-Directories im VRAM[cite: 15]. Ollama stürzt stumm ab und fällt auf die CPU zurück[cite: 15]. Die Lösung ist *nicht* Skripte umzuschreiben, sondern das Kernel-Feature zu aktivieren: `options nvidia NVreg_PreserveVideoMemoryAllocations=1` und den `nvidia-suspend.service` zu enablen[cite: 15].

---

### Q12 [Weiterentwicklung]: Was tun, wenn Hardware-Roboter im Labor nicht erkannt werden?
**User:** "Der ESP32 oder K1 verbindet sich nicht mit dem Host-Netzwerk."

**Gem:** Das liegt meistens an kaputten Nutzer-Profilen (DDS-Kollisionen)[cite: 15]. Die V5-Architektur nutzt deshalb die **.bashrc Immunity**[cite: 15]. Das Startskript überschreibt hart `export ROS_DOMAIN_ID=0` und `export RMW_IMPLEMENTATION=rmw_fastrtps_cpp`, um alle toxischen User-Umgebungsvariablen auszusperren[cite: 15].
