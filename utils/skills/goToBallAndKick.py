#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
import math
import json
import uuid
import time

# Import the vision and kicking messages
from detection.msg import DetectionMsgs
from brain.msg import Kick
from brain.msg import GoToBallAndKickCmd 
from std_msgs.msg import Empty  # Built-in message for the manual stop button

# Import the RPC message needed to control services
from booster_msgs.msg import RpcReqMsg

class GoToBallAndKickNode(Node):
    def __init__(self):
        super().__init__('go_to_ball_and_kick_node')
        
        # 1. Parameters & State Variables
        self.declare_parameter('robot_prefix', 'Booster')
        self.robot_prefix = self.get_parameter('robot_prefix').get_parameter_value().string_value
        
        self.is_active = False
        self.target_x = 0.0
        self.target_y = 0.0
        self.is_goalshot = False
        
        # Tracking states for the automatic stop mechanism
        self.has_reached_ball = False
        self.last_time_ball_seen = 0.0
        
        # 2. Subscriptions
        cmd_topic = f'/{self.robot_prefix}/GoToBallAndKick'
        self.cmd_sub = self.create_subscription(
            GoToBallAndKickCmd, cmd_topic, self.command_callback, 10
        )
        
        # Manual cancel topic (uses built-in Empty message to avoid compile overhead)
        cancel_topic = f'/{self.robot_prefix}/CancelKick'
        self.cancel_sub = self.create_subscription(
            Empty, cancel_topic, self.manual_cancel_callback, 10
        )
        
        self.vision_sub = self.create_subscription(
            DetectionMsgs, '/yolo_detection_server/detection_results', self.vision_callback, 10  
        )
        
        # 3. Publishers
        self.kick_pub = self.create_publisher(Kick, '/kick_ball', 10)
        self.vision_req_pub = self.create_publisher(RpcReqMsg, '/VisionApiTopicReq', 10)
        self.loco_req_pub = self.create_publisher(RpcReqMsg, f'/LocoApiTopicReq', 10)
        
        self.get_logger().info(f"Node ready. Commands: {cmd_topic} | Manual Cancel: {cancel_topic}")
        
        # 4. Startup Routine
        self.startup_timer = self.create_timer(1.0, self.activate_yolo_network)

    def activate_yolo_network(self):
        """Polls for connection and handles YOLO activation."""
        if self.vision_req_pub.get_subscription_count() == 0:
            self.get_logger().warn("YOLO server not yet connected to our publisher. Waiting...")
            return
            
        self.startup_timer.cancel()
        self.get_logger().info("Sending request to activate YOLO Vision Service...")
        
        req_msg = RpcReqMsg()
        req_msg.uuid = str(uuid.uuid4())
        req_msg.header = json.dumps({"api_id": 3000}) 
        req_msg.body = json.dumps({
            "enable_position": True, 
            "enable_color": True, 
            "enable_face_detection": False
        })
        
        self.vision_req_pub.publish(req_msg)
        self.get_logger().info("✅ YOLO Vision Service activation request sent!")

    def command_callback(self, msg):
        """Activates the node and resets tracking milestones."""
        self.target_x = msg.target_x
        self.target_y = msg.target_y
        self.is_goalshot = msg.is_goalshot
        
        # Reset tracking flags for the new kick
        self.has_reached_ball = False
        self.last_time_ball_seen = time.time()
        self.is_active = True
        
        mode = "GOALSHOT" if self.is_goalshot else "PASS"
        self.get_logger().info(f"Command Received! Mode: {mode} -> Target: ({self.target_x}, {self.target_y})")

    def manual_cancel_callback(self, msg):
        """Hhalts tracking immediately and sends an abort to the leg hardware."""
        if not self.is_active:
            return
            
        self.is_active = False
        self.get_logger().warn("🛑 Manual cancel received! Halting stream...")
        
        # API ID 2038 with start: false terminates an active kick motion on the robot
        abort_msg = RpcReqMsg()
        abort_msg.uuid = str(uuid.uuid4())
        abort_msg.header = json.dumps({"api_id": 2038})
        abort_msg.body = json.dumps({"start": False, "version": 0})
        self.loco_req_pub.publish(abort_msg)
        self.get_logger().warn("🛑 Hardware leg swing abort request sent.")

    def vision_callback(self, msg):
        """Streams targets to /kick_ball and handles automatic completion tracking."""
        if not self.is_active:
            return
            
        ball_found_this_frame = False
        current_time = time.time()
        
        for obj in msg.objects:
            if obj.tag == 'sports ball':

                sound_msg = RpcReqMsg()
                sound_msg.uuid = str(uuid.uuid4())
                sound_msg.header = json.dumps({"api_id": 2020})
                sound_msg.body = json.dumps({"sound_file_path": "/home/booster/Workspace/sounds/kicking.wav"})
                self.loco_req_pub.publish(sound_msg)

                ball_found_this_frame = True
                self.last_time_ball_seen = current_time
                
                ball_x = float(obj.position[0])
                ball_y = float(obj.position[1])
                ball_range = math.sqrt(ball_x**2 + ball_y**2)
                
                # --- AUTOMATIC STOP LOGIC ---
                # Milestone 1: Has the robot successfully arrived at the ball?
                if ball_range < 0.45:
                    if not self.has_reached_ball:
                        self.get_logger().info("🎯 Robot reached the ball. Striking...")
                    self.has_reached_ball = True
                
                # Milestone 2: If we previously reached the ball, but it is now far away,
                # it means the ball was successfully kicked downfield. 
                if self.has_reached_ball and ball_range > 1.2:
                    self.get_logger().info(f"⚽ Kick complete! Ball cleared to distance: {ball_range:.2f}m. Stopping stream.")
                    self.is_active = False
                    return
                
                # --- CONSTRUCT & SEND TARGETS ---
                kick_msg = Kick()
                kick_msg.header.stamp = self.get_clock().now().to_msg()
                kick_msg.header.frame_id = 'head_color_optical_frame'
                kick_msg.x = ball_x
                kick_msg.y = ball_y
                kick_msg.dir = 0.0 
                kick_msg.goal_x = self.target_x
                kick_msg.goal_y = self.target_y
                kick_msg.robot_theta_to_field = 0.0 
                
                dist_to_target = math.sqrt((self.target_x - ball_x)**2 + (self.target_y - ball_y)**2)
                if self.is_goalshot:
                    kick_msg.power = 1.5 if dist_to_target > 6.0 else 6.0
                else:
                    kick_msg.power = min(dist_to_target * 0.8, 4.0) 
                
                self.kick_pub.publish(kick_msg)
                break
                
        # Milestone 3: Handle high-velocity kicks. If the robot strikes the ball hard, 
        # it can vanish from the camera frame instantly. If the ball vanishes for more 
        # than 0.6 seconds *after* the robot reached it, the kick is finished.
        if not ball_found_this_frame and self.has_reached_ball:
            if (current_time - self.last_time_ball_seen) > 0.6:
                self.get_logger().info("⚽ Ball moved out of visual frame post-strike. Stopping stream.")
                sound_msg = RpcReqMsg()
                sound_msg.uuid = str(uuid.uuid4())
                sound_msg.header = json.dumps({"api_id": 2020})
                sound_msg.body = json.dumps({"sound_file_path": "/home/booster/Workspace/sounds/done.wav"})
                self.loco_req_pub.publish(sound_msg)
                self.is_active = False

def main(args=None):
    rclpy.init(args=args)
    node = GoToBallAndKickNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Shutting down GoToBallAndKick node.")
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()
