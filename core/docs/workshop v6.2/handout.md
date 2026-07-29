---
title: "ROS2K v6.3 Workshop — Student Handout"
type: HANDOUT
tags: [workshop, handout, student, v6.2, v6.3]
last_modified: 2026-07-29
---

# ROS2K v6.3 Workshop — Student Handout

> Dieses Handout begleitet dich durch die 5 Module. Es enthält die Aufgaben,
> die Kommandos und Platz für deine Notizen. Die Antworten hat nur der
> Lecturer — du sollst sie selbst entdecken.
>
> **Du brauchst:**
> - Laptop mit NVIDIA GPU + Ollama (`qwen2.5-coder:3b`)
> - `R2K-HSL`-Repo geclont, `./install.sh` durchgelaufen
> - `cheatpage.md` (Befehle, KPIs, Szenarien — deine Referenz)
> - `part1_boot_ramp.pdf` + `part2_running_system.pdf` (Architektur-Diagramme)
> - `rqt_graph_mockup.png` (ROS2 Node Graph)
>
> Alle Kommandos laufen in `~/R2K-HSL/core`.

---

## Glossar — Fachbegriffe

Diese Begriffe tauchen in den Experimenten und Diagrammen auf. Wenn du
unsicher bist, schau hier nach.

| Begriff | Erklärung | Wo im Workshop |
|---------|-----------|----------------|
| **deque** | Double-ended queue. Ein Sliding-Window mit fester Länge — alte Einträge fallen hinten raus, neue kommen vorne rein. `deque(maxlen=300)` = letzte 300 World-States (30s bei 10Hz). | `score_node.py`, Modul 1 |
| **OLS (Ordinary Least Squares)** | Lineare Regression. Legt eine Gerade durch Datenpunkte, indem der quadrierte Abstand minimiert wird. Berechnet den Momentum-Trend (rising/falling/stable) aus dem Score-deque. | `score_node.py`, Modul 1 |
| **Staleness** | Die Verzögerung zwischen Messung (Tracker liest `/gazebo/model_states`) und Wirkung (Bridge bewegt den Bot). Aktuell ~800ms. Die KI entscheidet immer auf Basis einer leicht veralteten Welt. | Modul 2 |
| **min_ents** | Die reduzierte Welt, die die KI sieht: Entity-Namen + X/Y-Koordinaten gerundet auf 0.1m. Keine Velocity, kein `match_state`, kein `tactical_score`. | `r2k_evaluator.py:88`, Modul 2 |
| **Fragment** | Eine Textdatei in `strategy/fragments/` mit einem Teil des System-Prompts: Regeln, Beispiele oder Persona. Wird von `setup_r2k.py` beim Boot assembliert. | Modul 4 |
| **Oracle / Expert** | Menschgeschriebene Analyse-Texte pro Szenario. Oracle = strategisch (was taktisch passieren soll). Expert = technisch (was die KI ausgeben soll). Wird NICHT der KI gezeigt — für menschlichen Vergleich mit `--explain`-Output. | Modul 2, Modul 5 |
| **RPC (Remote Procedure Call)** | Ein Nachrichtenformat, bei dem der Sender einen Befehl als JSON-String in einer ROS2-Nachricht serialisiert. Der K1 nutzt `booster_msgs/RpcReqMsg` mit `api_id` 2001 (Move) oder 2000 (Failsafe). | Modul 3 |
| **num_predict** | Ollama-API-Parameter, der **wie viele Tokens das Modell generieren darf**. `--no-explain` → 150 (nur `assignments`). `--explain` → 600 (`analysis` + `oracle` + `assignments`). Wenn die Antwort das Limit überschreitet → JSON wird abgeschnitten → `fast_parse` schlägt fehl → kein `current_strategy.json` → totes blaues Team. | `r2k_evaluator.py:111`, Modul 1+4 |
| **Twist** | Standard ROS2-Nachricht für Geschwindigkeitskommandos (`geometry_msgs/Twist`): `linear.x` = Vorwärtsgeschwindigkeit, `angular.z` = Drehgeschwindigkeit. Sim-Bots und Yahboom nutzen Twist, der K1 nicht. | `ollama_sandbox_bridge.py`, Modul 3 |
| **tmpfs** | Dateisystem im RAM. `shared_state/` liegt auf tmpfs für atomare Schreib-/Lesezugriffe ohne Disk-I/O. `os.replace()` ist POSIX-atomar auf demselben Dateisystem. | `state_aggregator.py`, Modul 2 |
| **R2K_RUN_ID** | Env-Var, von `launch_r2k.sh` gesetzt: `{scenario}_{strategy}_{timestamp}`. Korrelations-Schlüssel für Trace-Dateien (`llm_trace_{run_id}.jsonl`, `world_trace_{run_id}.jsonl`). | `launch_r2k.sh:87`, Modul 2 |
| **Composite Score** | Gewichtung: `0.4×Tor-Diff + 0.3×Tactical-Score + 0.2×Ballbesitz + 0.1×Latenz-Faktor`. Ein einziger Wert zum Vergleich von Experimenten. ≥0.5 ist ein gutes Match. | `analyze_trace.py`, Modul 1+4 |
| **Cold-Boot-Race** | Beim ersten Match nach `ollama serve` lädt Ollama das Modell in VRAM (30-40s). Schließt du in dieser Zeit das Fenster → LLM-Prozess stirbt → kein Strategy-File → totes blaues Team. Zweites Match klappt (Modell ist warm). | Warm-up-Box oben, Modul 1 |
| **PID-Controller** | Proportional-Integral-Derivative-Regler im Bridge. Berechnet aus Distanz + Winkel zum Target die Geschwindigkeiten `lin_x` und `ang_z`. Ist nicht KI-gesteuert — die KI liefert nur den Zielpunkt, der PID fährt dorthin. | `ollama_sandbox_bridge.py:188-190`, Modul 1+2 |

