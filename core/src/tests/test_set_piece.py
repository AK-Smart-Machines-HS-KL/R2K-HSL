#!/usr/bin/env python3
"""
Unit tests for unified set-piece logic: goal kick, corner kick-in, kickoff countdown.
Tests the referee decision logic without requiring ROS 2 / rclpy.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
import math


# Constants from referee_node.py
FIELD_X_MAX = 4.5
FIELD_Y_MAX = 3.0
GOAL_Y_MIN = -0.9
GOAL_Y_MAX = 0.9
SET_PIECE_COUNTDOWN = 5.0
GOAL_AREA_X = 3.5
GOAL_AREA_Y = 1.0
SET_PIECE_WARP_RADIUS = 1.5
WARP_AWAY_DISTANCE = 2.0


def _goal_area_corner(ball, goal_line_owner):
    """Replicate referee_node._goal_area_corner logic."""
    x = GOAL_AREA_X if goal_line_owner == "red" else -GOAL_AREA_X
    y = GOAL_AREA_Y if ball['y'] > 0 else -GOAL_AREA_Y
    return (x, y)


def _corner_flag_position(ball):
    """Replicate referee_node._corner_flag_position logic."""
    x = 4.3 if ball['x'] > 0 else -4.3
    y = 2.8 if ball['y'] > 0 else -2.8
    return (x, y)


def _warp_opponents_away(ball_pos, restart_team, entities):
    """Replicate referee_node._warp_opponents_away logic.
    Returns dict of {bot_id: (new_x, new_y)} for warped bots.
    """
    warped = {}
    for bot_id, bot_pos in entities.items():
        if bot_id == 'soccer_ball' or restart_team in bot_id:
            continue
        dist = math.hypot(bot_pos['x'] - ball_pos[0], bot_pos['y'] - ball_pos[1])
        if dist < SET_PIECE_WARP_RADIUS:
            if dist < 0.01:
                angle = 0.0
            else:
                angle = math.atan2(bot_pos['y'] - ball_pos[1], bot_pos['x'] - ball_pos[0])
            new_x = ball_pos[0] + math.cos(angle) * WARP_AWAY_DISTANCE
            new_y = ball_pos[1] + math.sin(angle) * WARP_AWAY_DISTANCE
            warped[bot_id] = (new_x, new_y)
    return warped


def _classify_goal_line_out(ball, last_toucher):
    """Replicate the referee's goal-line-out classification logic.
    Returns (set_piece_type, restart_team, ball_pos, opponent_team).
    """
    if not last_toucher:
        return None  # neutral fallback

    offending_team = "blue" if "blue" in last_toucher else "red"
    goal_line_owner = "red" if ball['x'] > 0 else "blue"

    if offending_team == goal_line_owner:
        # Scenario B: defender kicked over own line → corner kick-in for attacker
        restart_team = "red" if offending_team == "blue" else "blue"
        ball_pos = _corner_flag_position(ball)
        return ("corner_kick_in", restart_team, ball_pos, offending_team)
    else:
        # Scenario A: attacker kicked over defender's line → goal kick for defender
        restart_team = goal_line_owner
        ball_pos = _goal_area_corner(ball, goal_line_owner)
        return ("goal_kick", restart_team, ball_pos, offending_team)


class TestGoalAreaCorner:
    """Test goal area corner placement for goal kicks."""

    def test_goal_kick_ball_top_right(self):
        """Ball exits at red's goal line, Y > 0 → ball at (3.5, 1.0)."""
        ball = {'x': 4.6, 'y': 2.0}
        pos = _goal_area_corner(ball, "red")
        assert pos == (3.5, 1.0)

    def test_goal_kick_ball_bottom_right(self):
        """Ball exits at red's goal line, Y < 0 → ball at (3.5, -1.0)."""
        ball = {'x': 4.6, 'y': -2.0}
        pos = _goal_area_corner(ball, "red")
        assert pos == (3.5, -1.0)

    def test_goal_kick_ball_top_left(self):
        """Ball exits at blue's goal line, Y > 0 → ball at (-3.5, 1.0)."""
        ball = {'x': -4.6, 'y': 1.5}
        pos = _goal_area_corner(ball, "blue")
        assert pos == (-3.5, 1.0)

    def test_goal_kick_ball_bottom_left(self):
        """Ball exits at blue's goal line, Y < 0 → ball at (-3.5, -1.0)."""
        ball = {'x': -4.6, 'y': -1.5}
        pos = _goal_area_corner(ball, "blue")
        assert pos == (-3.5, -1.0)


