#!/bin/bash
# Deploy the GoToBallAndKick skill node + k1_skills_msgs msg package
# to a K1 robot. Copies the node script, builds the msg package on-robot
# via colcon, and installs a systemd service for auto-start.
#
# Prerequisites (must be deployed first):
#   - deploy_relay.sh  — relay pair (external + internal) for /GoToBallAndKick
#   - deploy_vision.sh — vision node + vision_interface msg package
#
# Usage: ./deploy_skill.sh [OPTIONS] <Robot_IP> <Robot_Name>
# Example: ./deploy_skill.sh 10.42.0.122 Kev1n
#          ./deploy_skill.sh --no_auto_start 192.168.0.69 Kev1n

set -e

# =====================================================================
# Configuration
# =====================================================================
ROBOT_USER="booster"
SKILL_REMOTE_DIR="/home/booster/Workspace/skills"
MSG_WS_REMOTE_DIR="/home/booster/Workspace/ros2_ws"
AUTO_START=true
ROBOT_IP=""
ROBOT_NAME=""

# Resolve repo root (utils/scripts/ -> utils/ -> repo root)
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SKILL_SRC="${REPO_ROOT}/utils/skills/goToBallAndKick.py"
SKILL_SERVICE="${REPO_ROOT}/utils/skills/system/goto-ball-and-kick.service"
K1_SKILLS_MSGS_SRC="${REPO_ROOT}/core/src/ros2_ws/src/k1_skills_msgs"

# =====================================================================
# Help
# =====================================================================
show_help() {
    echo "Usage: $0 [OPTIONS] <Robot_IP> <Robot_Name>"
    echo ""
    echo "Deploy the GoToBallAndKick skill node to a K1 robot."
    echo "Copies the node script + k1_skills_msgs msg package, builds"
    echo "the msg package on-robot via colcon, and installs a systemd service."
    echo ""
    echo "Prerequisites (deploy first):"
    echo "  deploy_relay.sh   — relay pair for /GoToBallAndKick transport"
    echo "  deploy_vision.sh  — vision node + vision_interface (Ball.msg)"
    echo ""
    echo "Arguments:"
    echo "  <Robot_IP>      IP address of the K1 (e.g., 10.42.0.122)"
    echo "  <Robot_Name>    Namespace prefix for this robot (e.g., Kev1n)"
    echo ""
    echo "Options:"
    echo "  -h, --help       Show this help message and exit"
    echo "  --no_auto_start  Do not enable the service on boot (install only)"
    echo "  --no_build       Skip the colcon build (msg package already built)"
    echo ""
    echo "Examples:"
    echo "  $0 10.42.0.122 Kev1n"
    echo "  $0 --no_auto_start 192.168.0.69 Kev1n"
}

# =====================================================================
# Argument Parsing
# =====================================================================
DO_BUILD=true
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        --no_auto_start)
            AUTO_START=false
            shift
            ;;
        --no_build)
            DO_BUILD=false
            shift
            ;;
        *)
            if [ -z "$ROBOT_IP" ]; then
                ROBOT_IP="$1"
            elif [ -z "$ROBOT_NAME" ]; then
                ROBOT_NAME="$1"
            else
                echo "Error: Unknown parameter: $1"
                show_help
                exit 1
            fi
            shift
            ;;
    esac
done

if [ -z "$ROBOT_IP" ] || [ -z "$ROBOT_NAME" ]; then
    echo "Error: Missing required arguments <Robot_IP> and <Robot_Name>."
    echo ""
    show_help
    exit 1
fi

# =====================================================================
# Pre-flight checks
# =====================================================================
if [ ! -f "${SKILL_SRC}" ]; then
    echo "Error: GoToBallAndKick node not found at ${SKILL_SRC}"
    exit 1
fi
if [ ! -f "${SKILL_SERVICE}" ]; then
    echo "Error: systemd unit not found at ${SKILL_SERVICE}"
    exit 1
fi
if [ ! -d "${K1_SKILLS_MSGS_SRC}" ]; then
    echo "Error: k1_skills_msgs package not found at ${K1_SKILLS_MSGS_SRC}"
    exit 1
fi

# =====================================================================
# Deploy
# =====================================================================
echo "========================================================"
echo "Deploying GoToBallAndKick skill to ${ROBOT_NAME} at ${ROBOT_IP}"
echo "Auto-Start: ${AUTO_START} | Build msg package: ${DO_BUILD}"
echo "========================================================"

