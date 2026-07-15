import rclpy
import json
import os
import time
from rclpy.node import Node
from std_msgs.msg import String

class StateAggregator(Node):
    def __init__(self):
        super().__init__('state_aggregator')
        self.create_subscription(String, '/world_positions', self.pos_cb, 10)
        self.create_subscription(String, '/match_state', self.match_cb, 10)
        self.create_subscription(String, '/tactical_score', self.score_cb, 10)
        self.create_subscription(String, '/tactical_reward', self.reward_cb, 10)
        
        # 10 Hz Schreib-Zyklus
        self.timer = self.create_timer(0.1, self.write_to_disk) 
        
        self.pos_data = {}
        self.match_data = {}
        self.score_data = {}
        self.reward_data = {}
        
        # FIX: Hier wurde der Pfad auf /workspace gesetzt!
        base_dir = os.getenv('ROS2K_WS', '.')
        self.file_path = os.path.join(base_dir, 'shared_state', 'Worldstate.json')
        
        # --- Phase 1 instrumentation: world-state trace logger ---
        self.run_id = os.getenv('R2K_RUN_ID', f"run_{int(time.time())}")
        self.log_dir = os.path.join(base_dir, 'logs')
        self.world_trace_path = os.path.join(self.log_dir, f"world_trace_{self.run_id}.jsonl")
        os.makedirs(self.log_dir, exist_ok=True)
        
        self.get_logger().info("📦 Aggregator V6 Online: Writing to Worldstate.json at 10 Hz")
        self.get_logger().info(f"📋 World trace: {self.world_trace_path}")

    def pos_cb(self, msg): self.pos_data = json.loads(msg.data)
    def match_cb(self, msg): self.match_data = json.loads(msg.data)
    def score_cb(self, msg): self.score_data = json.loads(msg.data)
    def reward_cb(self, msg): self.reward_data = json.loads(msg.data)

    def write_to_disk(self):
        if not self.pos_data: return # Warten auf erste echte Daten
        
        combined_state = self.pos_data.copy()
        combined_state['match_state'] = self.match_data
        combined_state['tactical_score'] = self.score_data
        if self.reward_data:
            combined_state['tactical_reward'] = self.reward_data
        
        try:
            # Atomares Schreiben verhindert "File in Use" Abstürze
            tmp_path = self.file_path + '.tmp'
            with open(tmp_path, 'w') as f:
                json.dump(combined_state, f)
            os.rename(tmp_path, self.file_path)
        except Exception:
            pass
        
        # --- Phase 1: world-state trace ---
        try:
            record = {
                "t": time.time(),
                "entities": combined_state.get("entities", {}),
                "match_state": combined_state.get("match_state", {}),
                "tactical_score": combined_state.get("tactical_score", {}),
            }
            with open(self.world_trace_path, 'a') as f:
                f.write(json.dumps(record) + "\n")
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
