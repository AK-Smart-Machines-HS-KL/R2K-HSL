"""Head/Face demo fast-path: routing, defaults, k1 alias, bridge passthrough.

Fast-tier: no ROS, no Ollama (bridge test skips without rclpy).
Covers the calibration showcase "face vs yaw": look/say (default blue_1 —
Y#1 body gestures; camera = explicit blue_2 prefix), face/turn/rotate
(default blue_1), k1 prefix → blue_1 mirror source, "all" scope prefix.
"""
import json
import math
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ai_tactics'))

import r2k_evaluator as ev
import head_cmds as hc

ENTS = {"soccer_ball": {"x": 1.0, "y": 1.0},
        "blue1": {"x": 0.0, "y": 0.0},
        "blue2": {"x": 0.0, "y": 1.0}}


@pytest.fixture(autouse=True)
def _clean_state(monkeypatch):
    ev._demo_state.clear()
    def _no_network(*a, **k):
        raise AssertionError("test attempted a real Ollama call")
    monkeypatch.setattr(ev.requests, "post", _no_network)
    yield
    ev._demo_state.clear()


@pytest.fixture
def paths(tmp_path, monkeypatch):
    wp = tmp_path / "waypoints.json"
    strat = tmp_path / "current_strategy.json"
    monkeypatch.setattr(ev, "WAYPOINTS_PATH", str(wp))
    monkeypatch.setattr(ev, "STRATEGY_PATH", str(strat))
    return {"wp": wp, "strat": strat}


def _assignments(paths):
    with open(paths["strat"]) as f:
        return json.load(f).get("assignments", {})


# --- Evaluator routing: head ---
# (Bare look/say default to blue_1 — the physical say bot (uniform default
# 2026-09-06: bare 'say' triggers the bridge body-gesture fork on Y#1).
# Camera gimbal = explicit 'blue_2 ...' prefix. K1 mirror via k1/k1_bot
# prefix. 'all' scope prefix routes to every blue bot.)


def test_look_defaults_to_blue_1(paths):
    ev._handle_task_clause("look left", ENTS)
    a = _assignments(paths)["blue1"]
    assert a == {"action": "Head", "pan_deg": hc.LOOK_PAN_DEG, "tilt_deg": 0.0}
    assert "blue2" not in _assignments(paths)


def test_look_right_is_negative_pan(paths):
    ev._handle_task_clause("look right", ENTS)
    assert _assignments(paths)["blue1"]["pan_deg"] == -hc.LOOK_PAN_DEG


def test_look_up_down_use_tilt_offsets(paths):
    ev._handle_task_clause("look up", ENTS)
    assert _assignments(paths)["blue1"]["tilt_deg"] == hc.LOOK_TILT_UP_DEG
    ev._demo_state.clear()
    ev._handle_task_clause("look down", ENTS)
    assert _assignments(paths)["blue1"]["tilt_deg"] == -hc.LOOK_TILT_DOWN_DEG


def test_look_center_is_neutral_pose(paths):
    ev._handle_task_clause("look center", ENTS)
    a = _assignments(paths)["blue1"]
    assert a["pan_deg"] == 0.0 and a["tilt_deg"] == 0.0


def test_explicit_blue_2_look_targets_camera(paths):
    ev._handle_task_clause("blue_2 look left", ENTS)
    a = _assignments(paths)["blue2"]
    assert a["action"] == "Head" and a["pan_deg"] == hc.LOOK_PAN_DEG


def test_say_yes_gesture_with_nonce_id(paths):
    ev._handle_task_clause("say yes", ENTS)
    a = _assignments(paths)["blue1"]
    assert a["action"] == "Head"
    assert a["gesture"] == "yes"
    assert a["cycles"] == hc.GESTURE_CYCLES
    assert "id" in a


def test_say_no_gesture(paths):
    ev._handle_task_clause("say no", ENTS)
    assert _assignments(paths)["blue1"]["gesture"] == "no"


def test_explicit_blue_2_say_targets_camera(paths):
    ev._handle_task_clause("blue_2 say yes", ENTS)
    a = _assignments(paths)["blue2"]
    assert a["action"] == "Head" and a["gesture"] == "yes"


def test_head_cmd_clears_waypoints(paths):
    st = ev._demo_bot_state("blue1")
    st["waypoints"] = ev._norm_demo_waypoints([{"label": "A", "x": 1, "y": 1}])
    ev._handle_task_clause("look left", ENTS)
    assert st["waypoints"] == []
    assert st["fast_cmd"]["action"] == "Head"


def test_k1_prefix_reroutes_to_blue_1(paths):
    ev._handle_task_clause("k1 say yes", ENTS)
    data = _assignments(paths)
    assert "blue1" in data and "k1" not in data
    assert data["blue1"]["gesture"] == "yes"


def test_k1_bot_prefix_look(paths):
    ev._handle_task_clause("k1_bot look left", ENTS)
    a = _assignments(paths)["blue1"]
    assert a["action"] == "Head" and a["pan_deg"] == hc.LOOK_PAN_DEG


def test_prefixed_look_targets_that_bot(paths):
    ev._handle_task_clause("blue_1 look left", ENTS)
    assert "blue1" in _assignments(paths)


# --- "all" scope prefix (user 2026-09-06: "all" -> cmd goes to all bots) ---

def test_all_prefix_coords_moves_every_bot(paths):
    ev._handle_task_clause("all go to (1,2)", ENTS)
    for bot in ("blue1", "blue2"):
        wps = ev._demo_bot_state(bot)["waypoints"]
        assert [(w["x"], w["y"]) for w in wps] == [(1.0, 2.0)]


def test_all_prefix_say_gestures_every_bot(paths):
    ev._handle_task_clause("all say no", ENTS)
    data = _assignments(paths)
    assert data["blue1"]["gesture"] == "no"   # bridge body-gesture fork
    assert data["blue2"]["gesture"] == "no"   # camera pan shake


