"""Head/Face command contract shared by evaluator (demo fast-path) and bridge.

Empirical hardware contract (2026-09-05 lab session, Yahboom#2 "pro" gimbal):
- Pan  topic <ns>/servo_s1 (std_msgs/Int32, degrees): topic +30 turned camera RIGHT.
  Mechanical limit observed at ~45 deg (firmware would allow [-90, 90] — must not use).
- Tilt topic <ns>/servo_s2 (std_msgs/Int32, degrees): vendor band [-90, +20], hard
  +20 stop. Level-camera park value assumed = vendor default -60 (retune live).
- Single-shot publishes are dropped by micro-ROS -> burst re-publish required
  (verified: --once silent, 5x @2Hz moved the servo).
- cmd_vel has NO firmware watchdog -> every motion must end with an explicit zero.
- K1 head: RPC api_id 2004 {"pitch","yaw"} in radians, vendor clamps
  yaw 1.03 / pitch -0.33..+0.86 (docs/plans/v68_pre_ifa/k1_kick_head_vendor_audit.md 2.2).
  K1 sign conventions + required RobotMode UNVERIFIED — tune on hardware (lab gate).

Model-facing convention (this module): pan_deg/tilt_deg are offsets from the
neutral head pose, +pan = camera turns to its LEFT, +tilt = camera UP.
Sign conversion to the servo topic happens ONLY here (SERVO_SIGN_PAN).
"""
import math

# --- Servo (Yahboom) limits & conversion ---
PAN_MECH_LIMIT_DEG = 45.0        # observed mechanical stop (2026-09-05)
PAN_LIMIT_DEG = 40.0             # demo clamp (mechanical limit minus margin)
TILT_SERVO_MIN_DEG = -85.0       # vendor hard stop -90 minus margin
TILT_SERVO_MAX_DEG = 15.0        # vendor hard stop +20 minus margin
TILT_NEUTRAL_DEG = 4.0           # measured upright/level park (live test 2026-09-05)
TILT_ENABLED = True              # Fault gate opened 2026-09-05: the "S2 servo
                                 # fault" premise was WRONG — instrumented replay
                                 # showed camera movement on BOTH axes; the
                                 # freezes are XRCE SESSION LOSS (ESP32 app wedges,
                                 # WiFi stack stays alive, no reconnect in vendor
                                 # firmware). See bridge SESSION_DEAD_* guard.
SERVO_SIGN_PAN = -1.0            # topic + = RIGHT  =>  left-positive model needs -1
SERVO_SIGN_TILT = 1.0            # UNVERIFIED — "say yes" (model -40) moved the
                                 # camera UP; flip to -1.0 after the -8/+8 probe
                                 # (planned: next lab hands-on)

# --- micro-ROS delivery guard ---
HEAD_CMD_EPS_DEG = 1.0           # edge-trigger dedup threshold
HEAD_BURST_TICKS = 3             # re-publish N consecutive 10Hz ticks (drop guard)

# --- XRCE session-liveness guard + livelock breaker (root cause 2026-09-05) ---
# Measured failure chain (instrumented): the ESP32 micro-ROS client STALLS
# under sustained reliable traffic (stochastic, ~1 stall / several min of
# 3-topic@10Hz max load) — its input queue overflows, publishing stops, the
# WiFi stack stays alive (ping OK). The stall is REVERSible: after a traffic
# SILENCE of <=60s the client drains and recovers by itself. It becomes a
# PERMANENT freeze only when traffic never stops — which is exactly what the
# bridge does (cmd_vel at 10Hz forever) => livelock => power-cycle required.
# Two defenses (bridge):
#   1. drain-gaps: periodic 200ms full-silence windows in the per-bot stream
#      guarantee queue drain BEFORE a stall (DRAIN_GAP_* below).
#   2. stall-breaker: on imu staleness the bridge goes fully silent for that
#      bot (quarantine) until the client recovers — converts any stall from
#      a permanent freeze into a seconds-long hiccup. Auto-resumes on
#      fresh imu, logs entry+recovery once.
SESSION_DEAD_S = 5.0             # imu staleness threshold (13-25Hz baseline;
                                 # 3.0 caused false quarantines on brief imu
                                 # blips under load, measured 2026-09-05)
