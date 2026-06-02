from dataclasses import dataclass
from typing import List, Tuple, Literal

# === Enums & Type Aliases ===
BallPossession_ENUM = Literal['R2K','ENEMY','NONE','UNKOWN']
State_Robot_ENUM = Literal['INIT','ACTIVE','PENALIZED','BROKEN','UNKNOWN']

# Pose in 2D incl. rotation (theta)
# theta counts counter clockwise: 0° up, 90° left, 180° down, 270° right
RobotPose = Tuple[int, int, float]

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
# The field size in the mid-divison approximated to be: -width: 6-9m; -height: 9-14m
# The testcase will use the smallest possible size, therefore: 6x9m, with 1 unit = 1 m

# === Testcase 8: Gelegenheit_zum_Weitschuss ===
# = Blue D2 attempts a long range shot from the penalty area =

# Blue team
# G1             ~ Further out of defaul goalie position, facing right
# D2 (with ball) ~ Right on the middle point, facing right
# A3             ~ Right wing attacker, facing right
position_team: List[RobotPose] = [
    (-4.0, 0.0, 270.0),
    (0.0, 0.0, 270.0),
    (3.3, -2.0, 270.0),
]

# Red team
# G1             ~ Defending the top corner of the goal, facing left
# D2             ~ Defending the right wing, facing left
# A3             ~ Defending the left wing, facing left
position_enemie: List[RobotPose] = [
    (6.0, 1.0, 90.0),
    (4.5, -1.3, 90.0),
    (4.5, 2.0, 90.0),
]

# Ball vector
# Heading towards the goal, high speed, high belief
ball_vector: Ball_Vector_TUPLE = (0.0, 0.0, 270, 5.5, 90)

# Ball possession: R2K
ball_possession: BallPossession_ENUM = 'R2K'

# Robot states: all active
state_robot: List[State_Robot_ENUM] = ['ACTIVE', 'ACTIVE', 'ACTIVE']

# Tactical evaluation: long-range shot, high potential due to goalie mispositioning: +9
score: int = 9

# Final WorldState instance
ws = WorldState(
    Ball_Vector=ball_vector,
    BallPossession=ball_possession,
    Position_Team=position_team,
    Position_Enemie=position_enemie,
    State_Robot=state_robot,
    Score=score,
)

if __name__ == '__main__':
    from pprint import pprint
    pprint(ws)