import pathlib
import time
import mujoco
import mujoco.viewer
import numpy

def main():

    # get controlling ID of a joint by name
    def _get_act_id(name: str) -> int:
        return mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, name)
    
    # get observing ID of joint angle by name
    def _get_qpos_id(name: str) -> int:
        jnt_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)
        return int(model.jnt_qposadr[jnt_id])
    

    model_path = pathlib.Path("poc/mujoco_legswing/booster-k1/assets/K1_sitting.xml")

    # load the static world description and initialize the simulation data
    model = mujoco.MjModel.from_xml_path(str(model_path))
    data = mujoco.MjData(model)

    # load sitting pose
    key_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_KEY, "sitting_pose")
    if key_id != -1:
        mujoco.mj_resetDataKeyframe(model, data, key_id)
    mujoco.mj_forward(model, data)

    # Hip and Knee IDs for controlling
    id_lhp = _get_act_id("Left_Hip_Pitch")
    id_rhp = _get_act_id("Right_Hip_Pitch")
    id_lkp = _get_act_id("Left_Knee_Pitch")
    id_rkp = _get_act_id("Right_Knee_Pitch")

    # Hip and Knee IDs for angle observation
    qpos_lhp = _get_qpos_id("Left_Hip_Pitch")
    qpos_rhp = _get_qpos_id("Right_Hip_Pitch")
    qpos_lkp = _get_qpos_id("Left_Knee_Pitch")
    qpos_rkp = _get_qpos_id("Right_Knee_Pitch")

    offset = 1.32  # Center position of the swing
    amplitude = 0.4  # Range of swing motion
    frequency = 0.8  # Swing speed in Hz
    
    # launch the MuJoCo-Viewer
    with mujoco.viewer.launch_passive(model, data) as viewer:
        real_time_start = time.perf_counter()
        while viewer.is_running():
            sim_time_target = time.perf_counter() - real_time_start

            while data.time < sim_time_target:
                sine_curve = amplitude * numpy.sin(2 * numpy.pi * frequency * data.time)

                # stabilize the hips for upright sitting
                data.ctrl[id_lhp] = (-offset - data.qpos[qpos_lhp]) * 30
                data.ctrl[id_rhp] = (-offset - data.qpos[qpos_rhp]) * 30

                # legs swing, following a sine curve
                data.ctrl[id_lkp] = ((offset + sine_curve) - data.qpos[qpos_lkp]) * 40
                data.ctrl[id_rkp] = ((offset - sine_curve) - data.qpos[qpos_rkp]) * 40

                mujoco.mj_step(model, data)
            
            viewer.sync()


if __name__ == "__main__":
    main()
