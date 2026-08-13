import rclpy
import json
import os
import math
import time
from rclpy.node import Node
from geometry_msgs.msg import Twist
from gazebo_msgs.msg import ModelStates
from gazebo_msgs.srv import SetEntityState
from rosgraph_msgs.msg import Clock

try:
    from booster_msgs.msg import RpcReqMsg
    HAS_BOOSTER_MSGS = True
except ImportError:
    HAS_BOOSTER_MSGS = False

# === Field dimensions (must match referee_node.py) ===
FIELD_HALF_LENGTH = 4.5   # X: [-4.5, +4.5]
FIELD_HALF_WIDTH  = 3.0   # Y: [-3.0, +3.0]
OWN_GOAL_X = -FIELD_HALF_LENGTH   # blue defends left goal

# === Goalie blending parameters (Phase 2a, tunable via trial-and-error) ===
# All distances are in % of field half-length (X) or half-width (Y) so the
# goalie logic scales with field size. Absolute meter values are derived at
# runtime via FIELD_HALF_LENGTH / FIELD_HALF_WIDTH.
# NOTE (Phase 5): these constants become obsolete once Phase 5.1 (Kalman
# filter) provides filtered positions + velocity. The bridge override is
# removed entirely and the LLM makes all goalie decisions with good data.
GOALIE_NEAR_GOAL_PCT = 0.22   # ball within 22% of half-length = full goal-line mode (~1.0m)
GOALIE_FAR_GOAL_PCT  = 0.89   # ball beyond 89% of half-length = full angle-block mode (~4.0m)
GOALIE_TACTICAL_WEIGHT = 0.7  # how much bridge overrides LLM target
GOALIE_LLM_WEIGHT      = 0.3  # how much LLM target is preserved
GOALIE_Y_DAMP_NEAR_PCT = 0.50 # Y-tracking dampening when ball near goal (fraction of half-width)
GOALIE_Y_DAMP_FAR_PCT  = 0.30 # Y-tracking dampening when ball far (fraction of half-width)
GOALIE_FORWARD_LIMIT_PCT = 0.56     # max forward X for small teams, as fraction of half-length from own goal (~-2.5m)
GOALIE_FORWARD_LIMIT_LARGE_PCT = 0.89  # max forward X for large teams (5vs5+, future), (~-4.0m)
GOALIE_DEADBAND_PCT = 0.022    # don't move if change < this (fraction of half-length, ~0.1m)
GOALIE_LINE_X_PCT = 0.96       # goal-line X as fraction of half-length from center (~-4.3m)


def smoothstep(t):
    """0 when t<=0, 1 when t>=1, S-curve between."""
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def get_yaw(q):
    siny_cosp = 2 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1 - 2 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)

