
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

# === Scene 7 Analysis ===
# Context: Blue team (R2K) in transition play; A3 dribbles through a defensive gap between R2 and R3.
# Red team’s defensive shape is too open.

# Blue team positions
# G1: (~15,55), stationary, facing right (270°)
# D2: (~55,35), positioned higher, facing up-right (315°), stationary
# A3: (~60,50), dribbling forward through center, facing right (270°), moving ~0.6 m/s
position_team: List[RobotPose] = [
    (15, 55, 270.0, 0.0),
    (55, 35, 315.0, 0.0),
    (60, 50, 270.0, 60.0),
]

# Red team positions
# R1: (~75,50), central defender
# R2: (~70,70), wide right, far from R3
# R3: (~70,30), wide left
position_enemie: List[RobotPose] = [
    (75, 50, 90.0, 0.0),
    (70, 70, 90.0, 0.0),
    (70, 30, 90.0, 0.0),
]

# Ball vector: at A3 (~60,50), dribbling forward (toward ~75,50), heading ≈ 270°, velocity ~3.5 m/s
ball_vector: Ball_Vector_TUPLE = (60, 50, 270, 3.5, 90)

# Ball possession: R2K (own team controls ball)
ball_possession: BallPossession_ENUM = 'R2K'

# Robot states: all active
state_robot: List[State_Robot_ENUM] = ['ACTIVE', 'ACTIVE', 'ACTIVE']

# Tactical evaluation: A3 advancing through open defensive line, strong offensive situation: +7
score: int = 7

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
