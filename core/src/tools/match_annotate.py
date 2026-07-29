#!/usr/bin/env python3
"""Match Annotator — freeze Gazebo, annotate a moment, continue.

Run alongside a live match. Press ENTER to pause Gazebo, record the game
state + your comment, then unpause. Annotations are saved to
logs/annotations_<run_id>.jsonl for post-match analysis with replay_trace.py.

Usage:
  python3 tools/match_annotate.py [--run-id <R2K_RUN_ID>]

If --run-id is omitted, reads R2K_RUN_ID from env, then falls back to
the latest world_trace file in logs/.

Requires: ros2 service /gazebo/pause_physics and /gazebo/unpause_physics
(available via libgazebo_ros_state.so, already loaded in robocup.world).
"""

import json
import os
import sys
import time
import glob
import shutil
import atexit
import subprocess
import termios
import tty
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
LOG_DIR = BASE_DIR / "logs"
WORLDSTATE_PATH = BASE_DIR / "shared_state" / "Worldstate.json"
LLM_TRACE_DIR = LOG_DIR

_gazebo_paused = False


def find_run_id():
    rid = os.getenv("R2K_RUN_ID")
    if rid:
        return rid
    files = sorted(glob.glob(str(LOG_DIR / "world_trace_*.jsonl")),
                   key=os.path.getmtime, reverse=True)
    if not files:
        return None
    fname = os.path.basename(files[0])
    return fname.replace("world_trace_", "").replace(".jsonl", "")


def find_llm_trace(run_id):
    path = LLM_TRACE_DIR / f"llm_trace_{run_id}.jsonl"
    if path.exists():
        return path
    return None


