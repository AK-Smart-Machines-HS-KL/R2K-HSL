/* SUPERSEDED as planning input — evidence log kept for reference. Live plans: v68_pre_ifa/, v68_after_ifa (sections), v7/. */

# scratch — raw notes (v6.8 session 2026-08-28)

## Task 1: walk K1 — evidence

### Code (ollama_sandbox_bridge.py)
- P-controller: ang_z = clamp(angle_diff*3.0, ±2.5) :526-527; lin_x = 0.8 if |angle_diff|<0.5 else 0.2 :528
- Arrival: distance > 0.15 else zeros :526
- K1: RPC 2001 {vx, vy:0.0, vyaw} :546-547 — vy NEVER used
- K1 "kick": RPC 2000 {"mode": 1} = kPrepare (STOP placeholder!) :542-544
- Mirror: target_bot = hw_info['mirror_of'] :364; bot pose looked up in /gazebo/model_states :375-377 — PID closes on SIM twin
- IDLE_FACE: standing bots aim at ball (ang gain IDLE_FACE_ANG_MAX 1.5)
- No accel ramp anywhere; no vyaw 0.4 clamp anywhere (KB 4_EDGE claim = folklore #2)
- stop_all_hardware: K1 2000/mode1, Yahboom Twist zeros (:261-276 approx)
- launch_r2k.sh watchdog: same 2000/mode1 ('emergency_stop' uuid) :145-148

### Vendor specs (docs.booster.tech K1 specifications)
- Walking 1.1 m/s max; Turning 1.5 rad/s max → firmware silently clamps our 2.5/1.2
- Head joints: Yaw ±59°, Pitch -19..+49° (joint limits table)
- Variants: Geek (ARM 48TOPS, 2Ah/20min) / Education (Jetson Orin NX 8GB, 117TOPS) / Professional (Jetson AGX Orin 32GB, 200TOPS, 5Ah/70min)
- 22 DoF; head 2 DoF (depth cam + mic array in head); RGB LED x1
- Soccer Agent built-in: "autonomously track, chase, kick, and shoot the ball"
- Safety: auto-DAMP on uncontrollable state; soft e-stop joystick/App/back-panel

### Relay (utils/ros2_relay/external_relay.py)
- Runs ON the K1; UDP airgap 6000/6001/6002 to internal relay
- Publishes /Kev1n/odometer_state (booster_interface/Odometer) + LocoApiTopicResp to fleet
- No clamping; TODO in code: Odometer import is robot-version dependent
- DDS note: odom channel exists — invisible to host only during the FastDDS default-route NIC bug (2026-08-26 entry); fix_network_switch branch adds auto-restart on network change

### Folklore ledger (updated)
- "0.4 rad/s bridge clamp" — BUSTED (no such code; real clamp ±2.5, firmware 1.5)
- "K1 kick = autonomous chase" — still unverified (K1-PROBE); Soccer Agent chase is a different mechanism (Agent app, not raw RPC skill)

## Task 3: face vs yaw — evidence

### K1 head (vendor-documented)
- kRotateHead 2004 (absolute rad; yaw ±59°, pitch -19..+49° — spec joint limits table), kRotateHeadWithTime 2043 (smooth, time_ms), kRotateHeadWithDirection 2006 (jog -1/0/1)
- Face = attention/camera direction, body stays: ball tracking at standstill (goalie scanning), worldstate info (ball bearing via vision), HCI (nod=pitch osc, shake=yaw osc)
- Mode requirement for head commands undocumented (probe: 2004 in kWalking?)
- Yaw (body) = 2001 vyaw turn-in-place or turn-while-walk; kick power needs body alignment; head ±59° only partially compensates

### Yahboom (user info + code)
- Pro model: 2-DoF camera mount (servo pan-tilt) — NO ROS2K code drives it; Yahboom firmware-owned; driver topic TBD (lab question)
- Standard: no head — "face" = body turn-in-place (bridge IDLE_FACE already does continuous bearing tracking, ang-only); user's distinction: emulate-face (spin w/o translation) vs yaw-target (turn until angle reached, then stop — needs yaw feedback!)
- Yaw feedback on hardware: bridge reads cyaw from Gazebo only → on hardware, yaw-target turns are open-loop timed (rotation-variation root cause, task 1); K1 gyro via LowState/odom; Yahboom gyro via micro-ROS TBD

### Demo mapping (task a preview)
- K1: fast-path cmds "look left/right/up/down/center" (2004 presets, limits as constants) + "say yes"/"say no" (2043 or 2004 oscillation script ~3x ±20°)
- Yahboom pro: same cmds → servo pan-tilt (pending driver topic)
- Standard Yahboom: "look left/right" → body micro-turn emulation

## Task 2: kick K1 — evidence

### RoboCup Demo guide (docs.booster.tech, github BoosterRobotics/robocup_demo)
- Pipeline: vision_node + brain_node + game_controller_node; fw 1.6 + SDK 1.3.6 mandatory pairing
- Vision: /boostercamera/head/rgb + /boostercamera/head/depth, YOLO model, /opt/booster/vision.yaml (system path WINS over demo config)
- Hand-eye calibration procedure exists (0.8-1m board) — trigger: "large ranging errors, kicks with obvious deviation"
- Kick = kVisualKick RPC, config `RLVisionKick: visual_kick_version: kV2`; kV2 = larger swing, longer distance, GREATER TOLERANCE FOR RANGING ERROR (vendor recommends kV2 first)
- Soccer mode: LT+A enter soccer mode → "complete LOCALIZATION", LT+B → automatic match strategy — on-field localization is part of soccer mode (vision-based, not odometry!)
- RobocupBehaviorStatus (RUNNING/SHOOTING/PASSING) + kGetStatus (2018) = observable behavior state → possible kick success/progress feedback
- Brain re-plans every cycle (chase is brain-side loop, not a stuck firmware skill)

### Our repo
- ros2_ws/src/brain/msg/GoToBallAndKickCmd.msg: demo-style fields (dir, goal_x/goal_y, robot_theta_to_field, power, is_goalshot) + Kick.msg — NO node uses them (dead definitions, likely imported from demo earlier as placeholder)
- Bridge K1 kick = 2000/mode1 placeholder (task 1)

### Folklore verdict (sharpened)
- "Approach until kick distance, then kick" = DEMO BRAIN behavior (vision-closed chase loop, re-planned per cycle) + short-range kVisualKick skill at the end
- Ball moves away mid-approach → brain re-plans (by design); mid-skill → kV2 ranging tolerance, abort semantics undocumented → K1-PROBE still required for raw-skill use
- If WE are the brain (LLM), WE own the abort decision — the "chase forever" firmware problem likely does not exist in the demo architecture; fear conflated brain loop with skill
- Success feedback: kGetStatus/RobocupBehaviorStatus candidate — verify in probe

### Open questions (rolling)
- Fleet: 2x K1 Education confirmed; Professional NOT ordered — budget request, justification = proposal_edge_llm_k1.md (user 2026-08-28)
- Does Yahboom publish usable odom? (micro-ROS; encoder quality)
- Odometer msg version match: external_relay (booster_interface.msg.Odometer) vs utils/interface (PR #17)
- How is the Yahboom-pro pan-tilt servo commanded? (driver topic — lab question)
- Head-command mode requirement (2004 in kWalking?) → K1-PROBE item

## Task 4: calibration — evidence
- PoseEstimator (PR#17 branch): EstimateByColor/ByDepth(p_eye2base, detection) → Pose; BallPoseEstimator + HumanLikePoseEstimator; head-angle-compensated
- vision_node publishes Detections + LineSegments (field lines) → demo brain localizes (soccer mode LT+A "complete localization")
- kResetOdometry 2031 = correction write-path; composition node (detections+odom→2031) = "vision-corrected odometry"
- calib_cli.py at core/tools/ (NOT src/tools); 193 lines; FAST_COMMANDS set + SAMPLE_COMMANDS + task_input.json; extension point: --odom watch mode (subscribe /Kev1n/odometer_state + yahboom odom, CSV log commanded-vs-reported)
- PR #17 status CORRECTION: still OPEN (not merged — user misremembered); vision stack NOT in main; main tip c74142ca (#18)

## Hardware search — Y1+B1 evidence (2026-08-28, build phase)

### Y1: Yahboom identification + docs
- B0D5QTST2N = **Yahboom MicroROS Robot Car** (amazon listing title; MicroROS board + ESP32 co-proc + TOF lidar + ROS2-Humble)
- Our class = **MicroROS-Pi5**: ESP32 microROS expansion board, 4x 370 encoder motors, **MS200 lidar** (2D TOF), 2MP cam + **2-DOF gimbal PTZ**, aluminum frame; product: category.yahboom.net/products/microros-pi5; study portal: yahboom.net/study/MicroROS-Pi5 (+ MicroROS-ESP32)
- **Gimbal interface FOUND**: PWM servo topics on the microROS ESP32 board (course PDF "17. microros basic course/5. Subscribe PWM servo topics") — the pan-tilt IS topic-driven
- GitHub: YahboomTechnology/* repos are COURSE PDFs only; driver source ships in the RPi5 OS image (lab-side fetch needed, like /opt/booster)
- Manuals mirrored fetchable: manuals.plus/ae/1005006615668219 + /1005007177825020
- MS200 driver repo: NOT in org top-100 (candidates: DTOF-mini-LiDar LD06/LD19, EAI-X3 YDLIDAR) — driver likely in car image

### B1: Booster sim/URDF assets
- **booster_assets** (github BoosterRobotics): robots/K1/K1_22dof.urdf (1336 lines, 27.3KB) + K1_locomotion.urdf + MuJoCo XMLs + 152 STL meshes — official K1 description exists
- Booster's official sim = MuJoCo (booster_gym, 300 stars, RL) + **Booster Studio** agent sim; NO official Gazebo K1 world
- **sim-3v3-simple-framework**: official 3v3 soccer AGENT framework (Python: agent.py, path_planner, obstacles, game_codec, player roles) for Booster Studio's virtual robot sim — strategy reference + the "goto-ball-and-kick" ecosystem (demos task c!)
- Third-party: roboticscenter.ai K1 software guide (SDK/ROS2/MuJoCo); NO ready Gazebo K1 projects found → Gazebo path = adapt official URDF + add gazebo plugins
- booster_robotics_sdk_ros2: official ROS2 interface pkg (12 stars)
