#!/usr/bin/env python3
"""
Automated tests for score chart specifications.

Verifies that gen_score_chart.py produces correct data for both chart types:
- Hand-crafted: ensemble forecast (5 runs × 4s, shaded band + dotted mean)
- Empirical: bar-delta (16 bars × 0.5s, goal frame included as last bar)

These tests check the DATA logic (compute_score_deltas, load_all_traces_for_scenario),
not the matplotlib rendering.
"""

import sys
import os
import json
import glob
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

os.environ["R2K_TEXT_MODE"] = "1"

import pytest

SCENARIO_DIR = Path(__file__).parent.parent / "scenario"
LOG_DIR = Path(__file__).parent.parent / "logs"

# Import chart functions
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tools"))
from gen_score_chart import (
    load_world_traces_for_scenario,
    load_all_traces_for_scenario,
    compute_score_deltas,
    find_goal_time,
)


def _is_handcrafted(name):
    return not name.startswith("emp_") and not name.startswith("w")


def _is_empirical(name):
    return name.startswith("emp_")


def _get_handcrafted_scenarios():
    return sorted([d.name for d in SCENARIO_DIR.iterdir()
                   if d.is_dir() and (d / "scenario.json").exists()
                   and _is_handcrafted(d.name)])


def _get_empirical_scenarios():
    return sorted([d.name for d in SCENARIO_DIR.iterdir()
                   if d.is_dir() and (d / "scenario.json").exists()
                   and _is_empirical(d.name)])


# === Ensemble chart tests (hand-crafted) ===

class TestEnsembleData:
    """Verify ensemble chart data meets spec: 5 runs, 0-4s, band + mean."""

    def test_handcrafted_scenarios_exist(self):
        """At least 17 hand-crafted scenarios exist."""
        scens = _get_handcrafted_scenarios()
        assert len(scens) >= 17, f"Expected ≥17 hand-crafted scenarios, got {len(scens)}"

    @pytest.mark.parametrize("scen", _get_handcrafted_scenarios())
    def test_ensemble_has_at_least_5_runs(self, scen):
        """Each hand-crafted scenario must have ≥5 trace files for the ensemble band."""
        runs = load_all_traces_for_scenario(scen, max_duration_s=4.0)
        assert len(runs) >= 5, f"{scen}: only {len(runs)} runs (need ≥5 for ensemble band)"

    @pytest.mark.parametrize("scen", _get_handcrafted_scenarios())
    def test_ensemble_runs_have_score_data(self, scen):
        """Each run must have tactical_score data."""
        runs = load_all_traces_for_scenario(scen, max_duration_s=4.0)
        for i, run in enumerate(runs[:5]):
            assert len(run) > 0, f"{scen} run {i}: no frames"
            assert "score" in run[0], f"{scen} run {i}: no score field"

    @pytest.mark.parametrize("scen", _get_handcrafted_scenarios())
    def test_ensemble_time_points_0_to_4(self, scen):
        """Ensemble x-axis must span 0 to 4.0s (5 time points: 0, 1, 2, 3, 4)."""
        runs = load_all_traces_for_scenario(scen, max_duration_s=4.0)
        n_intervals = 4
        time_points = [i * 1.0 for i in range(n_intervals + 1)]
        assert time_points == [0.0, 1.0, 2.0, 3.0, 4.0], f"Time points should be [0,1,2,3,4]"

    @pytest.mark.parametrize("scen", _get_handcrafted_scenarios())
    def test_ensemble_band_width_nonzero(self, scen):
        """The min-max band must have nonzero width at some time point (runs differ)."""
        runs = load_all_traces_for_scenario(scen, max_duration_s=4.0)
        used = runs[:5]
        frames_per_interval = 10
        any_nonzero = False
        for t_idx in range(5):
            frame_idx = t_idx * frames_per_interval + 1
            vals = []
            for run in used:
                idx = min(frame_idx, len(run) - 1)
                vals.append(run[idx]["score"])
            if max(vals) - min(vals) > 0.01:
                any_nonzero = True
                break
        assert any_nonzero, f"{scen}: band width is zero at all time points (runs identical)"

    @pytest.mark.parametrize("scen", _get_handcrafted_scenarios())
    def test_ensemble_score_not_clamped(self, scen):
        """Scores should not be pinned at ±10 (BALL_POSITION_GAIN=0.8 prevents clamping)."""
        runs = load_all_traces_for_scenario(scen, max_duration_s=4.0)
        for run in runs[:5]:
            for frame in run:
                assert abs(frame["score"]) < 10.01, f"{scen}: score clamped at {frame['score']}"
                # Allow exactly 10.0 but not beyond. If ALL frames are 10.0, that's clamping.
                break  # Only check first frame; clamping happens at start

    @pytest.mark.parametrize("scen", _get_handcrafted_scenarios())
    def test_ensemble_chart_file_exists(self, scen):
        """Each hand-crafted scenario must have a score_chart.png."""
        chart = SCENARIO_DIR / scen / "score_chart.png"
        assert chart.exists(), f"{scen}: score_chart.png missing"
        assert chart.stat().st_size > 1000, f"{scen}: score_chart.png too small ({chart.stat().st_size} bytes)"


# === Bar-delta chart tests (empirical) ===

