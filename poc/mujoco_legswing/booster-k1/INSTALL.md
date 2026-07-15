# 🛠️ Installationsanleitung & Software-Stände

Diese Anleitung beschreibt die Einrichtung der minimalen Reinforcement-Learning-Umgebungen.

---

## 📋 Software-Stände (Soll-Konfiguration)

### 1. CPU-Trainingsumgebung (`k1_env_cpu`)
* **Python-Version:** `3.11.15`
* **Kern-Pakete:**
  * `mujoco` >= 3.0.0 , getestet auf: 3.8.1 (Physik-Simulation)
  * `gymnasium` >= 0.29.0 , getestet auf: 1.3.0 (RL-Schnittstelle)
  * `torch` getestet auf: 2.11.0 (Reines CPU-Backend für die Netzwerkberechnung)
  * `stable-baselines3[extra]` >= 2.0.0 , getestet auf: 2.8.0 (PPO-Algorithmus)
  * `wandb` getestet auf: 0.27.0 (Logging)

### 2. GPU-Trainingsumgebung (`k1_env_gpu`)
* **Python-Version:** `3.11.15`
* **Kern-Pakete:**
  * `jax[cuda13]` getestet auf: 0.10.1 (Hardwarebeschleunigte Matrixberechnung)
  * `mujoco` >= 3.0.0 , getestet auf: 3.8.1 (MJX kompatibel)
  * `mujoco-warp` getestet auf: 3.9.0.1
  * `flax` getestet auf: 0.12.7 (Netzwerk-Framework für JAX)
  * `optax` getestet auf: 0.2.8 (Optimierungs-Framework für JAX)
  * `brax` getestet auf: 0.14.2 (Vektorisierte RL-Trainings-Pipeline)
  * `wandb` getestet auf: 0.27.0 (Logging)
  * `tensorboard` getestet auf: 2.20.0 (Logging)

---

## Automatische Installation

```bash
chmod +x install.sh
./install.sh