# Vision

YOLOv8-based perception node for the R2K-HSL robot. Detects the ball, goalposts, robots, and field markers from a head camera, estimates 3D poses using camera intrinsics + head pose, and publishes results on `/booster_soccer/*` topics.

Built as an ament_cmake ROS 2 package. Inference runs on Nvidia TensorRT (real robot) or ONNX Runtime (no-CUDA machines).

## Directory Structure

```
vision/
├── CMakeLists.txt          # Top-level package build (NO_CUDA, BUILD_CALIBRATION, BUILD_TEST options)
├── package.xml             # ament_cmake package manifest
├── config/
│   ├── vision.yaml         # Main config: camera topics, model paths, thresholds, pose estimator params
│   └── field.yaml          # Field marker ground-truth positions (TCross, LCross, XCross, PenaltyPoint)
├── launch/
│   └── launch.py           # Launch file with all runtime arguments
├── model/                  # Pre-built TensorRT engines + ONNX models (Git LFS)
├── include/booster_vision/
│   ├── base/               # intrin.h, pose.h, pointcloud_process.h, data_syncer.hpp, data_logger.hpp
│   ├── model/              # detector.h, segmentor.h, data_types.h
│   │   ├── trt/            # TensorRT layer implementations (yololayer, preprocess, postprocess, calibrator)
│   │   └── onnx/           # ONNX Runtime implementations
│   ├── pose_estimator/     # pose_estimator.h, hungarian_matching.hpp
│   ├── calibration/        # board_detector.h, calibration.h, optimizor.hpp (aarch64 only)
│   ├── img_bridge.h        # Image format conversion (ROS msg <-> cv::Mat)
│   ├── color_classifier.hpp
│   └── vision_node.h
├── src/
│   ├── main.cpp            # Entry point: MultiThreadedExecutor (4 threads), intra-process comms
│   ├── vision_node.cpp     # VisionNode: config loading, subscriptions, inference pipeline, publishing
│   ├── img_bridge.cpp      # CompressedImage/raw Image <-> cv::Mat conversion
│   ├── base/               # intrin.cpp, pose.cpp, pointcloud_process.cpp, data_syncer.cpp
│   ├── model/
│   │   ├── detector.cc     # YoloV8Detector factory (selects TRT or ONNX backend)
│   │   ├── segmentor.cc    # YoloV8Segmentor factory
│   │   ├── trt/            # TensorRT backend: .cpp + .cu sources, yolov8_det/yolov8_seg executables
│   │   └── onnx/           # ONNX backend: detection_impl.cpp, segmentation_impl.cpp
│   ├── pose_estimator/     # pose_estimator.cpp (pixel->world via intrinsics + head pose)
│   └── calibration/        # Offline hand-eye calibration (aarch64 only, opt-in via BUILD_CALIBRATION)
├── scripts/
│   ├── install_onnxruntime.sh   # Downloads + installs ONNX Runtime C++ library
│   └── model/
│       ├── build_engine.sh      # Converts .pt -> .wts -> .engine via conda + ros2 run
│       ├── gen_wts.py           # PyTorch weight extraction
│       └── requirements.txt     # Conda env spec for engine building
├── thirdparty/
│   ├── include/            # Ceres + munkres-cpp headers
│   └── lib/                # Precompiled Ceres (aarch64 only; x86_64 binary, do NOT use on Jetson)
└── install_drvier.md       # Camera driver install notes (ZED, RealSense)
```

## Prerequisites

| Dependency | Version | Location |
|---|---|---|
| ROS 2 | Humble | `/opt/ros/humble` |
| OpenCV | 4.5+ | apt (`libopencv-dev`) |
| PCL | 1.12+ | apt (`libpcl-dev`) |
| yaml-cpp | 0.7+ | apt (`libyaml-cpp-dev`) |
| CUDA | 12.x | `/usr/local/cuda` |
| TensorRT | 8.6.1.6 | `/usr/local/TensorRT-8.6.1.6` |
| Booster Robotics SDK | — | `/usr/local/lib/libbooster_robotics_sdk.a` |
| FastRTPS + FastCDR | 2.13 / 2.x | `/usr/local/lib` |
| ONNX Runtime | 1.21+ | `/usr/local/lib` (only if `NO_CUDA=ON`) |
| Ceres | 2.2+ | apt (`libceres-dev`, only if `BUILD_CALIBRATION=ON`) |

Install ONNX Runtime (no-CUDA builds only):

```bash
./scripts/install_onnxruntime.sh
```

## Build

### Quick (from `utils/`)

```bash
./build_vision.sh
```

### Manual

```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install \
  --packages-select vision_interface booster_interface booster_msgs vision
```

The interface packages must be built first (or in the same colcon invocation — colcon resolves order from `package.xml` dependencies).

