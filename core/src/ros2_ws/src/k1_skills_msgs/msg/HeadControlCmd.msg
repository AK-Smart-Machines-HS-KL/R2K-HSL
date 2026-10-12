# HeadControlCmd.msg
# High-level head control command. Phase 1: sent locally by the
# GoToBallAndKick node. Future: may also be relayed from the host bridge.
#
# Coordinate frame for LOOK_AT_POINT: robot-relative (x=forward, y=left).
# TODO: field-frame coordinates once a world model node exists.

uint8 MODE_ABORT          = 0
uint8 MODE_LOOK_AT_BALL   = 1
uint8 MODE_LOOK_AT_POINT  = 2
uint8 MODE_LOOK_AT_GOAL   = 3   # TODO — not implemented yet (needs field localization)
uint8 MODE_LOOK_AT_CORNER = 4   # TODO — not implemented yet
uint8 MODE_RAW_ANGLE      = 5

uint8 mode

# MODE_LOOK_AT_POINT: robot-relative target (meters)
float64 point_x
float64 point_y

# MODE_LOOK_AT_GOAL (TODO): 0=own, 1=opponent
uint8 GOAL_OWN       = 0
uint8 GOAL_OPPONENT  = 1
uint8 goal_id

# MODE_LOOK_AT_CORNER (TODO): 0=own_left, 1=own_right, 2=opp_left, 3=opp_right
uint8 CORNER_OWN_LEFT    = 0
uint8 CORNER_OWN_RIGHT   = 1
uint8 CORNER_OPP_LEFT    = 2
uint8 CORNER_OPP_RIGHT   = 3
uint8 corner_id

# MODE_RAW_ANGLE: absolute head angles (radians, model frame: +yaw=left, +pitch=up)
float64 pitch_rad
float64 yaw_rad

bool abort