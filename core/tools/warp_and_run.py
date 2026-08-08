#!/usr/bin/env python3
"""Warp-and-resume: teleport bots to start config, reset state, run 4s, repeat.

Avoids full Gazebo restart between ensemble runs. Uses:
  - /gazebo/set_entity_state to warp bots + ball
  - shared_state/reset_flag.json to reset referee + score_node state
  - Wall-clock timer for duration

Usage:
  python3 tools/warp_and_run.py --scenario 3vs3_attack_center --runs 5 --duration 4
  python3 tools/warp_and_run.py --scenario 3vs3_attack_center --runs 5 --duration 4 --dry-run
"""
import argparse
import json
import os
import sys
import time
import subprocess
import rclpy
from rclpy.node import Node
from gazebo_msgs.srv import SetEntityState
from geometry_msgs.msg import Twist

BASE_DIR = os.path.dirname(os.path.abspath(__file__)) + "/.."
SRC_DIR = os.path.join(BASE_DIR, "src")
SCENARIO_DIR = os.path.join(SRC_DIR, "scenario")
SHARED_STATE = os.path.join(SRC_DIR, "shared_state")
RESET_FLAG = os.path.join(SHARED_STATE, "reset_flag.json")
SETTLE_TIME = 0.3  # seconds to wait after warp for physics to settle


class WarpNode(Node):
    def __init__(self):
        super().__init__('warp_and_run_node')
        self.client = self.create_client(SetEntityState, '/gazebo/set_entity_state')
        self.get_logger().info("Waiting for /gazebo/set_entity_state service...")
        self.client.wait_for_service(timeout_sec=10.0)

    def warp_entity(self, name, x, y):
        """Teleport entity to (x, y), zero all velocities."""
        req = SetEntityState.Request()
        req.state.name = name
        req.state.reference_frame = 'world'
        req.state.pose.position.x = float(x)
        req.state.pose.position.y = float(y)
        req.state.pose.position.z = 0.1
        req.state.pose.orientation.w = 1.0  # identity quaternion
        req.state.twist = Twist()  # zero all velocities
        future = self.client.call_async(req)
        rclpy.spin_until_future_complete(self, future, timeout_sec=2.0)
        return future.result() is not None

    def warp_all(self, entities):
        """Warp all entities to their start positions."""
        ok = True
        for name, pos in entities.items():
            x, y = pos.get('x', 0), pos.get('y', 0)
            if not self.warp_entity(name, x, y):
                self.get_logger().warn(f"Failed to warp {name}")
                ok = False
        return ok

    def write_reset_flag(self):
        """Write reset flag to trigger referee + score_node state clear."""
        os.makedirs(SHARED_STATE, exist_ok=True)
        with open(RESET_FLAG, 'w') as f:
            json.dump({"timestamp": time.time()}, f)

    def stop_all_bots(self, entities):
        """Zero all bot velocities by warping in place."""
        for name, pos in entities.items():
            if name == 'soccer_ball':
                continue
            x, y = pos.get('x', 0), pos.get('y', 0)
            self.warp_entity(name, x, y)


def load_scenario(scenario_name):
    """Load scenario.json entities."""
    # Try package format first
    pkg = os.path.join(SCENARIO_DIR, scenario_name, "scenario.json")
    flat = os.path.join(SCENARIO_DIR, f"{scenario_name}.json")
    path = pkg if os.path.exists(pkg) else flat
    if not os.path.exists(path):
        print(f"ERROR: scenario not found: {scenario_name}")
        sys.exit(1)
    with open(path) as f:
        data = json.load(f)
    return data.get('entities', {})


def main():
    ap = argparse.ArgumentParser(description="Warp-and-resume ensemble runner")
    ap.add_argument("--scenario", required=True, help="Scenario name")
    ap.add_argument("--runs", type=int, default=5, help="Number of runs")
    ap.add_argument("--duration", type=float, default=4.0, help="Duration per run (seconds)")
    ap.add_argument("--dry-run", action="store_true", help="Print actions without executing")
    args = ap.parse_args()

    entities = load_scenario(args.scenario)
    print(f"Scenario: {args.scenario}")
    print(f"Entities: {len(entities)}")
    print(f"Runs: {args.runs} × {args.duration}s")
    print()

    if args.dry_run:
        for name, pos in entities.items():
            print(f"  Warp {name} to ({pos.get('x', 0):.2f}, {pos.get('y', 0):.2f})")
        print(f"  Write reset_flag.json")
        for i in range(args.runs):
            print(f"  Run {i+1}: warp → reset → settle {SETTLE_TIME}s → run {args.duration}s")
        return

    rclpy.init()
    node = WarpNode()

    for run_idx in range(args.runs):
        print(f"--- Run {run_idx + 1}/{args.runs} ---")

        # 1. Warp all entities to start positions
        print(f"  Warping {len(entities)} entities...")
        node.warp_all(entities)

        # 2. Write reset flag (triggers referee + score_node reset on next callback)
        node.write_reset_flag()

        # 3. Wait for physics to settle
        time.sleep(SETTLE_TIME)

        # 4. Run for duration (wall-clock)
        print(f"  Running for {args.duration}s...")
        t0 = time.time()
        while time.time() - t0 < args.duration:
            rclpy.spin_once(node, timeout_sec=0.1)

        print(f"  Run {run_idx + 1} complete ({time.time() - t0:.1f}s)")

    # Final stop: warp bots in place to zero velocities
    print("\nStopping all bots...")
    node.stop_all_bots(entities)

    node.destroy_node()
    rclpy.shutdown()
    print(f"\nDone: {args.runs} runs × {args.duration}s for {args.scenario}")


if __name__ == "__main__":
    main()