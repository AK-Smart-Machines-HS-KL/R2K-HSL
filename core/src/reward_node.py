#!/usr/bin/env python3
import rclpy
import json
import time
import os
from rclpy.node import Node
from std_msgs.msg import String

class RewardNode(Node):
    def __init__(self):
        super().__init__('reward_node')
        self.sub_score = self.create_subscription(String, '/tactical_score', self.score_callback, 10)
        self.sub_match = self.create_subscription(String, '/match_state', self.match_callback, 10)
        self.pub_reward = self.create_publisher(String, '/tactical_reward', 10)
        
        self.current_score = 0.0
        self.score_before = None
        self.last_strategy_mtime = 0
        self.action_start_time = None
        self.pending_action = None
        self.strategy_path = 'shared_state/current_strategy.json'
        
        self.create_timer(1.0, self.tick)
        
        self.get_logger().info("🏆 Reward Node v6 Online: 1Hz · -10..+10 · Foul penalty -1")
    
    def score_callback(self, msg):
        try:
            data = json.loads(msg.data)
            self.current_score = data.get('current_numerical_score', 0.0)
        except Exception as e:
            self.get_logger().error(f"Score parse error: {e}")
    
    def match_callback(self, msg):
        try:
            data = json.loads(msg.data)
            if data.get('foul') and data['foul'].get('offender'):
                foul = data['foul']
                # Ball-out foul: smaller penalty (-0.5)
                if foul.get('type') == 'ball_out':
                    self._publish_foul_reward(foul, penalty=-0.5)
                else:
                    self._publish_foul_reward(foul, penalty=-1.0)
        except Exception as e:
            self.get_logger().error(f"Match state parse error: {e}")
    
    def _publish_foul_reward(self, foul_data, penalty=-1.0):
        reward_data = {
            "timestamp": time.time(),
            "source": "foul",
            "action_type": foul_data.get('type', 'unknown'),
            "target_x": None,
            "target_y": None,
            "score_before": self.current_score,
            "score_after": None,
            "reward": penalty,
            "classification": "negative",
            "bot_id": foul_data.get('offender', 'unknown')
        }
        msg = String()
        msg.data = json.dumps(reward_data)
        self.pub_reward.publish(msg)
        self.get_logger().info(f"Foul penalty: {foul_data.get('offender')} → reward {penalty:.1f}")
    
    def tick(self):
        try:
            if not os.path.exists(self.strategy_path):
                return
            
            current_mtime = os.path.getmtime(self.strategy_path)
            
            if current_mtime != self.last_strategy_mtime:
                self.last_strategy_mtime = current_mtime
                self.score_before = self.current_score
                self.action_start_time = time.time()
                
                try:
                    with open(self.strategy_path, 'r') as f:
                        strat_data = json.load(f)
                        if 'assignments' in strat_data:
                            for bot_id, action_data in strat_data['assignments'].items():
                                if action_data.get('action') == 'Move':
                                    self.pending_action = {
                                        'bot_id': bot_id,
                                        'target_x': action_data.get('x'),
                                        'target_y': action_data.get('y')
                                    }
                                    break
                                elif action_data.get('action') == 'Kick':
                                    self.pending_action = {
                                        'bot_id': bot_id,
                                        'target_x': None,
                                        'target_y': None
                                    }
                except Exception as e:
                    self.get_logger().error(f"Strategy parse error: {e}")
            
            if self.action_start_time and self.pending_action:
                elapsed = time.time() - self.action_start_time
                action_type = 'Move' if self.pending_action.get('target_x') is not None else 'Kick'
                timeout = 5.0 if action_type == 'Move' else 2.0
                
                if elapsed >= timeout:
                    score_after = self.current_score
                    reward = score_after - (self.score_before if self.score_before is not None else score_after)
                    
                    classification = "neutral"
                    if reward > 1.0: classification = "positive"
                    elif reward < -1.0: classification = "negative"
                    
                    reward_data = {
                        "timestamp": time.time(),
                        "source": "decision",
                        "action_type": action_type,
                        "target_x": self.pending_action.get('target_x'),
                        "target_y": self.pending_action.get('target_y'),
                        "score_before": round(self.score_before, 2) if self.score_before is not None else None,
                        "score_after": round(score_after, 2),
                        "reward": round(reward, 2),
                        "classification": classification,
                        "bot_id": self.pending_action.get('bot_id', 'unknown')
                    }
                    
                    msg = String()
                    msg.data = json.dumps(reward_data)
                    self.pub_reward.publish(msg)
                    self.get_logger().info(f"Decision reward: {reward_data['bot_id']} → reward {reward:.2f}")
                    
                    self.score_before = None
                    self.action_start_time = None
                    self.pending_action = None
        
        except Exception as e:
            self.get_logger().error(f"Tick error: {e}")

def main():
    rclpy.init()
    node = RewardNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()