---

## Warm up Ollama JETZT

Bevor wir starten: Ollama muss das Modell in VRAM laden. Beim ersten Match
nach `ollama serve` dauert das 30-40 Sekunden. Wenn du in dieser Zeit das
Fenster schließt, stirbt das blaue Team (kein Strategy-File wird geschrieben).

```bash
curl -s http://127.0.0.1:11434/api/generate \
  -d '{"model":"qwen2.5-coder:3b","prompt":"hi","stream":false}' > /dev/null
nvidia-smi  # sollte ~2-4GB VRAM zeigen
```

Das war's — jetzt ist das Modell warm. Alle folgenden Matches starten in ~4s.

---

## Wie man die Architektur-Diagramme liest

Du hast zwei Diagramme (A4, Seite-an-Seite legen):

- **Part 1 — Boot & Ramp Phase** (links): Was passiert beim `./launch_r2k.sh`
  Aufruf. CLI-Flags → `setup_r2k.py` assembelt Fragmente → Ollama-Check →
  Gazebo-Start → Node-Ignition. Unten stehen die Marks ①-⑤.
- **Part 2 — Running System** (rechts): Was läuft im Steady State. Gazebo →
  Tracker → Engine-Nodes → Aggregator → Evaluator ↔ Ollama → Bridge → Bots.
  Oben stehen dieselben Marks ①-⑤.

Die ①-⑤ Marks zeigen, wo Part 1 in Part 2 übergeht:
① Gazebo läuft · ② Bots gespawnt · ③ Ollama warm · ④ `system_prompt.txt` ready · ⑤ Relay+Scenario kopiert.

Leg beide Diagramme nebeneinander: Part 1 rechts unten → Part 2 links oben.

---

## Module 1 — Scoring-Ökosystem (40 min)

### Experiment 1: Stack verifizieren (5 min)

```bash
nvidia-smi                          # Ollama sollte ~2-4GB VRAM zeigen
curl -s http://127.0.0.1:11434/api/tags   # Ollama läuft?
cd ~/R2K-HSL/core
./launch_r2k.sh --headless --duration 30 --scenario 2vs2_default --relay only_sim_bots
```

**Probleme?**
- "Ollama not found" → `nohup ollama serve > /dev/null 2>&1 &`
- "Model not pulled" → `ollama pull qwen2.5-coder:3b`

### Experiment 2: Live Match mit Visualizer (10 min)

```bash
./launch_r2k.sh --scenario 3vs3_attack_center --relay only_sim_bots
```

**Worauf achten:**
- Momentum-Panel: Bewegt sich die Linie? Korreliert sie mit Toren?
- Referee-Zeilen: Erscheinen Set-Pieces? Ball-out → Kick-in?
- HUD: `Blue X : Y Red` — aktualisiert sich der Score?
- Goalie: Bewegt er sich? (Erwartet: meistens still — bekanntes Problem)

### Experiment 3: Sample-Count A/B (10 min)

```bash
./tools/run_experiment.sh A baseline 120 3vs3_attack_center strat_default --no-explain
python3 tools/analyze_trace.py --run-id <ID>
```

> `A` = Experiment-Name (Baseline). Output: `results/A_r1_summary.txt`,
> `results/A_r2_summary.txt`, `results/A_r3_summary.txt`. Siehe `cheatpage.md` §2.

**Deine KPIs:**