### CMake Options

| Option | Default | Description |
|---|---|---|
| `NO_CUDA` | `OFF` | Build with ONNX Runtime instead of TensorRT. Requires ONNX Runtime installed. |
| `BUILD_CALIBRATION` | `OFF` | Build the offline calibration tool. Requires Ceres (aarch64 only). |
| `BUILD_TEST` | `OFF` | Build googletest-based tests. |

Example — no-CUDA build with debug symbols:

```bash
colcon build --symlink-install --packages-select vision \
  --cmake-args -DNO_CUDA=ON -DCMAKE_BUILD_TYPE=RelWithDebInfo
```

Example — with calibration (aarch64 + Ceres installed):

```bash
colcon build --symlink-install --packages-select vision \
  --cmake-args -DBUILD_CALIBRATION=ON
```

## Configuration

All runtime config is in `config/vision.yaml`. Key sections:

### Camera

Topic names for 4 supported cameras (uncomment the one you use):

| Camera | Color topic | Depth topic | Info topic |
|---|---|---|---|
| d-robotics (K1 default) | `/boostercamera/head/rgb` | `/boostercamera/head/depth` | `/boostercamera/head/rgb/camera_info` |
| Simulation | `/camera/robot0_rgbd_camera/rgb/image_compressed` | `/camera/robot0_rgbd_camera/depth/image_raw` | `/camera/robot0_rgbd_camera/rgb/camera_info` |
| Orbbec | `/camera/color/image_raw` | `/camera/depth/image_raw` | `/camera/color/camera_info` |
| RealSense | `/camera/camera/color/image_raw` | `/camera/camera/aligned_depth_to_color/image_raw` | `/camera/camera/color/camera_info` |
| ZED | `/zed/zed_node/left/image_rect_color` | `/zed/zed_node/depth/depth_registered` | `/zed/zed_node/left/camera_info` |

Camera intrinsics in `camera.intrin` are fallback values; if a `camera_info` topic is available, the node subscribes and overrides them dynamically at runtime.

`camera.extrin` is the 4x4 transform from camera frame (x-right, y-down, z-forward) to head frame (x-forward, y-left, z-up). Pitch compensation is applied in code; this matrix only contains the physical offset.

### Detection Model

```yaml
detection_model:
  model_path: best_digua_second_10.3.engine   # bare filename resolves against share/vision/model/
  confidence_threshold: 0.2
  nms_threshold: 0.4
  classnames: [Ball, Goalpost, Person, LCross, TCross, XCross, PenaltyPoint, Opponent, BRMarker]
  post_process:
    single_ball_assumption: false
    confidence_thresholds:    # per-class override of the global threshold
      Ball: 0.2
      Opponent: 0.5
      ...
```

### Segmentation Model

```yaml
segmentation_model:
  model_path: best_seg_orin_10.3.engine
  confidence_threshold: 0.3
  nms_threshold: 0.9
```

If the segmentation model fails to load, the node continues without field-line publishing (`no segmentor loaded.` log message).

### Pose Estimators

- `ball_pose_estimator` — ball radius (0.109m), PCL clustering params (downsample leaf size, cluster distance, min cluster size, filter distance)
- `human_like_pose_estimator` — outlier removal params
- `field_marker_pose_estimator` — line segment area threshold for field marker detection

### Robot Name

```yaml
robot_name: ""   # empty = single robot, "robot0" = multi-robot (namespaces all topics with /robot0)
```

When set, all published/subscribed topics get a `/<robot_name>` suffix. In simulation mode, `robot0_rgbd_camera` in topic names is replaced with `<robot_name>_rgbd_camera`.

## Launch

### Real Robot (K1, d-robotics camera, TensorRT)

```bash
source install/setup.bash
ros2 launch vision launch.py
```

### Simulation

```bash
ros2 launch vision launch.py \
  sim:=true \
  color_topic:=/camera/robot0_rgbd_camera/rgb/image_compressed \
  depth_topic:=/camera/robot0_rgbd_camera/depth/image_raw \
  intrin_topic:=/camera/robot0_rgbd_camera/rgb/camera_info \
  detection_model_path:=install/vision/share/vision/model/sim_data_det_0126.onnx \
  segmentation_model_path:=install/vision/share/vision/model/sim_data_seg_0126.onnx
```

### Launch Arguments

