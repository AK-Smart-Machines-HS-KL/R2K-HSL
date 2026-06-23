#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import PointStamped, Pose2D
from gazebo_msgs.msg import ModelStates
import cv2
import numpy as np
import math
import time

# --- FELD KONFIGURATION ---
FIELD_LENGTH = 9.0   
FIELD_WIDTH = 6.0    
BORDER_STRIP = 0.5   
SCALE = 90           

WINDOW_WIDTH = int((FIELD_LENGTH + 2*BORDER_STRIP) * SCALE)
WINDOW_HEIGHT = int((FIELD_WIDTH + 2*BORDER_STRIP) * SCALE)
DASHBOARD_HEIGHT = 140

# SENSOR KONFIGURATION
MAX_SENSOR_RANGE = 2.5     
FOV_ANGLE = 180            
CONSENSUS_THRESHOLD = 1.0  
SMOOTHING_FACTOR = 0.3     

# FILTER PARAMETER
SAFE_X = FIELD_LENGTH / 2.0  
SAFE_Y = FIELD_WIDTH / 2.0  
TEAMMATE_RADIUS = 0.4 
MAX_OBJ_WIDTH = 0.35 

# FARBEN
COLOR_GRASS     = (0, 100, 0)      
COLOR_LINES     = (240, 240, 240)  
COLOR_GT_BALL   = (255, 255, 255)  
COLOR_EST_BALL  = (0, 255, 255)    
COLOR_ROBOTS    = [(255, 100, 100), (100, 255, 100), (100, 100, 255)] 
COLOR_FOV       = (0, 200, 200)    
COLOR_GOAL_L    = (0, 255, 255)    
COLOR_GOAL_R    = (255, 100, 0)    

