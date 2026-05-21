#!/bin/bash

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <Robot_IP>"
    echo "Example: $0 10.42.0.102"
    exit 1
fi

ROBOT_IP=$1
ROBOT_USER="booster"

echo "Stopping relays on ${ROBOT_IP}..."

# Connect via SSH and kill both python scripts
ssh "${ROBOT_USER}@${ROBOT_IP}" << EOF
    pkill -f internal_relay.py
    pkill -f external_relay.py
    echo "Relays stopped successfully!"
    exit
EOF
