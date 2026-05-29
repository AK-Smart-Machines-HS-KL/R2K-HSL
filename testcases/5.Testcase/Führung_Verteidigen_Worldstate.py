
from dataclasses import dataclass
from typing import List, Tuple, Literal

# === Enums & Type Aliases ===
BallPossession_ENUM = Literal['R2K','ENEMIE','NONE','UNKOWN']
State_Robot_ENUM = Literal['INIT','ACTIVE','PENALIZED','BROKEN','UNKNOWN']

RobotPose = Tuple[int, int, float, float]  # (x, y, theta, velocity)
Ball_Vector_TUPLE = Tuple[int, int, int, float, int]  # (x, y, theta, velocity[m/s], prob[%])

@dataclass(frozen=True)
class WorldState:
    Ball_Vector: Ball_Vector_TUPLE
    BallPossession: BallPossession_ENUM
    Position_Team: List[RobotPose]
    Position_Enemie: List[RobotPose]
    State_Robot: List[State_Robot_ENUM]
    Score: int

# === Scene 5 Analysis ===
# Context: Blue team ("R2K") is in a compact defensive setup ("Igel") near own box.
# Opponent (R1) starts a run toward the blue defense line.

# Blue team positions (defensive block)
# G1: (~15,55), facing right (270°), stationary
# D2: (~25,45), facing right (270°), stationary
# A3: (~30,65), facing up-right (315°), stationary
position_team: List[RobotPose] = [
    (15, 55, 270.0, 0.0),
    (25, 45, 270.0, 0.0),
    (30, 65, 315.0, 0.0),
]

# Red team positions (offensive movement)
# R1: (~55,55), with ball, running forward (toward goal) (270°), ~0.6 m/s
# R2: (~65,35), supportive, stationary
# R3: (~65,70), supportive, stationary
position_enemie: List[RobotPose] = [
    (55, 55, 270.0, 60.0),
    (65, 35, 270.0, 0.0),
    (65, 70, 270.0, 0.0),
]

# Ball vector: at R1 (~55,55), heading toward goal (270°), medium-high speed, high belief
ball_vector: Ball_Vector_TUPLE = (55, 55, 270, 4.5, 90)

# Ball possession: ENEMIE (R1 at ball)
ball_possession: BallPossession_ENUM = 'ENEMIE'

# Robot states: all active
state_robot: List[State_Robot_ENUM] = ['ACTIVE', 'ACTIVE', 'ACTIVE']

# Tactical evaluation: strong defensive setup, low threat but high readiness: +4
score: int = 4

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
