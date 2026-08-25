import rclpy
import json
import os
import math
import time
from rclpy.node import Node
from geometry_msgs.msg import Twist
from gazebo_msgs.msg import ModelStates
from gazebo_msgs.srv import SetEntityState
from rosgraph_msgs.msg import Clock

try:
    from booster_msgs.msg import RpcReqMsg
    HAS_BOOSTER_MSGS = True
except ImportError:
    HAS_BOOSTER_MSGS = False

# === Field dimensions (must match referee_node.py) ===
FIELD_HALF_LENGTH = 4.5   # X: [-4.5, +4.5]
FIELD_HALF_WIDTH  = 3.0   # Y: [-3.0, +3.0]
OWN_GOAL_X = -FIELD_HALF_LENGTH   # blue defends left goal

# === Goalie blending parameters (Phase 2a, tunable via trial-and-error) ===
# All distances are in % of field half-length (X) or half-width (Y) so the
# goalie logic scales with field size. Absolute meter values are derived at
# runtime via FIELD_HALF_LENGTH / FIELD_HALF_WIDTH.
# NOTE (Phase 5): these constants become obsolete once Phase 5.1 (Kalman
# filter) provides filtered positions + velocity. The bridge override is
# removed entirely and the LLM makes all goalie decisions with good data.
GOALIE_NEAR_GOAL_PCT = 0.22   # ball within 22% of half-length = full goal-line mode (~1.0m)
GOALIE_FAR_GOAL_PCT  = 0.89   # ball beyond 89% of half-length = full angle-block mode (~4.0m)
GOALIE_TACTICAL_WEIGHT = 0.7  # how much bridge overrides LLM target
GOALIE_LLM_WEIGHT      = 0.3  # how much LLM target is preserved
GOALIE_Y_DAMP_NEAR_PCT = 0.50 # Y-tracking dampening when ball near goal (fraction of half-width)
GOALIE_Y_DAMP_FAR_PCT  = 0.30 # Y-tracking dampening when ball far (fraction of half-width)
GOALIE_FORWARD_LIMIT_PCT = 0.56     # max forward X for small teams, as fraction of half-length from own goal (~-2.5m)
GOALIE_FORWARD_LIMIT_LARGE_PCT = 0.89  # max forward X for large teams (5vs5+, future), (~-4.0m)
GOALIE_DEADBAND_PCT = 0.022    # don't move if change < this (fraction of half-length, ~0.1m)
GOALIE_LINE_X_PCT = 0.96       # goal-line X as fraction of half-length from center (~-4.3m)


def smoothstep(t):
    """0 when t<=0, 1 when t>=1, S-curve between."""
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def get_yaw(q):
    siny_cosp = 2 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1 - 2 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


# ====================================================================
# TeamCaptain Slice 1 (v7 pre-work, 2026-08-23) -- CPU-side execution layer.
# Activated via R2K_TEAMCAPTAIN=1 (propagated like R2K_EXPLAIN).
# Division of labor: the LLM decides WHO kicks and the kick TARGET;
# the kick skill computes approach + aim from the LIVE ball position at
# every control tick (10Hz) instead of a stale LLM-call snapshot.
# Evidence: tournament Gen0/Gen1 (no static offset aims AND triggers),
# SP (goalie-Y limit cycle, kicker flapping), WIN (prompt channel closed).
# ====================================================================
TEAMCAPTAIN_ACTIVE = os.getenv("R2K_TEAMCAPTAIN", "0") == "1"

# --- Kick skill state machine (all distances in meters, named constants) ---
KICK_ENGAGE_RANGE = 1.2       # bot within this range of ball -> skill takes over
KICK_OFFSET_FAR = 0.6         # behind-ball stand-off on engage (tournament: only working value)
KICK_OFFSET_NEAR = 0.45       # stand-off shrinks as bot closes (bridges 0.6->0.4 trigger gap)
KICK_SHRINK_START = 1.0       # distance-to-ball where offset shrink begins
KICK_EXECUTE_RANGE = 0.4      # physical execute gate (kick trigger, bridge invariant)
KICK_BEHIND_TOLERANCE = 1.2   # radians: bot must be on behind-side hemisphere of ball
KICK_COOLDOWN_S = 2.0         # same as legacy phantom-kick cooldown
KICK_BEHIND_GATE = os.getenv("R2K_KICK_BEHIND_GATE", "1") == "1"  # TC eval isolation sub-flag

