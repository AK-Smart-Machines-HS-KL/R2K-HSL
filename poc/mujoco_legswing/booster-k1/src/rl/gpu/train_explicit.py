import jax
import jax.numpy
import optax
import wandb
import orbax.checkpoint
from flax import linen
from flax.training.train_state import TrainState
from brax.envs.wrappers import training
from pathlib import Path
from legswing_mjx_env import LegswingMJXEnv

# Number of steps between checkpoints
SAVE_FREQ = 1_048_576

# Hyperparameters
NUM_ENVS = 1024
NUM_STEPS = 256
MINIBATCH_SIZE = 2048
TOTAL_TIMESTEPS = 10_000_000
GAMMA = 0.99
GAE_LAMBDA = 0.95

NUM_EPOCHS = 15
LEARNING_RATE = 0.00026168250526212707
CLIP_EPS = 0.1
ENT_COEF = 0.03128628696134781
MAX_GRAD_NORM = 0.5
VF_COEF = 0.6355702124640411
LAYER_SIZE = 256

# True: ignore hyperparameters from this script and turn off checkpoints
# False: normal training with the set hyperparameters and checkpoints
sweep = False

class ActorCritic(linen.Module):
    action_dim: int
    layer_size: int

    @linen.compact
    def __call__(self, obs: jax.Array):
        
        # Shared feature extractor
        x = linen.Dense(self.layer_size)(obs); x = linen.tanh(x)
        x = linen.Dense(self.layer_size)(x); x = linen.tanh(x)

        # Actor head: Predicts the mean of the action distribution
        mean = linen.Dense(self.action_dim)(x)

        log_std = self.param("log_std", linen.initializers.zeros, (self.action_dim,))

        # Critic head: Predicts the state-value
        value = linen.Dense(1)(x).squeeze(-1)

        return mean, jax.numpy.exp(log_std), value
    

# computes how much the network must be adjusted
def log_prob(mean, std, action):
    return -0.5 * jax.numpy.sum(((action - mean) / std) ** 2 + 2 * jax.numpy.log(std) + jax.numpy.log(2 * jax.numpy.pi), axis=-1)


# computes how insecure the network is in its choices
def entropy(std):
    return 0.5 * jax.numpy.sum(jax.numpy.log(2 * jax.numpy.pi * jax.numpy.e * std ** 2), axis=-1)


# factory of collect_rollout
def make_collect_fn(env, network):
    v_step = jax.jit(jax.vmap(env.step))

    # simulation and experience gathering
    @jax.jit
    def collect_rollout(train_state, states, obs, rng):

        def one_step(carry, _):
            states, obs, rng = carry
            rng, key = jax.random.split(rng)

            # generate the next action depending on previous results
            mean, std, value = network.apply({"params": train_state.params}, obs)
            noise = jax.random.normal(key, mean.shape)
            action = jax.numpy.clip(mean + std * noise, -1.0, 1.0)

            # calculate the probability of this action
            lp = log_prob(mean, std, action)

            # hand the action over into the simulation
            states_next = v_step(states, action)

            # results of the simulated action
            obs_next = states_next.obs
            reward = states_next.reward
            terminated = states_next.terminated
            truncated = states_next.truncated
            done = terminated | truncated

            # collect the experience of this step
            traj_step = {
                'obs': obs,
                'action': action,
                'reward': reward,
                'done': done,
                'value': value,
                'lp': lp,
                'terminated': terminated,
                'truncated': truncated
            }

            return (states_next, obs_next, rng), traj_step
        
        # JAX-loop: repeat one_step for the number of steps
        # traj contains num_envs * num_steps experiences (traj_step)
        (states, obs, rng), traj = jax.lax.scan(one_step, (states, obs, rng), None, length=NUM_STEPS)

        _, _, last_value = network.apply({"params": train_state.params}, obs)
        return states, obs, rng, traj, last_value
    
    return collect_rollout


