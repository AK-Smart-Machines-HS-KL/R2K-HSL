#!/bin/bash
UBUNTU_VERSION=$(lsb_release -rs)
echo "🛑 Beende ROS2K..."

if [ "$UBUNTU_VERSION" == "22.04" ]; then
    pkill -f "ros2 launch"
    pkill -f "gazebo"
    pkill -f "gzserver"
    pkill -f "gzclient"
    pkill -f "python3 ai_tactics"
    pkill -f "python3 r2k_"
    pkill -f "python3 rule_evaluator"
    pkill -f "python3 referee_node"
    sleep 2
    echo "✅ Alle nativen Prozesse beendet."
elif [ "$UBUNTU_VERSION" == "24.04" ]; then
    docker compose down
    echo "✅ Docker Container gestoppt."
fi
