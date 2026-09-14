---
title: "ROS2K Architecture Mentor - System FAQ (V6.3)"
type: DOCUMENTATION
tags: [faq, onboarding, gem-capabilities, q-and-a, ros2, relay, booster-k1, watchdog, hybrid-os, qwen, v6, v6.1, v6.2, v6.3, momentum, reward, trace-logging, set-piece, headless, kpi, analyze-trace, dump-prompt, goalie-idle, closed-loop, test-non-functional, composite-score, pytest, regression-suite, kpi-targets, skip-slow, dynamic-prompt-injection, content-hash-skip, role-condensation, replay-system, attack-kpis]
last_modified: 2026-08-05
version: v6.4
---
# ROS2K Architecture Mentor: FAQ & Capabilities

Dieses Dokument demonstriert die Fähigkeiten des KI-gestützten ROS2K-Mentors. Die Anfragen sind nach Nutzer-Intention klassifiziert: **[Neugierig]** (Onboarding & Grundlagen), **[Team Mitglied]** (Architektur-Verständnis & Use Cases) und **[Weiterentwicklung]** (Skalierung & Performance).

> [!info] V6.3 Addendum (2026-07-29)
> Q1-Q12 stammen aus V5 (2026-06-03) und wurden dort, wo nötig, inline aktualisiert
> (Flags, Szenarien). Q13-Q23 sind neu in V6.2 und decken Scoring/Momentum/Reward,
> Set-Pieces, Trace-Logging, KPI-Messung, Prompt-Architektur, Goalie-Idle und die
> Closed-Loop-Feedback-Lücke ab. Q24 (Regression Suite) ist V6.2. Q25 (Dynamic Prompt
> Injection) und Q26 (Content-Hash Skip) sind neu in V6.3. Autoritative Referenzen:
> `core/docs/referee_rulebook.md`, `core/docs/optimization_spec_v6.3.md` sowie Section 7
> der User-Docs.

---

### Q1 [Neugierig]: Wie starte ich das System und welche Optionen bietet das `--help` Menü?
**User:** "Wie steuere ich das System beim Start und was machen die Parameter aus dem `--help` Menü?"

**Gem:** Das Skript `launch_r2k.sh` ist der einzige Entrypoint des Systems. Das `--help` Menü listet folgende Parameter zur Steuerung auf:
* `--relay [profile]`: Bestimmt das Hardware-Routing. Nutze z.B. `only_sim_bots` für reine Simulation oder `hardware_mirror` für physische Labor-Hardware.
* `--scenario [name]`: Wählt das Spielfeld-Szenario (z.B. `3vs3_attack_center`, TC-01..09) und veranlasst `setup_r2k.py`, den System-Prompt dynamisch zu kompilieren.
* `--strategy [name]`: Wählt die Strategie-Fragmente (z.B. `strat_default`, `strat_aggro`). V6.1: `strat_*.txt` Build-Artefakte wurden entfernt, nur `strategy/fragments/` zählt.
* `--no-explain` / `--explain`: Unterdrückt bzw. aktiviert den textuellen Reasoning-Output der KI. `--no-explain` (150 Token Cap, Assignments-only) ist V6.2-Default. `--explain` (600 Token) senkt OOB auf 1.9%, kostet aber +44% Latenz.
* `--headless`: Startet Gazebo ohne GUI (`gzserver` only). 30-50% schneller, nötig für Batch-Evaluation.
* `--duration [s]`: Match-Dauer in Sekunden (Auto-Termination nach N Sekunden).
* `--model [name]`: Überschreibt das Ollama-Modell für diese Sitzung (V6.2, hauptsächlich für `batch_evaluator.py` relevant).
Im Hintergrund aktiviert das Skript völlig autonom die `.bashrc Immunity`, prüft das Host-OS und startet den 0.2s Asynchronous Watchdog. V6.1: zusätzlich wird `R2K_RUN_ID` exportiert und in Docker-Container propagiert.

---

### Q2 [Neugierig]: Was ist ROS2K und wie funktioniert das System grundlegend?
**User:** "Ich bin neu im Projekt. Kannst du mir einfach erklären, wie die KI und die Roboter zusammenhängen?"

**Gem:** ROS2K ist eine Testumgebung, in der ein KI-Sprachmodell (LLM) physische und simulierte Roboter steuert. Das System ist extrem simpel gehalten und besteht im Kern aus reinen Python-Skripten. Das LLM 'liest' eine Textdatei mit den aktuellen Koordinaten, entscheidet über den nächsten Zug und schreibt einen Text zurück. Unsere Python-Skripte übersetzen diesen Text dann in einfache Motorbefehle für die Roboter.

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

**Gem:** Nein, wir umgehen klassische Sensordaten-Fusion komplett. Kleine LLMs scheitern oft an der Mathematik von 3D-Quarternionen. Unser Wahrnehmungs-Knoten (`tracker_node.py`) liest die globale Wahrheit direkt aus Gazebo (`/gazebo/model_states`). Er extrahiert nur `position.x` und `position.y` — kein Yaw, keine Quaternion-Konvertierung, keine Z-Achse. Der `state_aggregator.py` bündelt dies und das LLM erhält eine perfekt flache 2D-Sichtweise (nur X/Y) auf das Spielfeld.

---

### Q4 [Team Mitglied]: Was sind die typischen Use Cases und wie starte ich sie?
**User:** "Wie wechsle ich zwischen reinen Simulationstests und echten Hardware-Tests?"

**Gem:** Das gesamte System wird über einen einzigen Einstiegspunkt gesteuert: das Skript `launch_r2k.sh`. Du definierst den Use Case rein über Kommandozeilen-Flags.
* **Use Case 1 (Reine Simulation):** Für das Testen neuer LLM-Prompts im Simulator. V6.2 nutzt 3vs3-Szenarien (TC-01..09, z.B. `3vs3_attack_center`).
  `./launch_r2k.sh --headless --duration 120 --scenario 3vs3_attack_center --strategy strat_default --relay only_sim_bots`
* **Use Case 2 (Sim2Real Hardware Test):** Wenn physische Roboter auf dem Feld stehen, die exakt das tun sollen, was in der Simulation passiert.
  `./launch_r2k.sh --scenario 1vs1_default --relay hardware_mirror`
