#!/usr/bin/env python3
"""
HeadControl node — K1 on-robot head controller.

Runs locally on the K1. Subscribes to:
  - /{prefix}/HeadControl  (k1_skills_msgs/HeadControlCmd)
      High-level head command from the GoToBallAndKick node (local, no relay).
      abort=true or MODE_ABORT -> stop tracking, head holds last pose.
  - /booster_soccer/ball   (vision_interface/Ball)
      Ball pose from the utils/vision perception node (for LOOK_AT_BALL mode).

Publishes:
  - /head_pose             (geometry_msgs/Pose, 30 Hz)
      Head-to-base transform for the vision node. Position = fixed neck
      offset (aahead_pitch_link origin in trunk frame, from K1 URDF).
      Orientation = quaternion from commanded yaw + pitch.
  - /{prefix}/head_state   (k1_skills_msgs/HeadState, 10 Hz)
      Feedback: current mode, angles, ball tracking status.

RPC:
  - /LocoApiTopicReq       (booster_msgs/RpcReqMsg, api_id 2004)
      RotateHead(pitch, yaw) — actual head motion. Requires kWalking mode.

Dependencies (must be built + sourced on the K1):
  - k1_skills_msgs   (core/src/ros2_ws/src/k1_skills_msgs)
  - vision_interface (core/src/ros2_ws/src/vision_interface)
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
from geometry_msgs.msg import Pose

try:
    from k1_skills_msgs.msg import HeadControlCmd, HeadState
    HAS_K1_SKILLS_MSGS = True
except ImportError:
    HAS_K1_SKILLS_MSGS = False
    HeadControlCmd = None
    HeadState = None

try:
    from vision_interface.msg import Ball as VisionBall
    HAS_VISION_INTERFACE = True
except ImportError:
    HAS_VISION_INTERFACE = False
    VisionBall = None

try:
    from booster_msgs.msg import RpcReqMsg
    HAS_BOOSTER_MSGS = True
except ImportError:
    HAS_BOOSTER_MSGS = False


# === Named constants (AGENTS.md: no hard-wired thresholds in code) ===

# --- Head-to-base offset (K1 URDF: K1_22dof.urdf) ---
# Fixed position of aahead_pitch_link origin in trunk frame.
# Does NOT change with head rotation (both joint axes pass through this point).
# Chain: trunk -> head_yaw_joint (z=0.2149) -> head_pitch_joint (z=0.033)
HEAD_OFFSET_X = 0.0056       # m, forward (trunk -> head_yaw_joint x)
HEAD_OFFSET_Y = 0.0          # m
HEAD_OFFSET_Z = 0.2479       # m, up (0.2149 + 0.033)

# --- Camera height above ground (for ball-tracking pitch geometry) ---
# K1 URDF leg chain: trunk-to-ankle = 0.51369 m, +head 0.2479, +cam 0.092774
# = 0.854 m above ankle. Add ~0.02 m foot sole = ~0.87 m (straight legs).
# Using 0.85 m per user directive (standing pose with slight knee bend).
# TODO: verify with tape measure on the K1 standing pose.
CAMERA_HEIGHT_ABOVE_GROUND = 0.85    # m

# --- K1 head limits (probe-verified 2026-10-07, head_cmds.py) ---
# Source: docs/plans/v68_pre_ifa/k1_kick_head_vendor_audit.md section 2.2
K1_HEAD_YAW_LIMIT_RAD = 1.0          # mechanical stop (vendor spec 1.03)
K1_HEAD_PITCH_MIN_RAD = -0.33        # vendor spec -19 deg
K1_HEAD_PITCH_MAX_RAD = 0.86         # vendor spec +49 deg
K1_SIGN_YAW = 1.0                    # verified: +yaw (RPC) = head LEFT
K1_SIGN_PITCH = 1.0                  # verified: +pitch (RPC) = head UP

# --- URDF pitch sign flip (for /head_pose quaternion) ---
# URDF pitch joint axis (0,1,0): +rotation = nose DOWN (opposite to RPC
# +pitch = UP). /head_pose orientation = R_z(rpc_yaw) * R_y(-rpc_pitch).
URDF_PITCH_SIGN_FLIP = -1.0

# --- Publishing rates ---
HEAD_POSE_PUB_HZ = 30.0              # /head_pose for vision node
HEAD_STATE_PUB_HZ = 10.0             # /head_state feedback
HEAD_RPC_HZ = 10.0                   # RPC 2004 command rate

# --- Tracking ---
BALL_LOST_TIMEOUT_S = 2.0            # hold last pose after no vision for this
BALL_CONFIDENCE_MIN = 0.2            # ignore vision ball below this confidence

# --- RPC ---
RPC_ROTATE_HEAD_API_ID = 2004        # kRotateHead (vendor-confirmed K1)


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def yaw_pitch_to_quaternion(yaw, pitch):
    """Build a quaternion (x, y, z, w) from RPC-frame yaw + pitch.

    /head_pose orientation = R_z(rpc_yaw) * R_y(urdf_pitch)
    where urdf_pitch = -rpc_pitch (URDF pitch axis is opposite to RPC sign).
    Uses the Hamilton product q_z(yaw) * q_y(urdf_pitch).
    """
    half_yaw = yaw * 0.5
    half_pitch = pitch * URDF_PITCH_SIGN_FLIP * 0.5
    cy = math.cos(half_yaw)
    sy = math.sin(half_yaw)
    cp = math.cos(half_pitch)
    sp = math.sin(half_pitch)
    # q = q_z(yaw) * q_y(urdf_pitch) — Hamilton product
    qx = -sy * sp
    qy = cy * sp
    qz = sy * cp
    qw = cy * cp
    return qx, qy, qz, qw


def compute_look_angles(target_x, target_y):
    """Compute head yaw + pitch (RPC frame) to look at a robot-relative point.

    target_x, target_y: robot-relative coordinates (x=forward, y=left, meters).
    The target is assumed to be on the ground (z=0 in base frame).

    Returns (yaw_rad, pitch_rad) in RPC convention:
      +yaw = head left, +pitch = head up.
    Looking at a ground-level ball in front: yaw toward it, pitch negative
    (looking down).
    """
    dist = math.hypot(target_x, target_y)
    if dist < 1e-6:
        return 0.0, 0.0
    yaw = math.atan2(target_y, target_x)
    # Camera is above the ground, ball is at ground level -> look down.
    # pitch < 0 = look down (RPC +pitch = up).
    # atan2(-(cam_height - ball_height), dist) = atan2(-cam_height, dist)
    # But pitch sign: RPC +pitch = up, so looking down = negative pitch.
    # The angle below horizontal = atan2(cam_height, dist).
    # RPC pitch = -angle_below_horizontal = -atan2(cam_height, dist).
    pitch = -math.atan2(CAMERA_HEIGHT_ABOVE_GROUND, dist)
    return yaw, pitch


def clamp_head_angles(yaw, pitch):
    """Clamp yaw and pitch to K1 mechanical limits (RPC frame)."""
    yaw = clamp(yaw, -K1_HEAD_YAW_LIMIT_RAD, K1_HEAD_YAW_LIMIT_RAD)
    pitch = clamp(pitch, K1_HEAD_PITCH_MIN_RAD, K1_HEAD_PITCH_MAX_RAD)
    return yaw, pitch


def build_head_pose_msg(yaw, pitch):
    """Build a geometry_msgs/Pose for /head_pose.

    Position: fixed neck offset (head pitch link origin in trunk frame).
    Orientation: quaternion from R_z(yaw) * R_y(-pitch).
    """
    msg = Pose()
    msg.position.x = HEAD_OFFSET_X
    msg.position.y = HEAD_OFFSET_Y
    msg.position.z = HEAD_OFFSET_Z
    qx, qy, qz, qw = yaw_pitch_to_quaternion(yaw, pitch)
    msg.orientation.x = qx
    msg.orientation.y = qy
    msg.orientation.z = qz
    msg.orientation.w = qw
    return msg


class HeadControlNode(Node):
    def __init__(self, robot_prefix: str):
        super().__init__('head_control_node')

        self.robot_prefix = robot_prefix.strip('/')

        # --- State (thread-safe: cmd callback + ball callback + timers) ---
        self._lock = threading.Lock()
        self._mode = HeadControlCmd.MODE_ABORT
        self._target_x = 0.0          # for LOOK_AT_POINT
        self._target_y = 0.0
        self._ball_x = 0.0            # latest ball position (robot-relative)
        self._ball_y = 0.0
        self._ball_t = 0.0            # timestamp of last ball msg
        self._ball_visible = False
        # Current commanded head angles (RPC frame, radians)
        self._cur_yaw = 0.0
        self._cur_pitch = 0.0

        # --- Subscriptions ---
        cmd_topic = f'/{self.robot_prefix}/HeadControl'
        self.cmd_sub = self.create_subscription(
            HeadControlCmd, cmd_topic, self._cmd_callback, 10)
        self.get_logger().info(f"Listening for commands on: {cmd_topic}")

        self.vision_sub = self.create_subscription(
            VisionBall, '/booster_soccer/ball',
            self._ball_callback, 10)

        # --- Publishers ---
        self.head_pose_pub = self.create_publisher(
            Pose, '/head_pose', 10)

        state_topic = f'/{self.robot_prefix}/head_state'
        self.head_state_pub = self.create_publisher(
            HeadState, state_topic, 10)

        if HAS_BOOSTER_MSGS:
            self.rpc_pub = self.create_publisher(
                RpcReqMsg, '/LocoApiTopicReq', 10)
        else:
            self.rpc_pub = None
            self.get_logger().warn(
                "booster_msgs not available — RPC 2004 head motion disabled")

        # --- Timers ---
        self._rpc_period = 1.0 / HEAD_RPC_HZ
        self._last_rpc_t = 0.0
        self._pose_timer = self.create_timer(
            1.0 / HEAD_POSE_PUB_HZ, self._publish_head_pose)
        self._state_timer = self.create_timer(
            1.0 / HEAD_STATE_PUB_HZ, self._publish_head_state)

    # ------------------------------------------------------------------
    # Ball callback — update ball position (thread-safe)
    # ------------------------------------------------------------------
    def _ball_callback(self, msg: VisionBall):
        if msg.confidence < BALL_CONFIDENCE_MIN:
            return
        with self._lock:
            self._ball_x = float(msg.x)
            self._ball_y = float(msg.y)
            self._ball_t = time.time()
            self._ball_visible = True

    # ------------------------------------------------------------------
    # Command callback — set mode or abort
    # ------------------------------------------------------------------
    def _cmd_callback(self, msg: HeadControlCmd):
        if msg.abort or msg.mode == HeadControlCmd.MODE_ABORT:
            with self._lock:
                self._mode = HeadControlCmd.MODE_ABORT
            self.get_logger().info("Head control: ABORT (hold last pose)")
            return

        with self._lock:
            self._mode = msg.mode
            if msg.mode == HeadControlCmd.MODE_LOOK_AT_POINT:
                self._target_x = float(msg.point_x)
                self._target_y = float(msg.point_y)
            elif msg.mode in (HeadControlCmd.MODE_LOOK_AT_GOAL,
                              HeadControlCmd.MODE_LOOK_AT_CORNER):
                self.get_logger().warn(
                    f"Mode {msg.mode} (goal/corner) not implemented yet — "
                    f"needs field localization. Holding last pose.")
                self._mode = HeadControlCmd.MODE_ABORT

        mode_names = {
            HeadControlCmd.MODE_LOOK_AT_BALL: "LOOK_AT_BALL",
            HeadControlCmd.MODE_LOOK_AT_POINT: "LOOK_AT_POINT",
            HeadControlCmd.MODE_RAW_ANGLE: "RAW_ANGLE",
        }
        name = mode_names.get(msg.mode, f"MODE_{msg.mode}")
        self.get_logger().info(f"Head control: {name}")

        # RAW_ANGLE: send the given angles immediately (one-shot)
        if msg.mode == HeadControlCmd.MODE_RAW_ANGLE:
            self._handle_raw_angle(msg)

    # ------------------------------------------------------------------
    # Timer: publish /head_pose at 30 Hz
    # ------------------------------------------------------------------
    def _publish_head_pose(self):
        # Compute + send head command at RPC rate (throttled)
        now = time.time()
        if now - self._last_rpc_t >= self._rpc_period:
            self._update_head_command()
            self._last_rpc_t = now

        # Always publish /head_pose at 30 Hz with current angles
        with self._lock:
            yaw = self._cur_yaw
            pitch = self._cur_pitch
        pose_msg = build_head_pose_msg(yaw, pitch)
        self.head_pose_pub.publish(pose_msg)

    # ------------------------------------------------------------------
    # Update head command: compute target angles, send RPC 2004
    # ------------------------------------------------------------------
    def _update_head_command(self):
        with self._lock:
            target = self._compute_target_angles_unlocked()

        if target is not None:
            yaw, pitch = clamp_head_angles(target[0], target[1])
            with self._lock:
                self._cur_yaw = yaw
                self._cur_pitch = pitch
            self._send_rotate_head(yaw, pitch)
        # If target is None (hold/abort/ball-lost), we don't send a new RPC.
        # The head holds its last pose (probe-verified 2026-10-07: K1 head
        # holds on no new command, and on failsafe RPC 2000).

    def _compute_target_angles_unlocked(self):
        """Compute target angles (caller must hold lock). Returns tuple or None."""
        now = time.time()

        if self._mode == HeadControlCmd.MODE_ABORT:
            return None

        if self._mode == HeadControlCmd.MODE_RAW_ANGLE:
            return None

        if self._mode == HeadControlCmd.MODE_LOOK_AT_BALL:
            if not self._ball_visible or self._ball_t == 0.0:
                return None
            if now - self._ball_t > BALL_LOST_TIMEOUT_S:
                return None
            return compute_look_angles(self._ball_x, self._ball_y)

        if self._mode == HeadControlCmd.MODE_LOOK_AT_POINT:
            return compute_look_angles(self._target_x, self._target_y)

        return None

    # ------------------------------------------------------------------
    # Send RPC 2004 (RotateHead)
    # ------------------------------------------------------------------
    def _send_rotate_head(self, yaw_rad, pitch_rad):
        """Send RPC 2004 {"pitch": pitch, "yaw": yaw} to /LocoApiTopicReq."""
        if not self.rpc_pub:
            return
        rpc = RpcReqMsg()
        rpc.uuid = f"head_{uuid.uuid4().hex[:8]}"
        rpc.header = json.dumps({"api_id": RPC_ROTATE_HEAD_API_ID})
        rpc.body = json.dumps({
            "pitch": round(pitch_rad, 4),
            "yaw": round(yaw_rad, 4),
        })
        self.rpc_pub.publish(rpc)

    # ------------------------------------------------------------------
    # Timer: publish /head_state at 10 Hz
    # ------------------------------------------------------------------
    def _publish_head_state(self):
        with self._lock:
            state = HeadState()
            state.current_mode = self._mode
            state.current_yaw_rad = self._cur_yaw
            state.current_pitch_rad = self._cur_pitch
            state.ball_tracking = (self._mode == HeadControlCmd.MODE_LOOK_AT_BALL)
            state.ball_visible = self._ball_visible and \
                (time.time() - self._ball_t <= BALL_LOST_TIMEOUT_S)
        self.head_state_pub.publish(state)

    # ------------------------------------------------------------------
    # Handle RAW_ANGLE command — set angles immediately
    # ------------------------------------------------------------------
    def _handle_raw_angle(self, msg: HeadControlCmd):
        """For MODE_RAW_ANGLE: clamp + send the given angles directly."""
        yaw = clamp(msg.yaw_rad * K1_SIGN_YAW,
                    -K1_HEAD_YAW_LIMIT_RAD, K1_HEAD_YAW_LIMIT_RAD)
        pitch = clamp(msg.pitch_rad * K1_SIGN_PITCH,
                      K1_HEAD_PITCH_MIN_RAD, K1_HEAD_PITCH_MAX_RAD)
        with self._lock:
            self._cur_yaw = yaw
            self._cur_pitch = pitch
        self._send_rotate_head(yaw, pitch)
        self.get_logger().info(
            f"RAW_ANGLE: yaw={yaw:.3f} pitch={pitch:.3f}")


def main(args=None):
    parser = argparse.ArgumentParser(
        description="K1 HeadControl node — on-robot head controller")
    parser.add_argument('--robot-prefix', type=str, default='Kev1n',
                        help='Robot namespace prefix (default: Kev1n)')
    parsed_args, ros_args = parser.parse_known_args()

    rclpy.init(args=ros_args)
    node = HeadControlNode(parsed_args.robot_prefix)

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Shutting down HeadControl node.")
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()