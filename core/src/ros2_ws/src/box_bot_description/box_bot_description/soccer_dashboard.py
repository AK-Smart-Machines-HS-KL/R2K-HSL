#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan
from gazebo_msgs.msg import ModelStates
import cv2
import numpy as np
import math
import time

# --- CONFIGURATION ---
FIELD_WIDTH_M = 14.0
FIELD_HEIGHT_M = 10.0
SCALE = 60
WINDOW_WIDTH = int(FIELD_WIDTH_M * SCALE)
WINDOW_HEIGHT = int(FIELD_HEIGHT_M * SCALE)
DASHBOARD_HEIGHT = 160

# SENSOR CONFIG
MAX_SENSOR_RANGE = 2.5     
FOV_ANGLE = 180            
CONSENSUS_THRESHOLD = 1.5  
SMOOTHING_FACTOR = 0.2     

# FILTERS
SAFE_X = 6.5  
SAFE_Y = 4.5  
TEAMMATE_RADIUS = 0.4 
MAX_OBJ_WIDTH = 0.35 # Objects wider than 35cm are ignored (Ball is ~22cm)

# COLORS
COLOR_FIELD = (0, 100, 0)
COLOR_LINES = (255, 255, 255)
COLOR_GT_BALL = (255, 255, 255) 
COLOR_CONFIDENCE_3 = (0, 255, 0)       
COLOR_CONFIDENCE_2 = (0, 165, 255)     
COLOR_CONFIDENCE_1 = (0, 69, 255)      
COLOR_LOST         = (0, 0, 150)       
COLOR_ROBOTS       = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
COLOR_FOV          = (0, 255, 255)     

