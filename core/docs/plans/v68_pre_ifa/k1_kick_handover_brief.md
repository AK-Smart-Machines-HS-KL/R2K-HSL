# K1 Kick — Übergabe

**Stand 2026-10-05:** Relay-Kick-Kanal gebaut, auf dem K1 deployt
(2026-09-25) und End-to-End validiert (2026-10-01). 5/6 Validierungs-Gates
grün (Gate 6 = Live-Kick, via `GoToBallAndKick.py` bereits getestet).
Step 2 (Bridge `hw_kick`) implementiert (2026-10-05). Step 3 (Evaluator +
CLI) und Step 4 (Tests + Doku) noch offen.

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

## Wo freitags stehen geblieben wurde → nachgeliefert 2026-10-01

**Gate 4+5 nachgeliefert (2026-10-01):**

- Gate 4: `ros2 topic list` auf nativem U22 zeigt `/Kev1n/kick_ball`;
  `ros2 topic info` bestätigt 1 Subscription (external_relay). ✅
- Gate 5: `ros2 topic pub --times 5` von nativem U22 → 4/5 Nachrichten
  empfangen auf `ros2 topic echo /kick_ball` auf dem K1. ✅
- Root cause für den ursprünglichen Fehlschlag: Publish lief aus
  `docker exec core_gazebo` (DDS-Env-Mismatch). Nativer U22-Publish
  funktioniert; U24/Docker noch nicht vollständig getestet — **nicht**
  als nicht-funktionierend einstufen.

> [!note] brain-Source auf dem K1
> Für manuelle SSH-Sessions: `source /opt/booster/booster_agent_data/
> data/agents/extract/com.boosterobotics.soccer/agent/local_setup.bash`
> ausführen, sonst kann `brain/msg/Kick` nicht aufgelöst werden.

**Nächster Schritt:** Gate 6 — Live-Kick (`power: 6.0`, K1 auf dem Ständer,
Abort `kick stop` / RPC 2038 `{"start": false}` bereit).

## Validierungs-Gates

| Gate | Status |
|---|---|
| 1 — Service-Health (journalctl) | ✅ |
| 2 — Kick.msg Typ-Identität (Robot ↔ Repo) | ✅ |
| 3 — Controller-Subscriber auf `/kick_ball` | ✅ (2 bare-DDS Vendor-Subscriber) |
| 4 — Host sieht `/Kev1n/kick_ball` | ✅ (2026-10-01, nativer U22) |
| 5 — End-to-End Round-Trip (Terminal A→B) | ✅ (2026-10-01, nativer U22, 4/5 Nachrichten; U24/Docker noch nicht vollständig getestet) |
| 6 — Live Kick (`power: 6.0`, Ständer) | ⬜ offen — nächste Aktion |

## Noch nicht gebaut (Steps 3–4)

- **Step 3 — Evaluator + CLI:** `kick` / `kick stop` Fast-Path-Verben
  (bare `kick` → k1 slot, wie bare `turn`). Separate Session.
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