import rclpy
import json
import os
from rclpy.node import Node
from std_msgs.msg import String

class StateAggregator(Node):
    def __init__(self):
        super().__init__('state_aggregator')
        self.create_subscription(String, '/world_positions', self.pos_cb, 10)
        self.create_subscription(String, '/match_state', self.match_cb, 10)
        self.create_subscription(String, '/tactical_score', self.score_cb, 10)
        
        # 10 Hz Schreib-Zyklus
        self.timer = self.create_timer(0.1, self.write_to_disk) 
        
        self.pos_data = {}
        self.match_data = {}
        self.score_data = {}
        
        # FIX: Hier wurde der Pfad auf /workspace gesetzt!
        base_dir = os.getenv('ROS2K_WS', '.')
        self.file_path = os.path.join(base_dir, 'shared_state', 'Worldstate.json')
        
        self.get_logger().info("📦 Aggregator V4 Online: Writing to Worldstate.json at 10 Hz")

    def pos_cb(self, msg): self.pos_data = json.loads(msg.data)
    def match_cb(self, msg): self.match_data = json.loads(msg.data)
    def score_cb(self, msg): self.score_data = json.loads(msg.data)

    def write_to_disk(self):
        if not self.pos_data: return # Warten auf erste echte Daten
        
        combined_state = self.pos_data.copy()
        combined_state['match_state'] = self.match_data
        combined_state['tactical_score'] = self.score_data
        
        try:
            # Atomares Schreiben verhindert "File in Use" Abstürze
            tmp_path = self.file_path + '.tmp'
            with open(tmp_path, 'w') as f:
                json.dump(combined_state, f)
            os.rename(tmp_path, self.file_path)
        except Exception:
            pass

def main(args=None):
    rclpy.init(args=args)
    node = StateAggregator()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()

if __name__ == '__main__':
    main()
