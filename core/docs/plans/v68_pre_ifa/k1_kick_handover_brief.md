# K1 Kick — Übergabe

**Stand 2026-09-28:** Relay-Kick-Kanal gebaut und auf dem K1 deployt
(2026-09-25). 3/5 Validierungs-Gates grün. Gate 5 (Terminal A sendet,
Terminal B empfängt) offen. Bridge, Evaluator und CLI noch nicht gebaut.

## Was gemacht wurde (2026-09-25)

**Relay-Kick-Bein** — `utils/ros2_relay/` erweitert um einen
`brain/Kick`-Pass-through-Kanal:

- Host-Publishes `/{prefix}/kick_ball` (brain/Kick) → external_relay →
  UDP 6003 → internal_relay → robot-lokales `/kick_ball` (dasselbe Topic,
  das der Vendor-Soccer-Agent abonniert).
- Keine RPC-Übersetzung im Relay — der Vendor-Controller IST der
  Kick-Ausführer.
- `brain`-Paket auf dem K1 gefunden (`/opt/booster/booster_agent_data/
  .../com.boosterobotics.soccer/agent/`), beide Service-Dateien sourcen
  dessen `local_setup.bash`.
- Auf den K1 (192.168.0.69) deployt via `deploy_relay.sh`, beide Services
  `active`.

**Design-Historie** (drei Iterationen, siehe kick_poc_status.md §"Design
history"): std_msgs/String → neues kick_ball.msg → bestehendes brain/Kick
als Pass-through (final — trivial auf der Robot-Seite, null colcon dort).

## Wo freitags stehen geblieben wurde

**Gate 5 — der Terminal-A→Terminal-B-Test:**

- Terminal A: `ros2 topic pub` aus dem Docker-Container auf `/Kev1n/kick_ball`.
- Terminal B: `ros2 topic echo /kick_ball` auf dem Roboter.
- Ergebnis: Terminal B zeigte nichts. Gate 4 (Host sieht das Topic) wurde
  übersprungen.

**Hauptverdächtiger:** DDS-Env-Mismatch zwischen dem Host-Container und
der Relay-Fleet-Seite (Domain-ID / RMW). Nächster Schritt: erst Gate 4
laufen lassen (`docker exec core_gazebo ... ros2 topic list | grep Kev1n`),
dann die DDS-Env beider Seiten vergleichen, dann `--times 5` statt
`--once` neu testen.

## Validierungs-Gates

| Gate | Status |
|---|---|
| 1 — Service-Health (journalctl) | ✅ |
| 2 — Kick.msg Typ-Identität (Robot ↔ Repo) | ✅ |
| 3 — Controller-Subscriber auf `/kick_ball` | ✅ (2 bare-DDS Vendor-Subscriber) |
| 4 — Host sieht `/Kev1n/kick_ball` | ⬜ übersprungen — zuerst nachholen |
| 5 — End-to-End Round-Trip (Terminal A→B) | ❌ offen — siehe oben |
| 6 — Live Kick (`power: 6.0`, Ständer) | ⬜ blockiert auf Gate 5 |

## Noch nicht gebaut (Steps 2–4)

- **Step 2 — Bridge:** `hw_kick` Action in `ollama_sandbox_bridge.py`
  (lazy `brain/Kick` Publisher auf `/Kev1n/kick_ball`, id-keyed one-shot,
  calib/demo-gated, Match-Modus unberührt bis GATE 0).
- **Step 3 — Evaluator + CLI:** `kick` / `kick stop` Fast-Path-Verben.
- **Step 4 — Tests + Doku:** Fast-Tier-Test, Cheat-Sheet-Sektion,
  Vokabular-Eintrag.

## Dateien für die Übergabe

**Status & Architektur (primär):**
- `docs/plans/v68_pre_ifa/kick_poc_status.md` — **das Hauptdokument**:
  Architektur-Diagramm, Gate-Ergebnisse, offene Issues, Steps 2–4,
  Design-Historie, geplantes Cheat-Sheet
- `docs/plans/v68_pre_ifa/k1_kick_head_vendor_audit.md` — GATE 0
  (Probe-Matrix, Vendor-Ground-Truth, die Folklore-Korrektur)
- `docs/plans/v68_pre_ifa/post_field_test_plan.md` — Phase 2.5 (K0–K4,
  ab Zeile 94)

**Code (gebaut, uncommittiert auf main):**
- `utils/ros2_relay/external_relay.py` — kick_callback + brain/Kick-Import
- `utils/ros2_relay/internal_relay.py` — UDP 6003 → `/kick_ball`
- `utils/ros2_relay/system/external-relay.service` — local_setup.bash
- `utils/ros2_relay/system/internal-relay.service` — dito
- `utils/ros2_relay/README.md` — kick_ball dokumentiert

**SDK-Header (für Step 2):**
- `src/booster/b1_loco_api.hpp` — API-Codes, RobotModes
- `src/booster/move_controller.hpp` — Vendor-Referenz-Geschwindigkeitsprofil

**Sicherheit / Betrieb:**
- `docs/plans/v7/laundry_list_k1_field_fixes.md` — Bremsen vor Live-Session
- `docs/plans/v68_pre_ifa/calib_validation_runbook.md` — §V11 Start-Haltung

## Vorgeschlagener Übergabe-Branch

```bash
git checkout -b handover/k1-kick-20260928
git add utils/ros2_relay/ docs/plans/v68_pre_ifa/kick_poc_status.md \
        docs/plans/v68_pre_ifa/k1_kick_handover_brief.md
git commit -m "handover: K1 kick POC — relay leg built, Gate 5 open"
git push -u origin handover/k1-kick-20260928
```

Enthält den gebauten Relay-Code + alle Status-/Plan-Dokumente. Die
übrigen uncommittierten Doku-Änderungen (FAQ, Cheat-Sheets, Overview)
bleiben auf main — sie sind nicht Kick-spezifisch.