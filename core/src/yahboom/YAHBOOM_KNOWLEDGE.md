# Yahboom Knowledge — ROS2K hardware notes (MicroROS-Pi5 class)

**Created:** 2026-08-29 | **Maintainer:** Prof-Adrian-Mueller
**Scope:** our two Yahboom diff-drive bots (MicroROS-Pi5 class) — interfaces, resources, POCs.

## Fleet naming (2026-08-30, 1→1/2→2 alignment)
| Bot | ESP32 namespace | Role | Sim twin |
|---|---|---|---|
| yahboom #1 (standard) | **/blue_1** (was /bot1) | main | blue_1 |
| yahboom #2 (vision, 2-DOF cam) | **/blue_2** (was /bot1 — collided with #1!) | camera | blue_2 |
Both were configured as /bot1 (the "ambiguous topic list" root cause). With name
alignment, `/blue_N/cmd_vel` is SHARED by sim twin + physical bot (implicit mirror
— no bridge mirror thread for Yahbooms). K1 stays `mirror_of: blue_1`.

**LESSON (XRCE domain):** the ESP32 domain register is NOT inert — the XRCE
create-participant payload carries it, and the agent creates entities in that
domain. The pro was set to domain 20 by a stale config script; every domain-0
query was blind to it. #1 (domain 0) always worked. Rule: fleet = domain 0.

**Radio note:** the host laptop (Intel Wi-Fi 7 BE200-class) resets in AP mode
every few minutes on this desk (journal: supplicant-failed → device removed,
kernel "Internal hw_queue N is full! stopping all queues").
Lab launches were stable. If in doubt about "no topics", FIRST check
`ip -4 -br addr` for a flapping hotspot, THEN suspect the graph.

**Cure for "yahboom never reconnects" (2026-09-04):** three layers —
1. Robot-side (one-time per Pi5, the actual reconnect fix):
   `sudo nmcli connection modify <PROFILE> connection.autoconnect yes connection.autoconnect-retries 0 802-11-wireless.powersave 2`
   (retries 0 = forever; powersave off prevents mid-session drops).
2. Host-side watchdog: `tools/hotspot_watchdog.sh` re-activates the Hotspot
   profile within 5s after a BE200 reset (NM does not reliably re-activate it).
3. Host-side stabilization (persistent, needs reboot):
   `echo "options iwlwifi power_save=0 uapsd_disable=1" | sudo tee /etc/modprobe.d/iwlwifi-ap-stability.conf`
**Sources of truth:** local `~/yahboom/` resources, ESP32 microROS samples, vendor docs
(`yahboom.net/study/MicroROS-Pi5`, `category.yahboom.net/products/microros-pi5`).
Avoid: Amazon listings for technical facts. See also `src/booster/ASSETS.md` (K1 side).

## 1. Hardware identity
- ESP32 microROS expansion board (the micro-ROS/XRCE-DDS endpoint — unicast agent 10.42.0.x:8888)
- 4× 370 encoder motors (310 in some kit revisions), fixed wheels → **DIFF-DRIVE, non-holonomic**
- **MS200 2D-TOF lidar** (chassis top; ROS2 `/scan`)
- 2MP camera on **2-DOF gimbal PTZ** (the "pro" head)
- 7.4V 2000mAh; aluminum frame; RPi5 host (ROS2-Humble, Python3)

