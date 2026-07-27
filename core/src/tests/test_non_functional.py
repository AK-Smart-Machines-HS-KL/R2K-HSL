#!/usr/bin/env python3
"""Non-functional regression suite — real Gazebo matches with KPI assertions.

Slow tests (marked @pytest.mark.slow): each test runs a headless 120s match
via launch_r2k.sh, then asserts KPIs fall within the scenario's kpi_targets.json
ranges. Run with: pytest tests/test_non_functional.py -v -s
Skip slow tests: pytest tests/ --skip-slow

Helpers:
  run_match_headless(scenario, duration) -> kpis dict (world_kpis + llm_kpis merged)
  compute_composite(kpis)                -> float in [0, 1]
  load_kpi_targets(scenario_name)        -> dict from scenario/<name>/kpi_targets.json
  assert_kpi_in_range(name, value, targets) -> None (asserts min <= value <= max)
"""
import glob
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).parent.parent
CORE_DIR = SRC_DIR.parent
SCENARIO_DIR = SRC_DIR / "scenario"
RESULTS_DIR = SRC_DIR / "results"
TEST_DURATION = 120


def run_match_headless(scenario: str, duration: int = TEST_DURATION) -> dict:
    """Run a headless match via launch_r2k.sh and return merged KPI dict."""
    cmd = [
        str(CORE_DIR / "launch_r2k.sh"),
        "--scenario", scenario,
        "--relay", "only_sim_bots",
        "--headless",
        "--duration", str(duration),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True,
                          timeout=duration + 60, cwd=str(CORE_DIR))
    run_id = None
    for line in proc.stdout.splitlines():
        if "Run ID:" in line:
            run_id = line.split("Run ID:")[1].strip().split()[0]
            break
    if not run_id:
        pytest.fail(f"Could not extract R2K_RUN_ID from launch output:\n{proc.stdout[-500:]}")

    out_dir = RESULTS_DIR / f"kpis_{run_id}"
    out_dir.mkdir(parents=True, exist_ok=True)
    analyze_cmd = [
        sys.executable, str(SRC_DIR / "tools" / "analyze_trace.py"),
        "--run-id", run_id, "--output", str(out_dir),
    ]
    subprocess.run(analyze_cmd, check=True, capture_output=True, timeout=30)
    kpi_files = glob.glob(str(out_dir / "*.json"))
    if not kpi_files:
        pytest.fail(f"analyze_trace.py produced no KPI file in {out_dir}")
    with open(kpi_files[0]) as f:
        data = json.load(f)
    return {**data.get("world_kpis", {}), **data.get("llm_kpis", {})}


def compute_composite(kpis: dict) -> float:
    """Composite score formula (spec §5.2).

    composite = 0.4 * goal_diff_norm + 0.3 * tac_score_norm
              + 0.2 * possession_norm + 0.1 * latency_factor
    """
    def clamp(x, lo=0.0, hi=1.0):
        return max(lo, min(hi, x))

    goal_diff_norm = clamp((kpis.get("goals_for_blue", 0) - kpis.get("goals_for_red", 0)) / 10.0)
    tac_score_norm = clamp((kpis.get("tactical_score_avg", -10.0) + 10.0) / 20.0)
    possession_norm = clamp(kpis.get("ball_possession_blue_pct", 0.0) / 100.0)
    latency_factor = clamp(1.0 - kpis.get("latency_p50", 3000) / 3000.0)
    return round(0.4 * goal_diff_norm + 0.3 * tac_score_norm
                 + 0.2 * possession_norm + 0.1 * latency_factor, 3)


def load_kpi_targets(scenario_name: str) -> dict:
    """Load per-scenario kpi_targets.json from scenario/<name>/ package."""
    path = SCENARIO_DIR / scenario_name / "kpi_targets.json"
    if not path.exists():
        pytest.skip(f"No kpi_targets.json for scenario {scenario_name} ({path})")
    with open(path) as f:
        return json.load(f)


def assert_kpi_in_range(name: str, value, targets: dict):
    """Assert value is within [min, max] from kpi_targets.json."""
    if name not in targets:
        pytest.fail(f"KPI '{name}' not in kpi_targets.json")
    t = targets[name]
    lo, hi = t["min"], t["max"]
    assert lo <= value <= hi, f"{name}={value} outside [{lo}, {hi}] ({t.get('note', '')})"


@pytest.mark.slow
def test_attack_center_performance():
    """3vs3_attack_center: composite, OOB, cluster, possession within targets."""
    kpis = run_match_headless("3vs3_attack_center", duration=TEST_DURATION)
    targets = load_kpi_targets("3vs3_attack_center")
    composite = compute_composite(kpis)
    assert_kpi_in_range("composite_score", composite, targets)
    assert_kpi_in_range("oob_pct", kpis["oob_pct"], targets)
    assert_kpi_in_range("cluster_pct", kpis["cluster_pct"], targets)
    assert_kpi_in_range("ball_possession_blue_pct", kpis["ball_possession_blue_pct"], targets)


