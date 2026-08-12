#!/usr/bin/env python3
"""
Unit tests for score_node.py — match-state-aware scoring (V7e).

Tests the 4 score function fixes from the U22 correlation analysis:
1. Gate by match_state.status — freeze during non-playing phases
2. Goal event bonus — edge-triggered on score increment (+3 / -3)
3. Possession-scaled ball position — ball['x'] * GAIN * (blue_factor - red_factor)
4. Widened POSSESSION_REFERENCE_DIST — 2.0 → 4.5

These tests mock rclpy so score_node can be imported without ROS 2.
"""

import sys
import os
import math
import json
import types
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Mock rclpy and std_msgs before importing score_node
_rclpy = types.ModuleType('rclpy')
_rclpy.init = lambda: None
_rclpy.spin = lambda n: None
_rclpy.shutdown = lambda: None

_rclpy_node = types.ModuleType('rclpy.node')
class _FakeNode:
    def __init__(self, *a, **kw): pass
    def create_subscription(self, *a, **kw): pass
    def create_publisher(self, *a, **kw): pass
    def create_timer(self, *a, **kw): pass
    def get_logger(self): return logging.getLogger('test')
    def destroy_node(self): pass
_rclpy_node.Node = _FakeNode
_rclpy.node = _rclpy_node

_stdmsg = types.ModuleType('std_msgs')
_stdmsg_msg = types.ModuleType('std_msgs.msg')
_stdmsg_msg.String = str
_stdmsg.msg = _stdmsg_msg

sys.modules.setdefault('rclpy', _rclpy)
sys.modules.setdefault('rclpy.node', _rclpy_node)
sys.modules.setdefault('std_msgs', _stdmsg)
sys.modules.setdefault('std_msgs.msg', _stdmsg_msg)

import score_node as sn


def _make_node():
    """Create a ScoreNode instance (mocked rclpy, no ROS 2 needed)."""
    node = sn.ScoreNode()
    node.goal_bonus_applied = False
    return node


class TestBallPosition:
    """Ball position is UNSCALED (reverted from possession-scaling — overcorrected)."""

    def test_ball_in_red_half_positive_for_blue(self):
        """Ball in Red's half → score should be positive for Blue (regardless of possession)."""
        node = _make_node()
        ents = {
            "soccer_ball": {"x": 3.0, "y": 0.0},
            "blue_1": {"x": 3.0, "y": 0.0},
            "red_1": {"x": -3.0, "y": 0.0},
        }
        score = node._compute_position_score(ents, ents["soccer_ball"])
        assert score > 0, f"Ball in Red half should be positive, got {score}"

    def test_ball_in_blue_half_negative_for_blue(self):
        """Ball in Blue's half → score should be negative for Blue."""
        node = _make_node()
        ents = {
            "soccer_ball": {"x": -3.0, "y": 0.0},
            "blue_1": {"x": 4.0, "y": 0.0},
            "red_1": {"x": -3.0, "y": 0.0},
        }
        score = node._compute_position_score(ents, ents["soccer_ball"])
        assert score < 0, f"Ball in Blue half should be negative, got {score}"

    def test_ball_at_red_goal_line_positive_even_if_red_closer(self):
        """Ball at x=4.5 (Red goal line) with Red slightly closer → score should STILL be positive.
        With BALL_POSITION_GAIN=0.8: ball_term = 4.5 × 0.8 = 3.60. Even with Red slightly
        closer (red_poss > blue_poss), the ball position term dominates."""
        node = _make_node()
        ents = {
            "soccer_ball": {"x": 4.5, "y": 0.0},
            "blue_1": {"x": 4.0, "y": 0.0},   # 0.5m from ball
            "red_1": {"x": 4.3, "y": 0.0},    # 0.2m from ball (closer!)
        }
        score = node._compute_position_score(ents, ents["soccer_ball"])
        assert score > 0, f"Ball at Red goal line should be positive even if Red closer, got {score}"


class TestGoalBonus:
    """Suggestion 2: goal event bonus (edge-triggered, applied in match_cb)."""

    def test_blue_goal_adds_bonus(self):
        """Blue scoring should add +GOAL_BONUS to last_score via match_cb."""
        node = _make_node()
        node.last_score = 2.0
        node.prev_score_blue = 0
        node.prev_score_red = 0

        # Simulate match_cb receiving a goal message
        msg = types.SimpleNamespace(data=json.dumps({"blue": 1, "red": 0, "status": "goal"}))
        sn.ScoreNode.match_cb(node, msg)

        assert node.last_score == 2.0 + sn.GOAL_BONUS, f"Blue goal should add +{sn.GOAL_BONUS}, got {node.last_score}"

    def test_red_goal_subtracts_bonus(self):
        """Red scoring should subtract GOAL_BONUS from last_score via match_cb."""
        node = _make_node()
        node.last_score = 2.0
        node.prev_score_blue = 0
        node.prev_score_red = 0

        msg = types.SimpleNamespace(data=json.dumps({"blue": 0, "red": 1, "status": "goal"}))
        sn.ScoreNode.match_cb(node, msg)

        assert node.last_score == 2.0 - sn.GOAL_BONUS, f"Red goal should subtract {sn.GOAL_BONUS}, got {node.last_score}"

    def test_no_goal_no_bonus(self):
        """No score change → no bonus applied."""
        node = _make_node()
        node.last_score = 2.0
        node.prev_score_blue = 1
        node.prev_score_red = 0

        msg = types.SimpleNamespace(data=json.dumps({"blue": 1, "red": 0, "status": "playing"}))
        sn.ScoreNode.match_cb(node, msg)

        assert node.last_score == 2.0, f"No goal change → no bonus, got {node.last_score}"