def test_all_prefix_face_turns_every_bot(paths):
    ev._handle_task_clause("all face west", ENTS)
    data = _assignments(paths)
    assert data["blue1"]["yaw"] == math.pi
    assert data["blue2"]["yaw"] == math.pi


def test_all_prefix_facing_chain_runs_on_every_bot(paths):
    ev._handle_task_clause("all face west, then say no", ENTS)
    data = _assignments(paths)
    for bot in ("blue1", "blue2"):
        assert data[bot]["action"] == "Seq"
        assert data[bot]["steps"][0]["yaw"] == math.pi
        assert data[bot]["steps"][1]["gesture"] == "no"


# --- Evaluator routing: face ---

def test_face_west_absolute_yaw(paths):
    ev._handle_task_clause("face west", ENTS)
    a = _assignments(paths)["blue1"]
    assert a["action"] == "Face"
    assert a["yaw"] == math.pi
    assert "id" in a          # nonce: bridge snapshots the target yaw once


def test_face_east_zero_yaw(paths):
    ev._handle_task_clause("face east", ENTS)
    assert _assignments(paths)["blue1"]["yaw"] == 0.0


def test_face_defaults_to_blue_1_not_blue_2(paths):
    ev._handle_task_clause("face east", ENTS)
    data = _assignments(paths)
    assert "blue1" in data and "blue2" not in data


def test_turn_right_relative(paths):
    ev._handle_task_clause("turn right", ENTS)
    assert _assignments(paths)["blue1"]["relative_angle"] == pytest.approx(-math.pi / 2)


def test_turn_around_relative(paths):
    ev._handle_task_clause("turn around", ENTS)
    assert _assignments(paths)["blue1"]["relative_angle"] == pytest.approx(math.pi)


def test_rotate_degrees(paths):
    ev._handle_task_clause("rotate 90", ENTS)
    assert _assignments(paths)["blue1"]["relative_angle"] == pytest.approx(math.pi / 2)
    ev._demo_state.clear()
    ev._handle_task_clause("rotate -45 deg", ENTS)
    assert _assignments(paths)["blue1"]["relative_angle"] == pytest.approx(-math.pi / 4)


def test_k1_prefix_face_reroutes_to_blue_1(paths):
    ev._handle_task_clause("k1 turn left", ENTS)
    a = _assignments(paths)["blue1"]
    assert a["action"] == "Face" and a["relative_angle"] == pytest.approx(math.pi / 2)


def test_face_the_ball_never_reaches_compiler(paths, monkeypatch):
    def _boom(*a, **k):
        raise AssertionError("compiler called for unsupported face target")
    monkeypatch.setattr(ev, "_compile_demo_task", _boom)
    ev._handle_task_clause("face the ball", ENTS)
    assert not os.path.exists(paths["strat"])


# --- head_cmds math (shared contract) ---

def test_normalize_angle():
    assert hc.normalize_angle(math.pi + 0.1) == pytest.approx(-math.pi + 0.1)
    assert hc.normalize_angle(-3 * math.pi) == pytest.approx(-math.pi)
    assert hc.normalize_angle(0.0) == 0.0


# --- XRCE session-liveness guard + livelock breaker (root cause 2026-09-05) ---

def test_session_alive_bootstrap_and_staleness():
    now = 1000.0
    # never-seen bot (K1, or boot window) must not be gated
    assert hc.session_is_alive(None, now) is True
    # fresh imu (13-25Hz baseline) = alive
    assert hc.session_is_alive(now - 0.5, now) is True
    # stalled XRCE client (publishing stops, network stays alive)
    assert hc.session_is_alive(now - hc.SESSION_DEAD_S - 0.1, now) is False
    # exactly at the threshold boundary
    assert hc.session_is_alive(now - hc.SESSION_DEAD_S, now) is False


def test_drain_gap_pattern():
    """Every DRAIN_GAP_EVERY ticks of streaming, DRAIN_GAP_LEN silent ticks:
    2s of 10Hz traffic then a 200ms full-silence window, repeating."""
    e, l = hc.DRAIN_GAP_EVERY_TICKS, hc.DRAIN_GAP_LEN_TICKS
    period = e + l
    # inside a stream burst: no gap
    assert all(not hc.drain_gap_active(t) for t in range(0, e))
    # inside the silence window: gap active
    assert all(hc.drain_gap_active(t) for t in range(e, period))
    # pattern repeats each period
    assert not hc.drain_gap_active(period)
    assert hc.drain_gap_active(period + e)
    assert hc.drain_gap_active(2 * period + e + l - 1)


def test_servo_tilt_sign_flag_pending():
    """Sign flip is a pending lab probe ('say yes' moved the camera UP) —
    the flag must exist so the fix is a one-constant change."""
    assert hc.SERVO_SIGN_TILT in (1.0, -1.0)


def test_servo_pan_sign_and_clamp():
    # empirical 2026-09-05: topic +30 = camera RIGHT -> model left needs -1
    assert hc.servo_pan_from_model(30.0) == -30
    assert hc.servo_pan_from_model(-90.0) == hc.PAN_LIMIT_DEG
    assert hc.servo_pan_from_model(90.0) == -hc.PAN_LIMIT_DEG


def test_servo_tilt_neutral_and_clamp():
    assert hc.servo_tilt_from_model(0.0) == hc.TILT_NEUTRAL_DEG
    assert hc.servo_tilt_from_model(100.0) == hc.TILT_SERVO_MAX_DEG
    assert hc.servo_tilt_from_model(-100.0) == hc.TILT_SERVO_MIN_DEG


def test_k1_head_clamps():
    yaw, pitch = hc.k1_head_from_model(90.0, 90.0)
    assert yaw == pytest.approx(hc.K1_HEAD_YAW_LIMIT_RAD)
    assert pitch == pytest.approx(hc.K1_HEAD_PITCH_MIN_RAD)
    yaw, pitch = hc.k1_head_from_model(-90.0, -90.0)
    assert yaw == pytest.approx(-hc.K1_HEAD_YAW_LIMIT_RAD)
    assert pitch == pytest.approx(hc.K1_HEAD_PITCH_MAX_RAD)


