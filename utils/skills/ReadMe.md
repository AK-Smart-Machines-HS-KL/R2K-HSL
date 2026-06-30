# GoToBallAndKick

A lightweight, standalone ROS 2 Python node designed to be executed directly on the robot. It automates the target tracking and visual kick process by bridging high-level coordinate targets with continuous YOLO vision data.

---

## 1. Setup & Environment Variables

This script **must be executed on the robot's onboard computer**. Before launching the script, you must source the specific ROS 2 workspace paths and clear the Fast DDS local-only profile to allow network communication.

Run the following commands in your terminal:

```bash
# Source ROS 2 system and local workspaces
source /opt/booster/BoosterRos2/install/local_setup.bash
source /opt/booster/BoosterFaceDetection/install/setup.bash
source ~/Workspace/booster/robocup_demo/install/setup.bash

# Wipe the local-only Fast DDS network restrictions
unset FASTRTPS_DEFAULT_PROFILES_FILE
export ROS_LOCALHOST_ONLY=0

```

---

## 2. Node Usage

The node handles two major tasks automatically upon startup:

1. It registers a dynamic target listener based on the robot's name.
2. It safely polls and triggers **API ID 3000** over `/VisionApiTopicReq` to automatically wake up the onboard YOLO network.

### Execution

Run the standalone script using Python. You can pass the `robot_name` parameter dynamically at runtime:

```bash
python3 goToBallAndKick.py --ros-args -p robot_name:=Kev1n

```

### Triggering a Kick

Once running, the node sits in an idle state. To execute a kick, publish a custom `GoToBallAndKickCmd` message to the robot's localized topic.

For example, to command the robot `Kev1n` to perform a high-power **Goalshot** at coordinates $x=5.0$, $y=0.0$:

```bash
ros2 topic pub --once /Kev1n/GoToBallAndKick brain/msg/GoToBallAndKickCmd "{
  target_x: 5.0, 
  target_y: 0.0, 
  is_goalshot: true
}"

```

### How it Works Internally

* **Active Tracking:** Once a command is received, the node flags itself as active and begins listening to `/yolo_detection_server/detection_results`.
* **Continuous Updates:** For every frame where a `sports ball` is detected, the node dynamically recalculates the exact distance to your specified coordinates and streams execution variables to the lower-level `/kick_ball` controller.
* **Smart Power Scaling:** If `is_goalshot` is `true`, it applies maximum kicking power based on distance thresholds derived from the team's core strategic state machine. If `is_goalshot` is `false`, it scales a softer, proportional power calculation intended for passing.
