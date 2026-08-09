import rclpy
import json
import os
import math
import time
from rclpy.node import Node
from std_msgs.msg import String
from collections import deque

# === Named module constants — ALL continuous, NO step thresholds ===
BALL_POSITION_GAIN = 1.5
SCORE_MIN = -10.0
SCORE_MAX = 10.0
MOMENTUM_WINDOW_SIZE = 300
MOMENTUM_MIN_SAMPLES = 10
MOMENTUM_SCALE_FACTOR = 10.0

# === Continuous possession (replaces step-function possession) ===
# max(0, REFERENCE - dist) * GAIN — proportional, no threshold
# At dist=0: +2.0, dist=1: +1.0, dist=2: 0.0, dist>2: 0.0
POSSESSION_GAIN = 1.0
POSSESSION_REFERENCE_DIST = 2.0

# === Continuous cluster penalty (replaces step-function cluster) ===
# Penalty grows as bots get closer: max(0, REFERENCE - min_dist) * GAIN
# At min_dist=0: -3.0, min_dist=1: -1.5, min_dist=2: 0.0
CLUSTER_GAIN = 1.5
CLUSTER_REFERENCE_DIST = 2.0

# === Continuous lane openness (replaces step-function lane) ===
# Penalty grows as fewer blockers cover the goal-to-ball line.
# Uses a smooth count: each blue bot on the line contributes proportionally.
LANE_OPEN_GAIN = 1.5
LANE_BLOCKER_BANDWIDTH = 1.5  # how close to the ball-goal line counts as "blocking"

# === Continuous pressing reward (proximity-based, stateless) ===
PRESSING_GAIN = 1.0
PRESSING_REFERENCE_DIST = 3.0

# === Continuous marking reward (conditional + proximity-based) ===
MARKING_GAIN = 0.5
MARKING_REFERENCE_DIST = 3.0

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

        self.get_logger().info("Scorer V7d Online: all-continuous score formula (no thresholds)")

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
                # 1. Ball position (continuous)
                score += ball['x'] * BALL_POSITION_GAIN

                # 2. Distances
                dist_blue = min([math.hypot(b['x']-ball['x'], b['y']-ball['y'])
                                 for k, b in ents.items() if 'blue' in k], default=99)
                dist_red = min([math.hypot(b['x']-ball['x'], b['y']-ball['y'])
                                for k, b in ents.items() if 'red' in k], default=99)

                # 3. Continuous possession (replaces step function)
                # Blue proximity reward — red proximity penalty
                blue_poss = max(0, POSSESSION_REFERENCE_DIST - dist_blue) * POSSESSION_GAIN
                red_poss = max(0, POSSESSION_REFERENCE_DIST - dist_red) * POSSESSION_GAIN
                score += blue_poss - red_poss

                if dist_blue < dist_red:
                    poss = "Blue Team"
                    fact = "Blue attacking" if ball['x'] > 0 else "Blue defending"
                elif dist_red < dist_blue:
                    poss = "Red Team"
                    fact = "Red attacking" if ball['x'] < 0 else "Red defending"

                # 4. Continuous cluster penalty (replaces step function)
                _blue = [(b['x'], b['y']) for k, b in ents.items() if 'blue' in k]
                if len(_blue) >= 2:
                    _min_d = min(math.hypot(_blue[i][0]-_blue[j][0], _blue[i][1]-_blue[j][1])
                                 for i in range(len(_blue))
                                 for j in range(i+1, len(_blue)))
                    cluster_penalty = max(0, CLUSTER_REFERENCE_DIST - _min_d) * CLUSTER_GAIN
                    score -= cluster_penalty

                # 5. Continuous lane openness (replaces step function)
                # Each blue bot on the ball-to-goal line reduces the penalty proportionally.
                # No blockers = full penalty. More blockers = less penalty.
                if ball['x'] < 0:
                    _ratio = ball['x'] + 4.5
                    if _ratio > 0.01:
                        _blocker_score = 0.0
                        for _k, _b in ents.items():
                            if 'blue' not in _k:
                                continue
                            if _b['x'] < ball['x'] and _b['x'] > -4.5:
                                _expected_y = ball['y'] * (_b['x'] + 4.5) / _ratio
                                _dist_to_line = abs(_b['y'] - _expected_y)
                                # Each blocker contributes proportionally (closer to line = more)
                                _blocker_score += max(0, 1.0 - _dist_to_line / LANE_BLOCKER_BANDWIDTH)
                        # 0 blockers → full penalty, 1 blocker → half, 2+ → minimal
                        _lane_penalty = max(0, LANE_OPEN_GAIN - _blocker_score * LANE_OPEN_GAIN * 0.5)
                        score -= _lane_penalty

                # 6. Continuous pressing reward (proximity-based, stateless)
                pressing_reward = max(0, PRESSING_REFERENCE_DIST - dist_blue) * PRESSING_GAIN
                score += pressing_reward

                # 7. Continuous marking reward (conditional + proximity-based)
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

            # Clamp
            score = max(min(score, SCORE_MAX), SCORE_MIN)

            # Running Average
            self.score_samples_count += 1
            self.total_score_sum += score
            avg_score = self.total_score_sum / self.score_samples_count

            # Momentum
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
