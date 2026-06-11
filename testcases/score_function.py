import math
from dataclasses import dataclass
from typing import List, Tuple, Literal

# =============================================================================
# 1. Datenstrukturen (Entspricht der neuen worldstate.py)
# =============================================================================

# ENUM für Ballbesitz
BallPossession_ENUM = Literal['R2K', 'ENEMY', 'NONE', 'UNKOWN']

# ENUM für Roboter-Status
State_Robot_ENUM = Literal['INIT', 'ACTIVE', 'PENALIZED', 'BROKEN', 'UNKNOWN']

# Pose in 2D (x, y, theta) - Floats für exakte Berechnung
RobotPose = Tuple[float, float, float]

# Ballvektor (x, y, theta, velocity, prob)
Ball_Vector_TUPLE = Tuple[float, float, float, float, float]

# TUPEL für Position im 2D-Raum (x,y) für interne Berechnungen
Position = Tuple[float, float]

@dataclass(frozen=True)
class WorldState:
    Ball_Vector: Ball_Vector_TUPLE
    BallPossession: BallPossession_ENUM
    Position_Team: List[RobotPose]
    Position_Enemie: List[RobotPose]
    State_Robot: List[State_Robot_ENUM]
    Score: int  # Ersetzt Score_Team und Score_Enemie

# =============================================================================
# 2. Konstanten (Feld in Metern) & Gewichte
# =============================================================================

# Angenommene Feldmaße (Basierend auf Testcase 1: Goalie bei X = -6.0)
OWN_GOAL_POS: Position = (-6.0, 0.0)
OPPONENT_GOAL_POS: Position = (6.0, 0.0)
MAX_FIELD_DISTANCE = 12.0  # Von -6.0 bis +6.0

# Gewichte für den Gesamt-Score
WEIGHT_GOAL_CHANCE = 4.0
WEIGHT_DEFENSIVE_DENSITY = 3.0
WEIGHT_BALL_POSSESSION = 2.0
WEIGHT_ROBOT_STATUS = 1.0

# Dynamische Gewichtsverschiebung
WEIGHT_SHIFT = 1.5
MAX_SHOT_ANGLE_DEVIATION = 15.0  # in Grad

# =============================================================================
# 3. Hilfsfunktionen
# =============================================================================

def calculate_distance(point1: Position, point2: Position) -> float:
    """Berechnet die euklidische Distanz zwischen zwei Punkten."""
    delta_x = point1[0] - point2[0]
    delta_y = point1[1] - point2[1]
    return math.sqrt(delta_x**2 + delta_y**2)

def calculate_angle_to_point(from_pos: Position, to_pos: Position) -> float:
    """Berechnet den absoluten Winkel (in Grad, 0-360) von Punkt 1 zu Punkt 2."""
    delta_x = to_pos[0] - from_pos[0]
    delta_y = to_pos[1] - from_pos[1]
    radian = math.atan2(delta_y, delta_x)
    angle = math.degrees(radian)
    if angle < 0:
        angle += 360.0
    return angle

def calculate_angle_difference(angle1: float, angle2: float) -> float:
    """Berechnet die kleinste absolute Differenz zwischen zwei Winkeln (in Grad)."""
    diff = angle1 - angle2
    while diff > 180:
        diff -= 360
    while diff <= -180:
        diff += 360
        
    return abs(diff)

# =============================================================================
# 4. Metrik-Funktionen
# =============================================================================

def evaluate_goal_chance(world_state: WorldState) -> float:
    """Metrik 1: Torchance (Offensiv- / Defensiv-Druck). Bereich: [-1.0 bis +1.0]"""
    ball_pos: Position = (world_state.Ball_Vector[0], world_state.Ball_Vector[1])
    possession = world_state.BallPossession

    # --- Threat Score (Gefahr für EIGENES Tor) ---
    dist_ball_to_own_goal = calculate_distance(ball_pos, OWN_GOAL_POS)
    threat_by_distance = max(0.0, 1.0 - (dist_ball_to_own_goal / MAX_FIELD_DISTANCE))

    threat_score = 0.0
    if possession == 'ENEMY':
        threat_score = threat_by_distance
    elif possession in ['NONE', 'UNKOWN']:  # Fallback für Tippfehler inkludiert
        threat_score = threat_by_distance * 0.5

    # --- Opportunity Score (Gelegenheit für GEGNER-Tor) ---
    dist_ball_to_opponent_goal = calculate_distance(ball_pos, OPPONENT_GOAL_POS)
    opportunity_by_distance = max(0.0, 1.0 - (dist_ball_to_opponent_goal / MAX_FIELD_DISTANCE))

    opportunity_score = 0.0
    if possession == 'R2K':
        try:
            striker_pose = world_state.Position_Team[2]
            striker_pos = (striker_pose[0], striker_pose[1])
            striker_angle = striker_pose[2]

            target_angle = calculate_angle_to_point(striker_pos, OPPONENT_GOAL_POS)
            angle_diff = calculate_angle_difference(striker_angle, target_angle)

            if angle_diff <= MAX_SHOT_ANGLE_DEVIATION:
                shot_factor = 1.0
            else:
                shot_factor = max(0.0, 1.0 - (angle_diff / 90.0))

            opportunity_score = opportunity_by_distance * shot_factor

        except IndexError:
            opportunity_score = 0.0
            
    elif possession in ['NONE', 'UNKOWN']:
        opportunity_score = opportunity_by_distance * 0.5

    return opportunity_score - threat_score


