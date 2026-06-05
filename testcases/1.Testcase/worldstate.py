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

# === Testcase 1: Defensive_Krise ===
# = Attacker with ball possesion infront of the goal with no other defender close by but the goalie himself =

# Blue team
# G1 (goalie)    ~ Infront of the goal, facing left
# D2 (defender)  ~ Outside of penalty area, facing top left
# A3 (attacker)  ~ Close to half way line, facing right
position_team: List[RobotPose] = [
    (-6.0, 0.0, 270.0),
    (-3.0, 2.0, 45.0),
    (0.5, -2.0, 270.0),
]

# Red team
# G1             ~ Far out, on left center circle, facing left 
# D2             ~ Right wing attacker, facing right
# A3 (with ball) ~ Inside penalty area, facing left
position_enemie: List[RobotPose] = [
    (-1.5, 0.0, 90.0),
    (-2.5, 3.5, 270.0),
    (-4.5, 0.5, 90.0),
]

# Ball vector
# Heading left toward goal, moderate speed, high belief
ball_vector: Ball_Vector_TUPLE = (-4.5, 0.5, 90, 3.0, 80)

# Ball possession is with the enemy
ball_possession: BallPossession_ENUM = 'ENEMY'

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
