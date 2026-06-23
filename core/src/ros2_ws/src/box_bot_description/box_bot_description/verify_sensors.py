#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from gazebo_msgs.srv import SetEntityState
import numpy as np
import time
import math

class SensorVerifier(Node):
    def __init__(self):
        super().__init__('sensor_verifier')
        self.cli = self.create_client(SetEntityState, '/gazebo/set_entity_state')
        self.sub = self.create_subscription(LaserScan, '/robot1/scan', self.scan_cb, 10)
        self.scan_data = None
        self.get_logger().info("TEST SUITE: Initializing...")

    def scan_cb(self, msg):
        self.scan_data = msg

    def teleport_ball(self, x, y):
        # Move ball to absolute position (x, y)
        req = SetEntityState.Request()
        req.state.name = 'soccer_ball'
        req.state.pose.position.x = float(x)
        req.state.pose.position.y = float(y)
        req.state.pose.position.z = 0.11
        
        while not self.cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('Waiting for Gazebo...')
        
        future = self.cli.call_async(req)
        rclpy.spin_until_future_complete(self, future)
        time.sleep(1.0) # Wait for physics to settle

    def run_diagnostics(self):
        print("\n" + "="*50)
        print("🔍 RUNNING SENSOR HARDWARE DIAGNOSTIC")
        print("="*50)

        # --- TEST 1: CHASSIS OBSTRUCTION ---
        print("\n[TEST 1] Internal Obstruction Check")
        # Move ball far away so we see 'empty' space
        self.teleport_ball(10.0, 10.0) 
        rclpy.spin_once(self, timeout_sec=1.0)
        
        if self.scan_data is None:
            print("❌ FAIL: No data received from /robot1/scan")
            return

        ranges = np.array(self.scan_data.ranges)
        total_rays = len(ranges)
        zero_readings = np.sum(ranges == 0.0)
        percent_zeros = (zero_readings / total_rays) * 100

        print(f"   Total Rays: {total_rays}")
        print(f"   Zero Readings (Blocked): {zero_readings} ({percent_zeros:.1f}%)")

        if percent_zeros > 20.0:
            print("❌ FAIL: CRITICAL BLOCKAGE DETECTED.")
            print("   The LIDAR is likely mounted inside the robot chassis.")
            print("   Fix: Move <origin x> to 0.30 in the URDF.")
        else:
            print("✅ PASS: Sensor view is clear (obstructions < 20%).")


        # --- TEST 2: BALL DETECTION ACCURACY ---
        print("\n[TEST 2] Ball Detection Accuracy")
        # Robot 1 is at (-2, 0). Move ball to (0, 0).
        # Expected Distance: 2.0 meters.
        self.teleport_ball(0.0, 0.0)
        # Robot 1 is facing East (0 rad). Ball is directly in front.
        
        # Flush buffer
        for _ in range(10): rclpy.spin_once(self, timeout_sec=0.1)
        
        ranges = np.array(self.scan_data.ranges)
        # Get the center ray (index corresponding to angle 0)
        # Note: Standard LIDAR scans often go -Pi to +Pi. Center index is usually middle.
        mid_idx = len(ranges) // 2
        center_dist = ranges[mid_idx]
        
        # Check a small cone around the center
        cone = ranges[mid_idx-5 : mid_idx+5]
        min_cone = np.min(cone)

        print(f"   Target Distance: ~2.00m")
        print(f"   Sensor Reading (Center Ray): {center_dist:.4f}m")
        print(f"   Sensor Reading (Min in Cone): {min_cone:.4f}m")

        if 1.8 < min_cone < 2.2:
            print("✅ PASS: Ball detected at correct distance.")
        elif min_cone == 0.0:
            print("❌ FAIL: Sensor reads 0.0 (Blocked) instead of 2.0m.")
        elif min_cone == float('inf'):
            print("❌ FAIL: Sensor sees Infinity (Blind/Too High) instead of 2.0m.")
        else:
            print(f"⚠️  WARNING: Reading {min_cone:.2f}m is inaccurate (Expected 2.0m).")
        
        print("="*50 + "\n")

def main(args=None):
    rclpy.init(args=args)
    node = SensorVerifier()
    node.run_diagnostics()
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