def test_gesture_offset_envelope():
    dur = hc.gesture_duration_s()
    assert hc.gesture_offset_deg(0.0) == 0.0
    assert hc.gesture_offset_deg(dur + 1.0) == 0.0
    # symmetric pan sine: full-amp peaks at every quarter/half-cycle offset
    # past the ramp-in (ramp 0.3s < period 0.5s at 2 Hz)
    assert hc.gesture_offset_deg(1.25 / hc.GESTURE_FREQ_HZ) == \
        pytest.approx(hc.GESTURE_AMP_PAN_DEG)
    assert hc.gesture_offset_deg(1.75 / hc.GESTURE_FREQ_HZ) == \
        pytest.approx(-hc.GESTURE_AMP_PAN_DEG)
    # ramp-in: quarter period of the first cycle is attenuated
    assert abs(hc.gesture_offset_deg(0.25 / hc.GESTURE_FREQ_HZ)) < hc.GESTURE_AMP_PAN_DEG


def test_gesture_nod_is_one_sided_below_neutral():
    """'say yes' = repeated bows: offset always <= 0, each cycle one full
    bow (neutral -> depth -> neutral). Servo +20 top stop has no headroom
    above the measured neutral (4), so a symmetric nod would clamp."""
    amp = hc.GESTURE_AMP_TILT_DEG
    f = hc.GESTURE_FREQ_HZ
    # mid-cycle 2 (past the ramp-in) = full depth below neutral
    assert hc.gesture_offset_deg(1.5 / f, amp_deg=amp, one_sided=True) == \
        pytest.approx(-amp)
    assert hc.gesture_offset_deg(2.0 / f, amp_deg=amp, one_sided=True) == \
        pytest.approx(0.0, abs=1e-9)           # cycle boundary = back at neutral
    for step in range(1, 40):                  # entire gesture never goes up
        t = step * dur / 40 if (dur := hc.gesture_duration_s()) else 0
        assert hc.gesture_offset_deg(t, amp_deg=amp, one_sided=True) <= 0.0


# --- Sequence chains (one bot per chain; NON-MOTION steps only —
# position-moving steps break drag_twin's waypath-watch, rewound 2026-09-05) ---

def test_chain_face_then_say(paths):
    ev._handle_task_clause("face west, then say no", ENTS)
    a = _assignments(paths)["blue1"]
    assert a["action"] == "Seq"
    assert a["steps"][0] == {"action": "Face", "yaw": math.pi}
    assert a["steps"][1]["gesture"] == "no"
    assert "id" in a


def test_move_chain_flattens_to_waypath(paths):
    """'go to 2,2, then pause 2sec, then go to 3,3' -> WAYPOINTS (the proven
    machinery — NOT bridge Seq moves, which caused the drag_twin teleport
    loop, rewound 2026-09-05). The pause attaches to the preceding stop."""
    ev._handle_task_clause("go to 2,2, then pause 2sec, then go to 3,3", ENTS)
    assert ev._demo_bot_state("blue1")["waypoints"] == [
        {"label": "FIRST", "x": 2.0, "y": 2.0, "hold_duration": 2.0},
        {"label": "SECOND", "x": 3.0, "y": 3.0, "hold_duration": 0.0},
    ]


def test_move_chain_goto_is_go_to(paths):
    ev._handle_task_clause("goto 3,3, then go to (1,1)", ENTS)
    wps = ev._demo_bot_state("blue1")["waypoints"]
    assert [(w["x"], w["y"]) for w in wps] == [(3.0, 3.0), (1.0, 1.0)]


def test_move_chain_leading_pause_holds_at_current_pos(paths):
    ev._handle_task_clause("pause 1s, then go to (2,0)", ENTS)
    # blue_1 stands at (0,0) in ENTS -> hold there first, then drive
    assert ev._demo_bot_state("blue1")["waypoints"] == [
        {"label": "FIRST", "x": 0.0, "y": 0.0, "hold_duration": 1.0},
        {"label": "SECOND", "x": 2.0, "y": 0.0, "hold_duration": 0.0},
    ]


def test_move_chain_respects_prefix_and_scope(paths):
    ev._handle_task_clause("blue_2 goto 1,1, then goto 2,2", ENTS)
    assert ev._demo_bot_state("blue2")["waypoints"][0]["x"] == 1.0
    assert "blue1" not in {b: None for b in ev._demo_state} or \
        not ev._demo_bot_state("blue1")["waypoints"]


def test_landmark_pause_compound_still_compiles(paths, monkeypatch):
    """REGRESSION GUARD (5d): the wing task ('landmark, pause, landmark')
    is pure compiler vocabulary — it must reach the 7B, not be rejected by
    the chain rules (5c accidentally rejected it via any(steps))."""
    calls = []
    monkeypatch.setattr(ev, "_compile_demo_task",
                        lambda *a, **k: calls.append(a) or True)
    ev._handle_task_clause("go to the left wing, pause 2 seconds, go to the right wing", ENTS)
    assert calls, "landmark+pause compounds belong to the compiler"


def test_facing_words_never_reach_the_compiler(paths, monkeypatch):
    """The 7B has no facing concept — it guessed coordinates for 'face west'
    in compounds. Mixed compile+facing compounds are rejected instead."""
    def boom(*a, **k):
        raise AssertionError("facing words must not reach the compiler")
    monkeypatch.setattr(ev, "_compile_demo_task", boom)
    ev._handle_task_clause("go to the wing, then face north", ENTS)
    assert not os.path.exists(paths["strat"])


