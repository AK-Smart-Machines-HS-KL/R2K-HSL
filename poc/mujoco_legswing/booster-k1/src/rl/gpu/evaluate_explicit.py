import time
import numpy
import pathlib
import mujoco
import mujoco.viewer
import jax.numpy
import orbax.checkpoint
from legswing_mjx_env import LegswingMJXEnv
from train_explicit import ActorCritic

def main():


    ckpt_path = pathlib.Path("poc/mujoco_legswing/booster-k1/checkpoints/9hwhuj2t/k1_legswing_rl_final").resolve()
    

    # load environment and network
    env = LegswingMJXEnv("poc/mujoco_legswing/booster-k1/assets/K1_sitting.xml")
    network = ActorCritic(action_dim=env.act_size, layer_size=256)
    
    # restore weights
    checkpointer = orbax.checkpoint.PyTreeCheckpointer()
    raw_restored = checkpointer.restore(str(ckpt_path))
    
    # load parameters
    params = raw_restored['params']
    print("Parameter geladen")

    # restore the static world description and initialize the simulation data
    cpu_model = env.cpu_model
    cpu_data = mujoco.MjData(cpu_model)
    
    # load sitting pose
    key_id = mujoco.mj_name2id(cpu_model, mujoco.mjtObj.mjOBJ_KEY, "sitting_pose")
    mujoco.mj_resetDataKeyframe(cpu_model, cpu_data, key_id)
    mujoco.mj_forward(cpu_model, cpu_data)

    # open the MuJoCo-Viewer
    with mujoco.viewer.launch_passive(cpu_model, cpu_data) as viewer:
        while viewer.is_running():
            step_start = time.time()

            # set Observationspace
            obs = numpy.array([
                cpu_data.qpos[4], cpu_data.qpos[5],
                cpu_data.qpos[env.qpos_lhp], cpu_data.qvel[env.id_lhp],
                cpu_data.qpos[env.qpos_rhp], cpu_data.qvel[env.id_rhp],
                cpu_data.qpos[env.qpos_lkp], cpu_data.qvel[env.id_lkp],
                cpu_data.qpos[env.qpos_rkp], cpu_data.qvel[env.id_rkp],
                cpu_data.sensordata[env.sensor_adr],
            ])

            # convert obs to jax_obs
            jax_obs = jax.numpy.array(obs)

            mean, std, value = network.apply({"params": params}, jax_obs)
            
            action = numpy.array(mean)
            action = numpy.clip(action, -1.0, 1.0) # safety-clip

            # connect the output-layer to the simulation model
            cpu_data.ctrl[env.id_lhp] = action[0]
            cpu_data.ctrl[env.id_rhp] = action[1]
            cpu_data.ctrl[env.id_lkp] = action[2]
            cpu_data.ctrl[env.id_rkp] = action[3]

            # 10 substeps per Step
            for _ in range(10):
                mujoco.mj_step(cpu_model, cpu_data)

            # check termination
            torso_tilt = (abs(cpu_data.qpos[4]) > 0.2) or (abs(cpu_data.qpos[5]) > 0.2)
            fell_off = cpu_data.qpos[2] < 0.5
            if torso_tilt or fell_off:
                for geom_id in range(2, cpu_model.ngeom):
                    cpu_model.geom_rgba[geom_id] = [1.0, 0.0, 0.0, 1.0] # paint the K1 red if terminated

            viewer.sync()

            # maintain real-time speed
            dt = cpu_model.opt.timestep * 10
            time_until_next_step = dt - (time.time() - step_start)
            if time_until_next_step > 0:
                time.sleep(time_until_next_step)


if __name__ == "__main__":
    main()