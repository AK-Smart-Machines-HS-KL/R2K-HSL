#!/bin/bash
# =====================================================================
# deploy_to_k1.sh — deploy the ROS2K GameController receiver to a K1
# ---------------------------------------------------------------------
# Pushes the gc_msgs package + the standalone game_controller_node.py to
# a K1 over SSH, builds gc_msgs with colcon on the robot, and starts the
# node in the background so the robot announces its presence to the HSL
# GameController (receives UDP 3838, returns UDP 3939).
#
# RUN FROM THE LAPTOP, BEFORE A MATCH (never during — Rules §3.9).
#
# Usage:
#   deploy_to_k1.sh [OPTIONS] <Robot_IP> <player_number>
#
# Arguments:
#   <Robot_IP>        current address of the K1 (e.g. 192.168.50.4)
#   <player_number>   1-based player number passed as --player
#
# Options:
#   -h, --help              show help
#   --team <N>              team number (default 50 = R-ZWEI KICKERS)
#   --user <u>              SSH user (default booster)
#   --remote-dir <path>     remote workspace dir (default ~/Workspace/r2k_gc)
#   --no-start              deploy + build only, do not launch the node
#   --stop                  stop a running node on the robot and exit
#
# Examples:
#   deploy_to_k1.sh 192.168.50.4 4
#   deploy_to_k1.sh --team 50 192.168.50.1 1
#   deploy_to_k1.sh --stop 192.168.50.4
# =====================================================================
set -euo pipefail

ROBOT_USER="booster"
REMOTE_DIR="/home/booster/Workspace/r2k_gc"
TEAM=50
PLAYER=""
ROBOT_IP=""
NO_START=false
STOP_ONLY=false

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
GCMSGS_SRC="$REPO_ROOT/core/src/ros2_ws/src/gc_msgs"
NODE_SRC="$REPO_ROOT/core/src/game_controller_node.py"

show_help() { sed -n '2,28p' "${BASH_SOURCE[0]}"; }

while [[ "$#" -gt 0 ]]; do
    case "$1" in
        -h|--help) show_help; exit 0 ;;
        --team) TEAM="$2"; shift 2 ;;
        --user) ROBOT_USER="$2"; shift 2 ;;
        --remote-dir) REMOTE_DIR="$2"; shift 2 ;;
        --no-start) NO_START=true; shift ;;
        --stop) STOP_ONLY=true; shift ;;
        *)
            if [ -z "$ROBOT_IP" ]; then ROBOT_IP="$1"
            elif [ -z "$PLAYER" ]; then PLAYER="$1"
            else echo "Error: unknown argument: $1" >&2; show_help >&2; exit 1; fi
            shift ;;
    esac
done

if [ -z "$ROBOT_IP" ]; then echo "Error: <Robot_IP> required" >&2; show_help >&2; exit 1; fi

REMOTE_USERHOST="${ROBOT_USER}@${ROBOT_IP}"
SSH=(ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=8 "$REMOTE_USERHOST")
SCP=(scp -o StrictHostKeyChecking=accept-new -o ConnectTimeout=8)

echo "[deploy_to_k1] target: $REMOTE_USERHOST  team=$TEAM  remote_dir=$REMOTE_DIR"

# --- --stop: kill a running node and exit ---------------------------------
if [ "$STOP_ONLY" = true ]; then
    echo "[deploy_to_k1] stopping game_controller_node on $ROBOT_IP ..."
    "${SSH[@]}" "pkill -f 'game_controller_node.py' || true"
    exit 0
fi

if [ -z "$PLAYER" ]; then echo "Error: <player_number> required" >&2; exit 1; fi
if ! [[ "$PLAYER" =~ ^[1-9][0-9]?$ ]] || [ "$PLAYER" -gt 20 ]; then
    echo "Error: <player_number> must be 1..20" >&2; exit 1
fi
if [ ! -d "$GCMSGS_SRC" ]; then echo "Error: missing $GCMSGS_SRC" >&2; exit 1; fi
if [ ! -f "$NODE_SRC" ];  then echo "Error: missing $NODE_SRC" >&2; exit 1; fi

