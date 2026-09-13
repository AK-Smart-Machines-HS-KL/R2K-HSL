# R2K Calibration CLI — Command Cheat Sheet

## Quick Start

**Terminal 1 — start the bot (Gazebo GUI, no matplotlib visualizer):**
```bash
cd ~/R2K-HSL/core
./launch_r2k.sh --demo --no-visualizer --scenario 1vs0_default --relay single_bot
```

**Two-bot (hardware mirror, K1 follows blue_1):**
```bash
./launch_r2k.sh --demo --no-visualizer --scenario 2vs0_demo --relay hardware_mirror
```

**Yahboom rehearsal (both Yahbooms, no K1 topics while K1 is offline):**
```bash
./launch_r2k.sh --calib --relay hardware_yahboom --scenario 2vs0_demo
```
(`--calib` = direct hardware addressing: `y1`/`y2` slots drive the physical
bots; Gazebo runs headless — the sim twins still spawn and feed the world
state. Same flag for the later K1 field test with `--relay hardware_mirror`.)

**Gazebo-free field stack (K1 field-test posture, validated 2026-09-08):**
```bash
./launch_r2k.sh --nosim --relay hardware_yahboom --scenario 2vs0_demo
```
(`--nosim` implies `--calib`. No gzserver, no spawner, no aggregator, **no
Ollama** — bridge (20 Hz wall-clock hw tick) + evaluator (direct
task_input poll) + micro-ROS agent only, ~15 s boot, no GPU. Works on a
laptop without Ollama installed. Vocabulary is hardware-only: `yN/k1 go to
(x,y)`, `yN forward/back/turn`, control verbs, `exec`, `results` —
landmarks/shapes/waypaths are demo-mode features (they target sim bots).
Boot order still applies: stack up FIRST, then power-cycle the robots.)