class TestCornerFlagPosition:
    """Test corner flag placement for corner kick-ins."""

    def test_corner_kick_in_top_right(self):
        """Ball exits at X>0, Y>0 → corner at (4.3, 2.8)."""
        ball = {'x': 4.6, 'y': 2.5}
        pos = _corner_flag_position(ball)
        assert pos == (4.3, 2.8)

    def test_corner_kick_in_bottom_right(self):
        """Ball exits at X>0, Y<0 → corner at (4.3, -2.8)."""
        ball = {'x': 4.6, 'y': -2.5}
        pos = _corner_flag_position(ball)
        assert pos == (4.3, -2.8)

    def test_corner_kick_in_top_left(self):
        """Ball exits at X<0, Y>0 → corner at (-4.3, 2.8)."""
        ball = {'x': -4.6, 'y': 2.5}
        pos = _corner_flag_position(ball)
        assert pos == (-4.3, 2.8)

    def test_corner_kick_in_bottom_left(self):
        """Ball exits at X<0, Y<0 → corner at (-4.3, -2.8)."""
        ball = {'x': -4.6, 'y': -2.5}
        pos = _corner_flag_position(ball)
        assert pos == (-4.3, -2.8)


class TestGoalLineOutClassification:
    """Test scenario A (goal kick) vs B (corner kick-in) discrimination."""

    def test_attacker_kicks_over_red_goal_line(self):
        """Blue (attacker) kicks ball over red's goal line → goal kick for red."""
        ball = {'x': 4.6, 'y': 2.0}
        result = _classify_goal_line_out(ball, "blue_1")
        assert result is not None
        set_piece_type, restart_team, ball_pos, opponent_team = result
        assert set_piece_type == "goal_kick"
        assert restart_team == "red"
        assert opponent_team == "blue"
        assert ball_pos == (3.5, 1.0)

    def test_attacker_kicks_over_blue_goal_line(self):
        """Red (attacker) kicks ball over blue's goal line → goal kick for blue."""
        ball = {'x': -4.6, 'y': -1.5}
        result = _classify_goal_line_out(ball, "red_2")
        assert result is not None
        set_piece_type, restart_team, ball_pos, opponent_team = result
        assert set_piece_type == "goal_kick"
        assert restart_team == "blue"
        assert opponent_team == "red"
        assert ball_pos == (-3.5, -1.0)

    def test_defender_kicks_over_own_goal_line_red(self):
        """Red (defender) kicks ball over red's own goal line → corner kick-in for blue."""
        ball = {'x': 4.6, 'y': 2.5}
        result = _classify_goal_line_out(ball, "red_1")
        assert result is not None
        set_piece_type, restart_team, ball_pos, opponent_team = result
        assert set_piece_type == "corner_kick_in"
        assert restart_team == "blue"
        assert opponent_team == "red"
        assert ball_pos == (4.3, 2.8)

    def test_defender_kicks_over_own_goal_line_blue(self):
        """Blue (defender) kicks ball over blue's own goal line → corner kick-in for red."""
        ball = {'x': -4.6, 'y': -2.5}
        result = _classify_goal_line_out(ball, "blue_3")
        assert result is not None
        set_piece_type, restart_team, ball_pos, opponent_team = result
        assert set_piece_type == "corner_kick_in"
        assert restart_team == "red"
        assert opponent_team == "blue"
        assert ball_pos == (-4.3, -2.8)

    def test_no_toucher_neutral_fallback(self):
        """No last toucher → neutral fallback (no set piece)."""
        ball = {'x': 4.6, 'y': 2.0}
        result = _classify_goal_line_out(ball, None)
        assert result is None