DRAIN_GAP_EVERY_TICKS = 20        # every 2s of 10Hz streaming ...
DRAIN_GAP_LEN_TICKS = 2           # ... insert this many ticks (200ms) of silence

# --- Look presets (offsets from neutral, left-positive / up-positive) ---
LOOK_PAN_DEG = 30.0
LOOK_TILT_UP_DEG = 15.0
LOOK_TILT_DOWN_DEG = 25.0

# --- Gesture ("say yes" nod / "say no" shake) ---
# Live-tuned 2026-09-05 (2nd pass): user: "lower the frequency, more amplitude"
GESTURE_CYCLES = 3
GESTURE_FREQ_HZ = 2.0            # cycles per second (4 Hz was too fast on servo)
GESTURE_AMP_PAN_DEG = 40.0       # "say no" shake (symmetric sine; stop at 45)
GESTURE_AMP_TILT_DEG = 25.0       # REDUCED from 40 after incident 1 (servo
                                  # stress). Gate since REOPENED (TILT_ENABLED
                                  # =True, 2026-09-05: the S2-fault premise was
                                  # retracted — freezes were XRCE session loss).
                                  # SERVO_SIGN_TILT probe (-8/+8) still pending —
                                  # verify direction before raising amplitude.
GESTURE_RAMP_S = 0.3             # amplitude ramp-in/out to spare the servos


# --- Body gestures (Yahboom#1 has no gimbal — body motion is its "say" channel) ---
# Fleet reality 2026-09-05: Y#1 (standard) has no PTZ camera; Y#2 (vision)
# carries the gimbal. On body bots the say-gestures run on the chassis:
# 'no' = yaw shake, 'yes' = forward-back bob (slight positional drift is
# accepted, user 2026-09-05). Servo publishes to body bots are HARMLESS
# (ESP32 consumes them, PWM on unconnected pins = no load, no stall) and
# still go out — no relay flag, no warning (user decision).
GESTURE_BODY_BOTS = ("blue1",)
# CALIB addressing (2026-09-08): calib addresses hw keys directly (y1/y2)
# — the gimbal-less body set there is just y1 (Y#2 has the camera PTZ).
CALIB_GESTURE_BODY_BOTS = ("y1",)
BODY_SHAKE_AMP_DEG = 100.0        # 'say no' yaw shake amplitude (5x, user 2026-09-06)
BODY_BOB_MPS = 0.75              # 'say yes' forward-back surge speed (5x)
                                  # (approx 10cm excursions at 2Hz)


def body_bob_mps(t, mps=BODY_BOB_MPS, freq_hz=GESTURE_FREQ_HZ,
                 cycles=GESTURE_CYCLES, ramp_s=GESTURE_RAMP_S):
    """'say yes' body bob: alternating forward/back velocity surges (a sine
    in lin_x), amplitude-ramped like the camera gestures; ~zero net travel.
    0 outside the gesture window."""
    duration = gesture_duration_s(cycles, freq_hz, ramp_s)
    if t <= 0.0 or t >= duration:
        return 0.0
    env = min(1.0, t / ramp_s, (duration - t) / ramp_s)
    return mps * math.sin(2.0 * math.pi * freq_hz * t) * max(env, 0.0)



# --- K1 head (RPC 2004, radians; vendor audit 2.2) ---
K1_HEAD_YAW_LIMIT_RAD = 1.03     # vendor spec 59 deg
K1_HEAD_PITCH_MIN_RAD = -0.33    # vendor spec -19 deg
K1_HEAD_PITCH_MAX_RAD = 0.86     # vendor spec +49 deg
K1_SIGN_YAW = 1.0                # UNVERIFIED: +yaw = left assumed (REP-103)
K1_SIGN_PITCH = -1.0             # UNVERIFIED: +pitch = down assumed (larger + range)

# --- Face (body turn-in-place) ---
FACE_ARRIVAL_TOL_RAD = 0.1       # ~6 deg — stop turning when within this
FACE_REENGAGE_RAD = 0.35         # after arrival, only correct again beyond
                                 # this (hysteresis: absorbs physical drift,
                                 # prevents endgame hunting)
