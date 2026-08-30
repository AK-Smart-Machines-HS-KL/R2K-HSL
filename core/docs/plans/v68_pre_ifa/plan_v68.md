# v6.8 Plan — Technical Depth & K1 Steering Improvements (DETAILED)

**Status:** ACTIVE — pre-IFA items are the IFA-gating set | **Owner:** Prof-Adrian-Mueller | **Date:** 2026-08-28/29
**Evidence base:** pre-ambles in `mgt_v68.md` (Walk, Kick), `mgt_demo_ifa.md` (Face/Yaw, Calibration), `scratch.md`

## Pre-IFA

| # | Task | Files | Acceptance | Effort |
|---|---|---|---|---|
| V1 | **Clamp alignment** — bridge constants to K1 spec: `ANG_Z_MAX 2.5→1.5`, `LIN_X_BOOST 1.2→1.1` (named constants, single source; removes the systematic rotation/distance shortfall) | `src/ai_tactics/ollama_sandbox_bridge.py` | lab: 360° turns ≈ commanded; fast dash distance ≈ expected | 0.5 d |
| V2 | **Demo task a** — face/yaw + say-yes/no (see plan_demo_ifa.md A1-A3) | bridge + evaluator + calib_cli | lab dry-run both bots | 1-2 d |
| V3 | **Demo task b-FAKE** — kick-ball waypoints (see plan_demo_ifa.md B1) | calib scenario/samples | lab dry-run, mirror simultaneity | 0.5 d |
| V4 | **LIDAR ball detection node** (pre-IFA per decision 2026-08-29): LaserScan → jump segmentation → cluster size-gate (ball diameter band) → arc centroid → nearest-neighbor Kalman; publish via `vision_interface/msg/Ball.msg` schema; runs UNCHANGED on sim `/scan` (ray sensor on Yahboom URDF twin) and MS200 | new node `src/lidar_ball_detector.py` + reuse POCs (`lidar_view.py`, `lidar_heatmap.py` patterns) | lab: ball at 2m detected ±5cm @ 2Hz; sim: same node on Gazebo scan | 1-2 d |
| V5 | **Odom watch for calib_cli** — `--odom` mode: subscribe `/Kev1n/odometer_state` + Yahboom `/odom` (bot1/bot2, proven by `wm.py` POC), CSV-log commanded-vs-reported per task | `core/tools/calib_cli.py` | lab session produces first drift CSV | 0.5 d |
| V6 | **Lab session gate** — the single pre-IFA session: fw probe (both K1s), 2004-in-WALKING, dry-runs V2-V4, ball-size pick, first calibration patterns (straight/rotation per mgt_demo_ifa ladder) | — | changelog-logged results | 90-120 min |

## After IFA

| # | Task | Gated by |
|---|---|---|
| V7 | **Kick placeholder removal** — bridge K1 Kick action → kVisualKick 2038 (`{"api_id": 2038, "start": true, "version": kV1/kV2}`), edge-triggered dedup | fw ≥ 1.5.2.1 (K1-PROBE); kV1 vs kV2 probe |
| V8 | Soccer-mode (4) evaluation vs custom skills (`kGoalie`, kicking postures) | K1-PROBE |
| V9 | Odom-closed control on hardware (bridge subscribes odom; optional 2031 reset composition node) | V5 drift data |
| V10 | Board-side PID cure — MOTOR_PID / IMU_YAW_PID tuning via config-robot serial tool (cheaper than host compensation) | V5 drift data |
| V11 | `vy` exploitation where useful (omnidirectional K1) | post-V1 |

## Firmware policy
See `mgt_v68.md` — no upgrade pre-IFA; in-session probe decides; post-IFA one-robot-first.

## Sources of truth
- Walk/Kick pre-ambles: `mgt_v68.md` | Calibration + cure ladder: `mgt_demo_ifa.md`
- Vendor audit + K1-PROBE protocol: `k1_kick_head_vendor_audit.md`
- K1 fleet: 2× Education (Orin NX 8GB); Professional = feasibility path (`plans/v7/proposal_edge_llm_k1.md`), NOT ordered