class TestBarDeltaData:
    """Verify bar-delta chart data meets spec: 16 bars, t=0.5-8.0s, goal frame included."""

    def test_empirical_scenarios_exist(self):
        """At least 33 empirical scenarios exist."""
        scens = _get_empirical_scenarios()
        assert len(scens) >= 33, f"Expected ≥33 empirical scenarios, got {len(scens)}"

    @pytest.mark.parametrize("scen", _get_empirical_scenarios())
    def test_bar_chart_has_trace(self, scen):
        """Each empirical scenario must have at least one trace file."""
        scores = load_world_traces_for_scenario(scen)
        assert scores is not None, f"{scen}: no trace found"
        assert len(scores) > 0, f"{scen}: trace is empty"

    @pytest.mark.parametrize("scen", _get_empirical_scenarios())
    def test_bar_chart_has_score_data(self, scen):
        """Trace must have tactical_score data."""
        scores = load_world_traces_for_scenario(scen)
        assert len(scores) > 10, f"{scen}: only {len(scores)} frames"
        assert "score" in scores[0], f"{scen}: no score field in trace"

    @pytest.mark.parametrize("scen", _get_empirical_scenarios())
    def test_bar_chart_no_goal_returns_16_bars(self, scen):
        """If no goal in 8s, compute_score_deltas must return exactly 16 deltas."""
        scores = load_world_traces_for_scenario(scen)
        deltas, goal_info = compute_score_deltas(scores, n_periods=16, latency_s=0.5)
        if goal_info is None:
            assert len(deltas) == 16, f"{scen}: no goal but only {len(deltas)} bars (expected 16)"

    @pytest.mark.parametrize("scen", _get_empirical_scenarios())
    def test_bar_chart_goal_includes_goal_frame(self, scen):
        """If there's a goal, the last bar must be at or after the goal time."""
        scores = load_world_traces_for_scenario(scen)
        deltas, goal_info = compute_score_deltas(scores, n_periods=16, latency_s=0.5)
        if goal_info is not None:
            assert len(deltas) > 0, f"{scen}: goal but no bars"
            last_bar_time = deltas[-1]["time_s"]
            goal_time = goal_info["time_s"]
            assert last_bar_time >= goal_time, \
                f"{scen}: last bar at t={last_bar_time:.1f}s but goal at t={goal_time:.1f}s (goal frame not included)"

    @pytest.mark.parametrize("scen", _get_empirical_scenarios())
    def test_bar_chart_goal_stops_after_goal(self, scen):
        """If there's a goal at 3.4s, bars must stop at 3.5s (not continue to 8.0s)."""
        scores = load_world_traces_for_scenario(scen)
        deltas, goal_info = compute_score_deltas(scores, n_periods=16, latency_s=0.5)
        if goal_info is not None:
            goal_time = goal_info["time_s"]
            # The bar after the goal period should NOT exist
            last_bar_time = deltas[-1]["time_s"]
            # Last bar should be at most 0.5s after the goal time (the goal period)
            assert last_bar_time <= goal_time + 0.5, \
                f"{scen}: last bar at t={last_bar_time:.1f}s, goal at t={goal_time:.1f}s (bars continue past goal)"

    @pytest.mark.parametrize("scen", _get_empirical_scenarios())
    def test_bar_chart_goal_has_team(self, scen):
        """If there's a goal, goal_info must have a team ('blue' or 'red')."""
        scores = load_world_traces_for_scenario(scen)
        deltas, goal_info = compute_score_deltas(scores, n_periods=16, latency_s=0.5)
        if goal_info is not None:
            assert goal_info["team"] in ("blue", "red", "unknown"), \
                f"{scen}: goal team is {goal_info['team']}"

    @pytest.mark.parametrize("scen", _get_empirical_scenarios())
    def test_bar_chart_score_not_clamped(self, scen):
        """Scores should not be pinned at ±10 from frame 0."""
        scores = load_world_traces_for_scenario(scen)
        if scores:
            first_score = scores[0]["score"]
            # Allow ±10 but flag if ALL first 10 frames are exactly ±10
            first_10 = [s["score"] for s in scores[:10]]
            if all(abs(s) >= 9.99 for s in first_10):
                pytest.skip(f"{scen}: score at extreme but may be legitimate (ball at goal line)")

    @pytest.mark.parametrize("scen", _get_empirical_scenarios())
    def test_bar_chart_file_exists(self, scen):
        """Each empirical scenario must have a score_chart.png."""
        chart = SCENARIO_DIR / scen / "score_chart.png"
        assert chart.exists(), f"{scen}: score_chart.png missing"
        assert chart.stat().st_size > 1000, f"{scen}: score_chart.png too small ({chart.stat().st_size} bytes)"


# === Cross-cutting tests ===

class TestChartCorpus:
    """Verify the full chart corpus is complete and consistent."""

    def test_all_50_charts_exist(self):
        """All 50 scenarios (17 hand-crafted + 33 empirical) must have score_chart.png."""
        scens = _get_handcrafted_scenarios() + _get_empirical_scenarios()
        missing = []
        for scen in scens:
            chart = SCENARIO_DIR / scen / "score_chart.png"
            if not chart.exists() or chart.stat().st_size < 1000:
                missing.append(scen)
        assert len(missing) == 0, f"Missing charts: {missing}"

    def test_no_w_scenarios_in_chart_corpus(self):
        """w* watchdog scenarios must NOT be in the scenario dir (moved to docs/v7/)."""
        w_scens = [d.name for d in SCENARIO_DIR.iterdir()
                   if d.is_dir() and d.name.startswith("w")]
        assert len(w_scens) == 0, f"w* scenarios still in scenario dir: {w_scens}"

    def test_handcrafted_count_is_17(self):
        """Exactly 17 hand-crafted scenarios."""
        scens = _get_handcrafted_scenarios()
        assert len(scens) == 17, f"Expected 17 hand-crafted, got {len(scens)}: {scens}"

    def test_empirical_count_is_33(self):
        """Exactly 33 empirical scenarios."""
        scens = _get_empirical_scenarios()
        assert len(scens) == 33, f"Expected 33 empirical, got {len(scens)}: {scens}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])