class WorldModel(Node):
    def __init__(self):
        super().__init__('worldmodel')
        
        self.robot_poses = [None, None, None]      
        self.ball_estimates = [None, None, None]   
        self.smoothed_ball_pos = None
        self.last_known_ball_pos = None
        self.gt_ball_pose = None 
        
        self.background_img = self.create_field_background()

        self.ball_pub = self.create_publisher(PointStamped, '/shared_ball_position', 10)
        self.ball_pose_pub = self.create_publisher(Pose2D, 'teamBallModel', 10)

        self.create_subscription(Odometry, '/robot1/odom', lambda m: self.odom_cb(m, 0), qos_profile_sensor_data)
        self.create_subscription(Odometry, '/robot2/odom', lambda m: self.odom_cb(m, 1), qos_profile_sensor_data)
        self.create_subscription(Odometry, '/robot3/odom', lambda m: self.odom_cb(m, 2), qos_profile_sensor_data)
        
        self.create_subscription(LaserScan, '/robot1/scan', lambda m: self.scan_cb(m, 0), qos_profile_sensor_data)
        self.create_subscription(LaserScan, '/robot2/scan', lambda m: self.scan_cb(m, 1), qos_profile_sensor_data)
        self.create_subscription(LaserScan, '/robot3/scan', lambda m: self.scan_cb(m, 2), qos_profile_sensor_data)

        self.create_subscription(ModelStates, '/gazebo/model_states', self.gt_cb, qos_profile_sensor_data)

        self.timer = self.create_timer(0.04, self.update_loop)
        self.get_logger().info("WorldModel: High-Def Field Visualization Active.")

    def world_to_px(self, x, y):
        px = int((x + (FIELD_LENGTH/2 + BORDER_STRIP)) * SCALE)
        py = int((-y + (FIELD_WIDTH/2 + BORDER_STRIP)) * SCALE)
        return px, py

    def create_field_background(self):
        img = np.zeros((WINDOW_HEIGHT, WINDOW_WIDTH, 3), dtype=np.uint8)
        cv2.rectangle(img, (0,0), (WINDOW_WIDTH, WINDOW_HEIGHT), COLOR_GRASS, -1)
        
        tl = self.world_to_px(-FIELD_LENGTH/2, FIELD_WIDTH/2)
        br = self.world_to_px(FIELD_LENGTH/2, -FIELD_WIDTH/2)
        cv2.rectangle(img, tl, br, COLOR_LINES, 2)
        
        top_mid = self.world_to_px(0, FIELD_WIDTH/2)
        bot_mid = self.world_to_px(0, -FIELD_WIDTH/2)
        cv2.line(img, top_mid, bot_mid, COLOR_LINES, 2)
        
        center_px = self.world_to_px(0, 0)
        radius_px = int(0.75 * SCALE)
        cv2.circle(img, center_px, radius_px, COLOR_LINES, 2)
        
        sz = 4 
        cv2.line(img, (center_px[0]-sz, center_px[1]-sz), (center_px[0]+sz, center_px[1]+sz), COLOR_LINES, 2)
        cv2.line(img, (center_px[0]-sz, center_px[1]+sz), (center_px[0]+sz, center_px[1]-sz), COLOR_LINES, 2)

        def draw_box(sign_x):
            x_back = sign_x * FIELD_LENGTH/2
            x_front = sign_x * (FIELD_LENGTH/2 - 1.5)
            y_top = 2.0
            y_bot = -2.0
            p1 = self.world_to_px(x_back, y_top)
            p2 = self.world_to_px(x_front, y_bot)
            cv2.rectangle(img, p1, p2, COLOR_LINES, 2)
            
            x_front_sm = sign_x * (FIELD_LENGTH/2 - 0.6)
            y_top_sm = 1.1
            y_bot_sm = -1.1
            p3 = self.world_to_px(x_back, y_top_sm)
            p4 = self.world_to_px(x_front_sm, y_bot_sm)
            cv2.rectangle(img, p3, p4, COLOR_LINES, 2)

            goal_color = COLOR_GOAL_L if sign_x < 0 else COLOR_GOAL_R
            post_top = self.world_to_px(x_back, 0.75)
            post_bot = self.world_to_px(x_back, -0.75)
            cv2.circle(img, post_top, 6, goal_color, -1)
            cv2.circle(img, post_bot, 6, goal_color, -1)
            cv2.line(img, post_top, post_bot, goal_color, 2)

        draw_box(-1) 
        draw_box(1)  
        
        return img

    def gt_cb(self, msg):
        if 'soccer_ball' in msg.name:
            idx = msg.name.index('soccer_ball')
            self.gt_ball_pose = (msg.pose[idx].position.x, msg.pose[idx].position.y)

    def odom_cb(self, msg, robot_id):
        p = msg.pose.pose.position
        q = msg.pose.pose.orientation
        theta = math.atan2(2*(q.w*q.z + q.x*q.y), 1-2*(q.y*q.y + q.z*q.z))
        self.robot_poses[robot_id] = (p.x, p.y, theta)

    def scan_cb(self, msg, robot_id):
        if self.robot_poses[robot_id] is None: return

        ranges = np.array(msg.ranges)
        ranges[ranges == float('inf')] = 100.0
        ranges[ranges < 0.2] = 100.0 

        num_readings = len(ranges)
        angles = np.linspace(msg.angle_min, msg.angle_max, num_readings)
        limit = math.radians(FOV_ANGLE / 2)
        blind_mask = (angles > limit) | (angles < -limit)
        ranges[blind_mask] = 100.0

        min_idx = np.argmin(ranges)
        min_dist = ranges[min_idx]

        self.ball_estimates[robot_id] = None 

        if min_dist < MAX_SENSOR_RANGE:
            start_idx = min_idx
            while start_idx > 0 and abs(ranges[start_idx] - ranges[start_idx-1]) < 0.2: start_idx -= 1
            end_idx = min_idx
            while end_idx < num_readings - 1 and abs(ranges[end_idx] - ranges[end_idx+1]) < 0.2: end_idx += 1
            
            width = (end_idx - start_idx) * msg.angle_increment * min_dist
            if width > MAX_OBJ_WIDTH: return 

            found_angle = angles[min_idx]
            rx, ry, r_theta = self.robot_poses[robot_id]
            obj_x = rx + min_dist * math.cos(r_theta + found_angle)
            obj_y = ry + min_dist * math.sin(r_theta + found_angle)
            
            if not ((-SAFE_X < obj_x < SAFE_X) and (-SAFE_Y < obj_y < SAFE_Y)): return 
            
            is_teammate = False
            for i, pose in enumerate(self.robot_poses):
                if pose and i != robot_id:
                    if math.sqrt((obj_x - pose[0])**2 + (obj_y - pose[1])**2) < TEAMMATE_RADIUS:
                        is_teammate = True
            
            if not is_teammate:
                self.ball_estimates[robot_id] = (obj_x, obj_y)

    def update_loop(self):
        valid = [p for p in self.ball_estimates if p is not None]
        avg_pos = None
        status = "SEARCHING"
        
        if valid:
            avg_x = sum(p[0] for p in valid) / len(valid)
            avg_y = sum(p[1] for p in valid) / len(valid)
            target = (avg_x, avg_y)
            
            if self.smoothed_ball_pos is None: self.smoothed_ball_pos = target
            else:
                sx = self.smoothed_ball_pos[0] * (1-SMOOTHING_FACTOR) + target[0]*SMOOTHING_FACTOR
                sy = self.smoothed_ball_pos[1] * (1-SMOOTHING_FACTOR) + target[1]*SMOOTHING_FACTOR
                self.smoothed_ball_pos = (sx, sy)
            
            avg_pos = self.smoothed_ball_pos
            status = f"TRACKING ({len(valid)} Bots)"
            
            msg = PointStamped()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.header.frame_id = "map"
            msg.point.x, msg.point.y = avg_pos
            self.ball_pub.publish(msg)

        img = self.background_img.copy() 
        overlay = img.copy()

        for i, pose in enumerate(self.robot_poses):
            if pose:
                px, py = self.world_to_px(pose[0], pose[1])
                radius = int(MAX_SENSOR_RANGE * SCALE)
                heading_deg = -math.degrees(pose[2])
                cv2.ellipse(overlay, (px, py), (radius, radius), heading_deg, -FOV_ANGLE/2, FOV_ANGLE/2, COLOR_FOV, -1)
        
        cv2.addWeighted(overlay, 0.3, img, 0.7, 0, img)

        for i, pose in enumerate(self.robot_poses):
            if pose:
                px, py = self.world_to_px(pose[0], pose[1])
                cv2.circle(img, (px, py), 14, (0,0,0), -1)
                cv2.circle(img, (px, py), 11, COLOR_ROBOTS[i], -1)
                end_x = int(px + 20 * math.cos(pose[2]))
                end_y = int(py - 20 * math.sin(pose[2]))
                cv2.line(img, (px, py), (end_x, end_y), (0,0,0), 2)
                # FIX HIER: FONT_HERSHEY_SIMPLEX statt FONT_HERSHEY_BOLD
                cv2.putText(img, str(i+1), (px-5, py+5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)

        if self.gt_ball_pose:
            bx, by = self.world_to_px(self.gt_ball_pose[0], self.gt_ball_pose[1])
            cv2.circle(img, (bx, by), 8, (0,0,0), -1) 
            cv2.circle(img, (bx, by), 6, COLOR_GT_BALL, -1)

        if avg_pos:
            cpx, cpy = self.world_to_px(avg_pos[0], avg_pos[1])
            cv2.circle(img, (cpx, cpy), 10, COLOR_EST_BALL, -1)
            cv2.circle(img, (cpx, cpy), 12, (0,0,0), 1)

        dashboard = np.zeros((DASHBOARD_HEIGHT, WINDOW_WIDTH, 3), dtype=np.uint8)
        dashboard[:] = (40, 40, 40) 
        
        cv2.putText(dashboard, f"STATUS: {status}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, COLOR_EST_BALL, 2)
        
        for i, est in enumerate(self.ball_estimates):
            col = COLOR_ROBOTS[i]
            txt = f"Robot {i+1}: NO DATA"
            if est: txt = f"Robot {i+1}: BALL DETECTED at ({est[0]:.2f}, {est[1]:.2f})"
            cv2.putText(dashboard, txt, (20, 80 + i*25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, col, 1)

        final_img = np.vstack((img, dashboard))
        cv2.imshow("World Model", final_img)
        cv2.waitKey(1)

def main(args=None):
    rclpy.init(args=args)
    node = WorldModel()
    try: rclpy.spin(node)
    except KeyboardInterrupt: pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
        cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