**Drag-Twin (demo only):** grab a blue sim bot in Gazebo and drag it — on release,
its hardware mirror walks to the drop point (`blue_1` → Yahboom #1 + K1 via relay
mirror, `blue_2` → Yahboom #2). Dragging interrupts that bot's waypath. Other
bots unaffected; the ball is ignored.

**Terminal 2 — interact:**
```bash
cd ~/R2K-HSL/core
python3 tools/calib_cli.py
```

Type a command and press Enter. The CLI shows the generated waypath.
`Ctrl+C` to exit the CLI.

**Tip:** Type `help` in the CLI to see numbered sample commands.
Type a number (e.g. `3`) to send that command directly — no typing needed.

## Instant Control Commands (no compiler delay — <20ms)

| Command | Aliases | Effect |
|---------|---------|--------|
| `stop` | `break`, `exit`, `halt` | Bot halts immediately, stays where it is |
| `resume` | `continue` | Recover from stop, follow remaining waypath |
| `restart` | `redo`, `repeat`, `re-start` | Replay waypath from the beginning |
| `go home` | `return`, `home`, `go to start`, `return to start` | Drive to START position (0, 0) |

## Sequences & Body Gestures (instant — bridge-executed, 2026-09-05)

**Sequences** (`", then"` / `", next"`; `"; "` stays PARALLEL clauses; one
bot per chain, prefix at chain start, else **blue_1**):

- **MOVE chains** → **waypath** (the proven machinery — drag_twin-safe, no
  new motion code): `"go to 2,2, then pause 2sec, then go to 3,3"` →
  waypoints `[(2,2) 2s hold] → [(3,3)]`, auto-park at the end. `goto` ==
  `go to`. A leading pause (`"pause 1s, then go to (2,0)"`) holds at the
  bot's current position first.
- **FACING chains** → bridge-executed Seq (the only component observing
  yaw + position + time): `"face west, then say no"` — steps `face/turn/
  rotate/look/say/pause`.
- **MIXED facing+move** → rejected with guidance: split into two commands.
- Facing/head words (`face|turn|rotate|look|say`) never reach the 7B
  compiler (it would guess coordinates for them); landmark/shape
  compounds without them compile normally.

**Say-gestures per robot** (Y#1 has no gimbal — its gestures run on the
chassis; servo publishes to it are harmless, no connected load):

| Command | Y#1 (blue_1) | K1 (mirror) | Y#2 camera (`blue_2 …`) |
|---|---|---|---|
| `say no` | body yaw shake ±20° @ 2 Hz (3 cycles, returns to base) | head shake via RPC 2004 | pan shake ±40° @ 2 Hz |
| `say yes` | body bob (3 forward-back surges, slight drift OK) | head nod via 2004 | tilt bows (one-sided) |

**Move arrival latch** (fixes the endgame PD limit cycle — constant
`lin_x=0.8` at 10 Hz overshot the 0.15 m band forever, "dog going to
sleep"): within 0.15 m the bot latches parked; only displacement >0.4 m
re-engages the drive. Direct `go to (x,y)` / `go home` are single-step
sequences → auto-park.

**Routing (uniform)**: ALL bare commands → **blue_1**; camera gimbal
(look/say on the PTZ) → explicit `blue_2 …`; bare control verbs → fleet.

## Model Capabilities

Two models work together:
- **qwen2.5:3B** (2 GB) — the **executor**: per-cycle string→coordinate lookup (~650ms). Always running.
- **qwen2.5:7B** (5 GB) — the **compiler**: one-shot NL→waypoint list (~1.2s). Called on each new task.

| Category | 3B pass rate | 7B pass rate | Recommendation |
|---|---|---|---|
| **Landmarks** | 7/10 (70%) | 9/10 (90%) | Both work. 7B more reliable. |
| **Shapes** | 4/5 (80%) | 5/5 (100%) | 7B for hexagon, pentagon |
| **Coords** | 2/3 (67%) | 3/3 (100%) | 7B for single-point tasks |
| **Circles** | 1/1 (100%) | 1/1 (100%) | Both work |
| **Paths** | 1/1 (100%) | 1/1 (100%) | Both work |
| **Patrol** | 1/1 (100%) | 0/1 (0%) | 3B! 7B may parse-fail |
| **Ball** | 0/1 (0%) | 1/1 (100%) | 7B only (reads ball position) |
| **Combos** | 1/2 (50%) | 1/2 (50%) | Both unreliable on long tasks |
| **Control** | 2/2 (100%) | 1/2 (50%) | Use fast-path commands instead |

**Key takeaways:**
- Simple tasks (coords, landmarks, shapes, circles, paths) work on **both** models.
- "approach the ball" needs the **7B** (reads ball position from world state).
- "patrol N times" works on **3B** but may fail on **7B** (parse error).
- Complex combos (5+ waypoints with pauses + return) are **unreliable on both**.
- "return" / "go home" as standalone commands use the **fast-path** (instant, no model).
- Latency: 3B ~0.8s, 7B ~1.2s per compilation.

## Field Orientation

**From Blue's POV** (standing at own goal, looking toward opponent goal):

```
       Y=+3  ┌──────────────────────────────────────────────────┐
              │  own left corner            opponent left corner  │
   LEFT       │  (-4.5, +3)                 (+4.5, +3)            │   RIGHT
   (Y > 0)   │                                                    │  (Y < 0)
              │                  left wing   right wing            │
              │                  (2, +2.5)  (2, -2.5)              │
              │                                                    │
              │           center (0, 0)    ← START position        │
              │                                                    │
              │  own goal                   opponent goal          │
              │  (-4.5, 0)                  (+4.5, 0)              │
              │                                                    │
              │  own right corner           opponent right corner  │
       Y=-3  │  (-4.5, -3)                 (+4.5, -3)             │
              └──────────────────────────────────────────────────┘
              X=-4.5 (OWN)                        X=+4.5 (OPPONENT)
```

- **Left** = positive Y. **Right** = negative Y.
- **Own goal** = X=-4.5. **Opponent goal** = X=+4.5.
- **Left wing** = (2, 2.5) — left side in opponent half (Y positive).
- **Right wing** = (2, -2.5) — right side in opponent half (Y negative).
- Bot starts at **center (0, 0)**. Ball spawns at **(1, 1)**.

## Landmarks

| Name | Position | Description |
|------|----------|-------------|
| center | (0, 0) | Field center, START position |
| left wing | (2, 2.5) | Left side in opponent half (Y positive) |
| right wing | (2, -2.5) | Right side in opponent half (Y negative) |
| wing | (2, 2.5) | Default = left wing |
| own goal | (-4.5, 0) | Blue's own goal |
| opponent goal | (4.5, 0) | Opponent's goal |
| own left corner | (-4.5, 3) | Left side of own goal |
| own right corner | (-4.5, -3) | Right side of own goal |
| opponent left corner | (4.5, 3) | Left side of opponent goal |
| opponent right corner | (4.5, -3) | Right side of opponent goal |
| corner | (-4.5, 3) | Default = own left corner |
| left corner | (-4.5, 3) | Default = own left corner |
| right corner | (-4.5, -3) | Default = own right corner |

## Coordinates

| Command                                      | 3B  | 7B  | Notes                   |
| -------------------------------------------- | --- | --- | ----------------------- |
| `go to (2, 0)`                               | ⚠️  | ✅   | Single point            |
| `go to (2, 0), then go to (2, 3)`            | ✅   | ✅   | Two points              |
| `go to -2, -3, then pause 2sec, then return` | ✅   | ✅   | Coords + pause + return |

## Shapes

| Command                                          | 3B  | 7B  | Notes             |
| ------------------------------------------------ | --- | --- | ----------------- |
| `draw a rectangle from (1,1) to (3,2)`           | ✅   | ✅   | 4 corners         |
| `draw a square with 2m sides starting at (-2,0)` | ✅   | ✅   | Square            |
| `draw a triangle (0,0) (3,0) (1.5,2)`            | ✅   | ✅   | Explicit vertices |
| `draw a hexagon 2m sides`                        | ⚠️  | ✅   | Hexagonal path    |
| `draw a pentagon centered at (0,0) radius 2m`    | ✅   | ✅   | Pentagon          |

## Circles

| Command | 3B | 7B | Notes |
|---------|-----|-----|-------|
| `trace a circle center (0,0) radius 2m` | ✅ | ✅ | 8-13 points around circle |

## Paths & Patrols

| Command | 3B | 7B | Notes |
|---------|-----|-----|-------|
| `patrol between (-2,0) and (2,0) three times` | ✅ | ⚠️ | 6 waypoints alternating |
| `go to (3,1) via (1,0) and (2,0)` | ✅ | ✅ | Via-points |

## Landmark Navigation

| Command | 3B | 7B | Notes |
|---------|-----|-----|-------|
| `go to the left wing, pause 2 seconds, go to the right wing` | ✅ | ✅ | Left = Y+, right = Y- |
| `go to center, then go to own goal` | ✅ | ✅ | Center to own goal |
| `go to opponent left corner, pause 3 seconds, go to own right corner` | ⚠️ | ✅ | Corner to corner |
| `go to own goal, then go to opponent goal` | ✅ | ✅ | Full field traversal |
| `go to the wing` | ⚠️ | ✅ | Default = left wing |
| `go to the corner` | ✅ | ✅ | Default = own left corner |

## Ball Interaction

| Command | 3B | 7B | Notes |
|---------|-----|-----|-------|
| `approach the ball into kicking distance` | ⚠️ | ✅ | Reads ball position, approaches to 0.3m |

## Pauses & Combinations

| Command | 3B | 7B | Notes |
|---------|-----|-----|-------|
| `go to (1,1), wait 2 seconds, go to (-1,1), wait 2 seconds, return` | ✅ | ⚠️ | Multi-pause + return |
| `go to (3,0), pause 3 seconds, draw a triangle (0,0)(2,0)(1,2), return` | ⚠️ | ✅ | Complex combo |

## Return

| Command | 3B | 7B | Notes |
|---------|-----|-----|-------|
| `return` | ✅ | ✅ | Instant (fast-path) — drives to START (0, 0) |
| `go home` | ✅ | ✅ | Instant (fast-path) — same as "return" |
| `...then return` (embedded) | ✅ | ✅ | Compiler translates to START coords |

## Not Yet Available (v7)

*(Face/turn/rotate ARE implemented — see "Sequences & Body Gestures" above.
This table only lists genuinely unavailable commands.)*

| Command | Why | v7 plan |
|---|---|---|
| Relative motion ("forward 3m", "turn left" as movement) | No bot yaw in the Worldstate — the compiler would guess. Calib exception: `yN forward/back/turn` = open-loop TimedMove (timed, operator measures). | v7 Task 3a: tracker yaw |
| Bot yaw in the Worldstate model | Tracker change required | v7 Task 3a |

## Hardware Closed-Loop Goto & Runbooks (2026-09-08)

**Calib = the lean field stack (mode merge):** `--calib` boots bridge +
evaluator + micro-ROS agent ONLY (no Gazebo, no aggregator, no Ollama,
~15 s). `--nosim` is an alias. The vocabulary is **frozen** — anything else
is demo-mode and rejected with the list:

| Command | Effect |
|---|---|
| `y1 go to (0.5, 0)` | Closed-loop drive on the bot's own odom (estimator: encoder-resynced, dead-reckoned between samples) |
| `k1 go to (1, 0)` | Closed-loop on `odometer_state` (490 Hz, vendor two-phase recipe) — **first real-K1 validation 2026-09-08** |
| `y1 go to home` / `y1 return` | Instant `Goto(0,0)` — home = **the power-cycle spot** (odom origin) |
| `y1 face east/north/south/west` | Body turn-in-place on the estimator yaw (0.5 rad/s cap) |
| `y1 say yes` / `say no` | Body gesture (bob / yaw-shake) — estimator yaw is the shake base |
| `y1 forward 0.5` / `y1 back 0.3` | Open-loop TimedMove — id-keyed, no repeat; **tape-measure** (distance can't close the loop: wheel slip) |
| `y1 turn 45` (`o`/`°` ok) | **Closed-loop on odom yaw** — **+ = clockwise/right** (compass convention: nose north, `turn 90` → nose east). Cap 1.2 rad/s (steady-state delivers ~0.9×; short turns lose a beat to motor spin-up) |
| `y1 say no` | **Seq of closed-loop shake swings** (±20°, 2 cycles, ~0.6-0.7 s per swing) — oscillating vyaw *cancels* in the board yaw PID, so the shake is built from the proven turn machinery. `y1 say yes` = body bob (vx). y2's `say` uses its camera pan/tilt |
| `y1 stop` / `stop` | Instant brake (per-bot / whole fleet) |
| `exec <runbook>` / `results` | Runbook stepper + calib_results.jsonl summary |

The CLI prints **what the bot believes** on goto/home/face commands
(`bot believes: (+0.12,−0.05) yaw +0.31 — 0.43 m to target`), and says
`ALREADY THERE` when the target is inside the deadband — a no-op is now
distinguishable from a failure.

**The wake-up ritual (calibration contract, 2026-09-08):** power-cycle the
bot **at the home mark, nose facing NORTH**. Boot state = `(0, 0)` home +
`yaw 0` = north. Compass in calib: `face north` = rest (no-op at boot),
`face east` = 90° **right** (clockwise), `face west` = 90° left, `face
south` = 180°. After a power-cycle anywhere else, that spot becomes home —
`y1 go to home` returns there.

**`say no` note:** the chassis shake runs at a slower calib profile
(±45° @ 1 Hz — ±14° swings at the 0.5 rad/s cap). The demo profile
(±100° @ 2 Hz) alternates faster than the board's yaw PID can reverse, so
it averaged to zero rotation (live 2026-09-08: armed + published, no
movement). Demo mode keeps the fast profile.

**Rear targets drive backward** (bearing > 135°) instead of turning 180°;
arrival is **distance-only for both hardware types** — park-range bearings
are geometric noise, and the former K1 heading term caused an endless
arrival spin on the real K1 (live 2026-09-08). Park orientation is not part
of the calib contract.

**Closed-loop Goto** (instant, no compiler — the bridge drives on the bot's
own odometry):

| Command | Effect |
|---|---|
| `k1 go to (1, 0)` | K1 drives via `odometer_state` odom (~0.2 m arrival) |
| `y1 go to (0.5, 0)` | Yahboom #1 drives via `odom_raw` (encoder, ±30% — **coarse arrival by design**, ~0.35 m deadband) |
| `y2 go to (1, 1)` | Same for Yahboom #2 |

State files (0.5 s cadence): `shared_state/k1_odom.json`, `y1_odom.json`,
`y2_odom.json`. Trace: `logs/k1_trace_<run_id>.jsonl` (per-bot records,
`"bot"` key). If odom goes silent, the bot **brakes and waits** (safe stop).

**Blind-start (calibration contract):** Yahboom encoder odom streams ONLY
when wheels turn — a goto on a freshly booted bot (no odom yet) drives
assuming the start pose (odom-frame origin 0, 0, yaw 0; place the bot at a
marked start before powering it) and self-corrects as soon as odom arrives.
No odom within 4 s (`Y_GOTO_BLIND_START_S`) → brake. Later (v7+): external
start pose (e.g. K1 camera) may refine this — not yet.

**Open-loop TimedMove** (calib verbs): `yN forward/back 0.5`,
`yN turn 90` (suffix `deg`/`°`/`o` tolerated) — bridge owns the clock,
operator measures with a tape.

**Hardware face + home (2026-09-08):**

| Command | Effect |
|---|---|
| `y1 face east` / `face south` / `face west` / `face north` | Body turn-in-place on the bot's OWN yaw (estimator — encoder-resynced; sim pose no longer needed in calib) |
| `y1 go to home` / `y1 return` / `y1 home` / bare `return` | Instant `Goto(0,0)` — the calibration start pose IS the odom origin (no 7B compile; the compiled waypath drove nothing on hardware) |
| `y1 turn 45` / `turn 45o` / `turn -90°` | Open-loop TimedMove turn (+ = CCW, ~0.5 rad/s) |

**Bare-command routing reminder:** in calib, bare `go to (x,y)` targets the
K1 slot (field-first default — dead while K1 is offline). Prefix `y1`/`y2`.
Bare `stop` halts the whole fleet instantly.

**Runbook executor + results reading** (the K1 field-test flow):

| Command | Effect |
|---|---|
| `exec short` / `square` / `triangle` | K1 goto runbook — stepper prints per-leg odom + drift, PASS threshold 0.15 m |
| `exec y_short` / `y_square` / `y_triangle` | Yahboom #1 rehearsal runbooks — same flow, threshold 0.5 m (informational, ±30% odom) |
| `exec y_line` / `y_turns` | Open-loop TimedMove runbooks (manual tape measurement) |
| `results` | Prints the `calib_results.jsonl` summary table (per-runbook drift, auto verdict, human report) |

**Known caveat (vendor firmware):** the ESP32 micro-ROS client stalls
stochastically under sustained load (~1 per several minutes); the bridge's
drain-gaps + stall-breaker convert this into a ≤60 s hiccup — the bot pauses
and the runbook continues after recovery.

## Tips

- **"return" and "go home" as standalone commands are instant** — no compiler delay.
- **The 7B compiler takes ~1-2 seconds** for path tasks. The CLI shows "compiling..." while waiting, then displays the generated waypath.
- **Explicit coordinates work best.** The more specific you are, the less the model has to interpret.
- **Use landmark names exactly** as listed above — the compiler looks up the LANDMARKS table for exact coordinates.
- **"wing" defaults to left, "corner" defaults to own left** — no need to type "own left" every time.
- **Circles are approximate.** The model outputs 8-13 points — the bot follows a polygon, not a smooth arc.
- **Field limits:** X ∈ [-4.5, 4.5], Y ∈ [-3.0, 3.0].
- **"pause N seconds"** stops the bot at its current position for N seconds, then continues.
- **3B vs 7B:** the 3B is the executor (per-cycle, always running). The 7B is the compiler (one-shot per task). Both are loaded in VRAM simultaneously (7 GB total).