# --- pre-flight: verify the K1 ROS 2 environment --------------------------
echo "[deploy_to_k1] pre-flight: checking ROS 2 environment on the K1 ..."
PREFLIGHT=$("${SSH[@]}" 'bash -lc "
    set +e
    if ! command -v ros2 >/dev/null 2>&1; then echo MISSING_ROS2; exit 0; fi
    distro=\"\"
    for d in /opt/ros/humble /opt/ros/jazzy /opt/ros/iron /opt/ros/foxy; do
        [ -f \"\$d/setup.bash\" ] && distro=\"\$d\" && break
    done
    [ -z \"\$distro\" ] && echo NO_DISTRO && exit 0
    source \"\$distro/setup.bash\"
    python3 - <<PY
import importlib
try:
    import rclpy; print(\"RCLPY_OK\")
except Exception as e:
    print(\"RCLPY_MISSING\", e)
PY
    if ! command -v colcon >/dev/null 2>&1; then echo COLCON_MISSING; fi
    echo \"DISTRO=\$distro\"
"' 2>/dev/null || true)

if echo "$PREFLIGHT" | grep -q "MISSING_ROS2\|NO_DISTRO\|RCLPY_MISSING\|COLCON_MISSING"; then
    echo "[deploy_to_k1] pre-flight FAILED on $ROBOT_IP:" >&2
    echo "$PREFLIGHT" | sed 's/^/    /' >&2
    echo "Resolve the missing ROS 2 / rclpy / colcon on the K1 first, then re-run." >&2
    exit 3
fi
DISTRO=$(echo "$PREFLIGHT" | grep -oE 'DISTRO=[^ ]+' | cut -d= -f2)
[ -z "$DISTRO" ] && DISTRO="/opt/ros/humble"
echo "[deploy_to_k1] pre-flight OK: $DISTRO"

# --- copy sources ---------------------------------------------------------
echo "[deploy_to_k1] copying gc_msgs + node to $REMOTE_USERHOST:$REMOTE_DIR ..."
"${SSH[@]}" "mkdir -p $REMOTE_DIR/src $REMOTE_DIR"
"${SCP[@]}" -r "$GCMSGS_SRC" "$REMOTE_USERHOST:$REMOTE_DIR/src/"
"${SCP[@]}" "$NODE_SRC" "$REMOTE_USERHOST:$REMOTE_DIR/"

# --- remote colcon build --------------------------------------------------
echo "[deploy_to_k1] building gc_msgs on the K1 ..."
"${SSH[@]}" "bash -lc \"
    set -e
    source $DISTRO/setup.bash
    cd $REMOTE_DIR
    if [ -d build/gc_msgs ] || [ -d install/gc_msgs ]; then
        rm -rf build install log
    fi
    colcon build --packages-select gc_msgs
\""

if [ "$NO_START" = true ]; then
    echo "[deploy_to_k1] --no-start: build complete, not launching."
    exit 0
fi

# --- launch the node ------------------------------------------------------
echo "[deploy_to_k1] launching game_controller_node (team=$TEAM player=$PLAYER) ..."
"${SSH[@]}" "bash -lc \"
    set -e
    source $DISTRO/setup.bash
    source $REMOTE_DIR/install/setup.bash
    pkill -f 'game_controller_node.py' || true
    mkdir -p $REMOTE_DIR/logs
    nohup python3 $REMOTE_DIR/game_controller_node.py \\
        --team $TEAM --player $PLAYER \\
        > $REMOTE_DIR/logs/gc_node.log 2>&1 &
    echo \\\$! > $REMOTE_DIR/logs/gc_node.pid
    sleep 1
    if kill -0 \\\$(cat $REMOTE_DIR/logs/gc_node.pid) 2>/dev/null; then
        echo STARTED pid=\\\$(cat $REMOTE_DIR/logs/gc_node.pid)
    else
        echo FAILED; cat $REMOTE_DIR/logs/gc_node.log; exit 4
    fi
\""

echo "[deploy_to_k1] done. Tail logs with:"
echo "    ssh $REMOTE_USERHOST 'tail -f $REMOTE_DIR/logs/gc_node.log'"