* **Use Case 3 (Regression Suite, V6.2):** Headless-Multi-Run mit KPI-Assertions. Ersetzt den deprecated `batch_evaluator.py` (dessen KPI-Collection nie funktionierte). Die Shared Regression Suite (`tests/test_non_functional.py`) nutzt pytest-Marker für Two-Tier-Testing — siehe Q24.
  `python3 -m pytest tests/test_non_functional.py -v -s  # slow tier (real Gazebo matches)`
  `python3 -m pytest tests/ --skip-slow -v               # fast tier (unit tests only, ~2s)`

---

### Q5 [Team Mitglied]: Wie routet das System Befehle an Simulation vs. echte Hardware?
**User:** "Woher weiß die Ausführungs-Bridge, ob ein Roboter virtuell oder physisch auf dem Feld steht?"

**Gem:** Das wird durch das dynamische **Hardware Relay System** gelöst. Das Startskript kompiliert eine flüchtige Konfigurationsdatei namens `active_relay.json`. Die Ausführungs-Bridge (`ollama_sandbox_bridge.py`) ist komplett zustandslos und nutzt **keine OOP HALs** (Hardware Abstraction Layers). Die Bridge liest einfach den `hardware_type` und startet dynamische Thread-Closures (`def task`), um generische X/Y-Koordinaten in Standard-ROS-Nachrichten oder proprietäre K1-Payloads zu übersetzen.

---

### Q6 [Team Mitglied]: Warum reagiert der Booster K1 nicht auf normale Fahrbefehle?
**User:** "Ich versuche, den physischen Booster K1 Bipeden über normale ROS 2 `cmd_vel` (Twist) Nachrichten zu steuern, aber er bewegt sich nicht."

**Gem:** Der K1 ignoriert Standard-Twist-Nachrichten. Die Bridge serialisiert die LLM-Befehle stattdessen in spezifische JSON-Strings und sendet sie an das isolierte Hardware-Topic (z.B. `/Kev1n/LocoApiTopicReq`, topic-name kommt aus `active_relay.json`). Wir nutzen API-Code `2001` für die aktive Bewegung und Code `2000` für den Not-Halt (Kinematic Freeze).

---

### Q7 [Team Mitglied]: Warum stehen die Roboter still, obwohl die KI Ausgaben generiert?
**User:** "Die KI generiert strategisch sinnvolle Züge, aber die Roboter bewegen sich nicht."

**Gem:** Das ist oft ein Schema-Problem (Parsing Paralysis). Unsere Python-Skripte erwarten zwingend ein **absolut flaches** JSON-Format für das `qwen2.5-coder:3b` Modell. Wenn die KI komplexe Verschachtelungen nutzt, stürzt die Ausführung ab. Der dynamische Prompt-Compiler (`setup_r2k.py`) muss zwingend exakte, flache Few-Shot-Beispiele übergeben.

---

### Q8 [Team Mitglied]: Wie verhindert das System Kollisionen beim Lesen der Textdateien?
**User:** "Die Positionsdaten werden mit 10Hz in die Textdatei geschrieben, während die KI asynchron darauf zugreift. Warum crasht das System nicht beim gleichzeitigen Lesen/Schreiben?"

**Gem:** Wir nutzen einen POSIX-Trick auf Dateisystemebene im `shared_state/` Ordner. Der Aggregator schreibt die Daten zunächst in eine temporäre Datei (`Worldstate.json.tmp`). Erst wenn der Schreibvorgang abgeschlossen ist, wird die Datei über `os.replace` atomar umbenannt (POSIX atomic rename — `os.replace` ist idiomatisch für atomare Swaps in Python, beide Nodes nutzen es).

~~~mermaid
graph LR
    TMP["Worldstate.json.tmp"] -->|"Atomic Swap (os.replace)"| FIN["Worldstate.json"]
    FIN -->|"Sicheres asynchrones Lesen"| EVAL["r2k_evaluator.py"]
~~~

---

### Q9 [Weiterentwicklung]: Wie funktioniert die Hybrid OS Topology?
**User:** "Wie gehen wir mit der Abhängigkeit von Ubuntu 22 (ROS Humble) um, wenn wir auf Ubuntu 24 Hosts arbeiten?"

**Gem:** Die `launch_r2k.sh` nutzt eine dynamische **Hybrid OS Topology**. Sie liest `lsb_release -rs` aus:
* **Auf Ubuntu 22.04:** Startet das System 100% nativ. Der `micro-ROS-agent` wird lokal im `uros_ws` kompiliert, um FastDDS Shared-Memory (SHM) Blockaden zu umgehen (0ms Latenz).
* **Auf Ubuntu 24.04:** Das System kapselt ROS 2 in Docker-Compose, nutzt X11-Forwarding für Gazebo und weist Containern dynamisch Namen via `COMPOSE_PROJECT_NAME` zu, um Kollisionen zu verhindern.

---

### Q10 [Weiterentwicklung]: Wie drücken wir die LLM-Latenz und umgehen Port-Locks?
**User:** "Die KI braucht zu lange. Kann ich Ollama als systemd-Dienst optimieren?"

**Gem:** Ollama muss unter `0.0.0.0:11434` erreichbar sein (nicht nur `127.0.0.1`), damit Docker-Container zugreifen koennen. Es funktioniert auf zwei Wegen: (1) **Manueller Start** im User-Space mit `OLLAMA_HOST=0.0.0.0 ollama serve` — der 0.2s Watchdog beendet es per `pkill -9`. (2) **systemd-Service** mit Override `Environment="OLLAMA_HOST=0.0.0.0"` (via `install.sh`) — der Watchdog killt den Prozess, systemd startet ihn neu (akzeptabel, da der Watchdog die Bots einfriert, nicht Ollama dauerhaft stoppen muss). Beide Wege sind erlaubt.

Optional kann der Nutzer vor dem Start in seiner Shell Latenz-Tuning-Variablen exportieren (nicht vom Startskript gesetzt):
`export OLLAMA_NUM_PARALLEL=1` und `export OLLAMA_KV_CACHE_TYPE=q8_0`.
Das verhindert Multi-User-Konkurrenz auf Port 11434 und quantisiert den Attention-Cache für rohe Inferenzgeschwindigkeit.

---

### Q11 [Weiterentwicklung]: Warum nutzt die KI plötzlich die CPU statt der GPU?
**User:** "Nachdem mein Rechner im Standby war, springt die Ollama-Latenz von 200ms auf über 7000ms. Was passiert da?"

**Gem:** Das ist der berüchtigte **Nvidia Xid 31 Suspend-Bug**. Wenn Linux in den Suspend-to-RAM geht, verliert der Treiber die Page-Directories im VRAM. Ollama stürzt stumm ab und fällt auf die CPU zurück. Die Lösung ist *nicht* Skripte umzuschreiben, sondern das Kernel-Feature zu aktivieren: `options nvidia NVreg_PreserveVideoMemoryAllocations=1` und den `nvidia-suspend.service` zu enablen.

