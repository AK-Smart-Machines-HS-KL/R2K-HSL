#!/bin/bash
UBUNTU_VERSION=$(lsb_release -rs)
echo "🚀 ROS2K Setup gestartet (System: Ubuntu $UBUNTU_VERSION)"

# 1. Projektnamen dynamisch aus dem Root-Verzeichnis generieren (für Docker)
export SAFE_DIR_NAME=$(basename "$PWD" | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9_-')
echo "⚙️ Setze Projektname dynamisch: $SAFE_DIR_NAME"

# 2. In den src-Ordner wechseln, da dort ros2_ws, uros_ws und docker-compose.yml verwaltet werden
cd src || { echo "❌ Ordner 'src' nicht gefunden! Bitte Struktur prüfen."; exit 1; }

if [ "$UBUNTU_VERSION" == "22.04" ]; then
    echo "🟢 Nativer Modus (Ubuntu 22.04): Richte ROS 2 Repositories ein..."
    sudo apt update && sudo apt install -y curl gnupg2 lsb-release jq
    sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
    
    echo "📦 Installiere native ROS 2 Humble Pakete & Build-Tools..."
    sudo apt update
    sudo apt install -y python3-pip python3-venv gazebo ros-humble-desktop ros-humble-gazebo-ros-pkgs \
                        libxcb-cursor0 libgl1-mesa-glx libxkbcommon-x11-0 libegl1 python3-tk \
                        python3-colcon-common-extensions ros-humble-ament-cmake python3-catkin-pkg \
                        python3-rosdep python3-vcstool build-essential cmake
    
    echo "🏗️ Kompiliere Haupt-ROS 2 Workspace..."
    source /opt/ros/humble/setup.bash
    cd ros2_ws && colcon build && cd ..
    
    echo "⚙️ Kompiliere NATIVEN micro-ROS Agenten (Lokal im aktuellen Ordner)..."
    sudo rosdep init 2>/dev/null || true
    rosdep update
    mkdir -p uros_ws/src
    cd uros_ws
    if [ ! -d "src/micro_ros_setup" ]; then
        git clone -b humble https://github.com/micro-ROS/micro_ros_setup.git src/micro_ros_setup
    fi
    source /opt/ros/humble/setup.bash
    rosdep install --from-paths src --ignore-src -y
    colcon build
    source install/local_setup.bash
    ros2 run micro_ros_setup create_agent_ws.sh
    ros2 run micro_ros_setup build_agent.sh
    cd ..
    
    echo "🐍 Erstelle Python-Venv mit strikten Versionen (Numpy < 2.0)..."
    [ -d "venv" ] && rm -rf venv
    python3 -m venv --system-site-packages venv 
    source venv/bin/activate
    pip install --upgrade pip
    pip install requests "numpy<2.0.0" PyQt6 matplotlib mplsoccer
    
    echo "✅ Native Installation auf Ubuntu 22.04 erfolgreich abgeschlossen."

elif [[ "$UBUNTU_VERSION" == 24.* ]]; then
    echo "🐳 Docker Modus: Installiere Docker-Umgebung für Ubuntu 24.04..."
    sudo apt update
    sudo apt install -y jq docker.io docker-buildx docker-compose-v2
    sudo systemctl enable --now docker
    sudo usermod -aG docker $USER
    
    # --- DYNAMISCHER PROJEKTNAME ---
    # .env wird in src/ geschrieben, damit docker-compose.yml ihn aufgreifen kann
    echo "COMPOSE_PROJECT_NAME=$SAFE_DIR_NAME" > .env
    echo "PROJECT_NAME=$SAFE_DIR_NAME" >> .env
    
    echo "🏗️ Kompiliere ROS 2 Workspace im Docker-Container..."
    docker compose up -d
    sleep 5
    CONTAINER_NAME="${SAFE_DIR_NAME}_gazebo"
    docker exec $CONTAINER_NAME bash -c "source /opt/ros/humble/setup.bash && cd /workspace/ros2_ws && colcon build"
    docker compose down

    # Configure Ollama to bind to 0.0.0.0 so Docker containers can reach it
    # via the bridge gateway (172.17.0.1). Without this, the evaluator inside
    # the container cannot reach Ollama on 127.0.0.1 (host loopback only),
    # resulting in silent dead-blue-team. See AGENTS.md axiom 5.
    if systemctl cat ollama.service &>/dev/null; then
        echo "🔧 Configuring Ollama systemd service for Docker bridge access..."
        sudo mkdir -p /etc/systemd/system/ollama.service.d
        echo -e '[Service]\nEnvironment="OLLAMA_HOST=0.0.0.0"' | \
            sudo tee /etc/systemd/system/ollama.service.d/override.conf > /dev/null
        sudo systemctl daemon-reload
        sudo systemctl restart ollama
        sleep 2
        if ss -tlnp | grep -q "0.0.0.0:11434"; then
            echo "✅ Ollama now listens on 0.0.0.0:11434 (Docker bridge accessible)."
        else
            echo "⚠️ WARNING: Ollama bind override did not take effect. Manual fix needed:"
            echo "   sudo systemctl edit ollama  →  [Service]  →  Environment=\"OLLAMA_HOST=0.0.0.0\""
        fi
    else
        echo "⚠️ NOTE: ollama.service not found. If you start Ollama manually,"
        echo "   use: OLLAMA_HOST=0.0.0.0 ollama serve"
    fi

    echo "✅ Docker installiert und Workspace kompiliert!"
    echo "Nun kannst du das System mit './launch_r2k.sh' aus dem Hauptverzeichnis starten."
else
    echo "❌ Fehler: System $UBUNTU_VERSION wird nicht unterstützt."
    exit 1
fi
