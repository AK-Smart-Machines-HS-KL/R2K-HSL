import rclpy
from rclpy.node import Node
from gazebo_msgs.msg import ModelStates
from std_msgs.msg import String
import json
import time

class WorldModelTracker(Node):
    def __init__(self):
        super().__init__('r2k_world_tracker')
        
        # INPUT: Gazebo Ground Truth
        self.subscription = self.create_subscription(
            ModelStates,
            '/gazebo/model_states',
            self.listener_callback,
            10
        )
        
        # OUTPUT REALTIME: Reine In-Memory Datenautobahn
        self.publisher_ = self.create_publisher(
            String, 
            '/world_positions', 
            10
        )
        
        self.get_logger().info("👁️ Tracker V4 Online: Pure Realtime Topic [/world_positions] (Zero File I/O)")

    def listener_callback(self, msg):
        entities = {}
        
        for i, name in enumerate(msg.name):
            if name.startswith('blue_') or name.startswith('red_') or name == 'soccer_ball':
                pos = msg.pose[i].position
                entities[name] = {
                    "x": round(pos.x, 3),
                    "y": round(pos.y, 3)
                }

        if entities:
            world_state = {
                "entities": entities,
                "sys_time": time.time()
            }
            
            ros_msg = String()
            ros_msg.data = json.dumps(world_state)
            self.publisher_.publish(ros_msg)

def main(args=None):
    rclpy.init(args=args)
    tracker = WorldModelTracker()
    try:
        rclpy.spin(tracker)
    except KeyboardInterrupt:
        pass
    finally:
        tracker.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