class HalBridge(Node):
    def __init__(self):
        super().__init__('hal_bridge')
        self.pubs = {}
        self.targets = {} 
        
        script_dir = os.path.dirname(os.path.abspath(__file__))
        base_dir = os.path.dirname(script_dir)
        self.strategy_file = os.path.join(base_dir, 'shared_state', 'current_strategy.json')
        self.relay_file = os.path.join(base_dir, 'ai_tactics', 'active_relay.json')
        
        self.ball_pos = None
        self.hardware_mapping = {}
        self.last_kick_time = {}
        
        self.is_paused = False
        self.last_clock_val = 0.0
        self.last_clock_rcv_time = time.time()
        self.clock_ever_received = False # FIX 1: Verhindert falschen Pause-Modus beim Start!
        
        self.load_hardware_mapping()
        if not HAS_BOOSTER_MSGS:
            self.get_logger().warn("⚠️ booster_msgs nicht gefunden! K1 Hardware-Kontrolle ist deaktiviert.")

        self.create_subscription(ModelStates, '/gazebo/model_states', self.state_cb, 10)
        self.create_subscription(Clock, '/clock', self.clock_cb, 10)
        
        self.create_timer(0.5, self.read_llm_strategy)
        self.create_timer(0.2, self.check_pause_state)
        
        self.set_state_client = self.create_client(SetEntityState, '/gazebo/set_entity_state')
        self.get_logger().info(f"⚙️ HAL Bridge Online! Smarte Hardware-Übersetzung aktiv.")

    def load_hardware_mapping(self):
        if os.path.exists(self.relay_file):
            try:
                with open(self.relay_file, 'r') as f:
                    data = json.load(f)
                    self.hardware_mapping = data.get('mapping', {})
            except Exception as e:
                self.get_logger().error(f"Hardware Mapping Error: {e}")

    def clock_cb(self, msg):
        self.clock_ever_received = True # Uhr tickt, System lebt!
        current_clock = msg.clock.sec + msg.clock.nanosec * 1e-9
        if self.last_clock_val != current_clock:
            if self.is_paused:
                self.get_logger().info("▶️ Gazebo fortgesetzt. Hardware reaktiviert.")
            self.is_paused = False
            self.last_clock_val = current_clock
            self.last_clock_rcv_time = time.time()

    def check_pause_state(self):
        if not self.clock_ever_received: return # Blockiert nicht mehr beim Booten!
        
        if time.time() - self.last_clock_rcv_time > 0.4:
            if not self.is_paused:
                self.is_paused = True
                self.get_logger().warn("⏸️ Gazebo Pause erkannt! Stoppe Hardware...")
                self.stop_all_hardware()

    def stop_all_hardware(self):
        for hw_name, hw_info in self.hardware_mapping.items():
            hw_type = hw_info.get('hardware_type', 'virtual').lower()
            if hw_name not in self.pubs: continue
            try:
                if hw_type == 'k1' and HAS_BOOSTER_MSGS:
                    rpc = RpcReqMsg()
                    rpc.uuid = f"stop_{int(time.time()*1000)}"
                    rpc.header = json.dumps({"api_id": 2000}) 
                    rpc.body = json.dumps({"mode": 1})
                    self.pubs[hw_name].publish(rpc)
                elif hw_type == 'yahboom':
                    t = Twist()
                    self.pubs[hw_name].publish(t)
            except Exception as e:
                self.get_logger().error(f"Stop Error für {hw_name}: {e}")

    def read_llm_strategy(self):
        if not os.path.exists(self.strategy_file): return
        try:
            with open(self.strategy_file, 'r') as f:
                data = json.load(f)
                assignments = data.get('assignments', {})
                for bot, task in assignments.items():
                    action = task.get('action', '').lower()
                    role = task.get('role', '')
                    if 'x' in task and 'y' in task:
                        self.targets[bot] = {'x': float(task['x']), 'y': float(task['y']), 'action': action, 'role': role}
                    else:
                        self.targets[bot] = {'action': action, 'role': role}
        except Exception: pass

    def trigger_phantom_kick(self, bot_name, bot_yaw):
        current_time = time.time()
        if current_time - self.last_kick_time.get(bot_name, 0.0) < 2.0: return
        self.last_kick_time[bot_name] = current_time

        req = SetEntityState.Request()
        req.state.name = 'soccer_ball' 
        req.state.reference_frame = 'world'
        req.state.pose.position.x = self.ball_pos.x 
        req.state.pose.position.y = self.ball_pos.y
        req.state.pose.position.z = 0.10 
        
        kick_power = 6.0  
        req.state.twist.linear.x = math.cos(bot_yaw) * kick_power
        req.state.twist.linear.y = math.sin(bot_yaw) * kick_power
        req.state.twist.linear.z = 1.0 
        self.set_state_client.call_async(req)

    def state_cb(self, msg):
        if self.is_paused: return

        try:
            ball_idx = next((i for i, name in enumerate(msg.name) if 'ball' in name.lower()), None)
            if ball_idx is not None:
                self.ball_pos = msg.pose[ball_idx].position
            if not self.ball_pos: return

            for hw_name, hw_info in self.hardware_mapping.items():
                hw_type = hw_info.get('hardware_type', 'virtual').lower()
                topic = hw_info.get('topic', f'/{hw_name}/cmd_vel')
                target_bot = hw_info.get('mirror_of', hw_name)
                
                if target_bot not in self.targets: continue
                target = self.targets[target_bot]

                if hw_name not in self.pubs:
                    if hw_type == 'k1' and HAS_BOOSTER_MSGS:
                        self.pubs[hw_name] = self.create_publisher(RpcReqMsg, topic, 10)
                    else:
                        self.pubs[hw_name] = self.create_publisher(Twist, topic, 10)
                
                bot_idx = next((i for i, name in enumerate(msg.name) if target_bot in name.lower()), None)
                if bot_idx is None: continue
                    
                bot_pose = msg.pose[bot_idx]
                cx, cy = bot_pose.position.x, bot_pose.position.y
                cyaw = get_yaw(bot_pose.orientation)
                
                dist_to_ball = math.hypot(self.ball_pos.x - cx, self.ball_pos.y - cy)
                action = target.get('action', '').lower()
                is_attacking = False

                if action == 'hold':
                    continue  # explicit hold: bot keeps current position

                if action == 'kick':
                    is_attacking = True
                    # Role-aware kick direction: goalie kicks away from own goal
                    # (upfield toward opponent half), all other bots aim at
                    # opponent goal center (X=+4.5, Y=0).
                    if target.get('role', '') == 'goalie':
                        # Goalie clear: aim upfield, away from own goal (X=-4.5).
                        # Kick toward opponent half along ball-goal axis, biased
                        # toward nearest sideline to avoid red interceptors.
                        aim_yaw = math.atan2(-self.ball_pos.y * 0.5, 4.5 - self.ball_pos.x)
                    else:
                        aim_yaw = math.atan2(0.0 - self.ball_pos.y, 4.5 - self.ball_pos.x)
                    behind_x, behind_y = self.ball_pos.x - math.cos(aim_yaw) * 0.6, self.ball_pos.y - math.sin(aim_yaw) * 0.6
                    dist_to_behind = math.hypot(behind_x - cx, behind_y - cy)
                    target_x, target_y = (behind_x, behind_y) if dist_to_behind > 0.3 and dist_to_ball > 0.5 else (self.ball_pos.x, self.ball_pos.y)
                else:
                    target_x, target_y = target.get('x', cx), target.get('y', cy)

                # Goalie tactical blending (Approach C, Phase 2a)
                # NOTE (Phase 5): this block is removed once Phase 5.1 (Kalman
                # filter) gives the LLM filtered positions + velocity. The
                # bridge override becomes unnecessary.
                is_goalie = target.get('role', '') == 'goalie'
                if is_goalie and action != 'kick' and self.ball_pos:
                    # Derive absolute meter values from field dimensions
                    near_dist = GOALIE_NEAR_GOAL_PCT * FIELD_HALF_LENGTH
                    far_dist  = GOALIE_FAR_GOAL_PCT  * FIELD_HALF_LENGTH
                    deadband  = GOALIE_DEADBAND_PCT  * FIELD_HALF_LENGTH
                    line_x    = -(GOALIE_LINE_X_PCT * FIELD_HALF_LENGTH)
                    fwd_limit = -(GOALIE_FORWARD_LIMIT_PCT * FIELD_HALF_LENGTH)
                    damp_near = GOALIE_Y_DAMP_NEAR_PCT
                    damp_far  = GOALIE_Y_DAMP_FAR_PCT
                    y_clamp   = FIELD_HALF_WIDTH * 0.5

                    ball_dist_to_goal = math.hypot(self.ball_pos.x - OWN_GOAL_X, self.ball_pos.y)

                    # Smooth transition: 0 when ball near goal, 1 when ball far
                    far_weight = smoothstep((ball_dist_to_goal - near_dist) /
                                            (far_dist - near_dist))

                    # Goal-line position (ball near): stay at line_x, damped Y
                    goal_line_x = line_x
                    goal_line_y = max(-y_clamp, min(y_clamp, self.ball_pos.y * damp_near))

                    # Angle-block position (ball far): on ball-goal line, forward, damped Y
                    ratio = min(0.5, 2.0 / max(ball_dist_to_goal, 0.1))
                    angle_x = max(OWN_GOAL_X + (self.ball_pos.x - OWN_GOAL_X) * ratio, fwd_limit)
                    angle_y = self.ball_pos.y * damp_far

                    # Blend between goal-line (near) and angle-block (far)
                    tactical_x = goal_line_x * (1 - far_weight) + angle_x * far_weight
                    tactical_y = goal_line_y * (1 - far_weight) + angle_y * far_weight

                    # Blend: tactical correction + LLM's own target
                    target_x = tactical_x * GOALIE_TACTICAL_WEIGHT + target_x * GOALIE_LLM_WEIGHT
                    target_y = tactical_y * GOALIE_TACTICAL_WEIGHT + target_y * GOALIE_LLM_WEIGHT

                    # Deadband: don't issue movement if change < threshold
                    if math.hypot(target_x - cx, target_y - cy) < deadband:
                        target_x, target_y = cx, cy  # hold position

                dx, dy = target_x - cx, target_y - cy
                distance = math.hypot(dx, dy)
                target_yaw = math.atan2(dy, dx)
                angle_diff = target_yaw - cyaw
                
                while angle_diff > math.pi: angle_diff -= 2 * math.pi
                while angle_diff < -math.pi: angle_diff += 2 * math.pi
                
                lin_x, ang_z = 0.0, 0.0
                if is_attacking and dist_to_ball <= 0.4:
                    if hw_type == 'virtual': self.trigger_phantom_kick(target_bot, cyaw)
                else:
                    if distance > 0.15:
                        ang_z = max(min(angle_diff * 3.0, 2.5), -2.5)
                        lin_x = 0.8 if abs(angle_diff) < 0.5 else 0.2
                
                if hw_type == 'k1':
                    if not HAS_BOOSTER_MSGS: continue
                    rpc = RpcReqMsg()
                    rpc.uuid = f"cmd_{int(time.time()*1000)}"
                    if is_attacking and dist_to_ball <= 0.4:
                        rpc.header = json.dumps({"api_id": 2000}) 
                        rpc.body = json.dumps({"mode": 1})
                    else:
                        rpc.header = json.dumps({"api_id": 2001}) 
                        rpc.body = json.dumps({"vx": round(lin_x, 3), "vy": 0.0, "vyaw": round(ang_z, 3)})
                    self.pubs[hw_name].publish(rpc)
                else:
                    t = Twist()
                    t.linear.x = lin_x
                    t.angular.z = ang_z
                    self.pubs[hw_name].publish(t)
                    
        except Exception as e:
            self.get_logger().error(f"Bridge Execution Error: {e}")

def main():
    rclpy.init()
    node = HalBridge()
    try: rclpy.spin(node)
    except KeyboardInterrupt: pass
    finally: node.destroy_node(); rclpy.shutdown()

if __name__ == '__main__':
    main()