| KPI | Run 1 | Run 2 | Run 3 | Mittelwert |
|-----|-------|-------|-------|------------|
| `goals_for_blue` | _____ | _____ | _____ | _____ |
| `goals_for_red` | _____ | _____ | _____ | _____ |
| `cluster_pct` | _____ | _____ | _____ | _____ |
| `oob_pct` | _____ | _____ | _____ | _____ |
| `latency_p50` | _____ | _____ | _____ | _____ |
| `composite_score` | _____ | _____ | _____ | _____ |

**Persönliche Beobachtungen / Ideen für eigene Experimente:**
- ________________________________
- ________________________________

### Experiment 4: 10 Fehler in 10 Minuten (10 min)

```bash
git show 0566c11:core/src/ros2k_knowledge/ROS2K_GEM_FAQ.md | head -200
```

Finde 5 faktische Fehler im alten FAQ-Text, die nicht mehr stimmen. Tipp:
Vergleiche mit dem echten Code (`tracker_node.py`, `launch_r2k.sh`,
`ollama_sandbox_bridge.py`).

**Gefundene Fehler:**
1. ________________________________
2. ________________________________
3. ________________________________
4. ________________________________
5. ________________________________

> Siehe `cheatpage.md` §3 für alle 14 KPI-Definitionen.

### opencode ausprobieren (Modul 1)

```text
How does the referee detect a foul? Show me the threshold values.
```
```text
What does score_node.py momentum calculation do? Explain deque and OLS.
```
```text
Run a 60s headless match with scenario 3vs3_attack_center and show me the KPIs.
```
```text
The goalie is not moving. Check ollama_sandbox_bridge.py for how it handles
the goalie bot. Show me the PID control section.
```

### Key Take-Aways Module 1

- **Scoring ist ein 3-Node-System:** Referee (Fouls/Set-Pieces) → Score
  (Tactical + Momentum OLS über 30s) → Reward (1Hz, -10..+10). Alles fließt
  durch flat JSON, nicht durch ROS-Topics.
- **1 Sample schlägt 6 Samples:** Das 3B-Modell kopiert ein Muster, es lernt
  nicht aus Diversität. Mehr Samples verdünnen den Fokus und erhöhen die Latenz.
- **`--explain` senkt OOB auf 1.9%, kostet aber +44% Latenz** (600 statt 150
  Tokens). Nutze es für Debugging, nicht für Produktion.
- **Goalie idle ~95% ist strukturell:** Der Bridge-PID verfolgt ein ball-Y
  Setpoint, das ~800ms alt und jittery ist. Kein Prompt-Fix — Phase 5.1
  (Kalman) ist die Lösung.
- **KPIs sind deine Wahrheit:** `composite_score` fasst alles zusammen.
  Ohne `analyze_trace.py` fliegst du blind.

---

## Module 2 — World Model (35 min)

### Experiment 1: Was sieht die KI? (8 min)

```bash
python3 tools/dump_prompt.py --scenario 3vs3_attack_center --strategy strat_default --no-explain
cat shared_state/Worldstate.json | python3 -m json.tool
```

Vergleiche: `Worldstate.json` enthält `match_state`, `tactical_score`,
alle Entities. Aber `r2k_evaluator.py` reduziert auf `min_ents` (nur X/Y,
gerundet auf 0.1m).

**Was fehlt der KI?**
- ________________________________
- ________________________________
- ________________________________

> Siehe `part2_running_system.pdf`: Finde den "mtime poll 20ms" Pfeil zwischen
> `Worldstate.json` und `r2k_evaluator.py`.

### Experiment 2: Staleness messen (7 min)

```bash
ls logs/llm_trace_*.jsonl logs/world_trace_*.jsonl | head -4
# Wähle eine Run-ID, schaue die Timestamps an:
head -1 logs/llm_trace_<ID>.jsonl | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'LLM call at t={d[\"t\"]:.3f}')"
head -1 logs/world_trace_<ID>.jsonl | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'World at t={d[\"t\"]:.3f}')"
```

**Deine Messung:**
- World-Timestamp: _____
- LLM-Timestamp: _____
- Staleness (Delta): _____ ms
- Erwartet: 700-900ms (B-Studie p50: 742-827ms)

### Experiment 3: Oracle/Expert-Vergleich (12 min)

```bash
cat scenario/3vs3_attack_center/analysis.md
./launch_r2k.sh --headless --duration 60 --scenario 3vs3_attack_center --relay only_sim_bots --explain
```

Nach dem Match: LLM-Reasoning im `llm_trace` ansehen (`raw_response` enthält
`analysis` + `oracle` Keys). Vergleiche mit der menschlichen Oracle.

