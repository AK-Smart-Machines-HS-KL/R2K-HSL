#!/bin/bash
# =====================================================================
# set_field_wifi.sh — RUNS ON THE K1 (Ubuntu 22.04, NetworkManager)
# ---------------------------------------------------------------------
# Installs/updates the 'field' WiFi profile with a STATIC IP taken from
# a field profile env file. Idempotent: safe to re-run.
#
# Validated target: Ubuntu 22.04 server/desktop with NetworkManager
# (the K1 relay deployment already installs NM dispatcher scripts).
#
# Usage (on the K1):
#   sudo bash set_field_wifi.sh <profile.env> --bot <N> [--exclusive]
#                          [--async-up | --skip-up]
#
#   <profile.env>   one of core/config/field_profiles/*.env
#   --bot N         which bot (selects FIELD_IP_N for the static IP)
#   --exclusive     set connection.autoconnect=no on ALL other wifi
#                   profiles -> the K1 joins ONLY this network
#   --async-up      schedule the activation (nohup + grace delay) so an
#                   SSH session riding the current wifi link closes
#                   cleanly BEFORE the link flaps (remote default)
#   --skip-up       install the profile but do not activate it
# =====================================================================
set -u

# Named constants (tuning without code archaeology)
ASYNC_GRACE_S=2        # async activation: delay before 'nmcli con up' so the SSH channel closes first
CON_UP_TIMEOUT_S=30    # nmcli activation timeout (sync-mode backstop)

usage() { sed -n '2,23p' "$0" | sed 's/^# \{0,1\}//'; exit 1; }

PROFILE_PATH=""
BOT=""
EXCLUSIVE=false
ASYNC_UP=false
SKIP_UP=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --bot)        BOT="$2"; shift 2 ;;
        --exclusive)  EXCLUSIVE=true; shift ;;
        --async-up)   ASYNC_UP=true; shift ;;
        --skip-up)    SKIP_UP=true; shift ;;
        -h|--help)    usage ;;
        *) if [ -z "$PROFILE_PATH" ]; then PROFILE_PATH="$1"; shift; else echo "Unknown arg: $1"; usage; fi ;;
    esac
done

[ -n "$PROFILE_PATH" ] && [ -n "$BOT" ] || { echo "ERROR: need <profile.env> and --bot N"; usage; }
if [ "$ASYNC_UP" = true ] && [ "$SKIP_UP" = true ]; then
    echo "ERROR: --async-up and --skip-up are mutually exclusive."
    exit 1
fi

# ---------------------------------------------------------------------
# 0. Load profile
# ---------------------------------------------------------------------
if [ ! -f "$PROFILE_PATH" ]; then
    echo "ERROR: profile file not found: $PROFILE_PATH"
    exit 1
fi
set -a
source "$PROFILE_PATH"
set +a

# Required fields
for V in FIELD_SSID FIELD_SECURITY FIELD_PREFIX FIELD_SUBNET; do
    [ -n "${!V}" ] || { echo "ERROR: $V not set in $PROFILE_PATH"; exit 1; }
done
case "$FIELD_SECURITY" in
    wpa-psk|sae) [ -n "${FIELD_PASS}" ] || { echo "ERROR: FIELD_PASS empty but FIELD_SECURITY=$FIELD_SECURITY"; exit 1; } ;;
    open) : ;;
    *) echo "ERROR: FIELD_SECURITY must be wpa-psk | sae | open (got: '$FIELD_SECURITY')"; exit 1 ;;
esac

# ---------------------------------------------------------------------
# 1. RULE GATE: real matches => FIELD_DEBUG_IP MUST be empty
#    (Rules §3.9: laptop access/remote processing during play is a
#     violation; debug exception is wired-only, <=1 pkt/s, §3.9.5.)
# ---------------------------------------------------------------------
if [ "${VENUE:-lab}" = "match" ] && [ -n "${FIELD_DEBUG_IP:-}" ]; then
    echo "=============================================================="
    echo "REFUSED: profile '$(basename "$PROFILE_PATH")' has VENUE=match"
    echo "         but FIELD_DEBUG_IP='${FIELD_DEBUG_IP}' is set."
    echo "         Accessing a robot via laptop during a real match is a"
    echo "         RULE VIOLATION (Rules §3.9; wired debug exception <=1"
    echo "         pkt/s per robot, §3.9.5)."
    echo "         Fix: clear FIELD_DEBUG_IP in the venue profile."
    echo "=============================================================="
    exit 2
fi

# ---------------------------------------------------------------------
# 2. Environment sanity (loud failures — no silent partial installs)
# ---------------------------------------------------------------------
if ! command -v nmcli >/dev/null 2>&1; then
    echo "ERROR: nmcli not found — K1 must run Ubuntu 22.04 with NetworkManager."
    exit 1
fi

IFC=$(nmcli -t -f DEVICE,TYPE,STATE device status 2>/dev/null | awk -F: '$2=="wifi"{print $1; exit}')
if [ -z "$IFC" ]; then
    # iw fallback (device may be in managed-but-idle state)
    IFC=$(iw dev 2>/dev/null | awk '$1=="Interface"{print $2; exit}')
