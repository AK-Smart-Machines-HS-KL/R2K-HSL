#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PointStamped, Twist
from nav_msgs.msg import Odometry
import math

# --- CONFIGURATION ---
TARGET_ROBOT_ID = 1          # Wir steuern Roboter 1
STOP_DISTANCE = 0.6          # Stoppt 60cm vor dem Ball
MAX_LINEAR_SPEED = 0.5       
MAX_ANGULAR_SPEED = 2.0      
ANGULAR_KP = 2.0             

class Navigator(Node):
    def __init__(self):
        super().__init__('navigator')
        
        self.ball_pos = None
        self.robot_pose = None
        
        # SUBSCRIBERS
        self.create_subscription(PointStamped, '/shared_ball_position', self.ball_cb, 10)
        topic_odom = f'/robot{TARGET_ROBOT_ID}/odom'
        self.create_subscription(Odometry, topic_odom, self.odom_cb, 10)
        
        # PUBLISHER
        topic_cmd = f'/robot{TARGET_ROBOT_ID}/cmd_vel'
        self.cmd_pub = self.create_publisher(Twist, topic_cmd, 10)
        
        # CONTROL LOOP (10Hz)
        self.timer = self.create_timer(0.1, self.control_loop)
        self.get_logger().info(f"Navigator: Controlling Robot {TARGET_ROBOT_ID} to chase the ball.")

    def ball_cb(self, msg):
        self.ball_pos = (msg.point.x, msg.point.y)

    def odom_cb(self, msg):
        p = msg.pose.pose.position
        q = msg.pose.pose.orientation
        # Quaternion zu Yaw (Theta)
        theta = math.atan2(2*(q.w*q.z + q.x*q.y), 1-2*(q.y*q.y + q.z*q.z))
        self.robot_pose = (p.x, p.y, theta)

    def control_loop(self):
        cmd = Twist()
        
        # Safety: Haben wir Ball und Roboter Position?
        if self.ball_pos is None or self.robot_pose is None:
            self.cmd_pub.publish(cmd) # Stop
            return

        bx, by = self.ball_pos
        rx, ry, r_theta = self.robot_pose

        # 1. Fehler berechnen (Distanz & Winkel)
        dx = bx - rx
        dy = by - ry
        distance = math.sqrt(dx**2 + dy**2)
        target_angle = math.atan2(dy, dx)
        
        angle_error = target_angle - r_theta
        
        # Winkel normalisieren (-PI...PI)
        while angle_error > math.pi: angle_error -= 2 * math.pi
        while angle_error < -math.pi: angle_error += 2 * math.pi

        # 2. Steuerlogik
        if distance > STOP_DISTANCE:
            # Drehen zum Ball
            cmd.angular.z = angle_error * ANGULAR_KP
            
            # Limitieren
            cmd.angular.z = max(min(cmd.angular.z, MAX_ANGULAR_SPEED), -MAX_ANGULAR_SPEED)
            
            # Nur fahren, wenn wir grob in die richtige Richtung schauen
            if abs(angle_error) < 0.5: # ~30 Grad
                cmd.linear.x = MAX_LINEAR_SPEED
            else:
                cmd.linear.x = 0.0 # Erst auf der Stelle drehen
        else:
            # Nah genug -> Stopp (oder Kick)
            cmd.linear.x = 0.0
            cmd.angular.z = 0.0

        self.cmd_pub.publish(cmd)

def main(args=None):
    rclpy.init(args=args)
    node = Navigator()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        stop_cmd = Twist()
        node.cmd_pub.publish(stop_cmd)
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