def read_worldstate():
    try:
        with open(WORLDSTATE_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return None


def read_last_llm_decision(llm_trace_path):
    if not llm_trace_path or not llm_trace_path.exists():
        return None
    try:
        lines = llm_trace_path.read_text().strip().splitlines()
        if not lines:
            return None
        rec = json.loads(lines[-1])
        raw = rec.get("raw_response", "").strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end >= 0:
            try:
                data = json.loads(raw[start:end + 1])
            except Exception:
                data = None
        else:
            data = None
        return {
            "t": rec.get("t"),
            "latency_ms": rec.get("latency_ms"),
            "assignments": data.get("assignments", {}) if data else {},
            "analysis": data.get("analysis", "") if data else "",
            "oracle": data.get("oracle", "") if data else "",
        }
    except Exception:
        return None


def get_ros2_prefix():
    """Detect how to call ros2: native (U22) or via docker exec (U24).
    Returns a list of args that, when + ['service', 'call', ...] appended,
    produce a valid command. For docker exec, uses bash -c with the full
    command constructed as a single string.
    """
    # Native mode (U22): ros2 on the host
    if shutil.which("ros2"):
        return []
    # Docker mode (U24): find the running container
    result = subprocess.run(
        ["docker", "ps", "--format", "{{.Names}}"],
        capture_output=True, text=True, timeout=5
    )
    running = result.stdout.split()
    # launch_r2k.sh exports COMPOSE_PROJECT_NAME and PROJECT_NAME (= lowercased basename of PWD).
    # Container name is ${PROJECT_NAME}_gazebo (see docker-compose.yml).
    project = os.getenv("PROJECT_NAME") or os.getenv("COMPOSE_PROJECT_NAME", "")
    candidates = []
    if project:
        candidates.append(f"{project}_gazebo")
    candidates.append("core_gazebo")  # legacy fallback
    container_name = next((c for c in candidates if c in running), None)
    if container_name:
        return ["docker", "exec", container_name, "bash", "-c",
                "source /opt/ros/humble/setup.bash && source /workspace/ros2_ws/install/setup.bash && ros2"]
    # No ros2 and no matching container — cannot proceed
    return None


ROS2_PREFIX = get_ros2_prefix()
_DOCKER_MODE = ROS2_PREFIX is not None and len(ROS2_PREFIX) > 0 and "bash" in ROS2_PREFIX and "-c" in ROS2_PREFIX


def _run_ros2(args, timeout=10):
    """Run a ros2 command with proper quoting for both native and docker modes."""
    if ROS2_PREFIX is None:
        return subprocess.CompletedProcess(["ros2"] + args, returncode=-1,
                                            stdout="", stderr="ros2 not available (no native binary, no matching container)")
    if _DOCKER_MODE:
        shell_cmd = ROS2_PREFIX[-1] + " " + " ".join(args)
        cmd = ROS2_PREFIX[:-1] + [shell_cmd]
    else:
        cmd = ROS2_PREFIX + args
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(cmd, returncode=-1, stdout="", stderr="timeout")


def pause_gazebo():
    global _gazebo_paused
    for svc in ["/pause_physics", "/gazebo/pause_physics"]:
        result = _run_ros2(["service", "call", svc, "std_srvs/srv/Empty"], timeout=15)
        if result.returncode == 0:
            _gazebo_paused = True
            return True
        print(f"   ⚠️  {svc} failed: {result.stderr.strip()[:100]}")
    print("   ❌ Could not pause Gazebo. Check service availability above.")
    return False


def unpause_gazebo():
    global _gazebo_paused
    for svc in ["/unpause_physics", "/gazebo/unpause_physics"]:
        result = _run_ros2(["service", "call", svc, "std_srvs/srv/Empty"], timeout=15)
        if result.returncode == 0:
            _gazebo_paused = False
            return True
        print(f"   ⚠️  {svc} failed: {result.stderr.strip()[:100]}")
    print("   ❌ Could not unpause Gazebo.")
    return False


def _cleanup():
    if _gazebo_paused:
        print("\n⚠️  Gazebo was paused — unpausing before exit...")
        unpause_gazebo()

atexit.register(_cleanup)


def format_positions(entities):
    lines = []
    for name in sorted(entities.keys()):
        pos = entities[name]
        if isinstance(pos, dict):
            lines.append(f"    {name}: ({pos.get('x', 0):.1f}, {pos.get('y', 0):.1f})")
    return "\n".join(lines)


def read_key():
    """Read a single keypress without waiting for ENTER. Returns the character."""
    try:
        old = termios.tcgetattr(sys.stdin.fileno())
    except (termios.error, ValueError):
        return input()
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, old)
    return ch


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Match Annotator")
    parser.add_argument("--run-id", default=None, help="R2K_RUN_ID (auto-detected if omitted)")
    args = parser.parse_args()

    run_id = args.run_id or find_run_id()
    if not run_id:
        print("❌ Could not determine R2K_RUN_ID. Set --run-id or R2K_RUN_ID env var.")
        sys.exit(1)

    annotations_path = LOG_DIR / f"annotations_{run_id}.jsonl"
    llm_trace_path = find_llm_trace(run_id)

    prefix_desc = " ".join(ROS2_PREFIX) if ROS2_PREFIX else ("native ros2" if shutil.which("ros2") else "(unavailable)")
    print(f"Match Annotator — press ENTER to freeze+annotate, 'q' to quit")
    print(f"Run ID: {run_id}")
    print(f"Annotations: {annotations_path}")
    print(f"LLM trace: {llm_trace_path}")
    print(f"ROS2 prefix: {prefix_desc}")
    # Debug: show env + container detection
    _proj = os.getenv("PROJECT_NAME") or os.getenv("COMPOSE_PROJECT_NAME")
    print(f"  [debug] PROJECT_NAME={os.getenv('PROJECT_NAME')!r} COMPOSE_PROJECT_NAME={os.getenv('COMPOSE_PROJECT_NAME')!r}")
    _dr = subprocess.run(["docker", "ps", "--format", "{{.Names}}"], capture_output=True, text=True, timeout=5)
    print(f"  [debug] containers={_dr.stdout.strip().splitlines()!r} (expected: {_proj + '_gazebo' if _proj else '?'})")

    # List available pause/unpause services to verify plugin is loaded
    print("Checking for Gazebo pause services...")
    pause_svcs = []
    for attempt in range(3):
        result = _run_ros2(["service", "list"], timeout=10)
        if result.returncode != 0:
            print(f"   (attempt {attempt+1}/3) ros2 service list failed — "
                  f"{result.stderr.strip()[:80]}")
            time.sleep(2)
            continue
        pause_svcs = [l for l in result.stdout.splitlines()
                      if "pause" in l.lower() or "unpause" in l.lower()]
        if pause_svcs:
            break
        # Gazebo may still be starting up
        all_svcs = [l for l in result.stdout.splitlines() if l.strip()]
        print(f"   (attempt {attempt+1}/3) {len(all_svcs)} services found, "
              f"but no pause/unpause. Gazebo may still be starting...")
        time.sleep(2)

    if pause_svcs:
        print(f"✅ Pause services: {pause_svcs}")
    else:
        print("⚠️  No pause/unpause services found after 3 attempts.")
        print("   Gazebo may not be running yet, or libgazebo_ros_state.so is not loaded.")
        print("   You can still annotate — pause will fail but state will be recorded.")

    print()

    annotation_count = 0

    while True:
        key = read_key()

        if key == "q":
            print(f"✅ {annotation_count} annotations saved to {annotations_path}")
            break

        if key != "\r" and key != "\n":
            continue

        print("⚡ Pausing Gazebo...")
        if not pause_gazebo():
            print("   Continuing without pause...\n")
            continue
        time.sleep(0.2)

        world = read_worldstate()
        if not world:
            print("❌ Could not read Worldstate.json — is the match running?")
            unpause_gazebo()
            continue

        entities = world.get("entities", {})
        match_state = world.get("match_state", {})
        sim_time = world.get("t", 0.0)
        wall_time = time.time()
        score = {"blue": match_state.get("blue", 0), "red": match_state.get("red", 0)}
        status = match_state.get("status", "playing")
        ball = entities.get("soccer_ball", {})

        last_llm = read_last_llm_decision(llm_trace_path)

        print(f"📋 Game time: {sim_time:.1f}s (sim) | Wall: {wall_time:.1f} | "
              f"Score: Blue {score['blue']} : {score['red']} Red | Status: {status}")
        print(f"   Ball: ({ball.get('x', 0):.1f}, {ball.get('y', 0):.1f})")
        print(format_positions(entities))

        if last_llm and last_llm.get("assignments"):
            print(f"\n   Last LLM decision (lat={last_llm['latency_ms']}ms):")
            for bot, action in last_llm["assignments"].items():
                print(f"     {bot}: {json.dumps(action)}")

        try:
            comment = input("Comment (or 'q' to skip): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n⚠️  Interrupted — skipping annotation. Unpausing...")
            unpause_gazebo()
            continue

        if comment.lower() == "q":
            print("⚠️  Skipping annotation. Unpausing...")
            unpause_gazebo()
            print()
            continue

        record = {
            "t_sim": sim_time,
            "t_wall": wall_time,
            "paused": True,
            "score": score,
            "status": status,
            "snapshot": entities,
            "last_llm_decision": {
                "latency_ms": last_llm["latency_ms"] if last_llm else None,
                "assignments": last_llm["assignments"] if last_llm else {},
                "analysis": last_llm["analysis"] if last_llm else "",
                "oracle": last_llm["oracle"] if last_llm else "",
            } if last_llm else None,
            "comment": comment,
            "annotation_index": annotation_count,
        }

        try:
            with open(annotations_path, "a") as f:
                f.write(json.dumps(record) + "\n")
            annotation_count += 1
            print(f"✅ Annotation #{annotation_count} saved.")
        except Exception as e:
            print(f"❌ Failed to save annotation: {e}")

        print("Unpausing Gazebo...")
        unpause_gazebo()
        print()


if __name__ == "__main__":
    main()