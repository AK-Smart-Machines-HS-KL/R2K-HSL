#!/bin/bash

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <Robot_IP> <Robot_Name>"
    echo "Example: $0 10.42.0.102 bot1"
    exit 1
fi

ROBOT_IP=$1
ROBOT_NAME=$2
ROBOT_USER="booster" 
SCRIPT_DIR="/home/booster/Workspace/ros2_relay" 

# =====================================================================
# IMPORTANT: Update this to the exact path of your fastdds_profile.xml 
# on the robot. This is what traps the un-prefixed topics!
# =====================================================================
PROFILE_PATH="/opt/booster/BoosterRos2/fastdds_profile.xml"

echo "Deploying to ${ROBOT_NAME} at ${ROBOT_IP}..."

ssh "${ROBOT_USER}@${ROBOT_IP}" << EOF
    
    # 1. Source the required ROS 2 workspaces
    source /opt/booster/BoosterRos2/install/local_setup.bash
    source /opt/booster/BoosterRos2Interface/install/setup.bash

    # 2. Kill old relays so we don't get duplicates/crosstalk
    pkill -f internal_relay.py
    pkill -f external_relay.py
    sleep 1

    echo "Starting Internal Relay (Isolated)..."
    # 3. Force the internal relay to use the restricted FastDDS profile!
    FASTRTPS_DEFAULT_PROFILES_FILE="${PROFILE_PATH}" nohup python3 ${SCRIPT_DIR}/internal_relay.py > ${SCRIPT_DIR}/internal_relay.log 2>&1 &
    
    echo "Starting External Relay (Public)..."
    # 4. Strip the profile for the external relay so it talks to the fleet
    FASTRTPS_DEFAULT_PROFILES_FILE="" nohup python3 ${SCRIPT_DIR}/external_relay.py ${ROBOT_NAME} > ${SCRIPT_DIR}/external_relay.log 2>&1 &
    
    echo "Both relays successfully launched!"
    
    exit
EOF

echo "Done. The un-prefixed topics should now be hidden."
