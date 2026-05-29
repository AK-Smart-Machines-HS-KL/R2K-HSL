
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

# === Scene 4 Analysis ===
# Context: Blue team (R2K) in controlled buildup, safe pass D2 -> A3.
# Opponent team (R1, R2, R3) forms defensive line deeper.

# Blue team positions
# G1: (~10,55), stationary, facing right (270°)
# D2: (~40,50), with ball, facing diagonal down-right (300°), stationary (0 m/s)
# A3: (~55,65), receiving pass, facing down-left (120°), velocity ~0.3 m/s (30 cm/s)
position_team: List[RobotPose] = [
    (10, 55, 270.0, 0.0),
    (40, 50, 300.0, 0.0),
    (55, 65, 120.0, 30.0),
]

# Red team positions
# R1: (~80,60), central defensive position
# R2: (~75,50), right defensive
# R3: (~75,40), left defensive
position_enemie: List[RobotPose] = [
    (80, 60, 90.0, 0.0),
    (75, 50, 90.0, 0.0),
    (75, 40, 90.0, 0.0),
]

# Ball vector: at D2 (~40,50) passing toward A3 (~55,65), direction ≈ 320°, low velocity
ball_vector: Ball_Vector_TUPLE = (40, 50, 320, 2.5, 95)

# Ball possession: R2K (own team controls play)
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
