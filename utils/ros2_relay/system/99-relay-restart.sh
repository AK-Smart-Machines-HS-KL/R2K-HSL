#!/bin/bash
# NetworkManager dispatcher: restart DDS relays on any network change.
# FastDDS captures the interface list at process startup. If the relay services
# start before the network is up, or the network changes, FastDDS binds to stale
# interfaces and topics don't propagate. This script restarts the relays on any
# interface up/down event so FastDDS re-binds to the current interfaces.

INTERFACE="$1"
ACTION="$2"

# Only act on up/down events
if [ "$ACTION" != "up" ] && [ "$ACTION" != "down" ]; then
    exit 0
fi

# Only act on network interfaces (skip lo, docker, veth, etc.)
case "$INTERFACE" in
    lo|docker*|veth*|br-*) exit 0 ;;
esac

logger "NM dispatcher: $INTERFACE $ACTION, restarting DDS relays"
systemctl restart internal-relay.service
systemctl restart external-relay.service