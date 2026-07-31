import time
import mujoco
import mujoco.viewer
from stable_baselines3 import PPO
from legswing_env import LegswingEnv

auto_reset = False

def main():

    env = LegswingEnv("poc/mujoco_legswing/booster-k1/assets/K1_sitting.xml")


    # load model to be evaluated by relative path
    model = PPO.load("poc/mujoco_legswing/booster-k1/models/cpu/i902a5b0/checkpoints/k1_legswing_rl_1600000_steps.zip", env=env)


    obs, _ = env.reset()

    # open the MuJoCo-Viewer
    with mujoco.viewer.launch_passive(env.model, env.data) as viewer:
        real_time_start = time.perf_counter()
        while viewer.is_running():
            sim_time_target = time.perf_counter() - real_time_start

            while env.data.time < sim_time_target:
                action, _ = model.predict(obs, deterministic=True)
                obs, reward, terminated, truncated, info = env.step(action)

                # Auto-reset
                if auto_reset and (terminated or truncated):
                    obs, _ = env.reset()
                    
            viewer.sync()


if __name__ == "__main__":
    main()
