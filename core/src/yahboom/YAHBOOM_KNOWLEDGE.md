# Yahboom Knowledge — ROS2K hardware notes (MicroROS-Pi5 class)

**Created:** 2026-08-29 | **Maintainer:** Prof-Adrian-Mueller
**Scope:** our two Yahboom diff-drive bots (MicroROS-Pi5 class) — interfaces, resources, POCs.
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
| Odometry | `<ns>/odom` (nav_msgs/Odometry), encoder-based, published by ESP32 | `odom_publisher` sample; team `wm.py` POC displays bot1+bot2 odom live |
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
