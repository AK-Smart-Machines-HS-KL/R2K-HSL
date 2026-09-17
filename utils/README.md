# R2K-HSL Utils

ROS 2 utility packages for the R2K-HSL robot stack — perception and topic relay.

## Structure

| Folder | Description |
|---|---|
| `vision/` | YOLOv8-based perception node (TensorRT/ONNX). Detects ball, goalposts, robots, and field markers; estimates 3D poses from camera + head pose. Publishes on `/booster_soccer/*` topics. See [`vision/README.md`](vision/README.md) for full documentation. |
| `ros2_relay/` | Python relay scripts that namespace-isolate per-robot topics on the K1. Deploys via SSH + systemd. See [`ros2_relay/README.md`](ros2_relay/README.md) for deployment instructions. |
| `scripts/` | Helper scripts for building, recording, and replaying camera data. Includes `build_vision.sh`, `record_vision.py` (ros2 bag recording), and `n12_converter.py` (NV12 to RGB for rqt_image_view). See [`scripts/README.md`](scripts/README.md) for replay instructions. |

## Msg Package Dependencies

The `vision` package depends on three ROS 2 msg packages that live in `core/src/ros2_ws/src/`:

| Package | Location | Description |
|---|---|---|
| `vision_interface` | `core/src/ros2_ws/src/vision_interface/` | Detection/ball/line-segment msgs consumed by the vision node |
| `booster_interface` | `core/src/ros2_ws/src/booster_ros2_interface/` | Low-level motor/IMU/odometer msgs + RPC service |
| `booster_msgs` | `core/src/ros2_ws/src/booster_msgs/` | Binary/RPC msgs used by the relay scripts |

`build_vision.sh` symlinks these into `utils/` at build time so colcon can resolve all dependencies in one workspace.

## Build

From this directory:

```bash
./scripts/build_vision.sh
```

This symlinks the ros2_ws msg packages into `utils/`, cleans `build/`/`install/`/`log/`, and runs `colcon build` for `vision_interface`, `booster_interface`, `booster_msgs`, and `vision`. See the script header for options.

## Launch

```bash
source install/setup.bash
ros2 launch vision launch.py
```