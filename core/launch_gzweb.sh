#!/bin/bash
# launch_gzweb.sh -- Minimal web-based experimental platform launcher.
# Runs a REAL AI match (sim-only, only_sim_bots relay) inside the r2k_gzweb
# container, plus GZWeb (gzbridge :8080 -> 3D scene in browser) and the
# file-bus WebSocket backend (ws_backend :8765 -> Worldstate.json to browser).
#
# No hardware sync, no micro-ROS agent, no hotspot, no --relay flag.
# Relay is fixed to only_sim_bots (sim cmd_vel via ollama_sandbox_bridge).
# GUI shell (dockview) is a separate Gate-2 concern; this launcher only
# brings up the container + backend wiring.
#
# Usage:
#   ./launch_gzweb.sh --scenario 2vs2_default --headless --duration 120
#   ./launch_gzweb.sh --help
#
# All work on this branch (feature/gzweb-experimental); production
# launch_r2k.sh is untouched.

set -euo pipefail

# --- SYSTEM OVERRIDES (same axioms as launch_r2k.sh) ---
export ROS_DOMAIN_ID=0
export ROS_LOCALHOST_ONLY=0
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export PYTHONWARNINGS="ignore"

SCENARIO="2vs2_default"
STRATEGY="strat_aggro"
MODEL="qwen2.5:3b"
EXPLAIN_FLAG="--no-explain"
HEADLESS=false
NO_VIZ=false
DURATION=0
DEMO=false
TRAP_TRIGGERED=false
UBUNTU_VERSION=$(lsb_release -rs)

if ! command -v jq >/dev/null 2>&1; then
    echo "❌ 'jq' is required. Run: sudo apt install jq"
    exit 1
fi

usage() {
    echo "=========================================================="
    echo "🌐 ROS2K GZWeb Experimental Launcher"
    echo "=========================================================="
    echo "  Runs a real AI match (sim-only) + GZWeb browser client."
    echo "  GZWeb:  http://localhost:8080  (3D scene)"
    echo "  Backend: ws://localhost:8765  (Worldstate.json push)"
    echo "=========================================================="
    echo "  --scenario <name>     (default: 2vs2_default)"
    echo "  --strategy <name>     (default: strat_aggro)"
    echo "  --model <name>        (default: qwen2.5:3b)"
    echo "  --explain             (Enable AI reasoning output)"
    echo "  --no-explain          (Disable AI reasoning)"
    echo "  --headless            (No Gazebo GUI + no visualizer)"
    echo "  --no-visualizer       (Gazebo GUI but no matplotlib visualizer)"
    echo "  --duration <seconds>  (Auto-terminate after N seconds)"
    echo "  --demo                (Demo/calibration mode)"
    echo "=========================================================="
    exit 0
}

while [[ "$#" -gt 0 ]]; do
    case $1 in
        -h|--help) usage ;;
        --scenario) SCENARIO="$2"; shift ;;
        --strategy) STRATEGY="$2"; shift ;;
        --model) MODEL="$2"; shift ;;
        --explain) EXPLAIN_FLAG="--explain" ;;
        --no-explain) EXPLAIN_FLAG="--no-explain" ;;
        --headless) HEADLESS=true ;;
        --no-visualizer) NO_VIZ=true ;;
        --duration) DURATION="$2"; shift ;;
        --demo) DEMO=true ;;
        *) echo "⚠️ Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

export R2K_EXPLAIN=$([[ "$EXPLAIN_FLAG" == "--explain" ]] && echo 1 || echo 0)
export R2K_TEAMCAPTAIN="${R2K_TEAMCAPTAIN:-0}"
export R2K_KICK_BEHIND_GATE="${R2K_KICK_BEHIND_GATE:-1}"
export R2K_PASS_RESOLVE="${R2K_PASS_RESOLVE:-0}"
export R2K_WING_STAGE="${R2K_WING_STAGE:-0}"

# Relay is FIXED to only_sim_bots (sim-only, no hardware).
RELAY="only_sim_bots"

# Container name is distinct from production core_gazebo.
CONTAINER_NAME="r2k_gzweb"
COMPOSE_FILE="docker-compose.gzweb.yml"

