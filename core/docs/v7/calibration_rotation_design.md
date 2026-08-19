# v7 Calibration: Rotation / Facing Design (Option D)

> **Date:** 2026-08-19
> **Status:** Design note — not yet implemented
> **Scope:** Demo/calibration mode only; soccer unaffected

## Problem

"rotate", "turn left", "face north" — none of these work in the current
calibration CLI. The 7B compiler has no heading (yaw) information and
the bridge has no rotation command. The compiler falls back to outputting
(0, 0) or garbage, and the bot drives to START instead of turning.

## Why yaw isn't in Worldstate

`tracker_node.py:34-38` extracts only `position.x` and `position.y` from
`/gazebo/model_states` — it discards the orientation quaternion. This is a
deliberate design choice (Axiom 2: "2D-Reduktion ohne Z/Pitch/Roll").
Adding yaw to the tracker requires a `colcon build` inside Docker —
deferred to v7 (scrum Task 3a: "Add gaze direction to Worldstate.json").

## Option D: Bridge has yaw — no Worldstate change needed

The bridge (`ollama_sandbox_bridge.py`) already subscribes to
`/gazebo/model_states` and computes `cyaw = get_yaw(bot_pose.orientation)`
at line 192 for every bot, every tick. It uses yaw for kick direction
aiming and PID angle control — but never exposes it to the evaluator
or writes it to `Worldstate.json`.

**Key insight:** the bridge HAS the current yaw. It just doesn't
accept a "turn to yaw X" command. We can add a `Face` action to the
bridge without any tracker/Worldstate/colcon changes.

## Design

### New action: `Face`

The evaluator writes a `Face` action to `current_strategy.json`:

```json
{"assignments": {"blue_1": {"action": "Face", "yaw": 1.5708}}}
```

or relative:

```json
{"assignments": {"blue_1": {"action": "Face", "relative_angle": 1.5708}}}
```

### Bridge handling (in `state_cb`, after Hold check, before Move/Kick)

```python
if action == 'face':
    target_yaw = target.get('yaw', 0.0)
    if 'relative_angle' in target:
        target_yaw = cyaw + float(target['relative_angle'])
    # normalize target_yaw to [-pi, pi]
    while target_yaw > math.pi: target_yaw -= 2 * math.pi
    while target_yaw < -math.pi: target_yaw += 2 * math.pi
    angle_diff = target_yaw - cyaw
    while angle_diff > math.pi: angle_diff -= 2 * math.pi
    while angle_diff < -math.pi: angle_diff += 2 * math.pi
    if abs(angle_diff) < 0.1:
        # arrived at target heading — active brake
        lin_x, ang_z = 0.0, 0.0
    else:
        ang_z = max(min(angle_diff * 3.0, 2.0), -2.0)
        lin_x = 0.0  # turn in place — no forward motion
    # publish to virtual (Twist), yahboom (Twist), k1 (RPC 2001)
```

The bot turns in place. No position change. When `abs(angle_diff) < 0.1`
(~6 degrees), the bot stops turning.

### Evaluator fast-path commands (no compiler call)

```python
# Absolute facing
if task_text.startswith("face "):
    direction = task_text[5:].strip()
    yaw_map = {
        "north": 1.5708,    # +Y
        "south": -1.5708,   # -Y
        "east": 0.0,        # +X (toward opponent goal)
        "west": 3.1416,     # -X (toward own goal)
        "opponent goal": 0.0,
        "own goal": 3.1416,
        "left": 1.5708,    # same as north
        "right": -1.5708,   # same as south
    }
    if direction in yaw_map:
        _write_face_strategy(yaw_map[direction])
        return

# Relative turns
if task_text.startswith("turn "):
    direction = task_text[5:].strip()
    rel_map = {"left": 1.5708, "right": -1.5708, "around": 3.1416}
    if direction in rel_map:
        _write_face_strategy_relative(rel_map[direction])
        return

# Rotate by degrees
if task_text.startswith("rotate "):
    try:
        degrees = float(task_text[7:].replace("degrees", "").replace("deg", "").strip())
        _write_face_strategy_relative(math.radians(degrees))
        return
    except: pass
```

### Supported commands

| Command | Type | Effect |
|---|---|---|
| `face north` | absolute | Turn to face +Y (yaw = π/2) |
| `face south` | absolute | Turn to face -Y (yaw = -π/2) |
| `face east` | absolute | Turn to face +X (yaw = 0) |
| `face west` | absolute | Turn to face -X (yaw = π) |
| `face opponent goal` | absolute | Turn to face +X |
| `face own goal` | absolute | Turn to face -X |
| `turn left` | relative | Turn 90° counterclockwise |
| `turn right` | relative | Turn 90° clockwise |
| `turn around` | relative | Turn 180° |
| `rotate 90` | relative | Turn 90° counterclockwise |
| `rotate -45` | relative | Turn 45° clockwise |
| `rotate 180` | relative | Turn 180° |

### Not supported (needs v7 yaw in Worldstate)

| Command | Why |
|---|---|
| `face the ball` | Needs ball position + current heading to compute angle to ball. The bridge has yaw but the evaluator's fast-path doesn't have ball position in the task_input.json flow. Could be added by reading ball from Worldstate in the fast-path. |
| `turn left 45 degrees` | Parse edge case — could be handled with better regex |

### Hardware compatibility

- **Virtual (Gazebo):** `Twist(linear.x=0, angular.z=ang_z)` — turns in place
- **Yahboom:** same Twist — differential drive turns in place
- **K1:** `RpcReqMsg(api_id=2001, vx=0, vy=0, vyaw=ang_z)` — biped rotates
- All three already supported by the bridge's existing publish logic

### What does NOT change

- `tracker_node.py` — no yaw added to Worldstate (deferred to v7 Task 3a)
- `state_aggregator.py` — no change
- `Worldstate.json` schema — no change
- Soccer mode — `Face` action only written by demo-mode fast-path
- Colcon build — not needed (bridge is standalone Python)

### Implementation effort

| Component | File | Lines | Colcon build? |
|---|---|---|---|
| Bridge Face handling | `ollama_sandbox_bridge.py` | ~20 | No |
| Evaluator fast-path | `r2k_evaluator.py` | ~25 | No |
| CLI help text | `tools/calib_cli.py` | ~5 | No |
| Cheat sheet | `docs/calibration_cheat_sheet.md` | ~10 | No |
| **Total** | 4 files | ~60 lines | No |

### Relation to v7 Task 3a

Task 3a ("Add gaze direction to Worldstate.json") would add yaw to the
tracker output. This is a **separate concern** — it would let the
**evaluator/compiler** see the bot's heading (enabling "face the ball"
and smarter path planning). But the bridge already has yaw for its own
use. Option D works without Task 3a.

If Task 3a is implemented later, the Face action still works the same
way — the bridge reads yaw from Gazebo directly, not from Worldstate.
The only benefit of Task 3a for calibration is enabling the compiler
to know the bot's current heading for relative commands and ball-facing.