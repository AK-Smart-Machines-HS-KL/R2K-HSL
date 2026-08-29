# R2K Calibration CLI — Command Cheat Sheet

## Quick Start

**Terminal 1 — start the bot (Gazebo GUI, no matplotlib visualizer):**
```bash
cd ~/R2K-HSL/core
./launch_r2k.sh --demo --no-visualizer --scenario 1vs0_waypoint --relay single_bot
```

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

| Command | Why | v7 plan |
|---|---|---|
| `face north` / `face south` | Bridge has no `Face` action | Option D: bridge reads yaw from Gazebo |
| `turn left` / `turn right` | Same — needs rotation command | Option D: relative angle in bridge |
| `rotate 90` | Same | Option D: degrees → radians |
| `face opponent goal` | Same | See `docs/plans/v68_pre_ifa/calibration_rotation_design.md` |

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