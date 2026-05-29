
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

# === Analysis of Scene 2 (Counter-attack setup) ===
# Blue team (R2K) in possession, preparing counter-attack.
# G1: Goalkeeper (~10,55), stationary, facing right (270°)
# D1: Defender (~27,45), facing down-right (315°), has the ball
# A3: Attacker (~60,55), moving forward (velocity 0.4 m/s ≈ 40 cm/s), facing right (270°)

position_team: List[RobotPose] = [
    (10, 55, 270.0, 0.0),
    (27, 45, 315.0, 0.0),
    (60, 55, 270.0, 40.0),
]

# Red team (enemies)
# R1: (~30,50) pressing D1
# R2: (~35,70) covering deeper
# R3: (~50,50) near midfield, not intercepting directly
position_enemie: List[RobotPose] = [
    (30, 50, 90.0, 0.0),
    (35, 70, 90.0, 0.0),
    (50, 50, 90.0, 0.0),
]

# Ball vector: at D1 (~27,45), directed diagonally to A3 (toward ~60,55)
# heading ≈ 300° (right-forward diagonal), medium-high pass speed
ball_vector: Ball_Vector_TUPLE = (27, 45, 300, 5.0, 90)

# Ball possession: R2K (own team)
ball_possession: BallPossession_ENUM = 'R2K'

# Robot states: all active
state_robot: List[State_Robot_ENUM] = ['ACTIVE', 'ACTIVE', 'ACTIVE']

# Tactical evaluation (strong counter opportunity): +6
score: int = 6

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
