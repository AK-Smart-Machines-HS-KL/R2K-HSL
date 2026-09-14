import rclpy
import json
import os
import math
import re
import time
from rclpy.node import Node
from geometry_msgs.msg import Twist
from gazebo_msgs.msg import ModelStates
from gazebo_msgs.srv import SetEntityState
from rosgraph_msgs.msg import Clock
from std_msgs.msg import Int32
from sensor_msgs.msg import Imu
from nav_msgs.msg import Odometry

import head_cmds as hc

try:
    from booster_msgs.msg import RpcReqMsg
    HAS_BOOSTER_MSGS = True
except ImportError:
    HAS_BOOSTER_MSGS = False

try:
    from booster_interface.msg import Odometer
    HAS_BOOSTER_ODOM = True
except ImportError:
    HAS_BOOSTER_ODOM = False

# === Calib mode (direct hardware addressing, no mirror_of resolution) ===
# Mode merge (2026-09-08): calib = the Gazebo-free field stack — the
# hardware dispatch runs on a wall-clock timer (state_cb never dispatches
# in CALIB), the evaluator polls task_input.json directly, no gzserver/
# aggregator/Ollama boot. --nosim is a launcher alias of --calib.
CALIB = os.getenv('R2K_CALIB') == '1'

# === K1 odometry visibility (mirror-drift monitoring) ===
# K1 stays a command mirror of blue1 in demo; its real odom is published to
# its own state file (NOT Worldstate.json — the aggregator rebuilds that file
# at 10Hz and would wipe/race any foreign entry). Evaluator/LLM payload
# deliberately excludes k1 (executor hallucinates assignments for visible bots).
K1_ODOM_DRIFT_M = 0.25          # warn when K1 strays this far from its sim twin
K1_DRIFT_WARN_DEBOUNCE_S = 1.0  # min seconds between drift warnings

# === Yahboom calib (open-loop timed drive) ===
# Encoder odom unreliable on real floors (slip) — calibration drives by TIME,
# the operator measures the real delta with a tape and CLI logs slip_factor
# (measured / commanded). Turn convention: + = CCW (ROS yaw).
Y_CALIB_VX = 0.2      # m/s — straight-line calib speed
Y_CALIB_VYAW = 1.2    # rad/s — calib ROTATIONAL cap (face/turn/goto/swings).
                      # User feedback 2026-09-08: "turn speed too low" at 0.5 —
                      # live steady-state delivers ~0.89x commanded (the 90°
                      # open-loop test: 80° of 90° in the nominal window; only
                      # SHORT turns lose time to motor spin-up). 1.2 keeps a
                      # margin under the 1.5 firmware ceiling. Stall safety
                      # rests on the XRCE quarantine + the 12Hz cmd_vel
                      # throttle, not on this cap.
Y_CALIB_PUB_PERIOD_S = 0.08  # ~12Hz cmd_vel for calib yahbooms — the
                              # firmware PID needs ~10Hz; the sustained
                              # 48Hz stream correlates with the XRCE stalls
Y_CALIB_SHAKE_FREQ_HZ = 1.0  # calib 'say no' shake: the demo profile
                              # (±100° @ 2Hz) saturates the vyaw cap with
                              # 0.25s alternating half-cycles — the board
                              # yaw PID cannot reverse that fast, so the
                              # commands averaged to ZERO (live 2026-09-08:
                              # gesture armed + published, yaw never moved;
                              # a CONSTANT 0.5 rad/s turn works). 1Hz gives
                              # 0.5s half-cycles (~±14° swings at the cap).
Y_CALIB_SHAKE_AMP_DEG = 45.0 # visible but trackable at the 0.5 rad/s cap

# === Yahboom odom rehearsal (K1 field-test prep, 2026-09-08) ===
# Yahbooms mirror the K1's pipeline (odom watch -> state file -> closed-loop
# Goto -> trace) so the CLI/exec/log-reading flow is rehearsed on cheap
# hardware before the K1 field session. Encoder odom slips on the floor
# (est. ±30% — ACCEPTED; rehearsal vehicle, not accuracy target): arrivals
# are coarse by design and auto-PASS thresholds are informational.
Y_GOTO_XY_TOL = 0.15            # m — arrival deadband on the ESTIMATE frame
                                 # (loop converges while wheels stream odom;
                                 # physical slip ±30% is odom's error, not
                                 # the deadband's — 0.35 parked 0.26m short,
                                  # live 2026-09-08)
                                  # (arrival is DISTANCE-ONLY for both hw
                                  # types — park-range bearings are geometric
                                  # noise; live-proven on real K1 2026-09-08,
                                  # see the arrival site in the goto branch)
Y_GOTO_REVERSE_BEARING = 2.356 # rad (135°) — target behind the bot: drive
                                 # BACKWARD instead of the 180° in-place
                                 # turn (user request 2026-09-08). A slow
                                 # rotation compounds ±30% encoder yaw error
                                 # and looks wrong to a soccer observer;
                                 # reversing reaches rear targets directly
                                 # (diff-drive has no preferred direction).
Y_GOTO_ACCEL_VX = 0.5           # m/s² — differential drive ramp
Y_GOTO_ACCEL_VYAW = 2.0         # rad/s² — reaches the 1.2 cap in 0.6s (was
                                 # 1.0: the ramp alone ate the turn budget)
Y_ODOM_FACTOR = 1.0             # no vendor correction (K1 has 0.8)
# Encoder odom streams ONLY while wheels turn (Phase-0 echo finding
# 2026-09-08) — any gate that requires fresh odom to MOVE deadlocks every
# rest->goto transition (y1 live: brake -> no motion -> no odom). Approach 6:
# the goto loop drives on a bridge-side ESTIMATE (calibration start pose =
# odom-frame origin 0,0,0 — user contract; external start info later),
# integrates the last COMMANDED velocities (dead reckoning, ±30% accepted)
# and resyncs to the encoder on every NEW sample. Odom is CORRECTION,
# never PERMISSION. Safety stays with the imu liveness gate (XRCE
# quarantine) which mutes publishing on a stalled client regardless of
# the estimate.

# === K1 Goto (calibration odom loop) — vendor two-phase recipe (2026-09-06) ===
# Source: ~/Workspace/robocup_demo (vendor RoboCup brain):
#   robot_client.cpp:149-248 moveToPoseOnField — rotate-in-place when heading
#   error exceeds turn_threshold BEFORE translating (vendor comments:
#   "Large angle, turn towards the target first"), hysteresis band
#   (breakOscillate) prevents phase flickering, arrival = x/y/theta tolerances.
#   config: striker turn_threshold 0.5 / vtheta 1.5; goalie 0.8 / vtheta 1.0;
#   odom_factor 0.8 (K1 odom over-reads ~20% — vendor scales it down).
# Field evidence driving this port: 2026-09-06 K1 turned in place 81s with
# vx throttled but never zeroed (simultaneous drive+turn breaks the gait).
K1_GOTO_VX_MAX = 0.7            # m/s — vendor striker value (firmware hard gate 1.1)
K1_GOTO_VYAW_MAX = 1.0          # rad/s — vendor goalie value (firmware hard gate 1.5)
K1_GOTO_ACCEL_VX = 1.5          # m/s² — 0→max in ~0.47s
K1_GOTO_ACCEL_VYAW = 2.0        # rad/s² — 0→max in ~0.5s
K1_GOTO_TURN_THRESHOLD = 0.5    # rad — heading error above this: vx=0, rotate only
K1_GOTO_XY_TOL = 0.2            # m — arrival distance (vendor xTolerance)
                                 # (arrival is DISTANCE-ONLY — the former
                                 # K1_GOTO_THETA_TOL heading term caused the
                                 # endless arrival spin on real K1: the
                                 # park-range bearing is noise; 2026-09-08)
K1_GOTO_PHASE_HYSTERESIS = 0.3  # rad — exit turn-phase only below (THRESHOLD - HYSTERESIS)
K1_ODOM_FACTOR = 0.8            # vendor K1 odom correction; controller-side only,
                                 # logs/state files keep raw odom (physical truth)