FACE_GAIN = 3.0                  # P-gain on heading error
FACE_VYAW_MAX_RAD_S = 1.5        # Yahboom firmware clamp (verified 2026-09-06:
                                  # 2.0 → sim outruns hardware → ~80% rotation;
                                  # 1.5 matches firmware, sim+hardware stay synced)
K1_FACE_VYAW_MAX_RAD_S = 1.0     # vendor-safe profile (k1 vendor audit 5.3)


def normalize_angle(a):
    """Wrap an angle to [-pi, pi]."""
    while a > math.pi:
        a -= 2.0 * math.pi
    while a < -math.pi:
        a += 2.0 * math.pi
    return a


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def session_is_alive(last_seen_ts, now_ts, dead_after_s=SESSION_DEAD_S):
    """XRCE liveness decision for the bridge guard.

    last_seen_ts=None (never seen yet) counts as alive — bootstrapping window;
    a bot whose imu never published must not be blocked by the guard."""
    if last_seen_ts is None:
        return True
    return (now_ts - last_seen_ts) < dead_after_s


def drain_gap_active(tick, every=DRAIN_GAP_EVERY_TICKS,
                     length=DRAIN_GAP_LEN_TICKS):
    """True while tick falls into a periodic full-silence window.

    The bridge counts 10Hz streaming ticks per bot; every `every` ticks it
    inserts `length` silent ticks, guaranteeing the ESP32's XRCE input queue
    a drain window before it can overflow (measured stall mechanism,
    2026-09-05)."""
    return (tick % (every + length)) >= every


def servo_pan_from_model(pan_deg):
    """Model-frame pan offset (deg, + = left) -> servo_s1 topic value."""
    return round(clamp(SERVO_SIGN_PAN * float(pan_deg), -PAN_LIMIT_DEG, PAN_LIMIT_DEG))


def servo_tilt_from_model(tilt_deg):
    """Model-frame tilt offset (deg, + = up) -> servo_s2 topic value."""
    return round(clamp(TILT_NEUTRAL_DEG + SERVO_SIGN_TILT * float(tilt_deg),
                       TILT_SERVO_MIN_DEG, TILT_SERVO_MAX_DEG))


def k1_head_from_model(pan_deg, tilt_deg):
    """Model-frame pan/tilt offsets (deg) -> K1 (yaw_rad, pitch_rad), clamped."""
    yaw = clamp(K1_SIGN_YAW * math.radians(pan_deg),
                -K1_HEAD_YAW_LIMIT_RAD, K1_HEAD_YAW_LIMIT_RAD)
    pitch = clamp(K1_SIGN_PITCH * math.radians(tilt_deg),
                  K1_HEAD_PITCH_MIN_RAD, K1_HEAD_PITCH_MAX_RAD)
    return round(yaw, 4), round(pitch, 4)


def gesture_duration_s(cycles=GESTURE_CYCLES, freq_hz=GESTURE_FREQ_HZ,
                       ramp_s=GESTURE_RAMP_S):
    """Total gesture time: N cycles + one ramp tail back to neutral."""
    return cycles / freq_hz + ramp_s


def gesture_offset_deg(t, amp_deg=None, freq_hz=GESTURE_FREQ_HZ,
                       cycles=GESTURE_CYCLES, ramp_s=GESTURE_RAMP_S,
                       one_sided=False):
    """Oscillation offset (deg, model frame) at t seconds into a gesture.

    one_sided=False: symmetric sine around neutral (pan shake).
    one_sided=True:  repeated bows (tilt nod) — offset always <= 0, each cycle
                     goes neutral -> full depth -> neutral (raised-cosine), the
                     correct nod shape given the +20 servo top stop.
    Amplitude-ramped in/out over ramp_s; 0 outside the gesture window."""
    if amp_deg is None:
        amp_deg = GESTURE_AMP_PAN_DEG
    duration = gesture_duration_s(cycles, freq_hz, ramp_s)
    if t <= 0.0 or t >= duration:
        return 0.0
    env = min(1.0, t / ramp_s, (duration - t) / ramp_s)
    if one_sided:
        osc = 0.5 - 0.5 * math.cos(2.0 * math.pi * freq_hz * t)  # 0..1 bows
        return -amp_deg * osc * max(env, 0.0)
    return amp_deg * math.sin(2.0 * math.pi * freq_hz * t) * max(env, 0.0)
