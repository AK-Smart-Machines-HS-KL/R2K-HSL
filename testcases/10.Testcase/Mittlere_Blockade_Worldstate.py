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


# === Szene 10 Analyse ===
# Kontext: Gegner R1 kontrolliert Ball im Zentrum, will Pässe zu R2 oder R3 spielen.
# D2 blockiert den Passweg zu R2, A3 blockiert Passweg zu R3. Defensive kompakt.

# Blaues Team (R2K)
# G1 (~10,55): Goalie, statisch
# D2 (~35,45): Blockiert Passweg oben, Richtung R2
# A3 (~35,65): Blockiert Passweg unten, Richtung R3
position_team: List[RobotPose] = [
    (10, 55, 270.0, 0.0),
    (35, 45, 270.0, 0.0),
    (35, 65, 270.0, 0.0),
]

# Rotes Team (ENEMY)
# R1 (~50,55): Im Zentrum, am Ball, will Pass spielen
# R2 (~65,40): Läuft in Passlinie
# R3 (~65,70): Läuft in Passlinie
position_enemie: List[RobotPose] = [
    (50, 55, 270.0, 0.0),
    (65, 40, 270.0, 0.0),
    (65, 70, 270.0, 0.0),
]

# Ballvektor: bei R1 (~50,55), Richtung R2 (~65,40), Theta ≈ 315°, 2.5 m/s, hohe Sicherheit
ball_vector: Ball_Vector_TUPLE = (50, 55, 315, 2.5, 85)

# Ballbesitz: ENEMIE
ball_possession: BallPossession_ENUM = 'ENEMIE'

# Alle blauen Roboter aktiv
state_robot: List[State_Robot_ENUM] = ['ACTIVE', 'ACTIVE', 'ACTIVE']

# Bewertung: Gegner unter Druck, Ballbesitz ungefährlich → Score leicht positiv für R2K
score: int = 3

# Instanziierung des WorldStates
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
