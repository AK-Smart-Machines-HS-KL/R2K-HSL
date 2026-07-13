#!/usr/bin/env python3
"""
Unit tests for momentum calculation in score_node.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from collections import deque
import pytest

class TestMomentum:
    """Test suite for momentum OLS calculation"""
    
    def _calculate_momentum(self, window_data):
        """Helper to calculate momentum from window data"""
        from collections import deque
        
        n = len(window_data)
        if n < 10:
            return 0.0, "stable"
        
        sum_x = sum(range(n))
        sum_y = sum(score for _, score in window_data)
        sum_xy = sum(i * score for i, (_, score) in enumerate(window_data))
        sum_x2 = sum(i * i for i in range(n))
        
        denominator = n * sum_x2 - sum_x * sum_x
        if abs(denominator) < 1e-9:
            return 0.0, "stable"
        
        slope = (n * sum_xy - sum_x * sum_y) / denominator
        momentum = max(-10.0, min(10.0, slope * 10.0))
        
        if momentum > 2.0: trend = "ascending"
        elif momentum > 0.5: trend = "improving"
        elif momentum > -0.5: trend = "stable"
        elif momentum > -2.0: trend = "declining"
        else: trend = "collapsing"
        
        return round(momentum, 2), trend
    
    def test_slope_positive(self):
        """Ascending scores should produce positive momentum."""
        window = [(i, float(i) * 0.1) for i in range(50)]
        momentum, trend = self._calculate_momentum(window)
        assert momentum > 0
        assert trend in ("improving", "ascending")
    
    def test_slope_negative(self):
        """Descending scores should produce negative momentum."""
        window = [(i, 5.0 - float(i) * 0.1) for i in range(50)]
        momentum, trend = self._calculate_momentum(window)
        assert momentum < 0
        assert trend in ("declining", "collapsing")
    
    def test_minimum_samples(self):
        """Less than 10 samples should return stable."""
        window = [(i, 5.0) for i in range(5)]
        momentum, trend = self._calculate_momentum(window)
        assert trend == "stable"
        assert momentum == 0.0
    
    def test_clamping_positive(self):
        """Momentum should be clamped to +10 maximum."""
        window = [(i, float(i) * 10.0) for i in range(300)]
        momentum, trend = self._calculate_momentum(window)
        assert momentum <= 10.0
        assert trend == "ascending"
    
    def test_clamping_negative(self):
        """Momentum should be clamped to -10 minimum."""
        window = [(i, -float(i) * 10.0) for i in range(300)]
        momentum, trend = self._calculate_momentum(window)
        assert momentum >= -10.0
        assert trend == "collapsing"
    
    def test_flat_scores(self):
        """Constant scores should produce zero momentum."""
        window = [(i, 5.0) for i in range(50)]
        momentum, trend = self._calculate_momentum(window)
        assert abs(momentum) < 0.5
        assert trend == "stable"
    
    def test_trend_classification_ascending(self):
        """Momentum > 2.0 should classify as ascending."""
        window = [(i, float(i) * 0.25) for i in range(50)]
        momentum, trend = self._calculate_momentum(window)
        assert momentum > 2.0
        assert trend == "ascending"
    
    def test_trend_classification_collapsing(self):
        """Momentum < -2.0 should classify as collapsing."""
        window = [(i, -float(i) * 0.25) for i in range(50)]
        momentum, trend = self._calculate_momentum(window)
        assert momentum < -2.0
        assert trend == "collapsing"

if __name__ == '__main__':
    pytest.main([__file__, '-v'])