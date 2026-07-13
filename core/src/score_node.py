import rclpy
import json
from rclpy.node import Node
from std_msgs.msg import String
from collections import deque

class ScoreNode(Node):
    def __init__(self):
        super().__init__('score_node')
        self.sub_pos = self.create_subscription(String, '/world_positions', self.pos_callback, 10)
        self.pub = self.create_publisher(String, '/tactical_score', 10)
        
        self.total_score_sum = 0.0
        self.score_samples_count = 0
        
        self.momentum_window = deque(maxlen=300)
        self.MOMENTUM_MIN_SAMPLES = 10
        self.MOMENTUM_SCALE_FACTOR = 10.0
        
        self.get_logger().info("🧮 Scorer V6 Online: Momentum tracking enabled")

    def _calculate_momentum(self):
        n = len(self.momentum_window)
        if n < self.MOMENTUM_MIN_SAMPLES:
            return 0.0, "stable"
        
        sum_x = sum(range(n))
        sum_y = sum(score for _, score in self.momentum_window)
        sum_xy = sum(i * score for i, (_, score) in enumerate(self.momentum_window))
        sum_x2 = sum(i * i for i in range(n))
        
        denominator = n * sum_x2 - sum_x * sum_x
        if abs(denominator) < 1e-9:
            return 0.0, "stable"
        
        slope = (n * sum_xy - sum_x * sum_y) / denominator
        momentum = max(-10.0, min(10.0, slope * self.MOMENTUM_SCALE_FACTOR))
        
        if momentum > 2.0: trend = "ascending"
        elif momentum > 0.5: trend = "improving"
        elif momentum > -0.5: trend = "stable"
        elif momentum > -2.0: trend = "declining"
        else: trend = "collapsing"
        
        return round(momentum, 2), trend

    def pos_callback(self, msg):
        try:
            data = json.loads(msg.data)
            ents = data.get('entities', {})
            ball = ents.get('soccer_ball')
            
            score = 0.0
            fact = "Neutral Game"
            poss = "Contested"

            if ball:
                # 1. Basis-Score durch Ball-Position (X-Achse: -4.5 bis +4.5)
                score += ball['x'] * 1.5 
                
                # 2. Distanz-Check: Wer ist näher am Ball?
                dist_blue = min([((b['x']-ball['x'])**2 + (b['y']-ball['y'])**2)**0.5 for k, b in ents.items() if 'blue' in k], default=99)
                dist_red = min([((b['x']-ball['x'])**2 + (b['y']-ball['y'])**2)**0.5 for k, b in ents.items() if 'red' in k], default=99)

                if dist_blue < dist_red and dist_blue < 1.0:
                    poss = "Blue Team"
                    score += 2.0
                    fact = "Blue attacking" if ball['x'] > 0 else "Blue defending"
                elif dist_red < dist_blue and dist_red < 1.0:
                    poss = "Red Team"
                    score -= 2.0
                    fact = "Red attacking" if ball['x'] < 0 else "Red defending"
            
            # Score auf max -10 bis +10 kappen
            score = max(min(score, 10.0), -10.0)

            # --- NEU: DURCHSCHNITT (Running Average) BERECHNEN ---
            self.score_samples_count += 1
            self.total_score_sum += score
            avg_score = self.total_score_sum / self.score_samples_count
            
            # --- NEU: MOMENTUM BERECHNEN ---
            import time
            timestamp = time.time()
            self.momentum_window.append((timestamp, score))
            momentum_30s, momentum_trend = self._calculate_momentum()

            out_data = {
                "current_numerical_score": round(score, 2),
                "average_numerical_score": round(avg_score, 2),
                "momentum_30s": momentum_30s,
                "momentum_trend": momentum_trend,
                "fact_label": fact,
                "ball_possession_fact": poss
            }
            out_msg = String()
            out_msg.data = json.dumps(out_data)
            self.pub.publish(out_msg)

        except Exception as e:
            self.get_logger().error(f"Scorer Error: {e}")

def main():
    rclpy.init()
    node = ScoreNode()
    try: rclpy.spin(node)
    except KeyboardInterrupt: pass
    finally: node.destroy_node(); rclpy.shutdown()

if __name__ == '__main__':
    main()
