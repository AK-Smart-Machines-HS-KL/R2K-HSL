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

# === Testcase 11:Eindaemmen_und_Verzoegern ===
# = Attackers try to defende the space around the attackers and cut off their attack =

# Blue team
# G1             ~ In front of goal, facing right
# D2             ~ Pressing attacker down right, facing down right 
# A3             ~ Guarding inside center circle, facing down right
position_team: List[RobotPose] = [
    (-6.0, 0.0, 270.0),
    (-3.5, -2.5, 250.0),
    (-0.5, 0.0, 225.0),
]

# Red team
# G1             ~ Far out, close to center line, facing left
# D2             ~ Right wing defender, facing left
# A3 (with ball) ~ Left wing attacker, facing left
position_enemie: List[RobotPose] = [
    (1.0, -2.0, 90.0),
    (2.0, 2.5, 90.0),
    (-2.0, -3.0, 90.0),
]

# Ball vector
# Heading left toward goal, low speed, high belief
ball_vector: Ball_Vector_TUPLE = (-2.0, -3.0, 90.0, 2.0, 85)

# Ball possession is with the enemy
ball_possession: BallPossession_ENUM = 'ENEMY'

# Robot states (own team): all active
state_robot: List[State_Robot_ENUM] = ['ACTIVE', 'ACTIVE', 'ACTIVE']

# Heuristic tactical score
score: int = 2

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