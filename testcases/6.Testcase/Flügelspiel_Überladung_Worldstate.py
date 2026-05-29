
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

# === Scene 6 Analysis ===
# Context: Offensive chance by blue team (R2K) after a backpass from A3 to D2.
# D2 has open shot opportunity since R2 moved out of position and center is open.

# Blue team positions
# G1: (~15,55), facing right (270°), stationary
# D2: (~75,50), positioned centrally near enemy box, facing toward goal (270°), stationary (0 m/s)
# A3: (~85,60), just performed backpass, facing back-left (120°), low velocity (~0.2 m/s)
position_team: List[RobotPose] = [
    (15, 55, 270.0, 0.0),
    (75, 50, 270.0, 0.0),
    (85, 60, 120.0, 20.0),
]

# Red team positions
# R1: (~90,45), in defensive position
# R2: (~80,55), moving out from center (facing up-left, 135°), moderate speed (~0.4 m/s)
# R3: (~95,35), deep defensive coverage
position_enemie: List[RobotPose] = [
    (90, 45, 270.0, 0.0),
    (80, 55, 135.0, 40.0),
    (95, 35, 270.0, 0.0),
]

# Ball vector: from A3 (~85,60) back to D2 (~75,50), directed ≈ 300°, medium speed, high confidence
ball_vector: Ball_Vector_TUPLE = (85, 60, 300, 4.0, 90)

# Ball possession: R2K (own team controls ball)
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