**Diskussion:**
- Stimmt das LLM-Reasoning mit der Oracle überein?
- Wenn KPIs gut sind, aber das Reasoning Unsinn ist — ist das eine echte Verbesserung?
- Wenn KPIs schlecht sind, aber das Reasoning sinnvoll ist — schlechter Prompt oder Varianz?

> Siehe `cheatpage.md` §4: Szenario-Liste mit Oracle + KPI-Targets.

### opencode ausprobieren (Modul 2)

```text
Read the latest world_trace file and tell me: how many frames, what was the
ball position at frame 100, and what was the match_state.status distribution?
```
```text
What does the LLM actually see? Show me the min_ents stripping in
r2k_evaluator.py and compare it to the full Worldstate.json.
```
```text
Why is the LLM producing empty JSON? Check the last llm_trace file for
parse errors.
```

### Key Take-Aways Module 2

- **Ground Truth = `/gazebo/model_states` only.** Kein `/odom`, kein TF2, kein
  IMU. Der Tracker extrahiert nur `position.x` und `position.y` — kein Yaw,
  keine Quaternionen. 2D reicht für Soccer-Taktik.
- **Die KI sieht eine reduzierte Welt:** `min_ents` = X/Y gerundet auf 0.1m.
  Kein `match_state`, kein `tactical_score`, keine Velocity. Was die KI nicht
  sieht, kann sie nicht nutzen.
- **Staleness ~800ms ist real:** Ball bei 2 m/s → Ball ist 1.6m weg von dort,
  wo die KI denkt. Das ist warum der Goalie stillsteht — er rennt zur Position
  von damals, nicht von jetzt.
- **Trace-Logging = Observability:** `llm_trace` (pro LLM-Call) +
  `world_trace` (pro 10Hz-Tick), korreliert via `R2K_RUN_ID`. 14 KPIs offline
  berechenbar. Ohne Traces kein Debugging.
- **Oracle/Expert = menschlicher Maßstab:** KPIs sagen OB die KI gut spielt.
  Oracle/Expert sagt WARUM. Du brauchst beides.

---

## Module 3 — K1-Anbindung & Thresholds (50 min)

### Experiment 1: Relay-Inspektion (8 min)

```bash
cat relay/only_sim_bots.json | python3 -m json.tool
cat relay/hardware_mirror.json | python3 -m json.tool
```

**Unterschied:**
- `only_sim_bots`: ________________________________
- `hardware_mirror`: ________________________________

> Siehe `rqt_graph_mockup.png`: Finde die `/cmd_vel` und `/LocoApiTopicReq` Topics.

### Experiment 2: Hysterese-Demo (12 min)

```bash
python3 -m pytest tests/test_foul_detection.py -v -s
```

Patche `HYSTERESIS_FRAMES=1` in `referee_node.py` (oder im Test), re-run.
Beobachte: Mehr Fouls erkannt (weniger Filterung = empfindlicher).

**Was macht Hysterese?**
- ________________________________

### Experiment 3: K1 mit opencode erkunden (10 min)

```text
How is the Booster K1 controlled? Show me the booster_msgs publishing code
in ollama_sandbox_bridge.py. What are API codes 2000 and 2001?
```

**K1 API-Codes:**
- 2001 = ________________________________
- 2000 = ________________________________

### Experiment 4: Korridor-Walk (8 min)

```bash
python3 -c "
import json, matplotlib.pyplot as plt
records = [json.loads(l) for l in open('logs/world_trace_<ID>.jsonl')]
scores = [r.get('tactical_score', {}).get('momentum_30s', 0) for r in records]
times = [r['t'] - records[0]['t'] for r in records]
plt.plot(times, scores)
plt.axhspan(-0.5, 0.5, alpha=0.2, color='gray', label='stable corridor')
plt.axhspan(0.5, 2.0, alpha=0.2, color='green', label='rising')
plt.axhspan(-2.0, -0.5, alpha=0.2, color='red', label='falling')
plt.xlabel('Time (s)'); plt.ylabel('Momentum 30s'); plt.legend()
plt.savefig('momentum_corridor.png')
"
```

### Threshold-Taxonomie

| Konzept | Erklärung | Wo in ROS2K? |
|---------|-----------|--------------|
| **Threshold** | Einzelwert-Vergleich (`if dist < 0.3`) | Referee: Distanz/Geschwindigkeit |
| **Hysterese** | Musste N Frames persistieren, verhindert Flackern | Referee: `HYSTERESIS_FRAMES=3` |
| **Korridor** | Akzeptabler Bereich (±0.5 = "stable") | Momentum-Trend-Klassifikation |
| **Probability** | Stochastische Konfidenz | Nicht verwendet |

