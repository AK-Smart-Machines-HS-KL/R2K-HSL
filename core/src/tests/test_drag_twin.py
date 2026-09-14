"""Drag-Twin tests: external-move detection, teleport-back protocol (no ROS).

Protocol: external move detected -> "<bot> stop" (instant waypath abort,
drag_origin captured), track until the sim bot holds still -> "<bot> goto
<final>" + detector enters "awaiting_target" (suppression until the
strategy Move lands or timeout, so the teleport-back + march is never
misread as a new drag).
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ai_tactics'))

import r2k_evaluator as ev  # noqa: E402  (task-text contract integration)
from drag_twin import (DragDetector, hardware_twins_from_relay,  # noqa: E402
                       AWAIT_TARGET_TIMEOUT_S, STABLE_EPS_M, TRACK_SETTLE_S)


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def advance(self, s):
        self.t += s


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def det(clock):
    return DragDetector(status_fn=lambda: "playing", now_fn=clock)


# --- relay parsing (teleport-back scoping) ------------------------------

def test_hardware_twins_from_relay():
    # hardware_mirror: yahbooms + K1 mirror -> both blue bots teleport-back
    relay = {"mapping": {
        "blue1": {"hardware_type": "yahboom", "topic": "/blue_1/cmd_vel"},
        "blue2": {"hardware_type": "yahboom", "topic": "/blue_2/cmd_vel"},
        "k1": {"hardware_type": "k1", "topic": "/Kev1n/LocoApiTopicReq",
                   "mirror_of": "blue1"},
    }}
    assert hardware_twins_from_relay(relay) == {"blue1", "blue2"}


def test_hardware_twins_virtual_only_relay():
    # single_bot (Gazebo only): no teleport -- dragged position IS the position
    relay = {"mapping": {"blue1": {"hardware_type": "virtual",
                                    "topic": "/blue_1/cmd_vel"}}}
    assert hardware_twins_from_relay(relay) == set()
    assert hardware_twins_from_relay({}) == set()
    assert hardware_twins_from_relay({"mapping": None}) == set()


# --- detection basics ----------------------------------------------------

def test_non_blue_bots_ignored(det):
    det.note_target("soccer_ball", (1.0, 1.0))
    det.note_target("red_1", (0.0, 0.0))
    assert det.check_move("soccer_ball", 9.0, 9.0) is None
    assert det.check_move("red_1", 9.0, 9.0) is None
    assert det.check_move("blue1", 9.0, 9.0) is None  # never armed -> ignored


def test_drag_origin_is_pre_drag_position(det, clock):
    det.note_target("blue1", None)
    det.check_move("blue1", 0.0, 0.0)      # anchor
    det.check_move("blue1", 0.1, 0.0)      # small drift below threshold
    assert det.check_move("blue1", 0.5, 0.0) == "blue1 stop"
    assert det.drag_origin("blue1") == (0.1, 0.0)  # one tick before detection


def test_drag_origin_fast_first_tick_jump(det, clock):
    # waypath case: even when the first displaced tick is a big jump,
    # drag_origin is the position seen on the previous tick
    det.note_target("blue1", (2.0, 0.0))
    det.check_move("blue1", 1.0, 0.0)     # baseline (min_dist arms)
    det.check_move("blue1", 1.1, 0.0)     # still approaching
    assert det.check_move("blue1", 0.2, 0.0) == "blue1 stop"
    assert det.drag_origin("blue1") == (1.1, 0.0)


def test_waypath_drag_stop_then_goto_final_pos(det, clock):
    det.note_target("blue1", (2.0, 0.0))
    assert det.check_move("blue1", 1.0, 0.0) is None    # baseline
    assert det.check_move("blue1", 1.6, 0.0) is None    # approaching
    assert det.check_move("blue1", 1.2, 0.0) == "blue1 stop"  # dragged away
    # tracking: user keeps dragging
    clock.advance(0.1)
    assert det.check_move("blue1", 0.8, 0.3) is None
    clock.advance(0.1)
    assert det.check_move("blue1", 0.8, 0.3) is None    # holding still
    clock.advance(TRACK_SETTLE_S)
    assert det.check_move("blue1", 0.8, 0.3) == "blue1 goto 0.80,0.30"
    # goto dispatched -> suppression phase (teleport-back must not re-detect)
    assert det._watch["blue1"]["phase"] == "awaiting_target"


def test_parked_drag_stop_then_goto_final_pos(det, clock):
    det.note_target("blue1", None)
    assert det.check_move("blue1", 0.0, 0.0) is None    # anchor
    assert det.check_move("blue1", 0.2, 0.0) is None    # below threshold
    assert det.check_move("blue1", 0.35, 0.0) == "blue1 stop"
    clock.advance(0.1)
    assert det.check_move("blue1", 0.35, 0.0) is None
    clock.advance(TRACK_SETTLE_S + 0.05)
    assert det.check_move("blue1", 0.35, 0.0) == "blue1 goto 0.35,0.00"


# --- tracking -----------------------------------------------------------

def test_tracking_follows_continued_drag(det, clock):
    det.note_target("blue1", None)
    det.check_move("blue1", 0.0, 0.0)
    assert det.check_move("blue1", 0.5, 0.0) == "blue1 stop"
    for i in range(10):  # long continuous drag, never stable
        clock.advance(0.1)
        assert det.check_move("blue1", 0.5 + i * 0.2, 0.0) is None
    clock.advance(TRACK_SETTLE_S + 0.1)
    assert det.check_move("blue1", 0.5 + 9 * 0.2, 0.0) == "blue1 goto 2.30,0.00"


def test_tracking_slow_drift_settles(det, clock):
    # lab failure mode: post-release physics settle drift (cm per tick,
    # below STABLE_EPS_M but accumulating past it -> timer resets) until
    # the bot truly stops -- then the goto fires with the final position
    det.note_target("blue1", None)
    det.check_move("blue1", 0.0, 0.0)
    assert det.check_move("blue1", 0.5, 0.0) == "blue1 stop"
    for i in range(3):  # 0.03m per tick; 0.09m accumulated -> timer reset
        clock.advance(0.1)
        assert det.check_move("blue1", 0.5 + 0.03 * (i + 1), 0.0) is None
    clock.advance(TRACK_SETTLE_S + 0.05)
    assert det.check_move("blue1", 0.59, 0.0) == "blue1 goto 0.60,0.00"


def test_tracking_small_jitter_does_not_reset_settle(det, clock):
    det.note_target("blue1", None)
    det.check_move("blue1", 0.0, 0.0)
    assert det.check_move("blue1", 0.5, 0.0) == "blue1 stop"
    clock.advance(0.2)
    assert det.check_move("blue1", 0.52, 0.0) is None   # jitter < STABLE_EPS
    clock.advance(TRACK_SETTLE_S)
    assert det.check_move("blue1", 0.52, 0.0) == "blue1 goto 0.50,0.00"


# --- awaiting_target suppression ----------------------------------------

def test_await_target_blocks_detection_until_move_lands(det, clock):
    det.note_target("blue1", None)
    det.check_move("blue1", 0.0, 0.0)
    assert det.check_move("blue1", 0.5, 0.0) == "blue1 stop"
    clock.advance(TRACK_SETTLE_S + 0.05)
    assert det.check_move("blue1", 0.5, 0.0) == "blue1 goto 0.50,0.00"
    # teleport-back lands: bot appears at the origin, then marches -- a large
    # displacement during suppression must NOT fire a new stop
    clock.advance(0.1)
    assert det.check_move("blue1", 0.0, 0.0) is None   # teleported back
    clock.advance(0.2)
    assert det.check_move("blue1", 0.3, 0.0) is None   # marching to the drop
    # strategy Move lands -> suppression released, watches re-armed
    det.note_target("blue1", (0.5, 0.0))
    assert det._watch["blue1"]["phase"] is None
    assert det.check_move("blue1", 0.3, 0.0) is None   # re-armed baseline
    assert det.check_move("blue1", 0.9, 0.0) is None    # approaching target


def test_await_target_timeout_releases(det, clock):
    det.note_target("blue1", None)
    det.check_move("blue1", 0.0, 0.0)
    assert det.check_move("blue1", 0.5, 0.0) == "blue1 stop"
    clock.advance(TRACK_SETTLE_S + 0.05)
    assert det.check_move("blue1", 0.5, 0.0) == "blue1 goto 0.50,0.00"
    # no Move ever lands (evaluator failure) -> timeout releases, idle anchor
    # re-arms at the current position
    clock.advance(AWAIT_TARGET_TIMEOUT_S + 0.05)
    det.check_move("blue1", 2.0, 0.0)   # anchors (post-march position)
    assert det._watch["blue1"]["phase"] is None
    assert det.check_move("blue1", 2.4, 0.0) == "blue1 stop"  # re-armed


def test_rearm_after_full_drag_cycle(det, clock):
    det.note_target("blue1", None)
    det.check_move("blue1", 0.0, 0.0)
    assert det.check_move("blue1", 0.5, 0.0) == "blue1 stop"
    clock.advance(TRACK_SETTLE_S + 0.05)
    assert det.check_move("blue1", 0.5, 0.0) == "blue1 goto 0.50,0.00"
    det.note_target("blue1", (0.5, 0.0))    # Move lands
    # new drag event after the completed one (waypath watch: baseline first)
    clock.advance(0.1)
    assert det.check_move("blue1", 0.5, 0.0) is None    # baseline at target
    assert det.check_move("blue1", 1.2, 0.0) == "blue1 stop"
    assert det.drag_origin("blue1") == (0.5, 0.0)  # twin stood at the drop
    clock.advance(TRACK_SETTLE_S + 0.05)
    assert det.check_move("blue1", 1.2, 0.0) == "blue1 goto 1.20,0.00"


def test_status_guard_blocks_all_channels(det, clock):
    det._status_fn = lambda: "ball_out"
    det.note_target("blue1", (2.0, 0.0))
    assert det.check_move("blue1", 1.3, 0.0) is None
    assert det.check_move("blue1", 0.9, 0.0) is None    # growth blocked
    det.note_target("blue1", None)
    assert det.check_move("blue1", 4.0, 0.0) is None    # idle drift blocked
    det._status_fn = lambda: "playing"
    assert det.check_move("blue1", 4.0, 0.0) is None    # anchors
    assert det.check_move("blue1", 4.4, 0.0) == "blue1 stop"


def test_bots_tracked_independently(det, clock):
    det.note_target("blue1", (2.0, 0.0))
    det.note_target("blue2", None)
    assert det.check_move("blue2", 0.0, 1.0) is None    # blue_2 anchor
    assert det.check_move("blue1", 1.3, 0.0) is None    # blue_1 baseline
    assert det.check_move("blue1", 0.9, 0.0) == "blue1 stop"
    assert det.check_move("blue2", 0.1, 1.0) is None
    assert det.check_move("blue2", 0.5, 1.0) == "blue2 stop"


def test_dispatch_tasks_match_evaluator_contract():
    for task, bot in [("blue1 stop", "blue1"), ("blue2 goto 1.40,-0.70", "blue2"),
                      ("blue2 goto -2.05,3.00", "blue2")]:
        parsed_bot, text, _prefixed = ev._parse_task_bot(task)
        assert parsed_bot == bot
        if " goto " in task:
            assert ev.DEMO_COORD_RE.match(text), task
        else:
            assert text in ev.DEMO_FAST_STOP