---

### Q12 [Weiterentwicklung]: Was tun, wenn Hardware-Roboter im Labor nicht erkannt werden?
**User:** "Der ESP32 oder K1 verbindet sich nicht mit dem Host-Netzwerk."

**Gem:** Das liegt meistens an kaputten Nutzer-Profilen (DDS-Kollisionen). Die Architektur nutzt deshalb die **.bashrc Immunity**: `launch_r2k.sh:4-6` überschreibt hart `export ROS_DOMAIN_ID=0` und `export RMW_IMPLEMENTATION=rmw_fastrtps_cpp`, um alle toxischen User-Umgebungsvariablen auszusperren.

> [!warning] V6.2 Axiom-Spannung: `ROS_DOMAIN_ID=0` vs. Multi-Participant-Workshops
> Die `.bashrc Immunity` (Axiom 4) ist für Einzelnutzer-Betrieb korrekt. Wenn aber
> **mehrere Team-Mitglieder auf isolierten GPUs im selben LAN** arbeiten, kollidiert
> das shared `ROS_DOMAIN_ID=0` genau so, wie Q12 es zu verhindern sucht. Optionen:
> (a) `launch_r2k.sh` patchen, sodass ein vorgesetzter `ROS_DOMAIN_ID` respektiert wird,
> (b) getrennte VLANs/Hosts, (c) Kollisionsrisiko für Teaching-Demos akzeptieren.
> Siehe Workshop-Diskussion Module 5.

---

## V6.2 Addendum — Neue FAQs (Q13-Q23)

> [!abstract] Scope
> Diese neuen Einträge decken die V6-Scoring-Engine, V6.1-Trace-Instrumentierung,
> V6.2-Prompt-Studie, Set-Pieces, Goalie-Idle und die offene Closed-Loop-Feedback-Lücke ab.
> Quellen: `core/docs/referee_rulebook.md` (autoritativ für Regeln),
> `core/docs/optimization_spec_v6.2.md` (autoritativ für Spezifikation),
> User-Docs Section 7 (`7_01`..`7_05`).

---

### Q13 [Team Mitglied]: Wie funktioniert das Scoring in V6? Was sind Momentum und Reward?
**User:** "Ich höre von `tactical_score`, `momentum_30s` und `tactical_reward`. Was ist der Unterschied?"

**Gem:** Drei Konzepte, drei Nodes, zwei Topics — nicht vermischen.

* **`score_node.py` → `/tactical_score` (10Hz):** Numerischer taktischer Score `-10..+10` (positiv = Blue-Vorteil). Komponenten: Ball-X × 1.5 (±6.75), Ball-Proximity ±2.0, geclamped auf ±10.
* **Momentum (V6):** `deque(maxlen=300)` Ringbuffer (30s bei 10Hz), OLS lineare Regression über das Fenster → Steigung × `MOMENTUM_SCALE_FACTOR=10.0`, geclamped `-10..+10`. Minimum 10 Samples vor Trend-Klassifikation (Cold-Start: erste 3s = "stable"). Fünf Trend-Klassen: `ascending >2.0`, `improving >0.5`, `stable >-0.5`, `declining >-2.0`, sonst `collapsing`.
* **`reward_node.py` → `/tactical_reward` (1Hz):** Belohnung `-10..+10`. **Zwei Code-Pfade, nie mischen:**
  * *Decision Reward:* Pollt `current_strategy.json` mtime. Snapshot vor Aktion, warte 5s (Move) / 2s (Kick), Snapshot nach. `Delta = Reward`.
  * *Foul Penalty:* Abonniert `/match_state` für Foul-Events. Fixer `-1.0` Penalty (`-0.5` für Ball-Out).

Klassifikation: `> +1.0` positive, `-1.0..+1.0` neutral, `< -1.0` negative. Siehe [[7_01_INTRODUCTION_Scoring_Referee_Gamestate]].

---

### Q14 [Team Mitglied]: Was sind Set-Pieces und wie setzt der Referee sie durch?
**User:** "Ich sehe Status wie `goal_kick`, `corner_kick_in` und `kickoff` im Match-State. Was passiert da?"

**Gem:** V6.1 hat alle Restart-Typen unter einem **Unified Restart Pattern** zusammengefasst (siehe `referee_rulebook.md` §4). Alle folgen demselben Ablauf:

1. Ball an Restart-Position platzieren (Torarea-Ecke ±3.5/±1.0 für Goal Kick, Eckflagge ±4.3/±2.8 für Corner Kick-In, Zentrum für Kickoff).
2. Gegner innerhalb 1.5m radial wegwarpen (`WARP_AWAY_DISTANCE=2.0m`).
3. Gegner-Team 5s einfrieren (Twist-zero auf `cmd_vel`).
4. `restart_team` setzen (Team, das den Restart ausführt).
5. **Early Termination:** Sobald ein Bot des Restart-Teams innerhalb 0.3m des Balls ist → `BALL FREE` → Status `playing`. Die 5s sind also ein Maximum, keine feste Dauer.

Kickoff-Semantik (V6.1 Flip): Das **scoring** Team wird 5s eingefroren, das **conceding** Team führt den Kickoff aus. Verhindert sofortiges Pressen durch das Torschieß-Team.

**Field Exit Exception:** Bots dürfen bis zu **1.0m außerhalb des Feldes** stehen, wenn sie der Restart-Team-Bot sind und der Status `ball_out`/`goal_kick`/`corner_kick_in` ist. Normales Spiel erlaubt ±0.5m. Siehe `referee_rulebook.md` §1 Field Exit Exception.

---

### Q15 [Team Mitglied]: Welche Fouls erkennt der Referee und welche Thresholds gelten?
**User:** "Wann pfeift der Referee? Und was ist der Unterschied zwischen Threshold und Hysterese?"

**Gem:** Zwei Foul-Typen, beide in `referee_node.py:24-30` definiert:

* **Pushing:** Zwei gegnerische Bots näher als `PUSHING_DISTANCE_THRESHOLD=0.3m`, beide mehr als `BALL_PROXIMITY_THRESHOLD=0.8m` vom Ball entfernt. Penalty: Täter zur gegnerischen Sideline warpen (`X=±4.0`, Random-Y). Cooldown 5s pro Bot. Reward `-1.0`.
* **Blocking without Ball:** Ein Bot blockiert den Gegner-Pfad zum Ball für `BLOCKING_MIN_DURATION=3.0s`, Blocker >0.8m vom Ball entfernt, `OBSTRUCTION_ANGLE=30°`. Penalty: Täter in eigene Hälfte warpen. Reward `-1.0`.

