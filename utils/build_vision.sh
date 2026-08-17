#!/bin/bash
# Clean rebuild of vision + interface packages for the remote robot.
# Usage: ./build_vision.sh [extra colcon args...]
set -e

cd "$(dirname "$0")"

source /opt/ros/humble/setup.bash

echo "[1/3] Removing build/, install/, log/"
rm -rf build install log

echo "[2/3] colcon build (vision_interface, booster_interface, booster_msgs, vision)"
colcon build --symlink-install \
  --packages-select vision_interface booster_interface booster_msgs vision \
  --cmake-args -Wno-dev \
  "$@"

echo "[3/3] Sourcing overlay"
source install/setup.bash

echo ""
echo "Build complete. Source the overlay with:"
echo "  source $(pwd)/install/setup.bash"
echo ""
echo "Launch vision:"
echo "  ros2 launch vision launch.py"