echo "=========================================================="
echo "🌐 GZWeb Experimental: $SCENARIO | sim-only | $MODEL"
echo "=========================================================="

cd src || { echo "❌ Ordner 'src' nicht gefunden!"; exit 1; }

RELAY_FILE="relay/${RELAY}.json"
if [ ! -f "$RELAY_FILE" ]; then
    echo "❌ Relay-Datei nicht gefunden: $RELAY_FILE"
    exit 1
fi

echo "🤖 Relay: $RELAY (sim-only, no hardware sync)"
jq -r '.mapping | to_entries[] | "  \(.key): \(.value.hardware_type) → \(.value.topic)"' "$RELAY_FILE"

export ROS2K_WS="$PWD"
mkdir -p shared_state logs
rm -f shared_state/current_strategy.json shared_state/Worldstate.json shared_state/waypoints.json shared_state/task_input.json

# --- Run ID for trace logs ---
export R2K_RUN_ID="${SCENARIO}_${STRATEGY}_$(date +%Y%m%d_%H%M%S)"
echo "📋 Run ID: $R2K_RUN_ID  (logs: src/logs/*_${R2K_RUN_ID}.jsonl)"

DEMO_FLAG=""
if [ "$DEMO" = true ]; then DEMO_FLAG="--demo"; fi
python3 setup_r2k.py --scenario "$SCENARIO" --strategy "$STRATEGY" --model "$MODEL" --relay "$RELAY" $EXPLAIN_FLAG $DEMO_FLAG || { echo "❌ Setup failed!"; exit 1; }

