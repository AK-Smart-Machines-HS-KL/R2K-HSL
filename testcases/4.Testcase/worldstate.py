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
#
# originally made by Luis Burgard, added by Tim Simon

# === Testcase 4: Organisierte_Offensive ===
# = Controlled buildup of an attack =

# Blue team
# G1             ~ In front of the goal, facing right
# D2 (with ball) ~ Close to center circle, facing down right
# A3             ~ Across the center line, facing right
position_team: List[RobotPose] = [
    (-5.5, 0.0, 270.0),
    (-2.0, 0.0, 235.0),
    (1.0, -2.0, 270.0),
]

# Red team
# G1             ~ In front of the goal, facing left 
# D2             ~ Defensive wall with A3, facing left
# A3             ~ Defensive wall with D2, facing left
position_enemie: List[RobotPose] = [
    (5.5, 0.0, 90.0),
    (3.0, -1.0, 90.0),
    (3.0, 1.5, 90.0),
]
# Ball vector
# Heading towards blue A3, low speed, high belief
ball_vector: Ball_Vector_TUPLE = (-2.0, 0.0, 235.0, 2.5, 95)

# Ball possession: R2K
ball_possession: BallPossession_ENUM = 'R2K'

# Robot states: all active
state_robot: List[State_Robot_ENUM] = ['ACTIVE', 'ACTIVE', 'ACTIVE']

# Tactical evaluation (safe buildup, stable formation): +5
score: int = 5

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
