#!/usr/bin/env python3
"""
GoToBallAndKick node — K1 on-robot kick executor.

Runs locally on the K1. Subscribes to:
  - /{prefix}/GoToBallAndKick  (k1_skills_msgs/GoToBallAndKickCmd)
      High-level trigger from the host bridge. abort=true stops the loop.
  - /booster_soccer/ball       (vision_interface/Ball)
      Filtered ball pose from the utils/vision perception node.

Publishes:
  - /kick_ball                 (brain/Kick)
      High-frequency stream (no rate cap — runs to the system limit) consumed
      by the vendor soccer agent kick controller
      (com.boosterobotics.soccer). A single message yields only a partial
      kick motion — the continuous stream is required for a full kick.

RPC:
  - /LocoApiTopicReq           (booster_msgs/RpcReqMsg, api_id 2038)
      VisualKick V1 arm (one-shot on first ball detection) + abort
      ({"start": false} on stop / timeout / ball-lost).

Head control is NOT handled by this node — a separate head-control node
publishes /head_pose for the vision node and drives RPC 2004. See the
migration plan (core/docs/plans/v68_pre_ifa/).

Dependencies (must be built + sourced on the K1):
  - k1_skills_msgs  (core/src/ros2_ws/src/k1_skills_msgs)
  - vision_interface (core/src/ros2_ws/src/vision_interface)
  - brain            (vendor soccer agent install, /opt/booster/...)
  - booster_msgs     (core/src/ros2_ws/src/booster_msgs)
"""

import argparse
import json
import math
import threading
import time
import uuid

import rclpy
from rclpy.node import Node

from k1_skills_msgs.msg import GoToBallAndKickCmd
from vision_interface.msg import Ball as VisionBall
from brain.msg import Kick

try:
    from booster_msgs.msg import RpcReqMsg
    HAS_BOOSTER_MSGS = True
except ImportError:
    HAS_BOOSTER_MSGS = False


# === Named constants (AGENTS.md: no hard-wired thresholds in code) ===

# VisualKick V1 arm / abort (api_id 2038, vendor-confirmed K1, fw >= 1.5.2.1)
VISUALKICK_API_ID = 2038
VISUALKICK_VERSION = 0          # V1 = base kick; V2 = 1 (stronger)

# Power auto-computation (when cmd.power == 0.0)
POWER_GOALSHOT_FAR = 6.0        # goalshot, distance > GOALSHOT_FAR_DIST_M
POWER_GOALSHOT_NEAR = 1.5       # goalshot, distance <= GOALSHOT_FAR_DIST_M
GOALSHOT_FAR_DIST_M = 6.0
POWER_PASS_MULTIPLIER = 0.8
POWER_PASS_CAP = 4.0

# Safety timeouts
KICK_MAX_DURATION_S = 8.0       # auto-abort after this many seconds
BALL_LOST_TIMEOUT_S = 2.0       # no vision msg for this long -> abort
BALL_CONFIDENCE_MIN = 0.2       # ignore vision ball detections below this

# Kick stream header
KICK_FRAME_ID = 'head_color_optical_frame'


