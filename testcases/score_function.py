import math
from typing import List, Tuple, Literal
from dataclasses import dataclass

# --- worldstate.py ---

# ENUM für Ballbesitz
BallPossession_ENUM = Literal['R2K','ENEMIE','NONE']

# ENUM für Roboter-Status:
State_Robot_ENUM = Literal['ACTIVE','PENALIZED','BROKEN', 'UNKNOWN']

# TUPEL für Postion im 2D-Raum (x,y)
Position = Tuple [float,float]

# TUPEL für Position im 2D-Raum inklusive Rotation (x,y,theta)
# theta counts counter clockwise 0o .. 259o, 0o is the axis, the bot is facing
Pose = Tuple [float,float,int]

# TUPEL für Ballvektor (x,y,theta,velocity, prob)
# velocity: in m/sec
# prob: probality of belief in the data 0%..100 %
Ball_Vector_TUPLE = Tuple[float,float,int,float,float]

@dataclass(frozen=True)
class WorldState:
    Ball_Vector: Ball_Vector_TUPLE

    Position_Team: List[Pose]
    Position_Enemie: List[Pose]

    BallPossession: BallPossession_ENUM
    State_Robot: List[State_Robot_ENUM]

    Goal_Team: Position
    Goal_Enemie: Position

# --- 3. Hilfsfunktionen ---

def calculate_distance(point1: Position, point2: Position) -> float:
    # euclidean distance
    delta_x = point1[0] - point2[0]
    delta_y = point2[1] - point2[1]
    return math.sqrt(delta_x**2 + delta_y**2)

# --- Gewichtung ---

class ScoreCalculator:
    WEIGHT_GOAL_CHANCE = 4.0
    WEIGTH_DEFENSIVE_DENSITY = 3.0
    WEIGHT_BALL_POSSESSION = 2.0
    WEIGHT_ROBOT_STATUS = 1.0
    TOTAL_WEIGHT = 10.0

    OWN_GOAL_POS = (0.0, 300.0)
    ENEMIE_GOAL_POS = (900.0, 300.0)
    MAX_DISTANCE = 900.0
    OWN_PENALTY_AREA_X = 250.0
    ENEMIE_PENALTY_AREA_X = 650.0

    #--- 1. Hauptfunktion ----

    def calculate_score(self, world_state: WorldState) -> float:
        # Score zwischen [-10.0, 10.0]
        # 1. Metriken berechnen
        metric_goal_chance = self._evaluate_goal_chance(world_state)
        metric_density = self._evaluate_defensive_density(world_state)
        metric_ball_possession = self._evaluate_ball_possession(world_state)
        metric_status = self._evaluate_robot_status(world_state)

        # 2. Gewichtung berechnen
        weighted_goal_chance = metric_goal_chance * self.WEIGHT_GOAL_CHANCE
        weighted_density = metric_density * self.WEIGTH_DEFENSIVE_DENSITY
        weighted_ball_possesion = metric_ball_possession * self.WEIGHT_BALL_POSSESSION
        weighted_status = metric_status * self.WEIGHT_ROBOT_STATUS

        # 3. Score berechnung
        unnormalized_score = weighted_goal_chance + weighted_density + weighted_ball_possesion + weighted_status

        # 4. Score normalisieren
        final_score = (unnormalized_score / self.TOTAL_WEIGHT) * 10.0

        return round(final_score, 1)
    
    #--- 2. Metrik-Berechnung ---

    def _evaluate_goal_chance(self, world_state: WorldState) -> float:
        # Metrik 1: Torchance (Offensiv-/Defensiv), -1 max Bedrohung, +1 max Chance

        ball_x = world_state.Ball_Vector[0]
        ball_y = world_state.Ball_Vector[1]
        possession = world_state.BallPossession
        ball_pos: Position = (ball_x, ball_y)

        # 1. Distanz zu eigenem Tor, Bedrohungswert

        dist_ball_to_own_goal = calculate_distance(ball_pos / self.OWN_GOAL_POS)
        # 0m = 1.0 (max Bedrohung) 90m = 0.0 (min Bedrohung)
        distance_threat_value = 1.0 - (dist_ball_to_own_goal / self.MAX_DISTANCE)

        # Modifizierung anhand Ballbesitz (Wenn 'R2K' score bleibt 0.0)
        threat_value = 0.0
        if possession == 'ENEMIE':
            threat_value = distance_threat_value
        elif possession == 'NONE':
            threat_value = distance_threat_value * 0.5

        # 2. Gelegenheit für Tor, Chancenwert

        dist_ball_to_enemie_goal = calculate_distance(ball_pos, self.ENEMIE_GOAL_POS)
        distance_chance_value = 1.0 - (dist_ball_to_enemie_goal / self.MAX_DISTANCE)

        chance_value = 0.0
        if possession == 'R2K':
            chance_value = distance_chance_value
        elif possession == 'NONE':
            chance_value = distance_chance_value * 0.5
        
        # 3. Finaler Score

        return (chance_value - threat_value)
    
    def _evaluate_defensive_density(self, world_state: WorldState) -> float:
        # 2. Metrik: Defensive Dichte (Bewertung Verteidiger Position)

        ball_x = world_state.Ball_Vector[0]

        # Pos der verteidiger, Min zwei Roboter im Team
        if len(world_state.Position_Team) < 2:
            return 0.0
        
        g1_pos_x = world_state.Position_Team[0][0]
        d2_pos_x = world_state.Position_Team[1][0]

        # Ball in gegnerischen Hälfte?
        if ball_x > 450.0:
            return 1.0 # Ball weit weg, also gut
        
        g1_blocking = (g1_pos_x < ball_x)
        d2_blocking = (d2_pos_x < ball_x)

        if g1_blocking and d2_blocking:
            return 1.0
        
        # Goalie blockt und Defense nicht, Goalie blockt nicht aber Defense tut es
        if g1_blocking and (not d2_blocking):
            return -0.5
        if (not g1_blocking) and d2_blocking:
            return -0.2
        
        if (not g1_blocking) and (not d2_blocking):
            return -1.0
        return 0.0 
        
        #Y?

    def _evaluate_ball_possession(self, world_state: WorldState) -> float:
        # 3. Metrik: Stabiler Ballbesitz im Mittelfeld

         ball_x =  world_state.Ball_Vector[0]
         possession = world_state.BallPossession

         # Bewertung nur im Mittelfeld
         if self.OWN_PENALTY_AREA_X < ball_x < self.ENEMIE_PENALTY_AREA_X:
             if possession == 'R2K':
                 return 1.0
             if possession == 'ENEMIE':
                 return -1.0
             
         return 0.0

    def _evaluate_robot_status(self, world_state: WorldState) -> float:
        # 4. Metrik: Wie viele Roboter sind aktiv

        robot_states_list = List[State_Robot_ENUM]
        active_robots = 0
        total_robots = len(robot_states_list)

        if total_robots == 0:
            return -1.0
        
        for status in robot_states_list:
            if status == 'ACTIVE':
                active_robots += 1
        
        metric_value = active_robots / total_robots

        return (metric_value * 2.0) - 1.0