def test_mixed_facing_move_chain_rejected(paths, monkeypatch):
    """Facing + move in ONE chain is ambiguous — rejected with guidance
    (run 'face west', then 'go to (1,1)' as two commands)."""
    def boom(*a, **k):
        raise AssertionError("mixed chain must not reach the compiler")
    monkeypatch.setattr(ev, "_compile_demo_task", boom)
    ev._handle_task_clause("face west, then go to 1,1", ENTS)
    assert not os.path.exists(paths["strat"])


def test_chain_next_alias_and_pause(paths):
    ev._handle_task_clause("say no, next pause 2s, then face north", ENTS)
    a = _assignments(paths)["blue1"]
    assert a["steps"][0]["gesture"] == "no"
    assert a["steps"][1] == {"action": "Pause", "duration": 2.0}
    assert a["steps"][2] == {"action": "Face", "yaw": math.pi / 2}


def test_chain_respects_explicit_prefix(paths):
    ev._handle_task_clause("blue_2 look left, then say no", ENTS)
    a = _assignments(paths)["blue2"]
    assert a["steps"][0]["pan_deg"] == hc.LOOK_PAN_DEG
    assert a["steps"][1]["gesture"] == "no"


def test_chain_clears_waypoints(paths):
    st = ev._demo_bot_state("blue1")
    st["waypoints"] = ev._norm_demo_waypoints([{"label": "A", "x": 1, "y": 1}])
    ev._handle_task_clause("face north, then say yes", ENTS)
    assert st["waypoints"] == []
    assert st["fast_cmd"]["action"] == "Seq"


def test_pure_compile_compound_still_reaches_compiler(paths, monkeypatch):
    """No chain-able segment at all (patrol+return) -> the 7B compiler owns
    the compound, unchanged by the chain rules."""
    calls = []
    monkeypatch.setattr(ev, "_compile_demo_task",
                        lambda *a, **k: calls.append(a) or True)
    ev._handle_task_clause("patrol between (-2,0) and (2,0), then return", ENTS)
    assert calls, "pure compile compounds must reach the compiler"


def test_comma_chain_preserves_bot_prefix(paths, monkeypatch):
    """Comma-split move sub-clauses are rejoined with 'then' so the 7B
    compiler sees the full sequence, and the bot prefix is preserved.
    Without these, 'blue_2 go to the left wing, pause 2 seconds, go to the
    right wing' sends the second sub-clause to ALL_BOTS (no prefix) → blue_1
    also moves, AND the two calls overwrite each other's waypoints instead
    of producing one chain. Regression 2026-09-06."""
    calls = []
    monkeypatch.setattr(ev, "_compile_demo_task",
                        lambda *a, **k: calls.append(a) or True)
    ev._handle_compound_task(
        "blue_2 go to the left wing, pause 2 seconds, go to the right wing",
        ENTS)
    assert len(calls) == 1, f"expected 1 compiler call (rejoined), got {len(calls)}"
    bot, text = calls[0][0], calls[0][1]
    assert bot == "blue2", f"bot={bot}, expected blue_2"
    assert "then" in text, "rejoined text must contain 'then' connector"


def test_chain_then_split_does_not_touch_semicolons(paths, monkeypatch):
    """';' stays PARALLEL clauses (independent bots) — not a sequence."""
    task = paths["strat"].parent / "task_input.json"
    monkeypatch.setattr(ev, "TASK_INPUT_PATH", str(task))
    task.write_text(json.dumps({"task": "blue_1 go to (1,1); blue_2 go to (2,2)"}))
    ev._check_task_input(ENTS, {})
    # direct moves = one-waypoint waypaths (proven machinery, auto-park)
    assert ev._demo_bot_state("blue1")["waypoints"] == [
        {"label": "FIRST", "x": 1.0, "y": 1.0, "hold_duration": 0.0}]
    assert ev._demo_bot_state("blue2")["waypoints"] == [
        {"label": "FIRST", "x": 2.0, "y": 2.0, "hold_duration": 0.0}]


# --- head_cmds waveforms ---

def test_body_bob_envelope():
    dur = hc.gesture_duration_s()
    assert hc.body_bob_mps(0.0) == 0.0
    assert hc.body_bob_mps(dur + 1.0) == 0.0
    # forward surge at quarter cycle (past ramp), back surge at 3/4 cycle
    assert hc.body_bob_mps(1.25 / hc.GESTURE_FREQ_HZ) == pytest.approx(hc.BODY_BOB_MPS)
    assert hc.body_bob_mps(1.75 / hc.GESTURE_FREQ_HZ) == pytest.approx(-hc.BODY_BOB_MPS)


def test_gesture_body_bots_constant():
    """Y#1 (no gimbal) runs say-gestures on its chassis; everything else
    (Y#2 camera, K1 head) keeps its own expression."""
    assert hc.GESTURE_BODY_BOTS == ("blue1",)


# --- Bridge strategy passthrough + Face snapshot semantics (skip w/o rclpy) ---


def _fb_mock(bridge_mod):
    """Create a minimal FB mock with _face_target_yaw, _advance_seq, and
    _seq_effective wired to the real HalBridge methods (unbound calls pass
    self=fb). Also includes get_logger and _publish_odom_states for
    read_llm_strategy."""
    import logging
    fb = type("FB", (), {
        "_face_target_yaw": bridge_mod.HalBridge._face_target_yaw,
        "_advance_seq": bridge_mod.HalBridge._advance_seq,
        "_seq_effective": bridge_mod.HalBridge._seq_effective,
        "get_logger": lambda self: logging.getLogger("test_bridge"),
        "_publish_odom_states": lambda self: None,
        "TARGET_EXTRA_KEYS": bridge_mod.HalBridge.TARGET_EXTRA_KEYS,
    })()
    fb._seq_state = {}
    fb._face_state = {}
    return fb


