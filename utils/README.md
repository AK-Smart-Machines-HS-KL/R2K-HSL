# R2K-HSL Utils

ROS 2 utility packages for the R2K-HSL robot stack — perception, message definitions, and topic relay.

## Structure

| Folder | Description |
|---|---|
| `vision/` | YOLOv8-based perception node (TensorRT/ONNX). Detects ball, goalposts, robots, and field markers; estimates 3D poses from camera + head pose. Publishes on `/booster_soccer/*` topics. See [`vision/README.md`](vision/README.md) for full documentation. |
| `interface/` | ROS 2 message/service definitions (4 packages). `vision_interface` (detection/ball/line-segment msgs), `booster_ros2_interface` (package name `booster_interface` — low-level motor/IMU/odometer msgs + RPC service), `booster_msgs` (binary/RPC msgs), `game_controller_interface` (RoboCup game control data). Build dependency for `vision` and `brain`. |
| `ros2_relay/` | Python relay scripts that namespace-isolate per-robot topics on the K1. Deploys via SSH + systemd. See [`ros2_relay/README.md`](ros2_relay/README.md) for deployment instructions. |
| `scripts/` | Helper scripts for building, recording, and replaying camera data. Includes `build_vision.sh`, `record_vision.py` (ros2 bag recording), and `n12_converter.py` (NV12 to RGB for rqt_image_view). See [`scripts/README.md`](scripts/README.md) for replay instructions. |

## Build

From this directory:

```bash
./scripts/build_vision.sh
```

This cleans `build/`, `install/`, `log/` and runs `colcon build` for `vision_interface`, `booster_interface`, `booster_msgs`, and `vision`. See the script header for options.

Manual alternative:

```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install \
  --packages-select vision_interface booster_interface booster_msgs vision
```

## Launch

```bash
source install/setup.bash
ros2 launch vision launch.py
```