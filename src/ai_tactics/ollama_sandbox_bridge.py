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
                    if 'x' in task and 'y' in task:
                        self.targets[bot] = {'x': float(task['x']), 'y': float(task['y']), 'action': action}
                    else:
                        self.targets[bot] = {'action': action}
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
                
                if action == 'kick':
                    is_attacking = True
                    aim_yaw = math.atan2(0.0 - self.ball_pos.y, 4.5 - self.ball_pos.x)
                    behind_x, behind_y = self.ball_pos.x - math.cos(aim_yaw) * 0.6, self.ball_pos.y - math.sin(aim_yaw) * 0.6
                    dist_to_behind = math.hypot(behind_x - cx, behind_y - cy)
                    target_x, target_y = (behind_x, behind_y) if dist_to_behind > 0.3 and dist_to_ball > 0.5 else (self.ball_pos.x, self.ball_pos.y)
                else:
                    target_x, target_y = target.get('x', cx), target.get('y', cy)

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
