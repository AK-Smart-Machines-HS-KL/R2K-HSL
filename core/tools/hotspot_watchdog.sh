#!/bin/bash
# Host-side watchdog: re-activates the WiFi hotspot after Intel BE200 AP resets.
#
# The BE200 on this desk resets in AP mode every few minutes
# (YAHBOOM_KNOWLEDGE.md radio note: supplicant-failed -> device removed,
# kernel "Internal hw_queue N is full!"). When the device reappears,
# NetworkManager does NOT reliably re-activate the Hotspot profile, so the
# robots find no AP and never rejoin ("yahboom never reconnects").
# This loop restores the hotspot within POLL_S seconds of a reset.
#
# Usage:  ./tools/hotspot_watchdog.sh [SSID] [PASSWORD]
#         (defaults match launch_r2k.sh: maker4 / nao12345)
# Run alongside ./launch_r2k.sh in its own terminal; Ctrl+C to stop.

HOTSPOT_SSID="${1:-maker4}"
HOTSPOT_PASS="${2:-nao12345}"
POLL_S=5

echo "hotspot_watchdog: ensuring hotspot '$HOTSPOT_SSID' (poll ${POLL_S}s, Ctrl+C to stop)"
while true; do
    if ! nmcli -t -f NAME,TYPE connection show --active 2>/dev/null | grep -q '^Hotspot:802-11-wireless$'; then
        # Wifi device may be absent mid-reset (firmware crash removes it)
        if nmcli device status 2>/dev/null | awk '$2=="wifi"{f=1} END{exit !f}'; then
            echo "[$(date +%H:%M:%S)] hotspot down - reactivating"
            if nmcli device wifi hotspot ssid "$HOTSPOT_SSID" password "$HOTSPOT_PASS" >/dev/null 2>&1; then
                echo "[$(date +%H:%M:%S)] hotspot reactivated - robots autoconnect on their own"
            else
                echo "[$(date +%H:%M:%S)] reactivation failed (device still resetting?)"
            fi
        else
            echo "[$(date +%H:%M:%S)] wifi device gone - waiting for firmware reset to finish"
        fi
    fi
    sleep "$POLL_S"
done