**Threshold vs Hysterese** (zentrales Konzept):
* **Threshold** = harte binäre Grenze. 0.29m = kein Foul, 0.31m = Foul jeden Frame → Flicker.
* **Hysterese** = N aufeinanderfolgende Frames / Cooldown zur Bestätigung. `HYSTERESIS_FRAMES=3` (Last-Touch), `DEBOUNCE_FRAMES=5` (Ball-Out), `foul_cooldown=5s`. Verhindert Flicker, kostet Latenz.
* **Kosten der Hysterese:** `last_toucher` verfällt **nie** — der Kicker bleibt verantwortlich, auch wenn 10s später der Ball ins Aus geht (by Design, `referee_rulebook.md` §6 Stale-Toucher-Warnung).

ROS2K nutzt heute **nur Threshold + Hysterese**. Korridor (Bänder mit gradiertem Wert, z.B. Momentum-Trend-Klassen) kommt nur im Scoring vor. **Probability** (Bayesian/Kalman) fehlt komplett — das ist die Phase-5-Forschungsfront (5.1 Kalman Filter).

---

### Q16 [Team Mitglied]: Was misst `analyze_trace.py` und wie korreliert das mit `R2K_RUN_ID`?
**User:** "Wie komme ich von einem Match-Lauf zu konkreten KPIs?"

**Gem:** Drei Schritte, alle offline (kein ROS, kein Ollama nötig):

1. **Während des Laufs:** `launch_r2k.sh:82` exportiert `R2K_RUN_ID="${SCENARIO}_${STRATEGY}_$(date +%Y%m%d_%H%M%S)"`. Der `r2k_evaluator.py` schreibt `logs/llm_trace_<run_id>.jsonl` (eine JSON-Zeile pro LLM-Call), der `state_aggregator.py` schreibt `logs/world_trace_<run_id>.jsonl` (eine Zeile pro 10Hz World-State-Write).
2. **Nach dem Lauf:** `python3 tools/analyze_trace.py --run-id <ID> --output results/kpis_<ID>.json`. Joint beide Trace-Files per Timestamp, berechnet **18 KPIs** (V6.2: +`goalie_tactical_pct`; V6.3: +`shots_on_goal`, +`shots_on_target`, +`pass_completion_pct`, +`restart_recovery_time_s`; V6.3: -`role_diversity` — dead metric nach Role Condensation).
3. **Lesen:** `world_kpis` (Goals, Cluster%, OOB%, Goalie-Idle%, **Goalie-Tactical%** [V6.2], **Shots on Goal/Target** [V6.3], **Pass Completion%** [V6.3], **Restart Recovery Time** [V6.3], Possession, Tactical-Score Avg/Final, Status-Distribution) + `llm_kpis` (LLM-Calls, Latenz p50/p95/max, Parse-Error-Rate, Roles-Counter, Avg-Tokens).

**Wichtig:** Trace-Files sind gitignored, werden beim Boot **nicht** gelöscht, akkumulieren sich. Manuell aufräumen: `rm src/logs/*.jsonl`. Wenn `R2K_RUN_ID` nicht gesetzt ist, fallen beide Nodes auf `run_{timestamp}` zurück — Traces lassen sich dann nicht mit dem Console-Log korrelieren. Siehe [[7_03_CHEATPAGE_Tools_and_Utils]].

---

### Q17 [Team Mitglied]: Wie viele Samples soll der System-Prompt enthalten?
**User:** "Mehr Few-Shot-Beispiele = bessere KI? Oder stören sie?"

**Gem:** **Nein.** Die B-Studie (Phase 1, 2026-07-15, 11 Experimente × 3 Runs × 120s) hat das getestet. Ergebnis:

| Samples | Goals B:R | OOB% | Lat p50 | Fazit |
|---|---|---|---|---|
| 0 (nur Rules, B7a) | 0.0:2.0 | 0% | 320ms | **Totaler Ausfall** — leeres/degenerates JSON |
| **1 (B6a)** | **1.7:1.0** | 16.4% | **742ms** | **Sweet Spot** — bester Scorer |
| 3 (Baseline A) | 0.7:1.0 | 30.6% | 827ms | Mehr Varianz, mehr OOB |
| 6 (B6b) | 0.3:1.7 | 15.2% | 792ms | Diminishing returns |

**Forschungsschluss (RQ2):** Das 3B-Modell kopiert **ein** Muster; es lernt nicht von Diversität. Mehr Samples verwässern den Fokus und erhöhen die Latenz. **1 Sample ist V6.2-Default.**

**RQ1 (Rules vs. Samples):** Beide nötig. Ohne Samples (B7a) → leeres JSON. Ohne Rules (B7b) → 46% OOB (Bots verlassen das Feld). Samples liefern das **Format**, Rules die **Grenzen**.

**RQ3 (`--explain`):** Explain-Mode senkt OOB auf 1.9% durch explizites Reasoning, kostet aber +44% Latenz (1190ms vs. 815ms). Die konsolidierte V6.2 nutzt stattdessen expliziten "STAY INSIDE FIELD AT ALL TIMES"-Text im `rules_core.txt` — ähnliche OOB-Reduktion ohne Latenz-Kosten.

> [!warning] Hohe Varianz
> Within-Experiment OOB-Spread bis zu 50 Prozentpunkte über 3 Runs. 3 Runs geben nur
> **directional insight**. Für statistische Confidence sind 10+ Runs nötig (D8). Siehe [[7_04_SPECIFICATION_Prompt_Architecture]].

---

### Q18 [Team Mitglied]: Warum bewegt sich der Goalie kaum, obwohl die KI Befehle sendet?
**User:** "Goalie-Idle-Rate ist 80-100% in allen Experimenten. Ist das ein Prompt-Problem?"

**Gem:** **Nein, und nicht per Prompt fixbar.** Goalie-Idle ist eine **strukturelle Grenze**, kein Prompt-Problem.

**Root Cause:** Der `ollama_sandbox_bridge.py` PD-Controller verfolgt einen jitterigen ball-Y-Setpoint. Die `smooth_membership` + Low-Pass-Filter reagieren überempfindlich auf Ballpositionsrauschen. Ergebnis: Mikro-Oszillationen, der Goalie "bewegt sich" ohne echte Positionsfortschritte. Die KPI zählt das als Idle (<0.1m Bewegung).