SSH_SOCKET="/tmp/skill_deploy_mux_${ROBOT_IP}"

echo "[1/7] Opening SSH connection to ${ROBOT_USER}@${ROBOT_IP}..."
ssh -M -S "${SSH_SOCKET}" -f -N "${ROBOT_USER}@${ROBOT_IP}"

# 2. Create remote directories
echo "[2/7] Creating remote directories..."
ssh -S "${SSH_SOCKET}" "${ROBOT_USER}@${ROBOT_IP}" \
    "mkdir -p ${SKILL_REMOTE_DIR} ${MSG_WS_REMOTE_DIR}/src"

# 3. Copy the skill node script
echo "[3/7] Copying GoToBallAndKick node..."
scp -o "ControlPath=${SSH_SOCKET}" \
    "${SKILL_SRC}" \
    "${ROBOT_USER}@${ROBOT_IP}:${SKILL_REMOTE_DIR}/"

# 4. Copy k1_skills_msgs msg package (for on-robot colcon build)
echo "[4/7] Copying k1_skills_msgs msg package..."
scp -r -o "ControlPath=${SSH_SOCKET}" \
    "${K1_SKILLS_MSGS_SRC}" \
    "${ROBOT_USER}@${ROBOT_IP}:${MSG_WS_REMOTE_DIR}/src/"

# 5. Build k1_skills_msgs on-robot (colcon)
if [ "${DO_BUILD}" = true ]; then
    echo "[5/7] Building k1_skills_msgs on K1..."
    ssh -S "${SSH_SOCKET}" -t "${ROBOT_USER}@${ROBOT_IP}" "
        cd ${MSG_WS_REMOTE_DIR}
        source /opt/ros/humble/setup.bash
        colcon build --packages-select k1_skills_msgs --symlink-install
    "
else
    echo "[5/7] Skipping colcon build (--no_build)"
fi

# 6. Copy + install systemd service
echo "[6/7] Installing systemd service..."
scp -o "ControlPath=${SSH_SOCKET}" \
    "${SKILL_SERVICE}" \
    "${ROBOT_USER}@${ROBOT_IP}:/tmp/goto-ball-and-kick.service"

ssh -S "${SSH_SOCKET}" -t "${ROBOT_USER}@${ROBOT_IP}" "
    echo '-> Substituting robot name (${ROBOT_NAME})...'
    sed -i 's/<Robot_Name>/${ROBOT_NAME}/g' /tmp/goto-ball-and-kick.service

    echo '-> Moving service file to /etc/systemd/system/...'
    sudo mv /tmp/goto-ball-and-kick.service /etc/systemd/system/
    sudo chown root:root /etc/systemd/system/goto-ball-and-kick.service
    sudo chmod 644 /etc/systemd/system/goto-ball-and-kick.service

    echo '-> Reloading systemd daemon...'
    sudo systemctl daemon-reload
"

# 7. Enable + start (or just install)
echo "[7/7] Configuring service..."
if [ "${AUTO_START}" = true ]; then
    ssh -S "${SSH_SOCKET}" -t "${ROBOT_USER}@${ROBOT_IP}" "
        sudo systemctl enable goto-ball-and-kick.service
        sudo systemctl restart goto-ball-and-kick.service
    "
    echo "Service enabled (auto-start on boot) + started."
else
    echo "Service installed but not enabled. Start manually:"
    echo "  ssh ${ROBOT_USER}@${ROBOT_IP} sudo systemctl start goto-ball-and-kick"
fi

# Cleanup
echo ""
echo "Cleaning up SSH connection..."
ssh -S "${SSH_SOCKET}" -O exit "${ROBOT_USER}@${ROBOT_IP}"

echo ""
echo "========================================================"
echo "Deployment Complete!"
echo "========================================================"
echo ""
echo "Verify on the K1:"
echo "  journalctl -u goto-ball-and-kick -f"
echo "  -> expect: 'Listening for commands on: /${ROBOT_NAME}/GoToBallAndKick'"
echo ""
echo "Verify from the host (maker4 PC):"
echo "  ros2 topic list | grep GoToBallAndKick"
echo "  -> expect: /${ROBOT_NAME}/GoToBallAndKick"
echo ""
echo "Prerequisites check:"
echo "  - Relay pair:  journalctl -u internal-relay -u external-relay (on K1)"
echo "  - Vision node: ros2 topic list | grep booster_soccer (on K1)"
echo "  - If vision is not deployed yet: ./deploy_vision.sh ${ROBOT_IP}"