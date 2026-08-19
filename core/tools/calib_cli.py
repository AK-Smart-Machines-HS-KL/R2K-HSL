#!/usr/bin/env python3
"""Interactive calibration CLI: type tasks, bot executes.

Usage:
  python3 tools/calib_cli.py

The bot must be running in demo mode in another terminal:
  ./launch_r2k.sh --demo --no-visualizer --scenario 1vs0_waypoint --relay single_bot

Type a task and press Enter. The evaluator detects the change, calls the
7B compiler to translate it to waypoints, and the 3B executor drives the bot.

Type "help" or "examples" to see numbered sample commands — type the number
to send that command directly.

Control commands (instant, no compiler delay):
  stop / break / exit    — bot halts immediately, stays where it is
  resume / continue      — recover from stop, follow remaining path
  restart / redo / repeat — replay waypath from start
  go home / return       — stop waypath, drive to START position
"""
import json
import os
import time

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
task_path = os.path.join(base_dir, 'src', 'shared_state', 'task_input.json')
wp_path = os.path.join(base_dir, 'src', 'shared_state', 'waypoints.json')

os.makedirs(os.path.dirname(task_path), exist_ok=True)

FAST_COMMANDS = {"stop", "break", "exit", "halt",
                 "resume", "continue",
                 "restart", "re-start", "redo", "repeat",
                 "go home", "return", "return to start", "go to start", "home"}

SAMPLE_COMMANDS = [
    ("draw a hexagon 2m sides", "Shapes"),
    ("draw a rectangle from (1,1) to (3,2)", "Shapes"),
    ("draw a square with 2m sides starting at (-2,0)", "Shapes"),
    ("draw a triangle (0,0) (3,0) (1.5,2)", "Shapes"),
    ("draw a pentagon centered at (0,0) radius 2m", "Shapes"),
    ("trace a circle center (0,0) radius 2m", "Circles"),
    ("go to (2, 0), then go to (2, 3)", "Coords"),
    ("go to -2, -3, then pause 2sec, then return", "Coords"),
    ("go to the left wing, pause 2 seconds, go to the right wing", "Landmarks"),
    ("go to the wing", "Landmarks"),
    ("go to the corner", "Landmarks"),
    ("go to own goal, then go to opponent goal", "Landmarks"),
    ("go to opponent left corner, pause 3 seconds, go to own right corner", "Landmarks"),
    ("approach the ball into kicking distance", "Ball"),
    ("patrol between (-2,0) and (2,0) three times", "Patrols"),
    ("go to (3,1) via (1,0) and (2,0)", "Paths"),
    ("go to (1,1), wait 2 seconds, go to (-1,1), wait 2 seconds, return", "Combos"),
    ("return", "Control"),
    ("stop", "Control"),
    ("resume", "Control"),
    ("go home", "Control"),
]


def show_waypoints():
    try:
        with open(wp_path, 'r') as f:
            data = json.load(f)
        wps = data.get("waypoints", [])
        if not wps:
            print("  (no waypoints — bot is stopped)")
            return
        print(f"  Waypath ({len(wps)} waypoints):")
        for w in wps:
            label = w.get("label", "?")
            x = w.get("x", 0)
            y = w.get("y", 0)
            hold = w.get("hold_duration", 0)
            if hold > 0:
                print(f"    {label:8s} -> ({x:6.1f}, {y:6.1f})  [pause {hold:.0f}s]")
            else:
                print(f"    {label:8s} -> ({x:6.1f}, {y:6.1f})")
    except Exception:
        print("  (could not read waypoints)")


def show_examples():
    """Show numbered sample commands grouped by category."""
    print()
    print("Sample commands (type the number to send, or copy the text):")
    print()
    cur_cat = None
    for i, (cmd, cat) in enumerate(SAMPLE_COMMANDS, 1):
        if cat != cur_cat:
            print(f"  --- {cat} ---")
            cur_cat = cat
        print(f"  {i:2d}  {cmd}")
    print()


def send_task(task_text):
    """Write task to task_input.json and wait for compiler result."""
    old_mtime = 0
    try:
        old_mtime = os.path.getmtime(wp_path)
    except OSError:
        pass

    with open(task_path, 'w') as f:
        json.dump({"task": task_text, "timestamp": time.time()}, f)

    task_clean = task_text.strip().lower()

    if task_clean in FAST_COMMANDS:
        print(f"  -> {task_clean}: executed (instant)")
        if task_clean in ("stop", "break", "exit", "halt"):
            print("  Bot halted at current position.")
        elif task_clean in ("resume", "continue"):
            print("  Bot resuming remaining waypath.")
        elif task_clean in ("restart", "re-start", "redo", "repeat"):
            print("  Bot replaying waypath from start.")
        elif task_clean in ("go home", "return", "return to start", "go to start", "home"):
            print("  Bot driving to START (0, 0).")
        print()
        return

    print(f"  -> compiling with 7B...", end="", flush=True)
    timeout = 8
    start = time.time()
    compiled = False
    while time.time() - start < timeout:
        time.sleep(0.2)
        try:
            new_mtime = os.path.getmtime(wp_path)
            if new_mtime > old_mtime:
                compiled = True
                break
        except OSError:
            pass
        print(".", end="", flush=True)

    if compiled:
        print(" done.")
        show_waypoints()
    else:
        print(" timeout.")
        print("  (compiler may still be processing — check bot terminal for errors)")
    print()


print("R2K Calibration CLI — type a task and press Enter. Ctrl+C to exit.")
print()
print('Type "help" or "examples" for sample commands (pick by number).')
print()
print("Control commands (instant):")
print('  "stop"  / "break" / "exit"   — halt bot where it is')
print('  "resume" / "continue"        — recover from stop, follow remaining path')
print('  "restart" / "redo" / "repeat" — replay waypath from start')
print('  "go home" / "return"        — drive to START position')
print()

show_waypoints()
print()

while True:
    try:
        task = input("task> ")
        if not task.strip():
            continue

        task_stripped = task.strip()

        # Help / examples
        if task_stripped.lower() in ("help", "examples", "?", "h"):
            show_examples()
            continue

        # Number selection from sample list
        if task_stripped.isdigit():
            idx = int(task_stripped)
            if 1 <= idx <= len(SAMPLE_COMMANDS):
                cmd = SAMPLE_COMMANDS[idx - 1][0]
                print(f"  -> sending: {cmd}")
                send_task(cmd)
                continue
            else:
                print(f"  Number out of range (1-{len(SAMPLE_COMMANDS)}). Type 'help' for list.")
                print()
                continue

        # Normal task
        send_task(task_stripped)

    except (KeyboardInterrupt, EOFError):
        print("\nBye.")
        break