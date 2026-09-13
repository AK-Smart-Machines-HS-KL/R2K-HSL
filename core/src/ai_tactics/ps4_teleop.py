#!/usr/bin/env python3
"""PS4 Teleop for ROS2K - yahboom-only live experiment (Option A)"""
import json
import os
import time
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
from std_msgs.msg import Int32

# === Constants (tunable, per repo convention) ===
PAN_MIN_DEG, PAN_MAX_DEG = -40.0, 40.0    # servo_s1 rotation
TILT_MIN_DEG, TILT_MAX_DEG = -20.0, 20.0  # servo_s2 tilt
MAX_VX, MAX_VYAW = 0.5, 1.0
STICK_DEADZONE = 0.1
HEARTBEAT_TIMEOUT_S = 0.3
ENGAGE_DEFAULT_BOT = "blue_1"

# PS4 button/axis indices (DS4 via joy_node - verify live, printed at startup)
BTN_ENGAGE = 10   # PS button
BTN_L1, BTN_R1 = 4, 5
BTN_CIRCLE, BTN_SQUARE = 1, 3
AX_LX, AX_LY, AX_RX, AX_RY = 0, 1, 2, 3
DEADMAN_AXIS = 5  # R2 analog trigger

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
TELEOP_STATE_PATH = os.path.join(BASE_DIR, "..", "shared_state", "teleop_state.json")


def clamp(value, min_val, max_val):
    return max(min(value, max_val), min_val)


class PS4Teleop(Node):
    def __init__(self):
        super().__init__('ps4_teleop')
        
        # Servo publishers (both bots)
        self.pub_s1_b1 = self.create_publisher(Int32, '/blue_1/servo_s1', 10)
        self.pub_s2_b1 = self.create_publisher(Int32, '/blue_1/servo_s2', 10)
        self.pub_s1_b2 = self.create_publisher(Int32, '/blue_2/servo_s1', 10)
        self.pub_s2_b2 = self.create_publisher(Int32, '/blue_2/servo_s2', 10)
        
        self.sub_joy = self.create_subscription(Joy, '/joy', self.joy_callback, 10)
        
        self.active = False
        self.selected_bot = ENGAGE_DEFAULT_BOT
        self.last_engage_press = False
        
        self.get_logger().info(f"PS4 Teleop online (defaults: engage={ENGAGE_DEFAULT_BOT}, pan=±{PAN_MAX_DEG}°, tilt=±{TILT_MAX_DEG}°)")
        self.get_logger().info(f"Button map: PS={BTN_ENGAGE}, L1={BTN_L1}, R1={BTN_R1}, Circle={BTN_CIRCLE}, Square={BTN_SQUARE}, R2={DEADMAN_AXIS}")
        
    def joy_callback(self, msg):
        # Check deadman (R2)
        deadman_pressed = msg.axes[DEADMAN_AXIS] > 0.9
        
        # PS button engage/disengage (edge detect)
        engage_press = msg.buttons[BTN_ENGAGE] and not self.last_engage_press
        if engage_press:
            self.active = not self.active
            self.get_logger().info(f"Teleop {'ENGAGED' if self.active else 'DISENGAGED'}")
        self.last_engage_press = msg.buttons[BTN_ENGAGE]
        
        if not self.active or not deadman_pressed:
            self._save_state(active=False)
            return
        
        # Bot selection (L1/R1)
        if msg.buttons[BTN_L1]:
            self.selected_bot = "blue_1"
        elif msg.buttons[BTN_R1]:
            self.selected_bot = "blue_2"
        
        # Left stick: drive (vx, vyaw)
        vx_raw = -msg.axes[AX_LY]  # negate Y for forward
        vyaw_raw = msg.axes[AX_LX]
        vx = clamp(vx_raw, -1, 1) * MAX_VX if abs(vx_raw) > STICK_DEADZONE else 0.0
        vyaw = clamp(vyaw_raw, -1, 1) * MAX_VYAW if abs(vyaw_raw) > STICK_DEADZONE else 0.0
        
        # Right stick: gimbal pan/tilt (both bots)
        pan_raw = msg.axes[AX_RX]
        tilt_raw = msg.axes[AX_RY]
        pan_angle = int(clamp(pan_raw * (PAN_MAX_DEG - PAN_MIN_DEG) / 2.0 + (PAN_MAX_DEG + PAN_MIN_DEG) / 2.0, PAN_MIN_DEG, PAN_MAX_DEG))
        tilt_angle = int(clamp(tilt_raw * (TILT_MAX_DEG - TILT_MIN_DEG) / 2.0 + (TILT_MAX_DEG + TILT_MIN_DEG) / 2.0, TILT_MIN_DEG, TILT_MAX_DEG))
        
        self.get_logger().info(f"[{self.selected_bot}] vx={vx:.2f}, vyaw={vyaw:.2f} | pan={pan_angle}°, tilt={tilt_angle}°")
        
        # Publish servos (both bots)
        self.pub_s1_b1.publish(Int32(data=pan_angle))
        self.pub_s1_b2.publish(Int32(data=pan_angle))
        self.pub_s2_b1.publish(Int32(data=tilt_angle))
        self.pub_s2_b2.publish(Int32(data=tilt_angle))
        
        # Save state for bridge
        self._save_state(active=True, bot=self.selected_bot, vx=vx, vyaw=vyaw)
    
    def _save_state(self, **kwargs):
        data = {
            "active": kwargs.get("active", self.active),
            "bot": kwargs.get("bot", self.selected_bot if self.active else None),
            "vx": kwargs.get("vx", 0.0),
            "vyaw": kwargs.get("vyaw", 0.0),
            "ts": time.time()
        }
        tmp_path = TELEOP_STATE_PATH + ".tmp"
        with open(tmp_path, 'w') as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, TELEOP_STATE_PATH)
        os.chmod(TELEOP_STATE_PATH, 0o666)


def main():
    rclpy.init()
    node = PS4Teleop()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node._save_state(active=False)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
