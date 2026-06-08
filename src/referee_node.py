import rclpy
import json
from rclpy.node import Node
from std_msgs.msg import String

class RefereeNode(Node):
    def __init__(self):
        super().__init__('referee_node')
        self.sub = self.create_subscription(String, '/world_positions', self.pos_callback, 10)
        self.pub = self.create_publisher(String, '/match_state', 10)
        
        self.score_blue = 0
        self.score_red = 0
        self.ball_was_in_goal = False
        
        self.get_logger().info("⚖️  Referee V4 Online: Watching Goal Lines (X=+/- 4.5)")

    def pos_callback(self, msg):
        try:
            data = json.loads(msg.data)
            ball = data.get('entities', {}).get('soccer_ball')
            
            if ball:
                x = ball['x']
                # Tor-Erkennung
                if x > 4.5 and not self.ball_was_in_goal:
                    self.score_blue += 1
                    self.ball_was_in_goal = True
                    self.get_logger().info(f"⚽ GOAL FOR BLUE! Score: {self.score_blue}:{self.score_red}")
                elif x < -4.5 and not self.ball_was_in_goal:
                    self.score_red += 1
                    self.ball_was_in_goal = True
                    self.get_logger().info(f"⚽ GOAL FOR RED! Score: {self.score_blue}:{self.score_red}")
                elif -4.0 <= x <= 4.0:
                    # Reset, wenn der Ball wieder im Spielfeld ist
                    self.ball_was_in_goal = False

            # Zustand publizieren
            state = {"blue": self.score_blue, "red": self.score_red, "status": "playing"}
            out_msg = String()
            out_msg.data = json.dumps(state)
            self.pub.publish(out_msg)
            
        except Exception as e:
            self.get_logger().error(f"Referee Error: {e}")

def main():
    rclpy.init()
    node = RefereeNode()
    try: rclpy.spin(node)
    except KeyboardInterrupt: pass
    finally: node.destroy_node(); rclpy.shutdown()

if __name__ == '__main__':
    main()
