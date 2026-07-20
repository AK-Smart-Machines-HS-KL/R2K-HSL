#!/bin/bash

# --- SYSTEM OVERRIDES & SILENCERS ---
export ROS_DOMAIN_ID=0
export ROS_LOCALHOST_ONLY=0
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export PYTHONWARNINGS="ignore"
# ------------------------------------

SCENARIO="2vs2_default"
STRATEGY="strat_aggro"
MODEL="qwen2.5-coder:3b"
EXPLAIN_FLAG="--no-explain"
RELAY="only_sim_bots"
HEADLESS=false
DURATION=0
TRAP_TRIGGERED=false
UBUNTU_VERSION=$(lsb_release -rs)

if ! command -v jq >/dev/null 2>&1; then
    echo "❌ 'jq' is required but not installed. Run: sudo apt install jq  (or rerun ./install.sh)"
    exit 1
fi

export SAFE_DIR_NAME=$(basename "$PWD" | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9_-')
export PROJECT_NAME="$SAFE_DIR_NAME"
export COMPOSE_PROJECT_NAME="$SAFE_DIR_NAME"
CONTAINER_NAME="${PROJECT_NAME}_gazebo"
export ROS2K_WS="$PWD"

while [[ "$#" -gt 0 ]]; do
    case $1 in
        -h|--help)
            echo "=========================================================="
            echo "🚀 ROS2K - Launch Sequence"
            echo "=========================================================="
            echo "  --scenario <name>     (default: 2vs2_default)"
            echo "  --strategy <name>     (default: strat_aggro)"
            echo "  --model <name>        (default: qwen2.5-coder:3b)"
            echo "  --relay <name>        (Available: only_sim_bots, hardware_mirror)"
            echo "  --explain             (Enable AI reasoning output)"
            echo "  --no-explain          (Disable AI reasoning)"
            echo "  --headless            (Run without visualizer)"
            echo "  --duration <seconds> (Auto-terminate after N seconds)"
            echo "=========================================================="
            exit 0 ;;
        --scenario) SCENARIO="$2"; shift ;;
        --strategy) STRATEGY="$2"; shift ;;
        --model) MODEL="$2"; shift ;;
        --explain) EXPLAIN_FLAG="--explain" ;;
        --no-explain) EXPLAIN_FLAG="--no-explain" ;;
        --relay) RELAY="$2"; shift ;;
        --headless) HEADLESS=true ;;
        --duration) DURATION="$2"; shift ;;
        *) echo "⚠️ Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

echo "=========================================================="
echo "🚀 FAST BOOT: R2K Launch Sequence... ($SCENARIO | Relay: $RELAY)"
echo "=========================================================="

# >>> WICHTIG: Wechsel in den src-Ordner für korrekten Python/ROS Kontext
cd src || { echo "❌ Ordner 'src' nicht gefunden! Bitte Struktur prüfen."; exit 1; }

RELAY_FILE="relay/${RELAY}.json"
if [ ! -f "$RELAY_FILE" ]; then
    echo "❌ Relay-Datei nicht gefunden: $RELAY_FILE"
    echo "💡 Verfügbare Relay-Dateien: $(ls relay/*.json 2>/dev/null | xargs -n1 basename -s .json | tr '\n' ' ')"
    exit 1
fi
REQUIRES_HARDWARE_SYNC=$(jq -r '.requires_hardware_sync' "$RELAY_FILE")
YAHBOOM_TOPIC=$(jq -r '[.mapping[] | select(.hardware_type=="yahboom") | .topic][0] // ""' "$RELAY_FILE")
K1_TOPIC=$(jq -r '[.mapping[] | select(.hardware_type=="k1") | .topic][0] // ""' "$RELAY_FILE")
YAHBOOM_NS=$(echo "$YAHBOOM_TOPIC" | sed 's|/cmd_vel||')
K1_NS=$(echo "$K1_TOPIC" | sed 's|/LocoApiTopicReq||')

echo "🤖 Relay bots ($RELAY):"
jq -r '.mapping | to_entries[] | "  \(.key): \(.value.hardware_type) → \(.value.topic)"' "$RELAY_FILE"

export ROS2K_WS="$PWD"
mkdir -p shared_state logs
rm -f shared_state/current_strategy.json shared_state/Worldstate.json

# --- Phase 1 instrumentation: auto-tag run ID for trace logs ---
export R2K_RUN_ID="${SCENARIO}_${STRATEGY}_$(date +%Y%m%d_%H%M%S)"
echo "📋 Run ID: $R2K_RUN_ID  (logs: src/logs/*_${R2K_RUN_ID}.jsonl)"

