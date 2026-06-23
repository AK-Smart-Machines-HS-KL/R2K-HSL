import sys
import termios
import tty
import select
import math
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from gazebo_msgs.srv import SetEntityState
from gazebo_msgs.msg import ModelStates

msg = """
ROS 2 Teleop & Dynamic Phantom Kicker (Controlling R1)
---------------------------------------
Moving around:
        w
   a         d
        x

s : KICK THE BALL (Dynamic power, max 40cm range)
space : force stop
CTRL-C to quit
"""

# Key bindings
moveBindings = {
    'w': (1.0, 0.0),
    'x': (-1.0, 0.0),
    'a': (0.0, 1.0),
    'd': (0.0, -1.0),
}

def getKey(settings, timeout=150.0):
    """Reads a keystroke without freezing the program, allowing ROS 2 to spin."""
    tty.setraw(sys.stdin.fileno())
    rlist, _, _ = select.select([sys.stdin], [], [], timeout)
    if rlist:
        key = sys.stdin.read(1)
    else:
        key = ''
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
    return key

class TeleopKicker(Node):
    def __init__(self):
        super().__init__('teleop_kicker_R1')
        
        # Publisher for R1
        self.vel_pub = self.create_publisher(Twist, '/R1/cmd_vel', 10)
        self.set_state_client = self.create_client(SetEntityState, '/gazebo/set_entity_state')
        
        self.create_subscription(ModelStates, '/gazebo/model_states', self.model_callback, 10)
        
        self.robot_pos = None
        self.ball_pos = None
        
        if not self.set_state_client.wait_for_service(timeout_sec=2.0):
            self.get_logger().warn('Gazebo set_entity_state service not found.')

    def model_callback(self, msg):
        try:
            if 'R1' in msg.name and 'soccer_ball' in msg.name:
                r_idx = msg.name.index('R1')
                b_idx = msg.name.index('soccer_ball')
                self.robot_pos = msg.pose[r_idx].position
                self.ball_pos = msg.pose[b_idx].position
        except ValueError:
            pass

    def kick_ball(self, current_linear_speed):
        if not self.set_state_client.service_is_ready():
            print("\n[Error] Gazebo service is not ready!\r")
            return

        if self.robot_pos is None or self.ball_pos is None:
            print("\n[Warning] Waiting for Gazebo model positions...\r")
            return

        # 1. Enforce Maximum Kick Distance
        dx = self.ball_pos.x - self.robot_pos.x
        dy = self.ball_pos.y - self.robot_pos.y
        distance = math.sqrt(dx**2 + dy**2)

        if distance > 0.4:
            print(f"\n[Miss] Ball is too far away! ({distance:.2f}m > 0.40m)\r")
            return

        # 2. Calculate Dynamic Kick Strength
        base_power = 3.0
        speed_multiplier = 8.0 
        
        bonus_power = max(0.0, current_linear_speed * speed_multiplier)
        total_kick_power = base_power + bonus_power

        request = SetEntityState.Request()
        request.state.name = 'soccer_ball' 
        request.state.reference_frame = 'R1' 
        
        # Spawn the ball slightly in front of R1 so it doesn't get stuck inside the mesh
        request.state.pose.position.x = 0.30 
        request.state.pose.position.y = 0.0
        request.state.pose.position.z = 0.10 
        
        request.state.twist.linear.x = total_kick_power  
        request.state.twist.linear.y = 0.0
        request.state.twist.linear.z = 0.5 
        
        future = self.set_state_client.call_async(request)
        future.add_done_callback(lambda f: self.kick_response_callback(f, total_kick_power))

    def kick_response_callback(self, future, power):
        try:
            response = future.result()
            if response.success:
                print(f"\n*** KICK EXECUTED! Power: {power:.1f} m/s ***\r")
            else:
                print(f"\n[GAZEBO ERROR]: {response.status_message}\r")
        except Exception as e:
            print(f"\n[SERVICE ERROR]: {e}\r")

def main():
    settings = termios.tcgetattr(sys.stdin)
    rclpy.init()
    node = TeleopKicker()
    
    speed = 0.5
    turn = 1.0
    x = 0.0
    th = 0.0

    print(msg)

    try:
        while True:
            rclpy.spin_once(node, timeout_sec=0)
            
            key = getKey(settings)
            
            if key == '':
                continue
            
            if key in moveBindings.keys():
                x = moveBindings[key][0]
                th = moveBindings[key][1]
                
                twist = Twist()
                twist.linear.x = x * speed
                twist.angular.z = th * turn
                node.vel_pub.publish(twist)

            elif key == 's':
                current_speed = x * speed 
                node.kick_ball(current_speed)
                
            elif key == ' ' or key == 'k':
                x = 0.0
                th = 0.0
                twist = Twist()
                node.vel_pub.publish(twist)
                
            else:
                if (key == '\x03'): # CTRL-C
                    break

    except Exception as e:
        print(f"Error: {e}")

    finally:
        twist = Twist()
        node.vel_pub.publish(twist)
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