### opencode ausprobieren (Modul 3)

```text
How is the Booster K1 controlled? Check the edge hardware power-file.
Show me the booster_msgs publishing code in ollama_sandbox_bridge.py.
What are API codes 2000 and 2001?
```
```text
Run a 30s headless match with --relay hardware_mirror and compare the
relay JSON mapping to what topics actually show up.
```

### Key Take-Aways Module 3

- **K1 nutzt ROS2, aber nicht Standard-Twist.** Custom `booster_msgs/RpcReqMsg`
  mit JSON-serialisiertem RPC: `api_id 2001` = Move (`vx, vy, vyaw`),
  `api_id 2000` = Failsafe. Topic-Name kommt aus `relay/hardware_mirror.json`.
- **Keine OOP HALs.** Die Bridge nutzt dynamische Thread-Closures (`def task`),
  keine `BaseBotDriver`-Vererbung. Das ist ein bewusstes Architektur-Axiom.
- **K1-Freeze ist sim-only.** Der Referee friert via `cmd_vel` Twist-zero ein,
  aber der K1 ignoriert `cmd_vel`. Set-Piece-Freeze funktioniert nur in Gazebo.
- **Threshold + Hysterese = ROS2K heute.** Threshold = Einzelwert-Vergleich,
  Hysterese = N-Frames-Persistenz gegen Flackern. Korridor = Momentum-Trend.
  Probability = nicht verwendet.
- **Relay-JSON ist die Hardware-Brücke.** `only_sim_bots` = alles virtuell.
  `hardware_mirror` = maps Bots zu echten Topics. Ohne Relay-Datei → Fallback
  ohne Hardware.

---

## Module 4 — Utils & Fragments (35 min)

### Die Iterations-Schleife

```
Fragment editieren → dump_prompt.py (verifizieren) → Match laufen lassen
→ analyze_trace.py (KPIs) → mit Baseline vergleichen → wenn besser: committen
```

> [!info] [NEW v6.3] Dynamic Prompt Injection
> Seit Phase 2.5b assembelt der Evaluator den Prompt **zur Laufzeit** aus
> Fragmenten — nicht mehr nur beim Boot. Der Prompt wechselt basierend auf
> `match_state.status`: bei `ball_out` wird `rules_ball_out.txt` additive
> hinzugefügt. `setup_r2k.py` schreibt `system_prompt.txt` beim Boot (für
> `dump_prompt.py`), aber der Evaluator liest es nicht mehr zur Laufzeit.
>
> **3 Rollen, nicht 5:** Seit 2026-07-28 nutzt das System nur noch
> `goalie`/`attacker`/`defender` (war: striker/midfielder/passer/receiver/
> supporter). Die Bridge prüft nur `role == 'goalie'`; alle anderen Rollen
> waren kosmetisch.
>
> **Content-Hash-Skip:** Der Evaluator überspringt LLM-Calls wenn sich die
> Entity-Positionen nicht geändert haben (64% weniger Calls pro Match,
> effektive Latenz ~684ms statt ~1328ms).

### Experiment 1: KPIs lesen (8 min)

```bash
python3 tools/analyze_trace.py --run-id <ID aus Module 1>
```

Schreibe die wichtigsten KPIs auf:
- `composite_score`: _____
- `oob_pct`: _____
- `cluster_pct`: _____
- `goalie_idle_pct`: _____
- `latency_p50`: _____
- `shots_on_goal`: _____ [NEW v6.3]
- `pass_completion_pct`: _____ [NEW v6.3]

> [!info] [NEW v6.3] Neue KPIs
> `shots_on_goal`, `shots_on_target`, `pass_completion_pct`,
> `restart_recovery_time_s` — gemessen via Join von `llm_trace` (Kick/Pass
> Actions) und `world_trace` (Ball-Positionen nach der Action).
> `role_diversity` wurde entfernt (war immer 3.0 nach Role-Condensation —
> keine Aussagekraft).

### Experiment 2: Fragment-Surgery (10 min)

```bash
python3 tools/dump_prompt.py --scenario 3vs3_attack_center --strategy strat_default --no-explain
# Editiere rules_core.txt — füge eine Regel hinzu (z.B. "ALWAYS pass to closest bot to goal")
python3 tools/dump_prompt.py --scenario 3vs3_attack_center --strategy strat_default --no-explain
./launch_r2k.sh --headless --duration 60 --scenario 3vs3_attack_center --relay only_sim_bots
python3 tools/analyze_trace.py --run-id <ID>
```

**Vergleich:**

