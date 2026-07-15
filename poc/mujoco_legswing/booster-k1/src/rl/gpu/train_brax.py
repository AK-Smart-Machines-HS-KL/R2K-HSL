from pathlib import Path
import optax
import wandb
from brax.training.agents.ppo import train
from brax.io import model
from legswing_mjx_env import LegswingMJXEnv

# Hyperparameters
# batch_size * num_minibatches must be divisible by num_envs
num_timesteps = 20_000_000
num_evals = 20
num_eval_envs = 4
reward_scaling = 1.0
episode_length = 1000
num_envs = 128
unroll_length = 256
batch_size = 64
num_minibatches = 4
num_updates_per_batch = 15
init_learning_rate = 0.0005
entropy_cost = 0.031
discounting = 0.99
gae_lambda = 0.95

# save interim results
def _save_checkpoint(current_params, run, current_steps):
    ckpt_dir = Path(f"models/gpu/{run.id}/checkpoints")
    ckpt_dir.mkdir(parents=True, exist_ok=True)

    file_path = ckpt_dir / f"k1_legswing_rl_{current_steps}_steps.pkl"
    model.save_params(str(file_path), current_params)


def main():

    env = LegswingMJXEnv("assets/K1_sitting.xml")

    # set learning_rate-scheduler
    steps_per_unroll = num_envs * unroll_length
    total_updates = (num_timesteps // steps_per_unroll) * (num_minibatches * num_updates_per_batch)
    
    learning_rate_schedule = optax.linear_schedule(
        init_value=init_learning_rate,
        end_value=0.0,
        transition_steps=total_updates
    )
    
    # initialize WandB-Run
    run = wandb.init(
        project="booster-k1",
        config={
            "algorithm": "PPO",
            "num_timesteps": num_timesteps,
            "num_evals": num_evals,
            "reward_scaling": reward_scaling,
            "unroll_length": unroll_length,
            "num_minibatches": num_minibatches,
            "num_updates_per_batch": num_updates_per_batch,
            "learning_rate": learning_rate_schedule,
            "entropy_cost": entropy_cost,
            "discounting": discounting,
            "gae_lambda": gae_lambda
        },
        sync_tensorboard=True,
        save_code=True
    )
    run.log_code("./src")

    print("\n=== Start Training ===\n")

    # configure and start training
    make_policy, params, metrics = train.train(
        environment=env,
        num_timesteps=num_timesteps,
        num_envs=num_envs,
        episode_length=episode_length,
        action_repeat=1,
        learning_rate=learning_rate_schedule,
        entropy_cost=entropy_cost,
        discounting=discounting,
        unroll_length=unroll_length,
        batch_size=batch_size,
        num_minibatches=num_minibatches,
        num_updates_per_batch=num_updates_per_batch,
        reward_scaling=reward_scaling,
        gae_lambda=gae_lambda,
        seed=0,
        num_evals=num_evals,
        num_eval_envs=num_eval_envs,
        progress_fn=lambda num_steps, metrics: wandb.log(metrics, step=num_steps),
        policy_params_fn=lambda current_params: _save_checkpoint(current_params, run, num_timesteps)
    )

    print("\n=== Stop Training ===\n")

    # model.save_params(f"models/gpu/{run.id}/k1_legswing_rl_final.pkl", final_params)
    
    run.finish()


if __name__ == "__main__":
    main()