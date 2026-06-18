import rclpy
import math
import time
from rclpy.node import Node
from geometry_msgs.msg import Twist
from gazebo_msgs.msg import ModelStates
from gazebo_msgs.srv import SetEntityState

def get_yaw(q):
    siny_cosp = 2 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1 - 2 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)

def clamp(val, min_val, max_val):
    return max(min_val, min(val, max_val))

class TeamRedEvaluator(Node):
    def __init__(self):
        super().__init__('rule_evaluator_red')
        self.pubs = {}
        self.ball_pos = None
        self.last_kick_time = {}
        
        self.create_subscription(ModelStates, '/gazebo/model_states', self.state_cb, 10)
        self.set_state_client = self.create_client(SetEntityState, '/gazebo/set_entity_state')
        self.get_logger().info("🔴 Team Red Online: Anti-Clustering, Staging & Precision Strike Active!")

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

            closest_bot = None
            min_dist_to_ball = float('inf')
            for name, pose in red_bots:
                dist = math.hypot(self.ball_pos.x - pose.position.x, self.ball_pos.y - pose.position.y)
                if dist < min_dist_to_ball:
                    min_dist_to_ball = dist
                    closest_bot = name

            supporter_assigned = False
            for name, pose in red_bots:
                if name not in self.pubs:
                    self.pubs[name] = self.create_publisher(Twist, f'/{name}/cmd_vel', 10)
                
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
                    
                    if dist_to_behind > 0.3 and dist_to_ball > 0.5:
                        target_x, target_y = behind_x, behind_y
                    else:
                        target_x, target_y = self.ball_pos.x, self.ball_pos.y
                
                elif not supporter_assigned:
                    target_x = 0.5 
                    target_y = 1.5 if self.ball_pos.y < 0 else -1.5
                    supporter_assigned = True
                    
                else:
                    target_x = 4.2
                    target_y = clamp(self.ball_pos.y * 0.5, -1.0, 1.0)

                target_x = clamp(target_x, -4.5, 4.5)
                target_y = clamp(target_y, -3.0, 3.0)

                dx = target_x - cx
                dy = target_y - cy
                angle_diff = math.atan2(dy, dx) - cyaw
                
                while angle_diff > math.pi: angle_diff -= 2 * math.pi
                while angle_diff < -math.pi: angle_diff += 2 * math.pi
                
                t = Twist()
                
                # --- WICHTIG: DIE NEUE SCHUSS-LOGIK ---
                if name == closest_bot and dist_to_ball <= 0.4:
                    # Berechne den Winkel zum Tor
                    aim_yaw = math.atan2(0.0 - self.ball_pos.y, -4.5 - self.ball_pos.x)
                    yaw_diff = aim_yaw - cyaw
                    
                    # Winkel normalisieren
                    while yaw_diff > math.pi: yaw_diff -= 2 * math.pi
                    while yaw_diff < -math.pi: yaw_diff += 2 * math.pi
                    
                    # Wenn die Abweichung kleiner als ~15 Grad (0.25 rad) ist -> KICK!
                    if abs(yaw_diff) < 0.25:
                        t.linear.x = 0.0
                        t.angular.z = 0.0
                        self.trigger_phantom_kick(name, cyaw)
                    else:
                        # Zu nah am Ball, aber nicht ausgerichtet! Auf der Stelle zum Tor drehen.
                        t.linear.x = 0.0
                        t.angular.z = clamp(yaw_diff * 4.0, -2.5, 2.5)
                # --------------------------------------
                else:
                    dist_to_target = math.hypot(dx, dy)
                    if dist_to_target > 0.1:
                        t.angular.z = clamp(angle_diff * 3.0, -2.5, 2.5)
                        if abs(angle_diff) < 0.5:
                            t.linear.x = 0.8 if name == closest_bot else 0.5
                        else:
                            t.linear.x = 0.2
                    else:
                        t.linear.x = 0.0
                        t.angular.z = 0.0
                    
                self.pubs[name].publish(t)
                
        except Exception as e:
            self.get_logger().error(f"Red Evaluator Error: {e}")

def main():
    rclpy.init()
    rclpy.spin(TeamRedEvaluator())
    rclpy.shutdown()

if __name__ == '__main__':
    main()
