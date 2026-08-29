# v6.8-demo_ifa Mgt Summary — Showcases & POCs before v7

**Status:** DRAFT (pre-ambles accumulate; condensed summary at assembly)
**Owner:** Prof-Adrian-Mueller | **Date:** 2026-08-28 | **Branch:** docs/v68Planning

---

## Pre-amble — Clarification: Face vs Yaw

**K1 (vendor-documented):** *Face* = head-only attention change — `kRotateHead` 2004 (absolute radians; **yaw ±59°, pitch −19°/+49°** per spec joint-limit table), `kRotateHeadWithTime` 2043 (smooth/timed), `kRotateHeadWithDirection` 2006 (jog). Body stays — ideal for standstill ball tracking (goalie scanning), ball-bearing info for the worldstate via vision, and HCI mimics (nod = pitch oscillation, shake = yaw oscillation). *Yaw* = body heading via 2001 `vyaw` (turn-in-place or turn-while-walking) — required for kick power (body alignment); head yaw only partially compensates.

**Yahboom:** *Pro* has a 2-DoF camera mount → face = servo pan-tilt, but **no ROS2K code drives it today** (Yahboom-firmware-owned; driver topic = lab question). *Standard* has no head → "face" is emulated by body turn-in-place without translation (the bridge's IDLE_FACE already does continuous bearing tracking, ang-only). The user-distinction maps cleanly: *emulate-face* = continuous bearing tracking; *yaw-to-target* = turn until target angle then stop — **needs yaw feedback**, which on hardware does not exist today (bridge reads yaw from Gazebo only; K1 gyro via LowState/odometer; Yahboom via micro-ROS TBD) → open-loop timed turns are the rotation-variation root cause (see v6.8 mgt, Walk pre-amble).

**Demo implementation sketch (task a):**
| Command | K1 | Yahboom Pro | Yahboom Std |
|---|---|---|---|
| look left/right/up/down/center | 2004 presets (limits as constants) | servo pan-tilt (pending driver topic) | body micro-turn emulation |
| say yes / say no | 2043 or scripted 2004 oscillation (~3× ±20°) | servo pitch/yaw oscillation | body shake (weak — likely skip) |

Open: head-command mode requirement (2004 accepted in kWalking?) — part of K1-PROBE.

---

## Pre-amble — Clarification: Calibration & Curing Distance/Rotation Variations

**Constraint honored: no eye-in-sky.** Ground truth comes only from floor marks + tape measure (human) and the robot's own senses.

**Is there K1 firmware that captures frames, analyzes deltas, updates odometry?** Not a single firmware switch, but all components exist and the vendor demo composes them:
1. **Vision ball pose**: `PoseEstimator::EstimateByColor/ByDepth` (PR #17 `utils/vision`, head-angle-compensated via `p_eye2base`) → ball position in robot frame each frame
2. **Field-line localization**: vision publishes `LineSegments`/`SegmentationResult`; the demo brain localizes the robot on the field (soccer mode: LT+A "complete localization") — vision-based, not dead-reckoning
3. **`kResetOdometry` (2031)**: re-zero the internal odometry origin — the correction WRITE path
So: "vision delta → odometry correction" = a small composition node (subscribe detections + odom → compute correction → 2031), not new firmware. The demo solves the same problem with continuous vision localization instead of corrected odometry.

**calib_cli.py extension (suggested):** add an odom-watch mode (`--odom`): subscribe `/Kev1n/odometer_state` (+ Yahboom odom topic once identified), print and CSV-log **commanded vs reported** per task (commanded is known from task_input/waypoints). This gives the team direct drift data per command type/speed with zero extra hardware.

**Suggested calibration patterns (floor marks + tape only):**
| Pattern | Procedure | Measures |
|---|---|---|
| Straight 2m ×10 | floor mark → run → measure endpoint deviation | linear drift vs speed (0.2/0.5/0.8 m/s) |
| Rotation 360° ×10 | toe-direction mark → run → heading error | yaw drift vs speed (validate the 1.5 rad/s clamp) |
| Square 2×2m | return-to-start error | combined drift |
| Arc r=1m, 90°/180° | endpoint vs ideal | worst case (turn+drive mixing) |
| Vision-corrected out-and-back | ball at known offset, walk away+back, compare odom-ball vs vision-ball | correction-gain data for the composition node |

**Procedure:** mark → PREP → WALK → calib pattern via CLI → odom CSV (new `--odom-log`) → human measures physical endpoint → delta table → per-speed correction factors → constants in the bridge (or command scaling `v_cmd = v_desired × k`).

**Cure ladder (cheap → expensive):**
1. Command clamps aligned to spec (v6.8, Walk pre-amble) — removes the systematic shortfall
2. calib_cli odom watch + patterns → quantified drift factors
3. Command scaling factors per axis/speed
4. Vision-corrected odometry composition node (2031)
5. Full vision localization (demo brain style) — v7 territory (TeamCaptain)

---

## Demos (tasks a-d)

### a) Face vs Yaw showcase (demo/calib mode)
- Implement new cmds per `calibration_rotation_design.md` (Option D, this dir) on **Yahboom (2-DOF gimbal) and K1 (2004)**
- Feature a "yes/no" mimic (pitch/yaw oscillation) → extending demo mode with **"look left", "say yes"**
- K1 head limits documented (yaw ±59°, pitch −19°/+49°); posture question (2004 in kWALKING vs PREP) resolved at the lab session — fallback path (2000/mode-1 → nod → back) uses existing commands

### b) Extended demo/calib for the IFA kick — THE FAKE variant
- Ball at fixed demo location (e.g. 1,0), bot at 0,0; user cmd: **"kick ball"**
- Yahboom: max-speed approach and push (metal push, proven). **LIDAR ball detection moves INTO the pre-IFA scope** (see sequence below)
- K1: walk-push (gait disturbance handling covers ball contact at low speed)
- `hardware_mirror`: both bots move simultaneously — the show

### c) Beyond FAKE for K1 (post-IFA)
- RoboCup modules from Booster for ball detection (vision stack, fw 1.6 + SDK 1.3.6)
- Integrated "goto-ball-and-kick" as exposed in the Booster demo app / `sim-3v3-simple-framework` agent API
- Yahboom: LIDAR + front-camera (2MP gimbal cam, color tracking is a stock kit feature)

### d) Yahboom Trailer Hitch Mechanism (frame BUILT, torque TESTED — no mechanics pending)
A0-sized K1 photo dummy on a movable frame, 2×2 free-rotating wheels in Y-forks on the two
short sides. Yahboom drives into a fork (front or rear end) and pushes the frame on a single
axle. Frame position via LIDAR only (decoupled from the udp-cam rework problem).
- **0° attack** = forward push (frame translates on casters); **45° attack** = frame rotates
  clockwise (−45° CCW) — rotation via approach-angle selection, no lateral motion needed
- Goal: maneuver to a freely selectable (x, y, yaw) — tractor-trailer-like patterns

### Sequence (easy first)

| # | Step | Type | Effort |
|---|---|---|---|
| 1 | **b-FAKE kick** — waypoints → (1,0) push-through, mirror simultaneity | existing pieces | ~0.5 d |
| 2 | **a — face/yaw + say-yes/no** | host code only (K1 2004 + Yahboom servo topics) | ~1-2 d |
| 3 | **b-LIDAR** — ball-detection node (jump segmentation → size gate → Kalman; reuses `vision_interface/msg/Ball.msg` schema; runs on sim `/scan` AND MS200) | pre-IFA per user decision | ~1-2 d |
| 4 | **d-FAKE trailer** — fork entry, 0° push, 45° CW rotation | same fake-waypoint class as #1 | ~1 d |
| 5 | **Lab session gate** (single session before IFA): fw probe both K1s, 2004-in-WALKING test, dry-runs 1-4, ball-size pick (3 sizes available) | 90-120 min |
| — | c-real (RoboCup vision / goto-ball-and-kick, camera tracking), d-real (LIDAR frame pose + free (x,y,yaw) maneuvers), kVisualKick behind our brain (fw-gated) | post-IFA |

**Firmware policy (pre-IFA):** NO firmware upgrade. K1-PROBE step 1 (`booster-cli version`) decides in-session; feature gating per `mgt_v68.md` firmware note.

**Soccer Agent (vendor app): out of this plan** — dropped from the IFA set and discussion.