| KPI | Baseline (Module 1) | Nach Edit | Delta |
|-----|---------------------|-----------|-------|
| `composite_score` | _____ | _____ | _____ |
| `oob_pct` | _____ | _____ | _____ |
| `cluster_pct` | _____ | _____ | _____ |
| `goals_for_blue` | _____ | _____ | _____ |
| `shots_on_goal` | _____ | _____ | _____ |

### Experiment 3: Replay — Match annotieren und abspielen [NEW v6.3] (10 min)

```bash
# Terminal 1: Match mit Annotator starten
./launch_r2k.sh --scenario 3vs3_attack_center --relay only_sim_bots --analyze

# Terminal 2 (öffnet sich automatisch): ENTER drücken um Gazebo zu pausieren
#   → Kommentar tippen → ENTER zum Fortsetzen. 'q' zum Beenden.
```

Nach dem Match — visuelles Replay mit Annotation-Navigation:
```bash
cd src
python3 r2k_visualizer.py --replay --nav
# f = nächste Annotation, b = vorherige, SPACE = Pause/Resume, q = Quit
```

Oder CLI-Review der Annotationen:
```bash
python3 tools/replay_trace.py          # letzte Match, interaktiv
python3 tools/replay_trace.py --all    # alle Annotationen als Text
```

**Pro Annotation siehst du:**
- Deinen Kommentar
- Die LLM-Decision direkt davor (assignments + analysis/oracle)
- Game-State (Score, Status, alle Bot-Positionen)
- Ball-Trajektorie für 5s nach der Annotation (Tore, Status-Wechsel)

**Deine Beobachtungen:**
- ________________________________
- ________________________________

### Experiment 4: opencode Fragment-Edit + Experiment (7 min)

```text
Edit rules_core.txt to add a rule: "ALWAYS pass to the bot closest to the
goal" if it's not already there. Then run dump_prompt.py to verify the prompt
includes the new rule.
```

```text
Run a 60s headless match with scenario 3vs3_attack_center and --no-explain,
then run analyze_trace.py on the result and show me the KPIs. Compare
goals_for_blue and cluster_pct to the baseline run from Module 1.
```

**Plan-Modus (Tab-Taste):**
```text
<Tab> "I want to add a new rule to rules_core.txt that prevents bots from
clustering. Show me a plan before making changes." <Tab> "Go ahead."
```

> Siehe `cheatpage.md` §1 (Launch-Flags), §2 (Test-Kommandos), §5 (Quick Recipes).

### Key Take-Aways Module 4

- **[NEW v6.3] Dynamic Prompt Injection:** Der Evaluator assembelt den Prompt
  zur Laufzeit aus Fragmenten, basierend auf `match_state.status`. Bei
  `ball_out` → `rules_ball_out.txt` wird additive hinzugefügt. Game-Phase-
  Fragmente sind ADDITIV zu Mode-Fragmenten (`rules_3vs3.txt`).
- **[NEW v6.3] 3 Rollen (goalie/attacker/defender):** War 5 Rollen, jetzt 3.
  Die Bridge prüft nur `role == 'goalie'`; alle anderen Rollen waren kosmetisch.
- **[NEW v6.3] Content-Hash-Skip:** 64% weniger LLM-Calls (171→62/Match).
  Effektive Latenz ~684ms (war ~1328ms). Bei `temperature: 0.0` → identische
  Input-Positionen → identischer Output → Call übersprungen.
- **Fragment-Assembly passiert beim Boot UND zur Laufzeit.** `setup_r2k.py`
  liest `fragments/` → schreibt `system_prompt.txt` (für `dump_prompt.py`).
  Der Evaluator assembelt zur Laufzeit direkt aus Fragmenten.
- **`dump_prompt.py` ist dein Pre-Flight-Check.** Zeigt den assemblierten
  Prompt ohne ROS/Ollama. Immer ausführen bevor du ein Match startest.
- **Die Iterations-Schleife ist manuell:** Fragment editieren → `dump_prompt`
  → Match → `analyze_trace` → KPIs vergleichen → wenn besser, committen.
  Kein automatischer Optimierer — Trial-and-Error mit pytest als Regressionsschutz.
- **[NEW v6.3] Replay-System:** `--analyze` öffnet Annotator-Terminal.
  `--replay --nav` spielt das Match ab mit f/b-Steuerung für Annotationen.

---

## Module 5 — Forschungs-Roadmap (45 min)

### Experiment 1: Make it your own (10 min)

```bash
./launch_r2k.sh --headless --duration 60 --scenario 3vs3_attack_center --relay only_sim_bots
python3 tools/analyze_trace.py --run-id <ID>
```

Das ist dein persönlicher Datensatz vom Workshop-Tag.