| Argument | Default | Description |
|---|---|---|
| `sim` | `false` | Use simulation time (`use_sim_time`) |
| `color_topic` | `''` | Override color image topic (empty = use yaml) |
| `depth_topic` | `''` | Override depth image topic (empty = use yaml) |
| `intrin_topic` | `''` | Override camera info topic (empty = use yaml) |
| `detection_model_path` | `''` | Override detection model path (empty = use yaml) |
| `segmentation_model_path` | `''` | Override segmentation model path (empty = use yaml) |
| `show_det` | `false` | Show detection result window |
| `show_seg` | `false` | Show segmentation result window |
| `save_data` | `true` | Save received image data to log directory |
| `save_depth` | `true` | Save depth image data |
| `save_fps` | `2` | Frames saved per second |
| `offline_mode` | `false` | Subscribe to `/booster_soccer/t_head2base` instead of `/head_pose` (for replay/offline) |
| `vision_config_path` | `''` | Directory containing `vision.yaml` + `vision_local.yaml` (empty = package default) |

### Model Path Resolution

- Bare filename (e.g. `best_digua_second_10.3.engine`) — resolved against the installed `share/vision/model/` directory
- Absolute path (starts with `/`) — used as-is
- Launch arg overrides take precedence over yaml

## Published Topics

| Topic | Type | Description |
|---|---|---|
| `/booster_soccer/detection[/<robot_name>]` | `vision_interface/Detections` | All detected objects with pixel coords, radar coords, corner positions |
| `/booster_soccer/ball[/<robot_name>]` | `vision_interface/Ball` | Filtered ball pose (x, y, confidence) |
| `/booster_soccer/line_segments[/<robot_name>]` | `vision_interface/LineSegments` | Field line segments from segmentation (uv + world coords) |
| `/booster_soccer/t_head2base[/<robot_name>]` | `geometry_msgs/TransformStamped` | Head-to-base transform (published in online mode) |

## Subscribed Topics

| Topic | Type | Description |
|---|---|---|
| Camera color (from config) | `sensor_msgs/Image` or `CompressedImage` | Color image (raw or compressed, auto-detected from topic name) |
| Camera depth (from config) | `sensor_msgs/Image` or `CompressedImage` | Depth image (only if `use_depth: true`) |
| Camera info (from config) | `sensor_msgs/CameraInfo` | Intrinsics (overrides yaml at runtime) |
| `/head_pose[/<robot_name>]` | `geometry_msgs/Pose` | Robot head pose (online mode) |
| `/booster_soccer/cal_param[/<robot_name>]` | `vision_interface/CalParam` | Online calibration params (pitch/yaw/z compensation) |
| `/booster_soccer/t_head2base[/<robot_name>]` | `geometry_msgs/TransformStamped` | Head-to-base transform (offline mode only) |

## Model Files

All files in `model/` are tracked via Git LFS. After cloning, run:

```bash
git lfs install   # one-time
git lfs pull
```

If the files are 133 bytes (ASCII text with `version https://git-lfs.github.com/spec/v1`), LFS has not been pulled — the node will fail to load the engine and crash on first inference.

| File | Type | Description |
|---|---|---|
| `best_digua_second_10.3.engine` | TensorRT | Default detection model (JetPack 6.2) |
| `best_seg_orin_10.3.engine` | TensorRT | Default segmentation model (Orin) |
| `best_digua_10.3.engine` | TensorRT | Older detection model |
| `best_digua_1223_10.3.engine` | TensorRT | Older detection model |
| `best_seg_orin.engine` | TensorRT | Older segmentation model |
| `k1_realsense_10.3.engine` | TensorRT | Detection model for K1 + RealSense camera |
| `sim_data_det_0126.onnx` | ONNX | Detection model for simulation |
| `sim_data_seg_0126.onnx` | ONNX | Segmentation model for simulation |

### Building Custom Engines

To convert a PyTorch `.pt` model to a TensorRT `.engine`:

```bash
cd scripts/model
./build_engine.sh /path/to/model.pt
```

This requires a conda environment (`trt`) with PyTorch + Ultralytics. The script creates it automatically from `requirements.txt` if it doesn't exist. The output is written to `exported_model/model.engine`.

## Cameras

See `install_drvier.md` for driver installation notes (ZED on JetPack 6.0, RealSense built from source).

## Known Issues

- **Calibration subdirectory**: Skipped by default (`BUILD_CALIBRATION=OFF`). The bundled `thirdparty/lib/libceres.so` is an x86_64 binary and will not link on aarch64. To build calibration on Jetson, install Ceres natively (`sudo apt install libceres-dev`) and pass `-DBUILD_CALIBRATION=ON`.
- **Relative model paths**: The original `./src/vision/model/...` paths in `vision.yaml` only work when launching from the source-tree root. Use bare filenames (resolve against installed `share/vision/model/`) or pass absolute paths via launch args.
- **CUDA architecture warning**: `CMAKE_CUDA_ARCHITECTURES` is not set in the TRT CMakeLists. This produces a CMake warning but does not affect the build — NVCC auto-detects the current GPU architecture.