def test_bridge_face_snapshot_semantics(tmp_path):
    """Relative turns must snapshot the target yaw ONCE per command id:
    re-deriving (cyaw + relative) every tick made the target move with the
    bot — endless spin (live 2026-09-05)."""
    pytest.importorskip("rclpy")
    try:
        import ollama_sandbox_bridge as bridge
    except ImportError:
        pytest.skip("gazebo_msgs/booster_msgs not available (no ROS env)")
    fb = _fb_mock(bridge)
    fb._face_state = {}
    # first sight at cyaw=0.0: snapshot = 0 + pi/2
    t1 = {"action": "face", "relative_angle": math.pi / 2, "id": 1}
    yaw1 = bridge.HalBridge._face_target_yaw(fb, "blue1", t1, 0.0)
    assert yaw1 == pytest.approx(math.pi / 2)
    # later tick at cyaw=1.0: SAME snapshot (not 1.0 + pi/2)
    yaw2 = bridge.HalBridge._face_target_yaw(fb, "blue1", t1, 1.0)
    assert yaw2 == pytest.approx(math.pi / 2)
    # new command id: fresh snapshot from the CURRENT yaw
    t2 = {"action": "face", "relative_angle": math.pi / 2, "id": 2}
    yaw3 = bridge.HalBridge._face_target_yaw(fb, "blue1", t2, 1.0)
    assert yaw3 == pytest.approx(1.0 + math.pi / 2)


def test_bridge_seq_cursor_and_forks(tmp_path):
    """Seq cursor semantics (bridge owns execution — yaw/position/time):
    face step reuses the snapshot machinery; a stale strategy carrying a
    motion step parks SAFELY (chains are non-motion only since the
    drag_twin rewind); say-step fork selects body motion for gimbal-less
    hardware and k1 head otherwise."""
    pytest.importorskip("rclpy")
    try:
        import ollama_sandbox_bridge as bridge
    except ImportError:
        pytest.skip("gazebo_msgs/booster_msgs not available (no ROS env)")
    fb = _fb_mock(bridge)
    seq = {"action": "Seq", "id": 1.0,
           "steps": [{"action": "Face", "yaw": math.pi},
                     {"action": "Pause", "duration": 5.0}]}

    # tick 1 (bot at origin, yaw 0): face step effective, snapshot stored
    eff = bridge.HalBridge._seq_effective(fb, "blue1", "yahboom", "blue1",
                                          seq, 0.0, 0.0, 0.0)
    assert eff["action"] == "Face"
    # face not yet arrived -> still on step 0
    assert bridge.HalBridge._seq_effective(fb, "blue1", "yahboom", "blue1",
                                           seq, 0.0, 0.0, 3.10)["action"] == "Face"
    # simulate arrival: mark the face snapshot arrived -> pause step (hold)
    fb._face_state["blue1"]["arrived"] = True
    eff = bridge.HalBridge._seq_effective(fb, "blue1", "yahboom", "blue1",
                                          seq, 0.0, 0.0, 3.14)
    assert eff["action"] == "hold" and fb._seq_state["blue1"]["idx"] == 1

    # stale strategy carrying a motion step: parks safely, never drives
    stale = {"action": "Seq", "id": 2.0,
             "steps": [{"action": "Move", "x": 3.0, "y": 1.0}]}
    eff = bridge.HalBridge._seq_effective(fb, "blue1", "yahboom", "blue1",
                                          stale, 0.0, 0.0, 0.0)
    assert eff["action"] == "hold"


def test_bridge_seq_say_step_forks_by_hardware(tmp_path):
    pytest.importorskip("rclpy")
    try:
        import ollama_sandbox_bridge as bridge
    except ImportError:
        pytest.skip("gazebo_msgs/booster_msgs not available (no ROS env)")
    fb = _fb_mock(bridge)
    seq = {"action": "Seq", "id": 9.0,
           "steps": [{"action": "Head", "gesture": "no", "cycles": 3}]}

    def eff_for(hw_type, bot):
        fb._seq_state.clear()
        return bridge.HalBridge._seq_effective(fb, "x", hw_type, bot,
                                               seq, 0.0, 0.0, 0.0)
    # Y#1 (yahboom, body bot): the head BRANCH forks gestures to the body
    # via GESTURE_BODY_BOTS — the cursor emits a Head gesture target either
    # way; the fork happens at dispatch. Cursor output is the raw step:
    e = eff_for("yahboom", "blue1")
    assert e["action"] == "Head" and e["gesture"] == "no"
    # K1 gets the same step (its branch routes to RPC 2004)
    e = eff_for("k1", "blue1")
    assert e["action"] == "Head" and e["gesture"] == "no"


def test_bridge_seq_effective_look_step_advances(tmp_path):
    pytest.importorskip("rclpy")
    try:
        import ollama_sandbox_bridge as bridge
    except ImportError:
        pytest.skip("gazebo_msgs/booster_msgs not available (no ROS env)")
    fb = _fb_mock(bridge)
    seq = {"action": "Seq", "id": 5.0,
           "steps": [{"action": "Head", "pan_deg": 30.0, "tilt_deg": 0.0},
                     {"action": "Face", "yaw": 0.0}]}
    eff = bridge.HalBridge._seq_effective(fb, "blue1", "yahboom", "blue1",
                                          seq, 0.0, 0.0, 0.0)
    assert eff["pan_deg"] == 30.0                 # look pose emitted ...
    assert fb._seq_state["blue1"]["idx"] == 1    # ... and cursor moved on


