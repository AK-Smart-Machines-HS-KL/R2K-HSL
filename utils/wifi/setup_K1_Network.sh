#!/bin/bash
# =====================================================================
# setup_K1_Network.sh — RUNS FROM THE LAPTOP (provisioning, pre-match)
# ---------------------------------------------------------------------
# Pushes a field profile + set_field_wifi.sh to each K1 via SSH and
# installs the static-IP wifi profile there. Mirrors the proven SSH
# pattern of utils/ros2_relay/deploy_relay.sh (master connection, scp,
# tmp-copy, sudo execution).
#
# THIS IS PROVISIONING ONLY. It must be run BEFORE a match (network
# setup), never during play — Rules §3.9 forbids any laptop access
# during a match.
#
# Usage:
#   setup_K1_Network.sh [OPTIONS] <Robot_IP> <bot_number>
#       Single bot: robot currently reachable at <Robot_IP> (e.g. on the
#       lab/old network), gets wifi profile for bot <bot_number>.
#
#   setup_K1_Network.sh [OPTIONS] --profile <P> --bot <N> <Robot_IP>
#       Same, explicit profile name.
#
#   setup_K1_Network.sh [OPTIONS] --all --profile <P>
#       ALL bots: SSH targets are the PROFILE static IPs (works for
#       re-provisioning/updating; first-time flash run per-bot against
#       its current discovery IP).
#
# Options:
#   -h, --help              show help
#   --profile <name>        field profile from core/config/field_profiles/
#                           (default: $FIELD_PROFILE env, else 'lab')
#   --all                   provision every bot in the profile (statics as targets)
#   --exclusive             other wifi profiles on the K1 get autoconnect=no
#                           -> K1 joins ONLY this network
#   --skip-up               do not run 'nmcli con up' remotely
#                           (profile installed, activates later)
#
# Sudo password: env BOT_SUDO_PASS (default 123456, as documented in
# utils/ros2_relay/README.md).
# =====================================================================
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PROFILES_DIR="$REPO_ROOT/core/config/field_profiles"
CURRENT_PROFILE_FILE="$PROFILES_DIR/.current_profile"

ROBOT_USER="booster"
BOT_SUDO_PASS="${BOT_SUDO_PASS:-123456}"

PROFILE=""
EXCLUSIVE=""
SKIP_UP=""
TARGET_IP=""
TARGET_BOT=""

usage() { sed -n '2,48p' "$0" | sed 's/^# \{0,1\}//'; exit 1; }

while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)     usage ;;
        --profile)     PROFILE="$2"; shift 2 ;;
        --bot)         TARGET_BOT="$2"; shift 2 ;;
        --all)         TARGET_BOT="all"; shift ;;
        --exclusive)   EXCLUSIVE="--exclusive"; shift ;;
        --skip-up)     SKIP_UP="DNORUN"; shift ;;
        *) if [ -z "$TARGET_IP" ]; then TARGET_IP="$1"; shift; else echo "Unknown arg: $1"; usage; fi ;;
    esac
done
[ -n "$SKIP_UP" ] && SKIP_UP="--skip-up"

