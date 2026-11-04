#!/bin/bash
# =====================================================================
# wifi_check.sh — RUNS ON THE K1 (or via SSH from the laptop)
# ---------------------------------------------------------------------
# Validates the 'field' wifi profile against a field profile env file
# and the RoboCup HSL Rules (network-relevant subset).
#
# Usage:
#   sudo bash wifi_check.sh <profile.env> [--bot N] [--ping-peers]
#
#   <profile.env>   the same profile used by set_field_wifi.sh
#   --bot N         expected static IP = FIELD_IP_N (recommended: pass it)
#   --ping-peers    ping every other bot from the profile (round-trip table)
#
# Exit code 0 = all PASS. Any FAIL -> exit 1.
# =====================================================================
set -u

PROFILE_PATH=""
BOT=""
PING_PEERS=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --bot)        BOT="$2"; shift 2 ;;
        --ping-peers) PING_PEERS=true; shift ;;
        -h|--help)    sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; exit 1 ;;
        *) if [ -z "$PROFILE_PATH" ]; then PROFILE_PATH="$1"; shift; else echo "Unknown arg: $1"; exit 1; fi ;;
    esac
done

[ -n "$PROFILE_PATH" ] || { echo "ERROR: need <profile.env>"; exit 1; }

FAILS=0
WARNS=0
ok()   { echo "  PASS  $1"; }
fail() { echo "  FAIL  $1"; FAILS=$((FAILS+1)); }
warn() { echo "  WARN  $1"; WARNS=$((WARNS+1)); }

# ---------------------------------------------------------------------
# 0. Load profile + rule gate
# ---------------------------------------------------------------------
set -a
source "$PROFILE_PATH"
set +a

if [ "${VENUE:-lab}" = "match" ] && [ -n "${FIELD_DEBUG_IP:-}" ]; then
    echo "  FAIL  FIELD_DEBUG_IP is set on a VENUE=match profile — accessing robots"
    echo "        via laptop during a REAL MATCH is a RULE VIOLATION (Rules §3.9;"
    echo "        debug is WIRED ONLY, <=1 pkt/s per robot, §3.9.5)."
    FAILS=$((FAILS+1))
else
    ok "FIELD_DEBUG_IP rule gate (VENUE=${VENUE:-lab}, DEBUG_IP='${FIELD_DEBUG_IP:-}')"
fi

# ---------------------------------------------------------------------
# 1. Connection + interface
# ---------------------------------------------------------------------
if ! command -v nmcli >/dev/null 2>&1; then echo "  FAIL  nmcli not found"; exit 1; fi

ACT=$(nmcli -t -f NAME,TYPE,DEVICE connection show --active | grep ':802-11-wireless:' | head -1 || true)
ACT_NAME="${ACT%%:*}"
ACT_IFC="${ACT##*:}"
if [ "$ACT_NAME" = "field" ] && [ -n "$ACT_IFC" ]; then
    ok "active wifi connection is 'field' on $ACT_IFC"
else
    fail "active wifi is not the 'field' profile (got: '${ACT_NAME:-none}' / '${ACT_IFC:-none}')"
fi

aw() { nmcli -g "802-11-wireless.$1" con show field 2>/dev/null | head -1; }

SSID=$(aw ssid)
if [ "$SSID" = "$FIELD_SSID" ]; then ok "SSID matches profile ('$SSID')"; else fail "SSID mismatch (active '$SSID' != profile '$FIELD_SSID')"; fi

# ---------------------------------------------------------------------
# 2. Managed mode only — ad-hoc is prohibited (Rules §3.9.3)
# ---------------------------------------------------------------------
MODE=$(iw dev "$ACT_IFC" info 2>/dev/null | awk '/^ *type/{print $2}')
if [ "$MODE" = "managed" ]; then
    ok "interface mode is managed (no ad-hoc — §3.9.3)"
else
    fail "interface mode is '$MODE' (must be 'managed' — ad-hoc prohibited, §3.9.3)"
fi