def test_bridge_read_llm_strategy_passthrough(tmp_path):
    pytest.importorskip("rclpy")
    try:
        import ollama_sandbox_bridge as bridge
    except ImportError:
        pytest.skip("gazebo_msgs/booster_msgs not available (no ROS env)")
    strat = tmp_path / "current_strategy.json"
    strat.write_text(json.dumps({"assignments": {
        "blue2": {"action": "Head", "pan_deg": 30.0, "tilt_deg": -5.0},
        "blue1": {"action": "Face", "yaw": 1.5},
        "blue3": {"action": "Head", "gesture": "no", "cycles": 3, "id": 42},
        "blue_4": {"action": "Move", "x": 1.0, "y": 2.0},
        "blue_5": {"action": "Seq", "id": 7.0, "steps": [
            {"action": "Move", "x": 3.0, "y": 1.0},
            {"action": "Pause", "duration": 2.0},
            {"action": "Face", "yaw": 1.5708},
        ]},
    }}))
    fb = _fb_mock(bridge)
    fb.strategy_file = str(strat)
    fb.targets = {"blue_9": {"action": "Move", "x": 9.0, "y": 9.0}}   # stale entry
    bridge.HalBridge.read_llm_strategy(fb)
    assert fb.targets["blue2"]["pan_deg"] == 30.0
    assert fb.targets["blue2"]["tilt_deg"] == -5.0
    assert fb.targets["blue1"]["yaw"] == 1.5
    assert fb.targets["blue3"]["gesture"] == "no"
    assert fb.targets["blue3"]["id"] == 42
    assert fb.targets["blue_4"]["x"] == 1.0
    assert "pan_deg" not in fb.targets["blue_4"]
    # Seq steps MUST survive the strategy read (whitelist gap 2026-09-05:
    # 'steps' was dropped -> _seq_effective saw an empty list -> "sequence
    # finished" -> bots never moved)
    assert fb.targets["blue_5"]["steps"][0] == {"action": "Move", "x": 3.0, "y": 1.0}
    assert fb.targets["blue_5"]["steps"][1] == {"action": "Pause", "duration": 2.0}
    assert len(fb.targets["blue_5"]["steps"]) == 3
    # Stale-target rebuild (runaway fix 2026-09-05): bots absent from the
    # strategy must NOT keep executing their last command
    assert "blue_9" not in fb.targets


def test_bridge_seq_production_roundtrip(tmp_path):
    """The EXACT chain that broke live: Seq in the strategy file ->
    read_llm_strategy -> _seq_effective must yield the right step target.
    (A unit test fed _seq_effective directly and missed the whitelist gap.)"""
    pytest.importorskip("rclpy")
    try:
        import ollama_sandbox_bridge as bridge
    except ImportError:
        pytest.skip("gazebo_msgs/booster_msgs not available (no ROS env)")
    strat = tmp_path / "current_strategy.json"
    strat.write_text(json.dumps({"assignments": {
        "blue1": {"action": "Seq", "id": 99.0, "steps": [
            {"action": "Face", "yaw": 3.14}]}}}))
    fb = _fb_mock(bridge)
    fb.strategy_file = str(strat)
    fb.targets = {}
    bridge.HalBridge.read_llm_strategy(fb)
    eff = bridge.HalBridge._seq_effective(fb, "blue1", "yahboom", "blue1",
                                          fb.targets["blue1"], 0.0, 0.0, 0.0)
    assert eff is not None and eff["action"] == "Face"
    assert eff["yaw"] == 3.14


def test_waypoint_merge_collapses_duplicate_pauses():
    """'left wing, pause 2s, right wing' compiles (via the 7B's own few-shot
    example) to a DUPLICATE waypoint carrying the hold — merge them."""
    wps = ev._norm_demo_waypoints([
        {"label": "FIRST", "x": 2.0, "y": 2.5},
        {"label": "SECOND", "x": 2.0, "y": 2.5, "hold_duration": 2.0},
        {"label": "THIRD", "x": 2.0, "y": -2.5},
    ])
    merged = ev._merge_duplicate_waypoints(wps)
    assert len(merged) == 2
    assert merged[0]["label"] == "FIRST"
    assert merged[0]["hold_duration"] == 2.0
    assert merged[1]["label"] == "SECOND"          # renumbered
    assert merged[1]["x"] == 2.0 and merged[1]["y"] == -2.5


def test_waypoint_merge_keeps_distinct_waypoints():
    wps = ev._norm_demo_waypoints([
        {"label": "FIRST", "x": 0.0, "y": 0.0},
        {"label": "SECOND", "x": 3.0, "y": 0.0},
    ])
    merged = ev._merge_duplicate_waypoints(wps)
    assert len(merged) == 2 and merged[1]["label"] == "SECOND"


def test_heading_relative_tasks_are_rejected(paths, monkeypatch):
    """'move forward 1m' has no yaw ground truth — the 7B compiled it to a
    ~2.3m diagonal garbage run (live 2026-09-05). Must be rejected, not
    compiled."""
    def _boom(*a, **k):
        raise AssertionError("heading-relative task reached the compiler")
    monkeypatch.setattr(ev, "_compile_demo_task", _boom)
    ev._handle_task_clause("move forward 1m", ENTS)
    ev._handle_task_clause("bots move backward 2m", ENTS)
    assert not os.path.exists(paths["strat"])


def test_go_back_to_phrasing_is_not_heading_relative(paths, monkeypatch):
    """Distance-less 'back' (e.g. 'move back and forth between (0,0) and
    (2,0)') must NOT trip the heading guard — it compiles normally."""
    called = []
    monkeypatch.setattr(ev, "_compile_demo_task",
                        lambda *a, **k: called.append(a) or True)
    ev._handle_task_clause("move back and forth between (0,0) and (2,0)", ENTS)
    assert called, "'back and forth' must reach the compiler, not the guard"


# --- K1 calibration Goto (eval-side routing only; bridge-side odom loop
# is integration-level, not unit-testable without rclpy) ---

def test_k1_goto_writes_assignment(paths):
    ev._handle_task_clause("k1 go to (1,0)", ENTS)
    a = _assignments(paths)
    assert a.get("k1") == {"action": "Goto", "x": 1.0, "y": 0.0}


def test_k1_goto_does_not_overwrite_blue_1(paths):
    ev._handle_task_clause("k1 go to (2,0)", ENTS)
    a = _assignments(paths)
    assert "blue1" not in a


