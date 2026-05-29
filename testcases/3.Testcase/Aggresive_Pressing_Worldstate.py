
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

# === Scene 3 Analysis ===
# Context: Blue team (R2K) defensively intercepts an opponent's attack.
# D2 is intercepting the passing lane, A3 presses the ball carrier (R2).
# G1 remains positioned in goal.

# Blue team positions
# G1: (~10,55), facing right (270°), stationary
# D2: (~65,45), moving diagonally forward-left to intercept (135°), ~0.5 m/s (50 cm/s)
# A3: (~70,60), pressing ballcarrier (facing up-left ≈ 135°), moving ~0.6 m/s (60 cm/s)
position_team: List[RobotPose] = [
    (10, 55, 270.0, 0.0),
    (65, 45, 135.0, 50.0),
    (70, 60, 135.0, 60.0),
]

# Red team positions
# R2 (ball carrier): (~75,50), moving diagonally right-down (~315°), ~0.3 m/s
# R1: (~85,70), stationary, potential pass target
# R3: (~80,35), stationary, offside zone
position_enemie: List[RobotPose] = [
    (75, 50, 315.0, 30.0),
    (85, 70, 270.0, 0.0),
    (80, 35, 270.0, 0.0),
]

# Ball vector: at R2 (~75,50), heading right-down (~315°), moderate speed, belief high
ball_vector: Ball_Vector_TUPLE = (75, 50, 315, 4.0, 85)

# Ball possession: ENEMIE (red team controls ball)
ball_possession: BallPossession_ENUM = 'ENEMIE'

# Robot states: all active
state_robot: List[State_Robot_ENUM] = ['ACTIVE', 'ACTIVE', 'ACTIVE']

# Tactical score (defensive interception well positioned): +3
score: int = 3

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
