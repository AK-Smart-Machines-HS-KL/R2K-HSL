from dataclasses import dataclass
from typing import List, Tuple, Literal

# === Enums & Type Aliases ===
BallPossession_ENUM = Literal['R2K','ENEMY','NONE','UNKNOWN']
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

# === Testcase 2: Schneller_Gegenangriff ===
# = Blue Defender prepares counter attack from own half =

# Blue Team
# G1:             ~ Infront of the goal, facing left
# D2: (with ball) ~ Inside penalty area, facing down right
# A3:             ~ On half way line, facing right

position_team: List[RobotPose] = [
    (-6.0, 0.0, 270.0),
    (-4.5, 1.5, 250.0),
    (0.0, -2.0, 270.0),
]

# Red team
# G1:              ~ Far out on right center circle, facing left
# D2:              ~ Close to left penalty area, facing left
# A3:              ~ On top of left penalty area lines, facing left
position_enemie: List[RobotPose] = [
    (1.0, 0.0, 90.0),
    (-3.0, -1.5, 90.0),
    (-4.0, 1.0, 90.0),
]

# Ball vector
# Heading right toward left wing, high speed, high belief
ball_vector: Ball_Vector_TUPLE = (-4.5, 1.5, 250, 5.0, 90)

# Ball possession: R2K (own team)
ball_possession: BallPossession_ENUM = 'R2K'

# Robot states: all active
state_robot: List[State_Robot_ENUM] = ['ACTIVE', 'ACTIVE', 'ACTIVE']

# Tactical evaluation (strong counter opportunity): +6
score: int = 6

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
    from pprint import pprint
    pprint(ws)
