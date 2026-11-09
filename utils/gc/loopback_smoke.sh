#!/bin/bash
# =====================================================================
# loopback_smoke.sh — Tier-1 self-test for the ROS2K GC receiver module
# ---------------------------------------------------------------------
# Starts game_controller_node.py on loopback, injects crafted
# RoboCupGameControlData (v20) packets to UDP 3838, and captures the
# RoboCupGameControlReturnData (RGrt) presence packets the node sends
# back to UDP 3939. Verifies the four Tier-1 acceptance checks:
#
#   1. PRESENCE    — node emits RGrt @ 2 Hz after receiving a packet
#   2. TRANSITION  — state-change log line emitted once per change
#   3. GARBAGE     — malformed packet is dropped, node stays alive
#   4. STALE       — announcer goes silent after GC_STALE_TIMEOUT_S (5s)
#
# No ROS 2 / Gazebo / hardware required. The node runs headless if
# rclpy or gc_msgs are unavailable; if they are sourced, it also
# publishes /gc/game_state (not asserted by this script — use
# `ros2 topic echo /gc/game_state` separately to see it).
#
# Run from anywhere:
#   utils/gc/loopback_smoke.sh
# =====================================================================
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
NODE="$REPO_ROOT/core/src/game_controller_node.py"
NODE_LOG="$(mktemp -t gc_smoke_node.XXXXXX.log)"
CAPTURE_LOG="$(mktemp -t gc_smoke_cap.XXXXXX.log)"
TEAM=50
PLAYER=1
STALE_S=5
PASS_COUNT=0
FAIL_COUNT=0
NODE_PID=""

cleanup() {
    if [ -n "$NODE_PID" ] && kill -0 "$NODE_PID" 2>/dev/null; then
        kill "$NODE_PID" 2>/dev/null || true
        wait "$NODE_PID" 2>/dev/null || true
    fi
    rm -f "$NODE_LOG" "$CAPTURE_LOG" 2>/dev/null || true
}
trap cleanup EXIT

# Try to enable ROS 2 publishing (optional; headless is fine too).
# ROS setup scripts reference unbound variables, so relax `set -u` here.
if [ -f /opt/ros/humble/setup.bash ]; then
    # shellcheck disable=SC1091
    set +u; source /opt/ros/humble/setup.bash 2>/dev/null || true; set -u
fi
if [ -f "$REPO_ROOT/core/src/ros2_ws/install/setup.bash" ]; then
    # shellcheck disable=SC1091
    set +u; source "$REPO_ROOT/core/src/ros2_ws/install/setup.bash" 2>/dev/null || true; set -u
fi
export PYTHONPATH="$REPO_ROOT/core/src${PYTHONPATH:+:$PYTHONPATH}"

check() {  # check <name> <pass|fail> <detail>
    local name="$1" verdict="$2" detail="${3:-}"
    if [ "$verdict" = "pass" ]; then
        printf "  [\033[32mPASS\033[0m] %s — %s\n" "$name" "$detail"
        PASS_COUNT=$((PASS_COUNT + 1))
    else
        printf "  [\033[31mFAIL\033[0m] %s — %s\n" "$name" "$detail"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
}

# --- helpers: send a control packet, capture returns -------------------
# send_state <state> <kicking_team> <secs_remaining>
send_state() {
    python3 - "$1" "$2" "$3" <<'PY'
import socket, struct, sys
state, kick, secs = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
hdr   = struct.pack("<4sBBBBBBBBBBhh", b"RGme", 20, 0, 3, 2, 0, 0, state, 0, 1, kick, secs, 0)
team0 = struct.pack("<BBBBBBHH", 50, 0, 0, 1, 2, 0, 0, 1200) + b"\x00" * 60
team1 = struct.pack("<BBBBBBHH", 7,  0, 0, 1, 0, 0, 0, 1200) + b"\x00" * 60
socket.socket(socket.AF_INET, socket.SOCK_DGRAM).sendto(hdr + team0 + team1, ("127.0.0.1", 3838))
PY
}

send_garbage() {
    python3 - <<'PY'
import socket
socket.socket(socket.AF_INET, socket.SOCK_DGRAM).sendto(b"RGxx" + b"\x00" * 154, ("127.0.0.1", 3838))
PY
}

# capture_returns <seconds> -> writes count + first packet bytes to CAPTURE_LOG
capture_returns() {
    local seconds="$1"
    python3 - "$seconds" "$CAPTURE_LOG" <<'PY'
import socket, sys
seconds, log = sys.argv[1], sys.argv[2]
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(("127.0.0.1", 3939))
s.settimeout(float(seconds))
count = 0
first = b""
while True:
    try:
        d, _a = s.recvfrom(64)
    except socket.timeout:
        break
    count += 1
    if not first:
        first = d
with open(log, "w") as f:
    f.write(f"{count}\n")
    f.write(f"{first[:4]!r} ver={first[4] if len(first)>4 else '-'} player={first[5] if len(first)>5 else '-'} team={first[6] if len(first)>6 else '-'}\n")
PY
}

