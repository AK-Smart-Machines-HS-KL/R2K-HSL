from dataclasses import dataclass
from typing import List, Tuple, Literal

# === Enums & Type Aliases ===
BallPossession_ENUM = Literal['R2K', 'ENEMIE', 'NONE', 'UNKOWN']
State_Robot_ENUM = Literal['INIT', 'ACTIVE', 'PENALIZED', 'BROKEN', 'UNKNOWN']

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


# === Szene 12 Analyse ===
# Kontext: Ballverlust A3 -> R1. R2 startet Konterlauf. D2 fällt zurück, G1 sichert.
# Bedrohungspotenzial: hoch, Konterchance für ENEMY.

# Blaues Team (R2K)
# G1 (~10, 55): im Torraum, stationär
# D2 (~55, 45): fällt schnell zurück, Bewegung nach hinten (theta ~230°)
# A3 (~75, 50): verliert Ball, geringe Geschwindigkeit
position_team: List[RobotPose] = [
    (10, 55, 270.0, 0.0),
    (55, 45, 230.0, 0.8),
    (75, 50, 270.0, 0.1),
]

# Rotes Team (ENEMY)
# R1 (~74, 50): erobert Ball, leitet Konter ein
# R2 (~50, 55): startet Konterlauf nach vorne (theta ~270°, velocity 2.0)
# R3 (~40, 65): bleibt höher positioniert
position_enemie: List[RobotPose] = [
    (74, 50, 270.0, 1.0),
    (50, 55, 270.0, 2.0),
    (40, 65, 270.0, 0.0),
]

# Ballvektor: bei R1 (~74,50), Richtung R2 (~50,55), Theta ≈ 255°, Geschwindigkeit 3.2 m/s
ball_vector: Ball_Vector_TUPLE = (74, 50, 255, 3.2, 90)

# Ballbesitz: ENEMY (nach Ballverlust A3)
ball_possession: BallPossession_ENUM = 'ENEMIE'

# Status: alle blauen Roboter aktiv
state_robot: List[State_Robot_ENUM] = ['ACTIVE', 'ACTIVE', 'ACTIVE']

# Bewertung: gefährlicher Konter, Ballbesitz Gegner → negativer Score
score: int = -4

# WorldState-Instanz
ws = WorldState(
    Ball_Vector=ball_vector,
    BallPossession=ball_possession,
    Position_Team=position_team,
    Position_Enemie=position_enemie,
    State_Robot=state_robot,
    Score=score
)

if __name__ == '__main__':
    from pprint import pprint
    pprint(ws)