**Status (V6.2, Phase 2a implementiert 2026-07-25):** Die Bridge nutzt jetzt **Smooth Blending** — 10 feldgrößen-relative `GOALIE_*`-Konstanten + `smoothstep()` für sanften Übergang zwischen Torlinie (Ball nah) und Angle-Block (Ball fern). 70% taktischer Override + 30% LLM-Einfluss. Deadband eliminiert Mikro-Oszillationen. Neue KPI `goalie_tactical_pct` unterscheidet "taktisch positioniert" von "feststecken" — der Goalie IST an der richtigen Position, bewegt sich nur nicht chasen. Die `goalie_idle_pct` bleibt hoch (Deadband hält Position), aber `goalie_tactical_pct` ist 100%. `test_non_functional.py` assertiert `goalie_tactical_pct >= 60%`.

**Implikation:** Goalie-Verhalten **NICHT** durch Prompt-Änderungen, Rollen-Deskriptionen oder Goalie-Positions-Parameter versuchen zu fixen. Die Lösung muss im Bridge-PD-Controller liegen — siehe v6.2 Phase 5.1 (Kalman-Filter → glatterer ball-Y-Setpoint → weniger PD-Jitter). Siehe [[7_04_SPECIFICATION_Prompt_Architecture]] §5.

---

### Q19 [Team Mitglied]: Wie baue ich den System-Prompt zusammen und wo leben die Fragments?
**User:** "Ich sehe kein `system_prompt.txt` im Repo. Wie wird der Prompt erzeugt?"

**Gem:** Es gibt **kein** statisches `system_prompt.txt` in der Versionierung. Es wird zur Boot-Zeit von `setup_r2k.py:111-136` aus Text-Fragmenten in `strategy/fragments/` zusammengesetzt — aber **nur für `dump_prompt.py` Dry-Runs**. Zur Laufzeit assembliert der `r2k_evaluator.py` den Prompt selbst (Dynamic Prompt Injection, V6.3 — siehe Q25).

**Boot-Zeit (nur `system_prompt.txt` für `dump_prompt.py`):**
```
header.txt          → ACT_ON_BOTS line + MODE line + {{EXPLAIN_INSTRUCTION}}
rules_core.txt      → Field Limits, Valid Actions, Strict Laws, Kick-In Exception
rules_{strat}.txt   → Strategie-spezifische Rules (OVERRIDES rules_{mode}.txt wenn vorhanden)
samples_{strat}.txt → Strategie-spezifische Samples (OVERRIDES samples_{mode}.txt wenn vorhanden)
```

**Laufzeit (Evaluator — V6.3 Dynamic Injection):** Der Evaluator liest `match_state.status` aus `Worldstate.json` und assembliert den Prompt basierend auf dem aktuellen Spielstatus:
```
header.txt              → immer
rules_core.txt          → immer
rules_ball_out.txt      → nur wenn status="ball_out" (ADDITIV zu rules_{mode}.txt)
rules_goal_kick.txt     → nur wenn status="goal_kick"
rules_corner_kick_in.txt→ nur wenn status="corner_kick_in"
rules_kickoff.txt       → nur wenn status="kickoff"
rules_{mode}.txt        → immer (IST die "playing"-Regel wenn status="playing")
samples_{mode}.txt      → immer
```
Game-Phase-Fragmente sind **additiv** — sie ersetzen nicht, sie ergänzen. Ollama ist stateless (sendet `system` per call), also kann der Prompt zwischen Calls wechseln. Gecacht pro `(status, mode)`-Tuple — File-Reads nur bei Status-Transition (<10/match).

**Rollen (V6.3):** 3 Rollen — `goalie`/`attacker`/`defender` (war 5: striker/midfielder/passer/receiver/supporter). Die Bridge prüft nur `role == 'goalie'`; alle anderen Rollen waren kosmetische Labels. `role_diversity` KPI wurde gedroppt (dead metric, CV=0%).

**Verifikation ohne ROS/Ollama:** `python3 tools/dump_prompt.py --scenario 3vs3_attack_center --strategy strat_default --no-explain` druckt den assemblierten Prompt + Per-Fragment-Breakdown + Token-Schätzung. Siehe [[7_04_SPECIFICATION_Prompt_Architecture]].

---

### Q20 [Team Mitglied]: Was sieht die KI wirklich und was wird ausgeblendet?
**User:** "Bekommt die KI die volle `Worldstate.json`? Oder eine reduzierte Sicht?"

**Gem:** **Reduziert.** `r2k_evaluator.py:88` strippt die Worldstate zu `min_ents` — ein flaches Dict von Entity-Positionen, gerundet auf 1 Dezimalstelle. Nur X/Y, nichts sonst.

**Was die KI sieht:** `{"blue_1": {"x": -1.5, "y": 0.3}, ..., "soccer_ball": {"x": 0.0, "y": 0.1}}`

**Was ausgeblendet wird:** `match_state` (Score, Status, Fouls, restart_team — **aber:** der Evaluator liest `match_state.status` für Dynamic Prompt Injection, siehe Q25), `tactical_score` (Momentum, Trend, Possession), `tactical_reward`, alle Yaw-Winkel, alle Geschwindigkeiten.

**V6.3 Dynamic Prompt Injection (ersetzt `R2K_INCLUDE_MATCH_STATE`):** Statt den `match_state` in den Prompt zu injizieren (B3-Experiment: keine Verbesserung — das 3B-Modell nutzt Game-State-Information nicht effektiv), wechselt der Evaluator jetzt den **gesamten System-Prompt** basierend auf `match_state.status`. Bei `status="ball_out"` wird `rules_ball_out.txt` additiv hinzugefügt. Der Prompt ändert sich, nicht die Eingabedaten. Siehe Q25.

**V6.3 Content-Hash Skip:** Der Evaluator hasht die Entity-Positionen (`min_ents` JSON) und überspringt den LLM-Call wenn identisch mit dem vorherigen Call. Bei `temperature: 0.0` → identischer Input → identischer Output → 64% der Calls waren verschwendet (171→62 pro Match). Effektive Latenz sinkt von ~1328ms auf ~684ms. Der Evaluator ist 64% der Zeit idle statt 100% beschäftigt. **[2026-08-01]** Caveat (gemessen): `temperature: 0.0` ist über KV-Cache-Zustände nicht bitt-exakt (Formatierung kann flippen, Semantik stabil) — siehe Q26.

