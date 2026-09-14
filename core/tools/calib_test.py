"""Calibration test module — offline evaluator routing checks + field runbooks.

Offline (no ROS, no Ollama, no K1)::

  python3 tools/calib_test.py
  → prints sim battery PASS/FAIL for 10 evaluator-routing checks

Field (hardware, via calib_cli.py "exec <id>")::

  >>> exec square        # interactive stepper, Enter=next, b=break

Runbooks defined in RUNBOOKS dict: each is a list of steps with cmd/note/target.
All sequences return to (0,0) so the human check is one Y/N at the end.
"""
import glob
import json
import math
import os
import sys
import time

# === Runbook definitions ===
# Each yields laser-printable commands for the K1 to follow on the field.
# All sequences start and end at (0,0) — one human check: "did it return?"

RUNBOOKS = {
    "short": [
        {"cmd": "k1 go to (0.5, 0)",      "note": "forward 0.5m (straight, vx only)",
         "target": (0.5, 0.0)},
        {"cmd": "k1 go to (0, 0)",         "note": "return to origin",
         "target": (0.0, 0.0)},
    ],
    "square": [
        {"cmd": "k1 go to (0.5, 0)",      "note": "leg 1: forward (east)",
         "target": (0.5, 0.0)},
        {"cmd": "k1 go to (0.5, 0.5)",    "note": "leg 2: 90° left turn (north)",
         "target": (0.5, 0.5)},
        {"cmd": "k1 go to (0, 0.5)",      "note": "leg 3: 90° left turn (west)",
         "target": (0.0, 0.5)},
        {"cmd": "k1 go to (0, 0)",         "note": "leg 4: 90° left turn (south — return)",
         "target": (0.0, 0.0)},
    ],
    "triangle": [
        {"cmd": "k1 go to (1, 0)",        "note": "leg 1: forward 1m",
         "target": (1.0, 0.0)},
        {"cmd": "k1 go to (0.5, 0.8660)", "note": "leg 2: ~60° left, diagonal",
         "target": (0.5, 0.8660)},
        {"cmd": "k1 go to (0, 0)",         "note": "leg 3: ~60° left, return to origin",
         "target": (0.0, 0.0)},
    ],
    # Yahboom calib runbooks (open-loop TimedMove — manual delta measurement)
    "y_line": [
        {"cmd": "y1 forward 0.5", "note": "y1 timed forward 0.5m — measure actual distance",
         "target": (0.5, 0.0), "prompt_measured": True},
        {"cmd": "y1 back 0.5",    "note": "y1 timed back 0.5m — measure from start mark",
         "target": (0.0, 0.0), "prompt_measured": True},
        {"cmd": "y2 forward 0.5", "note": "y2 timed forward 0.5m — measure actual distance",
         "target": (0.5, 0.0), "prompt_measured": True},
        {"cmd": "y2 back 0.5",    "note": "y2 timed back 0.5m — measure from start mark",
         "target": (0.0, 0.0), "prompt_measured": True},
    ],
    "y_turns": [
        {"cmd": "y1 turn 90",  "note": "y1 turn 90° CCW — measure actual angle",
         "target": (0.0, 0.0), "angle": 90.0, "prompt_measured": True},
        {"cmd": "y1 turn -90", "note": "y1 turn 90° CW (back to start)",
         "target": (0.0, 0.0), "angle": -90.0, "prompt_measured": True},
        {"cmd": "y2 turn 90",  "note": "y2 turn 90° CCW — measure actual angle",
         "target": (0.0, 0.0), "angle": 90.0, "prompt_measured": True},
        {"cmd": "y2 turn -90", "note": "y2 turn 90° CW (back to start)",
         "target": (0.0, 0.0), "angle": -90.0, "prompt_measured": True},
    ],
    # Yahboom goto rehearsal runbooks (2026-09-08) — EXACT same flow as the
    # k1 field test: closed-loop odom Goto + auto drift read + results
    # persistence. ±30% encoder odom => coarse arrivals; auto PASS/FAIL is
    # informational (relaxed threshold), the rehearsal value is exercising
    # the CLI + log-reading pipeline before the K1 field session.
    "y_short": [
        {"cmd": "y1 go to (0.5, 0)",  "note": "y1 forward 0.5m (closed-loop odom)",
         "target": (0.5, 0.0)},
        {"cmd": "y1 go to (0, 0)",     "note": "y1 return to origin",
         "target": (0.0, 0.0)},
    ],
    "y_square": [
        {"cmd": "y1 go to (0.5, 0)",  "note": "y1 leg 1: forward (east)",
         "target": (0.5, 0.0)},
        {"cmd": "y1 go to (0.5, 0.5)", "note": "y1 leg 2: 90° left (north)",
         "target": (0.5, 0.5)},
        {"cmd": "y1 go to (0, 0.5)",  "note": "y1 leg 3: 90° left (west)",
         "target": (0.0, 0.5)},
        {"cmd": "y1 go to (0, 0)",    "note": "y1 leg 4: 90° left (south — return)",
         "target": (0.0, 0.0)},
    ],
    "y_triangle": [
        {"cmd": "y1 go to (1, 0)",       "note": "y1 leg 1: forward 1m",
         "target": (1.0, 0.0)},
        {"cmd": "y1 go to (0.5, 0.8660)", "note": "y1 leg 2: ~60° left, diagonal",
         "target": (0.5, 0.8660)},
        {"cmd": "y1 go to (0, 0)",       "note": "y1 leg 3: ~60° left, return",
         "target": (0.0, 0.0)},
    ],
}

