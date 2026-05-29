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


# === Szene 11 Analyse ===
# Kontext: Gegner (R1) in Ballbesitz nahe der blauen Hälfte. D2 stellt ihn passiv, A3 schneidet Passweg zu R2.
# Das rote Team hat wenig Raum, Passoptionen eingeschränkt.

# Blaues Team (R2K)
# G1 (~10,55): Goalie, stationär
# D2 (~35,45): stellt R1, geringes Tempo
# A3 (~45,55): zentral, deckt Passweg zu R2
position_team: List[RobotPose] = [
    (10, 55, 270.0, 0.0),
    (35, 45, 270.0, 0.0),
    (45, 55, 270.0, 0.0),
]

# Rotes Team (ENEMY)
# R1 (~40,40): am Ball, versucht Pass auf R2
# R2 (~55,55): Passoption
# R3 (~75,30): tiefere Position
position_enemie: List[RobotPose] = [
    (40, 40, 270.0, 0.0),
    (55, 55, 270.0, 0.0),
    (75, 30, 270.0, 0.0),
]

# Ballvektor: bei R1 (~40,40), gerichtet auf R2 (~55,55), Theta ≈ 45°, Geschwindigkeit 2.0 m/s
ball_vector: Ball_Vector_TUPLE = (40, 40, 45, 2.0, 85)

# Ballbesitz: ENEMY
ball_possession: BallPossession_ENUM = 'ENEMIE'

# Roboterstatus: alle aktiv
state_robot: List[State_Robot_ENUM] = ['ACTIVE', 'ACTIVE', 'ACTIVE']

# Bewertung: Gegner mit Ball, aber stark eingeschränkt, kaum Gefahr. Score leicht positiv für R2K.
score: int = 2

# Instanz des WorldStates
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