fi
if [ -z "$IFC" ]; then
    echo "ERROR: no WiFi interface found (expected wlan0 or wlp*)."
    exit 1
fi
echo "WiFi interface: $IFC"

# Static IP for this bot
OCTET_VAR="FIELD_IP_${BOT}"
OCTET="${!OCTET_VAR:-}"
if [ -z "$OCTET" ]; then
    echo "ERROR: ${OCTET_VAR} not set in $PROFILE_PATH"
    exit 1
fi
BOT_IP="${FIELD_PREFIX}.${OCTET}"
echo "Bot ${BOT} -> static IP: ${BOT_IP}/${FIELD_SUBNET}"

# ---------------------------------------------------------------------
# 3. (Re)install the 'field' connection profile
#    delete+add = idempotent, no stale properties from older profiles
# ---------------------------------------------------------------------
echo "-> Removing stale 'field' profile (if any)..."
nmcli con delete field >/dev/null 2>&1 || true

# Security args go into 'con add' directly: secrets attached at creation
# are stored system-owned (password-flags=0). A post-add 'con mod' can
# leave them agent-owned (password-flags=1), which makes non-interactive
# 'nmcli con up' fail with "Secrets were required, but not provided".
CREATION_ARGS=(
    type wifi con-name field ifname "$IFC" ssid "$FIELD_SSID"
    802-11-wireless.powersave 2
    802-11-wireless.cloned-mac-address permanent
    802-11-wireless.mtu 0
    ipv4.method manual ipv4.addresses "${BOT_IP}/${FIELD_SUBNET}"
    ipv4.never-default yes
)
if [ "$FIELD_SECURITY" != "open" ]; then
    CREATION_ARGS+=(
        802-11-wireless-security.key-mgmt "$FIELD_SECURITY"
        802-11-wireless-security.psk "$FIELD_PASS"
    )
else
    CREATION_ARGS+=( 802-11-wireless-security.key-mgmt none )
fi

echo "-> Creating 'field' profile (SSID: $FIELD_SSID, security: $FIELD_SECURITY)..."
if ! nmcli con add "${CREATION_ARGS[@]}"; then
    echo "ERROR: nmcli con add failed."
    exit 1
fi

if [ -n "${FIELD_GATEWAY:-}" ]; then
    echo "-> Gateway requested: $FIELD_GATEWAY"
    nmcli con mod field ipv4.never-default no ipv4.gateway "$FIELD_GATEWAY"
fi

# ---------------------------------------------------------------------
# 4. --exclusive: ONLY this network. All other wifi profiles become
#    autoconnect=no so the K1 never drifts back to maker4 or any lab AP.
# ---------------------------------------------------------------------
if [ "$EXCLUSIVE" = true ]; then
    echo "-> Locking down: disabling autoconnect on every OTHER wifi profile..."
    OTHERS=$(nmcli -t -f NAME,TYPE connection show | awk -F: '$2=="802-11-wireless" && $1!="field"{print $1}')
    if [ -n "$OTHERS" ]; then
        while IFS= read -r name; do
            [ -n "$name" ] || continue
            echo "   - $name -> autoconnect no"
            nmcli con mod "$name" connection.autoconnect no
        done <<< "$OTHERS"
    else
        echo "   (no other wifi profiles found)"
    fi
fi

# ---------------------------------------------------------------------
# 5. Bring it up + print end state
#    --skip-up: install only. --async-up: schedule the activation with a
#    grace delay so an SSH session riding the current wifi link closes
#    cleanly BEFORE the link flaps. Default: synchronous activation.
# ---------------------------------------------------------------------
if [ "$SKIP_UP" = true ]; then
    echo "-> Activation skipped (--skip-up). Profile is installed;"
    echo "   the K1 will auto-connect when the network appears (autoconnect=yes)."
elif [ "$ASYNC_UP" = true ]; then
    echo "-> Scheduling 'field' activation (async — wifi link will flap in ~${ASYNC_GRACE_S}s)..."
    nohup sh -c "sleep ${ASYNC_GRACE_S}; nmcli con up field --timeout ${CON_UP_TIMEOUT_S}" \
        >/tmp/r2k_activate.log 2>&1 < /dev/null &
    echo "   Activation scheduled; this SSH session can close cleanly now."
    echo "   Activation log on the K1: /tmp/r2k_activate.log"
else
    echo "-> Activating 'field' profile (may fail if SSID out of range — not fatal)..."
    if nmcli con up field --timeout "${CON_UP_TIMEOUT_S}"; then
        echo "   Connected."
    else
        echo "   WARN: could not activate now (SSID out of range?). Profile is installed;"
        echo "         the K1 will auto-connect when the network appears."
    fi
fi

echo "--------------------------------------------------------------"
echo "End state of 'field' profile:"
nmcli -f connection.autoconnect,802-11-wireless.ssid,802-11-wireless.cloned-mac-address,802-11-wireless.powersave,802-11-wireless-security.key-mgmt,ipv4.method,ipv4.addresses,ipv4.never-default con show field
echo "--------------------------------------------------------------"
nmcli -t -f NAME,DEVICE,TYPE connection show --active | grep -i ':wifi' || echo "(no active wifi connection)"