# --- Goalie-Y smoothing (W2-proven formula: cycle amplitude 0.17 -> 0.03m) ---
GOALIE_SMOOTH_Y_GAIN = 0.5   # smoothed goalie target Y = ball_y * GAIN

# --- Idle facing ("always face the ball" when standing still) ---
IDLE_FACE_MAX_LIN = 0.01      # below this linear velocity the bot is "standing"
IDLE_FACE_ANG_GAIN = 2.5      # proportional yaw gain toward the ball
IDLE_FACE_ANG_MAX = 1.5       # rad/s clamp

# ====================================================================
# TeamCaptain Slice 2 (2026-08-23) -- pass-aware execution + wing staging.
# Evidence: 71% of slice-1 goals are Umschaltmomente (ball won at median
# x=+3.8m, goal <3s); only 7% of LLM kicks are real teammate passes; 79%
# carry target~ball (model-native contest pattern -> effectively shots).
# Slice 2 lets the CPU resolve degenerate kick targets:
#   shoot-first gate (protect the proven 0.67 B/match shot volume),
#   else redirect to the best FORWARD option (build-up passes + wings).
# Flags: R2K_PASS_RESOLVE, R2K_WING_STAGE (both require R2K_TEAMCAPTAIN=1).
# ====================================================================
PASS_RESOLVE_ACTIVE = os.getenv("R2K_PASS_RESOLVE", "0") == "1"
WING_STAGE_ACTIVE = os.getenv("R2K_WING_STAGE", "0") == "1"

SHOOT_RANGE_X = 3.0           # ball beyond this X (red half) -> shot allowed
SHOOT_LANE_HALF_WIDTH = 0.7   # no red bot within this Y band of the goal lane
PASS_TARGET_BALL_RADIUS = 0.5 # Kick targets within this radius of ball = degenerate
PASS_FORWARD_MIN_GAIN = 0.5   # resolved pass must advance X by at least this
PASS_OPEN_SPACE = 1.5         # teammate counts as "open" if no red bot this close
WING_STAGE_Y = 2.0            # wing staging target |Y|
WING_STAGE_X = 1.5            # wing staging forward X (opponent half edge)
WING_TRIGGER_BALL_X = 0.5     # ball beyond this X with no wide bot -> stage a wing


def kick_skill_target(ball_x, ball_y, aim_yaw, bot_x, bot_y):
    """Compute the live behind-ball approach point for the kick skill.

    Returns (target_x, target_y, behind_ok):
      - point behind the ball on the ball->aim axis (offset shrinks near),
      - behind_ok: True if the BOT is on the behind hemisphere (execute gate
        component; the bot still needs to be within KICK_EXECUTE_RANGE).
    """
    dx, dy = -math.cos(aim_yaw), -math.sin(aim_yaw)  # from ball toward behind point
    dist = math.hypot(ball_x - bot_x, ball_y - bot_y)
    if dist <= KICK_SHRINK_START:
        t = max(0.0, (dist - KICK_EXECUTE_RANGE) / (KICK_SHRINK_START - KICK_EXECUTE_RANGE))
        offset = KICK_EXECUTE_RANGE + t * (KICK_OFFSET_FAR - KICK_EXECUTE_RANGE)
        offset = max(KICK_OFFSET_NEAR, min(KICK_OFFSET_FAR, offset))
    else:
        offset = KICK_OFFSET_FAR
    tx, ty = ball_x + dx * offset, ball_y + dy * offset
    # bot behind the ball: vector bot->ball roughly aligned with aim direction
    bx, by = ball_x - bot_x, ball_y - bot_y
    bn = math.hypot(bx, by)
    behind_ok = False
    if bn > 1e-6:
         cos_a = (bx * math.cos(aim_yaw) + by * math.sin(aim_yaw)) / bn
         behind_ok = cos_a > math.cos(KICK_BEHIND_TOLERANCE)
    return tx, ty, behind_ok
# v7 adapters (k1 kShoot wrapper / yahboom push) plug in here behind the
# can_kick capability gate -- TODO when hardware-in-the-loop testing begins.