**Deine KPIs:**
- `composite_score`: _____
- `tactical_score_avg`: _____
- `ball_possession_blue_pct`: _____
- `shots_on_goal`: _____ [NEW v6.3]
- `pass_completion_pct`: _____ [NEW v6.3]
- `status_distribution`: _____

**Persönliche Beobachtungen / Ideen für eigene Experimente:**
- ________________________________
- ________________________________

### Experiment 2: Oracle/Expert mit --explain (10 min)

```bash
cat scenario/3vs3_attack_center/analysis.md
./launch_r2k.sh --headless --duration 60 --scenario 3vs3_attack_center --relay only_sim_bots --explain
```

Vergleiche das LLM-Reasoning (`analysis` + `oracle` im `llm_trace`) mit der
menschlichen Oracle aus `analysis.md`.

> [!info] [NEW v6.3] Explain-Mode repariert
> `--explain` war nach Phase 2.5b kaputt (dynamic injection umging
> `clean_json_samples()`). Jetzt gefixt via `R2K_EXPLAIN` env var +
> `{{EXPLAIN_INSTRUCTION}}` Placeholder. `num_predict` = 600 (explain) /
> 150 (no-explain). Explain kostet ~44% mehr Latenz pro Call, aber
> Content-Hash-Skip reduziert die Anzahl Calls.

**Hat die KI richtig gedacht?**
- ________________________________
- ________________________________

### Experiment 3: Replay mit Annotationen [NEW v6.3] (10 min)

```bash
# Match mit Annotationen aufzeichnen
./launch_r2k.sh --scenario 3vs3_attack_center --relay only_sim_bots --explain --analyze
# Im Annotator-Terminal: ENTER → Kommentar → ENTER (wiederholen)
```

Nach dem Match — visuelles Replay mit Step-Through:
```bash
cd src
python3 r2k_visualizer.py --replay --nav --speed 3
# f = nächste Annotation (pausiert automatisch)
# b = vorherige Annotation
# SPACE = Resume
# Im Visualizer: Note-Panel oben rechts, gelbe Diamanten im Momentum-Panel
```

**Fragen:**
- Stimmen die LLM-Entscheidungen an den annotierten Stellen mit deiner
  Einschätzung überein?
- Wo hat die KI das Spiel gedreht (Momentum-Knick im Panel)?
- Gibt es Timestamps, wo die KI gar nichts getan hat (Content-Hash-Skip)?

### Phase 5 — Forschungsrichtungen

| Richtung | Was | Status |
|----------|-----|--------|
| 5.1 Kalman-Filter | Noise filtern, Velocity schätzen. Goalie-Idle-Fix. | Geplant |
| 5.2 Predictive World Model | Welt ~684ms vorhersagen → Latenz kompensieren | Geplant |
| 5.3+5.4 Watchdog + Failsafe | Predicted vs. Actual vergleichen → Rule-based Fallback | Geplant |
| 5.5 Sim-to-Real | Auf K1/Yahboom-Hardware testen. Replay-System verfügbar (`--analyze`). | Geplant |
| 5.10 5vs5 Scale-Up | 5 Bots, ~~mehr Rollen~~ 3 Rollen + Spatial Split, größere Prompts | Geplant |
| 5.11 LLM-Output-Quality | Automated LLM-as-judge für Reasoning-Quality | Geplant |

> [!info] [NEW v6.3] Aktuelle Latenz
> Effektive Latenz (Situation-Change → Strategy-Output) ist jetzt ~684ms
> (war ~1328ms vor Content-Hash-Skip). Per-Call-Latenz bleibt ~777ms p50.
> Phase 5.2 (Predictive Model) muss nur noch ~684ms kompensieren, nicht ~1328ms.

**Welche Richtung interessiert dich für ein Praktikum / Studienprojekt?**
- ________________________________
- ________________________________

### opencode ausprobieren (Modul 5)

```text
Run a 60s headless match with scenario 3vs3_attack_center and --explain,
then extract the LLM's analysis and oracle fields from the llm_trace and
compare them to the oracle text in scenario/3vs3_attack_center/analysis.md.
```
```text
Explain the Phase 5.1 Kalman filter plan. Where in tracker_node.py would
it be implemented? Show me the current code that would need to change.
```
```text
How does the content-hash skip work in r2k_evaluator.py? Show me the
hashing code and explain why it saves 64% of LLM calls.
```

### Key Take-Aways Module 5

- **Phase 5 ist Forschung, nicht Implementiert.** Alles hier ist geplant.
  Sage "wir planen", nicht "wir haben". Keine Features als existent präsentieren.
- **Kalman-Filter (5.1) ist der Enabler.** Filtert Noise, schätzt Velocity,
  behebt Goalie-Idle. Ohne 5.1 kein 5.2 (Predictive World Model).