python3 setup_r2k.py --scenario "$SCENARIO" --strategy "$STRATEGY" --model "$MODEL" --relay "$RELAY" $EXPLAIN_FLAG || { echo "❌ Setup failed!"; exit 1; }

# ---- CLEANUP TRAP ----
cleanup() {
    if [ "$TRAP_TRIGGERED" = true ]; then return; fi
    TRAP_TRIGGERED=true
    echo -e "\n🛑 [TEARDOWN] Shutting down system..."

    if [ "$REQUIRES_HARDWARE_SYNC" = "true" ]; then
        if [ "$UBUNTU_VERSION" == "22.04" ]; then
            timeout 1 ros2 topic pub --once "$YAHBOOM_TOPIC" geometry_msgs/msg/Twist "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}" > /dev/null 2>&1 || true
            timeout 1 ros2 topic pub --once "$K1_TOPIC" booster_msgs/msg/RpcReqMsg "{uuid: 'emergency_stop', header: '{\"api_id\": 2000}', body: '{\"mode\": 1}'}" > /dev/null 2>&1 || true
        else
            docker exec -i $CONTAINER_NAME bash -c "source /opt/ros/humble/setup.bash && timeout 1 ros2 topic pub --once $YAHBOOM_TOPIC geometry_msgs/msg/Twist \"{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}\"" > /dev/null 2>&1 || true
            docker exec -i $CONTAINER_NAME bash -c "source /opt/ros/humble/setup.bash && timeout 1 ros2 topic pub --once $K1_TOPIC booster_msgs/msg/RpcReqMsg \"{uuid: 'emergency_stop', header: '{\\\"api_id\\\": 2000}', body: '{\\\"mode\\\": 1}'}\"" > /dev/null 2>&1 || true
        fi
    fi

    kill -9 $MONITOR_PID 2>/dev/null
    
    ../kill_r2k.sh > /dev/null 2>&1
    
    if [ "$UBUNTU_VERSION" == "22.04" ]; then
        pkill -9 -f "gazebo|gzserver|ruby|r2k_visualizer.py|referee_node|score_node|reward_node|state_aggregator|rule_evaluator_red|r2k_evaluator.py|tracker" > /dev/null 2>&1
        pkill -9 -f "python3.*ollama_sandbox_bridge" > /dev/null 2>&1
        pkill -9 -f micro_ros_agent > /dev/null 2>&1
    else
        docker stop uros_agent > /dev/null 2>&1 || true
        docker compose down > /dev/null 2>&1 || true
    fi
    echo "✅ Teardown complete."
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# ---- HARDWARE HOTSPOT ----
if [ "$REQUIRES_HARDWARE_SYNC" = "true" ]; then
    if nmcli -t -f NAME,TYPE connection show --active 2>/dev/null | grep -q '^Hotspot:802-11-wireless$'; then
        echo "📶 Hotspot 'maker4' already active, reusing existing connection."
    else
        nmcli device wifi hotspot ssid maker4 password nao12345
    fi
    
    echo "⏳ Warte auf Netzwerk-Routing (3s)..."
    sleep 3 
    
    if [ "$UBUNTU_VERSION" == "22.04" ]; then
        echo "🔌 Starting NATIVE micro-ROS Agent on Domain 0..."
        pkill -9 -f micro_ros_agent > /dev/null 2>&1
        bash -c "source /opt/ros/humble/setup.bash && source $PWD/uros_ws/install/setup.bash && export ROS_DOMAIN_ID=0 && ros2 run micro_ros_agent micro_ros_agent udp4 --port 8888" > /dev/null 2>&1 &
    else
        echo "🔌 Starting DOCKER micro-ROS Agent on Domain 0..."
        docker rm -f $(docker ps -a -q --filter ancestor=microros/micro-ros-agent:humble) > /dev/null 2>&1 || true
        docker run -d --name uros_agent --rm --net=host -e ROS_DOMAIN_ID=0 microros/micro-ros-agent:humble udp4 --port 8888 -v4 > /dev/null 2>&1
        sleep 3
    fi
fi

# --- Markdown Auto-Linker Bypass (Verhindert Syntaxfehler) ---
HTTP_PROT="http"
OLLAMA_LOCAL="${HTTP_PROT}://127.0.0.1:11434"
OLLAMA_DOCKER="${HTTP_PROT}://172.17.0.1:11434"

# ---- OLLAMA CHECK ----
echo "🧠 Checking Ollama AI Server..."
if curl -s "${OLLAMA_LOCAL}/api/tags" > /dev/null 2>&1; then
    echo "✅ Ollama ist bereits online und erreichbar."
else
    echo "🚀 Booting Ollama AI Server..."
    export OLLAMA_HOST=0.0.0.0
    nohup ollama serve > ollama.log 2>&1 &
    disown $!
    sleep 5
fi

if [[ "$SCENARIO" != 0vs* ]]; then
    echo "🔍 Prüfe, ob das Modell '$MODEL' lokal verfügbar ist..."
    if ! curl -s "${OLLAMA_LOCAL}/api/tags" | grep -q "\"name\":\"$MODEL\""; then
        echo "=========================================================="
        echo "❌ FEHLER: Das Modell '$MODEL' wurde nicht gefunden!"
        echo "💡 Lade es zuerst mit folgendem Befehl herunter:"
        echo "   ollama pull $MODEL"
        echo "=========================================================="
        echo "🛑 Abbruch der Startsequenz."
        exit 1
    fi
    echo "✅ Modell '$MODEL' ist bereit."
fi

export R2K_OLLAMA_URL="${OLLAMA_LOCAL}/api/generate"
export R2K_OLLAMA_MODEL=$MODEL

# ==========================================================
# 🟢 NATIVE LAUNCH (UBUNTU 22.04)
# ==========================================================
if [ "$UBUNTU_VERSION" == "22.04" ]; then
    echo "🟢 Nativer Modus aktiv: Bereite lokale Umgebung vor..."
    source /opt/ros/humble/setup.bash
    source ros2_ws/install/setup.bash
    source venv/bin/activate
    
    echo "🌍 Starting Gazebo natively..."
    if [ "$HEADLESS" = true ]; then
        ros2 launch r2k_scenario_spawner soccer_match.launch.py headless:=true > /dev/null 2>&1 &
    else
        ros2 launch r2k_scenario_spawner soccer_match.launch.py > /dev/null 2>&1 &
    fi

    # Fast-Polling Watchdog (0.2s)
    (
        sleep 10
        while true; do
            if ! pgrep -f "gazebo|gzserver|ruby" > /dev/null 2>&1; then
                if [ "$REQUIRES_HARDWARE_SYNC" = "true" ]; then
                    ros2 topic pub --once "$YAHBOOM_TOPIC" geometry_msgs/msg/Twist "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}" > /dev/null 2>&1 &
                fi
                pkill -f r2k_visualizer.py > /dev/null 2>&1
                kill -TERM $$ 2>/dev/null
                break
            fi
            sleep 0.2
        done
    ) &
    MONITOR_PID=$!

    echo "🤖 Waiting for Gazebo API & Spawning Bots..."
    sleep 2
    python3 ai_tactics/json_spawner.py

    if [ "$REQUIRES_HARDWARE_SYNC" = "true" ]; then
        echo "=========================================="
        echo "🚨 BITTE SCHALTE DEN YAHBOOM & K1 JETZT EIN 🚨"
        echo "=========================================="
        YAHBOOM_READY=false; K1_READY=false; WAIT_TIME=0
        while [ $WAIT_TIME -lt 10 ]; do
            if [ "$YAHBOOM_READY" = false ] && ros2 topic list 2>/dev/null | grep -q "${YAHBOOM_NS}/battery"; then
                echo "🔋 Yahboom Topic erkannt! Führe DDS Warm-Up durch..."
                ros2 topic echo --once --qos-reliability best_effort ${YAHBOOM_NS}/battery > /dev/null 2>&1 &
                echo "✅ YAHBOOM BEREIT!"
                YAHBOOM_READY=true
            fi
            if [ "$K1_READY" = false ] && ros2 topic list 2>/dev/null | grep -q "${K1_NS}/odometer_state"; then
                echo "⚙️ K1-INTERFACE ERKANNT! Führe DDS Warm-Up durch..."
                ros2 topic echo --once ${K1_NS}/LocoApiTopicResp > /dev/null 2>&1 &
                echo "✅ K1 BEREIT!"
                K1_READY=true
            fi
            if [ "$YAHBOOM_READY" = true ] && [ "$K1_READY" = true ]; then break; fi
            sleep 1; ((WAIT_TIME++))
        done
        
        if [ "$YAHBOOM_READY" = false ] || [ "$K1_READY" = false ]; then
            echo "⚠️ WARNUNG: Timeout erreicht. Hardware nicht vollständig erkannt. Starte trotzdem..."
        fi
    fi

    echo "⚡ Igniting Realtime Nodes & AI..."
    ros2 run r2k_world_model tracker > /dev/null 2>&1 &
    python3 referee_node.py > /dev/null 2>&1 &
    python3 score_node.py > /dev/null 2>&1 &
    python3 reward_node.py > /dev/null 2>&1 &
    python3 state_aggregator.py > /dev/null 2>&1 &
    python3 rule_evaluator_red.py > /dev/null 2>&1 &
    python3 ai_tactics/ollama_sandbox_bridge.py > /dev/null 2>&1 &
    
    echo "🧠 Starting Team Blue AI (Live Output)..."
    python3 -u ai_tactics/r2k_evaluator.py &
    
    # Duration-based auto-terminate (for batch evaluation)
    if [ "$DURATION" -gt 0 ]; then
        echo "⏱️  Auto-terminate scheduled after ${DURATION}s"
        (sleep "$DURATION"; echo "⏱️  Duration reached, triggering shutdown"; kill -TERM $$) &
    fi
    
    echo "📺 Launching Visualizer..."
    echo "=========================================================="
    echo "✅ System Online. Press CTRL+C to shutdown."
    echo "=========================================================="
    
    # Headless mode: skip visualizer
    if [ "$HEADLESS" = true ]; then
        echo "🏃 Headless mode: No visualizer"
        while true; do sleep 1; done
    fi
    
    # Ausführung des Visualizers ohne Fehlerunterdrückung
    python3 r2k_visualizer.py
    
    # Crash-Falle: Wenn der Visualizer abstürzt, fangen wir das ab und halten das Terminal offen.
    if [ $? -ne 0 ]; then
        echo "=========================================================="
        echo "⚠️ CRASH ERKANNT: Der Visualizer (r2k_visualizer.py) ist abgestürzt!"
        echo "Das System bleibt für Debugging-Zwecke am Leben. Scrolle hoch, um den Python-Fehler zu lesen."
        echo "Drücke CTRL+C, um das Teardown auszulösen."
        echo "=========================================================="
        while true; do sleep 1; done
    fi

# ==========================================================
# 🐳 DOCKER LAUNCH (UBUNTU 24.04+)
# ==========================================================
else
    xhost +local:root > /dev/null 2>&1
    export DISPLAY=$DISPLAY

    docker compose down > /dev/null 2>&1 || true
    docker compose up -d > /dev/null 2>&1
    sleep 2

    DOCKER_BASE="docker exec -d $CONTAINER_NAME bash -c"
    SOURCE_CMD="cd /workspace && source /opt/ros/humble/setup.bash && source ros2_ws/install/setup.bash"

    echo "🌍 Starting Gazebo in Docker..."
    if [ "$HEADLESS" = true ]; then
        $DOCKER_BASE "$SOURCE_CMD && ros2 launch r2k_scenario_spawner soccer_match.launch.py headless:=true > /dev/null 2>&1"
    else
        $DOCKER_BASE "$SOURCE_CMD && ros2 launch r2k_scenario_spawner soccer_match.launch.py > /dev/null 2>&1"
    fi

    # Fast-Polling Watchdog (0.2s)
    (
        sleep 10
        while true; do
            if ! docker exec $CONTAINER_NAME pgrep -f "gazebo|gzserver|ruby" > /dev/null 2>&1; then
                if [ "$REQUIRES_HARDWARE_SYNC" = "true" ]; then
                    docker exec -d $CONTAINER_NAME bash -c "$SOURCE_CMD && ros2 topic pub --once $YAHBOOM_TOPIC geometry_msgs/msg/Twist \"{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}\"" > /dev/null 2>&1
                fi
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

    if [ "$REQUIRES_HARDWARE_SYNC" = "true" ]; then
        echo "=========================================="
        echo "🚨 BITTE SCHALTE DEN YAHBOOM & K1 JETZT EIN 🚨"
        echo "=========================================="
        YAHBOOM_READY=false; K1_READY=false; WAIT_TIME=0
        while [ $WAIT_TIME -lt 10 ]; do
            if [ "$YAHBOOM_READY" = false ] && docker exec $CONTAINER_NAME bash -c "$SOURCE_CMD && ros2 topic list 2>/dev/null" | grep -q "${YAHBOOM_NS}/battery"; then
                echo "🔋 Yahboom Topic erkannt! Führe DDS Warm-Up durch..."
                docker exec -i $CONTAINER_NAME bash -c "$SOURCE_CMD && ros2 topic echo --once --qos-reliability best_effort ${YAHBOOM_NS}/battery > /dev/null 2>&1" &
                echo "✅ YAHBOOM BEREIT!"
                YAHBOOM_READY=true
            fi
            if [ "$K1_READY" = false ] && docker exec $CONTAINER_NAME bash -c "$SOURCE_CMD && ros2 topic list 2>/dev/null" | grep -q "${K1_NS}/odometer_state"; then
                echo "⚙️ K1-INTERFACE ERKANNT! Führe DDS Warm-Up durch..."
                docker exec -i $CONTAINER_NAME bash -c "$SOURCE_CMD && ros2 topic echo --once ${K1_NS}/LocoApiTopicResp > /dev/null 2>&1" &
                echo "✅ K1 BEREIT!"
                K1_READY=true
            fi
            if [ "$YAHBOOM_READY" = true ] && [ "$K1_READY" = true ]; then break; fi
            sleep 1; ((WAIT_TIME++))
        done
        
        if [ "$YAHBOOM_READY" = false ] || [ "$K1_READY" = false ]; then
            echo "⚠️ WARNUNG: Timeout erreicht. Hardware nicht vollständig erkannt. Starte trotzdem..."
        fi
    fi

    echo "⚡ Igniting Realtime Nodes & AI..."
    $DOCKER_BASE "$SOURCE_CMD && ros2 run r2k_world_model tracker > /dev/null 2>&1"
    $DOCKER_BASE "$SOURCE_CMD && python3 referee_node.py > /dev/null 2>&1"
    $DOCKER_BASE "$SOURCE_CMD && python3 score_node.py > /dev/null 2>&1"
    $DOCKER_BASE "$SOURCE_CMD && python3 reward_node.py > /dev/null 2>&1"
    docker exec -d -e R2K_RUN_ID="$R2K_RUN_ID" $CONTAINER_NAME bash -c "$SOURCE_CMD && python3 state_aggregator.py > /dev/null 2>&1"
    $DOCKER_BASE "$SOURCE_CMD && python3 rule_evaluator_red.py > /dev/null 2>&1"
    $DOCKER_BASE "$SOURCE_CMD && python3 ai_tactics/ollama_sandbox_bridge.py > /dev/null 2>&1"
    
    echo "🧠 Starting Team Blue AI (Live Output)..."
    docker exec -d -e PYTHONUNBUFFERED=1 -e PYTHONWARNINGS="ignore" -e R2K_OLLAMA_MODEL=$MODEL -e R2K_OLLAMA_URL="${OLLAMA_DOCKER}/api/generate" -e R2K_RUN_ID="$R2K_RUN_ID" $CONTAINER_NAME bash -c "$SOURCE_CMD && python3 -u ai_tactics/r2k_evaluator.py"
    
    # Duration-based auto-terminate (for batch evaluation)
    if [ "$DURATION" -gt 0 ]; then
        echo "⏱️  Auto-terminate scheduled after ${DURATION}s"
        (sleep "$DURATION"; echo "⏱️  Duration reached, triggering shutdown"; kill -TERM $$) &
    fi
    
    echo "📺 Launching Visualizer..."
    echo "=========================================================="
    echo "✅ System Online. Press CTRL+C to shutdown."
    echo "=========================================================="
    
    # Headless mode: skip visualizer
    if [ "$HEADLESS" = true ]; then
        echo "🏃 Headless mode: No visualizer"
        while true; do sleep 1; done
    fi
    
    # Ausführung des Visualizers ohne Fehlerunterdrückung
    docker exec -it -e PYTHONWARNINGS="ignore" -e DISPLAY=$DISPLAY -e QT_X11_NO_MITSHM=1 $CONTAINER_NAME bash -c "$SOURCE_CMD && python3 r2k_visualizer.py"
    
    # Crash-Falle
    if [ $? -ne 0 ]; then
        echo "=========================================================="
        echo "⚠️ CRASH ERKANNT: Der Visualizer (r2k_visualizer.py) ist im Docker abgestürzt!"
        echo "Das System bleibt für Debugging-Zwecke am Leben. Scrolle hoch, um den Python-Fehler zu lesen."
        echo "Drücke CTRL+C, um das Teardown auszulösen."
        echo "=========================================================="
        while true; do sleep 1; done
    fi
fi
