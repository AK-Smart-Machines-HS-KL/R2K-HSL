import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

class TripleMirror(Node):
    def __init__(self):
        super().__init__('triple_mirror')
        self.sub = self.create_subscription(Twist, '/blue_1/cmd_vel', self.cb, 10)
        self.pub_yahboom = self.create_publisher(Twist, '/bot1/cmd_vel', 10)
        self.pub_k1 = self.create_publisher(Twist, '/LocoApiTopicReq', 10)
        self.get_logger().info("🪞 Triple Mirror Online: Cloning blue_1 -> bot1 & k1_bot")

    def cb(self, msg):
        self.pub_yahboom.publish(msg)
        self.pub_k1.publish(msg)

def main():
    rclpy.init()
    node = TripleMirror()
    try: rclpy.spin(node)
    except KeyboardInterrupt: pass
    finally: node.destroy_node(); rclpy.shutdown()

if __name__ == '__main__':
    main()
