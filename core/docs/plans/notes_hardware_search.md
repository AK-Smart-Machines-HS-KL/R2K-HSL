# Hardware Search Report — Yahboom + K1 (projects, URDF/sim, LIDAR ball detection)

**Date:** 2026-08-28 | **Session:** v6.8 planning, tasks 6-adjacent | **Effort:** ~14 sources, ~90 min budget
**Status:** REPORT ONLY — persistence targets pending user selection.

---

## 1. Yahboom (our bot identified: MicroROS-Pi5 class) — CORRECTED 2026-08-29

**Kit identification:** Amazon B0D5QTST2N = "Yahboom MicroROS Robot Car" (ROS2-Humble,
microROS ESP32 board, TOF lidar, encoder motors). Our class = **MicroROS-Pi5**:
ESP32 microROS expansion board, 4× 370 encoder motors, **MS200 2D-TOF lidar**,
2MP camera on **2-DOF gimbal (the "pro" pan-tilt)**, 7.4V 2000mAh, aluminum frame.

**CORRECTION (Mecanum):** the recommended third-party sim `automaticaddison/yahboom_rosmaster`
targets the ROSMASTER X3 = **Mecanum wheels** (omnidirectional) — our chassis is a
4-fixed-wheel DIFF-DRIVE. Use it as scaffolding reference (xacro structure, ros2_control
wiring, lidar config, launch patterns) ONLY; the drive model must be diff-drive
(`gazebo_ros_diff_drive` on left/right pairs) — which EXACTLY matches our bridge's
(vx, vy=0, vyaw) command model. `Mojarras7/yahboomR2_sim` is Ackermann — also not ours.
Canonical diff-drive+lidar plugin reference: TurtleBot3-class sims (Gazebo classic).

**LOCAL RESOURCES RESOLVED (~/yahboom/, 2026-08-29):**
- Driver source IS on the laptop: `ROS_Source_Code/` (yahboomcar_ws pkg_*, imu_ws
  imu_tools-humble, gmapping_ws) — the "lab-side fetch needed" note is void
- **Gimbal interface confirmed at firmware level**: ESP32 microROS subscribes
  `<ns>/servo_s1` + `servo_s2` (angles → Servo_Set_Angle) — `Samples microros/`
- **Odometry ESP32-native**: `odom_publisher` sample (nav_msgs/Odometry); team's
  `wm.py` POC already shows bot1+bot2 odom — odometry flows today
- **Board-side PID registers** (serial tool `config_robot.py`): MOTOR_PID (0x09),
  IMU_YAW_PID (0x0A), SERVO_OFFSET (0x08), WIFI/AGENT_IP/DOMAIN_ID/NAMESPACE,
  REBOOT/RESET, FIRMWARE_VERSION (0x51) — team-modified for multi-robot setup
- Factory-Firmware: ESP32 images V1.1.3 / V2.0.0 / V2.1.0
- Team POCs: lidar_view.py, lidar_heatmap.py (sensor-data QoS learnings), wm.py,
  auto_explore.py (successful lab POC), udp_cam.py + direct_view.py (the KNOWN
  PROBLEMATIC udp camera — connectivity + performance, needs rework)
- "ROS node topic information.pdf" — topic reference (also in Factory-Firmware/)
- **Cure-ladder refinement**: Yahboom rotation/distance variations may be partially
  curable BOARD-SIDE (MOTOR_PID / IMU_YAW_PID) — below host-side compensation

**Interfaces (course documentation confirms):**
| Capability | Interface |
|---|---|
| Gimbal pan-tilt ("pro" head) | **PWM servo topics on the microROS ESP32 board** (course: "Subscribe PWM servo topics") — topic-driven, exists |
| LIDAR | MS200 2D TOF, ROS2 `/scan` via driver in car image |
| Odometry | encoder-based, published by microROS driver (quality TBD in lab) |
| Multi-machine sync | advertised feature (matches our multi-bot use) |

**Docs inventory (persist candidates for `src/yahboom/`):**
- `github.com/YahboomTechnology/MicroROS-Car-Pi5` — course PDF repo (URDF model course, lidar course, gimbal servo course); NO driver source on GitHub
- **Driver source ships in the RPi5 OS image** — lab-side fetch required (same pattern as K1 `/opt/booster`)
- Study portals: `yahboom.net/study/MicroROS-Pi5`, `yahboom.net/study/MicroROS-ESP32`
- Product: `category.yahboom.net/products/microros-pi5`
- Fetchable HTML manuals: `manuals.plus/ae/1005006615668219`, `/1005007177825020`
- MS200 driver repo: not in org top-100 (org has LD06/LD19, YDLIDAR X3, RPLIDAR repos) — driver lives in car image

**Third-party Gazebo projects (the gold):**
- **`github.com/automaticaddison/yahboom_rosmaster`** — full ROS2 Gazebo sim for ROSMASTER X3
  (URDF xacros, ros2_control configs, lidar sensor, Gazebo launch files + tutorial series).
  Best reference for simulating our diff-drive class. Well-maintained (Jazzy branch).
- `github.com/Mojarras7/yahboomR2_sim` — R2 (Ackermann) URDF+meshes+launch — secondary reference only.

## 2. K1 — sim/URDF assets