class SoccerDashboard(Node):
    def __init__(self):
        super().__init__('soccer_dashboard')
        
        self.robot_poses = [None, None, None]      
        self.ball_estimates = [None, None, None]   
        self.ball_gt = None                        
        self.smoothed_ball_pos = None
        self.last_known_ball_pos = None
        
        # SUBSCRIBERS
        self.create_subscription(Odometry, '/robot1/odom', lambda m: self.odom_cb(m, 0), 10)
        self.create_subscription(Odometry, '/robot2/odom', lambda m: self.odom_cb(m, 1), 10)
        self.create_subscription(Odometry, '/robot3/odom', lambda m: self.odom_cb(m, 2), 10)
        self.create_subscription(LaserScan, '/robot1/scan', lambda m: self.scan_cb(m, 0), 10)
        self.create_subscription(LaserScan, '/robot2/scan', lambda m: self.scan_cb(m, 1), 10)
        self.create_subscription(LaserScan, '/robot3/scan', lambda m: self.scan_cb(m, 2), 10)
        self.create_subscription(ModelStates, '/gazebo/model_states', self.model_states_cb, 10)

        self.timer = self.create_timer(0.05, self.draw_dashboard)
        self.get_logger().info("Dashboard: SIZE FILTER ENABLED (Max Width: 0.35m)")

    def odom_cb(self, msg, robot_id):
        p = msg.pose.pose.position
        q = msg.pose.pose.orientation
        theta = math.atan2(2*(q.w*q.z + q.x*q.y), 1-2*(q.y*q.y + q.z*q.z))
        self.robot_poses[robot_id] = (p.x, p.y, theta)

    def scan_cb(self, msg, robot_id):
        if self.robot_poses[robot_id] is None: return

        ranges = np.array(msg.ranges)
        # Pre-cleaning
        ranges[ranges == float('inf')] = 100.0
        ranges[ranges < 0.2] = 100.0 

        # 1. SOFTWARE BLIND SPOT (180 deg)
        num_readings = len(ranges)
        angles = np.linspace(msg.angle_min, msg.angle_max, num_readings)
        limit = math.radians(FOV_ANGLE / 2)
        blind_mask = (angles > limit) | (angles < -limit)
        ranges[blind_mask] = 100.0

        # 2. FIND CLOSEST OBJECT
        min_idx = np.argmin(ranges)
        min_dist = ranges[min_idx]

        self.ball_estimates[robot_id] = None # Reset

        if min_dist < MAX_SENSOR_RANGE:
            # --- 3. SIZE FILTER (New!) ---
            # Expand left and right to find how "wide" this object is
            # We look for contiguous points that are at roughly the same depth (+/- 0.2m)
            
            start_idx = min_idx
            while start_idx > 0 and abs(ranges[start_idx] - ranges[start_idx-1]) < 0.2:
                start_idx -= 1
            
            end_idx = min_idx
            while end_idx < num_readings - 1 and abs(ranges[end_idx] - ranges[end_idx+1]) < 0.2:
                end_idx += 1
            
            # Calculate Arc Width = Distance * AngleSpan
            # AngleSpan = (IndexCount) * AngleIncrement
            angular_width = (end_idx - start_idx) * msg.angle_increment
            physical_width = min_dist * angular_width

            if physical_width > MAX_OBJ_WIDTH:
                # self.get_logger().info(f"R{robot_id} ignored object width: {physical_width:.2f}m")
                return # IGNORE: Too wide to be a ball

            # --- PROCESS VALID CANDIDATE ---
            found_angle = angles[min_idx]
            rx, ry, r_theta = self.robot_poses[robot_id]
            
            obj_x = rx + min_dist * math.cos(r_theta + found_angle)
            obj_y = ry + min_dist * math.sin(r_theta + found_angle)
            
            # --- 4. WALL FILTER ---
            if not ((-SAFE_X < obj_x < SAFE_X) and (-SAFE_Y < obj_y < SAFE_Y)):
                return 
            
            # --- 5. TEAMMATE FILTER (Safety net) ---
            is_teammate = False
            for i, pose in enumerate(self.robot_poses):
                if pose and i != robot_id:
                    dist_to_mate = math.sqrt((obj_x - pose[0])**2 + (obj_y - pose[1])**2)
                    if dist_to_mate < TEAMMATE_RADIUS:
                        is_teammate = True
                        break 
            
            if not is_teammate:
                self.ball_estimates[robot_id] = (obj_x, obj_y)

    def model_states_cb(self, msg):
        for i, name in enumerate(msg.name):
            if 'ball' in name.lower() or 'sphere' in name.lower():
                self.ball_gt = (msg.pose[i].position.x, msg.pose[i].position.y)
                return

    def world_to_pixel(self, x, y):
        px = int((x * SCALE) + (WINDOW_WIDTH / 2))
        py = int((-y * SCALE) + (WINDOW_HEIGHT / 2))
        return px, py

    def get_consensus_ball(self):
        valid_ests = [p for p in self.ball_estimates if p is not None]
        count = len(valid_ests)
        final_pos = None; color = COLOR_LOST; status_text = "LOST"
        is_live_data = False

        if count == 0:
            self.smoothed_ball_pos = None 
            if self.last_known_ball_pos:
                final_pos = self.last_known_ball_pos
                status_text = "LOST (Last Known)"
                is_live_data = False
            else:
                status_text = "SEARCHING..."
        else:
            is_live_data = True
            avg_x = sum([p[0] for p in valid_ests]) / count
            avg_y = sum([p[1] for p in valid_ests]) / count
            target_pos = (avg_x, avg_y)

            if self.smoothed_ball_pos is None: self.smoothed_ball_pos = target_pos
            else:
                sx = self.smoothed_ball_pos[0] * (1 - SMOOTHING_FACTOR) + target_pos[0] * SMOOTHING_FACTOR
                sy = self.smoothed_ball_pos[1] * (1 - SMOOTHING_FACTOR) + target_pos[1] * SMOOTHING_FACTOR
                self.smoothed_ball_pos = (sx, sy)

            final_pos = self.smoothed_ball_pos
            self.last_known_ball_pos = final_pos

            agreed = True
            for p in valid_ests:
                if math.sqrt((p[0]-avg_x)**2 + (p[1]-avg_y)**2) > CONSENSUS_THRESHOLD: agreed = False
            
            if count == 3 and agreed: color = COLOR_CONFIDENCE_3; status_text = "HIGH PRECISION"
            elif count == 2 and agreed: color = COLOR_CONFIDENCE_2; status_text = "CONFIRMED (2 BOTS)"
            elif count == 1: color = COLOR_CONFIDENCE_1; status_text = "SINGLE SOURCE"
            else: color = COLOR_CONFIDENCE_1; status_text = "CONFLICTING DATA"

        return final_pos, color, status_text, is_live_data

    def draw_dashboard(self):
        img = np.zeros((WINDOW_HEIGHT + DASHBOARD_HEIGHT, WINDOW_WIDTH, 3), dtype=np.uint8)
        
        cv2.rectangle(img, (0, 0), (WINDOW_WIDTH, WINDOW_HEIGHT), COLOR_FIELD, -1)
        cx, cy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2
        cv2.line(img, (cx, 0), (cx, WINDOW_HEIGHT), COLOR_LINES, 2)
        cv2.circle(img, (cx, cy), int(0.75 * SCALE), COLOR_LINES, 2)
        
        sx_min, sy_min = self.world_to_pixel(-SAFE_X, -SAFE_Y)
        sx_max, sy_max = self.world_to_pixel(SAFE_X, SAFE_Y)
        cv2.rectangle(img, (sx_min, sy_min), (sx_max, sy_max), (0, 150, 0), 1)

        overlay = img.copy()
        for i, pose in enumerate(self.robot_poses):
            if pose:
                px, py = self.world_to_pixel(pose[0], pose[1])
                radius = int(MAX_SENSOR_RANGE * SCALE)
                heading_deg = -math.degrees(pose[2])
                cv2.ellipse(overlay, (px, py), (radius, radius), heading_deg, -FOV_ANGLE/2, FOV_ANGLE/2, COLOR_FOV, -1)
        cv2.addWeighted(overlay, 0.2, img, 0.8, 0, img)

        for i, pose in enumerate(self.robot_poses):
            if pose:
                px, py = self.world_to_pixel(pose[0], pose[1])
                cv2.circle(img, (px, py), 12, COLOR_ROBOTS[i], -1)
                end_x = int(px + 20 * math.cos(pose[2])); end_y = int(py - 20 * math.sin(pose[2]))
                cv2.line(img, (px, py), (end_x, end_y), (0,0,0), 2)
                cv2.putText(img, f"R{i+1}", (px-10, py-15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255,255,255), 1)

        if self.ball_gt:
            bx, by = self.world_to_pixel(self.ball_gt[0], self.ball_gt[1])
            cv2.circle(img, (bx, by), 5, COLOR_GT_BALL, -1)
            cv2.putText(img, "GT", (bx+5, by-5), cv2.FONT_HERSHEY_SIMPLEX, 0.3, COLOR_GT_BALL, 1)

        c_pos, c_color, c_status, is_live = self.get_consensus_ball()
        if c_pos:
            cpx, cpy = self.world_to_pixel(c_pos[0], c_pos[1])
            if is_live:
                cv2.circle(img, (cpx, cpy), 10, c_color, -1)
                cv2.circle(img, (cpx, cpy), 12, (255,255,255), 2)
            else:
                should_blink = int(time.time() * 2) % 2 == 0
                if should_blink:
                    cv2.circle(img, (cpx, cpy), 10, c_color, 2) 
                    cv2.putText(img, "?", (cpx-5, cpy+5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, c_color, 2)

        panel_y = WINDOW_HEIGHT
        cv2.rectangle(img, (0, panel_y), (WINDOW_WIDTH, panel_y+DASHBOARD_HEIGHT), (40,40,40), -1)
        cv2.putText(img, f"STATUS: {c_status}", (20, panel_y+30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, c_color, 2)
        col_x = 20; row_y = panel_y + 60
        for i, est in enumerate(self.ball_estimates):
            color = COLOR_ROBOTS[i]; txt = f"R{i+1}: [NO BALL]"
            if est: txt = f"R{i+1}: Found Ball!"
            cv2.putText(img, txt, (col_x, row_y + (i*25)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        cv2.imshow("RoboCup Dashboard", img)
        cv2.waitKey(1)

def main(args=None):
    rclpy.init(args=args)
    node = SoccerDashboard()
    rclpy.spin(node)
    node.destroy_node(); rclpy.shutdown(); cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
