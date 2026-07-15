import jax
import jax.numpy
import mujoco
from mujoco import mjx
from flax import struct
from brax.envs import PipelineEnv
from brax.envs import State

@struct.dataclass
class EnvState(State):
    uprightness: float = 0.0
    terminated: float = 0.0
    truncated: float = 0.0


class LegswingMJXEnv(PipelineEnv):

    def __init__(self, model_path: str):
        
        # load the static world description
        self.cpu_model = mujoco.MjModel.from_xml_path(model_path)

        # initialize brax
        super().__init__(
            sys=mjx.put_model(self.cpu_model),
            backend='mjx',
            n_frames=10  # 10 substeps
        )

        self.offset = 1.25           # Center position of the swing
        self.amplitude = 0.5         # Range of swing motion
        self.frequency = 0.5         # Swing speed in Hz
        self.min_uprightness = 0.95  # Limit for torso tilt (1.0 = perfectly upright, -1.0 = upside down)

        # set IDs by name
        # torso ID
        self.body_id = mujoco.mj_name2id(self.cpu_model, mujoco.mjtObj.mjOBJ_BODY, "Trunk")
        
        # Hip and Knee IDs for controlling
        self.id_lhp = self._get_act_id("Left_Hip_Pitch")
        self.id_rhp = self._get_act_id("Right_Hip_Pitch")
        self.id_lkp = self._get_act_id("Left_Knee_Pitch")
        self.id_rkp = self._get_act_id("Right_Knee_Pitch")

        # Hip and Knee IDs for angle observation
        self.qpos_lhp = self._get_qpos_id("Left_Hip_Pitch")
        self.qpos_rhp = self._get_qpos_id("Right_Hip_Pitch")
        self.qpos_lkp = self._get_qpos_id("Left_Knee_Pitch")
        self.qpos_rkp = self._get_qpos_id("Right_Knee_Pitch")

        # Hip and Knee IDs for velocity observation
        self.vel_lhp = self._get_qvel_id("Left_Hip_Pitch")
        self.vel_rhp = self._get_qvel_id("Right_Hip_Pitch")
        self.vel_lkp = self._get_qvel_id("Left_Knee_Pitch")
        self.vel_rkp = self._get_qvel_id("Right_Knee_Pitch")

        # address of angular-velocity sensor
        id_sensor = mujoco.mj_name2id(self.cpu_model, mujoco.mjtObj.mjOBJ_SENSOR, "angular-velocity")
        self.sensor_adr = int(self.cpu_model.sensor_adr[id_sensor])

        # ID of sitting-pose keyframe
        id_keyframe = mujoco.mj_name2id(self.cpu_model, mujoco.mjtObj.mjOBJ_KEY, "sitting_pose")
        self.keyframe_qpos = jax.numpy.array(self.cpu_model.key_qpos[id_keyframe])


    # get controlling ID of a joint by name
    def _get_act_id(self, name: str) -> int:
        return mujoco.mj_name2id(self.cpu_model, mujoco.mjtObj.mjOBJ_ACTUATOR, name)

    # get observing ID of joint angle by name
    def _get_qpos_id(self, name: str) -> int:
        jnt_id = mujoco.mj_name2id(self.cpu_model, mujoco.mjtObj.mjOBJ_JOINT, name)
        return int(self.cpu_model.jnt_qposadr[jnt_id])

    # get observing ID of joint velocity by name
    def _get_qvel_id(self, name: str) -> int:
            jnt_id = mujoco.mj_name2id(self.cpu_model, mujoco.mjtObj.mjOBJ_JOINT, name)
            return int(self.cpu_model.jnt_dofadr[jnt_id])
    
    
    def reset(self, rng: jax.Array) -> EnvState:
        rng, subkey = jax.random.split(rng)

        # insert joint-only-noise for more robust results
        # noise in coords or rotation could cause clipping with the table
        full_noise = jax.random.uniform(subkey, (self.cpu_model.nq,), minval=-0.01, maxval=0.01)
        mask = jax.numpy.concatenate([jax.numpy.zeros(7), jax.numpy.ones(self.cpu_model.nq - 7)])
        safe_noise = full_noise * mask

        # reset simulation state
        init_data = mjx.make_data(self.sys)
        mjx_data = init_data.replace(qpos=self.keyframe_qpos + safe_noise)
        mjx_data = mjx.forward(self.sys, mjx_data)

        uprightness = mjx_data.xmat[self.body_id].reshape(3, 3)[2, 2]
        
        obs = self._get_obs(mjx_data, uprightness)

        return EnvState(
            pipeline_state=mjx_data,
            obs=obs,
            reward=jax.numpy.zeros(()),
            done=jax.numpy.zeros(()),
            metrics={},
            info={},
            uprightness=uprightness,
            terminated=jax.numpy.zeros(()),
            truncated=jax.numpy.zeros(())
        )
    

    def step(self, state: EnvState, action: jax.Array) -> EnvState:

        # map actions into ctrl-array
        ctrl = state.pipeline_state.ctrl
        ctrl = ctrl.at[self.id_lhp].set(action[0])
        ctrl = ctrl.at[self.id_rhp].set(action[1])
        ctrl = ctrl.at[self.id_lkp].set(action[2])
        ctrl = ctrl.at[self.id_rkp].set(action[3])

        # brax step already includes substeps from initialization
        stepped = self.pipeline_step(state.pipeline_state, ctrl)

        uprightness = stepped.xmat[self.body_id].reshape(3, 3)[2, 2]

        # check if K1 has tipped over, fallen off the table or simulation time is up
        torso_tilted = uprightness < self.min_uprightness
        fell_off = stepped.qpos[2] < 0.5
        terminated = jax.numpy.where(torso_tilted | fell_off, 1.0, 0.0)
        truncated = jax.numpy.where(stepped.time > 10.0, 1.0, 0.0)
        done = jax.numpy.maximum(terminated, truncated)

        obs = self._get_obs(stepped, uprightness)
        reward = self._calculate_reward(stepped, action, terminated)

        return state.replace(
            pipeline_state=stepped,
            obs=obs,
            reward=reward,
            done=done,
            metrics={"reward": reward},
            uprightness=uprightness,
            terminated=terminated,
            truncated=truncated
        )
    

    def _get_obs(self, data: mjx.Data, uprightness: jax.Array) -> jax.Array:
        return jax.numpy.concatenate([
            # 4 joint angles and 4 joint velocities
            data.qpos[self.qpos_lhp : self.qpos_lhp + 1], data.qvel[self.vel_lhp : self.vel_lhp + 1],
            data.qpos[self.qpos_rhp : self.qpos_rhp + 1], data.qvel[self.vel_rhp : self.vel_rhp + 1],
            data.qpos[self.qpos_lkp : self.qpos_lkp + 1], data.qvel[self.vel_lkp : self.vel_lkp + 1],
            data.qpos[self.qpos_rkp : self.qpos_rkp + 1], data.qvel[self.vel_rkp : self.vel_rkp + 1],

            # torso tilt (velocity and angle from vertical axis)
            data.sensordata[self.sensor_adr : self.sensor_adr + 1], jax.numpy.atleast_1d(uprightness),

            # sine and cosine curve for leg controlling
            jax.numpy.array([jax.numpy.sin(2 * jax.numpy.pi * self.frequency * data.time)]),
            jax.numpy.array([jax.numpy.cos(2 * jax.numpy.pi * self.frequency * data.time)])
        ])
    

    # Reward function
    def _calculate_reward(self, data: mjx.Data, action: jax.Array, terminated: jax.Array, uprightness: jax.Array) -> jax.Array:
        stability = jax.numpy.exp(-20.0 * ((1.0 - uprightness)**2))  # higher reward for upright torso

        target_angle = self.offset + self.amplitude * jax.numpy.sin(2 * jax.numpy.pi * self.frequency * data.time)  # Sine Curve

        # delta between target angle and actual leg position
        error_left = -target_angle - data.qpos[self.qpos_lkp]
        error_right = target_angle - data.qpos[self.qpos_rkp]

        raw_swing_reward = jax.numpy.exp(-5.0 * error_left**2) + jax.numpy.exp(-5.0 * error_right**2)  # Bell Curve

        swing_reward = stability * raw_swing_reward
        termination_penalty = jax.numpy.where(terminated > 0.0, -1.0, 0.0)
        energy_penalty = -0.01 * jax.numpy.sum(jax.numpy.square(action))

        total_reward = swing_reward + termination_penalty + energy_penalty

        return total_reward
