import gymnasium
from gymnasium import spaces
import mujoco
import numpy

class LegswingEnv(gymnasium.Env):

    def __init__(self, model_path: str, seed=None):
        super().__init__()

        self.model_path = model_path
        self.init_seed = seed

        self.offset = 1.32           # Center position of the swing
        self.max_amplitude = 0.5     # Targeted range of swing motion
        self.amplitude = 0.0         # Range of swing motion
        self.frequency = 0.8         # Swing speed in Hz
        self.reset_counter = 0
        self.progress = 0.0

        # load the static world description and initialize the simulation data
        self.model = mujoco.MjModel.from_xml_path(model_path)
        self.data = mujoco.MjData(self.model)

        # set observationspace (Input Layer) and actionspace (Output Layer)
        self.observation_space = spaces.Box(low=-numpy.inf, high=numpy.inf, shape=(12,), dtype=numpy.float32)
        self.action_space = spaces.Box(low=-1, high=1, shape=(5,), dtype=numpy.float32)
        self.last_action = numpy.zeros(self.action_space.shape)

        # set IDs by name
        # torso ID
        self.body_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, "Trunk")

        # Hip and Knee IDs for controlling
        self.id_hp  = self._get_act_id("Head_pitch")
        self.id_lhp = self._get_act_id("Left_Hip_Pitch")
        self.id_rhp = self._get_act_id("Right_Hip_Pitch")
        self.id_lkp = self._get_act_id("Left_Knee_Pitch")
        self.id_rkp = self._get_act_id("Right_Knee_Pitch")

        # Hip and Knee IDs for angle observation
        self.qpos_hp  = self._get_qpos_id("Head_pitch")
        self.qpos_lhp = self._get_qpos_id("Left_Hip_Pitch")
        self.qpos_rhp = self._get_qpos_id("Right_Hip_Pitch")
        self.qpos_lkp = self._get_qpos_id("Left_Knee_Pitch")
        self.qpos_rkp = self._get_qpos_id("Right_Knee_Pitch")

        # Hip and Knee IDs for velocity observation
        self.qvel_hp  = self._get_qvel_id("Head_pitch")
        self.qvel_lhp = self._get_qvel_id("Left_Hip_Pitch")
        self.qvel_rhp = self._get_qvel_id("Right_Hip_Pitch")
        self.qvel_lkp = self._get_qvel_id("Left_Knee_Pitch")
        self.qvel_rkp = self._get_qvel_id("Right_Knee_Pitch")

        # ID of sitting-pose keyframe
        self.id_sitting_pose = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_KEY, "sitting_pose")


    # get controlling ID of a joint by name
    def _get_act_id(self, name: str) -> int:
        return mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_ACTUATOR, name)
    
    # get observing ID of joint angle by name
    def _get_qpos_id(self, name: str) -> int:
        jnt_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, name)
        return int(self.model.jnt_qposadr[jnt_id])
    
    # get observing ID of joint velocity by name
    def _get_qvel_id(self, name: str) -> int:
            jnt_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, name)
            return int(self.model.jnt_dofadr[jnt_id])
    

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)

        self.reset_counter += 1
        self.progress = min(self.reset_counter / 500, 1.0)
        self.amplitude = self.progress * self.max_amplitude
        print(f"Progress: {self.progress}")
        print(f"Amplitude: {self.amplitude}")

        if seed is not None:
            numpy.random.seed(seed)

        # reset simulation state
        mujoco.mj_resetData(self.model, self.data)
        self.uprightness = 1.0
        self.last_action = numpy.zeros(self.action_space.shape)

        # load sitting pose
        mujoco.mj_resetDataKeyframe(self.model, self.data, self.id_sitting_pose)
        mujoco.mj_forward(self.model, self.data)
        
        return self._get_obs(), {}
    

    def step(self, action):

        # set the joints to the calculated positions (scaled with max joint force in Nm)
        self.data.ctrl[self.id_hp] = action[0] * 6
        self.data.ctrl[self.id_lhp] = action[1] * 30
        self.data.ctrl[self.id_rhp] = action[2] * 30
        self.data.ctrl[self.id_lkp] = action[3] * 40
        self.data.ctrl[self.id_rkp] = action[4] * 40

        # substepping improves physics and reduces calculation overhead
        for _ in range(10):
            mujoco.mj_step(self.model, self.data)
        mujoco.mj_forward(self.model, self.data)

        self.uprightness = self.data.xmat[self.body_id].reshape(3, 3)[2, 2]

        # check if K1 has tipped over, fallen off the table or simulation time is up
        torso_tilted = self.uprightness < 0.95
        fell_off_table = self.data.qpos[2] < 0.5
        terminated = torso_tilted or fell_off_table
        truncated = self.data.time > 20.0

        # calculate reward with current simulation state
        obs = self._get_obs()
        reward = self._calculate_reward(action, terminated)

        self.last_action = action.copy()

        return obs, reward, terminated, truncated, {}
    

    def _get_obs(self):
        return numpy.array([
            # 5 joint angles and 5 joint velocities
            self.data.qpos[self.qpos_hp], self.data.qvel[self.qvel_hp],
            self.data.qpos[self.qpos_lhp], self.data.qvel[self.qvel_lhp],
            self.data.qpos[self.qpos_rhp], self.data.qvel[self.qvel_rhp],
            self.data.qpos[self.qpos_lkp], self.data.qvel[self.qvel_lkp],
            self.data.qpos[self.qpos_rkp], self.data.qvel[self.qvel_rkp],

            # sine and cosine curve for leg controlling
            self.progress * numpy.sin(2 * numpy.pi * self.frequency * self.data.time),
            self.progress * numpy.cos(2 * numpy.pi * self.frequency * self.data.time)
            #0, 0  Curriculum Learning Phase 1 (remove sine and cosine lines above)
        ], dtype=numpy.float32)
    

    def _calculate_reward(self, action, terminated):

        # keep head up
        head_reward = numpy.exp(-100.0 * self.data.qpos[self.qpos_hp]**2)

        # sit upright
        target_angle_hips = -(self.offset)
        actual_angle_hips = numpy.array([self.data.qpos[self.qpos_lhp], self.data.qpos[self.qpos_rhp]])
        error_hips = numpy.sum((actual_angle_hips - target_angle_hips)**2)
        hip_reward = numpy.exp(-100.0 * error_hips)

        # swing legs
        sine_curve = self.amplitude * numpy.sin(2 * numpy.pi * self.frequency * self.data.time)
        #sine_curve = 0.0  Curriculum Learning Phase 1
        target_angle_knees = numpy.array([self.offset + sine_curve, self.offset - sine_curve])
        actual_angle_knees = numpy.array([self.data.qpos[self.qpos_lkp], self.data.qpos[self.qpos_rkp]])
        error_knees = numpy.sum((actual_angle_knees - target_angle_knees)**2)
        knee_reward = numpy.exp(-50.0 * error_knees)

        # penalties
        asymmetry_penalty = -(numpy.abs(action[1] - action[2])**2)
        action_rate_penalty = -(numpy.sum(numpy.square(action - self.last_action)))
        energy_penalty = -(numpy.sum(numpy.square(action)))
        termination_penalty = -100.0 if terminated else 0.0

        total_reward = (1.0 * head_reward) \
                     + (1.0 * hip_reward) \
                     + (1.0 * knee_reward) \
                     + (0.5 * action_rate_penalty) \
                     + (0.1 * asymmetry_penalty) \
                     + (0.01 * energy_penalty) \
                     + termination_penalty

        return total_reward
