#!/usr/bin/env python3
"""Interactive calibration CLI: type tasks, bot executes.

Usage:
  python3 tools/calib_cli.py

The bot must be running in demo mode in another terminal:
  ./launch_r2k.sh --demo --no-visualizer --scenario 1vs0_default --relay single_bot

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
import math
import os
import re
import sys
import time

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(base_dir, 'tools'))
import calib_test
task_path = os.path.join(base_dir, 'src', 'shared_state', 'task_input.json')
wp_path = os.path.join(base_dir, 'src', 'shared_state', 'waypoints.json')

os.makedirs(os.path.dirname(task_path), exist_ok=True)

FAST_COMMANDS = {"stop", "break", "exit", "halt",
                 "resume", "continue",
                 "restart", "re-start", "redo", "repeat",
                 "go home", "return", "return to start", "go to start", "home"}

# Mirror of r2k_evaluator head/face fast-paths — these execute instantly, so
# the CLI must not wait on the 7B compiler. Sign convention (model frame):
# look pan + = camera LEFT, + = UP. Hardware: blue_2 = Yahboom#2 gimbal,
# k1 prefix → blue_1 (K1 head via RPC 2004 / Yahboom#1 gimbal via servo_s1|s2).
HEAD_LOOK_COMMANDS = ("look left", "look right", "look center", "look straight",
                      "look up", "look down")
HEAD_GESTURE_COMMANDS = ("say yes", "say no")
FACE_ABS_COMMANDS = ("face north", "face south", "face east", "face west",
                     "face opponent goal", "face own goal", "face left", "face right")
FACE_REL_COMMANDS = ("turn left", "turn right", "turn around")
ROTATE_RE = re.compile(r'^rotate\s+(-?\d+(?:\.\d+)?)\s*(?:deg(?:rees)?)?$')
# Mirror of r2k_evaluator.DEMO_HEADING_REL_RE — heading-relative tasks are
# rejected evaluator-side (no yaw in the world model; the 7B compiled
# "forward 1m" to a garbage ~2.3m run, 2026-09-05). Mirror here so the CLI
# gives the instant rejection instead of an 8s compiler timeout.
HEADING_REL_RE = re.compile(r'\b(forward|forwards|backward|backwards|ahead)\s+\d')
# Calib turn verb: "y1 turn 45" / "turn 90o" / "turn -45°" — open-loop
# TimedMove evaluator-side (mirror incl. the o/° suffixes people type)
TURN_CALIB_RE = re.compile(r'^turn\s+-?\d+(?:\.\d+)?\s*(?:deg(?:rees)?|[o°])?$')
# Mirror of r2k_evaluator chain semantics: "<step>, then <step>" chains
# instant commands into ONE sequence (one bot per chain). Chains are
# NON-MOTION steps only — coordinate moves break drag_twin's waypath-watch
# (rewound 2026-09-05): mixed chains are rejected with guidance.
CHAIN_SPLIT_RE = re.compile(r',?\s*\b(?:then|next)\b\s+')
CHAIN_STEP_FAST = re.compile(
    r'^(?:pause|wait)\s+\d|face\s+(?:north|south|east|west|opponent goal|own goal'
    r'|left|right)$|turn\s+(?:left|right|around)$|rotate\s+-?\d|look\s+|say\s+'
    r'(?:yes|no)$')
CHAIN_PAUSE_RE = re.compile(r'^(?:pause|wait)\s+\d')
# Mirror of r2k_evaluator.DEMO_INSTANT_WORD_RE: facing/head words must not
# reach the 7B compiler (it guesses coordinates for them)
INSTANT_WORD_RE = re.compile(r'\b(?:face|turn|rotate|look|say)\b')
# Mirror of r2k_evaluator._DEMO_COMMA_SEP_RE — CLI-side recognition only
_COMMA_SEP_CLI_RE = re.compile(r',\s+(?!\d)(?!(?:then|next)\b)')

def _chain_kind(core_cmd):
    """Mirror of the evaluator chain decision table:
    'seq'      — all segments instant (face/turn/rotate/look/say/pause)
    'waypath' — all segments moves ('goto' == 'go to') + pauses -> waypath
    'mixed'   — facing and move steps both present -> rejected
    None      — pure compiler vocabulary -> 7B"""
    segs = [s.strip() for s in CHAIN_SPLIT_RE.split(core_cmd)]
    if len(segs) < 2:
        return None
    is_pause = [bool(CHAIN_PAUSE_RE.match(s)) for s in segs]
    is_move = [bool(COORD_FASTPATH_RE.match(s)) for s in segs]
    is_instant = [bool(CHAIN_STEP_FAST.search(s)) for s in segs]
    instant_np = [i and not p for i, p in zip(is_instant, is_pause)]
    if all(is_instant):
        return "seq"
    if all(m or p for m, p in zip(is_move, is_pause)) and any(is_move):
        return "waypath"
    if any(instant_np) and any(is_move):
        return "mixed"
    return None

SAMPLE_COMMANDS = [
    "say yes",
    "say no",
    "blue_2 say yes",
    "face west",
    "turn left",
    "go to 2,2, then pause 2sec, then go to 3,3",
    "face west, then say no",
    "stop, resume",
    "go to (2,0), return",
    "go to -2, -3, then pause 2sec, then return",
    "go to the left wing, pause 2 seconds, go to the right wing",
    "go to own left corner, then go to opponent right corner",
    "draw a rectangle from (1,1) to (3,2)",
    "draw a pentagon centered at (0,0) radius 2m",
    "draw a hexagon 2m sides",
    "approach the ball into kicking distance",
    "all go to (1,1)",
    "all say no",
    "k1 go to (1,0)",
    "y1 go to (1,0)",
    "stop",
    "resume",
    "restart",
    "go home",
    "blue_2 look left",
]


BOT_PREFIX_RE = re.compile(r'^(blue_?\d+|y_?\d+|yahboom_?\d+|k1_bot|k1)\s+(.+)$')
# Mirror of r2k_evaluator.DEMO_SCOPE_TOKEN_RE / DEMO_SCOPE_BOTS_RE — scope
# prefixes ("all ...") route to every blue bot evaluator-side; stripped here
# so fast-path detection still matches (otherwise the CLI would wait on the
# 7B compiler for an instant command).
SCOPE_RE = re.compile(r'^(?:all|every|both|yahbooms?|sim(?:ulated)?)\b[\s,:\)-]*')
SCOPE_BOTS_RE = re.compile(r'^bots?\b[\s,:-]*')
# Mirror of the evaluator fleet-stop guard ("stop all bots" is instant).
FLEET_STOP_RE = re.compile(r'^(?:stop|halt)\s+(?:all|every|bots|everyone)\b')
# Mirror of r2k_evaluator.DEMO_COORD_RE — explicit coords execute instantly
# (coordinate fast-path), so the CLI must not wait for the 7B compiler.
COORD_FASTPATH_RE = re.compile(
    r'^(?:go(?:\s*to)?|goto|move(?:\s*to)?|drive(?:\s*to)?)\s*[\(\[]?\s*'
    r'(-?\d+(?:\.\d+)?)\s*[,; ]\s*(-?\d+(?:\.\d+)?)\s*[\)\]]?$')


def _print_wps(wps):
    for w in wps:
        label = w.get("label", "?")
        x = w.get("x", 0)
        y = w.get("y", 0)
        hold = w.get("hold_duration", 0)
        if hold >= 0.05:   # ignore the 7B's "0.0"-ish filler values
            print(f"    {label:8s} -> ({x:6.1f}, {y:6.1f})  [pause {hold:.0f}s]")
        else:
            print(f"    {label:8s} -> ({x:6.1f}, {y:6.1f})")


def show_waypoints():
    try:
        with open(wp_path, 'r') as f:
            data = json.load(f)
        bots = data.get("bots")
        if isinstance(bots, dict) and bots:
            for bot in sorted(bots):
                wps = bots[bot].get("waypoints", [])
                if wps:
                    print(f"  {bot} waypath ({len(wps)} waypoints):")
                    _print_wps(wps)
                else:
                    print(f"  {bot}: (no waypoints — stopped)")
            return
        wps = data.get("waypoints", [])
        if not wps:
            print("  (no waypoints — bot is stopped)")
            return
        print(f"  Waypath ({len(wps)} waypoints):")
        _print_wps(wps)
    except Exception:
        print("  (could not read waypoints)")


def show_examples():
    """Show numbered sample commands."""
    print()
    print("Sample commands (type the number to send, or copy the text).")
    print()
    print("Routing: bare cmds -> blue_1; camera gimbal -> \"blue_2 ...\";")
    print('         "all ..." -> every blue bot; bare control -> ALL bots.')
    print('Chains: "<step>, then <step>" sequence ONE bot; "; " runs parallel.')
    print()
    print()
    for i, cmd in enumerate(SAMPLE_COMMANDS, 1):
        print(f"  {i:2d}  {cmd}")
    print()


def send_task(task_text):
    """Write task to task_input.json and wait for compiler result."""
    old_mtime = 0
    try:
        old_mtime = os.path.getmtime(wp_path)
    except OSError:
        pass

    try:
        with open(task_path, 'w') as f:
            json.dump({"task": task_text, "timestamp": time.time()}, f)
    except PermissionError:
        print(f"  ✗ Permission denied on {task_path}")
        print("    (file was created by a root-identity process — fix once with:")
        print("     sudo chmod 666 src/shared_state/task_input.json)")
        return

    task_clean = task_text.strip().lower().strip('"').strip("'")

    m = BOT_PREFIX_RE.match(task_clean)
    core_cmd = m.group(2).strip() if m else task_clean
    bot_label = m.group(1) if m else None

    # Scope prefix ("all go to ..."): strip for fast-path matching; the
    # evaluator routes the clause to every blue bot in the world state.
    m_scope = SCOPE_RE.match(core_cmd)
    if m_scope:
        rest = SCOPE_BOTS_RE.sub('', core_cmd[m_scope.end():]).strip()
        if rest:
            bot_label = "all bots"
            core_cmd = rest
        else:
            print('  -> scope only ("all" / "all bots") — nothing to do.')
            print()
            return

    if FLEET_STOP_RE.match(core_cmd):
        print("  -> stop [all bots]: executed (instant)")
        print()
        return

    if core_cmd in FAST_COMMANDS:
        target = bot_label if bot_label else "all bots"
        print(f"  -> {core_cmd} [{target}]: executed (instant)")
        if core_cmd in ("stop", "break", "exit", "halt"):
            print(f"  {target} halted at current position.")
        elif core_cmd in ("resume", "continue"):
            print(f"  {target} resuming remaining waypath.")
        elif core_cmd in ("restart", "re-start", "redo", "repeat"):
            print(f"  {target} replaying waypath from start.")
        elif core_cmd in ("go home", "return", "return to start", "go to start", "home"):
            print(f"  {target} driving to its START position.")
        print()
        return

    # Belief feedback (cleanup plan 2026-09-08): read the bot's odom state
    # file and tell the operator WHAT THE SYSTEM THINKS — "driving 0.50m"
    # vs "ALREADY THERE, nothing to do" (the ambiguity cost a full debug
    # round: home + face east were no-ops after a power-cycle reset and
    # looked like failures).
    def _print_belief(bot_key, tx, ty):
        d = calib_test.read_odom(bot_key)
        if not d:
            print(f"     (no odom yet — estimator assumes start (0,0,0))")
            return
        dist = math.hypot(tx - d.get('x', 0.0), ty - d.get('y', 0.0))
        print(f"     bot believes: ({d.get('x', 0):+.2f},{d.get('y', 0):+.2f}) "
              f"yaw {d.get('theta', 0):+.2f} [{d.get('src', '?')}] — "
              f"{dist:.2f} m to target")
        if dist <= 0.15:
            print("     ⚠ ALREADY THERE (within 0.15 m deadband) — nothing to do.")
            print("       (After a power-cycle, (0,0) = the spot where the bot booted.)")

    def _bot_key(label):
        bl = label.lower()
        if bl.startswith("k1"):
            return "k1"
        if bl in ("y2", "y_2", "yahboom2", "yahboom_2"):
            return "y2"
        return "y1"

    # Closed-loop Goto fast-path (k1 + yahboos): bot prefix + explicit coords
    # routes to the bridge's odom loop — NOT the waypath machinery. Instant,
    # no compiler, no executor. Yahboom = K1 field-test rehearsal (2026-09-08).
    if COORD_FASTPATH_RE.match(core_cmd) and bot_label:
        bl = bot_label.lower()
        if bl in ("k1", "k1_bot"):
            print("  -> instant Goto [k1] (closed-loop odom, no compiler)")
            print("     bridge drives; parks at the target (~0.2m)")
            print()
            return
        if bl in ("y1", "y_1", "yahboom1", "yahboom_1",
                  "y2", "y_2", "yahboom2", "yahboom_2"):
            print(f"  -> instant Goto [{bl}] (closed-loop odom_raw, no compiler)")
            print("     coarse arrival (encoder odom ±30% — rehearsal); parks at the target")
            m_c = COORD_FASTPATH_RE.match(core_cmd)
            _print_belief(_bot_key(bl), float(m_c.group(1)), float(m_c.group(2)))
            print()
            return

    if COORD_FASTPATH_RE.match(core_cmd):
        target = bot_label if bot_label else "blue_1"
        print(f"  -> waypath to the coords [{target}] (no compiler;")
        print("     executor drives, parks at the target)")
        if bot_label is None and _detect_mode() == "calib":
            # Calib routing: bare task verbs default to the K1 slot
            # (field-first) — on a Yahboom rehearsal that is a DEAD slot
            # while K1 is offline. Say so instead of moving nothing
            # (live confusion 2026-09-08).
            print("     ⚠ calib: bare 'go to' targets K1 — prefix y1/y2 to")
            print("       drive the Yahboos (e.g. 'y1 go to (0.5,0)').")
        print()
        return

    # Home verbs with a bot prefix in calib: instant Goto(0,0) — the
    # calibration start pose IS the odom origin (hardware semantics; the
    # 7B-compiled waypath drove nothing, live 2026-09-08).
    if bot_label and re.match(
            r'^(?:go\s*to\s*|goto\s*|go\s+|drive\s+to\s+)?(?:home|origin|start|return)$',
            core_cmd):
        print(f"  -> instant Goto [{bot_label}] home (0,0 — odom origin)")
        _print_belief(_bot_key(bot_label), 0.0, 0.0)
        print()
        return

    # Head/face fast-paths (instant; ALL bare cmds default to blue_1)
    if core_cmd in HEAD_LOOK_COMMANDS or core_cmd in HEAD_GESTURE_COMMANDS:
        target = bot_label if bot_label else "blue_1 (body; camera: blue_2 ...)"
        print(f"  -> instant Head [{target}] (no compiler)")
        if core_cmd in HEAD_GESTURE_COMMANDS:
            print("     blue_1: body bob/shake — K1 head follows; blue_2: camera")
        print()
        return
    if core_cmd in FACE_ABS_COMMANDS or core_cmd in FACE_REL_COMMANDS or ROTATE_RE.match(core_cmd):
        target = bot_label if bot_label and not bot_label.startswith("k1") else "blue_1"
        print(f"  -> instant Face [{target}] (body turn-in-place, no compiler)")
        if bot_label and _detect_mode() == "calib":
            d = calib_test.read_odom(_bot_key(bot_label))
            if d:
                # Calib boot compass: yaw 0 = north (power-cycle ritual).
                face_yaw = ({"face east": -math.pi / 2, "face north": 0.0,
                             "face west": math.pi / 2, "face south": math.pi}
                            .get(core_cmd))
                if face_yaw is not None:
                    diff = math.degrees(math.atan2(
                        math.sin(face_yaw - d.get('theta', 0.0)),
                        math.cos(face_yaw - d.get('theta', 0.0))))
                    print(f"     bot yaw {d.get('theta', 0):+.2f} rad — "
                          f"{abs(diff):.0f}° to {core_cmd.split()[-1]}")
                    if abs(diff) < 6:
                        print("     ⚠ ALREADY FACING that way — nothing to do.")
        print()
        return

    if (HEADING_REL_RE.search(core_cmd) or TURN_CALIB_RE.match(core_cmd)) \
            and _detect_mode() == "calib":
        # Calib mode: forward/back = open-loop TimedMove (tape-measure);
        # turn <deg> = CLOSED-LOOP on odom yaw (relative Face machinery —
        # the board's yaw authority is ~half the commanded rate, so
        # open-loop timing under-delivers; live 2026-09-08).
        if TURN_CALIB_RE.match(core_cmd):
            target = bot_label if bot_label else "k1 (default)"
            print(f"  -> closed-loop Turn [{target}] on odom yaw (no compiler;")
            print("     + = clockwise/right, compass convention)")
            if bot_label is None:
                print("     ⚠ calib: bare 'turn' targets K1 — prefix y1/y2 to")
                print("       drive the Yahboos.")
        else:
            target = bot_label if bot_label else "y1"
            print(f"  -> instant TimedMove [{target}] (open-loop, no compiler)")
            print("     Measure the real delta with a tape; runbook legs prompt for it.")
        print()
        return

    if HEADING_REL_RE.search(core_cmd):
        print("  -> rejected (heading-relative): bots have no yaw in the world")
        print("     model yet, so the compiler would guess coordinates.")
        print('     Use coordinates instead: e.g. "go to (2, 0)" or a landmark')
        print('     ("go to the left wing"). Rejected evaluator-side as well.')
        print()
        return

    kind = _chain_kind(core_cmd)
    if kind == "seq":
        target = bot_label if bot_label else "blue_1"
        print(f"  -> instant Seq [{target}] (chained steps, bridge executes in order):")
        for i, seg in enumerate(CHAIN_SPLIT_RE.split(core_cmd), 1):
            print(f"     {i}. {seg.strip()}")
        print()
        return
    if kind == "waypath":
        target = bot_label if bot_label else "blue_1"
        print(f"  -> instant waypath chain [{target}] (no compiler; the executor")
        print("     drives the stops in order, holds the pauses, auto-parks):")
        for i, seg in enumerate(CHAIN_SPLIT_RE.split(core_cmd), 1):
            print(f"     {i}. {seg.strip()}")
        print()
        return
    if kind == "mixed":
        print("  -> rejected (mixed chain): chains are either moves+pauses")
        print("     (waypath) OR facing/head steps (Seq) — not both. Split:")
        print('     e.g. "face west" first, then "go to (1,1)".')
        print()
        return

    # Comma-only independent clauses: "stop, resume" = two independent calls
    comma_segs = [s.strip() for s in _COMMA_SEP_CLI_RE.split(core_cmd) if s.strip()]
    if len(comma_segs) > 1:
        print(f"  -> comma chain ({len(comma_segs)} clauses — evaluator handles")
        print("     each independently; 'then'/'next' for sequenced chains)")
        print()
        return

    if INSTANT_WORD_RE.search(core_cmd):
        print("  -> rejected (facing/head words): the 7B has no facing concept")
        print("     and would guess coordinates. Split the compound: run the")
        print('     landmark/shape task and the "face ..."/"say ..." command')
        print("     separately. Rejected evaluator-side as well.")
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
        print("  (compiler may still be processing — or the task was ignored;")
        print("   check the bot terminal for the compile/ignore message)")
    print()


print("R2K Calibration CLI — type a task and press Enter. Ctrl+C to exit.")
print('Type "help" for sample commands (pick by number).')
print()
print("Routing: bare cmds -> blue_1; camera gimbal -> \"blue_2 ...\";")
print('         "all ..." -> every blue bot; bare control -> ALL bots.')
print("Chains: \"<step>, then <step>\" sequence ONE bot; \"; \" runs parallel.")
print("Instant: control verbs, look/say, face/turn/rotate, coords.")
print("'exec <runbook>' steps a calibration runbook; 'results' shows the log.")
print("Compiler (~1-2s): landmarks, shapes, paths, patrol, ball.")
print()

show_waypoints()
print()

EXEC_BREAK_SENTINEL = "__break__"
EXEC_ABORT_WORDS = frozenset({"b", "break", "abort", "stop"})
EXEC_CONTINUE_WORDS = frozenset({"", "c", "cont", "continue", "next"})


def _detect_mode():
    """Detect sim vs field vs calib mode from active_relay.json.
    Returns 'calib' if relay has y1/y2/k1 hardware keys (R2K_CALIB=1),
    'sim' if k1_bot has sim_bot key, else 'field'."""
    relay_path = os.path.join(base_dir, 'src', 'ai_tactics', 'active_relay.json')
    try:
        with open(relay_path) as f:
            relay = json.load(f)
        mapping = relay.get('mapping', {})
        # Calib mode: hardware keys y1/y2/k1 present
        if any(k in mapping for k in ('y1', 'y2', 'k1')):
            return "calib"
        # Sim mode: k1_bot has sim_bot key
        km = mapping.get('k1_bot', {})
        if km.get('sim_bot'):
            return "sim"
    except Exception:
        pass
    return "field"


def _show_results():
    """Log-reading leg of the rehearsal: summarize calib_results.jsonl —
    one line per completed/aborted runbook (drift, auto verdict, human
    report). This is the exact flow the K1 field session will use."""
    recs = calib_test.load_results()
    if not recs:
        print("  (no results yet — run 'exec <runbook>' first)")
        print()
        return
    print(f"  {len(recs)} runbook result(s)  [calib_results.jsonl]:")
    print()
    hdr = (f"  {'when':<12s} {'runbook':<10s} {'bot':<4s} {'mode':<6s} "
           f"{'drift':>6s} {'auto':<5s} {'human':<6s} legs")
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))
    for r in recs:
        when = time.strftime('%m-%d %H:%M', time.localtime(r.get('t_wall', 0)))
        od = r.get('origin_drift_m')
        od_s = f"{od:.3f}" if isinstance(od, (int, float)) else "n/a"
        if r.get('auto_result'):
            auto = r['auto_result']
        elif r.get('aborted'):
            auto = "ABRT"
        else:
            auto = "?"
        print(f"  {when:<12s} {r.get('runbook', '?'):<10s} {r.get('bot', '?'):<4s} "
              f"{r.get('mode', '?'):<6s} {od_s:>6s} {auto:<5s} "
              f"{str(r.get('human_report') or '-'):<6s} {len(r.get('legs') or [])}")
    print()


def _exec_runbook(rb_id):
    """Interactive runbook stepper. Sends one command at a time, waits for
    Enter, reads the runbook bot's odom file, prints drift. Type b/break to
    abort safely. Persists per-leg data to calib_results.jsonl on finish AND
    break. k1 runbooks read k1_odom.json; y_* runbooks read y1_odom.json —
    SAME flow for both (K1 field-test rehearsal on the Yahbooms, 2026-09-08)."""
    steps = calib_test.RUNBOOKS[rb_id]
    bot = calib_test.RUNBOOK_BOT.get(rb_id, "k1")
    mode = _detect_mode()
    print()
    print(f"  RUNBOOK \"{rb_id.upper()}\" — {len(steps)} legs, returns to (0,0).")
    print(f"  Mode: {mode}  Bot: {bot}  [Enter=next step, b=break]")
    print()
    initial_odom = calib_test.read_odom(bot)
    print(f"  initial odom:{calib_test.fmt_odom(initial_odom)}")
    print()

    legs = []
    aborted = False
    for i, step in enumerate(steps, 1):
        print(f"  Step {i}/{len(steps)}: {step['cmd']}")
        print(f"    {step['note']}")
        inp = input("  > ")
        resp = inp.strip().lower()
        if resp in EXEC_ABORT_WORDS:
            send_task("stop")
            aborted = True
            print(f"  BREAK: aborting runbook ({i}/{len(steps)} legs done)")
            break
        if resp not in EXEC_CONTINUE_WORDS:
            pass
        send_task(step["cmd"])
        
        # For TimedMove legs (yahboom calib), prompt for manual measurement
        if step.get("prompt_measured"):
            if "angle" in step:
                meas = input("  Measured angle [deg] (Enter to skip): ").strip()
                if meas:
                    try:
                        measured = float(meas)
                        slip = measured / step["angle"] if step["angle"] != 0 else None
                        print(f"  -> slip factor: {slip:.3f}")
                        legs.append({"step": i, "cmd": step["cmd"],
                                     "commanded": step["angle"], "measured": measured,
                                     "slip_factor": round(slip, 3) if slip else None})
                    except ValueError:
                        print("  (invalid number — skipping)")
            else:
                meas = input("  Measured distance [m] (Enter to skip): ").strip()
                if meas:
                    try:
                        measured = float(meas)
                        commanded = float(step.get("cmd").split()[2])
                        slip = measured / commanded if commanded != 0 else None
                        print(f"  -> slip factor: {slip:.3f}")
                        legs.append({"step": i, "cmd": step["cmd"],
                                     "commanded": commanded, "measured": measured,
                                     "slip_factor": round(slip, 3) if slip else None})
                    except (ValueError, IndexError):
                        print("  (invalid number — skipping)")
            print()
            continue
        
        s = calib_test.read_odom(bot)
        if s:
            tx, ty = step["target"]
            drift = math.hypot(s.get('x', 0) - tx, s.get('y', 0) - ty)
            print(f"   odom:{calib_test.fmt_odom(s)}  drift {drift:.3f}m")
            legs.append({"step": i, "cmd": step["cmd"],
                         "target": [tx, ty],
                         "odom": {"x": s['x'], "y": s['y'], "theta": s.get('theta', 0)},
                         "drift_m": round(drift, 4)})
        else:
            print("   (no odom yet)")
            legs.append({"step": i, "cmd": step["cmd"],
                         "target": [step["target"][0], step["target"][1]],
                         "odom": None, "drift_m": None})
        print()

    # Build the result record
    record = {
        "type": "runbook_result",
        "t_wall": time.time(),
        "run_id": calib_test.current_run_id(),
        "runbook": rb_id,
        "bot": bot,
        "mode": mode,
        "initial_odom": {"x": initial_odom.get('x', 0), "y": initial_odom.get('y', 0),
                         "theta": initial_odom.get('theta', 0)} if initial_odom else None,
        "legs": legs,
        "aborted": aborted,
    }

    if aborted:
        record["origin_drift_m"] = None
        record["auto_result"] = None
        record["human_report"] = None
        calib_test.append_result(record)
        print()
        return

    s = calib_test.read_odom(bot)
    if s:
        od = math.hypot(s.get('x', 0), s.get('y', 0))
        thresh = calib_test.RESULT_TOL_M.get(bot, 0.15)
        auto = "PASS" if od <= thresh else "FAIL"
        print(f"  === {auto} ===  origin drift: {od:.3f}m  (threshold {thresh}m"
              f"{' — informational, rehearsal' if bot != 'k1' else ''})")
    else:
        od = None
        auto = "?"
        print("  (no odom — can't compute result)")

    inp = input("  Walk looked correct? (y/n): ").strip().lower()
    human = "OK" if inp.startswith('y') else "ISSUE"
    print(f"  Human report: {human}")
    print()

    record["origin_drift_m"] = round(od, 4) if od is not None else None
    record["auto_result"] = auto
    record["human_report"] = human
    calib_test.append_result(record)


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

        # Results summary (log reading)
        if task_stripped.lower() in ("results", "res", "result"):
            _show_results()
            continue

        # Exec runbook
        if task_stripped.lower().startswith("exec "):
            rb_id = task_stripped.lower().split(" ", 1)[1].strip()
            if rb_id not in calib_test.RUNBOOK_IDS:
                print(f"  Unknown runbook. Available: {', '.join(calib_test.RUNBOOK_IDS)}")
                print()
                continue
            _exec_runbook(rb_id)
            continue

        # Number selection from sample list
        if task_stripped.isdigit():
            idx = int(task_stripped)
            if 1 <= idx <= len(SAMPLE_COMMANDS):
                cmd = SAMPLE_COMMANDS[idx - 1]
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