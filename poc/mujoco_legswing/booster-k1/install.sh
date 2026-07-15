#!/bin/bash
set -e # Bricht bei Fehlern sofort ab

echo "🚀 Booster-K1 MuJoCo RL Setup-Assistent"
echo "================================="

# Prüfen, ob Conda/Miniforge installiert ist
if ! command -v conda &> /dev/null; then
    echo "🔍 Miniforge wurde nicht gefunden. Starte Download und Installation..."
    curl -L -O "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-$(uname)-$(uname -m).sh"
    echo "⚠️ Bitte folge den Anweisungen des Miniforge-Installers."
    bash "Miniforge3-$(uname)-$(uname -m).sh"
    echo "🔄 Bitte starte dein Terminal neu und führe das Skript erneut aus."
    exit 0
fi

echo "Welche Umgebung möchtest du einrichten?"
echo "1) CPU-Modus (Stable-Baselines3 + PyTorch Core)"
echo "2) GPU-Modus (JAX + Flax + Brax)"
read -p "Auswahl (1 oder 2): " MODE

if [ "$MODE" == "1" ]; then
    echo "🟢 Richte CPU-Umgebung (k1_env_cpu) ein..."
    
    conda create -n k1_env_cpu python=3.11 pip -y
    
    CONDA_BASE=$(conda info --base)
    source "$CONDA_BASE/etc/profile.d/conda.sh"
    conda activate k1_env_cpu
    
    echo "📦 Installiere minimale CPU-Pakete..."
    pip install --upgrade pip
    pip install torch==2.11.0 mujoco==3.8.1 gymnasium==1.3.0 wandb==0.27.0
    pip install "stable-baselines3==2.8.0[extra]"
    
    echo "🧪 Teste Installation..."
    python -c "import torch; import stable_baselines3; print('✅ CPU-Pipeline erfolgreich verifiziert!')"
    echo "Nutze 'conda activate k1_env_cpu' zum Starten."

elif [ "$MODE" == "2" ]; then
    echo "🔥 Richte GPU-Umgebung (k1_env_gpu) ein..."
    
    conda create -n k1_env_gpu python=3.11 pip -y
    
    CONDA_BASE=$(conda info --base)
    source "$CONDA_BASE/etc/profile.d/conda.sh"
    conda activate k1_env_gpu
    
    echo "📦 Installiere minimale GPU-Pakete..."
    pip install --upgrade pip
    pip install --upgrade "jax[cuda13]==0.10.1"
    pip install mujoco==3.8.1 mujoco-warp==3.9.0.1 flax==0.12.7 optax==0.2.8 brax==0.14.2 wandb==0.27.0 tensorboard==2.20.0
    
    echo "🧪 Teste JAX GPU-Erkennung..."
    python -c "import jax; print('✅ JAX Backend:', jax.default_backend(), '| Gefundene GPUs:', jax.devices())"
    echo "Nutze 'conda activate k1_env_gpu' zum Starten."

else
    echo "❌ Ungültige Auswahl. Abbruch."
    exit 1
fi

echo "================================="
echo "💡 Vergiss nicht, dich bei Weights & Biases anzumelden: wandb login"