# ---------------------------------------------------------------------
# 0. Resolve profile
# ---------------------------------------------------------------------
PROFILE="${PROFILE:-${FIELD_PROFILE:-lab}}"
if [[ "$PROFILE" == */* ]]; then
    PROFILE_FILE="$PROFILE"
else
    PROFILE_FILE="$PROFILES_DIR/${PROFILE}.env"
fi
if [ ! -f "$PROFILE_FILE" ]; then
    echo "ERROR: profile not found: $PROFILE_FILE"
    echo "Available profiles:"
    ls -1 "$PROFILES_DIR"/*.env 2>/dev/null | xargs -n1 basename || echo "  (none)"
    exit 1
fi

# Source profile for IP map + rule gate
set -a
source "$PROFILE_FILE"
set +a

# ---------------------------------------------------------------------
# 1. RULE GATE: real matches => FIELD_DEBUG_IP MUST be empty
#    (Rules §3.9: laptop access / remote processing during play is a
#     violation; wired debug exception <=1 pkt/s per robot, §3.9.5.)
# ---------------------------------------------------------------------
if [ "${VENUE:-lab}" = "match" ] && [ -n "${FIELD_DEBUG_IP:-}" ]; then
    echo "=============================================================="
    echo "REFUSED: profile '$PROFILE' has VENUE=match but FIELD_DEBUG_IP"
    echo "         is set ('${FIELD_DEBUG_IP}')."
    echo "         Accessing robots via laptop during a REAL MATCH is a"
    echo "         RULE VIOLATION (Rules §3.9; debug is WIRED ONLY <=1"
    echo "         pkt/s per robot, §3.9.5)."
    echo "         Fix: clear FIELD_DEBUG_IP in $(basename "$PROFILE_FILE")."
    echo "=============================================================="
    exit 2
fi

# ---------------------------------------------------------------------
# 1a. Argument sanity
# ---------------------------------------------------------------------
if [ "$TARGET_BOT" = "all" ]; then
    if [ -n "$TARGET_IP" ]; then
        echo "NOTE: <Robot_IP> is ignored in --all mode (targets are the profile statics)."
        TARGET_IP=""
    fi
    echo "Profile: $PROFILE | mode: --all (bots 1..6 with set FIELD_IP_N)"
    BOT_LIST=()
    for i in 1 2 3 4 5 6; do
        V="FIELD_IP_${i}"
        [ -n "${!V:-}" ] && BOT_LIST+=("$i")
    done
    [ ${#BOT_LIST[@]} -gt 0 ] || { echo "ERROR: profile has no FIELD_IP_N entries."; exit 1; }
else
    # single bot: build BOT_LIST from positional
    BOT_LIST=()
    [ -n "$TARGET_BOT" ] || { echo "ERROR: need --bot <N> (or --all)."; usage; }
    [ -n "$TARGET_IP" ] || { echo "ERROR: single-bot mode needs <Robot_IP>."; usage; }
    BOT_LIST+=("$TARGET_BOT")
    echo "Profile: $PROFILE | target: $TARGET_IP as bot $TARGET_BOT"
fi

# ---------------------------------------------------------------------
# 2. Per-bot provisioning (same SSH pattern as deploy_relay.sh)
# ---------------------------------------------------------------------
RESULT_LINES=()
for BOT in "${BOT_LIST[@]}"; do
    if [ "$TARGET_BOT" = "all" ]; then
        V="FIELD_IP_${BOT}"
        BOT_ADDR="${FIELD_PREFIX}.${!V}"
    else
        BOT_ADDR="$TARGET_IP"
    fi

    echo ""
    echo "========================================================"
    echo "[$BOT] Provisioning bot $BOT at $BOT_ADDR (profile: $PROFILE)"
    echo "========================================================"

    SSH_SOCKET="/tmp/r2k_k1_ssh_${BOT_ADDR}"

    echo "[1/3] Opening master SSH connection (password prompt once)..."
    if ! ssh -M -S "$SSH_SOCKET" -f -N "${ROBOT_USER}@${BOT_ADDR}"; then
        echo "  ERROR: SSH to ${ROBOT_USER}@${BOT_ADDR} failed. Skipping bot $BOT."
        RESULT_LINES+=("bot $BOT ($BOT_ADDR): SSH FAILED")
        continue
    fi

    echo "[2/3] Pushing profile + set_field_wifi.sh..."
    scp -o "ControlPath=$SSH_SOCKET" "$PROFILE_FILE" "${ROBOT_USER}@${BOT_ADDR}:/tmp/r2k_field_profile.env" || {
        RESULT_LINES+=("bot $BOT ($BOT_ADDR): scp FAILED"); ssh -S "$SSH_SOCKET" -O exit "${ROBOT_USER}@${BOT_ADDR}" 2>/dev/null; continue; }
    scp -o "ControlPath=$SSH_SOCKET" "$SCRIPT_DIR/set_field_wifi.sh" "${ROBOT_USER}@${BOT_ADDR}:/tmp/r2k_set_field_wifi.sh" || {
        RESULT_LINES+=("bot $BOT ($BOT_ADDR): scp FAILED"); ssh -S "$SSH_SOCKET" -O exit "${ROBOT_USER}@${BOT_ADDR}" 2>/dev/null; continue; }

    echo "[3/3] Installing wifi profile on the K1 (sudo)..."
    REMOTE_FLAGS="--bot ${BOT} ${EXCLUSIVE} ${SKIP_UP}"
    if ssh -S "$SSH_SOCKET" "${ROBOT_USER}@${BOT_ADDR}" \
        "printf '%s\n' '${BOT_SUDO_PASS}' | sudo -S bash /tmp/r2k_set_field_wifi.sh /tmp/r2k_field_profile.env ${REMOTE_FLAGS}"; then
        IP_VAR="FIELD_IP_${BOT}"
        REMOTE_IP="${FIELD_PREFIX}.${!IP_VAR}"
        RESULT_LINES+=("bot $BOT: OK  -> wifi '$FIELD_SSID' static ${REMOTE_IP}/${FIELD_SUBNET}")
    else
        RESULT_LINES+=("bot $BOT ($BOT_ADDR): REMOTE SETUP FAILED")
    fi

    echo "Cleaning up SSH connection..."
    ssh -S "$SSH_SOCKET" -O exit "${ROBOT_USER}@${BOT_ADDR}" 2>/dev/null || true
done

# ---------------------------------------------------------------------
# 3. Summary + record active profile (only if at least one bot succeeded)
# ---------------------------------------------------------------------
echo ""
echo "======================== SUMMARY ========================"
FAILED=0
for L in "${RESULT_LINES[@]}"; do
    echo "  $L"
    case "$L" in *FAILED|*"SSH FAILED") FAILED=$((FAILED+1)) ;; esac
done
echo "========================================================="

# Only pin the profile once at least one bot took it, and fail loudly otherwise
if [ "$FAILED" -eq 0 ]; then
    echo "$PROFILE" > "$CURRENT_PROFILE_FILE" 2>/dev/null \
        && echo "Active profile set: $PROFILE  (stored in .current_profile)"
    exit 0
else
    echo "$FAILED bot(s) failed — .current_profile NOT updated."
    exit 1
fi