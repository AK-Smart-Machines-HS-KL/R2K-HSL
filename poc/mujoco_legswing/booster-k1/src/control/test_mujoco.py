import mujoco
import mujoco.viewer
import time

paused = True

def main():

    # Space pauses/continues the viewer
    def key_callback(keycode):
        if chr(keycode) == ' ':
            global paused
            paused = not paused

    # load the static world description and initialize the simulation data
    model = mujoco.MjModel.from_xml_path("poc/mujoco_legswing/booster-k1/assets/K1_22dof.xml")
    data = mujoco.MjData(model)

    # open the MuJoCo-Viewer
    with mujoco.viewer.launch_passive(model, data, key_callback=key_callback) as viewer:
        sim_timestep = model.opt.timestep
        while viewer.is_running():
            start_time = time.perf_counter()

            # Pause-logic
            if paused:
                time.sleep(0.01)
            else:
                # calculate the physics-step
                mujoco.mj_step(model, data)
                
                # real-time sync
                elapsed = time.perf_counter() - start_time
                sleep_time = sim_timestep - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

            # sync the viewer with the simulation state
            viewer.sync()


if __name__ == "__main__":
    main()
