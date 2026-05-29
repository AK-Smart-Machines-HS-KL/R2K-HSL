
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

# === Scene 8 Analysis ===
# Context: D2 attempts a long-range shot ("Weitschuss D2") from midfield.
# Red goalie (R1) is positioned incorrectly; potential goal threat from distance.

# Blue team positions
# G1: (~10,55), stationary, facing right (270°)
# D2: (~50,50), taking the shot, facing right (270°), velocity ~0.4 m/s (approaching ball)
# A3: (~60,70), supporting, facing right (270°), stationary
position_team: List[RobotPose] = [
    (10, 55, 270.0, 0.0),
    (50, 50, 270.0, 40.0),
    (60, 70, 270.0, 0.0),
]

# Red team positions
# R1: (~90,50), positioned too far left, acting as goalie
# R2: (~75,60), midfield cover
# R3: (~85,35), defensive left
position_enemie: List[RobotPose] = [
    (90, 50, 270.0, 0.0),
    (75, 60, 270.0, 0.0),
    (85, 35, 270.0, 0.0),
]

# Ball vector: at D2 (~50,50), directed toward goal (~90,50), heading 270°, velocity ~5.5 m/s
ball_vector: Ball_Vector_TUPLE = (50, 50, 270, 5.5, 90)

# Ball possession: R2K (own team controls ball)
ball_possession: BallPossession_ENUM = 'R2K'

# Robot states: all active
state_robot: List[State_Robot_ENUM] = ['ACTIVE', 'ACTIVE', 'ACTIVE']

# Tactical evaluation: long-range shot, high potential due to goalie mispositioning: +9
score: int = 9

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