| Asset | Content | Verdict |
|---|---|---|
| `github.com/BoosterRobotics/booster_assets` | **`robots/K1/K1_22dof.urdf`** (1336 lines) + `K1_locomotion.urdf` + MuJoCo XMLs + 152 STL meshes + example motion data | THE official K1 description — Gazebo path = adapt this (add gazebo_ros plugins); no ready Gazebo K1 world exists anywhere |
| `BoosterRobotics/booster_gym` (300★) | RL framework, MuJoCo walking sim (`examples/walk_sim.py`) | vendor sim = MuJoCo, not Gazebo; walking-policy reference |
| `BoosterRobotics/sim-3v3-simple-framework` | **Official 3v3 soccer AGENT framework** (Python: agent.py, path_planner.py, obstacles, game_codec, player roles) for Booster Studio virtual-robot sim | strategy architecture reference + the "integrated goto-ball-and-kick" ecosystem (demos task c) |
| `BoosterRobotics/robocup_demo` (141★) | official 5v5 demo (fw 1.6 + SDK 1.3.6) | covered by earlier audit |
| `BoosterRobotics/booster_robotics_sdk_ros2` | official ROS2 interface pkg | PR #17 already imports this family |
| `roboticscenter.ai/...booster-k1/software` | third-party "guide" | **UNVERIFIED — contradicts official specs** (claims vx ±0.5 m/s vs vendor 1.1; head ±90° vs ±59°; nonexistent PyPI SDK + booster_ros2 repo; wrong subnet). Do NOT persist as reference. |

## 3. LIDAR ball detection (2D scan → ball position)

**Context:** MS200 lidar on Yahboom chassis top; ball LARGE (kid-size league ~15-20cm),
intersects the scan plane (user-confirmed). Clutter: field lines (low), other bots' legs,
goal frame. Approach options ranked by implementation cost:

1. **Distance-jump segmentation + size gate** (cheapest): adaptive breakpoint detection
   (angle/distance judgment) → clusters → gate on chord length ≈ ball diameter band →
   centroid + arc-fit → position. Enough for a slow ball on a mostly-empty field.
   Algorithmic reference: "Fast clustering method of LiDAR point clouds from coarse-to-fine"
   (ScienceDirect S1350449523000026).
2. **Off-the-shelf ROS2 packages** (mid):
   - `privvyledge/autodriver_laser_object_segmentation` — ROS2, optimized for small platforms
     (F1/10, Jetson Orin Nano!): clustering + multi-model shape fitting + multi-target tracking
   - `alejotoro-o/lidar_object_detection_ros2` — LaserScan → tracked objects (pose, dims, velocity)
   - `multi_object_tracking_lidar` (ROS1/PCL, C++, classic) — cluster→track→classify (needs port)
3. **Kalman tracking layer** (recommended regardless): nearest-neighbor + constant-velocity
   Kalman over frames → ball velocity, outlier rejection (also cures MS200 noise).

**Ball-vs-leg discrimination:** bots' legs = vertical narrow clusters similar to ball chord;
distinguish by (a) height (ball below knee — needs scan height below knee, else ambiguous),
(b) motion signature (legs shuffle periodically, ball rolls smoothly), (c) color/vision fusion
on the K1 only. For Yahboom-only: use motion consistency + size band + max-2-balls gate.

**Recommended minimal pipeline (Yahboom):** LaserScan → jump segmentation → cluster size gate
(ball diameter band ±tolerance) → arc centroid → nearest-to-expected Kalman →
publish `Detections`-style msg (reuse PR #17 `vision_interface/msg/Ball.msg` schema!).
**Gazebo twin:** add `gpu_lidar`/`ray` sensor to the Yahboom URDF at chassis-top height;
ball = sphere intersecting the plane; the SAME node runs on sim scans → sim2real
identical code path (calibration of noise only).

## 4. Gazebo world-extension plan sketch (for demo_ifa + v6.8)

1. Yahboom URDF: adapt `automaticaddison/yahboom_rosmaster` xacros → our chassis dims +
   MS200-equivalent ray sensor (matching FOV/range/frequency of MS200) + 2-DOF gimbal joints
   (camera + PTZ servos simulated) → replaces the box bot for Yahboom-mirrored entities
2. K1 URDF: adapt `booster_assets/robots/K1/K1_22dof.urdf` (meshes ship with it) →
   add gazebo plugins (diff-drive fallback for the mirrored PID steering, head camera) —
   locomotion stays bridge-driven; URDF is for VISUALS + sensors only
3. World: extend `soccer_match.launch.py`/world with field + goals (exists) + optional
   static markers (pit §9 item) ; LIDAR ball detection node runs against simulated `/scan`
4. Bridge: new actions route to the same hardware topics — no bridge change for sensors
   (sensor nodes are separate); gimbal = new PWM-servo topic action (mirrors real interface)

## 5. Persistence targets (PENDING USER SELECTION)

| Candidate | Target |
|---|---|
| Yahboom docs/URL inventory (this §1) | `src/yahboom/README.md` (+ PDFs/manuals if wanted) |
| K1 asset inventory + URDF pointer (§2) | `src/booster/ASSETS.md` |
| LIDAR ball-detection pipeline + packages (§3) | KB `4_EDGE_HARDWARE_SIM2REAL.md` addendum + demo_ifa plan |
| Gazebo world-extension plan (§4) | `mgt_demo_ifa.md` Demos section |
| UNVERIFIED flag roboticscenter.ai | KB 4_EDGE ( folklore ledger) |