def test_blue_1_direct_move_still_uses_move(paths):
    ev._handle_task_clause("blue_1 go to (3,0)", ENTS)
    st = ev._demo_bot_state("blue1")
    assert any(w["x"] == 3.0 and w["y"] == 0.0 for w in st["waypoints"])


# --- Yahboom calibration Goto (K1 field-test rehearsal, 2026-09-08) ---
# Same routing as k1: y1/y2 prefix + coords -> bridge odom loop; blue bots
# keep the sim-pose Move. TimedMove verbs unchanged (open-loop calib).

def test_y1_goto_writes_assignment(paths):
    ev._handle_task_clause("y1 go to (0.5, 0)", ENTS)
    a = _assignments(paths)
    assert a.get("y1") == {"action": "Goto", "x": 0.5, "y": 0.0}


def test_yahboom2_alias_goto_writes_assignment(paths):
    ev._handle_task_clause("yahboom2 go to (1, 1)", ENTS)
    a = _assignments(paths)
    assert a.get("y2") == {"action": "Goto", "x": 1.0, "y": 1.0}


def test_y_goto_does_not_touch_blue_1(paths):
    ev._handle_task_clause("y1 go to (2,0)", ENTS)
    a = _assignments(paths)
    assert "blue1" not in a
    st = ev._demo_bot_state("blue1")
    assert not any(w["x"] == 2.0 and w["y"] == 0.0 for w in st["waypoints"])


def test_y_forward_still_timedmove_in_calib(paths, monkeypatch):
    monkeypatch.setattr(ev, "CALIB", True)
    ev._handle_task_clause("y1 forward 0.5", ENTS)
    a = _assignments(paths)
    assert a.get("y1", {}).get("action") == "TimedMove"


# --- Hardware home / face / turn verbs (2026-09-08, live complaints) ---

def test_y1_goto_home_is_goto_origin_in_calib(paths, monkeypatch):
    # "y1 go to home" used to fall through to the 7B compiler (waypath,
    # sim semantics — drove nothing on hardware). Home = odom origin.
    monkeypatch.setattr(ev, "CALIB", True)
    ev._handle_task_clause("y1 go to home", ENTS)
    a = _assignments(paths)
    assert a.get("y1") == {"action": "Goto", "x": 0.0, "y": 0.0}


def test_y1_return_is_goto_origin_in_calib(paths, monkeypatch):
    monkeypatch.setattr(ev, "CALIB", True)
    ev._handle_task_clause("y1 return", ENTS)
    a = _assignments(paths)
    assert a.get("y1") == {"action": "Goto", "x": 0.0, "y": 0.0}


def test_y1_turn_with_degree_suffix_in_calib(paths, monkeypatch):
    # "y1 turn 45o" (people type the degree sign as 'o') used to miss the
    # turn regex and hit the facing-words rejection. Turn routes CLOSED-
    # LOOP now, and the sign is the COMPASS convention (user 2026-09-08,
    # "counter intuitive"): + = clockwise/right = NEGATIVE ROS yaw.
    monkeypatch.setattr(ev, "CALIB", True)
    ev._handle_task_clause("y1 turn 45o", ENTS)
    a = _assignments(paths)
    assert a.get("y1", {}).get("action") == "Face"
    assert abs(a.get("y1", {}).get("relative_angle", 0) - math.radians(-45)) < 1e-9


def test_y1_turn_negative_routes_relative_face(paths, monkeypatch):
    # turn -30 = counterclockwise/left = +30° ROS yaw.
    monkeypatch.setattr(ev, "CALIB", True)
    ev._handle_task_clause("y1 turn -30", ENTS)
    a = _assignments(paths)
    assert a.get("y1", {}).get("action") == "Face"
    assert abs(a.get("y1", {}).get("relative_angle", 0) - math.radians(30)) < 1e-9


def test_calib_y1_say_no_is_seq_of_closed_loop_swings(paths, monkeypatch):
    # Oscillating vyaw CANCELS in the board yaw PID (live twice, even at
    # 1 Hz) — the calib shake is built from arrival-latched relative
    # Faces instead (the proven turn machinery). y1 = gimbal-less body
    # bot; y2 keeps the servo pan path.
    monkeypatch.setattr(ev, "CALIB", True)
    ev._handle_task_clause("y1 say no", ENTS)
    a = _assignments(paths)
    assert a.get("y1", {}).get("action") == "Seq"
    steps = a.get("y1", {}).get("steps", [])
    assert all(s.get("action") == "Face" for s in steps)
    # starts +A, alternates -2A/+2A, ends -A back at base
    A = math.radians(ev.CALIB_SAYNO_SHAKE_AMP_DEG)
    assert abs(steps[0]["relative_angle"] - A) < 1e-9
    assert abs(steps[-1]["relative_angle"] + A) < 1e-9


def test_canon_assignments_normalizes_executor_world_names():
    # The match-mode 3B executor echoes Worldstate entity names (blue_1)
    # into strategy slots; relays + fast-paths speak canon (blue1). The
    # normalization at the write boundary makes the two conventions ONE —
    # live 2026-09-12: the mismatch braked every blue bot in match mode.
    a = ev._canon_assignments({
        "blue_1": {"action": "Move", "x": 1.0, "y": 0.0},
        "blue_2": {"action": "Move", "x": 2.0, "y": 0.0},
        "blue_3": {"action": "Move", "x": 3.0, "y": 0.0},
        "y1": {"action": "Hold"},
        "k1_bot": {"action": "Goto", "x": 0.0, "y": 0.0},
    })
    assert set(a) == {"blue1", "blue2", "blue3", "y1", "k1"}
    assert a["blue1"]["action"] == "Move"


# --- Demo pair-mirror semantics (Option A, 2026-09-14): in demo mode a
# y1/y2-prefixed command addresses the PAIR (sim twin + hardware mirror
# share one command stream) — the redirect happens at the write boundary,
# driven by the relay's mirror_of declaration. Calib stays direct.

