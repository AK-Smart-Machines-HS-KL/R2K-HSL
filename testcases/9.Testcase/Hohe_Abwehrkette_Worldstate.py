
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

# === Scene 9 Analysis ===
# Context: Blue team (R2K) executes a long pass from D2 to A3.
# The opponent has a high defensive line (R2, R3), leaving free space behind them.

# Blue team positions
# G1: (~10,55), stationary, facing right (270°)
# D2: (~45,50), passing forward-right (315°), stationary
# A3: (~65,65), running into free space (270°), velocity ~0.6 m/s (60 cm/s)
position_team: List[RobotPose] = [
    (10, 55, 270.0, 0.0),
    (45, 50, 315.0, 0.0),
    (65, 65, 270.0, 60.0),
]

# Red team positions
# R1: (~85,55), acting as central defender
# R2: (~70,70), positioned high, leaving space behind
# R3: (~70,40), also high, forming a high defensive line
position_enemie: List[RobotPose] = [
    (85, 55, 270.0, 0.0),
    (70, 70, 270.0, 0.0),
    (70, 40, 270.0, 0.0),
]

# Ball vector: at D2 (~45,50), long pass to A3 (~65,65), heading ≈ 330°, velocity ~6.0 m/s, high confidence
ball_vector: Ball_Vector_TUPLE = (45, 50, 330, 6.0, 90)

# Ball possession: R2K (own team controls ball)
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