# --- start the node -----------------------------------------------------
echo "[loopback_smoke] starting game_controller_node (headless ok) ..."
python3 "$NODE" --team "$TEAM" --player "$PLAYER" >"$NODE_LOG" 2>&1 &
NODE_PID=$!
# wait for the listen line (up to 4s)
for _ in $(seq 1 40); do
    if grep -q "listen=0.0.0.0:3838" "$NODE_LOG" 2>/dev/null; then break; fi
    if ! kill -0 "$NODE_PID" 2>/dev/null; then
        echo "[loopback_smoke] node died during startup:"; cat "$NODE_LOG"; exit 1
    fi
    sleep 0.1
done
if ! grep -q "listen=0.0.0.0:3838" "$NODE_LOG" 2>/dev/null; then
    echo "[loopback_smoke] node did not signal readiness:"; cat "$NODE_LOG"; exit 1
fi
sleep 0.3  # let the recv loop settle

echo "[loopback_smoke] running checks ..."

# --- Check 1: PRESENCE --------------------------------------------------
# Start a 3s capture, then send one PLAYING packet. Expect RGrt packets.
capture_returns 3 &
CAP_PID=$!
sleep 0.2
send_state 3 50 600
wait "$CAP_PID" 2>/dev/null || true
if [ -f "$CAPTURE_LOG" ]; then
    RGRRT_COUNT=$(sed -n '1p' "$CAPTURE_LOG")
    RGRRT_INFO=$(sed -n '2p' "$CAPTURE_LOG")
else
    RGRRT_COUNT=0; RGRRT_INFO="(no capture file)"
fi
if [ "${RGRRT_COUNT:-0}" -ge 2 ] && echo "$RGRRT_INFO" | grep -q "b'RGrt'"; then
    check "PRESENCE" pass "got ${RGRRT_COUNT} RGrt packets in 3s (${RGRRT_INFO})"
else
    check "PRESENCE" fail "got ${RGRRT_COUNT} packets (${RGRRT_INFO})"
fi

# --- Check 2: TRANSITION dedupe ----------------------------------------
# Node is currently in PLAYING (from Check 1). Send READY twice -> the
# second must NOT log a new transition; then SET -> one SET line.
MARKER=$(wc -l < "$NODE_LOG")
send_state 1 50 590
sleep 0.3
send_state 1 50 580
sleep 0.3
send_state 2 50 570
sleep 0.3
TAIL=$(tail -n +$((MARKER + 1)) "$NODE_LOG")
READY_HITS=$(echo "$TAIL" | grep -c "GC state -> READY")
SET_HITS=$(echo "$TAIL" | grep -c "GC state -> SET")
if [ "$READY_HITS" -eq 1 ] && [ "$SET_HITS" -eq 1 ]; then
    check "TRANSITION" pass "READY logged ${READY_HITS}x (2nd send deduped), SET ${SET_HITS}x"
else
    check "TRANSITION" fail "READY=${READY_HITS} SET=${SET_HITS} (expected 1 and 1)"
fi

# --- Check 3: GARBAGE resilience ---------------------------------------
MARKER=$(wc -l < "$NODE_LOG")
send_garbage
sleep 0.4
if kill -0 "$NODE_PID" 2>/dev/null && tail -n +$((MARKER + 1)) "$NODE_LOG" | grep -q "dropped control packet"; then
    # confirm a subsequent good packet still works (node is in SET, go to PLAYING)
    MARKER2=$(wc -l < "$NODE_LOG")
    send_state 3 50 570
    sleep 0.4
    if tail -n +$((MARKER2 + 1)) "$NODE_LOG" | grep -q "GC state -> PLAYING"; then
        check "GARBAGE" pass "malformed dropped, node alive, next good packet decoded"
    else
        check "GARBAGE" fail "dropped ok but node did not decode a following good packet"
    fi
else
    check "GARBAGE" fail "no 'dropped control packet' log or node died"
fi

# --- Check 4: STALE silence --------------------------------------------
# Stop sending; after STALE_S the announcer must go quiet.
sleep $((STALE_S + 1))
capture_returns 2 &
CAP_PID=$!
wait "$CAP_PID" 2>/dev/null || true
if [ -f "$CAPTURE_LOG" ]; then
    STALE_COUNT=$(sed -n '1p' "$CAPTURE_LOG")
else
    STALE_COUNT="?"
fi
if [ "${STALE_COUNT:-0}" -eq 0 ]; then
    check "STALE" pass "0 RGrt packets after ${STALE_S}s GC silence"
else
    check "STALE" fail "announcer sent ${STALE_COUNT} packets despite GC silence"
fi

# --- summary ------------------------------------------------------------
echo
echo "[loopback_smoke] ${PASS_COUNT} passed, ${FAIL_COUNT} failed"
[ "$FAIL_COUNT" -eq 0 ]