class GoToBallAndKickNode(Node):
    def __init__(self, robot_prefix: str):
        super().__init__('go_to_ball_and_kick_node')

        self.robot_prefix = robot_prefix.strip('/')

        # --- State (thread-safe: vision callback + kick thread access) ---
        self._lock = threading.Lock()
        self._is_active = False
        self._target_x = 0.0
        self._target_y = 0.0
        self._power_cmd = 0.0       # 0.0 = auto-compute
        self._is_goalshot = False
        self._ball_x = 0.0
        self._ball_y = 0.0
        self._last_ball_t = 0.0
        self._armed = False         # VisualKick V1 armed flag
        self._kick_start_t = 0.0
        self._kick_thread = None    # background publish loop

        # --- Subscriptions ---
        cmd_topic = f'/{self.robot_prefix}/GoToBallAndKick'
        self.cmd_sub = self.create_subscription(
            GoToBallAndKickCmd, cmd_topic, self._cmd_callback, 10)
        self.get_logger().info(f"Listening for commands on: {cmd_topic}")

        self.vision_sub = self.create_subscription(
            VisionBall, '/booster_soccer/ball',
            self._vision_callback, 10)

        # --- Publishers ---
        self.kick_pub = self.create_publisher(Kick, '/kick_ball', 10)

        if HAS_BOOSTER_MSGS:
            self.rpc_pub = self.create_publisher(
                RpcReqMsg, '/LocoApiTopicReq', 10)
        else:
            self.rpc_pub = None
            self.get_logger().warn(
                "booster_msgs not available — VisualKick arm/abort disabled")

    # ------------------------------------------------------------------
    # Vision callback — update ball position (thread-safe)
    # ------------------------------------------------------------------
    def _vision_callback(self, msg: VisionBall):
        if msg.confidence < BALL_CONFIDENCE_MIN:
            return
        with self._lock:
            self._ball_x = float(msg.x)
            self._ball_y = float(msg.y)
            self._last_ball_t = time.time()
            # Arm VisualKick V1 on first valid detection if active
            if self._is_active and not self._armed:
                self._arm_visualkick()

    # ------------------------------------------------------------------
    # Command callback — start or abort the kick loop
    # ------------------------------------------------------------------
    def _cmd_callback(self, msg: GoToBallAndKickCmd):
        if msg.abort:
            self._abort("cmd abort")
            return

        with self._lock:
            self._target_x = float(msg.target_x)
            self._target_y = float(msg.target_y)
            self._power_cmd = float(msg.power)
            self._is_goalshot = bool(msg.is_goalshot)
            self._kick_start_t = time.time()
            # (Re)activate
            was_active = self._is_active
            self._is_active = True
            # Reset armed flag so a new kick re-arms on next ball detection
            self._armed = False

        mode = "GOALSHOT" if msg.is_goalshot else "PASS"
        self.get_logger().info(
            f"Command received! Mode: {mode} | Target: "
            f"({self._target_x:.2f}, {self._target_y:.2f}) | "
            f"power: {self._power_cmd:.1f}{' (auto)' if self._power_cmd == 0.0 else ''}"
        )

        # If not already running, start the kick thread
        if not was_active or self._kick_thread is None or \
           not self._kick_thread.is_alive():
            self._kick_thread = threading.Thread(
                target=self._kick_loop, daemon=True)
            self._kick_thread.start()

    # ------------------------------------------------------------------
    # Kick loop — tight publish, no rate cap (runs to system limit)
    # ------------------------------------------------------------------
    def _kick_loop(self):
        self.get_logger().info("Kick stream thread started (no rate cap)")
        while True:
            with self._lock:
                if not self._is_active:
                    break
                now = time.time()
                # Safety timeout
                if now - self._kick_start_t > KICK_MAX_DURATION_S:
                    active = True
                    break_reason = f"timeout ({KICK_MAX_DURATION_S}s)"
                    break
                # Ball-lost timeout
                if self._last_ball_t > 0 and \
                   now - self._last_ball_t > BALL_LOST_TIMEOUT_S:
                    active = True
                    break_reason = (
                        f"ball lost ({BALL_LOST_TIMEOUT_S}s no vision)")
                    break
                ball_x = self._ball_x
                ball_y = self._ball_y
                target_x = self._target_x
                target_y = self._target_y
                power_cmd = self._power_cmd
                is_goalshot = self._is_goalshot

            # Build + publish Kick message outside the lock
            kick_msg = self._build_kick_msg(
                ball_x, ball_y, target_x, target_y, power_cmd, is_goalshot)
            self.kick_pub.publish(kick_msg)
            # Yield GIL — no rate cap, rclpy + DDS pace it naturally
            time.sleep(0)

        # Loop exited — clean up if we broke due to timeout/ball-lost
        if break_reason:
            self._abort(break_reason)

    # ------------------------------------------------------------------
    # Build a brain/Kick message from current state
    # ------------------------------------------------------------------
    def _build_kick_msg(self, ball_x, ball_y, target_x, target_y,
                        power_cmd, is_goalshot):
        msg = Kick()
        stamp = self.get_clock().now().to_msg()
        msg.header.stamp = stamp
        msg.header.frame_id = KICK_FRAME_ID

        # Ball position (relative to robot, from vision)
        msg.x = ball_x
        msg.y = ball_y

        # Kick direction: angle from ball to target, relative to robot
        msg.dir = math.atan2(target_y - ball_y, target_x - ball_x)

        # Goal position (target = where the ball should go)
        msg.goal_x = target_x
        msg.goal_y = target_y

        # Robot theta to field — unknown from vision alone; 0.0 = let
        # the vendor controller infer from its own kinematics
        msg.robot_theta_to_field = 0.0

        # Power
        if power_cmd > 0.0:
            msg.power = power_cmd
        else:
            msg.power = self._compute_power(
                ball_x, ball_y, target_x, target_y, is_goalshot)

        return msg

    @staticmethod
    def _compute_power(ball_x, ball_y, target_x, target_y, is_goalshot):
        dist = math.hypot(target_x - ball_x, target_y - ball_y)
        if is_goalshot:
            return POWER_GOALSHOT_FAR if dist > GOALSHOT_FAR_DIST_M \
                else POWER_GOALSHOT_NEAR
        return min(dist * POWER_PASS_MULTIPLIER, POWER_PASS_CAP)

    # ------------------------------------------------------------------
    # VisualKick V1 arm / abort via RPC 2038
    # ------------------------------------------------------------------
    def _arm_visualkick(self):
        """Send RPC 2038 {"start": true, "version": V1} to arm the firmware
        visual-kick skill. Must be called BEFORE the /kick_ball stream —
        without it, messages are received but no motion happens
        (verified live 2026-10-05). Idempotent under the lock."""
        if not self.rpc_pub:
            return
        if self._armed:
            return
        rpc = RpcReqMsg()
        rpc.uuid = f"vk1_arm_{uuid.uuid4().hex[:8]}"
        rpc.header = json.dumps({"api_id": VISUALKICK_API_ID})
        rpc.body = json.dumps(
            {"start": True, "version": VISUALKICK_VERSION})
        self.rpc_pub.publish(rpc)
        self._armed = True
        self.get_logger().info(
            f"VisualKick V1 armed (RPC {VISUALKICK_API_ID})")

    def _abort_visualkick(self):
        """Send RPC 2038 {"start": false} to stop the firmware kick skill."""
        if not self.rpc_pub:
            return
        rpc = RpcReqMsg()
        rpc.uuid = f"vk1_stop_{uuid.uuid4().hex[:8]}"
        rpc.header = json.dumps({"api_id": VISUALKICK_API_ID})
        rpc.body = json.dumps({"start": False})
        self.rpc_pub.publish(rpc)
        self.get_logger().info(
            f"VisualKick V1 STOP (RPC {VISUALKICK_API_ID})")

    # ------------------------------------------------------------------
    # Abort — stop the kick loop + firmware skill
    # ------------------------------------------------------------------
    def _abort(self, reason: str):
        with self._lock:
            was_active = self._is_active
            self._is_active = False
        if was_active:
            self._abort_visualkick()
            self.get_logger().info(f"Kick loop stopped ({reason})")


def main(args=None):
    parser = argparse.ArgumentParser(
        description="K1 GoToBallAndKick node — on-robot kick executor")
    parser.add_argument('--robot-prefix', type=str, default='Kev1n',
                        help='Robot namespace prefix (default: Kev1n)')
    parsed_args, ros_args = parser.parse_known_args()

    rclpy.init(args=ros_args)
    node = GoToBallAndKickNode(parsed_args.robot_prefix)

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Shutting down GoToBallAndKick node.")
    finally:
        node._abort("node shutdown")
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()