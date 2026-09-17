#!/bin/bash
# Clean rebuild of vision + interface packages for the remote robot.
# Msg packages (booster_msgs, booster_ros2_interface, vision_interface) live
# in core/src/ros2_ws/src/. This script symlinks them into utils/ so colcon
# can build them alongside utils/vision/ in one workspace.
#
# Usage: ./build_vision.sh [extra colcon args...]
set -e

cd "$(dirname "$0")/.."

source /opt/ros/humble/setup.bash

echo "[1/4] Symlinking ros2_ws msg packages into workspace"
ln -sf ../core/src/ros2_ws/src/booster_msgs booster_msgs
ln -sf ../core/src/ros2_ws/src/booster_ros2_interface booster_ros2_interface
ln -sf ../core/src/ros2_ws/src/vision_interface vision_interface

echo "[2/4] Removing build/, install/, log/"
rm -rf build install log

echo "[3/4] colcon build (vision_interface, booster_interface, booster_msgs, vision)"
colcon build --symlink-install \
  --packages-select vision_interface booster_interface booster_msgs vision \
  --cmake-args -Wno-dev \
  "$@"

echo "[4/4] Sourcing overlay"
source install/setup.bash

echo ""
echo "Build complete. Source the overlay with:"
echo "  source $(pwd)/install/setup.bash"
echo ""
echo "Launch vision:"
echo "  ros2 launch vision launch.py"