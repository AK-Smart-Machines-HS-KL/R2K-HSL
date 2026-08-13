import rclpy
import json
import os
import math
import time
from rclpy.node import Node
from std_msgs.msg import String
from collections import deque

# === Named module constants — ALL continuous, NO step thresholds ===
BALL_POSITION_GAIN = 0.8
SCORE_MIN = -10.0
SCORE_MAX = 10.0
MOMENTUM_WINDOW_SIZE = 300
MOMENTUM_MIN_SAMPLES = 10
MOMENTUM_SCALE_FACTOR = 10.0

# === Continuous possession (replaces step-function possession) ===
# max(0, REFERENCE - dist) * GAIN — proportional, no threshold
# Widened from 2.0 to 4.5 (half-field) so the possession term competes
# with the ball-position gain. At dist=0: +4.5, dist=2: +2.5, dist=4.5: 0.0
POSSESSION_GAIN = 1.0
POSSESSION_REFERENCE_DIST = 4.5

# === Goal event bonus (edge-triggered on score increment) ===
# Makes the score event-aware at the most important moment.
# Blue scoring → +GOAL_BONUS, Red scoring → -GOAL_BONUS.
GOAL_BONUS = 3.0

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
        self.sub_match = self.create_subscription(String, '/match_state', self.match_cb, 10)
        self.pub = self.create_publisher(String, '/tactical_score', 10)

        self.total_score_sum = 0.0
        self.score_samples_count = 0

        self.momentum_window = deque(maxlen=MOMENTUM_WINDOW_SIZE)

        self.match_data = {}
        self.prev_score_blue = 0
        self.prev_score_red = 0
        self.last_score = 0.0
        self.goal_bonus_applied = False  # flag to prevent double-application

        self.get_logger().info("Scorer V7e Online: match-state-aware score formula")

    def match_cb(self, msg):
        try:
            new_data = json.loads(msg.data)

            # --- Suggestion 2: Goal event bonus (edge-triggered) ---
            # Applied HERE (in match_cb) so the bonus fires immediately when the
            # referee announces the goal. Also checked in pos_callback as a fallback
            # in case pos_callback fires before match_cb (ROS 2 callback ordering
            # is not guaranteed). The goal_bonus_applied flag prevents double-application.
            cur_blue = new_data.get("blue", 0)
            cur_red = new_data.get("red", 0)
            if not self.goal_bonus_applied:
                if cur_blue > self.prev_score_blue:
                    self.last_score = max(min(self.last_score + GOAL_BONUS, SCORE_MAX), SCORE_MIN)
                    self.goal_bonus_applied = True
                    self.get_logger().info(f"⚽ Goal bonus (match_cb): Blue +{GOAL_BONUS}")
                if cur_red > self.prev_score_red:
                    self.last_score = max(min(self.last_score - GOAL_BONUS, SCORE_MAX), SCORE_MIN)
                    self.goal_bonus_applied = True
                    self.get_logger().info(f"⚽ Goal bonus (match_cb): Red -{GOAL_BONUS}")
            self.prev_score_blue = cur_blue
            self.prev_score_red = cur_red

            self.match_data = new_data
        except Exception as e:
            self.get_logger().error(f"Match state parse error: {e}")

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
            self.prev_score_blue = 0
            self.prev_score_red = 0
            self.last_score = 0.0
            self.goal_bonus_applied = False
            try:
                os.remove(RESET_FLAG)
            except OSError:
                pass
            self.get_logger().info("Reset flag detected — clearing momentum + score state")

    def pos_callback(self, msg):
        try:
            self._check_reset()

            data = json.loads(msg.data)
            ents = data.get('entities', {})
            ball = ents.get('soccer_ball')

            # --- Suggestion 1: Gate by match_state.status ---
            # During non-playing phases (goal, ball_out, set-piece), the ball is at
            # a referee-set position that does not reflect gameplay. Freeze the score.
            status = self.match_data.get("status", "playing")
            if status != "playing":
                score = self.last_score
            else:
                # Reset the goal bonus flag when playing resumes
                self.goal_bonus_applied = False
                score = self._compute_position_score(ents, ball)

            # --- Suggestion 2 fallback: Goal bonus in pos_callback ---
            # If match_cb hasn't fired yet (ROS 2 callback ordering), apply the bonus here.
            if not self.goal_bonus_applied:
                cur_blue = self.match_data.get("blue", 0)
                cur_red = self.match_data.get("red", 0)
                if cur_blue > self.prev_score_blue:
                    score += GOAL_BONUS
                    self.goal_bonus_applied = True
                    self.get_logger().info(f"⚽ Goal bonus (pos_cb): Blue +{GOAL_BONUS}")
                if cur_red > self.prev_score_red:
                    score -= GOAL_BONUS
                    self.goal_bonus_applied = True
                    self.get_logger().info(f"⚽ Goal bonus (pos_cb): Red -{GOAL_BONUS}")
                self.prev_score_blue = cur_blue
                self.prev_score_red = cur_red

            # Clamp
            score = max(min(score, SCORE_MAX), SCORE_MIN)
            self.last_score = score

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
                "fact_label": self._fact_label(ents, ball),
                "ball_possession_fact": self._poss_label(ents, ball)
            }
            out_msg = String()
            out_msg.data = json.dumps(out_data)
            self.pub.publish(out_msg)

        except Exception as e:
            self.get_logger().error(f"Scorer Error: {e}")

    def _compute_position_score(self, ents, ball):
        """Compute the position-based tactical score (suggestions 3-7)."""
        score = 0.0

        if ball:
            # 1. Ball position (continuous, unscaled)
            # The status gate (Suggestion 1) prevents anti-correlated deltas during
            # ball resets — the ball position term itself doesn't need possession scaling.
            score += ball['x'] * BALL_POSITION_GAIN

            # 2. Distances
            dist_blue = min([math.hypot(b['x']-ball['x'], b['y']-ball['y'])
                             for k, b in ents.items() if 'blue' in k], default=99)
            dist_red = min([math.hypot(b['x']-ball['x'], b['y']-ball['y'])
                            for k, b in ents.items() if 'red' in k], default=99)

            # 3. Continuous possession (replaces step function)
            blue_poss = max(0, POSSESSION_REFERENCE_DIST - dist_blue) * POSSESSION_GAIN
            red_poss = max(0, POSSESSION_REFERENCE_DIST - dist_red) * POSSESSION_GAIN
            score += blue_poss - red_poss

            # 4. Continuous cluster penalty (replaces step function)
            _blue = [(b['x'], b['y']) for k, b in ents.items() if 'blue' in k]
            if len(_blue) >= 2:
                _min_d = min(math.hypot(_blue[i][0]-_blue[j][0], _blue[i][1]-_blue[j][1])
                             for i in range(len(_blue))
                             for j in range(i+1, len(_blue)))
                cluster_penalty = max(0, CLUSTER_REFERENCE_DIST - _min_d) * CLUSTER_GAIN
                score -= cluster_penalty

            # 5. Continuous lane openness (replaces step function)
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
                            _blocker_score += max(0, 1.0 - _dist_to_line / LANE_BLOCKER_BANDWIDTH)
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

        return score

    def _fact_label(self, ents, ball):
        if not ball:
            return "Neutral Game"
        dist_blue = min([math.hypot(b['x']-ball['x'], b['y']-ball['y'])
                         for k, b in ents.items() if 'blue' in k], default=99)
        dist_red = min([math.hypot(b['x']-ball['x'], b['y']-ball['y'])
                        for k, b in ents.items() if 'red' in k], default=99)
        if dist_blue < dist_red:
            return "Blue attacking" if ball['x'] > 0 else "Blue defending"
        elif dist_red < dist_blue:
            return "Red attacking" if ball['x'] < 0 else "Red defending"
        return "Neutral Game"

    def _poss_label(self, ents, ball):
        if not ball:
            return "Contested"
        dist_blue = min([math.hypot(b['x']-ball['x'], b['y']-ball['y'])
                         for k, b in ents.items() if 'blue' in k], default=99)
        dist_red = min([math.hypot(b['x']-ball['x'], b['y']-ball['y'])
                        for k, b in ents.items() if 'red' in k], default=99)
        if dist_blue < dist_red:
            return "Blue Team"
        elif dist_red < dist_blue:
            return "Red Team"
        return "Contested"

def main():
    rclpy.init()
    node = ScoreNode()
    try: rclpy.spin(node)
    except KeyboardInterrupt: pass
    finally: node.destroy_node(); rclpy.shutdown()

if __name__ == '__main__':
    main()
