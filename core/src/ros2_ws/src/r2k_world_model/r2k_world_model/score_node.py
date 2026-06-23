import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import json
import math
import os

BASE_DIR = os.getenv('ROS2K_WS', '.')
WORLD_STATE_PATH = os.path.join(BASE_DIR, "shared_state", "Worldstate.json")

class PureNumericalScorer(Node):
    def __init__(self):
        super().__init__('r2k_pure_scorer')
        
        # INPUT: Realzeit-Koordinaten vom Tracker
        self.sub_pos = self.create_subscription(
            String, 
            '/world_positions', 
            self.positions_callback, 
            10
        )
        
        # OUTPUT: Numerischer Score für andere ROS-Knoten/Visualizer
        self.pub_score = self.create_publisher(
            String, 
            '/tactical_score', 
            10
        )
        
        # Feldgrenzen-Konstanten für Out-of-Bounds Berechnung
        self.pitch_x_min, self.pitch_x_max = -4.5, 4.5
        self.pitch_y_min, self.pitch_y_max = -3.0, 3.0
        
        self.get_logger().info("🔢 Scorer V4 Online: Pure Numerical Fact-Checking & Aggregation Node")

    def get_distance(self, p1, p2):
        return math.sqrt((p1['x'] - p2['x'])**2 + (p1['y'] - p2['y'])**2)

    def positions_callback(self, msg):
        try:
            incoming_data = json.loads(msg.data)
            entities = incoming_data['entities']
            ball = entities.get('soccer_ball', {'x': 0.0, 'y': 0.0})
            
            # --- 1. METRIK: Ballbesitz / Distanz-Vorteil (Euklidischer Ist-Zustand) ---
            blue_distances = {name: self.get_distance(data, ball) for name, data in entities.items() if 'blue' in name}
            red_distances = {name: self.get_distance(data, ball) for name, data in entities.items() if 'red' in name}
            
            min_blue_dist = min(blue_distances.values()) if blue_distances else 99.0
            min_red_dist = min(red_distances.values()) if red_distances else 99.0
            
            # Objektive Zuweisung des faktischen Ballbesitzes basierend auf physischer Nähe (< 0.5m)
            if min_blue_dist < 0.5 and min_blue_dist < min_red_dist:
                possession_status = "R2K"
                possession_score = 3.0
            elif min_red_dist < 0.5 and min_red_dist < min_blue_dist:
                possession_status = "ENEMIE"
                possession_score = -3.0
            else:
                possession_status = "NONE"
                # Wer ist dem Ball mathematisch näher, wenn er frei rollt?
                possession_score = 1.0 if min_blue_dist < min_red_dist else -1.0

            # --- 2. METRIK: Ball-Progression (X-Achsen Territorium) ---
            # Normierung der X-Koordinate des Spielfelds (-4.5 bis +4.5) auf einen Progression-Wert
            progression_score = ball['x'] * 1.5

            # --- 3. METRIK: Feldgrenzen-Gefahr (Out of Bounds Risk) ---
            # Bestraft Situationen, in denen der Ball kurz davor ist, das Spielfeld zu verlassen
            boundary_penalty = 0.0
            dist_to_y_edge = min(abs(self.pitch_y_max - ball['y']), abs(ball['y'] - self.pitch_y_min))
            dist_to_x_edge = min(abs(self.pitch_x_max - ball['x']), abs(ball['x'] - self.pitch_x_min))
            
            if dist_to_y_edge < 0.3 or dist_to_x_edge < 0.3:
                boundary_penalty = -1.5

            # --- 4. METRIK: Material-Vorteil (Active Robot Delta) ---
            # Reine Mengenzählung der detektierten Roboter im aktuellen Frame
            blue_count = sum(1 for name in entities if 'blue' in name)
            red_count = sum(1 for name in entities if 'red' in name)
            material_delta = (blue_count - red_count) * 2.0

            # --- CALCULATE FINAL MATHEMATICAL SCORE ---
            total_score = possession_score + progression_score + boundary_penalty + material_delta
            final_score = max(-10.0, min(10.0, total_score))

            # Rein deskriptive Labels für den Visualizer ohne taktische Analysen
            if final_score > 4.0:
                score_label = "HIGH_VALUE"
            elif final_score > 1.0:
                score_label = "POSITIVE"
            elif final_score < -4.0:
                score_label = "CRITICAL"
            elif final_score < -1.0:
                score_label = "NEGATIVE"
            else:
                score_label = "NEUTRAL"

            score_payload = {
                "current_numerical_score": round(final_score, 2),
                "fact_label": score_label,
                "ball_possession_fact": possession_status
            }
            
            # Publizieren des nackten Scores im ROS-Netzwerk
            self.pub_score.publish(String(data=json.dumps(score_payload)))
            
            # --- AGGREGATOR FUNCTION: Zusammenführen und sicheres Schreiben der Worldstate.json ---
            aggregated_state = {
                "entities": entities,
                "sys_time": incoming_data["sys_time"],
                "numerical_analysis": score_payload
            }
            
            temp_path = WORLD_STATE_PATH + ".tmp"
            try:
                with open(temp_path, 'w') as f:
                    json.dump(aggregated_state, f, indent=2)
                os.replace(temp_path, WORLD_STATE_PATH)
            except Exception:
                pass

        except Exception as e:
            self.get_logger().error(f"Failed to process and aggregate world state: {str(e)}")

def main(args=None):
    rclpy.init(args=args)
    scorer = PureNumericalScorer()
    try:
        rclpy.spin(scorer)
    except KeyboardInterrupt:
        pass
    finally:
        scorer.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