RUNBOOK_IDS = tuple(RUNBOOKS.keys())

# Odom source per runbook (drift reads + auto-PASS threshold lookup).
RUNBOOK_BOT = {
    "short": "k1", "square": "k1", "triangle": "k1",
    "y_line": "y1", "y_turns": "y1",
    "y_short": "y1", "y_square": "y1", "y_triangle": "y1",
}

# Auto-PASS origin-drift thresholds per bot (m). k1 = real accuracy gate;
# yahboom = informational (encoder odom ±30% — rehearsal vehicle, not an
# accuracy target; the number is data, not a verdict).
RESULT_TOL_M = {"k1": 0.15, "y1": 0.5, "y2": 0.5}

# === Result persistence ===
# One JSONL file, append-only, one line per completed/aborted runbook.
# Lives in src/logs/ alongside k1_trace_<run_id>.jsonl for cross-joins.

_RESULT_PATH = None

def _result_base():
    return os.path.join(os.path.dirname(__file__), '..', 'src', 'logs')

def _result_path():
    global _RESULT_PATH
    if _RESULT_PATH is None:
        p = os.path.join(_result_base(), 'calib_results.jsonl')
        os.makedirs(os.path.dirname(p), exist_ok=True)
        _RESULT_PATH = p
    return _RESULT_PATH

def current_run_id():
    """Infer current R2K_RUN_ID from the newest k1_trace_*.jsonl file.
    Fallback to an offline timestamp if no trace file exists."""
    files = sorted(glob.glob(os.path.join(_result_base(), 'k1_trace_*.jsonl')))
    if not files:
        return f"offline_{int(time.time())}"
    name = os.path.basename(files[-1])
    return name.replace('k1_trace_', '').replace('.jsonl', '')

def append_result(record):
    """Append one line to calib_results.jsonl. Non-blocking. Record must
    include: type, t_wall, run_id, runbook, mode, initial_odom, legs,
    origin_drift_m, auto_result, human_report, aborted."""
    try:
        with open(_result_path(), 'a') as f:
            f.write(json.dumps(record) + '\n')
    except Exception:
        pass


def load_results():
    """Read all runbook result records from calib_results.jsonl (oldest
    first). Malformed lines are skipped, not fatal. Used by the CLI 'results'
    command — the log-reading leg of the K1 field-test rehearsal."""
    recs = []
    try:
        with open(_result_path()) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    recs.append(json.loads(line))
                except ValueError:
                    continue
    except Exception:
        pass
    return recs


