# v6.8 Mgt Summary — Technical Depth & K1 Steering Improvements

**Status:** DRAFT (pre-ambles accumulate per task; condensed summary at assembly)
**Owner:** Prof-Adrian-Mueller | **Date:** 2026-08-28 | **Branch:** docs/v68Planning

---

## Pre-amble — Clarification: Walk (K1)

**Who walks the K1 (v6.7 status):** the LLM emits flat-JSON `Move(x,y)` targets; the bridge's P-controller (10Hz) computes `{vx, vyaw}` from the *sim twin's* Gazebo pose and streams RPC 2001 to the K1; Booster's gait controller executes planar velocity (joints closed inside firmware). The hardware loop is open: no K1 pose or odometry feeds back — mirroring assumes the robot executes exactly what the sim twin needs.

**Known inaccuracies (lab-observed, root-caused):**
1. Command/spec mismatch — bridge sends up to 2.5 rad/s & 1.2 m/s, robot executes ≤1.5 rad/s & 1.1 m/s (firmware clamps silently) → systematic rotation/distance shortfall on fast moves
2. Open-loop error accumulation (slip, gait latency, no correction)
3. Step-discretized gait variance (cm-level, inherent)

Verdict: structural insufficiency, not a bug. The KB claim "vyaw hard-clamped to 0.4 rad/s in the bridge" is folklore — the code clamps at ±2.5 (no clamp exists in relay either).

**Stop semantics:**
- *Target reached* = RPC 2001 zeros (stays in kWalking, active brake, 0.15m threshold); demo-Hold identical
- *Emergency* = RPC 2000 mode 1 (kPrepare) via watchdog / Gazebo-pause detection
- Vendor DAMP (mode 0) auto-triggers on instability — never sent by us
- Note: the K1 "Kick" action currently sends 2000/mode-1 — a stop placeholder, no kick command exists (see the Kick pre-amble below)

**Odometry:** unused today (Gazebo-only, Axiom 2), but `/Kev1n/odometer_state` (Odometer) + IMU LowState are already relayed to the fleet by `external_relay.py` — closing the hardware loop is a subscription away. Lateral walking (`vy`) is available but never commanded.

**Implications for v6.8:**
1. Align command clamps to spec (1.5 rad/s, 1.1 m/s) — named constants, single source
2. Optional odometry-closed control on hardware (subscribe `/Kev1n/odometer_state`)
3. Exploit `vy` (omnidirectional) where useful
4. Remove the kick placeholder (see the Kick pre-amble below)
5. K1 fleet: 2x Education (Orin NX 8GB) — onboard vision plausible; Professional (AGX Orin 32GB) not ordered — feasibility path in proposal_edge_llm_k1.md

---

## Pre-amble — Clarification: Kick (K1)

**Kick on K1 — state & path forward.** Today the bridge's K1 "kick" is a placeholder (RPC 2000/mode-1 = stop); `GoToBallAndKickCmd.msg`/`Kick.msg` exist unused. The vendor's own RoboCup demo shows the target architecture: vision (head camera, YOLO; vision stack in PR #17 — open, not yet merged) feeds a per-cycle decision loop that closes on the ball and triggers **kVisualKick** (config `visual_kick_version: kV2`, fw ≥ 1.5.2.1) at kick distance. The chase lives in the brain, not the skill — with our LLM as brain, the abort decision is ours, dissolving the "chase forever" folklore (raw-skill abort semantics still pending K1-PROBE verification). Kick progress/success is likely queryable via kGetStatus (2018) / RobocupBehaviorStatus (RUNNING/SHOOTING/PASSING). Vision ranging quality depends on hand-eye calibration (documented procedure, board at 0.8-1m).

**v6.8 path:**
1. Replace the bridge placeholder with a VisualKick-trigger action (`{"api_id": 2038, "start": true, "version": ...}`)
2. Optional: integrate `GoToBallAndKickCmd` (interface exists, demo-proven semantics)
3. Evaluate Soccer-mode (4) built-ins (`kGoalie`, kicking postures) BEFORE custom code
4. Probe kV1 vs kV2 on hardware (part of K1-PROBE); vision ranging needs hand-eye calibration
5. Reuse PR #17 vision stack (`utils/vision/`, pending merge) for ball detection — no LIDAR needed on K1

---

## Firmware policy (pre-IFA, 2026-08-28)

**No firmware upgrade before IFA.** One lab session only — a botched flash (motion control off during upgrade, fw↔SDK pairing, fall/brick risk) would cost both the session and the demo robot. Decision is made in-session by K1-PROBE step 1 (`booster-cli version`, zero risk):

| Result | Consequence |
|---|---|
| fw ≥ 1.6 | everything available; VisualKick + Soccer-mode testable in-session |
| 1.5.2.1 ≤ fw < 1.6 | VisualKick works (v6.8 kick scope safe); RoboCup modules deferred |
| fw < 1.5.2.1 | NO upgrade in-session — kick work deferred post-IFA; demos unaffected (2004 head + walking + push) |

Post-IFA policy: upgrade ONE Education unit first, validate walking + head + VisualKick, then the second — never both before an event. ESP32-board firmware (Yahboom) is a separate track: images V1.1.3/V2.0.0/V2.1.0 exist in the local Factory-Firmware set; installed version queryable via the config tool (register 0x51) — no upgrade planned.

---

## Pre-amble — Clarification: Face vs Yaw

See mgt_demo_ifa.md in this directory (Face vs Yaw pre-amble).
