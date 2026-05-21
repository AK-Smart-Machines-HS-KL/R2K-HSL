#!/bin/bash

# =====================================================================
# Configuration Variables
# =====================================================================
ROBOT_USER="booster"
REMOTE_DIR="/home/booster/Workspace/ros2_relay"
AUTO_START=true
ROBOT_IP=""
ROBOT_NAME=""

# =====================================================================
# Help Function
# =====================================================================
show_help() {
    echo "Usage: $0 [OPTIONS] <Robot_IP> <Robot_Name>"
    echo ""
    echo "Deploy and configure ROS 2 DDS relays to the Booster robot."
    echo ""
    echo "Arguments:"
    echo "  <Robot_IP>        The IP address of the robot (e.g., 10.42.0.102)"
    echo "  <Robot_Name>      The namespace prefix for this robot (e.g., bot2)"
    echo ""
    echo "Options:"
    echo "  -h, --help        Show this help message and exit"
    echo "  --no_auto_start   Do not configure systemctl to auto-start the services on boot"
    echo ""
    echo "Examples:"
    echo "  $0 10.42.0.102 bot2"
    echo "  $0 --no_auto_start 10.42.0.102 bot2"
}

# =====================================================================
# Argument Parsing
# =====================================================================
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
        *)
            if [ -z "$ROBOT_IP" ]; then
                ROBOT_IP="$1"
            elif [ -z "$ROBOT_NAME" ]; then
                ROBOT_NAME="$1"
            else
                echo "Error: Unknown parameter passed: $1"
                show_help
                exit 1
            fi
            shift
            ;;
    esac
done

# Check if required arguments are provided
if [ -z "$ROBOT_IP" ] || [ -z "$ROBOT_NAME" ]; then
    echo "Error: Missing required arguments <Robot_IP> and <Robot_Name>."
    echo ""
    show_help
    exit 1
fi

# =====================================================================
# Deployment Steps
# =====================================================================
echo "========================================================"
echo "Deploying Relay System to ${ROBOT_NAME} at ${ROBOT_IP}"
echo "Auto-Start enabled: ${AUTO_START}"
echo "========================================================"

# 1. Create the remote workspace directory if it doesn't exist
echo "[1/4] Creating workspace directory on the robot..."
ssh ${ROBOT_USER}@${ROBOT_IP} "mkdir -p ${REMOTE_DIR}"

# 2. Copy the Python relay scripts directly to the workspace
echo "[2/4] Copying Python relay files..."
scp ./internal_relay.py ./external_relay.py ${ROBOT_USER}@${ROBOT_IP}:${REMOTE_DIR}/

# 3. Copy the service files to the robot's /tmp folder first (since /etc requires sudo)
echo "[3/4] Copying systemd service files..."
scp ./system/internal-relay.service ./system/external-relay.service ${ROBOT_USER}@${ROBOT_IP}:/tmp/

# 4. Execute remote commands to finalize setup
echo "[4/4] Configuring systemd (may ask for robot's sudo password)..."
ssh -t ${ROBOT_USER}@${ROBOT_IP} "
    echo '-> Updating robot name to ${ROBOT_NAME} in service file...'
    # Replaces the new <Robot_Name> placeholder in the ExecStart line
    sed -i 's/<Robot_Name>/${ROBOT_NAME}/g' /tmp/external-relay.service

    echo '-> Moving service files to /etc/systemd/system/...'
    sudo mv /tmp/internal-relay.service /etc/systemd/system/
    sudo mv /tmp/external-relay.service /etc/systemd/system/

    echo '-> Setting correct file permissions...'
    sudo chown root:root /etc/systemd/system/internal-relay.service
    sudo chown root:root /etc/systemd/system/external-relay.service
    sudo chmod 644 /etc/systemd/system/internal-relay.service
    sudo chmod 644 /etc/systemd/system/external-relay.service

    echo '-> Reloading systemd daemon...'
    sudo systemctl daemon-reload

    if [ \"${AUTO_START}\" = true ]; then
        echo '-> Enabling services to start automatically on boot...'
        sudo systemctl enable internal-relay.service
        sudo systemctl enable external-relay.service
    else
        echo '-> Skipping auto-start configuration (--no_auto_start flag used).'
    fi

    echo '-> Starting services now...'
    sudo systemctl restart internal-relay.service
    sudo systemctl restart external-relay.service

    echo '-> Checking status...'
    sudo systemctl is-active internal-relay.service
    sudo systemctl is-active external-relay.service
"

echo "========================================================"
echo "Deployment Complete! The relays are now running."
echo "========================================================"
