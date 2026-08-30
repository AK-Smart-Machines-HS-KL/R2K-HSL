# Lab Session — Trello Cards (Pre-IFA)

> [!info] Zweck
> Detaillierte Ausführung der Lab-Aufgaben als Trello-Quelle. Muster wie
> `student_projects_autumn_fair.md`: **jeder Abschnitt zwischen den `---`
> Trennern = eine Karte** kopieren. Summary-Tabelle am Ende für das Board.
> Einzelquelle: `LAB_SESSION.md` bleibt die Agenda (Zeitboxen, Reihenfolge);
> dieses File enthält die Schritt-für-Schritt-Ausführung je Karte.
> Titel-Prefix **„Pre-IFA:"** markiert den Scope auf dem Board.

---

## Pre-IFA: Lab-Vorbereitung (Checkliste)

**Ziel:** Session startet ohne Unterbruch. **Zeit:** 10 min vor Ort.

- [ ] Beide K1 Education: Akku > 50 % (App oder Terminal), Gelenke/Kamera sichtbar OK
- [ ] Yahboom bot1: Akku geladen, Hotspot 10.42.0.x erreichbar (`ping 10.42.0.122`)
- [ ] Safety-Stand für K1-Kick-Probes aufgebaut; Spotter eingewiesen; E-Stop-Position bekannt
- [ ] 3 Ball-Kandidaten bereit; Boden-Marker (Klebeband) + Maßband
- [ ] 5090-Laptop: Bridge/Evaluator/Gazebo bereit; SSH zu beiden K1s geprüft
- [ ] `bash core/tools/start_ollama.sh --ensure` (selbstheilend — silent = OK)
- [ ] `LAB_SESSION.md` (Agenda) + `SESSION_CHANGELOG.md` zum Loggen offen

---

## Pre-IFA: Firmware-Probe K1 (beide Roboter)

**Ziel:** Firmware/SDK-Stand kennen →决定 Kick-Strategie. **Zeit:** 5 min.

1. `ssh booster@10.42.0.122` (zweiter K1: dessen IP)
2. `booster-cli version` → erwartet: `Firmware: 1.x.x` + `SDK: 1.3.x`
3. Beide Nummern ins Changelog.

**Gates:**
| Ergebnis | Konsequenz |
|---|---|
| fw ≥ 1.5.2.1 | VisualKick verfügbar → Karte „VisualKick-Probe" fährt |
| fw ≥ 1.6 | RoboCup-Module post-IFA möglich |
| fw < 1.5.2.1 | Kick-Work post-IFA; Demos laufen ohne Kick-Skill |

---

## Pre-IFA: Head-Smoke-Test (2004 in WALKING?)

**Ziel:** Klären, ob `kRotateHead` (2004) im kWALKING-Modus (stehend) ausgeführt wird. **Zeit:** 10 min.

1. K1: DAMP → PREP (**5 s warten!**) → WALK
2. WALK stehend — RPC 2004, halbe Range zuerst (~29° yaw):
   ```
   ros2 topic pub /Kev1n/LocoApiTopicReq booster_msgs/msg/RpcReqMsg \
     "{header: \"{api_id: 2004}\", body: \"{\\\"pitch\\\": 0.0, \\\"yaw\\\": 0.5}\"}" --once
   ```
3. Kopf bewegt sich? → Rückführung: `yaw: 0.0`
4. Keine Bewegung in WALKING → in PREP wiederholen (Fallback-Pfad für Demo bestätigt)
5. Limits (Vendor-Spec): yaw ±59° (±1.03 rad), pitch −19°/+49° (−0.33/+0.86 rad)

**Pass:** sichtbare Kopfbewegung; akzeptierter Modus (WALKING oder PREP) dokumentiert.

---

## Pre-IFA: Dry-Run a — Face/Yaw + say-yes/no

**Ziel:** Demo a end-to-end auf Hardware. **Zeit:** ~10 min.

1. `./launch_r2k.sh --demo --no-visualizer --scenario 1vs0_waypoint --relay hardware_mirror`
2. Zweites Terminal: `python3 core/tools/calib_cli.py`
3. `look left` → K1 via 2004, Yahboom via /<ns>/servo_s1 (blue_1/blue_2) — erwartete Drehung ~30°, Sim-Twin sichtbar
4. `say yes` → Pitch-Oszillation ~3× ±20° (K1: 2004-Sequenz; Yahboom: servo_s2)
5. Problem → Notiz (Demo / Fehler / Fix-Kandidat), zweiter Lauf

**Pass:** beide Bots zeigen Head-Bewegung synchron zum Sim-Twin; kein Mode-Fehler.

---

## Pre-IFA: Dry-Run b — FAKE + LIDAR Kick

**Ziel:** Demo b end-to-end. **Zeit:** ~10 min.