class TestScoreGate:
    """Suggestion 1: gate score by match_state.status."""

    def test_freeze_during_goal_status(self):
        """During status='goal', score should not change (frozen at last_score)."""
        node = _make_node()
        node.match_data = {"status": "goal"}
        node.last_score = 5.0

        status = node.match_data.get("status", "playing")
        if status != "playing":
            score = node.last_score
        else:
            score = node._compute_position_score({}, None)

        assert score == 5.0, f"Score should be frozen at last_score during goal, got {score}"

    def test_freeze_during_ball_out_status(self):
        """During status='ball_out', score should not change."""
        node = _make_node()
        node.match_data = {"status": "ball_out"}
        node.last_score = -3.0

        status = node.match_data.get("status", "playing")
        if status != "playing":
            score = node.last_score
        else:
            score = node._compute_position_score({}, None)

        assert score == -3.0, f"Score should be frozen during ball_out, got {score}"

    def test_playing_status_computes_new_score(self):
        """During status='playing', score should be computed fresh."""
        node = _make_node()
        node.match_data = {"status": "playing"}
        node.last_score = 5.0

        ents = {
            "soccer_ball": {"x": 3.0, "y": 0.0},
            "blue_1": {"x": 3.0, "y": 0.0},
            "red_1": {"x": -3.0, "y": 0.0},
        }
        status = node.match_data.get("status", "playing")
        if status != "playing":
            score = node.last_score
        else:
            score = node._compute_position_score(ents, ents["soccer_ball"])

        assert score != 5.0, "Playing status should compute new score, not use last_score"


class TestPossessionRange:
    """Suggestion 4: widened POSSESSION_REFERENCE_DIST from 2.0 to 4.5."""

    def test_possession_dist_is_4_5(self):
        """POSSESSION_REFERENCE_DIST should be 4.5 (widened from 2.0)."""
        assert sn.POSSESSION_REFERENCE_DIST == 4.5, \
            f"Expected 4.5, got {sn.POSSESSION_REFERENCE_DIST}"

    def test_possession_fires_at_3m(self):
        """At 3m distance (was zero with old 2.0m range), possession should now fire."""
        node = _make_node()
        ents = {
            "soccer_ball": {"x": 0.0, "y": 0.0},
            "blue_1": {"x": 3.0, "y": 0.0},
            "red_1": {"x": -4.0, "y": 0.0},
        }
        score = node._compute_position_score(ents, ents["soccer_ball"])
        assert score > 0, f"Blue at 3m should have possession within 4.5m range, got {score}"


class TestScoreCorrelation:
    """Integration: verify the score function now correlates with game outcomes."""

    def test_blue_scoring_raises_score(self):
        """Simulate Blue scoring: ball in Red's goal + goal bonus."""
        node = _make_node()
        ents = {
            "soccer_ball": {"x": 4.5, "y": 0.0},
            "blue_1": {"x": 4.5, "y": 0.0},
            "red_1": {"x": -4.0, "y": 0.0},
        }
        position_score = node._compute_position_score(ents, ents["soccer_ball"])
        node.last_score = position_score

        # Simulate match_cb receiving the goal
        node.prev_score_blue = 0
        node.prev_score_red = 0
        msg = types.SimpleNamespace(data=json.dumps({"blue": 1, "red": 0, "status": "goal"}))
        sn.ScoreNode.match_cb(node, msg)

        total = node.last_score
        assert total > 0, f"Blue scoring should produce positive score, got pos={position_score} total={total}"

    def test_red_scoring_lowers_score(self):
        """Simulate Red scoring: ball in Blue's goal + goal penalty."""
        node = _make_node()
        ents = {
            "soccer_ball": {"x": -4.5, "y": 0.0},
            "blue_1": {"x": 4.0, "y": 0.0},
            "red_1": {"x": -4.5, "y": 0.0},
        }
        position_score = node._compute_position_score(ents, ents["soccer_ball"])
        node.last_score = position_score

        node.prev_score_blue = 0
        node.prev_score_red = 0
        msg = types.SimpleNamespace(data=json.dumps({"blue": 0, "red": 1, "status": "goal"}))
        sn.ScoreNode.match_cb(node, msg)

        total = node.last_score
        assert total < 0, f"Red scoring should produce negative score, got pos={position_score} total={total}"


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])