# ---------------------------------------------------------------------
# 3. Static IP correctness
# ---------------------------------------------------------------------
ACTUAL_IP=$(ip -4 -o addr show dev "$ACT_IFC" 2>/dev/null | awk '$2!="lo"{print $4; exit}')
EXPECT_IP=""
if [ -n "$BOT" ]; then
    V="FIELD_IP_${BOT}"
    F="${!V:-}"
    if [ -n "$F" ]; then
        EXPECT_IP="${FIELD_PREFIX}.${F}"
    else
        warn "FIELD_IP_${BOT} not set in profile — cannot verify the assignment"
    fi
fi
if [ -n "$EXPECT_IP" ]; then
    if [ "$ACTUAL_IP" = "$EXPECT_IP/${FIELD_SUBNET}" ]; then
        ok "static IP as assigned: $ACTUAL_IP"
    else
        fail "IP mismatch (active '$ACTUAL_IP' != expected '$EXPECT_IP/${FIELD_SUBNET}')"
    fi
else
    ok "static IP active: $ACTUAL_IP (pass --bot N to compare against the assignment)"
fi

# ---------------------------------------------------------------------
# 4. No default route on the field (unless the profile allows it)
# ---------------------------------------------------------------------
DEFROUTE=$(ip route show default 2>/dev/null | head -1)
if [ -n "${FIELD_GATEWAY:-}" ]; then
    [ -n "$DEFROUTE" ] && ok "default route present as configured: $DEFROUTE" || warn "FIELD_GATEWAY set but no default route"
else
    if [ -z "$DEFROUTE" ]; then ok "no default route (robots need no internet on the field)"; else warn "unexpected default route: $DEFROUTE"; fi
fi

# ---------------------------------------------------------------------
# 5. Radio tuning + hardening
# ---------------------------------------------------------------------
PS=$(iw dev "$ACT_IFC" get power_save 2>/dev/null | awk '{print $2}')
if [ "$PS" = "off" ]; then ok "wifi powersave OFF (latency)"; else warn "wifi powersave is '$PS' in interface; profile value: $(nmcli -g 802-11-wireless.powersave con show field)"; fi

CMAC=$(nmcli -g 802-11-wireless.cloned-mac-address con show field 2>/dev/null)
[ "$CMAC" = "permanent" ] && ok "MAC stays permanent/stable per bot" || warn "cloned-mac-address is '$CMAC' (should be permanent)"

# ---------------------------------------------------------------------
# 6. Single-network lock: no OTHER profile autoconnects
# ---------------------------------------------------------------------
OTHER=0
while IFS= read -r line; do
    name="${line%%:*}"
    [ "$name" = "field" ] && continue
    ac=$(nmcli -g connection.autoconnect con show "$name" 2>/dev/null)
    if [ "$ac" = "yes" ]; then
        warn "other wifi profile allows autoconnect: '$name' (K1 could drift away — run set_field_wifi.sh --exclusive)"
        OTHER=$((OTHER+1))
    fi
done < <(nmcli -t -f NAME,TYPE connection show | awk -F: '$2=="802-11-wireless" && $1!="field"{print $1}')
[ "$OTHER" -eq 0 ] && ok "no other wifi profile will steal the connection"

# ---------------------------------------------------------------------
# 7. Peer reachability (full bot matrix from the profile)
# ---------------------------------------------------------------------
if [ "$PING_PEERS" = true ]; then
    echo ""
    echo "Peer ping matrix:"
    for i in 1 2 3 4 5 6; do
        V="FIELD_IP_${i}"
        IP_N="${!V:-}"
        [ -n "$IP_N" ] || continue
        if [ -n "$BOT" ] && [ "$i" = "$BOT" ]; then
            echo "   bot $i (${FIELD_PREFIX}.${IP_N}): (this bot)"
            continue
        fi
        if ping -c 1 -W 1 "${FIELD_PREFIX}.${IP_N}" >/dev/null 2>&1; then
            echo "   bot $i (${FIELD_PREFIX}.${IP_N}): reachable"
        else
            echo "   bot $i (${FIELD_PREFIX}.${IP_N}): NOT reachable"
            FAILS=$((FAILS+1))
        fi
    done
fi

echo ""
if [ "$FAILS" -eq 0 ]; then
    echo "RESULT: OK (warns: $WARNS)"
    exit 0
else
    echo "RESULT: FAILED (fails: $FAILS, warns: $WARNS)"
    exit 1
fi