# processes trajectories to estimate how much better an action was compared to the base expectation
@jax.jit
def compute_gae(rewards, dones, values, last_value):
    def gae_step(carry, t):
        gae, next_val = carry
        r, d, v = rewards[t], dones[t], values[t]

        # difference between expected reward and gained reward
        delta = r + GAMMA * next_val * (1.0 - d) - v

        # accumulate advantages backward through time with exponential decay
        gae = delta + GAMMA * GAE_LAMBDA * (1.0 - d) * gae

        return (gae, v), gae
    
    _, advantages = jax.lax.scan(gae_step, (jax.numpy.zeros(NUM_ENVS), last_value), jax.numpy.arange(NUM_STEPS - 1, -1, -1))

    # flip advantages back to chronological order
    advantages = advantages[::-1]

    returns = advantages + values

    return advantages, returns


# update the network weights and behaviour dependent on the trajectories (experiences) of the batch
@jax.jit
def ppo_update(train_state, batch):
    obs_b, act_b, adv_b, ret_b, logp_old_b = batch

    # standardization
    adv_b = (adv_b - adv_b.mean()) / (adv_b.std() + 1e-8)

    def loss_fn(params):
        mean, std, value = train_state.apply_fn({"params": params}, obs_b)

        lp = log_prob(mean, std, act_b)
        ent = entropy(std).mean()
        ratio = jax.numpy.exp(lp - logp_old_b)

        # Policy Gradient Loss (Actor Loss)
        pg_loss = -jax.numpy.minimum(ratio * adv_b, jax.numpy.clip(ratio, 1.0 - CLIP_EPS, 1.0 + CLIP_EPS) * adv_b,).mean()

        # Value Function Loss (Critic Loss)
        vf_loss = 0.5 * jax.numpy.mean((value - ret_b) ** 2)

        # Total loss (to be minimized)
        loss = pg_loss + VF_COEF * vf_loss - ENT_COEF * ent

        return loss, {"pg_loss": pg_loss, "vf_loss": vf_loss, "entropy": ent, "loss": loss}
    
    (_, metrics), grads = jax.value_and_grad(loss_fn, has_aux=True)(train_state.params)

    # gradient clipping (cut off extreme values possibly caused by faulty inputs)
    grads = jax.tree_util.tree_map(lambda g: jax.numpy.clip(g, -MAX_GRAD_NORM, MAX_GRAD_NORM), grads)

    # update the train_state
    train_state = train_state.apply_gradients(grads=grads)

    return train_state, metrics