def shoot_lane_open(ball_x, ball_y, red_bots):
    """Shoot-first gate: ball in shooting range AND no red bot blocks the
    straight lane to the opponent goal mouth center (X=+4.5, Y=0).
    red_bots: iterable of (x, y)."""
    if ball_x < SHOOT_RANGE_X:
        return False
    gx, gy = FIELD_HALF_LENGTH, 0.0
    dx, dy = gx - ball_x, gy - ball_y
    n = math.hypot(dx, dy)
    if n < 1e-6:
        return True
    ux, uy = dx / n, dy / n
    for rx, ry in red_bots:
        px, py = rx - ball_x, ry - ball_y
        along = px * ux + py * uy
        if along <= 0 or along >= n:
            continue
        perp = abs(px * uy - py * ux)
        if perp < SHOOT_LANE_HALF_WIDTH:
            return False
    return True


def resolve_pass_target(kicker, ball_x, ball_y, blue_bots, red_bots):
    """Resolve a degenerate Kick (target~ball) into the best FORWARD option.

    blue_bots/red_bots: dicts {bot_name: (x, y)} WITHOUT the kicker.
    Returns (target_x, target_y) or None (fall back to goal shot).
    Priority: open teammate ahead of the ball and ahead of the kicker,
    most open-lane first; ties by forward progress."""
    best, best_score = None, -1.0
    for name, (bx_, by_) in blue_bots.items():
        # forward gain vs ball AND vs kicker (no backward passes)
        gain_ball = bx_ - ball_x
        gain_kicker = bx_ - blue_bots.get(kicker, (ball_x, ball_y))[0] if kicker in blue_bots else gain_ball
        if gain_ball < PASS_FORWARD_MIN_GAIN:
            continue
        # openness: no red bot within PASS_OPEN_SPACE of the receiver
        open_dist = min((math.hypot(rx - bx_, ry - by_) for rx, ry in red_bots),
                        default=99.0)
        if open_dist < PASS_OPEN_SPACE:
            continue
        # lane clearance kicker -> receiver
        dx, dy = bx_ - ball_x, by_ - ball_y
        n = math.hypot(dx, dy)
        lane_clear = True
        if n > 1e-6:
            ux, uy = dx / n, dy / n
            for rx, ry in red_bots:
                px, py = rx - ball_x, ry - ball_y
                along = px * ux + py * uy
                if along <= 0 or along >= n:
                    continue
                if abs(px * uy - py * ux) < SHOOT_LANE_HALF_WIDTH:
                    lane_clear = False
                    break
        if not lane_clear:
            continue
        # score: forward progress + openness
        score = gain_ball + min(open_dist, 3.0)
        if score > best_score:
            best, best_score = (bx_, by_), score
    return best