K1_ODOM_STALE_S = 3.0           # k1 odom streams ~490Hz — this stale = robot silent

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

# === PS4 Teleop (Option A, yahboom-only experiment) ===
TELEOP_STATE_PATH = os.path.join(os.path.dirname(__file__), "..", "shared_state", "teleop_state.json")
TELEOP_HEARTBEAT_S = 0.3

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

        # --- Demo head control state (calibration mode only) ---
        # Gesture runtime keyed by mirrored bot: {"id", "gesture", "t0"}
        self._head_gesture = {}
        # Completed gesture ids (prevent restart while the assignment persists)
        self._head_done = {}
        # Edge-triggered static pose + burst counter keyed by hw_name
        self._last_head_cmd = {}
        self._head_burst_left = {}
        self._servo_pubs = {}
        self._head_brake_tick = {}
        # XRCE session liveness (per hw_name): last imu receipt + quarantine
        self._imu_last_seen = {}
        self._imu_quarantined = {}
        self._drain_tick = {}
        # Face snapshots per mirrored bot: {'id', 'tgt', 'arrived'}
        self._face_state = {}
        # Seq cursors per mirrored bot: {'id', 'idx', 't_step', 'move_latched'}
        self._seq_state = {}
        # Body-gesture runtime per hw_name (gimbal-less 'say' on the chassis)
        self._body_gesture = {}
        # K1 odometry (per hw_name): latest odom from /Kev1n/odometer_state
        self._k1_odom = {}  # {'k1': {'x': 0.0, 'y': 0.0, 'theta': 0.0, 't': 0.0}}
        self._k1_odom_subs = {}  # subscription objects (keep alive for rclpy)
        # Yahboom odometry (per hw_name): latest RAW odom from <ns>/odom_raw
        # (K1-pipeline rehearsal — same state-file/trace/goto machinery)
        self._y_odom = {}   # {'y1': {'x': .., 'y': .., 'theta': .., 't': ..}}
        self._y_odom_subs = {}  # subscription objects (keep alive for rclpy)
        # Yahboom goto ESTIMATE (per hw_name): calibration start pose
        # (0,0,0) + commanded-velocity integration, resynced by every NEW
        # raw odom sample (odom-as-correction, approach 6, 2026-09-08)
        self._y_est = {}         # {'y1': {'x','y','theta','t','src'}}
        self._y_last_raw_t = {}  # {'y1': <t of last consumed raw sample>}
        # cmd_vel throttle state (per hw_name): last publish time
        self._y_last_pub_t = {}  # {'y1': <t>}
        self._k1_drift_warn_ts = 0.0  # drift-warning debounce
        # Goto calibration state (per hw_name, k1 + yahboom): rate limiting
        self._goto_state = {}  # {'k1': {'last_vx', 'last_vyaw', 'last_t'}}
        # Arrival log debounce (per hw_name): last (x,y) target that logged
        # ARRIVED — one line per destination, not one per tick
        self._goto_arrived_id = {}  # {'k1': (0.5, 0.0)}
        # TimedMove calib state (per hw_name): vx/vyaw latch + end deadline
        self._timedmove_state = {}  # {'y1': {'vx', 'vyaw', 't_end'}}
        # Odom trace file (JSONL, 0.5s per sample — matches _publish_odom_states
        # schedule; k1 + yahboom records share the run file, keyed by "bot")
        _run_id = os.getenv('R2K_RUN_ID', f"run_{int(time.time())}")
        self._odom_trace_path = os.path.join('logs', f"k1_trace_{_run_id}.jsonl")
        os.makedirs('logs', exist_ok=True)
        
        self.is_paused = False
        self.last_clock_val = 0.0
        self.last_clock_rcv_time = time.time()
        self.clock_ever_received = False # FIX 1: Verhindert falschen Pause-Modus beim Start!
        
        self.load_hardware_mapping()
        if not HAS_BOOSTER_MSGS:
            self.get_logger().warn("⚠️ booster_msgs nicht gefunden! K1 Hardware-Kontrolle ist deaktiviert.")
        # Odom watches are ROBOT-side (relay-publishes regardless of Gazebo) —
        # subscribe eagerly at boot, not lazily in state_cb (k1: odometer_state,
        # yahboom: odom_raw — the function gates per hardware type).
        for _hw, _info in self.hardware_mapping.items():
            self._ensure_odom_watch(_hw, _info)

        self.create_subscription(ModelStates, '/gazebo/model_states', self.state_cb, 10)
        self.create_subscription(Clock, '/clock', self.clock_cb, 10)
        
        self.create_timer(0.5, self.read_llm_strategy)
        self.create_timer(0.2, self.check_pause_state)
        # CALIB = wall-clock tick (mode merge 2026-09-08): ONE dispatch
        # path for all calib sessions — state_cb never dispatches in
        # CALIB (see state_cb), the timer owns the hardware loop at a
        # deterministic rate regardless of any sim presence.
        if CALIB:
            self.create_timer(0.05, self._nosim_hw_tick)
            self.get_logger().info("CALIB: hardware dispatch on a 20Hz "
                                   "wall-clock timer (single tick path).")
        
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
        self._head_gesture.clear()
        self._head_done.clear()
        self._head_burst_left.clear()
        self._imu_quarantined.clear()
        self._drain_tick.clear()
        self._face_state.clear()
        self._seq_state.clear()
        self._body_gesture.clear()
        self._goto_state.clear()
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

    # Extra keys forwarded from strategy JSON to the per-bot target
    # (demo Face/Head actions carry no x/y and would otherwise be dropped)
    TARGET_EXTRA_KEYS = ('yaw', 'relative_angle', 'pan_deg', 'tilt_deg',
                         'gesture', 'cycles', 'id', 'steps',
                         'vx', 'vyaw', 'duration_s')

    def read_llm_strategy(self):
        if not os.path.exists(self.strategy_file): return
        try:
            with open(self.strategy_file, 'r') as f:
                data = json.load(f)
                assignments = data.get('assignments', {})
                fresh = {}
                for bot, task in assignments.items():
                    action = task.get('action', '').lower()
                    role = task.get('role', '')
                    tgt = {'action': action, 'role': role}
                    if 'x' in task and 'y' in task:
                        tgt['x'] = float(task['x'])
                        tgt['y'] = float(task['y'])
                    for k in self.TARGET_EXTRA_KEYS:
                        if k in task:
                            tgt[k] = task[k]
                    fresh[bot] = tgt
                self.targets = fresh
                # DIAG: log what we loaded
                for bot, tgt in fresh.items():
                    self.get_logger().info(f"LOADED target for {bot}: {tgt}")
                if not fresh:
                    self.get_logger().info("LOADED empty strategy (no assignments)")
        except Exception as e:
            self.get_logger().error(f"Strategy parse error: {e}")
        # Publish per-bot odom state files (0.5s cadence, same timer)
        self._publish_odom_states()

    def _write_odom_sample(self, hw_name, odom, src):
        """One sample to shared_state/<hw>_odom.json (atomic rename) + one
        trace record. 'src' names the data source ('odometer_state' |
        'odom_raw' | 'integrated' | 'start') — honest rehearsal telemetry:
        the CLI/analyze leg can tell physical truth from dead-reckoned
        belief. Non-blocking: state-file failure must not kill the bridge."""
        data = {'x': round(odom['x'], 4), 'y': round(odom['y'], 4),
                'theta': round(odom['theta'], 4), 't': odom['t'],
                'src': src}
        path = os.path.join(os.path.dirname(self.strategy_file),
                            f'{hw_name}_odom.json')
        try:
            tmp = path + '.tmp'
            with open(tmp, 'w') as f:
                json.dump(data, f)
            os.replace(tmp, path)
        except Exception:
            pass
        try:
            target = self.targets.get(hw_name, {})
            trace = {
                "t_wall": time.time(),
                "t_odom": odom['t'],
                "bot": hw_name,
                "pose": {"x": data['x'], "y": data['y'],
                         "theta": data['theta']},
                "src": src,
                "target": {"action": target.get('action'),
                           "x": target.get('x'), "y": target.get('y')},
            }
            with open(self._odom_trace_path, 'a') as f:
                f.write(json.dumps(trace) + '\n')
        except Exception:
            pass

    def _publish_odom_states(self):
        """Publish each bot's odometry to shared_state/<hw>_odom.json (0.5s
        cadence, atomic rename) + trace records to logs/k1_trace_<run_id>.jsonl.
        k1: raw odometer_state; yahboom: the FRESHER of raw odom and the goto
        estimate (encoder is silent at rest — the estimate carries the
        belief; src field names which). Own state files on purpose:
        Worldstate.json is rebuilt at 10Hz by state_aggregator.py — a
        foreign entry would be wiped/raced. K1 additionally warns on mirror
        drift vs the blue_1 sim pose."""
        for hw_name, odom in self._k1_odom.items():
            if odom.get('t', 0) > 0:
                self._write_odom_sample(hw_name, odom, 'odometer_state')
        for hw_name, odom in self._y_odom.items():
            est = self._y_est.get(hw_name)
            if est is not None and (odom.get('t', 0) <= 0
                                    or est.get('t', 0) >= odom.get('t', 0)):
                self._write_odom_sample(hw_name, est,
                                        est.get('src', 'integrated'))
            elif odom.get('t', 0) > 0:
                self._write_odom_sample(hw_name, odom, 'odom_raw')
        # Mirror-drift detection vs blue_1 sim pose (50Hz cache from state_cb)
        # — K1 only. Yahboom divergence vs sim twins is EXPECTED under closed
        # loop (sim twin follows sim physics, the robot its own odometry);
        # warning on it would just spam the rehearsal log.
        odom = next((o for o in self._k1_odom.values() if o.get('t', 0) > 0), None)
        if odom is None:
            return
        pose = getattr(self, '_last_bot_poses', {}).get('blue_1')
        if pose is None:
            return
        dist = math.hypot(pose.position.x - odom['x'], pose.position.y - odom['y'])
        now = time.time()
        if dist > K1_ODOM_DRIFT_M and now - self._k1_drift_warn_ts >= K1_DRIFT_WARN_DEBOUNCE_S:
            self._k1_drift_warn_ts = now
            self.get_logger().warning(
                f"⚠️ K1 drift: {dist:.2f}m from blue_1 sim "
                f"(blue_1=({pose.position.x:.2f},{pose.position.y:.2f}) "
                f"k1=({odom['x']:.2f},{odom['y']:.2f}))")
    
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

    def _publish_motion(self, hw_name, hw_type, lin_x, ang_z, kick_fire=False):
        """Common velocity publisher: Twist for virtual/yahboom, RPC 2001 for K1.
        kick_fire sends the K1 kick-mode switch (2000) instead of a Move.
        CALIB yahboom: throttled to Y_CALIB_PUB_PERIOD_S — the dispatch
        ticks at 20-50Hz but the firmware PID needs ~10Hz; halving+ the
        sustained input stream is the strongest stall correlate (3 XRCE
        stalls on the first heavy-motion day, 2026-09-08)."""
        if hw_type == 'yahboom' and CALIB:
            now = time.time()
            if now - self._y_last_pub_t.get(hw_name, 0.0) < Y_CALIB_PUB_PERIOD_S:
                return
            self._y_last_pub_t[hw_name] = now
        if hw_type == 'k1':
            if not HAS_BOOSTER_MSGS: return
            rpc = RpcReqMsg()
            rpc.uuid = f"cmd_{int(time.time()*1000)}"
            if kick_fire:
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

    def _servo_pubs_for(self, hw_name, hw_info):
        """Lazily create (pan, tilt) Int32 publishers on <ns>/servo_s1|s2.
        None for hardware without a gimbal (K1 uses RPC 2004, virtual has none)."""
        if hw_name in self._servo_pubs:
            return self._servo_pubs[hw_name]
        hw_type = hw_info.get('hardware_type', 'virtual').lower()
        pubs = None
        if hw_type not in ('k1', 'virtual'):
            ns = hw_info.get('topic', f'/{hw_name}/cmd_vel').rsplit('/', 1)[0]
            pubs = (self.create_publisher(Int32, f'{ns}/servo_s1', 10),
                    self.create_publisher(Int32, f'{ns}/servo_s2', 10))
        self._servo_pubs[hw_name] = pubs
        return pubs

    def _ensure_liveness_watch(self, hw_name, hw_info):
        """Eagerly create the imu liveness subscription for Yahboom bots.
        The ESP32 client publishes imu at 13-25Hz; a stalled client stops
        publishing while its network stack stays alive (root cause
        2026-09-05). Non-yahboom hw gets a None marker (guard = alive)."""
        if hw_name in self._imu_last_seen:
            return
        hw_type = hw_info.get('hardware_type', 'virtual').lower()
        self._imu_last_seen[hw_name] = None
        if hw_type == 'yahboom':
            ns = hw_info.get('topic', f'/{hw_name}/cmd_vel').rsplit('/', 1)[0]
            self.create_subscription(
                Imu, f'{ns}/imu',
                lambda m, _n=hw_name: self._imu_last_seen.__setitem__(_n, time.time()),
                10)
    
    def _ensure_odom_watch(self, hw_name, hw_info):
        """Eagerly create the odometry subscription per hardware type.
        K1: <ns>/odometer_state (booster_interface/msg/Odometer, ~490Hz) —
        k1_odom.json + mirror-drift detection.
        Yahboom: <ns>/odom_raw (nav_msgs/Odometry from the ESP32 YB_Car_Node,
        encoder-based) — K1-pipeline rehearsal (2026-09-08): state file +
        trace + closed-loop Goto feedback. ±30% slip accepted by design.
        Other hw gets no subscription. Msg type for odom_raw is the expected
        nav_msgs/Odometry (odom_publisher sample lineage) — verify live on
        first lab contact (Phase 0): ros2 topic info /blue_1/odom_raw -v."""
        if hw_name in self._k1_odom or hw_name in self._y_odom:
            return  # already subscribed
        hw_type = hw_info.get('hardware_type', 'virtual').lower()
        ns = hw_info.get('topic', f'/{hw_name}/cmd_vel').rsplit('/', 1)[0]
        if hw_type == 'k1' and HAS_BOOSTER_ODOM:
            sub = self.create_subscription(
                Odometer, f'{ns}/odometer_state',
                lambda m, _n=hw_name: self._k1_odom.__setitem__(_n, {
                    'x': float(m.x),
                    'y': float(m.y),
                    'theta': float(m.theta),
                    't': time.time()
                }),
                10)
            self._k1_odom_subs[hw_name] = sub  # keep reference alive
            self._k1_odom[hw_name] = {'x': 0.0, 'y': 0.0, 'theta': 0.0, 't': 0.0}
            self.get_logger().info(f"📍 K1 odom subscription active for {hw_name} on {ns}/odometer_state")
        elif hw_type == 'yahboom':
            sub = self.create_subscription(
                Odometry, f'{ns}/odom_raw',
                lambda m, _n=hw_name: self._y_odom.__setitem__(
                    _n, HalBridge._odom_from_nav(m)),
                10)
            self._y_odom_subs[hw_name] = sub  # keep reference alive
            self._y_odom[hw_name] = {'x': 0.0, 'y': 0.0, 'theta': 0.0, 't': 0.0}
            self.get_logger().info(f"📍 Yahboom odom subscription active for {hw_name} on {ns}/odom_raw (rehearsal)")

    @staticmethod
    def _odom_from_nav(m):
        """nav_msgs/Odometry -> flat {x, y, theta, t} (yaw from quaternion)."""
        p = m.pose.pose
        q = m.pose.pose.orientation
        yaw = math.atan2(2.0 * (q.w * q.z + q.x * q.y),
                         1.0 - 2.0 * (q.y * q.y + q.z * q.z))
        return {'x': float(p.position.x), 'y': float(p.position.y),
                'theta': yaw, 't': time.time()}

    def _publish_head_pose(self, hw_name, hw_info, pan_deg, tilt_deg):
        """One head-pose sample to the Yahboom gimbal servos (burst-driven).
        Tilt flows when hc.TILT_ENABLED (gate OPEN 2026-09-05: the "S2 servo
        fault" premise was retracted — instrumented replay showed movement on
        both axes; the freezes were XRCE session loss, see head_cmds.py)."""
        pubs = self._servo_pubs_for(hw_name, hw_info)
        if not pubs: return
        safe_tilt = tilt_deg if hc.TILT_ENABLED else 0.0
        pubs[0].publish(Int32(data=hc.servo_pan_from_model(pan_deg)))
        pubs[1].publish(Int32(data=hc.servo_tilt_from_model(safe_tilt)))

    def _publish_k1_head(self, hw_name, pan_deg, tilt_deg):
        """K1 head pose via RPC 2004 (radians, vendor-clamped)."""
        if not HAS_BOOSTER_MSGS: return
        if not self._session_alive(hw_name):
            return
        yaw_rad, pitch_rad = hc.k1_head_from_model(pan_deg, tilt_deg)
        rpc = RpcReqMsg()
        rpc.uuid = f"head_{int(time.time()*1000)}"
        rpc.header = json.dumps({"api_id": 2004})
        rpc.body = json.dumps({"pitch": pitch_rad, "yaw": yaw_rad})
        self.pubs[hw_name].publish(rpc)

    def _session_alive(self, hw_name):
        """XRCE liveness gate (imu staleness) — used by head output paths."""
        return hc.session_is_alive(self._imu_last_seen.get(hw_name), time.time())

    def _publish_allowed(self, hw_name, action):
        """Per-tick publishing gate for Yahboom bots (XRCE stall handling).

        SAFETY OVERRIDE: 'hold' (emergency stop) is NEVER silenced — during
        a stall quarantine it throttles to a 1Hz zero heartbeat so the
        stalled client still drains, and the FIRST thing it executes on
        recovery is STOP (2026-09-05: gated Hold left bots running with no
        firmware watchdog).

        Other actions: full silence while quarantined (drain), and periodic
        drain-gaps (stall prevention). Non-yahboom hardware (sim twins,
        K1) is never gated."""
        if hw_name not in self.hardware_mapping:
            return True
        hw_type = self.hardware_mapping[hw_name].get('hardware_type', 'virtual').lower()
        if hw_type != 'yahboom':
            return True
        alive = hc.session_is_alive(self._imu_last_seen.get(hw_name), time.time())
        if not alive:
            if not self._imu_quarantined.get(hw_name):
                self._imu_quarantined[hw_name] = True
                self.get_logger().error(
                    f"[{hw_name}] XRCE STALL detected (no imu >{hc.SESSION_DEAD_S}s) — "
                    f"silencing non-stop output so the client can drain (Hold "
                    f"heartbeat continues). Auto-resumes when imu returns; if it "
                    f"does NOT recover within ~60s: power-cycle the bot.")
            if action == 'hold':
                tick = self._drain_tick.get(hw_name, 0) + 1
                self._drain_tick[hw_name] = tick
                return tick % 10 == 1          # 1Hz hold heartbeat while stalled
            return False
        if self._imu_quarantined.get(hw_name):
            self._imu_quarantined[hw_name] = False
            self.get_logger().warn(f"[{hw_name}] XRCE session RECOVERED — resuming output.")
        if action == 'hold':
            return True                        # stop always flows at full rate
        tick = self._drain_tick.get(hw_name, 0) + 1
        self._drain_tick[hw_name] = tick
        return not hc.drain_gap_active(tick)

    def _face_target_yaw(self, target_bot, target, cyaw):
        """Snapshot the Face target yaw ONCE per command id.

        Relative turns are relative to the yaw AT COMMAND RECEIPT —
        re-deriving (cyaw + relative) every tick made the target move with
        the bot: endless spin (live 2026-09-05)."""
        fs = self._face_state.get(target_bot)
        if fs is None or fs.get('id') != target.get('id'):
            rel = target.get('relative_angle')
            base = cyaw + float(rel) if rel is not None else float(target.get('yaw', 0.0))
            fs = {'id': target.get('id'), 'tgt': hc.normalize_angle(base)}
            self._face_state[target_bot] = fs
        return fs['tgt']

    def _advance_seq(self, st, cyaw):
        st['idx'] += 1
        st['t_step'] = time.time()
        st['base_yaw'] = cyaw

    def _seq_effective(self, hw_name, hw_type, target_bot, target, cx, cy, cyaw):
        """Seq cursor: synthesize the effective per-tick target for the
        current step, advancing on completion. The BRIDGE owns sequence
        execution because only it observes yaw + position + time (design
        2026-09-05; the evaluator only translates the chain). Chains are
        NON-MOTION steps (face/look/say/pause) — position-moving steps are
        excluded evaluator-side: drag_twin only recognizes plain waypath
        Move targets, and chained moves made its idle-watch false-positive
        (stop + teleport-back + goto loop — reverted 2026-09-05). Returns
        None when the sequence is finished — the caller parks the bot."""
        steps = target.get('steps') or []
        st = self._seq_state.get(target_bot)
        if st is None or st.get('id') != target.get('id'):
            st = {'id': target.get('id'), 'idx': 0, 't_step': time.time(),
                  'base_yaw': cyaw}
            self._seq_state[target_bot] = st
        idx = st['idx']
        if idx >= len(steps):
            return None
        step = steps[idx]
        sa = step.get('action', '').lower()
        now = time.time()
        step_id = (target.get('id'), idx)

        def _next():
            self._advance_seq(st, cyaw)
            return self._seq_effective(hw_name, hw_type, target_bot, target,
                                       cx, cy, cyaw)

        if sa == 'pause':
            if now - st['t_step'] >= float(step.get('duration', 0)):
                return _next()
            return {"action": "hold"}
        if sa == 'face':
            eff = {"action": "Face", "id": step_id,
                   "yaw": step.get("yaw"),
                   "relative_angle": step.get("relative_angle")}
            self._face_target_yaw(target_bot, eff, cyaw)
            fs = self._face_state.get(target_bot) or {}
            if fs.get('id') == step_id and fs.get('arrived'):
                return _next()
            return eff
        if sa == 'head' and 'gesture' in step:
            if now - st['t_step'] >= hc.gesture_duration_s(step.get('cycles', hc.GESTURE_CYCLES)):
                return _next()
            return {"action": "Head", "gesture": step['gesture'],
                    "cycles": step.get('cycles', hc.GESTURE_CYCLES), "id": step_id}
        if sa == 'head':      # look step: pose burst, instant advance
            self._advance_seq(st, cyaw)
            return {"action": "Head", "pan_deg": step.get('pan_deg', 0.0),
                    "tilt_deg": step.get('tilt_deg', 0.0)}
        # unknown/motion step (evaluator rejects those chains, but a stale
        # strategy could carry one): park safely instead of moving blindly
        return {"action": "hold"}

    def _render_body_gesture(self, hw_name, hw_type, target, cyaw):
        """Body 'say' gesture for gimbal-less hardware (Y#1 chassis, sim
        twins): 'no' = yaw shake around the snapshot base heading (P-control
        against an intentionally moving target that ends AT base); 'yes' =
        forward-back bob. Time-driven; parks (zeros) after the window."""
        g_id = target.get('id')
        st = self._body_gesture.get(hw_name)
        if st is None or st.get('id') != g_id:
            if CALIB and hw_type == 'yahboom' and target.get('gesture') == 'no':
                # Calib shake profile (see Y_CALIB_SHAKE_FREQ_HZ)
                freq, amp = Y_CALIB_SHAKE_FREQ_HZ, Y_CALIB_SHAKE_AMP_DEG
            else:
                freq, amp = hc.GESTURE_FREQ_HZ, hc.BODY_SHAKE_AMP_DEG
            st = {'id': g_id, 'gesture': target.get('gesture'), 't0': time.time(),
                  'base_yaw': cyaw, 'cycles': target.get('cycles', hc.GESTURE_CYCLES),
                  'freq_hz': freq, 'amp_deg': amp}
            self._body_gesture[hw_name] = st
            # Observability (2026-09-08): log every gesture arm with its
            # parameters ("say no" once ran silent — this line pins down
            # branch execution in one glance).
            _cap = ((hc.K1_FACE_VYAW_MAX_RAD_S if hw_type == 'k1'
                     else hc.FACE_VYAW_MAX_RAD_S)
                    if st['gesture'] == 'no' else 0.0)
            if CALIB and hw_type == 'yahboom' and st['gesture'] == 'no':
                _cap = Y_CALIB_VYAW
            self.get_logger().info(
                f"[{hw_name}] body gesture '{st['gesture']}' armed: "
                f"base_yaw={cyaw:+.2f} vyaw_cap={_cap} "
                f"freq={freq}Hz amp={amp}° "
                f"window={hc.gesture_duration_s(st['cycles'], freq_hz=freq):.1f}s")
        t = time.time() - st['t0']
        vyaw_cap = (hc.K1_FACE_VYAW_MAX_RAD_S if hw_type == 'k1'
                    else hc.FACE_VYAW_MAX_RAD_S)
        if CALIB and hw_type == 'yahboom':
            # Rehearsal spin cap (same rationale as face): the shake
            # P-gain saturates and full-speed wiggles triple the XRCE
            # burst — Y_CALIB_VYAW is the validated load band.
            vyaw_cap = Y_CALIB_VYAW
        if t >= hc.gesture_duration_s(st['cycles'],
                                       freq_hz=st.get('freq_hz', hc.GESTURE_FREQ_HZ)):
            self._publish_motion(hw_name, hw_type, 0.0, 0.0)
            return
        if st['gesture'] == 'no':
            tgt = st['base_yaw'] + math.radians(
                hc.gesture_offset_deg(t, amp_deg=st.get('amp_deg', hc.BODY_SHAKE_AMP_DEG),
                                      freq_hz=st.get('freq_hz', hc.GESTURE_FREQ_HZ),
                                      cycles=st['cycles']))
            diff = hc.normalize_angle(tgt - cyaw)
            ang_z = max(min(diff * hc.FACE_GAIN, vyaw_cap), -vyaw_cap)
            if CALIB and hw_type == 'yahboom':
                # Feed the estimator (integration between encoder samples)
                self._goto_state[hw_name] = {'last_vx': 0.0, 'last_vyaw': ang_z,
                                              'last_t': time.time(),
                                              'translating': False}
            self._publish_motion(hw_name, hw_type, 0.0, ang_z)
        else:   # 'yes': bob
            bob_vx = hc.body_bob_mps(t, cycles=st['cycles'])
            if CALIB and hw_type == 'yahboom':
                self._goto_state[hw_name] = {'last_vx': bob_vx, 'last_vyaw': 0.0,
                                              'last_t': time.time(),
                                              'translating': True}
            self._publish_motion(hw_name, hw_type, bob_vx, 0.0)

    def _handle_head_action(self, hw_name, hw_info, target):
        """Demo Head action. Gestures (yes/no) stream a ramped sine for the
        requested cycle count, then park neutral once (per gesture id).
        Static poses publish as an edge-triggered burst (micro-ROS drops
        single-shot messages — verified 2026-09-05)."""
        hw_type = hw_info.get('hardware_type', 'virtual').lower()
        t_now = time.time()
        if hw_type not in ('k1', 'virtual') and not self._session_alive(hw_name):
            return
        pan, tilt = float(target.get('pan_deg', 0.0)), float(target.get('tilt_deg', 0.0))
        gesture = target.get('gesture')
        if gesture:
            g_id = target.get('id')
            st = self._head_gesture.get(hw_name)
            if gesture == 'yes' and not hc.TILT_ENABLED and hw_type != 'k1':
                # nod needs tilt — refused on Yahboom (S2 servo fault gate).
                # K1 pitch is a separate actuator (RPC 2004) — NOT gated.
                if self._head_done.get(hw_name) != ('refused', g_id):
                    self._head_done[hw_name] = ('refused', g_id)
                    self.get_logger().warn(
                        f"[{hw_name}] 'say yes' refused: TILT_ENABLED=False "
                        f"(S2 servo fault — see head_cmds.py)")
                gesture = None
                pan, tilt = 0.0, 0.0
            elif st is None or st.get('id') != g_id:
                if self._head_done.get(hw_name) == g_id:
                    gesture = None          # already played to the end — park neutral
                else:
                    st = {'id': g_id, 'gesture': gesture, 't0': t_now}
                    self._head_gesture[hw_name] = st
            if gesture:
                cycles = target.get('cycles', hc.GESTURE_CYCLES)
                elapsed = t_now - st['t0']
                if elapsed < hc.gesture_duration_s(cycles):
                    # 5Hz servo sampling (every 2nd 10Hz tick): the servo
                    # can't mechanically track 10Hz at ±40° anyway, and the
                    # doubled stream congested the XRCE queue (say-yes
                    # degradation: weaker + delayed nods, 2026-09-05)
                    st['tick'] = st.get('tick', 0) + 1
                    if st['tick'] % 2 != 1:
                        return
                    if st['gesture'] == 'no':
                        g_pan = hc.gesture_offset_deg(elapsed, amp_deg=hc.GESTURE_AMP_PAN_DEG,
                                                      cycles=cycles)
                        g_tilt = 0.0
                    else:  # 'yes': one-sided bow below neutral
                        g_pan = 0.0
                        g_tilt = hc.gesture_offset_deg(elapsed, amp_deg=hc.GESTURE_AMP_TILT_DEG,
                                                        cycles=cycles, one_sided=True)
                    if hw_type == 'k1':
                        self._publish_k1_head(hw_name, g_pan, g_tilt)
                    else:
                        self._publish_head_pose(hw_name, hw_info, g_pan, g_tilt)
                    return
                # finished: remember the id, park neutral via the burst path
                self._head_gesture.pop(hw_name, None)
                self._head_done[hw_name] = g_id
                pan, tilt = 0.0, 0.0
        else:
            self._head_gesture.pop(hw_name, None)
            self._head_done.pop(hw_name, None)
        # static pose: edge-triggered burst
        key = (round(pan, 1), round(tilt, 1))
        if self._last_head_cmd.get(hw_name) != key:
            self._last_head_cmd[hw_name] = key
            self._head_burst_left[hw_name] = hc.HEAD_BURST_TICKS
        if self._head_burst_left.get(hw_name, 0) > 0:
            self._head_burst_left[hw_name] -= 1
            if hw_type == 'k1':
                self._publish_k1_head(hw_name, pan, tilt)
            else:
                self._publish_head_pose(hw_name, hw_info, pan, tilt)

    def state_cb(self, msg):
        """Sim-tick path: cache poses/ball for match/demo strategies. In
        CALIB this NEVER dispatches — the 20Hz wall-clock timer owns the
        hardware loop (single tick path, mode merge 2026-09-08)."""
        if self.is_paused: return
        self._state_cb_count = getattr(self, '_state_cb_count', 0) + 1
        if self._state_cb_count % 50 == 0:
            self.get_logger().info(f"state_cb #{self._state_cb_count}: {len(msg.name)} entities, ball={self.ball_pos is not None}")

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
            if not self.ball_pos and not CALIB:
                return
            if not CALIB:
                self._hw_dispatch_tick(msg)
        except Exception as e:
            self.get_logger().error(f"state_cb error: {e}")

    def _y_est_tick(self, hw_name):
        """Advance the yahboom position ESTIMATE by one tick and return it.
        Resyncs to a NEW encoder sample when one arrived (physical truth
        wins), else integrates the last COMMANDED velocity since the
        estimate's reference time (dead reckoning; the odom-as-correction
        design note lives at the Y_GOTO_* constants). Arms at the
        calibration start pose (0,0,0) on first use. Shared by the goto
        and face branches (face needs only the theta)."""
        now = time.time()
        est = self._y_est.get(hw_name)
        if est is None:
            est = {'x': 0.0, 'y': 0.0, 'theta': 0.0, 't': now, 'src': 'start'}
            self._y_est[hw_name] = est
            self.get_logger().info(
                f"[{hw_name}] goto estimator armed at the calibration start "
                f"pose (0,0,0) — encoder samples will resync it")
        raw = self._y_odom.get(hw_name)
        if raw and raw.get('t', 0) > self._y_last_raw_t.get(hw_name, 0.0):
            # NEW encoder sample — physical truth wins
            est = dict(raw)
            est['src'] = 'odom_raw'
            self._y_est[hw_name] = est
            self._y_last_raw_t[hw_name] = raw['t']
        else:
            # Dead-reckon the commanded velocity since the reference time
            gs_i = self._goto_state.get(hw_name) or {}
            dt = max(0.0, min(now - est['t'], 0.2))
            vx_i = gs_i.get('last_vx', 0.0)
            vyaw_i = gs_i.get('last_vyaw', 0.0)
            est['x'] += vx_i * math.cos(est['theta']) * dt
            est['y'] += vx_i * math.sin(est['theta']) * dt
            est['theta'] += vyaw_i * dt
            est['t'] = now
        return est

    def _nosim_hw_tick(self):
        """--nosim calib tick: wall-clock driver for the hardware dispatch
        (no /gazebo/model_states — state_cb never fires). Runs the SAME
        dispatch loop with msg=None: every hardware entry takes the
        pose-independent path (goto drives on odom/estimate, timedmove
        owns its clock, hold brakes)."""
        if self.is_paused: return
        self._hw_dispatch_tick(None)

    def _hw_dispatch_tick(self, msg):
        """One hardware-dispatch pass over the relay mapping (extracted
        from state_cb 2026-09-08 so the nosim timer can drive it without
        Gazebo). msg=None = nosim mode: no model names → bot_idx None for
        every entry (pose-independent actions only, per the CALIB gate).
        Do NOT run a Gazebo stack alongside --nosim — both would tick."""
        try:
            for hw_name, hw_info in self.hardware_mapping.items():
                hw_type = hw_info.get('hardware_type', 'virtual').lower()
                topic = hw_info.get('topic', f'/{hw_name}/cmd_vel')
                target_bot = hw_name if CALIB else hw_info.get('mirror_of', hw_name)

                # CALIB: virtual sim-twin entries NEVER publish (user
                # directive 2026-09-08 — no shadowing logic at all). The
                # relay pairs each twin with a hardware entry on the SAME
                # topic (blue1 + y1 -> /blue_1/cmd_vel); the twin's
                # active-brake zeros interleaved with the hardware goto
                # commands (~50% zeros to the robot: y1 moved 3.5mm in 5s,
                # y2 parked at 0.24m of a 0.5m leg). In calib the hardware
                # entry owns its topic, including the brake on loss.
                if CALIB and hw_type == 'virtual':
                    continue

                # Eager imu liveness watch for Yahboom bots (stall-breaker)
                self._ensure_liveness_watch(hw_name, hw_info)
                # Eager odom watch (k1: odometer_state; yahboom: odom_raw)
                self._ensure_odom_watch(hw_name, hw_info)

                if hw_name not in self.pubs:
                    if hw_type == 'k1' and HAS_BOOSTER_MSGS:
                        self.pubs[hw_name] = self.create_publisher(RpcReqMsg, topic, 10)
                    else:
                        self.pubs[hw_name] = self.create_publisher(Twist, topic, 10)

                # SLOT FALLBACK (2026-09-14, demo pair-mirror Option A): a
                # hardware mirror is driven by EITHER its mirror slot
                # (blue1 — system/pair semantics) OR its own direct slot
                # (y1 — a y1-prefixed command that reached the strategy
                # unredirected, e.g. from a calib-era leftover). One topic,
                # one stream: the fallback only bridges the name domains —
                # it never merges two DIFFERENT commands (first match wins).
                target = (self.targets.get(target_bot)
                          or self.targets.get(hw_name))
                if target is None:
                    # No assignment for this bot: ACTIVE BRAKE (publish zeros).
                    # The physical bots have no cmd_vel watchdog — silence
                    # would leave them running on their last command forever
                    # (stale-target runaway, 2026-09-05).
                    if self._publish_allowed(hw_name, 'hold'):
                        self._publish_motion(hw_name, hw_type, 0.0, 0.0)
                    continue
                target_action = target.get('action', '').lower()

                # XRCE stall-breaker + drain-gaps (Yahboom only; Hold always
                # flows — see _publish_allowed safety override)
                if not self._publish_allowed(hw_name, target_action):
                    continue

                # CALIB GATE FIX (2026-09-08): in calib mode hardware entries
                # are addressed DIRECTLY by relay key (y1/y2/k1) — those names
                # match no Gazebo model (2vs0_demo spawns blue_1/blue_2), so
                # the model lookup stranded every hardware action at this
                # gate (TimedMove/Goto/Hold never executed on the physical
                # bots — "instant" printed CLI-side only; sim_k1 worked solely
                # via its sim_bot key). Pose-INDEPENDENT actions proceed with
                # zeroed pose: goto reads the bot's own odom, timedmove owns
                # its clock, hold only brakes. Pose-dependent actions still
                # require the sim twin (they'd misbehave without a pose).
                #
                # NAME-DOMAIN TRANSLATION (2026-09-12, the SECOND rename
                # break): the bus/relays speak canon (blue1), Gazebo model
                # names are world-form (blue_1) — the 09-06/07 relay rename
                # stranded every virtual entry in match mode even with
                # canon slots: "blue1" is not a substring of "blue_1".
                # Try BOTH forms (and both directions) at the model lookup;
                # sim_bot keys stay world-form (sim_k1: blue_2).
                if msg is None:
                    bot_idx = None   # lean calib: no model names exist at all
                else:
                    _lookups = [target_bot]
                    if re.fullmatch(r'blue\d+', target_bot):
                        _lookups.append('blue_' + target_bot[4:])
                    elif re.fullmatch(r'blue_\d+', target_bot):
                        _lookups.append(target_bot.replace('_', '', 1))
                    bot_idx = None
                    for _ln in _lookups:
                        bot_idx = next((i for i, name in enumerate(msg.name)
                                 if (hw_info.get('sim_bot') or _ln) in name.lower()), None)
                        if bot_idx is not None:
                            break
                if bot_idx is None:
                    if not (CALIB and target_action in ('goto', 'timedmove',
                                                        'hold', 'face',
                                                        'head', 'seq')):
                        continue
                    cx, cy, cyaw = 0.0, 0.0, 0.0
                else:
                    bot_pose = msg.pose[bot_idx]
                    cx, cy = bot_pose.position.x, bot_pose.position.y
                    cyaw = get_yaw(bot_pose.orientation)
                
                # CALIB: ball_pos may be None (no model_states sets it in the
                # lean stack) —
                # computing dist_to_ball crashed EVERY dispatch tick,
                # killing goto/timedmove/hold with it (live 2026-09-08:
                # 'NoneType' object has no attribute 'x'). The ball only
                # matters for ball-adjacent actions (kick/move-to-ball),
                # which are sim-only — pose-independent actions don't read it.
                if self.ball_pos is not None:
                    dist_to_ball = math.hypot(self.ball_pos.x - cx, self.ball_pos.y - cy)
                else:
                    dist_to_ball = float('inf')
                action = target.get('action', '').lower()
                is_attacking = False

                # Sequence execution: the cursor synthesizes the effective
                # per-tick target from the current step (bridge owns yaw,
                # position and time — the only complete observer).
                if action == 'seq':
                    # CALIB (2026-09-08): the gate zeroed cyaw, and 'seq'
                    # wasn't even admitted — chained face/say steps never
                    # dispatched (live: "face east, then face north" =
                    # no movement). Source the pose/yaw from the bot's
                    # own odometry like the face branch: the seq's
                    # relative-turn snapshots (_advance_seq base_yaw)
                    # then anchor on real heading, and the synthesized
                    # Face/Head steps flow into the calib-adapted
                    # branches below (estimator yaw, spin caps).
                    if CALIB and hw_type == 'yahboom':
                        es = self._y_est_tick(hw_name)
                        cx, cy, cyaw = es['x'], es['y'], es['theta']
                    elif CALIB and hw_type == 'k1':
                        o = self._k1_odom.get(hw_name)
                        if o is None or o.get('t', 0) < time.time() - K1_ODOM_STALE_S:
                            self._publish_motion(hw_name, hw_type, 0.0, 0.0)
                            continue
                        cx, cy, cyaw = o['x'], o['y'], o['theta']
                    eff = self._seq_effective(hw_name, hw_type, target_bot,
                                              target, cx, cy, cyaw)
                    if eff is None:
                        self._publish_motion(hw_name, hw_type, 0.0, 0.0)
                        continue
                    target = eff
                    action = eff.get('action', '').lower()

                if action == 'bodygesture':
                    # gimbal-less 'say' (Y#1 chassis, sim twins): shake/bob
                    self._render_body_gesture(hw_name, hw_type, target, cyaw)
                    continue

                if action == 'hold':
                    # Active brake: publish zero velocity to stop the bot
                    # (not just skip -- skipping lets the bot coast on its
                    # last velocity command, which is unsafe on hardware)
                    self._publish_motion(hw_name, hw_type, 0.0, 0.0)
                    continue

                if action == 'timedmove':
                    # Yahboom calib: open-loop drive by TIME (encoder odom is
                    # unreliable on real floors — slip). Bridge owns the clock:
                    # publish Twist for duration_s, then auto-brake.
                    # ID-KEYED DONE-SET (2026-09-08): the assignment PERSISTS
                    # in the strategy file — the old expiry path popped the
                    # in-memory target, the 0.5s reader restored it, and the
                    # re-latch turned "y1 turn -30" into an endless
                    # turn-stop-turn-stop loop (live report 2026-09-08).
                    # Now: a completed id re-publishes zeros; only a NEW id
                    # (new command) re-arms. Same pattern as _head_done.
                    g_id = target.get('id')
                    tm = self._timedmove_state.setdefault(hw_name, {})
                    t_end = tm.get('t_end')
                    if t_end is None or tm.get('id') != g_id:
                        # first tick of this leg (or a NEW command): latch
                        tm['id'] = g_id
                        tm['vx'] = float(target.get('vx', 0.0))
                        tm['vyaw'] = float(target.get('vyaw', 0.0))
                        tm['t_end'] = time.time() + float(target.get('duration_s', 0.0))
                        t_end = tm['t_end']
                    if time.time() < t_end:
                        self._publish_motion(hw_name, hw_type, tm['vx'], tm['vyaw'])
                    else:
                        self._publish_motion(hw_name, hw_type, 0.0, 0.0)
                    continue

                if action == 'face':
                    # Demo body turn-in-place (Option D design:
                    # docs/plans/v68_pre_ifa/calibration_rotation_design.md).
                    # CALIB/hardware (2026-09-08): no sim pose exists — the
                    # CALIB gate zeroed cyaw, which used to strand Face
                    # entirely (assignment landed, bot never turned). Source
                    # the yaw from the bot's OWN odometry instead: yahboom
                    # from the goto estimator (encoder-resynced), k1 from
                    # its 490Hz odometer_state.
                    if CALIB and hw_type == 'yahboom':
                        cyaw_eff = self._y_est_tick(hw_name)['theta']
                    elif CALIB and hw_type == 'k1':
                        o = self._k1_odom.get(hw_name)
                        if o is None or o.get('t', 0) < time.time() - K1_ODOM_STALE_S:
                            self._publish_motion(hw_name, hw_type, 0.0, 0.0)
                            continue
                        cyaw_eff = o['theta']
                    else:
                        cyaw_eff = cyaw
                    tgt_yaw = self._face_target_yaw(target_bot, target, cyaw_eff)
                    fs = self._face_state[target_bot]
                    diff = hc.normalize_angle(tgt_yaw - cyaw_eff)
                    # Arrival latch with hysteresis: once within tolerance,
                    # stay braked until drift exceeds the wider re-engage band
                    if fs.get('arrived'):
                        if abs(diff) > hc.FACE_REENGAGE_RAD:
                            fs['arrived'] = False
                    elif abs(diff) < hc.FACE_ARRIVAL_TOL_RAD:
                        fs['arrived'] = True
                    vyaw_cap = (hc.K1_FACE_VYAW_MAX_RAD_S if hw_type == 'k1'
                                else hc.FACE_VYAW_MAX_RAD_S)
                    if CALIB and hw_type == 'yahboom':
                        # Rehearsal spin cap: FACE_GAIN (3.0) saturates
                        # instantly, so the demo cap (1.5 rad/s, the firmware
                        # ceiling) means full-speed spins — 3x the encoder/
                        # imu burst through the marginal ESP32 XRCE client.
                        # Live-correlated with the stalls (2026-09-08: stall
                        # #3 fired during a face east). Y_CALIB_VYAW keeps
                        # the firmware load inside the band the goto drives
                        # validated. Demo mode keeps the 1.5 ceiling.
                        vyaw_cap = Y_CALIB_VYAW
                    if fs.get('arrived'):
                        lin_x, ang_z = 0.0, 0.0   # arrived — active brake
                    else:
                        ang_z = max(min(diff * hc.FACE_GAIN, vyaw_cap), -vyaw_cap)
                        lin_x = 0.0               # turn in place, no forward motion
                    # Feed the estimator: the face command IS the commanded
                    # velocity the integration dead-reckons between encoder
                    # samples (goto ramp-in starts from it too — smooth).
                    if CALIB and hw_type == 'yahboom':
                        self._goto_state[hw_name] = {'last_vx': 0.0,
                                                      'last_vyaw': ang_z,
                                                      'last_t': time.time(),
                                                      'translating': False}
                    self._publish_motion(hw_name, hw_type, lin_x, ang_z)
                    continue

                if action == 'head':
                    # Demo head action. GESTURE FORK: on gimbal-less hardware
                    # (Y#1 has no PTZ; sim twins have no gimbal joints) the
                    # 'say' gestures run on the chassis instead — servo
                    # publishes to those bots are harmless (no connected
                    # load, no stall) and still go out; the K1 keeps using
                    # its head (RPC 2004) via the head path below.
                    # CALIB (2026-09-08): the fork checked DEMO slot names
                    # (blue_1) — calib addresses hw keys (y1), so the body
                    # fork missed and Y#1 took the servo path. Use the
                    # calib body set (y1 — gimbal-less; y2 keeps its camera)
                    # and feed the EST yaw as the shake base (cyaw is zeroed
                    # in calib; the 'no'-shake P-controls around the base).
                    body_bots = (hc.CALIB_GESTURE_BODY_BOTS if CALIB
                                 else hc.GESTURE_BODY_BOTS)
                    if target.get('gesture') and (
                            hw_type == 'virtual' or
                            (hw_type == 'yahboom' and target_bot in body_bots)):
                        cyaw_g = cyaw
                        if CALIB and hw_type == 'yahboom':
                            cyaw_g = self._y_est_tick(hw_name)['theta']
                        self._render_body_gesture(hw_name, hw_type, target, cyaw_g)
                        continue
                    # body stays braked at 2Hz (heartbeat; 10Hz zeros tripled
                    # gesture-time queue load and caused the say-yes
                    # congestion degradation, 2026-09-05)
                    self._handle_head_action(hw_name, hw_info, target)
                    tick = self._head_brake_tick.get(hw_name, 0) + 1
                    self._head_brake_tick[hw_name] = tick
                    if tick % 5 == 1:
                        self._publish_motion(hw_name, hw_type, 0.0, 0.0)
                    continue

                if action == 'goto':
                    # Calibration-only: closed-loop drive to (x,y) on the bot's
                    # OWN odometry. K1: vendor two-phase recipe (robocup_demo
                    # robot_client.cpp:149) — heading error beyond the turn
                    # threshold -> rotate in place (vx=0); translate only when
                    # aligned; arrival needs BOTH distance and heading
                    # tolerance (kills the 2026-09-06 "turned forever at
                    # target" — biped sway re-triggered the theta P-term).
                    # Yahboom (2026-09-08): SAME loop at Y_CALIB speeds —
                    # K1-pipeline rehearsal on cheap hardware; encoder odom
                    # ±30% => coarse arrival by design.
                    target_x = target.get('x', cx)
                    target_y = target.get('y', cy)
                    # Odom source: if relay has sim_bot, read Gazebo sim pose
                    # (offline practice mode — blue_2 stands in for K1).
                    # Otherwise read the bot's real odometry subscription
                    # (k1: odometer_state @490Hz; yahboom: odom_raw).
                    sim_bot = hw_info.get('sim_bot')
                    if sim_bot:
                        pose = self._last_bot_poses.get(sim_bot)
                        if pose is None:
                            continue
                        siny_c = 2.0 * (pose.orientation.w * pose.orientation.z + pose.orientation.x * pose.orientation.y)
                        cosy_c = 1.0 - 2.0 * (pose.orientation.y * pose.orientation.y + pose.orientation.z * pose.orientation.z)
                        yaw = math.atan2(siny_c, cosy_c)
                        odom = {'x': pose.position.x, 'y': pose.position.y,
                                'theta': yaw, 't': time.time()}
                        self._k1_odom[hw_name] = odom
                    else:
                        if hw_type == 'yahboom':
                            # ODOM AS CORRECTION, NOT PERMISSION (approach 6,
                            # 2026-09-08): encoder odom streams only while
                            # wheels turn — gating motion on fresh odom
                            # deadlocks every rest->goto transition. The
                            # loop drives on the ESTIMATE (calibration start
                            # pose 0,0,0 + commanded-velocity integration;
                            # every NEW encoder sample resyncs it — see
                            # _y_est_tick). ±30% slip accepted (rehearsal
                            # vehicle). Safety: imu liveness (XRCE
                            # quarantine) gates publishing independently.
                            odom = self._y_est_tick(hw_name)
                        else:
                            # K1: odometer_state streams ~490Hz even idle —
                            # silence genuinely means the robot is gone.
                            odom = self._k1_odom.get(hw_name)
                            if odom is None or odom.get('t', 0) < time.time() - K1_ODOM_STALE_S:
                                self._publish_motion(hw_name, hw_type, 0.0, 0.0)
                                continue
                    # Per-hardware gains/tolerances (named constants, file top)
                    if hw_type == 'yahboom':
                        vx_max, vyaw_max = Y_CALIB_VX, Y_CALIB_VYAW
                        accel_vx, accel_vyaw = Y_GOTO_ACCEL_VX, Y_GOTO_ACCEL_VYAW
                        xy_tol = Y_GOTO_XY_TOL
                        odom_factor = Y_ODOM_FACTOR
                    else:
                        vx_max, vyaw_max = K1_GOTO_VX_MAX, K1_GOTO_VYAW_MAX
                        accel_vx, accel_vyaw = K1_GOTO_ACCEL_VX, K1_GOTO_ACCEL_VYAW
                        xy_tol = K1_GOTO_XY_TOL
                        odom_factor = K1_ODOM_FACTOR
                    # Controller-side odom correction (K1 vendor odom_factor
                    # 0.8: wheel/footstep odom over-reads ~20%). Logs and
                    # state files keep raw odom; only control math scales it.
                    kx, ky = odom['x'] * odom_factor, odom['y'] * odom_factor
                    kyaw = odom['theta']
                    dx, dy = target_x - kx, target_y - ky
                    dist = math.hypot(dx, dy)
                    target_yaw = math.atan2(dy, dx)
                    angle_diff = hc.normalize_angle(target_yaw - kyaw)
                    # Arrival — DISTANCE-ONLY for BOTH hw types (2026-09-08,
                    # live-proven on real K1): at park range dx,dy are tiny,
                    # so target_yaw = atan2(dy,dx) is geometric noise (a few
                    # cm lateral offset swings the bearing ±14-90°) — the
                    # dist+heading gate chased that noise into an endless
                    # arrival spin (real K1: spins at target until stop; sim
                    # validation was too clean to expose it). Park
                    # orientation was never part of the calib contract.
                    if dist < xy_tol:
                        gs_id = (target_x, target_y)
                        if self._goto_arrived_id.get(hw_name) != gs_id:
                            self._goto_arrived_id[hw_name] = gs_id
                            self.get_logger().info(
                                f"[{hw_name}] goto ARRIVED at ({target_x:.2f},"
                                f" {target_y:.2f}) — dist {dist:.2f} m, braking")
                        # Reset the rate-limiter state to zeros — it feeds
                        # the estimator: leftover vyaw (up to 1.2 rad/s)
                        # would keep dead-reckoning the belief after the
                        # wheels stopped (no encoder samples at rest to
                        # heal it) and poison the next goto's bearing.
                        self._goto_state[hw_name] = {'last_vx': 0.0,
                                                     'last_vyaw': 0.0,
                                                     'last_t': time.time(),
                                                     'translating': False}
                        self._publish_motion(hw_name, hw_type, 0.0, 0.0)
                        continue
                    gs = self._goto_state.get(hw_name)
                    was_translating = bool(gs.get('translating')) if gs else False
                    if hw_type == 'yahboom' and abs(angle_diff) > Y_GOTO_REVERSE_BEARING:
                        # Rear window: back up (see Y_GOTO_REVERSE_BEARING).
                        # Steering uses the REAR bearing error: positive
                        # rear error -> positive yaw rate brings the rear
                        # centerline onto the target while reversing.
                        rotate_only = False   # reversing IS a translate phase
                        rear_err = hc.normalize_angle(angle_diff - math.pi)
                        lin_x = -max(0.0, min(0.8 * dist, vx_max))
                        ang_z = max(min(rear_err * 1.2, vyaw_max * 0.5),
                                    -vyaw_max * 0.5)
                    elif was_translating:
                        # Two-phase gate with hysteresis (vendor breakOscillate
                        # pattern): once in translate-phase, keep translating
                        # until heading error grows past the full threshold.
                        rotate_only = abs(angle_diff) >= K1_GOTO_TURN_THRESHOLD
                        lin_x = 0.0 if rotate_only else max(0.0, min(0.8 * dist, vx_max))
                        if rotate_only:
                            ang_z = max(min(angle_diff * 1.2, vyaw_max),
                                        -vyaw_max)  # vendor gain 1.2
                        else:
                            ang_z = max(min(angle_diff * 1.2, vyaw_max * 0.5),
                                        -vyaw_max * 0.5)  # damped while moving
                    else:
                        rotate_only = abs(angle_diff) >= (
                            K1_GOTO_TURN_THRESHOLD - K1_GOTO_PHASE_HYSTERESIS)
                        if rotate_only:
                            lin_x = 0.0  # turn in place — gait survives this
                            ang_z = max(min(angle_diff * 1.2, vyaw_max),
                                        -vyaw_max)  # vendor gain 1.2
                        else:
                            lin_x = max(0.0, min(0.8 * dist, vx_max))
                            ang_z = max(min(angle_diff * 1.2, vyaw_max * 0.5),
                                        -vyaw_max * 0.5)  # damped while moving
                    now = time.time()
                    dt = min(now - gs.get('last_t', now), 0.2) if gs else 0.1
                    lvx = gs.get('last_vx', 0.0) if gs else 0.0
                    lvyaw = gs.get('last_vyaw', 0.0) if gs else 0.0
                    # Clamp leftover state to the caps BEFORE ramping — a
                    # gesture can leave last_vx = BODY_BOB_MPS (0.75) in the
                    # shared state; ramping from there would command 0.7m/s
                    # on the next goto (calib cap is 0.2).
                    lvx = max(-vx_max, min(lvx, vx_max))
                    lvyaw = max(-vyaw_max, min(lvyaw, vyaw_max))
                    lin_x = max(lvx - accel_vx * dt,
                                min(lin_x, lvx + accel_vx * dt))
                    ang_z = max(lvyaw - accel_vyaw * dt,
                                min(ang_z, lvyaw + accel_vyaw * dt))
                    self._goto_state[hw_name] = {'last_vx': lin_x,
                                                  'last_vyaw': ang_z,
                                                  'last_t': now,
                                                  'translating': not rotate_only}
                    self._publish_motion(hw_name, hw_type, lin_x, ang_z)
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
                
                self._publish_motion(hw_name, hw_type, lin_x, ang_z,
                                     kick_fire=is_attacking and kick_execute)
                    
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
