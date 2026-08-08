import rclpy
import json
import os
import math
import time
from rclpy.node import Node
from std_msgs.msg import String
from collections import deque

# === Named module constants (no hard-coded thresholds in code body) ===
BALL_POSITION_GAIN = 1.5
POSSESSION_BONUS = 2.0
POSSESSION_DIST = 1.0
CLUSTER_PENALTY_SEVERE = 2.0
CLUSTER_PENALTY_MILD = 1.0
CLUSTER_DIST_SEVERE = 0.5
CLUSTER_DIST_MILD = 1.0
LANE_OPEN_PENALTY = 3.0
LANE_BLOCKER_BONUS = 1.0
LANE_BLOCKER_BANDWIDTH = 1.5
SCORE_MIN = -10.0
SCORE_MAX = 10.0
MOMENTUM_WINDOW_SIZE = 300
MOMENTUM_MIN_SAMPLES = 10
MOMENTUM_SCALE_FACTOR = 10.0

# === Continuous proximity reward constants (no thresholds, proportional) ===
# Reward is stateless: based on current distance, not delta.
# max(0, REFERENCE_DIST - dist) * GAIN gives a continuous bonus that
# scales with how close the nearest blue is to the ball / nearest red.
PRESSING_GAIN = 1.0
PRESSING_REFERENCE_DIST = 3.0   # max distance at which pressing is rewarded
MARKING_GAIN = 0.5
MARKING_REFERENCE_DIST = 3.0   # max distance at which marking is rewarded

RESET_FLAG = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          'shared_state', 'reset_flag.json')


