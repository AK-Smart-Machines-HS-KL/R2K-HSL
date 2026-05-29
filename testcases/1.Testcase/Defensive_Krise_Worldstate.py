
from dataclasses import dataclass
from typing import List, Tuple, Literal

# === Enums & Type Aliases (as specified) ===
BallPossession_ENUM = Literal['R2K','ENEMIE','NONE','UNKOWN']
State_Robot_ENUM = Literal['INIT','ACTIVE','PENALIZED','BROKEN','UNKNOWN']

# Pose in 2D incl. rotation (theta) and velocity (cm/s)
# theta counts counter clockwise: 0° up, 90° left, 180° down, 270° right
RobotPose = Tuple[int, int, float, float]

# Ball vector (x,y,theta,velocity[m/s],prob[%])
Ball_Vector_TUPLE = Tuple[int, int, int, float, int]

@dataclass(frozen=True)
class WorldState:
    Ball_Vector: Ball_Vector_TUPLE
    BallPossession: BallPossession_ENUM
    Position_Team: List[RobotPose]
    Position_Enemie: List[RobotPose]
    State_Robot: List[State_Robot_ENUM]
    Score: int

# === Field normalization note ===
# Coordinates are given in percent of the pitch image (0..100) derived from the provided PNG (1177x785).
# This matches the "for now assume standard field" requirement and keeps it simulator-agnostic.

# === World state extracted from the PNG (approximate, image-based) ===
# Blue team (own robots)
# G (goalie)     ~ (11,48), facing right (270°), stationary
# D2 (defender)  ~ (33,25), facing down-left (~225°), stationary
# A3 (ally)      ~ (53,75), facing right (270°), stationary
position_team: List[RobotPose] = [
    (11, 48, 270.0, 0.0),
    (33, 25, 225.0, 0.0),
    (53, 75, 270.0, 0.0),
]

# Red team (enemies)
# R5 (top-left)  ~ (39,16), facing right (270°)
# R2 (mid-left)  ~ (42,50), facing left  ( 90°)
# R? (with ball) ~ (22,45), facing left  ( 90°)
position_enemie: List[RobotPose] = [
    (39, 16, 270.0, 0.0),
    (42, 50,  90.0, 0.0),
    (22, 45,  90.0, 0.0),
]

# Ball vector (estimated from the white ball at the red attacker on ~22,45)
# Heading left toward goal, moderate speed, high belief
ball_vector: Ball_Vector_TUPLE = (22, 45, 90, 3.0, 80)

# Ball possession is with the enemy
ball_possession: BallPossession_ENUM = 'ENEMIE'

# Robot states (own team): all active
state_robot: List[State_Robot_ENUM] = ['ACTIVE','ACTIVE','ACTIVE']

# Heuristic tactical score (danger for us near our box): -4
score: int = -4

# Final world state instance
ws = WorldState(
    Ball_Vector=ball_vector,
    BallPossession=ball_possession,
    Position_Team=position_team,
    Position_Enemie=position_enemie,
    State_Robot=state_robot,
    Score=score,
)

if __name__ == '__main__':
    # Simple sanity print
    from pprint import pprint
    pprint(ws)
