##!/usr/bin/env python3

import rclpy
from rclpy.node import Node
import math
import json
import uuid

# Import the vision and kicking messages
from detection.msg import DetectionMsgs
from brain.msg import Kick
from brain.msg import GoToBallAndKickCmd 

# Import the RPC message needed to start the vision service
from booster_msgs.msg import RpcReqMsg

class GoToBallAndKickNode(Node):
    def __init__(self):
        super().__init__('go_to_ball_and_kick_node')
        
        # 1. Parameter for the robot prefix (e.g., 'Kev1n')
        self.declare_parameter('robot_prefix', 'Booster')
        robot_prefix = self.get_parameter('robot_prefix').get_parameter_value().string_value
        
        # 2. State Variables
        self.is_active = False
        self.target_x = 0.0
        self.target_y = 0.0
        self.is_goalshot = False
        
        # 3. Subscriptions
        # Subscribe to the high-level command trigger
        cmd_topic = f'/{robot_prefix}/GoToBallAndKick'
        self.cmd_sub = self.create_subscription(
            GoToBallAndKickCmd,
            cmd_topic,
            self.command_callback,
            10
        )
        self.get_logger().info(f"Listening for commands on: {cmd_topic}")
        
        # Subscribe to the continuous YOLO visual feed
        self.vision_sub = self.create_subscription(
            DetectionMsgs,
            '/yolo_detection_server/detection_results',
            self.vision_callback,
            10  # Keep QoS history small so we only use fresh frames
        )
        
        # 4. Publishers
        self.kick_pub = self.create_publisher(Kick, '/kick_ball', 10)
        
        # Publisher to send the vision activation request
        self.vision_req_pub = self.create_publisher(RpcReqMsg, '/VisionApiTopicReq', 10)
        
        # 5. Startup Routine
        # Use a 1-second timer to ensure the publisher is registered with the ROS network 
        # before we try to send the activation command.
        self.startup_timer = self.create_timer(1.0, self.activate_yolo_network)

    def activate_yolo_network(self):
        """Sends the RPC request to start the YOLO vision service on startup."""
        
        # 1. Check if the YOLO server is actually listening yet
        if self.vision_req_pub.get_subscription_count() == 0:
            self.get_logger().warn("YOLO server not yet connected to our publisher. Waiting...")
            return # Let the timer trigger this function again in 1 second
            
        # 2. Once connected, cancel the timer so it only executes exactly once
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
        """Activates the kicking loop and updates the target parameters."""
        self.target_x = msg.target_x
        self.target_y = msg.target_y
        self.is_goalshot = msg.is_goalshot
        self.is_active = True
        
        mode = "GOALSHOT" if self.is_goalshot else "PASS"
        self.get_logger().info(
            f"Command Received! Mode: {mode} | Target: ({self.target_x}, {self.target_y}). "
            "Engaging visual tracking..."
        )

    def vision_callback(self, msg):
        """Processes YOLO data and publishes to /kick_ball continuously IF active."""
        if not self.is_active:
            return # Ignore visual data if we haven't been commanded to kick
            
        for obj in msg.objects:
            if obj.tag == 'sports ball':
                
                # Extract ball coordinates relative to the robot
                ball_x = float(obj.position[0])
                ball_y = float(obj.position[1])
                
                # Construct the continuous kick message
                kick_msg = Kick()
                kick_msg.header.stamp = self.get_clock().now().to_msg()
                kick_msg.header.frame_id = 'head_color_optical_frame'
                
                # Ball position
                kick_msg.x = ball_x
                kick_msg.y = ball_y
                kick_msg.dir = 0.0 # Standard forward-facing kick
                
                # Target positioning (where the ball should go)
                kick_msg.goal_x = self.target_x
                kick_msg.goal_y = self.target_y
                kick_msg.robot_theta_to_field = 0.0 
                
                # Calculate Power
                dist_to_target = math.sqrt((self.target_x - ball_x)**2 + (self.target_y - ball_y)**2)
                
                if self.is_goalshot:
                    # Max power logic derived from brain.cpp
                    kick_msg.power = 1.5 if dist_to_target > 6.0 else 6.0
                else:
                    # If it's just a pass (not a goalshot), you likely want a proportional/softer kick
                    # You can tune this multiplier based on your robot's physical strength
                    kick_msg.power = min(dist_to_target * 0.8, 4.0) 
                
                # Fire the command
                self.kick_pub.publish(kick_msg)
                
                # For debugging (you might want to comment this out to prevent terminal spam)
                self.get_logger().debug(f"Publishing kick -> Ball:({ball_x:.2f},{ball_y:.2f}) Power:{kick_msg.power:.1f}")
                
                # Break after finding the first sports ball to save processing
                break

def main(args=None):
    rclpy.init(args=args)
    node = GoToBallAndKickNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Shutting down GoToBallAndKick node.")
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