**Staleness-Problem:** Die Positionen sind bis zu 100ms alt (Aggregator-Write) + **~684ms** effektive LLM-Latenz (V6.3, war ~800ms — Content-Hash-Skip halbiert die effektive Latenz) ≈ die KI entscheidet über eine ~0.8s alte Welt. Motiviert Phase 5.2 (Predictive World Model).

---

### Q21 [Weiterentwicklung]: Was ist die "Closed-Loop-Feedback-Lücke"?
**User:** "Ich höre, das World Model sei 'open-loop'. Was fehlt?"

**Gem:** **Definition:** Closed-Loop-Feedback bedeutet, ein System prüft, ob seine Befehle ausgeführt wurden, und korrigiert bei Abweichung. ROS2K ist heute **open-loop** in der Kognitionsschicht:

```
LLM sieht Welt → LLM gibt Befehl → Bridge führt aus → (KEINE Rückmeldung an LLM)
                                                            ↑
                                              Hier fehlt die Feedback-Schleife
```

**Konkret:** Die KI sendet `{"blue_2": {"action": "Move", "x": 1.5, "y": 2.0}}`. Ob `blue_2` das Ziel erreichte, ob der Bot auf dem Weg blockiert wurde, ob ein Foul ihn warpte — die KI erfährt es **nicht**. Sie sieht beim nächsten Call nur eine neue Position, aber ohne Kausalzusammenhang zu ihrem Befehl. Sie kann nicht zwischen "Befehl war schlecht" und "Befehl wurde gut erteilt, aber Ausführung scheiterte" unterscheiden.

**Nicht verwechseln mit Datei-I/O-Safety (Q8):** Die atomare `os.replace`-Schreibweise löst das Read/Write-Race. Das ist gelöst. Die **Entscheidungs-Rückkopplung** ist ungelöst.

**Warum das ein Problem ist:** Ohne Feedback kann die KI nicht lernen, dass z.B. ein Block-Pfaden-Weg blockiert ist, oder dass ein Move-Befehl an der Sideline ins Leere läuft. Sie wiederholt fehlerhafte Strategien, weil sie nicht weiß, dass sie fehlerhaft waren.

**Phase-5-Roadmap schließt die Lücke:**
* **5.1 Kalman Filter:** Geschwindigkeits-Schätzung → die KI kann Bewegung erkennen, nicht nur Positionen.
* **5.2 Predictive World Model:** Forward-Simulation um N ms → Kompensation der LLM-Latenz.
* **5.3 Deviation Watchdog:** Vergleicht prädizierte vs. tatsächliche Welt → erkennt Anomalien (Bots fliegen, Ball warpt, Befehl nicht ausgeführt).
* **5.4 Failsafe Fallback:** Wenn LLM-Latenz >5s oder Parse-Error-Rate >20% oder Watchdog kritisch → Blue schaltet auf regelbasiertes Verhalten (Mirror von `rule_evaluator_red.py`). System hängt nie, produziert nie gefährliche Befehle.
* **5.9 Temporal Reasoning:** Letzte N World-States im Prompt → KAI kann Bewegung inferieren.

**Read-Order-Empfehlung:** 5.3 + 5.4 zuerst (am billigsten, höchster Sicherheitsgewinn). 5.1 Kalman ist die Foundation und fixt zusätzlich das Goalie-Idle-Problem. Siehe `optimization_spec_v6.2.md` §7 Phase 5 und [[7_02_ARCHITECTURE_World_Model_Components]] §5.

---

### Q22 [Weiterentwicklung]: Was bedeutet "Threshold vs Hysterese vs Korridor vs Probability"?
**User:** "Ich sehe diese vier Konzepte im Code. Was ist der Unterschied?"

**Gem:** Vier Entwurfsmuster für Entscheidungslogik. ROS2K nutzt heute nur die ersten zwei voll:

| Konzept | Was es ist | Beispiel in ROS2K | Wann es scheitert |
|---|---|---|---|
| **Threshold** | Harte binäre Grenze | `PUSHING_DISTANCE_THRESHOLD=0.3m`, `BALL_PROXIMITY=0.8m` | Flicker an der Grenze; 0.29m=kein Foul, 0.31m=Foul jeden Frame |
| **Hysterese** | N aufeinanderfolgende Frames / Cooldown | `HYSTERESIS_FRAMES=3`, `DEBOUNCE_FRAMES=5`, `foul_cooldown=5s` | Addet Latenz; `last_toucher` verfällt nie (by Design — Kicker bleibt verantwortlich) |
| **Korridor** | Band mit gradiertem Wert | Momentum-Trend-Klassen (`ascending >2.0` … `collapsing <-2.0`), Goalie-Korridor x=-4.0, Boundary-Clamp ±0.5m normal / ±1.0m Restart | Weite Korridore maskieren Signal, enge Korridore werden spröde |
| **Probability** | Bayesianische Belief | **Nicht genutzt** — `temperature=0.0` ist deterministisch, kein Kalman, kein Occupancy | Voll crisp-System — Forschungslücke (Phase 5.1) |

**Lehrpunkt:** ROS2K heute = Threshold + Hysterese. Korridor nur im Scoring. Probability fehlt — das ist die Phase-5-Forschungsfront.

---

### Q23 [Weiterentwicklung]: Wenn jeder Team-Member einen eigenen GPU-PC hat, was ändert sich?
**User:** "Was ändert die Multi-GPU-Topologie an der Architektur?"

**Gem:** Jeder Member läuft den **vollen Stack isoliert** (eigener Gazebo headless + eigener Ollama + eigene `results/`). Vier Capabilities werden freigeschaltet, ein Merge-Problem entsteht:

| Capability | Was sie ermöglicht | Mappt auf |
|---|---|---|
| **Parallel Batch-Runs** | Phase 2 (27 Runs) und Phase 3 (135 Runs) aufgeteilt auf N Member → Wall-Clock ÷ N. Jeder Member besitzt einen Slice der Run-Matrix. | Phase 2c/3b |
| **Per-Bot LLM** | Eine GPU kann 3 parallele 3b-Calls laufen lassen (Goalie/Striker/Supporter) — Latenz bleibt ~800ms, nicht 3×. Jeder Bot bekommt rollenspezifischen Kontext. Passt perfekt zum isolierten Modell. | C5 / Phase 5.5 |
| **Größere Modelle (7b+)** | Besseres Soccer-Reasoning; Test ob 7b das 3b schlägt (D1 Model-Size-Scaling). Braucht das GPU-Budget. | D1, Phase 3 |
| **Unabhängige Reproduktion** | Jeder Member hat eigenen Headless-Gazebo+Ollama → kein Contention, keine Port/DDS-Kämpfe (gegeben distinct `ROS_DOMAIN_ID`). | Reproducibility |
| **Merge-Problem (das eine Shared-Concern)** | Aller `results/kpis_*.json` müssen in einem Dashboard landen. Offline-JSON-Merge — keine Live-Koordination nötig. | Phase 5.6 |

