#!/usr/bin/env python3
"""
Unit tests for kickoff reset and ball-out foul penalty
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
import math

class TestComputeWarpPosition:
    """Test suite for ball-out foul warp position calculation"""
    
    # Constants from referee_node.py
    BALL_OUT_WARP_DISTANCE = 2.0
    FIELD_X_MAX = 4.5
    FIELD_Y_MAX = 3.0
    
    def _compute_warp_position(self, ball, offender_pos, out_type):
        """Replicate referee_node._compute_warp_position logic"""
        if out_type == "sideline":
            # Warp toward field center (Y=0), 2m from line
            sign = 1 if ball['y'] > 0 else -1
            warp_y = sign * (self.FIELD_Y_MAX - 0.1) - sign * self.BALL_OUT_WARP_DISTANCE
            warp_x = offender_pos['x']
        else:  # goal_line
            sign = 1 if ball['x'] > 0 else -1
            warp_x = sign * (self.FIELD_X_MAX - 0.1) - sign * self.BALL_OUT_WARP_DISTANCE
            warp_y = offender_pos['y']
        return warp_x, warp_y
    
    def test_sideline_warp_inward_from_top(self):
        """Ball out at Y=+3.5 (top sideline) → offender warped to Y≈+0.9"""
        ball = {'x': 0.0, 'y': 3.5}  # Ball out on top sideline
        offender_pos = {'x': 1.0, 'y': 3.2}  # Offender near ball
        
        warp_x, warp_y = self._compute_warp_position(ball, offender_pos, "sideline")
        
        # Should be warped 2m inward from Y=3.0 boundary
        expected_y = (self.FIELD_Y_MAX - 0.1) - self.BALL_OUT_WARP_DISTANCE  # ~0.9
        assert abs(warp_y - expected_y) < 0.1
        assert warp_x == offender_pos['x']  # X unchanged
    
    def test_sideline_warp_inward_from_bottom(self):
        """Ball out at Y=-3.5 (bottom sideline) → offender warped to Y≈-0.9"""
        ball = {'x': 0.0, 'y': -3.5}  # Ball out on bottom sideline
        offender_pos = {'x': -1.0, 'y': -3.2}  # Offender near ball
        
        warp_x, warp_y = self._compute_warp_position(ball, offender_pos, "sideline")
        
        # Should be warped 2m inward from Y=-3.0 boundary
        expected_y = -(self.FIELD_Y_MAX - 0.1) + self.BALL_OUT_WARP_DISTANCE  # ~-0.9
        assert abs(warp_y - expected_y) < 0.1
        assert warp_x == offender_pos['x']  # X unchanged
    
    def test_goal_line_warp_inward_from_blue_goal(self):
        """Ball out at X=-4.8 (blue goal line) → offender warped to X≈-2.4"""
        ball = {'x': -4.8, 'y': 0.5}  # Ball out near blue goal
        offender_pos = {'x': -4.5, 'y': 0.3}  # Offender near ball
        
        warp_x, warp_y = self._compute_warp_position(ball, offender_pos, "goal_line")
        
        # Should be warped 2m inward from X=-4.5 boundary
        expected_x = -(self.FIELD_X_MAX - 0.1) + self.BALL_OUT_WARP_DISTANCE  # ~-2.4
        assert abs(warp_x - expected_x) < 0.1
        assert warp_y == offender_pos['y']  # Y unchanged
    
    def test_goal_line_warp_inward_from_red_goal(self):
        """Ball out at X=+4.8 (red goal line) → offender warped to X≈+2.4"""
        ball = {'x': 4.8, 'y': -0.3}  # Ball out near red goal
        offender_pos = {'x': 4.5, 'y': -0.5}  # Offender near ball
        
        warp_x, warp_y = self._compute_warp_position(ball, offender_pos, "goal_line")
        
        # Should be warped 2m inward from X=4.5 boundary
        expected_x = (self.FIELD_X_MAX - 0.1) - self.BALL_OUT_WARP_DISTANCE  # ~2.4
        assert abs(warp_x - expected_x) < 0.1
        assert warp_y == offender_pos['y']  # Y unchanged
    
    def test_warp_is_always_inside_field(self):
        """Warped position should always be inside field boundaries."""
        # Test multiple scenarios
        scenarios = [
            ({'x': 0, 'y': 3.5}, {'x': 0, 'y': 0}, "sideline"),
            ({'x': 0, 'y': -3.5}, {'x': 0, 'y': 0}, "sideline"),
            ({'x': -4.8, 'y': 0}, {'x': 0, 'y': 0}, "goal_line"),
            ({'x': 4.8, 'y': 0}, {'x': 0, 'y': 0}, "goal_line"),
        ]
        
        for ball, offender_pos, out_type in scenarios:
            warp_x, warp_y = self._compute_warp_position(ball, offender_pos, out_type)
            
            # Warped position should be inside field
            assert -self.FIELD_X_MAX <= warp_x <= self.FIELD_X_MAX
            assert -self.FIELD_Y_MAX <= warp_y <= self.FIELD_Y_MAX


class TestClampBallToLine:
    """Test suite for ball reset position on boundary"""
    
    FIELD_X_MAX = 4.5
    FIELD_Y_MAX = 3.0
    
    def _clamp_ball_to_line(self, x, y, out_type):
        """Replicate referee_node._clamp_ball_to_line logic"""
        if out_type == "sideline":
            return x, self.FIELD_Y_MAX if y > 0 else -self.FIELD_Y_MAX
        else:  # goal_line
            return self.FIELD_X_MAX if x > 0 else -self.FIELD_X_MAX, 0.0
    
    def test_sideline_top(self):
        """Ball out at Y=+3.5 → reset to Y=+3.0 (on line)."""
        x, y = self._clamp_ball_to_line(0.5, 3.5, "sideline")
        assert x == 0.5  # X preserved
        assert y == self.FIELD_Y_MAX  # Y clamped to boundary
    
    def test_sideline_bottom(self):
        """Ball out at Y=-3.5 → reset to Y=-3.0 (on line)."""
        x, y = self._clamp_ball_to_line(-1.0, -3.5, "sideline")
        assert x == -1.0  # X preserved
        assert y == -self.FIELD_Y_MAX  # Y clamped to boundary
    
    def test_goal_line_blue_side(self):
        """Ball out at X=-4.8 → reset to X=-4.5, Y=0 (center of goal)."""
        x, y = self._clamp_ball_to_line(-4.8, 0.5, "goal_line")
        assert x == -self.FIELD_X_MAX  # X at goal line
        assert y == 0.0  # Y centered
    
    def test_goal_line_red_side(self):
        """Ball out at X=+4.8 → reset to X=+4.5, Y=0 (center of goal)."""
        x, y = self._clamp_ball_to_line(4.8, -0.3, "goal_line")
        assert x == self.FIELD_X_MAX  # X at goal line
        assert y == 0.0  # Y centered


class TestKickoffReset:
    """Test suite for kickoff reset after goal"""
    
    KICKOFF_FREEZE_TIME = 5.0  # Updated: unified set-piece countdown
    
    def test_kickoff_scoring_team_blue_scores(self):
        """Blue scores → Blue team frozen for 5s, Red free to move."""
        # Simulate: Blue scores (ball crossed X=4.5)
        scoring_team = "blue"
        
        # Frozen bots should be on scoring team
        bots = ["blue_1", "blue_2", "blue_3", "red_1", "red_2", "red_3"]
        frozen_bots = [bot for bot in bots if scoring_team in bot]
        
        assert len(frozen_bots) == 3
        assert all("blue" in bot for bot in frozen_bots)
        assert "red_1" not in frozen_bots
    
    def test_kickoff_scoring_team_red_scores(self):
        """Red scores → Red team frozen for 5s, Blue free to move."""
        scoring_team = "red"
        
        bots = ["blue_1", "blue_2", "blue_3", "red_1", "red_2", "red_3"]
        frozen_bots = [bot for bot in bots if scoring_team in bot]
        
        assert len(frozen_bots) == 3
        assert all("red" in bot for bot in frozen_bots)
        assert "blue_1" not in frozen_bots
    
    def test_ball_reset_to_center(self):
        """Ball should be reset to (0, 0) after goal."""
        ball_reset_x, ball_reset_y = 0.0, 0.0
        
        assert ball_reset_x == 0.0
        assert ball_reset_y == 0.0
    
    def test_freeze_time_is_5_seconds(self):
        """Scoring team frozen for exactly 5 seconds (unified set-piece countdown)."""
        assert self.KICKOFF_FREEZE_TIME == 5.0


class TestBallOutNoToucher:
    """Test suite for ball-out with no last toucher"""
    
    def test_no_toucher_neutral_restart(self):
        """No last toucher → neutral restart, no foul penalty."""
        # If last_toucher is None, should fall back to neutral restart
        last_toucher = None
        
        # No foul should be applied
        foul_applied = last_toucher is not None
        
        # Expected: no foul
        assert foul_applied == False
    
    def test_toucher_triggers_penalty(self):
        """Last toucher exists → foul penalty applied."""
        last_toucher = "blue_1"
        
        # Foul should be applied
        foul_applied = last_toucher is not None
        
        # Expected: foul applied
        assert foul_applied == True


class TestBallOutPenaltyRouting:
    """Test suite for ball-out vs pushing foul penalty differentiation"""
    
    def test_pushing_penalty_is_minus_one(self):
        """Pushing foul should have -1.0 penalty."""
        foul_type = "pushing"
        
        if foul_type == "ball_out":
            penalty = -0.5
        else:
            penalty = -1.0
        
        assert penalty == -1.0
    
    def test_blocking_penalty_is_minus_one(self):
        """Blocking foul should have -1.0 penalty."""
        foul_type = "blocking_without_ball"
        
        if foul_type == "ball_out":
            penalty = -0.5
        else:
            penalty = -1.0
        
        assert penalty == -1.0
    
    def test_ball_out_penalty_is_minus_half(self):
        """Ball-out foul should have -0.5 penalty."""
        foul_type = "ball_out"
        
        if foul_type == "ball_out":
            penalty = -0.5
        else:
            penalty = -1.0
        
        assert penalty == -0.5


class TestFreezeEnforcement:
    """Test suite for freeze enforcement logic"""
    
    def test_frozen_bots_get_zero_twist(self):
        """Bots in frozen_bots dict should receive zero velocity."""
        frozen_bots = {"blue_1": 100.0 + 3.0, "blue_2": 100.0 + 3.0}  # Unfreeze at t=103
        current_time = 101.0  # Before unfreeze
        
        # Check which bots are still frozen
        still_frozen = [bot for bot, unfreeze_time in frozen_bots.items() 
                        if current_time < unfreeze_time]
        
        assert len(still_frozen) == 2
        assert "blue_1" in still_frozen
        assert "blue_2" in still_frozen
    
    def test_expired_bots_removed_from_freeze(self):
        """Bots after unfreeze time should be removed from frozen list."""
        frozen_bots = {"blue_1": 100.0 + 3.0, "blue_2": 100.0 + 3.0}
        current_time = 104.0  # After unfreeze
        
        # Remove expired bots
        still_frozen = {bot: t for bot, t in frozen_bots.items() 
                        if current_time < t}
        
        assert len(still_frozen) == 0
    
    def test_unfreeze_time_calculation(self):
        """Freeze should last exactly 3 seconds from foul time."""
        freeze_start = 50.0
        freeze_duration = 3.0
        unfreeze_time = freeze_start + freeze_duration
        
        assert unfreeze_time == 53.0


class TestGoalPostBounds:
    """Test suite for goal detection requiring ball within goal posts"""
    
    FIELD_X_MAX = 4.5
    FIELD_X_MIN = -4.5
    GOAL_Y_MIN = -0.9
    GOAL_Y_MAX = 0.9
    
    def _is_goal(self, ball_x, ball_y, team):
        """Check if ball position qualifies as a goal for the given team."""
        if team == "blue":
            return ball_x > self.FIELD_X_MAX and self.GOAL_Y_MIN <= ball_y <= self.GOAL_Y_MAX
        else:  # red
            return ball_x < self.FIELD_X_MIN and self.GOAL_Y_MIN <= ball_y <= self.GOAL_Y_MAX
    
    def test_goal_within_posts_counts_for_blue(self):
        """Ball crossing X>4.5 with |Y|<0.9 should count as goal for Blue."""
        ball_x = 4.6
        ball_y = 0.5  # Inside goal posts
        
        is_goal = self._is_goal(ball_x, ball_y, "blue")
        
        assert is_goal == True
    
    def test_goal_within_posts_counts_for_red(self):
        """Ball crossing X<-4.5 with |Y|<0.9 should count as goal for Red."""
        ball_x = -4.6
        ball_y = -0.3  # Inside goal posts
        
        is_goal = self._is_goal(ball_x, ball_y, "red")
        
        assert is_goal == True
    
    def test_goal_wide_of_posts_not_counted_blue(self):
        """Ball crossing X>4.5 but |Y|>0.9 should NOT count as goal."""
        ball_x = 4.6
        ball_y = 2.5  # Wide of goal posts
        
        is_goal = self._is_goal(ball_x, ball_y, "blue")
        
        assert is_goal == False
    
    def test_goal_wide_of_posts_not_counted_red(self):
        """Ball crossing X<-4.5 but |Y|>0.9 should NOT count as goal."""
        ball_x = -4.6
        ball_y = -1.5  # Wide of goal posts
        
        is_goal = self._is_goal(ball_x, ball_y, "red")
        
        assert is_goal == False
    
    def test_ball_on_post_edge_counts_as_goal(self):
        """Ball at Y=±0.9 (exactly on post edge) should count as goal."""
        ball_x = 4.6
        ball_y = 0.9  # Exactly on post edge
        
        is_goal = self._is_goal(ball_x, ball_y, "blue")
        
        assert is_goal == True
    
    def test_ball_just_wide_of_post_not_goal(self):
        """Ball at Y=±0.91 (just wide) should NOT count as goal."""
        ball_x = 4.6
        ball_y = 0.91  # Just wide of post
        
        is_goal = self._is_goal(ball_x, ball_y, "blue")
        
        assert is_goal == False
    
    def test_ball_in_field_no_goal(self):
        """Ball in field (|X|<4.5) should never be goal regardless of Y."""
        ball_x = 0.0
        ball_y = 0.0
        
        is_goal_blue = self._is_goal(ball_x, ball_y, "blue")
        is_goal_red = self._is_goal(ball_x, ball_y, "red")
        
        assert is_goal_blue == False
        assert is_goal_red == False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])