import rclpy
import math
import time
import json
import random
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import String
from gazebo_msgs.msg import ModelStates
from gazebo_msgs.srv import SetEntityState

def get_yaw(q):
    siny_cosp = 2 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1 - 2 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)

def clamp(val, min_val, max_val):
    return max(min_val, min(val, max_val))

def smoothstep(t):
    t = clamp(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)

class TeamRedEvaluator(Node):
    def __init__(self):
        super().__init__('rule_evaluator_red')
        self.pubs = {}
        self.ball_pos = None
        self.last_kick_time = {}

        # Aggression factor for foul simulation (15% chance to approach opponent aggressively)
        self.AGGRESSION_FACTOR = 0.15

        # Match state tracking (referee decisions, freeze compliance)
        self.match_state = {}
        self.last_blue_score = 0

        # Per-bot hysteresis state (prevents threshold flickering)
        self.bot_states = {}

        self.create_subscription(ModelStates, '/gazebo/model_states', self.state_cb, 10)
        self.create_subscription(String, '/match_state', self.match_state_cb, 10)
        self.set_state_client = self.create_client(SetEntityState, '/gazebo/set_entity_state')
        self.get_logger().info("🔴 Team Red Online: Hysteresis, Freeze Compliance, Kick-in Awareness & Aggression Active!")

    def match_state_cb(self, msg):
        try:
            self.match_state = json.loads(msg.data)
        except:
            pass

    def _check_freeze(self):
        """Determine freeze status from match_state. Returns (all_red_frozen, frozen_bot_ids, context)."""
        status = self.match_state.get('status', 'playing')
        blue_score = self.match_state.get('blue', 0)

        red_conceded = blue_score > self.last_blue_score
        self.last_blue_score = blue_score

        all_red_frozen = False
        frozen_bots = set()
        ctx = {
            'status': status,
            'ball_out': status == 'ball_out',
            'restart_team': self.match_state.get('restart_team', ''),
            'kick_in_for_red': status == 'ball_out' and self.match_state.get('restart_team', '') == 'red',
            'kick_in_against_red': status == 'ball_out' and self.match_state.get('restart_team', '') == 'blue',
        }

        if status == 'goal' and red_conceded:
            all_red_frozen = True
        elif status == 'ball_out' and ctx['restart_team'] == 'blue':
            all_red_frozen = True
        elif status == 'foul_penalty':
            foul = self.match_state.get('foul', {})
            offender = foul.get('offender', '')
            if 'red' in offender:
                frozen_bots.add(offender)

        return all_red_frozen, frozen_bots, ctx

    def trigger_phantom_kick(self, bot_name, bot_yaw):
        if not self.set_state_client.service_is_ready():
            return

        current_time = time.time()
        if current_time - self.last_kick_time.get(bot_name, 0.0) < 2.0:
            return

        self.last_kick_time[bot_name] = current_time
        self.get_logger().info(f"💥 [{bot_name}] Executing Precision Phantom Kick!")

        request = SetEntityState.Request()
        request.state.name = 'soccer_ball'
        request.state.reference_frame = 'world'

        request.state.pose.position.x = self.ball_pos.x
        request.state.pose.position.y = self.ball_pos.y
        request.state.pose.position.z = 0.10

        kick_power = 5.0
        request.state.twist.linear.x = math.cos(bot_yaw) * kick_power
        request.state.twist.linear.y = math.sin(bot_yaw) * kick_power
        request.state.twist.linear.z = 1.0

        self.set_state_client.call_async(request)

    def smooth_membership(self, name, key, value, near, far, alpha=0.35):
        """Smooth 0..1 membership with low-pass filter.
        1.0 when value <= near, 0.0 when value >= far, S-curve between.
        The low-pass filter (alpha) damps rapid oscillation — implicit hysteresis
        without hard boolean flips."""
        bs = self.bot_states.setdefault(name, {})
        if value <= near:
            target = 1.0
        elif value >= far:
            target = 0.0
        else:
            t = (far - value) / (far - near)
            target = smoothstep(t)
        prev = bs.get(key, 0.0)
        smoothed = prev + (target - prev) * alpha
        bs[key] = smoothed
        return smoothed

    def state_cb(self, msg):
        try:
            ball_idx = next((i for i, name in enumerate(msg.name) if 'ball' in name.lower()), None)
            if ball_idx is not None:
                self.ball_pos = msg.pose[ball_idx].position

            if not self.ball_pos:
                return

            red_bots = []
            for i, name in enumerate(msg.name):
                if 'red_' in name:
                    red_bots.append((name, msg.pose[i]))

            if not red_bots:
                return

            # Check freeze status from referee match_state
            all_red_frozen, frozen_bots, ctx = self._check_freeze()

            closest_bot = None
            min_dist_to_ball = float('inf')
            for name, pose in red_bots:
                dist = math.hypot(self.ball_pos.x - pose.position.x, self.ball_pos.y - pose.position.y)
                if dist < min_dist_to_ball:
                    min_dist_to_ball = dist
                    closest_bot = name

            # Aggression: occasionally target nearest opponent (for foul simulation)
            blue_bots = []
            for i, name in enumerate(msg.name):
                if 'blue_' in name:
                    blue_bots.append((name, msg.pose[i]))

            aggression_active = random.random() < self.AGGRESSION_FACTOR

            supporter_assigned = False
            for name, pose in red_bots:
                if name not in self.pubs:
                    self.pubs[name] = self.create_publisher(Twist, f'/{name}/cmd_vel', 10)

                # Freeze gate: skip publishing if frozen (let referee's zero-twist take effect)
                if all_red_frozen:
                    continue
                if name in frozen_bots:
                    continue

                cx = pose.position.x
                cy = pose.position.y
                cyaw = get_yaw(pose.orientation)

                target_x, target_y = cx, cy
                dist_to_ball = math.hypot(self.ball_pos.x - cx, self.ball_pos.y - cy)

                if name == closest_bot:
                    aim_yaw = math.atan2(0.0 - self.ball_pos.y, -4.5 - self.ball_pos.x)

                    behind_x = self.ball_pos.x - math.cos(aim_yaw) * 0.6
                    behind_y = self.ball_pos.y - math.sin(aim_yaw) * 0.6
                    dist_to_behind = math.hypot(behind_x - cx, behind_y - cy)

                    # Smooth staging: 0.0 when close to ball, 1.0 when far (was: boolean staging)
                    stage_factor = self.smooth_membership(name, 'stage', dist_to_ball, 0.3, 0.5)
                    # Blend target: behind-ball when staging high, ball when staging low
                    target_x = behind_x * stage_factor + self.ball_pos.x * (1 - stage_factor)
                    target_y = behind_y * stage_factor + self.ball_pos.y * (1 - stage_factor)

                elif not supporter_assigned:
                    target_x = 0.5
                    target_y = 1.5 if self.ball_pos.y < 0 else -1.5
                    supporter_assigned = True

                else:
                    target_x = 4.2
                    target_y = clamp(self.ball_pos.y * 0.5, -1.0, 1.0)

                # Aggression logic: 15% chance to move toward nearest opponent
                if aggression_active and name != closest_bot and blue_bots:
                    nearest_blue = min(blue_bots, key=lambda b: math.hypot(b[1].position.x - cx, b[1].position.y - cy))
                    blue_x, blue_y = nearest_blue[1].position.x, nearest_blue[1].position.y
                    blue_dist = math.hypot(blue_x - cx, blue_y - cy)
                    if blue_dist < 3.0:
                        # 50% chance: blocking (position between blue and ball)
                        # 50% chance: pushing (move directly toward blue)
                        if random.random() < 0.5:
                            target_x = (blue_x + self.ball_pos.x) / 2.0
                            target_y = (blue_y + self.ball_pos.y) / 2.0
                        else:
                            target_x = blue_x + (cx - blue_x) * 0.3
                            target_y = blue_y + (cy - blue_y) * 0.3

                # Kick-in behavior override during ball_out
                if ctx['kick_in_against_red']:
                    # Blue has the restart — red plays defensively, hold midfield, close pass lanes
                    if name != closest_bot:
                        target_x = 2.0
                        target_y = clamp(self.ball_pos.y * 0.7, -2.0, 2.0)
                elif ctx['kick_in_for_red'] and name == closest_bot:
                    # Red has the restart — approach ball from behind for kick-in
                    target_x, target_y = behind_x, behind_y

                # Anti-clustering: maintain 1.5m minimum distance between red bots
                if name != closest_bot and len(red_bots) > 1:
                    for other_name, other_pose in red_bots:
                        if other_name == name or other_name == closest_bot:
                            continue
                        red_dist = math.hypot(cx - other_pose.position.x, cy - other_pose.position.y)
                        if red_dist < 1.5:
                            if cy >= other_pose.position.y:
                                target_y = max(target_y, other_pose.position.y + 1.5)
                            else:
                                target_y = min(target_y, other_pose.position.y - 1.5)
                            break

                # Boundary tolerance: 0.5m outside for turning back
                target_x = clamp(target_x, -5.0, 5.0)
                target_y = clamp(target_y, -3.5, 3.5)

                dx = target_x - cx
                dy = target_y - cy
                angle_diff = math.atan2(dy, dx) - cyaw

                while angle_diff > math.pi: angle_diff -= 2 * math.pi
                while angle_diff < -math.pi: angle_diff += 2 * math.pi

                t = Twist()

                # --- PRECISION SHOT LOGIC (smooth blended) ---
                if name == closest_bot:
                    # Smooth kick zone: 1.0 when dist < 0.3, 0.0 when dist > 0.6, S-curve between
                    kick_factor = self.smooth_membership(name, 'kick', dist_to_ball, 0.3, 0.6)

                    if kick_factor > 0.5:
                        aim_yaw = math.atan2(0.0 - self.ball_pos.y, -4.5 - self.ball_pos.x)
                        yaw_diff = aim_yaw - cyaw

                        while yaw_diff > math.pi: yaw_diff -= 2 * math.pi
                        while yaw_diff < -math.pi: yaw_diff += 2 * math.pi

                        # Smooth alignment: 1.0 when yaw_diff < 0.15, 0.0 when > 0.35
                        align_factor = self.smooth_membership(name, 'align', abs(yaw_diff), 0.15, 0.35)

                        # Kick readiness: both closeness AND alignment must be high
                        kick_readiness = kick_factor * align_factor
                        if kick_readiness > 0.85:
                            t.linear.x = 0.0
                            t.angular.z = 0.0
                            self.trigger_phantom_kick(name, cyaw)
                        else:
                            # Rotate toward goal; angular speed reduces smoothly as alignment improves
                            t.linear.x = (1 - kick_factor) * 0.3
                            t.angular.z = clamp(yaw_diff * 4.0 * (1 - align_factor * 0.5), -2.5, 2.5)
                    else:
                        # Not in kick zone — normal movement with smooth deceleration near ball
                        dist_to_target = math.hypot(dx, dy)
                        # Smooth stop: 1.0 when at target (dist < 0.05), 0.0 when far (dist > 0.15)
                        stop_factor = self.smooth_membership(name, 'stop', dist_to_target, 0.05, 0.15)
                        # Smooth course: 1.0 when aligned (angle_diff < 0.3), 0.0 when misaligned (> 0.7)
                        course_factor = self.smooth_membership(name, 'course', abs(angle_diff), 0.3, 0.7)

                        t.angular.z = clamp(angle_diff * 3.0, -2.5, 2.5)
                        base_speed = 0.8
                        t.linear.x = (1 - stop_factor) * (0.2 + course_factor * 0.6) * base_speed
                # ----------------------------------------------
                else:
                    # Non-striker movement with smooth speed control
                    dist_to_target = math.hypot(dx, dy)
                    stop_factor = self.smooth_membership(name, 'stop', dist_to_target, 0.05, 0.15)
                    course_factor = self.smooth_membership(name, 'course', abs(angle_diff), 0.3, 0.7)

                    t.angular.z = clamp(angle_diff * 3.0, -2.5, 2.5)
                    base_speed = 0.5
                    t.linear.x = (1 - stop_factor) * (0.2 + course_factor * 0.6) * base_speed

                self.pubs[name].publish(t)

        except Exception as e:
            self.get_logger().error(f"Red Evaluator Error: {e}")

def main():
    rclpy.init()
    rclpy.spin(TeamRedEvaluator())
    rclpy.shutdown()

if __name__ == '__main__':
    main()