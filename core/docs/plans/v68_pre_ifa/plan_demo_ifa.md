# IFA Demo Plan (DETAILED) — show-cases & POCs

**Status:** ACTIVE | **Owner:** Prof-Adrian-Mueller | **Date:** 2026-08-28/29
**Show set:** a (face/yaw) · b-FAKE (kick) · b-LIDAR (detection) · d-FAKE (trailer) · Lab gate. Soccer Agent: OUT.

## A1-A3 — Face vs Yaw + say-yes/no (task a)

| # | Step | Detail |
|---|---|---|
| A1 | Bridge head actions | K1: `headturn` → RPC 2004 `{"pitch","yaw"}` radians, edge-triggered dedup (`_last_head_cmd`, eps), clamp constants: yaw ±59° (1.03 rad), pitch −19°/+49° (−0.33/+0.86 rad). Yahboom: `headturn` → publish angle to `<ns>/servo_s1` (pan) / `servo_s2` (tilt) — interface confirmed at ESP32-firmware level (`servo_subscriber` sample) |
| A2 | Evaluator fast-path | "look left/right/center/up/down" presets + "say yes" (pitch osc ~3× ±20°) + "say no" (yaw osc) — scripted 2004 sequences; same commands for Yahboom via servo topics; no soccer-mode leakage (demo-only) |
| A3 | CLI + sim twin | `calib_cli.py` samples; K1 URDF twin gets 2 head joints visible (teammate's Gazebo task) so hardware_mirror shows the nod in sim too |

## B1-B2 — Kick demo (task b)

| # | Step | Detail |
|---|---|---|
| B1 | b-FAKE | "kick ball" fast-path → waypoints: drive to ball (1,0) with push-through overshoot; Yahboom metal push; K1 walk-push; `hardware_mirror` simultaneity (proven) |
| B2 | b-LIDAR (pre-IFA) | `lidar_ball_detector` node (see plan_v68.md V4) feeds ball position → demo no longer needs the fixed location: "kick ball" works with the ball anywhere in the front semicircle; ball-size picked at the lab session (3 candidates) |

## D1-D3 — Trailer FAKE (task d; frame BUILT, torque TESTED)

| # | Step | Detail |
|---|---|---|
| D1 | Choreography | waypoints: approach fork at 0° → push to marked target; return; approach at 45° → CW rotation; (−45° CCW if time) — rotation via approach-angle selection, NO lateral motion (diff-drive) |
| D2 | Detection | LIDAR-only (decoupled from the udp-cam rework): frame posts/forks are strong scan returns; pose = 2-post fit + known geometry |
| D3 | Goal (post-IFA) | free (x, y, yaw) via tractor-style arc library + LIDAR frame pose |

## Lab session gate (single session, 90-120 min — agenda)

1. [5'] K1-PROBE step 1: `booster-cli version` both K1s → changelog
2. [10'] Yahboom driver-source verification vs local `ROS_Source_Code/` (freshness check only — source already on laptop)
3. [10'] Head smoke test: 2004 look-left/center on one K1 (answers 2004-in-WALKING)
4. [30'] Dry-runs: a (both bots), b-FAKE, b-LIDAR, d-FAKE
5. [15'] Ball-size pick (3 candidates) + first calibration patterns (straight 2m ×5, rotation 360° ×5)
6. [15', optional] VisualKick probe V1/V2 + ball-motion experiment — ONLY if fw ≥ 1.5.2.1 and all green
7. [5'] Changelog entry with all measured numbers

## Post-IFA
c-real (RoboCup vision / goto-ball-and-kick / camera color tracking), d-real (LIDAR frame pose + free-pose maneuver library), kVisualKick integration (fw-gated), udp-cam rework (separate track).

## Trello
Card source: `plans/student_projects_autumn_fair.md` (per-section cards, established pattern) + this plan's A/B/D tables.
