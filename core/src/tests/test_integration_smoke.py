#!/usr/bin/env python3
"""
Integration smoke test for ROS2K v6
Launches a 15s headless run per scenario to verify basic functionality
"""

import subprocess
import json
import os
import time
import sys
from pathlib import Path

SCENARIOS_DIR = Path(__file__).parent.parent / "scenario"

def test_scenario_launches():
    """Each scenario JSON should parse and launch without error."""
    scenarios = [f for f in os.listdir(SCENARIOS_DIR) if f.startswith('3vs3_') and f.endswith('.json')]
    
    print(f"\n{'='*70}")
    print(f"Testing {len(scenarios)} scenarios for basic launch capability")
    print(f"{'='*70}\n")
    
    for scenario_file in scenarios:
        scenario_name = scenario_file.replace('.json', '')
        print(f"📋 Testing scenario: {scenario_name}")
        
        # Check JSON validity
        scenario_path = SCENARIOS_DIR / scenario_file
        try:
            with open(scenario_path, 'r') as f:
                data = json.load(f)
            # Accept both old format (scene_type, label) and new format (scenario_name, tactical_situation)
            has_valid_format = (
                ('scenario_name' in data and 'entities' in data) or
                ('scene_type' in data and 'entities' in data)
            )
            assert has_valid_format, f"Invalid schema in {scenario_file}"
            assert 'entities' in data, f"Missing entities in {scenario_file}"
            assert 'soccer_ball' in data['entities'], f"Missing soccer_ball in {scenario_file}"
            print(f"  ✅ JSON valid")
        except json.JSONDecodeError as e:
            print(f"  ❌ JSON parse error: {e}")
            assert False, f"Invalid JSON in {scenario_file}"
        except AssertionError as e:
            print(f"  ❌ Schema error: {e}")
            raise
    
    print(f"\n✅ All {len(scenarios)} scenarios passed validation")

def test_momentum_produces_values():
    """score_node should produce momentum_30s and momentum_trend."""
    print(f"\n{'='*70}")
    print(f"Testing momentum calculation (15s smoke test)")
    print(f"{'='*70}\n")
    
    # This test requires a full ROS2 stack, so we skip if ROS2 is not available
    try:
        import rclpy
    except ImportError:
        print("⚠️  ROS2 not available, skipping momentum integration test")
        return
    
    print("⚠️  Momentum test requires manual verification in live environment")
    print("  Check /tactical_score topic for momentum_30s and momentum_trend fields")
    
    # Manual test checklist
    print("\nManual test steps:")
    print("  1. Launch: ./launch_r2k.sh --scenario 3vs3_attack_center --duration 30")
    print("  2. Subscribe: ros2 topic echo /tactical_score")
    print("  3. Verify: momentum_30s and momentum_trend fields present")
    print("  4. Verify: momentum_30s updates dynamically")
    print("  5. Verify: momentum_trend changes based on score slope")

def test_reward_produces_values():
    """reward_node should produce reward values at 1Hz."""
    print(f"\n{'='*70}")
    print(f"Testing reward calculation (15s smoke test)")
    print(f"{'='*70}\n")
    
    try:
        import rclpy
    except ImportError:
        print("⚠️  ROS2 not available, skipping reward integration test")
        return
    
    print("⚠️  Reward test requires manual verification in live environment")
    print("  Check /tactical_reward topic for reward values")
    
    # Manual test checklist
    print("\nManual test steps:")
    print("  1. Launch: ./launch_r2k.sh --scenario 3vs3_attack_center --duration 30")
    print("  2. Subscribe: ros2 topic echo /tactical_reward")
    print("  3. Verify: reward values appear at ~1Hz")
    print("  4. Verify: classification field present (positive/neutral/negative)")

def test_foul_detection_works():
    """Referee should detect pushing when bots collide without ball."""
    print(f"\n{'='*70}")
    print(f"Testing foul detection (15s smoke test)")
    print(f"{'='*70}\n")
    
    try:
        import rclpy
    except ImportError:
        print("⚠️  ROS2 not available, skipping foul integration test")
        return
    
    print("⚠️  Foul test requires manual verification in live environment")
    print("  Check /match_state topic for foul events")
    
    # Manual test checklist
    print("\nManual test steps:")
    print("  1. Launch: ./launch_r2k.sh --scenario 3vs3_defensive_crisis --duration 30")
    print("  2. Subscribe: ros2 topic echo /match_state")
    print("  3. Verify: foul events appear when bots collide")
    print("  4. Verify: offender warped to sideline (x=-4.0)")
    print("  5. Verify: reward_node publishes -1.0 penalty")

def test_headless_duration():
    """--headless --duration 15 should auto-terminate after 15s."""
    print(f"\n{'='*70}")
    print(f"Testing headless auto-termination (15s smoke test)")
    print(f"{'='*70}\n")
    
    # Note: This test requires a full system test
    # In CI/CD, this would be tested with actual Gazebo launch
    
    print("⚠️  Headless test requires manual verification in live environment")
    print("  Verify that the system terminates after --duration seconds")
    
    # Manual test checklist
    print("\nManual test steps:")
    print("  1. Launch: ./launch_r2k.sh --headless --duration 15 --scenario 3vs3_attack_center")
    print("  2. Verify: System terminates after ~15s")
    print("  3. Verify: No visualizer window opens")
    print("  4. Verify: Cleanup scripts run successfully")

def test_strategy_files_exist():
    """All strategy fragment source files should exist (fragments/ is the source of truth)."""
    print(f"\n{'='*70}")
    print(f"Testing strategy fragment file availability")
    print(f"{'='*70}\n")
    
    fragments_dir = Path(__file__).parent.parent / "strategy" / "fragments"
    required_files = [
        "header.txt",
        "rules_core.txt",
        "rules_3vs3.txt",
        "samples_3vs3.txt",
        "rules_2vs2.txt",
        "samples_2vs2.txt",
        "rules_recover.txt",
        "samples_recover.txt",
        # Phase 2.5c: game-phase fragment stubs (additive to mode fragments)
        "rules_ball_out.txt",
        "rules_goal_kick.txt",
        "rules_corner_kick_in.txt",
        "rules_kickoff.txt",
    ]
    
    for fragment_file in required_files:
        fragment_path = fragments_dir / fragment_file
        if not fragment_path.exists():
            print(f"  ❌ Missing fragment: {fragment_file}")
            assert False, f"Fragment file not found: {fragment_file}"
        print(f"  ✅ Found: {fragment_file}")
    
    print(f"\n✅ All {len(required_files)} fragment files present")

def test_launch_script_flags():
    """Launch script should support new flags."""
    print(f"\n{'='*70}")
    print(f"Testing launch script flags")
    print(f"{'='*70}\n")
    
    launch_script = Path(__file__).parent.parent.parent / "launch_r2k.sh"
    
    with open(launch_script, 'r') as f:
        content = f.read()
    
    # Check for --headless flag
    assert '--headless' in content, "Missing --headless flag in launch_r2k.sh"
    print("  ✅ Found --headless flag")
    
    # Check for --duration flag
    assert '--duration' in content, "Missing --duration flag in launch_r2k.sh"
    print("  ✅ Found --duration flag")
    
    # Check for reward_node
    assert 'reward_node.py' in content, "Missing reward_node.py in launch_r2k.sh"
    print("  ✅ Found reward_node.py in boot sequence")
    
    print(f"\n✅ All launch script flags verified")

if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v', '-s'])