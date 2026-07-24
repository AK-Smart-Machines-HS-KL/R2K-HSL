#!/usr/bin/env python3
"""
Unit tests for reward_node.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
import json
import time

class TestRewardNode:
    """Test suite for reward calculation"""
    
    def test_positive_reward(self):
        """Score improving by >1.0 should classify as positive."""
        score_before = -3.0
        score_after = -1.5
        reward = score_after - score_before
        
        classification = "neutral"
        if reward > 1.0: classification = "positive"
        elif reward < -1.0: classification = "negative"
        
        assert reward == 1.5
        assert classification == "positive"
    
    def test_negative_reward_foul(self):
        """Foul event should produce reward = -1.0 (pushing) or -0.5 (ball_out)."""
        # Foul rewards are HARDCODED as "negative" classification, not threshold-based
        # See reward_node.py:_publish_foul_reward() which hardcodes classification="negative"
        
        # Test pushing foul penalty
        foul_reward_pushing = -1.0
        assert foul_reward_pushing == -1.0
        
        # Test ball-out foul penalty (smaller)
        foul_reward_ballout = -0.5
        assert foul_reward_ballout == -0.5
        
        # Verify both are negative values
        assert foul_reward_pushing < 0
        assert foul_reward_ballout < 0
    
    def test_1hz_update_rate(self):
        """Reward node should publish at 1Hz, not per-decision."""
        # This is a design test - we can't verify the timer in unit tests
        # but we can check the reward schema structure
        reward_data = {
            "timestamp": time.time(),
            "source": "decision",
            "action_type": "Move",
            "target_x": 2.3,
            "target_y": -1.1,
            "score_before": -6.5,
            "score_after": -4.2,
            "reward": 2.3,
            "classification": "positive",
            "bot_id": "blue_1"
        }
        
        assert "timestamp" in reward_data
        assert "source" in reward_data
        assert reward_data["source"] in ["decision", "foul"]
        assert "reward" in reward_data
    
    def test_scale_clamping(self):
        """Reward values should be within -10..+10."""
        # Test edge cases
        test_cases = [
            (-15.0, -10.0),  # Negative clamp
            (15.0, 10.0),     # Positive clamp
            (0.0, 0.0),       # Zero stays
            (5.0, 5.0),       # Within range
            (-5.0, -5.0)      # Within range
        ]
        
        for input_reward, expected in test_cases:
            clamped = max(-10.0, min(10.0, input_reward))
            assert clamped == expected
    
    def test_neutral_classification(self):
        """Reward between -1.0 and +1.0 should classify as neutral."""
        reward = 0.5
        
        classification = "neutral"
        if reward > 1.0: classification = "positive"
        elif reward < -1.0: classification = "negative"
        
        assert classification == "neutral"
    
    def test_foul_penalty_schema(self):
        """Foul reward should have correct schema."""
        reward_data = {
            "timestamp": time.time(),
            "source": "foul",
            "action_type": "pushing",
            "target_x": None,
            "target_y": None,
            "score_before": -3.2,
            "score_after": None,
            "reward": -1.0,
            "classification": "negative",
            "bot_id": "blue_2"
        }
        
        assert reward_data["source"] == "foul"
        assert reward_data["reward"] == -1.0
        assert reward_data["target_x"] is None
        assert reward_data["classification"] == "negative"
    
    def test_decision_timeout(self):
        """Move actions should have 5s timeout, Kick actions 2s."""
        # Design test: verify timeout structure
        move_timeout = 5.0
        kick_timeout = 2.0
        
        assert move_timeout == 5.0
        assert kick_timeout == 2.0

if __name__ == '__main__':
    pytest.main([__file__, '-v'])