**Wichtiger Hinweis zu `OLLAMA_NUM_PARALLEL`:** Q10 erwähnt `OLLAMA_NUM_PARALLEL=1` als optionales Single-Call-Latenz-Tuning (nicht vom Startskript gesetzt). Für **3 parallele per-bot Calls** muss dieser Wert **≥3** gesetzt werden, sonst serialisiert Ollama sie. Ohne dieses Setting wird aus "parallelen 800ms" serielles 2400ms.

**`ROS_DOMAIN_ID`-Spannung:** Siehe Q12 V6.2-Warnung. Das hardcoded `ROS_DOMAIN_ID=0` (Axiom 4) kollidiert mit N Teilnehmern im selben LAN. Option (a) `launch_r2k.sh` patchen (respektiere vorgesetzten `ROS_DOMAIN_ID`), (b) getrennte VLANs, (c) Kollisionsrisiko akzeptieren. Siehe Workshop-Diskussion Module 5.

---

### Q24 [Team Mitglied]: Was ist die Shared Regression Suite und wie nutze ich sie?
**User:** "Wie stelle ich sicher, dass meine Code-Änderung nichts kaputt macht?"

**Gem:** Die **Shared Regression Suite** (`tests/test_non_functional.py`, V6.2 Phase 2b) ist ein Two-Tier-pytest-System:

| Tier | Kommando | Was läuft | Dauer |
|------|----------|-----------|-------|
| **Fast** | `pytest tests/ --skip-slow` | 91 Unit-Tests (Rule-Logic, Parsing, Set-Piece-Math) | ~2s |
| **Slow** | `pytest tests/ -v -s` | 91 Unit + reale 120s Gazebo-Matches mit KPI-Assertions | ~10min |

**Was ist ein pytest-Marker?** Ein Marker ist ein Metadaten-Label, das man an eine Test-Funktion hängt. Er ändert nicht, was der Test tut, sondern erlaubt Selektion/Filterung:

```python
@pytest.mark.slow
def test_attack_center_performance():
    ...
```

`@pytest.mark.slow` taggt die Funktion. Der Marker ist in `pytest.ini` registriert. Das Flag `--skip-slow` (implementiert in `conftest.py`) liest diesen Marker und überspringt alle Tests, die ihn tragen. Das ist der komplette Two-Tier-Mechanismus — ein Marker ist reine Metadaten für Selektion, keine Test-Bedingung oder Assertion.

**Composite Score (spec §5.2):** Jeder Slow-Test berechnet einen gewichteten KPI-Score:

```
composite = 0.4 * goal_diff_norm + 0.3 * tac_score_norm
          + 0.2 * possession_norm + 0.1 * latency_factor
```

Range [0, 1]. Höher ist besser. Gewichtung: 40% Tor-Differenz, 30% Tactical-Score, 20% Possession, 10% Latenz.

**Per-Szenario-Thresholds:** Jedes Szenario-Paket (`scenario/<name>/`) enthält eine `kpi_targets.json` mit akzeptablen KPI-Ranges. Der Test assertet, dass jeder KPI innerhalb seiner Szenario-spezifischen `[min, max]`-Range liegt. Die Thresholds sind kalibriert aus der v6.3 27-Run-Baseline (Phase 2.5d, commit `532360b`) mit 30-50% Margin.

**Wann was laufen:**
- Nach jeder Code-Änderung: `pytest tests/ --skip-slow` (Fast-Tier, ~2s Feedback-Loop)
- Vor Commit: `pytest tests/ -v -s` (Full-Tier, ~10min, fängt Regressionen)
- Einzelner Slow-Test: `pytest tests/test_non_functional.py::test_attack_center_latency -v -s`

Siehe [[7_03_CHEATPAGE_Tools_and_Utils]] §6.5 für Details.

---

### Q25 [Team Mitglied] [V6.3]: Was ist Dynamic Prompt Injection und wie funktioniert es?
**User:** "Der Evaluator wechselt den System-Prompt zur Laufzeit? Geht das ohne Restart?"

**Gem:** Ja. Ollama ist **stateless** — es sendet den `system`-Parameter bei jedem `/api/generate`-Call neu. Der Evaluator nutzt das, um den Prompt basierend auf `match_state.status` zu wechseln, ohne etwas zu restarten.

**Mechanismus (`r2k_evaluator.py`):**
1. Evaluator liest `Worldstate.json` alle 20ms → extrahiert `match_state.status`
2. `_assemble_prompt(status, mode)` baut den Prompt aus Fragmenten:
   - Statische Fragmente (immer): `header.txt`, `rules_core.txt`, `rules_{mode}.txt`, `samples_{mode}.txt`
   - Game-Phase-Fragmente (additiv, nur wenn status ≠ "playing"): `rules_{status}.txt`, `samples_{status}.txt`
3. Prompt wird pro `(status, mode)`-Tuple gecacht → File-Reads nur bei Status-Transition (<10/match)
4. Ollama bekommt den neuen `system`-Parameter im nächsten Call — kein State, kein Cache-Miss

**Warum nicht alles in einen Prompt?** Das 3B-Modell kann große Prompts schlecht verarbeiten (B-Studie: 1 Sample > 6 Samples). Game-Phase-Fragmente halten den Prompt fokussiert auf die aktuelle Situation. Bei `status="ball_out"` weiß der Prompt, dass ein Einwurf kommt — ohne dass der "playing"-Prompt mit Einwurf-Regeln überladen wird.

**4 minimale Game-Phase-Fragmente (V6.3 Phase 2.5c):** `rules_ball_out.txt`, `rules_goal_kick.txt`, `rules_corner_kick_in.txt`, `rules_kickoff.txt` (je 2 Zeilen). Fallback: wenn ein Game-Phase-Fragment fehlt, fällt der Evaluator auf den "playing"-Prompt zurück (kein Crash).

**Ersetzt `R2K_INCLUDE_MATCH_STATE`:** Statt `match_state`-Daten in den Prompt zu injizieren (B3-Experiment: keine Verbesserung — das Modell ignorierte sie), wechselt der Prompt selbst. Das ist wirkungsvoller: der Prompt *ist* kontext-aware, ohne dass das Modell Game-State-Daten parsen muss.