class HalBridge(Node):
    def __init__(self):
        super().__init__('hal_bridge')
        self.pubs = {}
        self.targets = {} 
        
        script_dir = os.path.dirname(os.path.abspath(__file__))
        base_dir = os.path.dirname(script_dir)
        self.strategy_file = os.path.join(base_dir, 'shared_state', 'current_strategy.json')
        self.relay_file = os.path.join(base_dir, 'ai_tactics', 'active_relay.json')
        
        self.ball_pos = None
        self.hardware_mapping = {}
        self.last_kick_time = {}
        
        self.is_paused = False
        self.last_clock_val = 0.0
        self.last_clock_rcv_time = time.time()
        self.clock_ever_received = False # FIX 1: Verhindert falschen Pause-Modus beim Start!
        
        self.load_hardware_mapping()
        if not HAS_BOOSTER_MSGS:
            self.get_logger().warn("⚠️ booster_msgs nicht gefunden! K1 Hardware-Kontrolle ist deaktiviert.")

        self.create_subscription(ModelStates, '/gazebo/model_states', self.state_cb, 10)
        self.create_subscription(Clock, '/clock', self.clock_cb, 10)
        
        self.create_timer(0.5, self.read_llm_strategy)
        self.create_timer(0.2, self.check_pause_state)
        
        self.set_state_client = self.create_client(SetEntityState, '/gazebo/set_entity_state')
        self.get_logger().info(f"⚙️ HAL Bridge Online! Smarte Hardware-Übersetzung aktiv.")

    def load_hardware_mapping(self):
        if os.path.exists(self.relay_file):
            try:
                with open(self.relay_file, 'r') as f:
                    data = json.load(f)
                    self.hardware_mapping = data.get('mapping', {})
            except Exception as e:
                self.get_logger().error(f"Hardware Mapping Error: {e}")

    def clock_cb(self, msg):
        self.clock_ever_received = True # Uhr tickt, System lebt!
        current_clock = msg.clock.sec + msg.clock.nanosec * 1e-9
        if self.last_clock_val != current_clock:
            if self.is_paused:
                self.get_logger().info("▶️ Gazebo fortgesetzt. Hardware reaktiviert.")
            self.is_paused = False
            self.last_clock_val = current_clock
            self.last_clock_rcv_time = time.time()

    def check_pause_state(self):
        if not self.clock_ever_received: return # Blockiert nicht mehr beim Booten!
        
        if time.time() - self.last_clock_rcv_time > 0.4:
            if not self.is_paused:
                self.is_paused = True
                self.get_logger().warn("⏸️ Gazebo Pause erkannt! Stoppe Hardware...")
                self.stop_all_hardware()

    def stop_all_hardware(self):
        for hw_name, hw_info in self.hardware_mapping.items():
            hw_type = hw_info.get('hardware_type', 'virtual').lower()
            if hw_name not in self.pubs: continue
            try:
                if hw_type == 'k1' and HAS_BOOSTER_MSGS:
                    rpc = RpcReqMsg()
                    rpc.uuid = f"stop_{int(time.time()*1000)}"
                    rpc.header = json.dumps({"api_id": 2000}) 
                    rpc.body = json.dumps({"mode": 1})
                    self.pubs[hw_name].publish(rpc)
                elif hw_type == 'yahboom':
                    t = Twist()
                    self.pubs[hw_name].publish(t)
            except Exception as e:
                self.get_logger().error(f"Stop Error fuer {hw_name}: {e}")

    def read_llm_strategy(self):
        if not os.path.exists(self.strategy_file): return
        try:
            with open(self.strategy_file, 'r') as f:
                data = json.load(f)
                assignments = data.get('assignments', {})
                for bot, task in assignments.items():
                    action = task.get('action', '').lower()
                    role = task.get('role', '')
                    if 'x' in task and 'y' in task:
                        self.targets[bot] = {'x': float(task['x']), 'y': float(task['y']), 'action': action, 'role': role}
                    else:
                        self.targets[bot] = {'action': action, 'role': role}
        except Exception: pass

    def trigger_phantom_kick(self, bot_name, bot_yaw):
        current_time = time.time()
        if current_time - self.last_kick_time.get(bot_name, 0.0) < 2.0: return
        self.last_kick_time[bot_name] = current_time

        req = SetEntityState.Request()
        req.state.name = 'soccer_ball' 
        req.state.reference_frame = 'world'
        req.state.pose.position.x = self.ball_pos.x 
        req.state.pose.position.y = self.ball_pos.y
        req.state.pose.position.z = 0.10 
        
        kick_power = 6.0  
        req.state.twist.linear.x = math.cos(bot_yaw) * kick_power
        req.state.twist.linear.y = math.sin(bot_yaw) * kick_power
        req.state.twist.linear.z = 1.0 
        self.set_state_client.call_async(req)

    def _resolve_kick_aim(self, target, target_bot, aim_yaw):
        """Slice 2 pass resolution: decide the effective aim for a Kick.

        Rules (shoot-first gate):
          1. Real pass targets (farther than PASS_TARGET_BALL_RADIUS from the
             ball) stay untouched -- the LLM's intent is honored.
          2. Degenerate targets (~ball): if a shot is on (ball beyond
             SHOOT_RANGE_X with an open lane), shoot at goal (return goal aim).
          3. Else resolve a forward pass to the best open teammate; fall back
             to the goal aim when no option qualifies.
        Returns the (possibly updated) aim_yaw.
        """
        ball_x, ball_y = self.ball_pos.x, self.ball_pos.y
        goal_yaw = math.atan2(0.0 - ball_y, FIELD_HALF_LENGTH - ball_x)
        has_target = target.get('target_x') is not None and target.get('target_y') is not None
        if has_target:
            try:
                tx, ty = float(target['target_x']), float(target['target_y'])
            except (TypeError, ValueError):
                return aim_yaw
            if math.hypot(tx - ball_x, ty - ball_y) > PASS_TARGET_BALL_RADIUS:
                return aim_yaw  # real pass intent -- honor it
        # degenerate or no target: shoot-first gate
        red_bots = [(p.position.x, p.position.y) for name, p in self._last_bot_poses.items()
                    if name.startswith('red')] if hasattr(self, '_last_bot_poses') else []
        if shoot_lane_open(ball_x, ball_y, red_bots):
            return goal_yaw
        blue_bots = {name: (p.position.x, p.position.y)
                     for name, p in self._last_bot_poses.items()
                     if name.startswith('blue') and name != target_bot} if hasattr(self, '_last_bot_poses') else {}
        pass_tgt = resolve_pass_target(target_bot, ball_x, ball_y, blue_bots, red_bots)
        if pass_tgt is not None:
            return math.atan2(pass_tgt[1] - ball_y, pass_tgt[0] - ball_x)
        return goal_yaw

    def state_cb(self, msg):
        if self.is_paused: return

        try:
            # Cache all bot poses for CPU-side strategy (Slice 2: pass
            # resolution + wing staging need teammate/opponent positions).
            self._last_bot_poses = {}
            for i, name in enumerate(msg.name):
                if name.startswith(('blue', 'red')):
                    self._last_bot_poses[name] = msg.pose[i]
            ball_idx = next((i for i, name in enumerate(msg.name) if 'ball' in name.lower()), None)
            if ball_idx is not None:
                self.ball_pos = msg.pose[ball_idx].position
            if not self.ball_pos: return

            for hw_name, hw_info in self.hardware_mapping.items():
                hw_type = hw_info.get('hardware_type', 'virtual').lower()
                topic = hw_info.get('topic', f'/{hw_name}/cmd_vel')
                target_bot = hw_info.get('mirror_of', hw_name)
                
                if target_bot not in self.targets: continue
                target = self.targets[target_bot]

                if hw_name not in self.pubs:
                    if hw_type == 'k1' and HAS_BOOSTER_MSGS:
                        self.pubs[hw_name] = self.create_publisher(RpcReqMsg, topic, 10)
                    else:
                        self.pubs[hw_name] = self.create_publisher(Twist, topic, 10)
                
                bot_idx = next((i for i, name in enumerate(msg.name) if target_bot in name.lower()), None)
                if bot_idx is None: continue
                    
                bot_pose = msg.pose[bot_idx]
                cx, cy = bot_pose.position.x, bot_pose.position.y
                cyaw = get_yaw(bot_pose.orientation)
                
                dist_to_ball = math.hypot(self.ball_pos.x - cx, self.ball_pos.y - cy)
                action = target.get('action', '').lower()
                is_attacking = False

                if action == 'hold':
                    # Active brake: publish zero velocity to stop the bot
                    # (not just skip -- skipping lets the bot coast on its
                    # last velocity command, which is unsafe on hardware)
                    if hw_type == 'k1' and HAS_BOOSTER_MSGS:
                        rpc = RpcReqMsg()
                        rpc.uuid = f"hold_{int(time.time()*1000)}"
                        rpc.header = json.dumps({"api_id": 2001})
                        rpc.body = json.dumps({"vx": 0.0, "vy": 0.0, "vyaw": 0.0})
                        self.pubs[hw_name].publish(rpc)
                    else:
                        t = Twist()
                        self.pubs[hw_name].publish(t)
                    continue

                if action == 'kick':
                    is_attacking = True
                    # Pass-aware kick direction (priority: pass target > role > goal):
                    # 1. If Kick has target_x/target_y, aim toward that position (pass to teammate)
                    # 2. If role is goalie, kick upfield away from own goal (clearance)
                    # 3. Otherwise aim at opponent goal center (X=+4.5, Y=0)
                    if target.get('target_x') is not None and target.get('target_y') is not None:
                        aim_yaw = math.atan2(float(target['target_y']) - self.ball_pos.y, float(target['target_x']) - self.ball_pos.x)
                    elif target.get('role', '') == 'goalie':
                        aim_yaw = math.atan2(-self.ball_pos.y * 0.5, 4.5 - self.ball_pos.x)
                    else:
                        aim_yaw = math.atan2(0.0 - self.ball_pos.y, 4.5 - self.ball_pos.x)
                    # Slice 2 -- pass resolution: degenerate targets (~ball) get
                    # resolved CPU-side. Shoot-first gate protects the proven
                    # shot volume (71% of goals are box-area Umschaltmomente).
                    if TEAMCAPTAIN_ACTIVE and PASS_RESOLVE_ACTIVE:
                        aim_yaw = self._resolve_kick_aim(target, target_bot, aim_yaw)
                    if TEAMCAPTAIN_ACTIVE:
                        # Kick skill: live behind-ball recompute each tick (10Hz),
                        # offset shrinks on approach, execute gated on range + behind-side.
                        target_x, target_y, behind_ok = kick_skill_target(
                            self.ball_pos.x, self.ball_pos.y, aim_yaw, cx, cy)
                    else:
                        behind_x, behind_y = self.ball_pos.x - math.cos(aim_yaw) * 0.6, self.ball_pos.y - math.sin(aim_yaw) * 0.6
                        dist_to_behind = math.hypot(behind_x - cx, behind_y - cy)
                        target_x, target_y = (behind_x, behind_y) if dist_to_behind > 0.3 and dist_to_ball > 0.5 else (self.ball_pos.x, self.ball_pos.y)
                    target['_aim_yaw'] = aim_yaw
                    target['_behind_ok'] = behind_ok if TEAMCAPTAIN_ACTIVE else True
                else:
                    target_x, target_y = target.get('x', cx), target.get('y', cy)

                # Goalie tactical blending (Approach C, Phase 2a)
                # NOTE (Phase 5): this block is removed once Phase 5.1 (Kalman
                # filter) gives the LLM filtered positions + velocity. The
                # bridge override becomes unnecessary.
                is_goalie = target.get('role', '') == 'goalie'
                if is_goalie and action != 'kick' and self.ball_pos:
                    # Derive absolute meter values from field dimensions
                    near_dist = GOALIE_NEAR_GOAL_PCT * FIELD_HALF_LENGTH
                    far_dist  = GOALIE_FAR_GOAL_PCT  * FIELD_HALF_LENGTH
                    deadband  = GOALIE_DEADBAND_PCT  * FIELD_HALF_LENGTH
                    line_x    = -(GOALIE_LINE_X_PCT * FIELD_HALF_LENGTH)
                    fwd_limit = -(GOALIE_FORWARD_LIMIT_PCT * FIELD_HALF_LENGTH)
                    damp_near = GOALIE_Y_DAMP_NEAR_PCT
                    damp_far  = GOALIE_Y_DAMP_FAR_PCT
                    y_clamp   = FIELD_HALF_WIDTH * 0.5

                    ball_dist_to_goal = math.hypot(self.ball_pos.x - OWN_GOAL_X, self.ball_pos.y)

                    # Smooth transition: 0 when ball near goal, 1 when ball far
                    far_weight = smoothstep((ball_dist_to_goal - near_dist) /
                                            (far_dist - near_dist))

                    # Goal-line position (ball near): stay at line_x, damped Y
                    goal_line_x = line_x
                    goal_line_y = max(-y_clamp, min(y_clamp, self.ball_pos.y * damp_near))

                    # Angle-block position (ball far): on ball-goal line, forward, damped Y
                    ratio = min(0.5, 2.0 / max(ball_dist_to_goal, 0.1))
                    angle_x = max(OWN_GOAL_X + (self.ball_pos.x - OWN_GOAL_X) * ratio, fwd_limit)
                    angle_y = self.ball_pos.y * damp_far

                    # Blend between goal-line (near) and angle-block (far)
                    tactical_x = goal_line_x * (1 - far_weight) + angle_x * far_weight
                    tactical_y = goal_line_y * (1 - far_weight) + angle_y * far_weight

                    # Blend: tactical correction + LLM's own target
                    target_x = tactical_x * GOALIE_TACTICAL_WEIGHT + target_x * GOALIE_LLM_WEIGHT
                    target_y = tactical_y * GOALIE_TACTICAL_WEIGHT + target_y * GOALIE_LLM_WEIGHT

                    # TeamCaptain: goalie-Y smoothing (W2-proven formula) -- kills
                    # the LLM's Y limit cycle (SP finding: +/-0.1-0.5m alternation).
                    if TEAMCAPTAIN_ACTIVE:
                        target_y = self.ball_pos.y * GOALIE_SMOOTH_Y_GAIN

                    # Deadband: don't issue movement if change < threshold
                    if math.hypot(target_x - cx, target_y - cy) < deadband:
                        target_x, target_y = cx, cy  # hold position

                # Slice 2 -- wing staging: when blue attacks (ball forward) but
                # no field bot is wide, stage the widest non-kicking field bot
                # toward the open wing (W5-proven geometry, CPU-delivered).
                if (TEAMCAPTAIN_ACTIVE and WING_STAGE_ACTIVE and action != 'kick'
                        and not is_goalie and self.ball_pos
                        and self.ball_pos.x > WING_TRIGGER_BALL_X):
                    if not hasattr(self, '_last_bot_poses'):
                        pass
                    else:
                        wide = [n for n, p in self._last_bot_poses.items()
                                if n.startswith('blue') and n != 'blue_1'
                                and abs(p.position.y) >= WING_STAGE_Y]
                        if not wide:
                            # pick the non-kicking field bot farthest from ball Y-side
                            cands = [n for n, p in self._last_bot_poses.items()
                                     if n.startswith('blue') and n != 'blue_1'
                                     and n != target_bot]
                            if cands:
                                staged = cands[0]
                                sp = self._last_bot_poses[staged].position
                                wing_y = WING_STAGE_Y if sp.y >= 0 else -WING_STAGE_Y
                                if abs(target_y - wing_y) > 0.5 or abs(target_x - WING_STAGE_X) > 0.5:
                                    target_x, target_y = WING_STAGE_X, wing_y

                dx, dy = target_x - cx, target_y - cy
                distance = math.hypot(dx, dy)
                target_yaw = math.atan2(dy, dx)
                angle_diff = target_yaw - cyaw
                
                while angle_diff > math.pi: angle_diff -= 2 * math.pi
                while angle_diff < -math.pi: angle_diff += 2 * math.pi
                
                lin_x, ang_z = 0.0, 0.0
                kick_execute = False
                if is_attacking and dist_to_ball <= KICK_EXECUTE_RANGE:
                    if TEAMCAPTAIN_ACTIVE and KICK_BEHIND_GATE:
                        # Skill execute gate: physical range AND behind-side
                        # (sim2real honesty: no teleport kicks from bad angles)
                        kick_execute = bool(target.get('_behind_ok', True))
                    else:
                        kick_execute = True
                    if kick_execute and hw_type == 'virtual':
                        self.trigger_phantom_kick(
                            target_bot,
                            target.get('_aim_yaw', cyaw))
                else:
                    if distance > 0.15:
                        ang_z = max(min(angle_diff * 3.0, 2.5), -2.5)
                        lin_x = 0.8 if abs(angle_diff) < 0.5 else 0.2
                    elif TEAMCAPTAIN_ACTIVE and self.ball_pos:
                        # Idle facing: standing still -> aim at the ball
                        face_yaw = math.atan2(self.ball_pos.y - cy, self.ball_pos.x - cx)
                        face_diff = face_yaw - cyaw
                        while face_diff > math.pi: face_diff -= 2 * math.pi
                        while face_diff < -math.pi: face_diff += 2 * math.pi
                        ang_z = max(min(face_diff * IDLE_FACE_ANG_GAIN, IDLE_FACE_ANG_MAX),
                                    -IDLE_FACE_ANG_MAX)
                
                if hw_type == 'k1':
                    if not HAS_BOOSTER_MSGS: continue
                    rpc = RpcReqMsg()
                    rpc.uuid = f"cmd_{int(time.time()*1000)}"
                    if is_attacking and kick_execute:
                        rpc.header = json.dumps({"api_id": 2000})
                        rpc.body = json.dumps({"mode": 1})
                    else:
                        rpc.header = json.dumps({"api_id": 2001})
                        rpc.body = json.dumps({"vx": round(lin_x, 3), "vy": 0.0, "vyaw": round(ang_z, 3)})
                    self.pubs[hw_name].publish(rpc)
                else:
                    t = Twist()
                    t.linear.x = lin_x
                    t.angular.z = ang_z
                    self.pubs[hw_name].publish(t)
                    
        except Exception as e:
            self.get_logger().error(f"Bridge Execution Error: {e}")

def main():
    rclpy.init()
    node = HalBridge()
    try: rclpy.spin(node)
    except KeyboardInterrupt: pass
    finally: node.destroy_node(); rclpy.shutdown()

if __name__ == '__main__':
    main()
