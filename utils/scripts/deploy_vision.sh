#!/bin/bash
# Deploy the vision node + vision_interface msg package to a K1 robot.
# Copies source + model engines, then builds on-robot via colcon.
# No auto-start — run ros2 launch vision launch.py manually after deploy.
#
# Usage: ./deploy_vision.sh <Robot_IP> [Robot_User]
# Example: ./deploy_vision.sh 10.42.0.122 booster

set -e

# =====================================================================
# Configuration
# =====================================================================
ROBOT_IP="${1:?Usage: $0 <Robot_IP> [Robot_User]}"
ROBOT_USER="${2:-booster}"
REMOTE_DIR="/home/${ROBOT_USER}/Workspace/vision_ws"

# Resolve repo root (utils/scripts/ -> utils/ -> repo root)
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VISION_SRC="${REPO_ROOT}/utils/vision"
VISION_INTERFACE_SRC="${REPO_ROOT}/core/src/ros2_ws/src/vision_interface"

# =====================================================================
# Help
# =====================================================================
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    echo "Usage: $0 <Robot_IP> [Robot_User]"
    echo ""
    echo "Deploy the vision node to a K1 robot."
    echo "Copies vision_interface (msg package) + vision (perception node)"
    echo "including model engines, then builds on-robot via colcon."
    echo ""
    echo "No auto-start. After deploy, launch manually:"
    echo "  source ~/Workspace/vision_ws/install/setup.bash"
    echo "  ros2 launch vision launch.py"
    echo ""
    echo "Arguments:"
    echo "  <Robot_IP>    IP address of the K1 (e.g., 10.42.0.122)"
    echo "  [Robot_User]  SSH user (default: booster)"
    exit 0
fi

# =====================================================================
# Pre-flight checks
# =====================================================================
if [ ! -d "${VISION_SRC}" ]; then
    echo "Error: vision source not found at ${VISION_SRC}"
    exit 1
fi
if [ ! -d "${VISION_INTERFACE_SRC}" ]; then
    echo "Error: vision_interface not found at ${VISION_INTERFACE_SRC}"
    exit 1
fi

# =====================================================================
# Deploy
# =====================================================================
echo "========================================================"
echo "Deploying Vision to ${ROBOT_IP}"
echo "========================================================"

SSH_SOCKET="/tmp/vision_deploy_mux_${ROBOT_IP}"

echo "[1/6] Opening SSH connection to ${ROBOT_USER}@${ROBOT_IP}..."
ssh -M -S "${SSH_SOCKET}" -f -N "${ROBOT_USER}@${ROBOT_IP}"

echo "[2/6] Creating remote workspace..."
ssh -S "${SSH_SOCKET}" "${ROBOT_USER}@${ROBOT_IP}" "mkdir -p ${REMOTE_DIR}/src"

echo "[3/6] Copying vision_interface (msg package)..."
scp -r -o "ControlPath=${SSH_SOCKET}" \
    "${VISION_INTERFACE_SRC}" \
    "${ROBOT_USER}@${ROBOT_IP}:${REMOTE_DIR}/src/"

echo "[4/6] Copying vision package (source + config + models + thirdparty)..."
rsync -avz --delete \
    -e "ssh -o ControlPath=${SSH_SOCKET}" \
    --exclude='.git/' \
    --exclude='build/' \
    --exclude='install/' \
    --exclude='log/' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    --exclude='README.md' \
    --exclude='CHANGELOG' \
    --exclude='.clang-format' \
    "${VISION_SRC}/" \
    "${ROBOT_USER}@${ROBOT_IP}:${REMOTE_DIR}/src/vision/"

echo "[5/6] Writing build script..."
ssh -S "${SSH_SOCKET}" "${ROBOT_USER}@${ROBOT_IP}" "cat > ${REMOTE_DIR}/build_vision_on_k1.sh << 'BUILDEOF'
#!/bin/bash
set -e
cd ~/Workspace/vision_ws

source /opt/ros/humble/setup.bash
source /opt/booster/BoosterRos2/install/local_setup.bash
source /opt/booster/BoosterRos2Interface/install/setup.bash

echo \"Building vision_interface + vision...\"
colcon build --symlink-install \\
  --packages-select vision_interface vision \\
  --cmake-args -Wno-dev

echo \"\"
echo \"Build complete. Launch with:\"
echo \"  source ~/Workspace/vision_ws/install/setup.bash\"
echo \"  ros2 launch vision launch.py\"
BUILDEOF
chmod +x ${REMOTE_DIR}/build_vision_on_k1.sh"

echo "[6/6] Building on K1 (this takes a few minutes)..."
ssh -S "${SSH_SOCKET}" -t "${ROBOT_USER}@${ROBOT_IP}" "bash ${REMOTE_DIR}/build_vision_on_k1.sh"

echo ""
echo "Cleaning up SSH connection..."
ssh -S "${SSH_SOCKET}" -O exit "${ROBOT_USER}@${ROBOT_IP}"

echo ""
echo "========================================================"
echo "Deployment Complete!"
echo "========================================================"
echo ""
echo "Launch vision on the K1:"
echo "  source ~/Workspace/vision_ws/install/setup.bash"
echo "  ros2 launch vision launch.py"
echo ""
echo "Verify topics (from maker4 PC):"
echo "  ros2 topic list | grep booster_soccer"