# === Field odom reader ===

def read_odom(bot="k1"):
    """Read latest odometry from shared_state/<bot>_odom.json (bridge writes
    k1_odom.json / y1_odom.json / y2_odom.json on the 0.5s cadence).
    Returns dict with x, y, theta, t, or None if file missing/garbled."""
    path = os.path.join(os.path.dirname(__file__), '..', 'src', 'shared_state',
                        f'{bot}_odom.json')
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def read_k1_odom():
    """Back-compat alias — read_odom('k1')."""
    return read_odom("k1")


def fmt_odom(odom):
    """Pretty-print a single odom sample for terminal display."""
    if odom is None:
        return "  (no odom)"
    return (f"  x={odom.get('x', 0):+7.3f}  y={odom.get('y', 0):+7.3f}  "
            f"theta={odom.get('theta', 0):+7.3f}")


def drift_from(targets, odom):
    """Euclidean distance between last step target and current odom."""
    if odom is None:
        return None
    tx, ty = targets[-1]["target"] if targets else (0.0, 0.0)
    return math.hypot(odom.get('x', 0) - tx, odom.get('y', 0) - ty)


# === Offline sim battery ===

def run_sim_battery():
    """10 offline checks of evaluator demo routing (no ROS, no Ollama).
    Returns (passed, total, report_lines)."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'ai_tactics'))
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
    import r2k_evaluator as ev

    import tempfile
    tmp = tempfile.mkdtemp()
    wp_path = os.path.join(tmp, 'waypoints.json')
    strat_path = os.path.join(tmp, 'current_strategy.json')
    open(wp_path, 'w').write('{}')
    open(strat_path, 'w').write('{}')

    # Monkeypatch paths
    ev.WAYPOINTS_PATH = wp_path
    ev.STRATEGY_PATH = strat_path

    # Monkeypatch the 7B compiler (we're offline — it must never fire)
    _compile_calls = []

    def _fake_compile(bot, text, ents):
        _compile_calls.append((bot, text))
        # If the text contains 'wing', simulate a compiler that writes waypoints
        # so the evaluator chain completes (otherwise waypath code runs)
        if 'wing' in text:
            import json as _j
            wps = _j.loads('[{"label":"FIRST","x":0.5,"y":1.0,"hold_duration":0},'
                           '{"label":"SECOND","x":0.5,"y":1.0,"hold_duration":2}]')
            st = ev._demo_bot_state(bot)
            st["waypoints"] = ev._norm_demo_waypoints(wps)
            st["target_idx"] = 0
            st["arrival_time"] = 0
            st["fast_cmd"] = None
        return True

    ev._compile_demo_task = _fake_compile

    ENTS = {"soccer_ball": {"x": 1.0, "y": 1.0},
            "blue_1": {"x": 0.0, "y": 0.0},
            "blue_2": {"x": 0.0, "y": 1.0}}

    def _assign():
        try:
            with open(strat_path) as f:
                return json.load(f).get("assignments", {})
        except Exception:
            return {}

    battery = [
        # Slot-name note (2026-09-08): expectations use the CANONICAL relay
        # keys the bridge consumes in CALIB direct addressing ("k1", not the
        # legacy "k1_bot"; "blue1"/"blue2", not "blue_1"). The old battery
        # checked the legacy names and failed vacuously against current code.
        ("k1 go to (1,0)", "Goto -> k1 slot, correct target",
         lambda a: a.get("k1") == {"action": "Goto", "x": 1.0, "y": 0.0},
         ev),
        ("k1 go to (-1,0)", "Goto -> k1 slot, negative x",
         lambda a: a.get("k1") == {"action": "Goto", "x": -1.0, "y": 0.0},
         ev),
        ("k1 go to (0,1)", "Goto -> k1 slot, y-only target",
         lambda a: a.get("k1") == {"action": "Goto", "x": 0.0, "y": 1.0},
         ev),
        ("k1 go to (-2,-1.5)", "Goto -> k1 slot, negative quadrant",
         lambda a: a.get("k1") == {"action": "Goto", "x": -2.0, "y": -1.5},
         ev),
        ("y1 go to (0.5, 0)", "y1 Goto -> y1 slot (rehearsal)",
         lambda a: a.get("y1") == {"action": "Goto", "x": 0.5, "y": 0.0},
         ev),
        ("y2 go to (0, 0.5)", "y2 Goto -> y2 slot (rehearsal)",
         lambda a: a.get("y2") == {"action": "Goto", "x": 0.0, "y": 0.5},
         ev),
        ("go to (1,0)", "bare go to -> blue1 waypath (not k1 forward)",
         lambda a: bool(ev._demo_bot_state("blue1").get("waypoints")),
         ev),
        ("face west", "face -> blue1 fast_cmd",
         lambda a: ev._demo_bot_state("blue1").get("fast_cmd", {}).get("action")
                   in ("Face", "Seq"),
         ev),
        ("blue_2 go to the left wing, pause 2s, go to the right wing",
         "blue2 only, compiler chain — blue1 not touched",
         lambda a: len(_compile_calls) == 1 and _compile_calls[0][0] == "blue2",
         ev),
        ("stop, resume", "comma chain — resume clears Hold",
         lambda a: ev._demo_bot_state("blue1").get("fast_cmd") is None
                   and not ev._demo_bot_state("blue1").get("waypoints"),
         ev),
        ("stop", "stop -> Hold for all",
         lambda a: all(
             ev._demo_bot_state(b).get("fast_cmd", {}).get("action") == "Hold"
             for b in ("blue1", "blue2")),
         ev),
        ("all say no", "all -> every blue bot gets Head gesture 'no'",
         lambda a: ev._demo_bot_state("blue1").get("fast_cmd", {}).get("gesture") == "no"
                   and ev._demo_bot_state("blue2").get("fast_cmd", {}).get("gesture") == "no",
         ev),
    ]

    passed = 0
    total = len(battery)
    lines = []

    for i, (cmd, desc, check_fn, ev_ref) in enumerate(battery, 1):
        _compile_calls.clear()
        ev._demo_state.clear()
        try:
            ev._handle_task_clause(cmd, ENTS)
            ok = check_fn(_assign())
        except Exception as e:
            ok = False
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        lines.append(f" {i:2d}  {status}  {cmd}")
        if not ok:
            lines.append(f"       {desc}")
    return passed, total, lines


def print_sim_battery():
    """Run the sim battery and print a terminal report."""
    passed, total, lines = run_sim_battery()
    print()
    print("=== Calibration Sim Test Report ========================")
    print()
    for l in lines:
        print(l)
    print()
    print(f"{passed}/{total} passed  ({total-passed} failed)")
    print()


def print_runbook(name):
    """Print a field runbook as ASCII text for offline reference."""
    steps = RUNBOOKS.get(name)
    if not steps:
        print(f"Unknown runbook. Available: {', '.join(RUNBOOK_IDS)}")
        return
    print()
    print(f"=== K1 Calibration Runbook: {name.upper()} ===================")
    print(f"  {len(steps)} legs, returns to (0,0)")
    print(f"  Make sure K1 is out of DAMP and standing at origin.")
    print()
    for i, s in enumerate(steps, 1):
        print(f"  Step {i}/{len(steps)}: {s['cmd']}")
        print(f"    {s['note']}")
        print(f"    target: ({s['target'][0]:.4f}, {s['target'][1]:.4f})")
        print(f"    odom:  x=____  y=____  theta=____")
        print()
    print(f"  Origin distance: ____ m  (threshold 0.15m)")
    print(f"  Walk looked correct?  [Y/N]: ____")
    print(f"  Wobbly? [{'.'}]  Overshoot? [{'.'}]  Slipped? [{'.'}]")
    print()


if __name__ == "__main__":
    print_sim_battery()