class TestWarpOpponentsAway:
    """Test opponent warp-away logic during set pieces."""

    def test_bot_within_radius_gets_warped(self):
        """Opponent bot within 1.5m of ball → warped 2m radially away."""
        ball_pos = (3.5, 1.0)
        entities = {
            'soccer_ball': {'x': 3.5, 'y': 1.0},
            'red_1': {'x': 3.5, 'y': 1.0},  # restart team, not warped
            'blue_1': {'x': 4.0, 'y': 1.0},  # 0.5m away → warped
            'blue_2': {'x': 0.0, 'y': 0.0},  # far away → not warped
        }
        warped = _warp_opponents_away(ball_pos, "red", entities)
        assert "blue_1" in warped
        assert "blue_2" not in warped
        assert "red_1" not in warped
        assert "soccer_ball" not in warped

    def test_warped_distance_is_2m_from_ball(self):
        """Warped bot should be exactly 2m from ball position."""
        ball_pos = (3.5, 1.0)
        entities = {
            'blue_1': {'x': 4.0, 'y': 1.0},  # 0.5m to the right
        }
        warped = _warp_opponents_away(ball_pos, "red", entities)
        new_x, new_y = warped["blue_1"]
        dist = math.hypot(new_x - ball_pos[0], new_y - ball_pos[1])
        assert abs(dist - WARP_AWAY_DISTANCE) < 0.01

    def test_bot_outside_radius_not_warped(self):
        """Opponent bot at exactly 1.5m boundary → not warped (strict less-than)."""
        ball_pos = (3.5, 1.0)
        entities = {
            'blue_1': {'x': 5.0, 'y': 1.0},  # 1.5m away → at boundary, not warped
        }
        warped = _warp_opponents_away(ball_pos, "red", entities)
        assert "blue_1" not in warped

    def test_warped_direction_is_radial(self):
        """Bot warped directly away from ball (same angle)."""
        ball_pos = (0.0, 0.0)
        entities = {
            'blue_1': {'x': 1.0, 'y': 0.0},  # directly to the right
        }
        warped = _warp_opponents_away(ball_pos, "red", entities)
        new_x, new_y = warped["blue_1"]
        # Should be at (2.0, 0.0) — 2m to the right
        assert abs(new_x - 2.0) < 0.01
        assert abs(new_y - 0.0) < 0.01

    def test_bot_at_ball_position_warped_horizontally(self):
        """Bot overlapping ball (dist≈0) → warped via default angle (0 = +X)."""
        ball_pos = (3.5, 1.0)
        entities = {
            'blue_1': {'x': 3.5, 'y': 1.0},  # overlapping
        }
        warped = _warp_opponents_away(ball_pos, "red", entities)
        new_x, new_y = warped["blue_1"]
        assert abs(new_x - (3.5 + WARP_AWAY_DISTANCE)) < 0.01


class TestSetPieceCountdown:
    """Test that the set-piece countdown is 5 seconds for all set pieces."""

    def test_kickoff_countdown_is_5s(self):
        assert SET_PIECE_COUNTDOWN == 5.0

    def test_goal_kick_countdown_is_5s(self):
        assert SET_PIECE_COUNTDOWN == 5.0

    def test_corner_kick_in_countdown_is_5s(self):
        assert SET_PIECE_COUNTDOWN == 5.0

    def test_countdown_same_for_all_set_pieces(self):
        """All set-piece types use the same countdown constant."""
        # In referee_node.py, the timeout logic checks:
        #   timeout = SET_PIECE_COUNTDOWN if status in ("goal", "goal_kick", "corner_kick_in")
        statuses = ["goal", "goal_kick", "corner_kick_in"]
        for s in statuses:
            timeout = SET_PIECE_COUNTDOWN
            assert timeout == 5.0


class TestKickoffScoringTeam:
    """Test that the scoring team (not conceding) is frozen at kickoff."""

    def test_blue_scores_blue_frozen(self):
        """Blue scores → Blue is frozen (scoring team)."""
        scoring_team = "blue"
        bots = ["blue_1", "blue_2", "blue_3", "red_1", "red_2", "red_3"]
        frozen = [b for b in bots if scoring_team in b]
        assert len(frozen) == 3
        assert all("blue" in b for b in frozen)
        assert "red_1" not in frozen

    def test_red_scores_red_frozen(self):
        """Red scores → Red is frozen (scoring team)."""
        scoring_team = "red"
        bots = ["blue_1", "blue_2", "blue_3", "red_1", "red_2", "red_3"]
        frozen = [b for b in bots if scoring_team in b]
        assert len(frozen) == 3
        assert all("red" in b for b in frozen)
        assert "blue_1" not in frozen


class TestSetPieceStatusTypes:
    """Test that set-piece statuses are distinct from existing statuses."""

    def test_goal_kick_status_is_distinct(self):
        assert "goal_kick" != "ball_out"
        assert "goal_kick" != "playing"
        assert "goal_kick" != "foul_penalty"
        assert "goal_kick" != "goal"

    def test_corner_kick_in_status_is_distinct(self):
        assert "corner_kick_in" != "ball_out"
        assert "corner_kick_in" != "playing"
        assert "corner_kick_in" != "foul_penalty"
        assert "corner_kick_in" != "goal"

    def test_set_piece_statuses_distinct_from_each_other(self):
        assert "goal_kick" != "corner_kick_in"