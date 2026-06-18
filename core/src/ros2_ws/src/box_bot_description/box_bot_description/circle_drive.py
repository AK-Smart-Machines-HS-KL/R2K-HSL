import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

class CircleDriver(Node):
    def __init__(self):
        super().__init__('circle_driver')
        
        # Create publishers specifically for box_bot1 and box_bot3
        self.pub1 = self.create_publisher(Twist, '/robot1/cmd_vel', 10)
        self.pub3 = self.create_publisher(Twist, '/robot3/cmd_vel', 10)
        
        # Timer to send commands at 2Hz (matches 0.5s interval)
        self.timer = self.create_timer(0.5, self.timer_callback)
        self.get_logger().info('Driving Robot 1 and Robot 3 in circles...')

    def timer_callback(self):
        msg = Twist()
        msg.linear.x = 0.5  # Move forward
        msg.angular.z = 0.5 # Turn left
        
        # Publish to bot 1 and bot 3
        self.pub1.publish(msg)
        self.pub3.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = CircleDriver()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
