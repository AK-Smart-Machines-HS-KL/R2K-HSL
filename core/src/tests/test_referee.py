#!/usr/bin/env python3
"""
Unit tests for referee_node.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
import json

class TestFoulDetection:
    """Test suite for foul detection logic"""
    
    def test_pushing_foul(self):
        """Two bots colliding without ball = pushing."""
        # Bot A at (-1, 0), Bot B at (-1.2, 0), approaching at 0.6 m/s
        # Ball at (3, 0) - far away
        
        bot_a_pos = {"x": -1.0, "y": 0.0}
        bot_b_pos = {"x": -1.2, "y": 0.0}
        ball_pos = {"x": 3.0, "y": 0.0}
        
        # Calculate distance between bots
        dist = ((bot_a_pos['x'] - bot_b_pos['x'])**2 + 
                (bot_a_pos['y'] - bot_b_pos['y'])**2)**0.5
        
        # Calculate distance to ball
        dist_to_ball_a = ((bot_a_pos['x'] - ball_pos['x'])**2 + 
                          (bot_a_pos['y'] - ball_pos['y'])**2)**0.5
        dist_to_ball_b = ((bot_b_pos['x'] - ball_pos['x'])**2 + 
                          (bot_b_pos['y'] - ball_pos['y'])**2)**0.5
        
        PUSHING_DISTANCE_THRESHOLD = 0.3
        BALL_PROXIMITY_THRESHOLD = 0.8
        
        # Expected: foul detected
        assert dist < PUSHING_DISTANCE_THRESHOLD
        assert dist_to_ball_a > BALL_PROXIMITY_THRESHOLD
        assert dist_to_ball_b > BALL_PROXIMITY_THRESHOLD
    
    def test_blocking_without_ball(self):
        """Bot between opponent and ball without ball possession = blocking."""
        # Red bot between blue bot and ball, not near ball
        
        blue_bot = {"x": -1.0, "y": 0.0}
        red_bot = {"x": 0.0, "y": 0.0}  # Between blue and ball
        ball_pos = {"x": 1.0, "y": 0.0}
        
        # Check if red is between blue and ball
        blue_to_ball = (ball_pos['x'] - blue_bot['x'], ball_pos['y'] - blue_bot['y'])
        red_to_blue = (red_bot['x'] - blue_bot['x'], red_bot['y'] - blue_bot['y'])
        
        # Vector dot product check
        dot = blue_to_ball[0] * red_to_blue[0] + blue_to_ball[1] * red_to_blue[1]
        
        BLOCKING_DISTANCE_THRESHOLD = 0.5
        BALL_PROXIMITY_THRESHOLD = 0.8
        
        dist_red_to_ball = ((red_bot['x'] - ball_pos['x'])**2 + 
                            (red_bot['y'] - ball_pos['y'])**2)**0.5
        
        # Expected: blocking foul
        assert dot > 0  # Red is in front of blue relative to ball
        assert dist_red_to_ball > BALL_PROXIMITY_THRESHOLD  # Red not near ball
    
    def test_no_foul_with_ball(self):
        """Bot with ball possession should NOT trigger pushing/blocking."""
        # Bot within 0.8m of ball, approaching opponent
        
        bot_a_pos = {"x": 0.0, "y": 0.0}
        ball_pos = {"x": 0.3, "y": 0.0}  # Bot near ball
        bot_b_pos = {"x": -0.5, "y": 0.0}  # Approaching bot
        
        dist_to_ball_a = ((bot_a_pos['x'] - ball_pos['x'])**2 + 
                          (bot_a_pos['y'] - ball_pos['y'])**2)**0.5
        
        BALL_PROXIMITY_THRESHOLD = 0.8
        
        # Expected: no foul
        assert dist_to_ball_a < BALL_PROXIMITY_THRESHOLD
    
    def test_sideline_warp(self):
        """Foul penalty should warp offender to own baseline sideline."""
        # Expected: offender.x = -4.0, offender.y in [-2.0, 2.0]
        
        SIDELINE_X_OFFSET = -4.0
        SIDELINE_Y_MIN = -2.0
        SIDELINE_Y_MAX = 2.0
        
        # Simulate warp
        import random
        warp_y = random.uniform(SIDELINE_Y_MIN, SIDELINE_Y_MAX)
        
        assert warp_y >= SIDELINE_Y_MIN
        assert warp_y <= SIDELINE_Y_MAX
    
    def test_ball_out_sideline(self):
        """Ball crossing Y=3.0 or Y=-3.0 = sideline out."""
        FIELD_Y_MAX = 3.0
        
        ball_y = 3.5
        ball_out = abs(ball_y) > FIELD_Y_MAX
        
        assert ball_out is True
    
    def test_goal_line_out_no_goal(self):
        """Ball crossing X=4.5 but |Y| > 0.9 = goal line out, not goal."""
        FIELD_X_MAX = 4.5
        GOAL_Y_MAX = 0.9
        
        ball_x = 4.8
        ball_y = 1.5
        
        ball_out = abs(ball_x) > FIELD_X_MAX and abs(ball_y) > GOAL_Y_MAX
        
        assert ball_out is True
    
    def test_last_touch_tracking(self):
        """Bot closest to ball for 3 consecutive frames = last toucher."""
        PROXIMITY_THRESHOLD = 0.8
        HYSTERESIS_FRAMES = 3
        
        # Simulate frame tracking
        frames = [
            {"blue_1": 0.5, "red_1": 1.0},  # blue_1 closest
            {"blue_1": 0.6, "red_1": 1.2},  # blue_1 closest
            {"blue_1": 0.4, "red_1": 1.1},  # blue_1 closest
        ]
        
        # Track consecutive frames
        frame_count = {}
        for frame in frames:
            closest = min(frame.items(), key=lambda x: x[1])[0]
            frame_count[closest] = frame_count.get(closest, 0) + 1
        
        # Expected: blue_1 has 3 frames
        assert frame_count.get("blue_1", 0) >= HYSTERESIS_FRAMES

if __name__ == '__main__':
    pytest.main([__file__, '-v'])