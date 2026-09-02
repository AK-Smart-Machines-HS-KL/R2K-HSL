from stable_baselines3 import PPO
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import SubprocVecEnv
from stable_baselines3.common.callbacks import CheckpointCallback, CallbackList
import wandb
from wandb.integration.sb3 import WandbCallback
from legswing_env import LegswingEnv

model_exists = True  # if True, set relative model path
model_path = "poc/mujoco_legswing/booster-k1/final/k1_sit_upright_rl.zip"

# Factory for multithreading
def make_env(rank, seed=0):
    def _init():
        env = Monitor(LegswingEnv("poc/mujoco_legswing/booster-k1/assets/K1_sitting.xml", seed=seed + rank))
        return env
    return _init


# decrease the learning rate over time
def linear_schedule(init_value: float):
    def func(progress_remaining: float) -> float:
        return progress_remaining * init_value
    return func


def main():
    num_cpu = 16                 # Number of parallel environments
    num_timesteps = 20_000_000   # Total training timesteps
    n_steps = 4096               # Number of steps per environment before PPO update
    batch_size = 1024            # Samples per gradient update
    n_epochs = 10                # Number of passes over collected data per update
    init_learning_rate = 0.0003  # initial learning rate (decreasing over time)
    num_checkpoints = 50         # Number of checkpoints per training

    # generate one env for each in num_cpu
    env = SubprocVecEnv([make_env(i, 0) for i in range(num_cpu)])

    # initialize WandB-Run
    run = wandb.init(
        project="booster-k1",
        config={
            "n_steps": n_steps,
            "batch_size": batch_size,
            "n_epochs": n_epochs,
            "init_learning_rate": init_learning_rate
        },
        sync_tensorboard=True,
        save_code=True
    )
    run.log_code("./src")

    # log gradients every 100 steps in wandb
    wandb_callback = WandbCallback(gradient_save_freq=100, verbose=2)

    # set checkpoint_frequency and callback
    save_freq = num_timesteps / num_cpu / num_checkpoints
    checkpoint_callback = CheckpointCallback(
        save_freq=save_freq,
        save_path=f"./poc/mujoco_legswing/booster-k1/models/cpu/{run.id}/checkpoints",
        name_prefix="k1_legswing_rl"
    )
    callbacks = CallbackList([wandb_callback, checkpoint_callback])

    # configure training
    if model_exists:
        model = PPO.load(model_path, env=env)
    else:
        model = PPO(
            "MlpPolicy",
            env,
            verbose=1,
            device="cuda",
            n_steps=n_steps,
            batch_size=batch_size,
            n_epochs=n_epochs,
            learning_rate=linear_schedule(init_learning_rate),
            tensorboard_log=f"runs/{run.id}"
        )
    
    # start training
    model.learn(total_timesteps=num_timesteps, callback=callbacks)

    model.save(f"./poc/mujoco_legswing/booster-k1/models/cpu/{run.id}/k1_legswing_rl_final.zip")

    run.finish()


if __name__ == "__main__":
    main()
