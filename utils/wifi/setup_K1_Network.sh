#!/bin/bash
# =====================================================================
# setup_K1_Network.sh — RUNS FROM THE LAPTOP (provisioning, pre-match)
# ---------------------------------------------------------------------
# Pushes a field profile + wifi scripts to each K1 via SSH (persistent
# folder ~/Workspace/r2k_wifi, mirroring deploy_relay.sh's ros2_relay
# convention) and installs the static-IP wifi profile there.
#
# THIS IS PROVISIONING ONLY. It must be run BEFORE a match (network
# setup), never during play — Rules §3.9 forbids any laptop access
# during a match.
#
# Activation: by DEFAULT the remote installer schedules the wifi switch
# asynchronously (--async-up) so this SSH session closes cleanly BEFORE
# the K1's link flaps, then the script waits (ping, up to
# REACH_TIMEOUT_S) for the bot to appear at its new static IP.
# --skip-up disables both.
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
#                           -> K1 joins ONLY this network. RECOMMENDED:
#                           without it a failed 'field' activation can
#                           leave a competitor profile holding the same
#                           IP and the reachability wait can report a
#                           false positive.
#   --skip-up               install only: no activation, no reachability wait
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

# Persistent remote folder on the K1 (mirrors deploy_relay.sh's
# /home/booster/Workspace/ros2_relay convention). Survives reboot, so
# wifi_check.sh stays available for validation at any time.
REMOTE_DIR="/home/booster/Workspace/r2k_wifi"

# Reachability wait after async activation: pause for the wifi flap to
# happen (remote ASYNC_GRACE_S + margin), then ping the new static IP
# until REACH_TIMEOUT_S have passed in total.
POST_FLAP_GRACE_S=5
REACH_TIMEOUT_S=60

# SSH robustness: fail fast on dead links instead of hanging for the
# TCP timeout (the K1's wifi link flaps during activation).
SSH_OPTS="-o ServerAliveInterval=2 -o ServerAliveCountMax=3 -o ConnectTimeout=10"

PROFILE=""
EXCLUSIVE=""
SKIP_UP=""
TARGET_IP=""
TARGET_BOT=""

usage() { sed -n '2,47p' "$0" | sed 's/^# \{0,1\}//'; exit 1; }

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

# Async activation is the default for remote provisioning (an SSH session
# riding the K1's wifi link would die mid-command otherwise). Warn when it
# runs without --exclusive: a competitor profile (autoconnect=yes) can
# hold the same IP if 'field' fails to activate, making the
# reachability wait report a false positive.
if [ -z "$SKIP_UP" ] && [ -z "$EXCLUSIVE" ]; then
    echo "WARN: async activation without --exclusive — if 'field' fails to"
    echo "      activate, a competitor profile (autoconnect=yes) may hold the"
    echo "      same IP and the reachability wait can report a false positive."
    echo "      Recommended: add --exclusive."
