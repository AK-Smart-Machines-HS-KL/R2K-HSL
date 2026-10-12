# GoToBallAndKickCmd.msg
# High-level kick command from the host bridge to the on-robot
# GoToBallAndKick node (utils/skills/goToBallAndKick.py). The node
# closes the loop locally on the K1 using utils/vision ball data
# (/booster_soccer/ball, vision_interface/Ball) and publishes the
# high-frequency brain/Kick stream to the robot-local /kick_ball.
#
# power = 0.0  -> node computes power from distance + is_goalshot
# abort = true -> stop kick loop + RPC 2038 {"start": false}
float64 target_x
float64 target_y
float64 power
bool is_goalshot
bool abort