- **[NEW v6.3] Predictive World Model (5.2) kompensiert ~684ms** (war ~800ms).
  Content-Hash-Skip halbiert die effektive Latenz. Der Predictor muss nur
  noch die halbe Strecke überbrücken — Value-Prop reduziert, aber nicht null.
- **Watchdog + Failsafe (5.3+5.4) = Sicherheit.** Predicted vs. Actual
  vergleichen → bei Divergenz → rule-based Fallback.
  **[NEW v6.3] Achtung:** Content-Hash-Skip macht `current_strategy.json`
  mtime unzuverlässig als Staleness-Indikator — Failsafe muss auf
  `llm_trace`-Records prüfen, nicht auf File-mtime.
- **Sim-to-Real (5.5) ist der Endtest.** `--relay hardware_mirror` auf
  K1/Yahboom. **[NEW v6.3]** Replay-System verfügbar: `--analyze` für
  Live-Annotationen, `--replay --nav` für Post-Match-Review.
- **5vs5 (5.10) ist offen:** Schafft das 3B-Modell 5-Bot-Koordination mit
  ~~mehr Rollen~~ **[NEW v6.3]** 3 Rollen (goalie/attacker/defender) +
  Spatial Split? Oder braucht es 7B? Höhere Latenz bei 5 Assignments.

---

## Wenn etwas schiefgeht

| Problem                                   | Fix                                                                                                                            |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| Ollama nicht erreichbar                   | `pkill -9 -f "ollama runner"; pkill -9 -f "ollama serve"; sleep 2; nohup ollama serve > /dev/null 2>&1 &; sleep 3; nvidia-smi` |
| Blaues Team bewegt sich nicht (dead blue) | `ls logs/llm_trace_*_<run_id>.jsonl` — wenn Datei fehlt: Cold-Boot-Race. Match neu starten (Modell ist jetzt warm). **[NEW v6.3]** Auf U24 (Docker): Ollama muss auf `0.0.0.0` lauschen, nicht `127.0.0.1` — siehe `install.sh` systemd override. |
| Gazebo startet nicht                      | `ros2 run r2k_world_model tracker` in anderem Terminal prüfen. Docker: `docker ps` — Container läuft?                          |
| `parse_error_rate` hoch                   | `num_predict` zu niedrig? Versuche `--explain` (600 Tokens statt 150). Siehe `cheatpage.md` §3.                                |
| **[NEW v6.3]** Annotator: "ros2 not available" | Container läuft nicht oder `PROJECT_NAME` nicht gesetzt. Auf U24: `launch_r2k.sh --analyze` öffnet Annotator erst NACH Container-Start. |
| **[NEW v6.3]** Replay: alle Timestamps zeigen t=0.0s | Sim-time (`/clock`) nicht verfügbar — `libgazebo_ros_init.so` noch nicht im Container gebaut. `replay_trace.py` nutzt `t_wall` als Fallback (Wall-Clock). Baut mit: `docker exec core_gazebo bash -c "cd /workspace/ros2_ws && rm -rf build install && colcon build"` |

---

## Wo finde ich was?

| Was                                            | Wo                                    |
| ---------------------------------------------- | ------------------------------------- |
| Launch-Flags (`--scenario`, `--explain`, `--analyze`, etc.) | `cheatpage.md` §1                     |
| Test-Kommandos (`pytest`)                      | `cheatpage.md` §2                     |
| 18 KPI-Definitionen                            | `cheatpage.md` §3                     |
| 10 Szenarien + Oracle + KPI-Targets            | `cheatpage.md` §4                     |
| Quick-Test-Rezepte (Smoke test, etc.)          | `cheatpage.md` §5                     |
| Dateipfade (wo liegen die Files?)              | `cheatpage.md` §6                     |
| Architektur-Übersicht (Boot)                   | `part1_boot_ramp.pdf`                 |
| Architektur-Übersicht (Runtime)                | `part2_running_system.pdf`            |
| ROS2 Node Graph                                | `rqt_graph_mockup.png`                |
| Referee-Regelwerk (alle Entscheidungen)        | `core/docs/referee_rulebook.md`       |
| Optimierungs-Spec (Phasen 0-5)                 | `core/docs/optimization_spec_v6.3.md` |
| **[NEW v6.3]** Replay: Match annotieren        | `tools/match_annotate.py`             |
| **[NEW v6.3]** Replay: CLI-Review              | `tools/replay_trace.py`               |
| **[NEW v6.3]** Replay: Visuelles Playback      | `r2k_visualizer.py --replay --nav`    |
| opencode starten                               | `cd ~/R2K-HSL/core && opencode`       |