@pytest.mark.slow
def test_attack_center_goalie():
    """3vs3_attack_center: goalie idle + tactical positioning within targets (Phase 2a)."""
    kpis = run_match_headless("3vs3_attack_center", duration=TEST_DURATION)
    targets = load_kpi_targets("3vs3_attack_center")
    assert_kpi_in_range("goalie_idle_pct", kpis["goalie_idle_pct"], targets)
    assert kpis["goalie_tactical_pct"] >= 60.0, \
        f"goalie_tactical_pct={kpis['goalie_tactical_pct']} below 60%"


@pytest.mark.slow
def test_attack_center_latency():
    """3vs3_attack_center: latency p50 under threshold for qwen2.5-coder:3b on GPU."""
    kpis = run_match_headless("3vs3_attack_center", duration=TEST_DURATION)
    targets = load_kpi_targets("3vs3_attack_center")
    assert_kpi_in_range("latency_p50", kpis["latency_p50"], targets)


@pytest.mark.slow
def test_default_performance():
    """3vs3_default: composite, OOB, cluster, possession within targets (baseline)."""
    kpis = run_match_headless("3vs3_default", duration=TEST_DURATION)
    targets = load_kpi_targets("3vs3_default")
    composite = compute_composite(kpis)
    assert_kpi_in_range("composite_score", composite, targets)
    assert_kpi_in_range("oob_pct", kpis["oob_pct"], targets)
    assert_kpi_in_range("cluster_pct", kpis["cluster_pct"], targets)
    assert_kpi_in_range("ball_possession_blue_pct", kpis["ball_possession_blue_pct"], targets)


@pytest.mark.slow
def test_default_goalie():
    """3vs3_default: goalie idle + tactical positioning within targets (Phase 2a)."""
    kpis = run_match_headless("3vs3_default", duration=TEST_DURATION)
    targets = load_kpi_targets("3vs3_default")
    assert_kpi_in_range("goalie_idle_pct", kpis["goalie_idle_pct"], targets)
    assert kpis["goalie_tactical_pct"] >= 60.0, \
        f"goalie_tactical_pct={kpis['goalie_tactical_pct']} below 60%"


@pytest.mark.slow
def test_high_line_performance():
    """3vs3_high_line: worst composite (0.27) — defensive transition from high line."""
    kpis = run_match_headless("3vs3_high_line", duration=TEST_DURATION)
    targets = load_kpi_targets("3vs3_high_line")
    composite = compute_composite(kpis)
    assert_kpi_in_range("composite_score", composite, targets)
    assert_kpi_in_range("oob_pct", kpis["oob_pct"], targets)
    assert_kpi_in_range("cluster_pct", kpis["cluster_pct"], targets)


@pytest.mark.slow
def test_long_shot_performance():
    """3vs3_long_shot: 2nd worst composite (0.28) — opponent shoots from distance."""
    kpis = run_match_headless("3vs3_long_shot", duration=TEST_DURATION)
    targets = load_kpi_targets("3vs3_long_shot")
    composite = compute_composite(kpis)
    assert_kpi_in_range("composite_score", composite, targets)
    assert_kpi_in_range("oob_pct", kpis["oob_pct"], targets)
    assert_kpi_in_range("cluster_pct", kpis["cluster_pct"], targets)


@pytest.mark.slow
def test_contain_delay_performance():
    """3vs3_contain_delay: 3rd worst composite (0.28) — delay/contain defensive shape."""
    kpis = run_match_headless("3vs3_contain_delay", duration=TEST_DURATION)
    targets = load_kpi_targets("3vs3_contain_delay")
    composite = compute_composite(kpis)
    assert_kpi_in_range("composite_score", composite, targets)
    assert_kpi_in_range("oob_pct", kpis["oob_pct"], targets)
    assert_kpi_in_range("cluster_pct", kpis["cluster_pct"], targets)


@pytest.mark.slow
def test_high_line_goalie():
    """3vs3_high_line: goalie idle + tactical positioning (high line = ball near)."""
    kpis = run_match_headless("3vs3_high_line", duration=TEST_DURATION)
    targets = load_kpi_targets("3vs3_high_line")
    assert_kpi_in_range("goalie_idle_pct", kpis["goalie_idle_pct"], targets)
    assert kpis["goalie_tactical_pct"] >= 60.0, \
        f"goalie_tactical_pct={kpis['goalie_tactical_pct']} below 60%"


@pytest.mark.slow
def test_long_shot_goalie():
    """3vs3_long_shot: goalie idle + tactical positioning (long shot = ball far)."""
    kpis = run_match_headless("3vs3_long_shot", duration=TEST_DURATION)
    targets = load_kpi_targets("3vs3_long_shot")
    assert_kpi_in_range("goalie_idle_pct", kpis["goalie_idle_pct"], targets)
    assert kpis["goalie_tactical_pct"] >= 60.0, \
        f"goalie_tactical_pct={kpis['goalie_tactical_pct']} below 60%"


@pytest.mark.slow
def test_contain_delay_goalie():
    """3vs3_contain_delay: goalie idle + tactical positioning (contain = ball mid)."""
    kpis = run_match_headless("3vs3_contain_delay", duration=TEST_DURATION)
    targets = load_kpi_targets("3vs3_contain_delay")
    assert_kpi_in_range("goalie_idle_pct", kpis["goalie_idle_pct"], targets)
    assert kpis["goalie_tactical_pct"] >= 60.0, \
        f"goalie_tactical_pct={kpis['goalie_tactical_pct']} below 60%"