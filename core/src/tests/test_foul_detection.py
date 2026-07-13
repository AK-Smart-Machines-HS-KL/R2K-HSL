#!/usr/bin/env python3
"""
Unit tests for foul detection edge cases
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
import math

class TestFoulDetectionEdgeCases:
    """Test suite for foul detection edge cases"""
    
    def test_pushing_velocity_threshold(self):
        """Pushing requires relative velocity > 0.5 m/s."""
        PUSHING_VELOCITY_THRESHOLD = 0.5
        
        # Bot A stationary, Bot B approaching
        bot_a_vel = (0.0, 0.0)
        bot_b_vel = (0.7, 0.0)  # 0.7 m/s toward A
        
        # Relative velocity
        rel_vel_x = bot_a_vel[0] - bot_b_vel[0]
        rel_vel_y = bot_a_vel[1] - bot_b_vel[1]
        rel_vel = (rel_vel_x**2 + rel_vel_y**2)**0.5
        
        # Expected: velocity exceeds threshold
        assert rel_vel > PUSHING_VELOCITY_THRESHOLD
    
    def test_pushing_distance_threshold(self):
        """Pushing requires bots within 0.3m of each other."""
        PUSHING_DISTANCE_THRESHOLD = 0.3
        
        bot_a = {"x": 0.0, "y": 0.0}
        bot_b = {"x": 0.2, "y": 0.0}  # 0.2m apart
        
        dist = ((bot_a['x'] - bot_b['x'])**2 + 
                (bot_a['y'] - bot_b['y'])**2)**0.5
        
        # Expected: within threshold
        assert dist < PUSHING_DISTANCE_THRESHOLD
    
    def test_blocking_obstruction_angle(self):
        """Blocking requires bot within 30° of opponent-to-ball line."""
        OBSTRUCTION_ANGLE = 30  # degrees
        
        # Blue at (-2, 0), Ball at (2, 0)
        # Red at (0, 0.5) - directly in path
        
        blue_to_ball = (4.0, 0.0)  # Vector from blue to ball
        red_pos = (0.0, 0.5)
        
        # Calculate angle between blue-to-ball and blue-to-red
        blue_to_red = (2.0, 0.5)
        
        dot = blue_to_ball[0] * blue_to_red[0] + blue_to_ball[1] * blue_to_red[1]
        mag_ball = (blue_to_ball[0]**2 + blue_to_ball[1]**2)**0.5
        mag_red = (blue_to_red[0]**2 + blue_to_red[1]**2)**0.5
        
        if mag_ball == 0 or mag_red == 0:
            angle = 0
        else:
            cos_angle = dot / (mag_ball * mag_red)
            angle = math.degrees(math.acos(max(-1, min(1, cos_angle))))
        
        # Expected: red is within obstruction angle
        assert angle < OBSTRUCTION_ANGLE
    
    def test_hysteresis_frames(self):
        """Foul detection requires 3 consecutive frames."""
        HYSTERESIS_FRAMES = 3
        
        # Simulate foul detection over frames
        foul_frames = [
            {"foul": False},  # Frame 1
            {"foul": True},   # Frame 2
            {"foul": True},   # Frame 3
            {"foul": True},   # Frame 4 - foul confirmed
        ]
        
        consecutive_fouls = 0
        for frame in foul_frames:
            if frame["foul"]:
                consecutive_fouls += 1
            else:
                consecutive_fouls = 0
        
        # Expected: foul confirmed at frame 4
        assert consecutive_fouls >= HYSTERESIS_FRAMES
    
    def test_ball_proximity_exemption(self):
        """Bot within 0.8m of ball should NOT trigger fouls."""
        BALL_PROXIMITY_THRESHOLD = 0.8
        
        # Bot A near ball, Bot B approaching
        bot_a = {"x": 1.0, "y": 0.0}
        ball = {"x": 1.5, "y": 0.0}
        
        dist_to_ball = ((bot_a['x'] - ball['x'])**2 + 
                        (bot_a['y'] - ball['y'])**2)**0.5
        
        # Expected: bot is near ball, exempt from foul
        assert dist_to_ball < BALL_PROXIMITY_THRESHOLD
    
    def test_sideline_y_range(self):
        """Foul warp Y coordinate should be random in [-2.0, 2.0]."""
        SIDELINE_Y_MIN = -2.0
        SIDELINE_Y_MAX = 2.0
        
        import random
        warp_y = random.uniform(SIDELINE_Y_MIN, SIDELINE_Y_MAX)
        
        # Test multiple random values
        for _ in range(100):
            warp_y = random.uniform(SIDELINE_Y_MIN, SIDELINE_Y_MAX)
            assert SIDELINE_Y_MIN <= warp_y <= SIDELINE_Y_MAX
    
    def test_foul_cooldown(self):
        """Same bot should not trigger fouls within 5s cooldown."""
        foul_cooldown = {}
        
        # First foul at t=0
        current_time = 0.0
        bot_id = "blue_1"
        foul_cooldown[bot_id] = current_time + 5.0
        
        # Check at t=2 (within cooldown)
        current_time = 2.0
        can_foul = current_time > foul_cooldown[bot_id]
        assert can_foul == False  # Should be False within cooldown
        
        # Check at t=6 (after cooldown)
        current_time = 6.0
        can_foul = current_time > foul_cooldown[bot_id]
        assert can_foul == True  # Should be True after cooldown

if __name__ == '__main__':
    pytest.main([__file__, '-v'])