1. FAKE: Ball auf (1,0) tape-markiert; LIDAR-Variante: Ball beliebig im vorderen Halbraum
2. calib_cli: `kick ball`
3. `hardware_mirror`: Yahboom-Push + K1-Walk-Push **gleichzeitig** (Sim-Twin läuft mit)
4. Beobachten: Simultanität, Ball-Kontakt, K1-Stabilität beim Kontakt

**Pass:** Ball rollt, kein Sturz, simultane Bewegung beider Hardware-Klassen.

---

## Pre-IFA: Dry-Run d — Trailer (0° Push / 45° Rotation)

**Ziel:** Frame-Manipulation per Wegpunkt-Choreografie. **Zeit:** ~15 min. (Frame ist gebaut, Drehmoment getestet.)

1. Gabel offen, Yahboom 0,5 m davor; Startposition + Ziellinie tape-markiert
2. 0°-Anfahrt: gerade in die Gabel → Push → Rückzug (Frame translatiert auf Rollen)
3. 45°-Anfahrt: diagonaler Kontakt → Frame rotiert **clockwise** (−45° = CCW)
4. Wdh. mit Detektion (Karte „Trailer-LIDAR") statt fester Startpose

**Pass:** Frame rollt frei, Rotation sichtbar, Gabel bleibt geführt (kein Entgleisen).

---

## Pre-IFA: Ball-Pick (3 Größen × 3 Distanzen)

**Ziel:** kleinsten zuverlässig erkannten Ball + Size-Gate-Kalibrierung. **Zeit:** 15 min.

- Matrix: 3 Ball-Größen × 1 m / 2 m / 3 m vor dem Yahboom
- Pro Zelle: `/scan`-Cluster sichtbar? erkannter Chord vs. wahrer Durchmesser
- Optional K1-Kamera-Pfad, falls Stream steht

| Größe | Distanz | Cluster ja/nein | gemessener Chord | wahrer Ø |
|---|---|---|---|---|
| S/M/L | 1/2/3 m | | | |

**Pass:** kleinste zuverlässig erkannte Größe dokumentiert → Size-Gate-Konstante für den Ball-Detektor.

---

## Pre-IFA: Kalibrier-Muster (Gerade + Rotation)

**Ziel:** erste Drift-Daten (commanded vs odom vs tape). **Zeit:** 15 min.

- Gerade 2 m ×5 @ 0,5 m/s: Startmarker → Fahrt → Endabweichung messen (lateral + longitudinal, cm)
- Rotation 360° ×5: Zehenmarker → Heading-Fehler (Grad)
- Mit implementiertem `calib_cli --odom`: CSV pro Lauf; sonst manuelle Tabelle:

| Lauf | commanded (m bzw. rad) | odom | tape-gemessen |
|---|---|---|---|
| 1..5 | | | |

**Pass:** vollständige Tabelle (5+5 Läufe) → Drift-Faktoren für die Cure-Ladder.

---

## Pre-IFA: VisualKick-Probe (conditional, fw ≥ 1.5.2.1)

**Ziel:** Folklore „chase forever" durch Messung ersetzen. **Zeit:** 15 min. **Nur wenn Karten 1-8 grün.**

K1 am Stand, Ball ~0,5 m voraus:
1. RPC 2038 `{"start": true, "version": 0}` (V1) → Bewegung? Termination?
2. `version: 1` (V2, stärker) → Kraftunterschied?
3. **Ball-Wegroll-Experiment:** Kick triggern, Ball wegschieben → jagt der K1 endlos oder terminiert er? (DER Folklore-Test)
4. RPC 2024 (Shoot) → erwarte `StateTransitionFailed` (Vendor: „configuration-dependent, no model-name gate"); exaktes Ergebnis protokollieren
5. Abort: RPC 2000 `{"mode": 1}` mid-Skill → stoppt der Skill?

Alle Ergebnisse → v7 Kick-Abort-Design (`k1_kick_head_vendor_audit.md`, Sektion 'Hardware probe protocol').

---

## Pre-IFA: Nachbereitung (Changelog + Results)

**Zeit:** 5 min.

- [ ] SESSION_CHANGELOG-Eintrag: alle Zahlen (fw, 2004-Modus, Demo-Status, Ball-Größe, Kalibrier-Tabelle, VisualKick-Ergebnisse)
- [ ] `LAB_SESSION_RESULTS_<datum>.md` neben diesem File: Roh-Tabellen
- [ ] `PLANS_v6_v7_overview.md`: Zeilen 10-17 Status updaten

---

## Board-Summary (Spaltenvorschlag)

| Karte | Board-Spalte |
|---|---|
| Lab-Vorbereitung | Vorbereitung |
| Firmware-Probe | Probes |
| Head-Smoke-Test | Probes |
| Dry-Run a / b / d | Dry-Runs |
| Ball-Pick | Messung |
| Kalibrier-Muster | Messung |
| VisualKick-Probe | Probes (conditional) |
| Nachbereitung | Nachbereitung |
