# Utils Scripts

Helper scripts for building, recording, and replaying camera data on the K1 robot.

## Files

| File | Description |
|---|---|
| `build_vision.sh` | Clean rebuild of vision + interface packages. Removes `build/`/`install/`/`log/` in `utils/`, runs `colcon build --packages-select vision_interface booster_interface booster_msgs vision`. Accepts extra colcon args (e.g. `./build_vision.sh --cmake-args -DBUILD_CALIBRATION=ON`). |
| `n12_converter.py` | ROS 2 node that subscribes to `/boostercamera/head/rgb` (NV12 encoding), converts to `rgb8` via OpenCV, and publishes on `/boostercamera/head/rgb_converted`. Needed because `rqt_image_view` cannot display NV12-encoded images directly. |
| `record_vision.py` | Records 15 seconds of `/boostercamera/head/rgb`, `/boostercamera/head/depth`, `/boostercamera/head/rgb/camera_info` to a ros2 bag directory named `booster_camera_recording/`. Sends SIGINT for clean bag closure. Edit `DURATION` and `OUTPUT_NAME` constants at the top of the file to customize. |
| `booster_camera_recording/` | Sample ros2 bag recording (14.3s, 879 messages, ~250MB). Contains `booster_camera_recording_0.db3` (sqlite3 storage) + `metadata.yaml`. 293 messages per topic. Gitignored (large binary) — record fresh bags with `record_vision.py` as needed. |

## Replaying a Ros2 Bag and Viewing in rqt_image_view

The K1 head camera publishes images in NV12 encoding, which `rqt_image_view` cannot display directly. The `n12_converter.py` node bridges this by converting NV12 to `rgb8` on a separate topic.

### Prerequisites

```bash
# Install rqt_image_view if not present
sudo apt install ros-humble-rqt-image-view

# Install cv_bridge if not present
sudo apt install ros-humble-cv-bridge
```

### Steps

**Terminal 1 — Start the NV12 converter:**

```bash
source /opt/ros/humble/setup.bash
cd ~/Workspace/R2K-HSL/utils
python3 scripts/n12_converter.py
```

This subscribes to `/boostercamera/head/rgb` (NV12) and publishes `/boostercamera/head/rgb_converted` (rgb8). Start it first so it is ready to receive frames when the bag plays.

**Terminal 2 — Open the image viewer:**

```bash
source /opt/ros/humble/setup.bash
ros2 run rqt_image_view rqt_image_view
```

In the rqt_image_view GUI, select `/boostercamera/head/rgb_converted` from the topic dropdown at the top. The raw `/boostercamera/head/rgb` topic will also appear but will display as a corrupted/garbled image because rqt_image_view does not decode NV12.

**Terminal 3 — Play the bag:**

```bash
source /opt/ros/humble/setup.bash
cd ~/Workspace/R2K-HSL/utils
ros2 bag play scripts/booster_camera_recording
```

The recorded frames appear in rqt_image_view in real time. Starting the converter and viewer first ensures you see the full recording from the first frame onward.

Add `--clock` if you want the replayed timestamps to drive `use_sim_time`:

```bash
ros2 bag play scripts/booster_camera_recording --clock
```

### Optional — Verify Camera Info

In a fourth terminal:

```bash
ros2 topic echo /boostercamera/head/rgb/camera_info
```

This confirms the `CameraInfo` messages are replaying correctly (intrinsics, distortion model, image dimensions).

### Optional — Replay into the Vision Node

To feed the replayed bag data into the vision node as if it were live camera input:

```bash
# Terminal 1: play bag with sim clock
ros2 bag play scripts/booster_camera_recording --clock

# Terminal 2: launch vision in sim mode
source ~/Workspace/R2K-HSL/utils/install/setup.bash
ros2 launch vision launch.py sim:=true
```

The vision node subscribes to the same `/boostercamera/head/*` topics and will process the replayed frames. Note that head pose (`/head_pose`) is not in the bag, so pose estimation will use stale/zero head pose unless you also replay or publish that topic.