---

### Q26 [Team Mitglied] [V6.3]: Was ist der Content-Hash Skip und warum spart er 64% der LLM-Calls?
**User:** "Die KI wiederholt sich oft im Visualizer. Warum ruft sie Ollama so oft auf?"

**Gem:** Das war ein V6.2-Problem — der `state_aggregator.py` schreibt `Worldstate.json` bei 10Hz bedingungslos. 67% der Writes haben identische Positionen → `mtime` ändert sich → Evaluator triggert LLM-Call → identischer Input bei `temperature: 0.0` → identischer Output → 64% verschwendete Calls (153s GPU-Zeit pro Match).

**V6.3 Fix (`r2k_evaluator.py:259-266`):** Der Evaluator hasht die `min_ents`-Entity-Positionen (JSON-String) und überspringt den LLM-Call wenn der Hash identisch mit dem vorherigen Call ist. ~7 Zeilen Code.

**Impact:**
- ~62 Calls pro Match (war 171) — **64% weniger**
- Effektive Latenz (Situation ändert sich → Strategie-Output): **~684ms** (war ~1328ms)
- Der Evaluator ist 64% der Zeit **idle** statt 100% beschäftigt — er reagiert auf echte Änderungen innerhalb eines Poll-Cycles (~20ms) statt auf einen redundanten Call zu warten.

**Warum ist das safe?** `temperature: 0.0` ist deterministisch. Identische Positionen → identische Strategie. Es gibt keinen Grund, denselben Input zweimal an Ollama zu senden.

> [!warning] [2026-08-01] **Präzisierung:** `temperature: 0.0` ist über KV-Cache-Zustände hinweg NICHT bitt-exakt deterministisch (gemessen, Cache-Layout-A/B-Studie): byte-identischer Prompt + Optionen ergab unterschiedliche Token-Streams (Pretty- vs. Compact-JSON, 118 vs. 91 Tokens), abhängig von der Cache-Historie (frisches Prefill vs. gecachtes Präfix) — die Richtung drehte sich zwischen Testläufen sogar um. Reproduziert mit `OLLAMA_KV_CACHE_TYPE=q8_0` UND Default-f16 (llama.cpp-Cache-Reuse-Numerik, nicht KV-Quantisierung). Die **Semantik** bleibt stabil → der Content-Hash-Skip bleibt sicher. Aber: Latenz-A/B-Vergleiche müssen den Cache-Zustand kontrollieren (erst mit anderem World stören, dann beide Seiten vergleichen). `prompt_eval_count` ist KEIN Cache-Indikator (konstant trotz Hits) — `prompt_eval_duration` ist es (identische Calls: 68.9ms → 5.0ms → 3.8ms).

---

## Q25: Warum clusteren die Blue-Bots? (V6.4)

**A:** Das LLM produziert **korrekte, nicht-clusternde Targets** (blue_1 → -4.0, blue_2 → Ball, blue_3 → -2.7). Aber blue_1 bleibt physisch bei X=-2.6 "stecken" (PD-Controller zu schwach für 1.8m Rückkehr) und blue_3 wird nach -2.7 geschickt — genau wo blue_1 steckt. Sie clustern bei X≈-2.6, weil das LLM nicht weiß, dass blue_1 sein Ziel nicht erreicht.

**Fix:** Relative Positionierung statt fester Zonen. blue_3 geht nicht mehr nach "X=-2.0 to -3.0", sondern "maximiere Abstand von blue_1 und blue_2". Unabhängig davon, wo blue_1 steckt, geht blue_3 woanders hin. cluster_all fiel von 47% → 0-1%.

## Q26: Was ist der TeamCaptain? (V6.4, v7)

**A:** Ein geplanter CPU-only ROS2-Node (v7) zwischen Evaluator und Bridge. Er nimmt die LLM-Endpunkte und produziert optimierte Ausführungspläne (Waypoints, Geschwindigkeit, Ankunftswinkel). Auch: Multi-Bot-Koordination (keine Kollisionen), Watchdog (Odometrie-Vergleich → Failsafe), Augmented World Model (freie Wege, Sweet Spots → reicheres LLM-Input), Kick-Abort (Ball-Bewegungsänderung → K1 stoppt Chase). Siehe ADR-A07. Downward-kompatibel: Bridge fällt auf `current_strategy.json` zurück, wenn TeamCaptain inaktiv.

## Q27: Wie kalibriere ich Bots? (V6.4)

**A:** Zwei Wege: (1) `--demo` Flag in `launch_r2k.sh` lädt einen Demo-Prompt — Mensch tippt "blue_2 move to (1.0, 0.5)", LLM reformatiert zu Inter-Lingua, gleiche Pipeline wie Match-Modus. (2) `tools/calibrate_bot.py` (standalone, kein LLM) — JSON-Waypoints → cmd_vel/RPC direkt. Dual-Use: Workshop-Demos + Kalibrierung. JSON-Fallback funktioniert, wenn Ollama down ist.

## Q28: Der K1 folgt dem Ball endlos beim Kick — warum? (V6.4)

> **Korrektur 2026-08-28:** Die "autonome Verfolgung" unten ist eine
> **unbestätigte KB-intern Behauptung** — kein Vendor-Dokument und keine
> protokollierte Hardware-Session belegt sie. Laut offizieller Doku
> (docs.booster.tech) sind `Shoot()`/`VisualKick()` nur "firmware-configured"
> Aktionen ohne dokumentierte Autonomie; Shoots Bewegung ist aktuell
> T1-only (kann auf dem K1 fehlschlagen); `VisualKick` braucht Firmware
> ≥ v1.5.2.1. Das Verhalten MUSS per Hardware-Probe geklärt werden, bevor
> Abort-Code gebaut wird — siehe `docs/plans/v68_pre_ifa/k1_kick_head_vendor_audit.md`.

**A:** Die K1-Kick-Skills `kShoot` (api_id 2024) und `kVisualKick` (2038) sind **autonom** — der K1 übernimmt und jagt den Ball bis zur Kick-Distanz. Wenn der Ball wegrollt (selbst gekickt, Gegner, Ablenker), folgt der K1 endlos. Das ist ein Showstopper für echte Spiele. **Lösung (v7):** K1-Kamera erkennt Ball-Geschwindigkeits-/Richtungsänderung → ROS2-Topic → TeamCaptain/Bridge sendet `kChangeMode` (2000) → K1 stoppt Chase. Kein Threshold, keine Hysterese — "Ball bewegt → Abbruch".
