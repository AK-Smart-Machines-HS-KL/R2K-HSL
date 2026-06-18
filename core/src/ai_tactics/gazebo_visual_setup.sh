#!/bin/bash
# R2K Visual Field Painter

# Explicitly load ROS 2 inside this subshell
source /opt/ros/*/setup.bash 2>/dev/null
source /root/ros2k_test/ros2_ws/install/setup.bash 2>/dev/null

echo "🎨 Painting Gazebo Field markers..."
ros2 service list | grep -q "marker" && echo "✅ Marker service found." || echo "⚠️ Marker service missing."
