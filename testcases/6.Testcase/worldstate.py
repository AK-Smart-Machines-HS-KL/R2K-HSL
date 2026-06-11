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
# The testcase will use the smallest possible size, therefore: 6x9m, with 1 unit = 1 
#
# originally made by Luis Burgard, added by Tim Simon

# === Testcase 6: Fluegelspiel_Ueberladung ===
# = Offensive chance by blue team by passing the ball back =

# Blue team
# G1             ~ Outside the penalty area, facing left
# D2             ~ Close to the penalty area, facing left
# A3 (with ball) ~ Right wing, facing top left
position_team: List[RobotPose] = [
    (-3.0, 0.0, 270.0),
    (3.0, -1.0, 270.0),
    (5.0, -3.0, 60.0),
]

# Red team
# G1             ~ In front of the goal, facing left
# D2             ~ Right corner of penalty area, facing down right
# A3 (with ball) ~ Inside the penalty area, facing left
position_enemie: List[RobotPose] = [
    (6.0, 0.0, 90.0),
    (4.5, -2.5, 230.0),
    (4.5, 1.5, 90.0),
]

# Ball vector
# Heading left toward blue A3, moderate speed, high belief
ball_vector: Ball_Vector_TUPLE = (5.0, -3.0, 60.0, 4.0, 90)

# Ball possession: R2K
ball_possession: BallPossession_ENUM = 'R2K'

# Robot states: all active
state_robot: List[State_Robot_ENUM] = ['ACTIVE', 'ACTIVE', 'ACTIVE']

# Tactical evaluation: strong offensive setup, open shot opportunity for D2 -> high score: +8
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
