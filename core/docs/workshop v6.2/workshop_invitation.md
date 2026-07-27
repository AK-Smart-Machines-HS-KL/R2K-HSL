---
title: "ROS2K v6.2 Team Workshop — Einladung"
type: INVITATION
tags: [workshop, invitation, team, v6.2]
last_modified: 2026-07-22
---

# ROS2K v6.2 Team Workshop

> **Wann:** [Datum TBD] · **Dauer:** ~3,5 Stunden (Halbtages-Workshop)
> **Wo:** [Ort TBD] · **Mitbringen:** Eigener Laptop mit GPU + Ollama

## Was lernt ihr?

Dieser Workshop gibt euch einen vollständigen Überblick über die ROS2K-v6.2-
Architektur — vom Scoring-System über das Weltmodell bis zur Hardware-Anbindung.
Jeder Teilnehmer arbeitet auf seinem eigenen GPU-Rechner und führt echte
Experimente durch. Alle Beispiele laufen lokal auf eurem Laptop (localhost).

## Die 5 Module

**Module 1 — Scoring-Ökosystem (40 min)**
Wie Score, Momentum, Reward und Referee zusammen ein geschlossenes System
bilden. Warum 1 Sample besser ist als 6. Warum `--explain` OOB auf 1.9% senkt
aber 44% langsamer ist. Warum der Goalie ~95% der Zeit stillsteht (staleness +
jittery ball-Y setpoint im Bridge PID). Szenario-Packages mit Feld-Diagrammen
und oracle/expert-Analyse.

**Module 2 — World Model (35 min)**
Was die KI sieht und was verborgen bleibt. Warum wir nur X/Y-Koordinaten
nutzen (kein Yaw, keine Quaternionen). Wie die ~800ms LLM-Latenz die
Entscheidungen veraltet ("staleness"). Wie Trace-Logging uns 14 KPIs liefert.
Oracle/expert-Vergleich: Stimmt das LLM-Reasoning mit der menschlichen
Einschätzung überein?

**Module 3 — K1-Anbindung & Thresholds (50 min)**
Wie der Booster K1 über ROS2 gesteuert wird (custom `booster_msgs/RpcReqMsg`,
nicht Standard Twist). Welche Anti-Patterns wir vermeiden. Der Unterschied
zwischen Threshold, Hysterese, Korridor und Probability — und wo ROS2K heute
nur die ersten zwei nutzt.

**Module 4 — Utils & Fragments (35 min)**
Wie ihr eigene Experimente baut: Prompt-Fragmente editieren, Matches headless
laufen lassen, 14 KPIs messen mit `analyze_trace.py`. Das Referee-Regelwerk
als Source of Truth. `dump_prompt.py` zum Prompt-Inspektieren ohne ROS.
`opencode` als AI-gestützter Development-Assistent. `run_experiment.sh`:
der erste Parameter ist der Experiment-Name (`A` = Baseline, `B1`–`B7b` =
Varianten aus der B-Studie) — er bestimmt die Output-Dateinamen
(`results/A_r1_summary.txt`, etc.).

**Module 5 — Forschungs-Roadmap (45 min)**
Die Phase-5-Forschungsrichtungen aus `optimization_spec_v6.2.md`: Kalman-Filter
für weniger Noise + Velocity-Schätzung, Predictive World Model gegen Latenz,
Watchdog + Failsafe, Sim-to-Real auf K1-Hardware, 5vs5-Scale-Up, LLM-Output-
Quality-Evaluation. Plus ein praktischer "Make it your own"-Spike.

## Voraussetzungen

- Laptop mit NVIDIA GPU + installiertem Ollama (`qwen2.5-coder:3b`)
- ROS 2 Humble + Gazebo (Ubuntu 22.04 nativ oder 24.04 via Docker)
- `R2K-HSL`-Repo geclont und `./install.sh` durchgelaufen
- Keine ROS 2 Expertenkenntnisse nötig — Grundlagen reichen

## Was ihr mitnehmt

- Verständnis der v6.2-Scoring- und Referee-Architektur
- Fähigkeit, eigene Prompt-Experimente zu bauen und zu messen
- Kenntnis der K1-Hardware-Grenzen und Anti-Patterns
- Einen eigenen KPI-Datensatz vom Workshop-Tag
- Überblick über die Phase-5-Forschungs-Roadmap

---

*Anmeldung bis [Datum TBD] bei [Kontakt TBD].*
*Plätze begrenzt — jeder Teilnehmer braucht einen eigenen GPU-Rechner.*