def test_demo_y1_goto_redirects_to_mirror_slot(paths, monkeypatch):
    monkeypatch.setattr(ev, "CALIB", False)
    monkeypatch.setattr(ev, "_active_mode", "demo")
    monkeypatch.setattr(ev, "_RELAY_MAPPING", {
        "blue1": {"hardware_type": "virtual", "topic": "/blue_1/cmd_vel"},
        "y1": {"hardware_type": "yahboom", "topic": "/blue_1/cmd_vel",
               "mirror_of": "blue1"},
    })
    ev._handle_task_clause("y1 go to (1,0)", ENTS)
    a = _assignments(paths)
    assert a.get("blue1") == {"action": "Goto", "x": 1.0, "y": 0.0}
    assert "y1" not in a


def test_demo_fleet_say_writes_canon_slots(paths, monkeypatch):
    # "all say yes" fans out over Worldstate entity names (blue_1/blue_2) —
    # the write boundary normalizes them to canon so the relay-keyed bridge
    # consumes them (live 2026-09-14: world-key slots braked every bot).
    monkeypatch.setattr(ev, "CALIB", False)
    monkeypatch.setattr(ev, "_active_mode", "demo")
    monkeypatch.setattr(ev, "_RELAY_MAPPING", {})
    ev._handle_task_clause("all say yes", ENTS)
    a = _assignments(paths)
    assert a.get("blue1", {}).get("action") == "Head"
    assert a.get("blue2", {}).get("action") == "Head"
    assert "blue_1" not in a and "blue_2" not in a


def test_calib_y1_goto_stays_direct(paths, monkeypatch):
    # Calib = direct hardware addressing: the relay mirror_of must NOT
    # redirect y1 commands (the whole field-day vocabulary depends on it).
    monkeypatch.setattr(ev, "CALIB", True)
    monkeypatch.setattr(ev, "_active_mode", "demo")
    monkeypatch.setattr(ev, "_RELAY_MAPPING",
                        {"y1": {"hardware_type": "yahboom",
                                "mirror_of": "blue1"}})
    ev._handle_task_clause("y1 go to (1,0)", ENTS)
    a = _assignments(paths)
    assert a.get("y1") == {"action": "Goto", "x": 1.0, "y": 0.0}


def test_y1_face_east_writes_face_assignment(paths):
    # Face routes to a fast_cmd assignment on the y1 slot; the bridge
    # executes it against the estimator yaw (CALIB gate + odom source).
    ev._handle_task_clause("y1 face east", ENTS)
    a = _assignments(paths)
    assert a.get("y1", {}).get("action") == "Face"
    assert "yaw" in a.get("y1", {})


# --- Cleanup round (2026-09-08): mode merge, TimedMove ids, vocabulary
# freeze, say gestures on hardware ---

def test_timedmove_carries_id_in_calib(paths, monkeypatch):
    # The bridge done-set keys by id: without it a re-loaded assignment
    # re-latched forever ("y1 turn -30" = endless turn-stop-turn-stop).
    # forward/back remain open-loop TimedMove (turn went closed-loop).
    monkeypatch.setattr(ev, "CALIB", True)
    ev._handle_task_clause("y1 forward 0.5", ENTS)
    a = _assignments(paths)
    assert a.get("y1", {}).get("action") == "TimedMove"
    assert "id" in a.get("y1", {})


def test_calib_freeze_rejects_compiler_vocab(paths, monkeypatch):
    # Compiler vocabulary (landmarks/shapes) is demo-mode — in calib it
    # must reject loudly instead of compiling dead waypaths. Rejection
    # writes NOTHING (the strategy file may not even exist).
    monkeypatch.setattr(ev, "CALIB", True)
    ev._handle_task_clause("y1 go to the left wing", ENTS)
    try:
        a = _assignments(paths)
    except FileNotFoundError:
        return   # nothing was written at all — the cleanest rejection
    assert "y1" not in a


def test_y1_say_yes_routes_head(paths):
    # Say gestures are IN the calib vocabulary: the Head assignment lands
    # on the y1 slot (bridge body-gesture fork, estimator yaw base).
    ev._handle_task_clause("y1 say yes", ENTS)
    a = _assignments(paths)
    assert a.get("y1", {}).get("action") == "Head"
    assert a.get("y1", {}).get("gesture") == "yes"


def test_y1_face_chain_routes_seq(paths):
    # Chained facing steps route to ONE Seq assignment on the y1 slot —
    # the bridge cursor executes them in order (calib: 'seq' admitted
    # through the gate, estimator yaw as the relative-turn base).
    ev._handle_task_clause("y1 face east, then face north", ENTS)
    a = _assignments(paths)
    assert a.get("y1", {}).get("action") == "Seq"
    steps = a.get("y1", {}).get("steps", [])
    assert [s.get("action") for s in steps] == ["Face", "Face"]


def test_calib_boot_compass_yaw0_is_north(paths, monkeypatch):
    # Calib convention (user 2026-09-08): power-cycle at the home mark with
    # the nose facing NORTH — odom boots (0,0,0), so face north = yaw 0
    # (no-op at boot), face east = -π/2 (clockwise right turn).
    monkeypatch.setattr(ev, "CALIB", True)
    ev._handle_task_clause("y1 face north", ENTS)
    a = _assignments(paths)
    assert abs(a.get("y1", {}).get("yaw", 999) - 0.0) < 1e-9
    ev._handle_task_clause("y1 face east", ENTS)
    a = _assignments(paths)
    assert abs(a.get("y1", {}).get("yaw", 0) - (-math.pi / 2)) < 1e-9


def test_demo_world_compass_unchanged(paths, monkeypatch):
    # Demo keeps the world frame: sim twins spawn with yaw 0 = +X = east.
    monkeypatch.setattr(ev, "CALIB", False)
    ev._handle_task_clause("blue_1 face east", ENTS)
    a = _assignments(paths)
    assert abs(a.get("blue1", {}).get("yaw", 999) - 0.0) < 1e-9