class ScoreNode(Node):
    def __init__(self):
        super().__init__('score_node')
        self.sub_pos = self.create_subscription(String, '/world_positions', self.pos_callback, 10)
        self.pub = self.create_publisher(String, '/tactical_score', 10)

        self.total_score_sum = 0.0
        self.score_samples_count = 0

        self.momentum_window = deque(maxlen=MOMENTUM_WINDOW_SIZE)

        self.get_logger().info("Scorer V7 Online: continuous proximity pressing + marking, momentum tracking")

    def _calculate_momentum(self):
        n = len(self.momentum_window)
        if n < MOMENTUM_MIN_SAMPLES:
            return 0.0, "stable"

        sum_x = sum(range(n))
        sum_y = sum(score for _, score in self.momentum_window)
        sum_xy = sum(i * score for i, (_, score) in enumerate(self.momentum_window))
        sum_x2 = sum(i * i for i in range(n))

        denominator = n * sum_x2 - sum_x * sum_x
        if abs(denominator) < 1e-9:
            return 0.0, "stable"

        slope = (n * sum_xy - sum_x * sum_y) / denominator
        momentum = max(SCORE_MIN, min(SCORE_MAX, slope * MOMENTUM_SCALE_FACTOR))

        if momentum > 2.0: trend = "ascending"
        elif momentum > 0.5: trend = "improving"
        elif momentum > -0.5: trend = "stable"
        elif momentum > -2.0: trend = "declining"
        else: trend = "collapsing"

        return round(momentum, 2), trend

    def _check_reset(self):
        """Check for warp-and-resume reset flag. Clears all stateful metrics."""
        if os.path.exists(RESET_FLAG):
            self.total_score_sum = 0.0
            self.score_samples_count = 0
            self.momentum_window.clear()
            try:
                os.remove(RESET_FLAG)
            except OSError:
                pass
            self.get_logger().info("Reset flag detected — clearing momentum state")

    def pos_callback(self, msg):
        try:
            self._check_reset()

            data = json.loads(msg.data)
            ents = data.get('entities', {})
            ball = ents.get('soccer_ball')

            score = 0.0
            fact = "Neutral Game"
            poss = "Contested"

            if ball:
                # 1. Basis-Score durch Ball-Position (X-Achse: -4.5 bis +4.5)
                score += ball['x'] * BALL_POSITION_GAIN

                # 2. Distanz-Check: Wer ist näher am Ball?
                dist_blue = min([((b['x']-ball['x'])**2 + (b['y']-ball['y'])**2)**0.5 for k, b in ents.items() if 'blue' in k], default=99)
                dist_red = min([((b['x']-ball['x'])**2 + (b['y']-ball['y'])**2)**0.5 for k, b in ents.items() if 'red' in k], default=99)

                if dist_blue < dist_red and dist_blue < POSSESSION_DIST:
                    poss = "Blue Team"
                    score += POSSESSION_BONUS
                    fact = "Blue attacking" if ball['x'] > 0 else "Blue defending"
                elif dist_red < dist_blue and dist_red < POSSESSION_DIST:
                    poss = "Red Team"
                    score -= POSSESSION_BONUS
                    fact = "Red attacking" if ball['x'] < 0 else "Red defending"

                # === Phase R: additional metrics (appended, non-breaking) ===
                try:
                    # Cluster penalty: blue bots too close
                    _blue = [(b['x'], b['y']) for k, b in ents.items() if 'blue' in k]
                    if len(_blue) >= 2:
                        _min_d = 999.0
                        for _i in range(len(_blue)):
                            for _j in range(_i+1, len(_blue)):
                                _d = math.hypot(_blue[_i][0]-_blue[_j][0], _blue[_i][1]-_blue[_j][1])
                                if _d < _min_d: _min_d = _d
                        if _min_d < CLUSTER_DIST_SEVERE: score -= CLUSTER_PENALTY_SEVERE
                        elif _min_d < CLUSTER_DIST_MILD: score -= CLUSTER_PENALTY_MILD

                    # Lane openness: no blue bot between ball and own goal
                    if ball['x'] < 0:
                        _blockers = 0
                        for _k, _b in ents.items():
                            if 'blue' not in _k: continue
                            if _b['x'] < ball['x'] and _b['x'] > -4.5:
                                _ratio = (ball['x'] + 4.5)
                                if _ratio > 0.01:
                                    _expected_y = ball['y'] * (_b['x'] + 4.5) / _ratio
                                    if abs(_b['y'] - _expected_y) < LANE_BLOCKER_BANDWIDTH:
                                        _blockers += 1
                        if _blockers == 0: score -= LANE_OPEN_PENALTY
                        elif _blockers >= 2: score += LANE_BLOCKER_BONUS
                except Exception:
                    pass  # never let the new metrics break the existing score

                # === V7: Continuous pressing reward (proximity-based, stateless) ===
                # Reward proportional to how CLOSE the nearest blue is to the ball.
                # No threshold: max(0, REFERENCE - dist) * GAIN
                # At dist=0: +3.0, dist=1.5: +1.5, dist=3.0: 0, dist>3.0: 0
                pressing_reward = max(0, PRESSING_REFERENCE_DIST - dist_blue) * PRESSING_GAIN
                score += pressing_reward

                # === V7: Continuous marking reward (conditional + proximity-based) ===
                # Only active when red is closer to ball than blue (red has possession potential).
                # No threshold — comparison determines "possession potential."
                # Reward proportional to how CLOSE the nearest blue is to the nearest red.
                if dist_red < dist_blue:
                    _blue_ents = {k: v for k, v in ents.items() if 'blue' in k}
                    _red_ents = {k: v for k, v in ents.items() if 'red' in k}
                    _nearest_blue_red = min([
                        math.hypot(b['x']-r['x'], b['y']-r['y'])
                        for b in _blue_ents.values()
                        for r in _red_ents.values()
                    ], default=99)
                    marking_reward = max(0, MARKING_REFERENCE_DIST - _nearest_blue_red) * MARKING_GAIN
                    score += marking_reward

            # Score auf max -10 bis +10 kappen
            score = max(min(score, SCORE_MAX), SCORE_MIN)

            # --- Running Average ---
            self.score_samples_count += 1
            self.total_score_sum += score
            avg_score = self.total_score_sum / self.score_samples_count

            # --- Momentum ---
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