def main():
    if sweep:  # get hyperparameters from sweep.yaml
        run = wandb.init(project="booster-k1", save_code=True)

        NUM_EPOCHS = run.config.get("num_epochs")
        LEARNING_RATE = run.config.get("learning_rate")
        CLIP_EPS = run.config.get("clip_epsilon")
        ENT_COEF = run.config.get("entropy_coefficient")
        MAX_GRAD_NORM = run.config.get("max_grad_norm")
        VF_COEF = run.config.get("vf_coefficient")
        LAYER_SIZE = run.config.get("layer_size")
    else:  # use hyperparameters from the script
        run = wandb.init(
            project="booster-k1",
            config={
                "algorithm": "PPO-MJX",
                "num_envs": NUM_ENVS,
                "num_steps": NUM_STEPS,
                "minibatch_size": MINIBATCH_SIZE,
                "total_timesteps": TOTAL_TIMESTEPS,
                "gamma": GAMMA,
                "gae_lambda": GAE_LAMBDA,
                "num_epochs": NUM_EPOCHS,
                "learning_rate": LEARNING_RATE,
                "clip_eps": CLIP_EPS,
                "ent_coef": ENT_COEF,
                "max_grad_norm": MAX_GRAD_NORM,
                "vf_coef": VF_COEF,
                "layer_size": LAYER_SIZE
            },
            save_code=True
        )

    # AutoResetWrapper resets each env indivually if terminated
    env = training.AutoResetWrapper(LegswingMJXEnv("poc/mujoco_legswing/booster-k1/assets/K1_sitting.xml"))
    network = ActorCritic(action_dim=env.act_size, layer_size=LAYER_SIZE)

    # create the train_state
    rng = jax.random.PRNGKey(0)
    rng, k = jax.random.split(rng)
    params = network.init(k, jax.numpy.zeros(env.obs_size))["params"]
    tx = optax.adam(LEARNING_RATE)
    train_state = TrainState.create(apply_fn=network.apply, params=params, tx=tx)

    # initialize the checkpointer and save-directories
    ckptr = orbax.checkpoint.PyTreeCheckpointer()
    ckpt_dir = Path(f"checkpoints/{run.id}").resolve()
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    savefile = Path(f"poc/mujoco_legswing/booster-k1/{ckpt_dir}/k1_legswing_rl_final").resolve()


    collect_rollout = make_collect_fn(env, network)

    # start each environment with slighlty different starting position 
    rng, *env_rngs = jax.random.split(rng, NUM_ENVS + 1)
    env_rngs = jax.numpy.stack(env_rngs)
    states_all = jax.jit(jax.vmap(env.reset))(env_rngs)
    obs_all = states_all.obs

    total_steps = 0
    last_save = 0
    num_saves = 1

    print("\n=== Start Training ===\n")

    while total_steps < TOTAL_TIMESTEPS:

        # data gathering (simulation)
        rng, rollout_rng = jax.random.split(rng)
        states_all, obs_all, rng, traj, last_val = collect_rollout(train_state, states_all, obs_all, rollout_rng)

        # extract the parts of the trajectories
        obs_t, act_t, rew_t, done_t, val_t, logp_t = traj

        # evaluate the results
        adv_t, ret_t = compute_gae(rew_t, done_t, val_t, last_val)

        # flatten the 3D Array into a 1D Array
        flat = lambda x: x.reshape(-1, *x.shape[2:])
        obs_f, act_f, adv_f, ret_f, logp_f = map(flat, (obs_t, act_t, adv_t, ret_t, logp_t))


        # each batch is used NUM_EPOCHS times, split into minibatches to update the network
        n_samples = obs_f.shape[0]
        epoch_metrics = []
        for _ in range(NUM_EPOCHS):
            rng, perm_rng = jax.random.split(rng)
            perm = jax.random.permutation(perm_rng, n_samples)
            for start in range(0, n_samples, MINIBATCH_SIZE):
                idx = perm[start : start + MINIBATCH_SIZE]
                batch = (obs_f[idx], act_f[idx], adv_f[idx], ret_f[idx], logp_f[idx])
                train_state, metrics = ppo_update(train_state, batch)
                epoch_metrics.append(metrics)

        # WandB logging
        total_steps += NUM_STEPS * NUM_ENVS
        avg = {k: float(jax.numpy.mean(jax.numpy.stack([m[k] for m in epoch_metrics]))) for k in epoch_metrics[0]}
        wandb.log({
            "global_step": total_steps,
            "train/reward_mean": float(rew_t.mean()),
            "train/reward_max": float(rew_t.max()),
            "train/policy_loss": avg["pg_loss"],
            "train/value_loss": avg["vf_loss"],
            "train/entropy": avg["entropy"],
            "train/loss": avg["loss"]
        }, step=total_steps)
        
        # save checkpoints if sweep = False
        if total_steps - last_save >= SAVE_FREQ and not sweep:
            path = ckpt_dir / f"checkpoint_{num_saves}"
            ckptr.save(str(path), train_state)
            wandb.save(str(savefile))
            print(f"\n=== saved into {path} ===\n")
            num_saves += 1
            last_save = total_steps

    # save final version
    ckptr.save(str(savefile), train_state)
    wandb.save(str(savefile))
    run.finish()


if __name__ == "__main__":
    main()