## 2. Interfaces (CONFIRMED)
| Capability | Interface | Evidence |
|---|---|---|
| Gimbal pan-tilt | microROS topics `<ns>/servo_s1` (pan) + `<ns>/servo_s2` (tilt), Int angle → Servo_Set_Angle | ESP32 `servo_subscriber` sample (`Samples microros/`), course PDF "Subscribe PWM servo topics" |
| Odometry | `<ns>/odom` (nav_msgs/Odometry, encoder-based, published by ESP32; in the RELAYED domain the physical robot's stream appears as `<ns>/odom_raw` from `YB_Car_Node` — `<ns>/odom` there is the SIM TWIN, see the odom_raw trap in LESSONS_LEARNED 2026-08-31) | `odom_publisher` sample; team `wm.py` POC displays bot1+bot2 odom live |
| Odom rehearsal (2026-09-08) | bridge (`ollama_sandbox_bridge.py:_ensure_odom_watch`) subscribes `<ns>/odom_raw` per yahboom relay entry → `shared_state/y{1,2}_odom.json` (0.5 s, atomic rename) + `k1_trace_<run_id>.jsonl` records + closed-loop `Goto` feedback (`y1 go to (x,y)`). K1 field-test PREP: Yahbooms mirror the K1 pipeline (odometer_state → k1_odom.json → Goto) so the CLI/exec/results flow is rehearsed on cheap hardware. ±30% encoder slip ACCEPTED (rehearsal vehicle, not accuracy target — arrivals coarse, per-bot PASS thresholds informational). Msg type assumed nav_msgs/Odometry (odom_publisher lineage) — verify live at first lab contact (`ros2 topic info /blue_N/odom_raw -v`, expect `YB_Car_Node`) | bridge code 2026-09-08; `docs/plans/v68_pre_ifa/calib_validation_runbook.md` §V11 |
| cmd_vel | `<ns>/cmd_vel` Twist | `twist_subscriber` sample; our bridge drives it |
| LIDAR | `/scan` LaserScan via MS200 driver | course "09.Lidar course"; POCs below |
| IMU | filtered (imu_tools-humble Madgwick/complementary in `imu_ws`) | driver set |
| Board config | serial protocol `config_robot.py` (115200 8N1, head 0xFF/F8/F7): WIFI_SSID/PASSWD, AGENT_IP/PORT, CAR_TYPE (COMPUTER=0/RPI5=1), DOMAIN_ID, SERVO_OFFSET (0x08), **MOTOR_PID (0x09)**, **IMU_YAW_PID (0x0A)**, ROS_NAMESPACE (0x0B), REBOOT (0x20), RESET_CONFIG (0x21), REQUEST_DATA (0x50), FIRMWARE_VERSION (0x51) | team-modified script for multi-robot WLAN/agent/namespace |
| ESP32 firmware | microROS_Robot V1.1.3 / V2.0.0 / V2.1.0 images (local `Factory-Firmware/`) | version query via 0x51 |

## 3. Local resources (`~/yahboom/`)
| Path | Content |
|---|---|
| `ROS_Source_Code/` | **driver/ROS source on the laptop**: `yahboomcar_ros2_ws/yahboomcar_ws` (pkg_topic/service/tf/interfaces/param/action), `imu_ws` (imu_tools-humble), `gmapping_ws` (openslam gmapping), `yahboomcar_ros2_ws` top |
| `Samples microros/` | ESP32-side microROS samples: servo_subscriber, odom_publisher, lidar_publisher, imu_publisher, twist_subscriber, custom_transport, beep, ... |
| `Factory-Firmware/` | 3 firmware .bin images + config_robot.py + topic-info PDF |
| `config_robot.py` (+ 5090/variants) | the fleet configuration tool (multi-robot WLAN/agent/namespace) |
| POCs | `lidar_view.py`, `lidar_heatmap.py` (LaserScan viz; sensor-data QoS Best-Effort gotcha documented), `wm.py` (PyQt world model, bot1+bot2 odom), `auto_explore.py` (lidar wall-follow, STOP_DIST 0.4), `udp_cam.py`/`direct_view.py` (**KNOWN PROBLEMATIC** udp camera — connectivity + performance, rework pending; ports 6500/8000; SO_RCVBUF=1 drop-old hack) |
| `ROS node topic information.pdf` | topic reference |

## 4. Kinematics / control facts
- Diff-drive: no lateral motion — rotation via wheel-speed differential (slight skid on 4 fixed wheels)
- Bridge commands `(vx, vy=0, vyaw)` — matches the kinematics exactly (v6.8: clamps aligned to a realistic Yahboom speed)
- Physical limits live ON the ESP32: MOTOR_PID + IMU_YAW_PID registers → **rotation/distance variations may be curable board-side** (tune via config tool) — cheaper than host-side compensation
- Gazebo twin: diff-drive plugin (left/right wheel pairs) + ray/lidar sensor at chassis-top height + 2 gimbal joints driven by servo-topic mirrors; canonical plugin reference = TurtleBot3-class sims (NOT the Mecanum ROSMASTER X3 sims — `automaticaddison/yahboom_rosmaster` is scaffolding-only, drive model differs)

## 5. Ball detection (LIDAR, pre-IFA v6.8)
Pipeline (sim2real-identical code): LaserScan → adaptive jump segmentation → cluster
size-gate (ball diameter band ±tolerance; ball is LARGE, intersects the scan plane) →
arc centroid → nearest-neighbor Kalman (velocity + outlier rejection) → publish via
`vision_interface/msg/Ball.msg` schema. Clutter: other bots' legs (size+motion-gate),
field lines (below scan height). Off-the-shelf references:
`privvyledge/autodriver_laser_object_segmentation` (F1/10-scale ROS2),
`alejotoro-o/lidar_object_detection_ros2`, algorithmic:
"Fast clustering ... coarse-to-fine" (ScienceDirect S1350449523000026).

## 6. Known problems / open
- udp camera stream (udp_cam/direct_view): connectivity + performance — rework pending;
  demos deliberately use LIDAR-only perception until fixed
- MS200 driver repo not in Yahboom org top-100 (driver lives in the RPi5 image; local
  ROS_Source_Code may contain it — verify at next lab session)
- Installed ESP32 firmware version unknown (query 0x51 via config tool)

## 7. Booster K1 ROS 2 interface (`booster_ros2_interface`)

**Location:** `src/ros2_ws/src/booster_ros2_interface/`

**Package structure:**
- **Messages** (`msg/`):
  - `Odometer.msg` — `float32 x, y, theta` (wheel odometry, vendor SDK internal)
  - `LowState.msg` / `LowCmd.msg` — vendor low-level state/command
  - `MotorState.msg` / `MotorCmd.msg` — per-motor state/command
  - `ImuState.msg` — IMU data
  - `BoosterApiReqMsg.msg` / `BoosterApiRespMsg.msg` — RPC request/response
  - `HandCommand.msg` / `HandDdsMsg.msg` / `HandParam.msg` — hand control
  - `RemoteControllerState.msg` — gamepad state
  - `ButtonEventMsg.msg` — button events
  - `RawBytesMsg.msg` / `RawBytesStamped.msg` — raw data transport
  - `FallDownState.msg` — fall detection state
- **Services** (`srv/`):
  - `RpcService.srv` — generic RPC
  - `AgentService.srv` — agent communication
- **Header:** `include/booster_interface/booster_interface/message_utils.hpp`
- **Build:** standard `ament_cmake` + `rosidl_default_generators` (CMakeLists.txt)

**Odom status (CORRECTED 2026-09-06 — live-verified; supersedes the "silent
placeholder" claim from the 2026-08-26 vendor audit):**
- `/Kev1n/odometer_state` (type `booster_interface/msg/Odometer`: float32 x, y, theta)
  **FLOWS at ~490 Hz** — live-verified: echo shows updating values, theta responds to motion.
- WHY the audit saw "eternal silence": `booster_interface` was never colcon-built, so
  `ros2 topic echo` failed silently on every past observation — no subscriber could ever
  exist. LESSON: a topic may only be called silent after its message type is built and a
  real subscriber has attached.
- Verified chain: K1 publishes `/odometer_state` (SSH topic list on robot) →
  `external_fleet_relay_Kev1n` subscribes → republishes `/Kev1n/odometer_state` here.
- `booster_interface` built 2026-09-06 (`colcon build --packages-select booster_interface`, 4.6s).
- Vendor-docs note (user, 2026-09-06): docs.booster.tech "Low-Level Topics" concern the
  C++ SDK transport (ChannelSubscriber) — `rt/odom`/`rt/odometer_state` are SDK-internal
  names, NOT ROS 2 topics to chase. The ROS 2 surface is what the robot's topic list shows.
- Bridge integration (2026-09-06): `hal_bridge` subscribes `<ns>/odometer_state` eagerly at
  boot, writes `shared_state/k1_odom.json` (atomic rename, 0.5 s cadence) and warns on
  mirror drift > 0.25 m vs the blue_1 sim twin (1 s debounce). K1 stays command-mirror of
  blue_1; `k1_bot` is deliberately NEVER injected into the LLM payload (phantom-assignment
  lesson round 4). `Worldstate.json` is off-limits for foreign entries — the aggregator
  rebuilds it at 10 Hz (entry would be wiped/raced).

**Integration status:**
- `booster_msgs` built in `ros2_ws` (RpcReqMsg for K1 control)
- `booster_ros2_interface` provides the full vendor message set
- K1 control via `/Kev1n/LocoApiTopicReq` (RPC, api_id 2000=stop, 2001=move, 2004=head)
- K1 mirror slot: `blue_1` (mirrors Y#1 commands, keeps own head for gestures)

**See also:** `docs/plans/v68_pre_ifa/k1_kick_head_vendor_audit.md` (K1 API status),
`src/booster/ASSETS.md` (K1 assets), `4_EDGE_HARDWARE_SIM2REAL.md` (K1 hardware specifics)