def evaluate_defensive_density(world_state: WorldState) -> float:
    """Metrik 2: Defensive Dichte. Bereich: [-1.0 bis +1.0]"""
    ball_x = world_state.Ball_Vector[0]

    try:
        g1_pos_x = world_state.Position_Team[0][0]
        d2_pos_x = world_state.Position_Team[1][0]
    except IndexError:
        return -1.0 

    # Ist der Ball in der gegnerischen Hälfte? (0.0 = Mittellinie)
    if ball_x > 0.0:
        return 1.0

    # "Dazwischen" = Roboter-X ist näher am eigenen Tor (kleinerer X-Wert) als der Ball-X
    g1_is_blocking = (g1_pos_x < ball_x)
    d2_is_blocking = (d2_pos_x < ball_x)

    if g1_is_blocking and d2_is_blocking:
        return 1.0
    elif g1_is_blocking and not d2_is_blocking:
        return -0.5
    elif not g1_is_blocking and d2_is_blocking:
        return -0.2
    elif not g1_is_blocking and not d2_is_blocking:
        return -1.0

    return 0.0


def evaluate_ball_possession(world_state: WorldState) -> float:
    """Metrik 3: Ballbesitz im Mittelfeld. Bereich: [-1.0 bis +1.0]"""
    ball_x = world_state.Ball_Vector[0]
    possession = world_state.BallPossession

    # Definiere "Mittelfeld" in Metern (z.B. von Strafraumgrenze zu Strafraumgrenze)
    OWN_PENALTY_AREA_X = -4.5
    OPPONENT_PENALTY_AREA_X = 4.5

    if OWN_PENALTY_AREA_X < ball_x < OPPONENT_PENALTY_AREA_X:
        if possession == 'R2K':
            return 1.0
        if possession == 'ENEMY':
            return -1.0

    return 0.0


def evaluate_robot_status(robot_states_list: List[State_Robot_ENUM]) -> float:
    """Metrik 4: Roboter-Status. Bereich: [-1.0 bis +1.0]"""
    active_robots = 0
    total_robots = len(robot_states_list)

    if total_robots == 0:
        return -1.0

    for status in robot_states_list:
        if status == 'ACTIVE':
            active_robots += 1

    metric_value = active_robots / total_robots
    return (metric_value * 2.0) - 1.0

# =============================================================================
# 5. Haupt-Scoring-Funktion
# =============================================================================

def calculate_score(world_state: WorldState) -> float:
    """Berechnet den finalen, normalisierten Score [-10 bis +10] für den WorldState."""
    
    # 1. Tordifferenz / Heuristischen Score auslesen
    goal_difference = world_state.Score

    # 2. Lokale Gewichte initialisieren
    local_weight_goal_chance = WEIGHT_GOAL_CHANCE
    local_weight_density = WEIGHT_DEFENSIVE_DENSITY

    # 3. Gewichte anpassen
    if goal_difference < 0:
        local_weight_goal_chance = WEIGHT_GOAL_CHANCE + WEIGHT_SHIFT
        local_weight_density = WEIGHT_DEFENSIVE_DENSITY - WEIGHT_SHIFT 
    elif goal_difference > 0:
        local_weight_goal_chance = WEIGHT_GOAL_CHANCE - WEIGHT_SHIFT
        local_weight_density = WEIGHT_DEFENSIVE_DENSITY + WEIGHT_SHIFT
    
    local_weight_goal_chance = max(0.5, local_weight_goal_chance)
    local_weight_density = max(0.5, local_weight_density)

    # 4. Metriken berechnen
    metric_goal_chance = evaluate_goal_chance(world_state)
    metric_density = evaluate_defensive_density(world_state)
    metric_possession = evaluate_ball_possession(world_state)
    metric_status = evaluate_robot_status(world_state.State_Robot)

    # 5. Beiträge berechnen
    contribution_goal_chance = metric_goal_chance * local_weight_goal_chance
    contribution_density = metric_density * local_weight_density
    contribution_possession = metric_possession * WEIGHT_BALL_POSSESSION
    contribution_status = metric_status * WEIGHT_ROBOT_STATUS

    local_total_weight = (
        local_weight_goal_chance +
        local_weight_density +
        WEIGHT_BALL_POSSESSION +
        WEIGHT_ROBOT_STATUS
    )
    unnormalized_score = (
        contribution_goal_chance +
        contribution_density +
        contribution_possession +
        contribution_status
    )

    final_score = (unnormalized_score / local_total_weight) * 10.0
    return round(final_score, 1)