fi

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
    PROFILE_BASE="$(basename "$PROFILE_FILE")"

    echo "[1/5] Opening master SSH connection (password prompt once)..."
    if ! ssh $SSH_OPTS -M -S "$SSH_SOCKET" -f -N "${ROBOT_USER}@${BOT_ADDR}"; then
        echo "  ERROR: SSH to ${ROBOT_USER}@${BOT_ADDR} failed. Skipping bot $BOT."
        RESULT_LINES+=("bot $BOT ($BOT_ADDR): SSH FAILED")
        continue
    fi

    echo "[2/5] Preparing remote folder ${REMOTE_DIR}..."
    if ! ssh $SSH_OPTS -S "$SSH_SOCKET" "${ROBOT_USER}@${BOT_ADDR}" "mkdir -p ${REMOTE_DIR}"; then
        RESULT_LINES+=("bot $BOT ($BOT_ADDR): mkdir ${REMOTE_DIR} FAILED")
        ssh $SSH_OPTS -S "$SSH_SOCKET" -O exit "${ROBOT_USER}@${BOT_ADDR}" 2>/dev/null
        continue
    fi

    echo "[3/5] Pushing profile + wifi scripts to ${REMOTE_DIR}..."
    scp $SSH_OPTS -o "ControlPath=$SSH_SOCKET" "$PROFILE_FILE" "${ROBOT_USER}@${BOT_ADDR}:${REMOTE_DIR}/${PROFILE_BASE}" || {
        RESULT_LINES+=("bot $BOT ($BOT_ADDR): scp FAILED"); ssh $SSH_OPTS -S "$SSH_SOCKET" -O exit "${ROBOT_USER}@${BOT_ADDR}" 2>/dev/null; continue; }
    scp $SSH_OPTS -o "ControlPath=$SSH_SOCKET" "$SCRIPT_DIR/set_field_wifi.sh" "${ROBOT_USER}@${BOT_ADDR}:${REMOTE_DIR}/set_field_wifi.sh" || {
        RESULT_LINES+=("bot $BOT ($BOT_ADDR): scp FAILED"); ssh $SSH_OPTS -S "$SSH_SOCKET" -O exit "${ROBOT_USER}@${BOT_ADDR}" 2>/dev/null; continue; }
    scp $SSH_OPTS -o "ControlPath=$SSH_SOCKET" "$SCRIPT_DIR/wifi_check.sh" "${ROBOT_USER}@${BOT_ADDR}:${REMOTE_DIR}/wifi_check.sh" || {
        RESULT_LINES+=("bot $BOT ($BOT_ADDR): scp FAILED"); ssh $SSH_OPTS -S "$SSH_SOCKET" -O exit "${ROBOT_USER}@${BOT_ADDR}" 2>/dev/null; continue; }
    # The profile env carries FIELD_PASS: restrict to owner-only read.
    ssh $SSH_OPTS -S "$SSH_SOCKET" "${ROBOT_USER}@${BOT_ADDR}" "chmod 600 ${REMOTE_DIR}/${PROFILE_BASE}" || true

    if [ -n "$SKIP_UP" ]; then ACT_FLAG="--skip-up"; else ACT_FLAG="--async-up"; fi
    echo "[4/5] Installing wifi profile on the K1 (sudo, ${ACT_FLAG})..."
    REMOTE_FLAGS="--bot ${BOT} ${EXCLUSIVE} ${ACT_FLAG}"
    if ssh $SSH_OPTS -S "$SSH_SOCKET" "${ROBOT_USER}@${BOT_ADDR}" \
        "printf '%s\n' '${BOT_SUDO_PASS}' | sudo -S bash ${REMOTE_DIR}/set_field_wifi.sh ${REMOTE_DIR}/${PROFILE_BASE} ${REMOTE_FLAGS}"; then

        IP_VAR="FIELD_IP_${BOT}"
        NEW_IP="${FIELD_PREFIX}.${!IP_VAR}"

        if [ -n "$SKIP_UP" ]; then
            echo "   Profile installed at ${REMOTE_DIR} on the K1 (activation skipped)."
            RESULT_LINES+=("bot $BOT: OK  -> profile installed at ${REMOTE_DIR}; K1 activates 'field' via autoconnect (static ${NEW_IP}/${FIELD_SUBNET})")
        else
            echo "[5/5] Waiting for bot $BOT at ${NEW_IP} (up to ${REACH_TIMEOUT_S}s)..."
            # Grace: let the async activation (remote grace delay) flap the
            # link BEFORE the first ping, so a hit means the K1 is BACK on
            # the air on the new profile, not the pre-flap state.
            sleep ${POST_FLAP_GRACE_S}
            START=$(date +%s)
            DEADLINE=$(( START + REACH_TIMEOUT_S - POST_FLAP_GRACE_S ))
            REACHED=false
            while [ "$(date +%s)" -lt "$DEADLINE" ]; do
                if ping -c 1 -W 1 "$NEW_IP" >/dev/null 2>&1; then REACHED=true; break; fi
                sleep 1
            done
            ELAPSED=$(( $(date +%s) - START + POST_FLAP_GRACE_S ))
            if [ "$REACHED" = true ]; then
                echo "   bot $BOT reachable at ${NEW_IP} after ~${ELAPSED}s."
                RESULT_LINES+=("bot $BOT: OK  -> ${NEW_IP}/${FIELD_SUBNET} reachable after ~${ELAPSED}s (confirm 'field' is active: run wifi_check.sh on the K1)")
            else
                echo "   bot $BOT NOT reachable at ${NEW_IP} after ~${REACH_TIMEOUT_S}s — activation may have failed."
                echo "   - Is the laptop on the ${FIELD_PREFIX}.x subnet?"
                echo "   - Inspect on the K1: cat /tmp/r2k_activate.log"
                RESULT_LINES+=("bot $BOT: NOT REACHABLE at ${NEW_IP} after ~${REACH_TIMEOUT_S}s (check /tmp/r2k_activate.log on the K1)")
            fi
        fi
    else
        RESULT_LINES+=("bot $BOT ($BOT_ADDR): REMOTE SETUP FAILED")
    fi

    echo "Cleaning up SSH connection..."
    ssh $SSH_OPTS -S "$SSH_SOCKET" -O exit "${ROBOT_USER}@${BOT_ADDR}" 2>/dev/null || true
done

# ---------------------------------------------------------------------
# 3. Summary + record active profile (only if every bot succeeded)
# ---------------------------------------------------------------------
echo ""
echo "======================== SUMMARY ========================"
FAILED=0
for L in "${RESULT_LINES[@]}"; do
    echo "  $L"
    case "$L" in
        *FAILED|*"NOT REACHABLE"*) FAILED=$((FAILED+1)) ;;
    esac
done
echo "========================================================="
echo "Validate on each K1 (from the laptop):"
echo "  ssh ${ROBOT_USER}@<bot_ip>"
echo "  sudo bash ${REMOTE_DIR}/wifi_check.sh ${REMOTE_DIR}/$(basename "$PROFILE_FILE") --bot <N> --ping-peers"
echo "========================================================="

# Only pin the profile once every bot took it, and fail loudly otherwise
if [ "$FAILED" -eq 0 ]; then
    echo "$PROFILE" > "$CURRENT_PROFILE_FILE" 2>/dev/null \
        && echo "Active profile set: $PROFILE  (stored in .current_profile)"
    exit 0
else
    echo "$FAILED bot(s) failed — .current_profile NOT updated."
    exit 1
fi