# ---- CLEANUP TRAP (no hardware -> no kinematic freeze) ----
cleanup() {
    if [ "$TRAP_TRIGGERED" = true ]; then return; fi
    TRAP_TRIGGERED=true
    echo -e "\n🛑 [TEARDOWN] Shutting down GZWeb experimental..."
    kill -9 $MONITOR_PID 2>/dev/null
    docker exec $CONTAINER_NAME pkill -f "server.js 8080" > /dev/null 2>&1 || true
    # Unload ALL Ollama models from VRAM (free GPU memory)
    for m in $(curl -s http://127.0.0.1:11434/api/ps 2>/dev/null | python3 -c "import sys,json;[print(m['name']) for m in json.load(sys.stdin).get('models',[])]" 2>/dev/null); do
        curl -s -m 5 "${OLLAMA_LOCAL}/api/generate" -d "{\"model\":\"$m\",\"keep_alive\":0}" > /dev/null 2>&1 || true
    done
    docker compose -f "$COMPOSE_FILE" down > /dev/null 2>&1 || true
    echo "✅ Teardown complete."
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# ---- OLLAMA CHECK (same as launch_r2k.sh) ----
HTTP_PROT="http"
OLLAMA_LOCAL="${HTTP_PROT}://127.0.0.1:11434"
OLLAMA_DOCKER="${HTTP_PROT}://172.17.0.1:11434"

echo "🧠 Checking Ollama AI Server..."
export OLLAMA_HOST=0.0.0.0
if curl -s "${OLLAMA_LOCAL}/api/tags" > /dev/null 2>&1; then
    echo "✅ Ollama ist bereits online und erreichbar."
else
    echo "🚀 Booting Ollama AI Server..."
    nohup ollama serve > ollama.log 2>&1 &
    disown $!
    sleep 5
fi

if [[ "$SCENARIO" != 0vs* ]]; then
    echo "🔍 Prüfe, ob das Modell '$MODEL' lokal verfügbar ist..."
    if ! curl -s "${OLLAMA_LOCAL}/api/tags" | grep -q "\"name\":\"$MODEL\""; then
        echo "❌ FEHLER: Modell '$MODEL' nicht gefunden!  → ollama pull $MODEL"
        exit 1
    fi
    echo "✅ Modell '$MODEL' ist bereit."
fi

if [[ "$SCENARIO" != 0vs* ]]; then
    echo "🔥 Warming up model '$MODEL' (cold-boot load, ~30s on first run)..."
    curl -s --max-time 120 "${OLLAMA_LOCAL}/api/generate" \
        -d "{\"model\":\"$MODEL\",\"prompt\":\"hi\",\"stream\":false}" > /dev/null 2>&1
    echo "✅ Model '$MODEL' is warm."
fi

if [[ "$UBUNTU_VERSION" == 24.* ]]; then
    if ! ss -tlnp 2>/dev/null | grep -q "0.0.0.0:11434\|\\*:11434"; then
        echo "❌ FEHLER: Ollama lauscht nicht auf 0.0.0.0:11434!"
        echo "   Fix: OLLAMA_HOST=0.0.0.0 ollama serve  (or systemd override)"
        exit 1
    fi
fi

export R2K_OLLAMA_URL="${OLLAMA_LOCAL}/api/generate"
export R2K_OLLAMA_MODEL=$MODEL

# ==========================================================
# 🐳 DOCKER LAUNCH (r2k_gzweb container)
# ==========================================================
xhost +local:root > /dev/null 2>&1
export DISPLAY=$DISPLAY

echo "🐳 Starting r2k_gzweb container (first build ~15 min, then seconds)..."
docker compose -f "$COMPOSE_FILE" down > /dev/null 2>&1 || true
docker compose -f "$COMPOSE_FILE" up -d > /dev/null 2>&1
sleep 2

DOCKER_BASE="docker exec -d $CONTAINER_NAME bash -c"
SOURCE_CMD="cd /workspace && source /opt/ros/humble/setup.bash && source ros2_ws/install/setup.bash"

echo "🌍 Starting Gazebo in r2k_gzweb..."
if [ "$HEADLESS" = true ]; then
    $DOCKER_BASE "$SOURCE_CMD && ros2 launch r2k_scenario_spawner soccer_match.launch.py headless:=true > /dev/null 2>&1"
else
    $DOCKER_BASE "$SOURCE_CMD && ros2 launch r2k_scenario_spawner soccer_match.launch.py > /dev/null 2>&1"
fi

# Fast-Polling Watchdog (0.2s) -- gzserver only, no hardware
(
    sleep 10
    while true; do
        if ! docker exec $CONTAINER_NAME pgrep -f "gazebo|gzserver|ruby" > /dev/null 2>&1; then
            docker exec $CONTAINER_NAME pkill -f r2k_visualizer.py > /dev/null 2>&1
            kill -TERM $$ 2>/dev/null
            break
        fi
        sleep 0.2
    done
) &
MONITOR_PID=$!

echo "🤖 Waiting for Gazebo API & Spawning Bots..."
sleep 2
docker exec $CONTAINER_NAME bash -c "$SOURCE_CMD && python3 ai_tactics/json_spawner.py"

# ---- GZWeb browser client (gzbridge :8080) ----
echo "🌐 Starting GZWeb server on http://localhost:8080 ..."
docker exec -d $CONTAINER_NAME bash -c 'cd /opt/gzweb/gzbridge && ./server.js 8080' > /dev/null 2>&1
for _ in 1 2 3 4 5; do
    sleep 1
    if curl -s -o /dev/null -w '' http://localhost:8080/ 2>/dev/null; then
        echo "✅ GZWeb is live → http://localhost:8080"
        break
    fi
done
if ! curl -s -o /dev/null -w '' http://localhost:8080/ 2>/dev/null; then
    echo "⚠️ GZWeb server did not respond on :8080 (check: docker exec $CONTAINER_NAME bash -c 'cd /opt/gzweb/gzbridge && ./server.js 8080')"
fi

# ---- Host-side context dump for GUI homepage (repo root NOT mounted in
# ---- container; supervisor falls back to these files in shared_state/) ----
git log --oneline -5 > shared_state/git_commits.txt 2>/dev/null || true
CHANGELOG="$(git rev-parse --show-toplevel 2>/dev/null)/core/docs/SESSION_CHANGELOG.md"
tail -n 30 "$CHANGELOG" > shared_state/session_digest.txt 2>/dev/null || true
# Assistant panel context (persona + META-ROUTER) for the /assistant/ask endpoint
KB_DIR="$(git rev-parse --show-toplevel 2>/dev/null)/core/src/ros2k_knowledge"
mkdir -p shared_state/assistant_ctx
cp "$KB_DIR/agent_prompt_de.txt" "$KB_DIR/META_KNOWLEDGE_ROUTER.md" shared_state/assistant_ctx/ 2>/dev/null || true

# ---- File-bus WebSocket backend (ws_backend :8765) ----
echo "🔌 Starting file-bus WebSocket backend on ws://localhost:8765 ..."
docker exec -d $CONTAINER_NAME bash -c 'cd /workspace && python3 tools/r2k_supervisor.py' > /dev/null 2>&1
echo "   Pushes Worldstate.json / current_strategy.json / waypoints.json to browser."

# ---- Realtime Nodes & AI (real match, sim-only) ----
echo "⚡ Igniting Realtime Nodes & AI..."
$DOCKER_BASE "$SOURCE_CMD && ros2 run r2k_world_model tracker > /dev/null 2>&1"
if [ "$DEMO" = false ]; then
    $DOCKER_BASE "$SOURCE_CMD && python3 referee_node.py > /dev/null 2>&1"
    $DOCKER_BASE "$SOURCE_CMD && python3 score_node.py > /dev/null 2>&1"
    $DOCKER_BASE "$SOURCE_CMD && python3 reward_node.py > /dev/null 2>&1"
    $DOCKER_BASE "$SOURCE_CMD && python3 rule_evaluator_red.py > /dev/null 2>&1"
fi
docker exec -d -e R2K_RUN_ID="$R2K_RUN_ID" $CONTAINER_NAME bash -c "$SOURCE_CMD && python3 state_aggregator.py > /dev/null 2>&1"
docker exec -d -e R2K_TEAMCAPTAIN="$R2K_TEAMCAPTAIN" -e R2K_KICK_BEHIND_GATE="$R2K_KICK_BEHIND_GATE" -e R2K_PASS_RESOLVE="$R2K_PASS_RESOLVE" -e R2K_WING_STAGE="$R2K_WING_STAGE" -e R2K_RUN_ID="$R2K_RUN_ID" $CONTAINER_NAME bash -c "$SOURCE_CMD && python3 ai_tactics/ollama_sandbox_bridge.py > /dev/null 2>&1"

echo "🧠 Starting Team Blue AI (Live Output)..."
docker exec -d -e PYTHONUNBUFFERED=1 -e PYTHONWARNINGS="ignore" -e R2K_OLLAMA_MODEL=$MODEL -e R2K_OLLAMA_URL="${OLLAMA_DOCKER}/api/generate" -e R2K_RUN_ID="$R2K_RUN_ID" -e R2K_EXPLAIN="$R2K_EXPLAIN" $CONTAINER_NAME bash -c "$SOURCE_CMD && python3 -u ai_tactics/r2k_evaluator.py"

# Duration-based auto-terminate
if [ "$DURATION" -gt 0 ]; then
    echo "⏱️  Auto-terminate scheduled after ${DURATION}s"
    (sleep "$DURATION"; echo "⏱️  Duration reached, triggering shutdown"; kill -TERM $$) &
fi

echo "=========================================================="
echo "✅ GZWeb Experimental Online."
echo "   🌐 3D scene:    http://localhost:8080"
echo "   🔌 Worldstate:  ws://localhost:8765"
echo "   Press CTRL+C to shutdown."
echo "=========================================================="

# Headless or no-visualizer: idle loop (watchdog handles teardown)
if [ "$HEADLESS" = true ] || [ "$NO_VIZ" = true ]; then
    echo "🏃 No matplotlib visualizer"
    while true; do sleep 1; done
fi

# Visualizer (optional, GUI mode)
docker exec -it -e PYTHONWARNINGS="ignore" -e DISPLAY=$DISPLAY -e QT_X11_NO_MITSHM=1 $CONTAINER_NAME bash -c "$SOURCE_CMD && python3 r2k_visualizer.py --live"

if [ $? -ne 0 ]; then
    echo "⚠️ Visualizer crashed. System stays alive for debugging. CTRL+C to teardown."
    while true; do sleep 1; done
fi