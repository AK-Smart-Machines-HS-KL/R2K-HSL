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

# === Testcase 9: Hohe_Abwehrkette ===
# = Executing a long pass to play in the open space behind the defense =

# Blue team
# G1             ~ In front of the goal, facing right
# D2 (with ball) ~ Close to center circle, facing down right
# A3             ~ Outside the center circle, right wing, facing right
position_team: List[RobotPose] = [
    (-6.0, 0.0, 270.0),
    (-1.0, 2.0, 240.0),
    (1.0, -2.0, 270.0)
]

# Red team
# G1             ~ In front of the goal, facing left
# D2             ~ Left wing defender, facing right
# A3 (with ball) ~ Right wind defender, facing left
position_enemie: List[RobotPose] = [
    (6.0, 0.0, 90.0),
    (2.5, 2.5, 90.0),
    (2.5, -2.5, 90.0)
]
# Ball vector
# Long pass for A3 behind the defense, high speed, high belief
ball_vector: Ball_Vector_TUPLE = (-1.0, 2.0, 240.0, 6.0, 90)

# Ball possession: R2K
ball_possession: BallPossession_ENUM = 'R2K'

# Robot states: all active
state_robot: List[State_Robot_ENUM] = ['ACTIVE', 'ACTIVE', 'ACTIVE']

# Tactical evaluation: strong offensive buildup with free space behind defense: +8
score: int = 8

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