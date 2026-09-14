# Standard Demo/Calib Validation Runbook

**Status:** ACTIVE | **Date:** 2026-08-30 | **Scope:** v6.6 demo/calib baseline + A2bot scope 1 — full validation before any commit.
**Method:** user executes in lab, records PASS/FAIL + numbers; defects get root-caused, fixed, fast-tested, then the case is re-run.

## Pre-flight (every phase)

1. Ollama models present: `curl -s http://127.0.0.1:11434/api/tags | jq '.models[].name'` → needs `qwen2.5:3b` (executor) + `qwen2.5:7b` (compiler)
2. Phase 1 (sim, single bot): `./launch_r2k.sh --scenario 1vs0_default --demo --relay single_bot`
3. Phase 2 (sim twins + hardware): `./launch_r2k.sh --scenario 2vs0_demo --demo --relay hardware_mirror` — both yahbooms powered; boot is QUIESCENT (no bot moves until tasked)
4. Second terminal: `python3 tools/calib_cli.py` — restart the CLI after every launch (it is a separate process)
5. Safety: `stop all bots` halts everything instantly; closing Gazebo/CTRL+C triggers the watchdog (Kinematic Freeze → pkill). Never run `kill_r2k.sh`.

## Result recording

Per case: PASS/FAIL, waypoint count, observed coords/pauses, latency feel (instant vs compile delay). FAILs: copy the CLI line + the evaluator-terminal lines into the Defect Log at the bottom.

| Case | Cmd (type exactly) | Expect | Result |
|---|---|---|---|
| **V1 Control** |
| V1.1 | `goto 3,3` / `go 0,0` | #1 moves immediately (NO "compiling" wait), CLI shows `instant Move` | |
| V1.2 | `stop` | BOTH bots halt within ~1s; CLI `[all bots]` | |
| V1.3 | `resume` | #1 continues waypath from saved index (not from start) | |
| V1.4 | `restart` | waypath replays from FIRST | |
| V1.5 | `go home` | both drive to their START (boot position) | |
| V1.6 | `"goto 1,-1"` (WITH quotes) | instant, quotes ignored, #1 moves | |
| V1.7 | `blue_2 stop` | ONLY #2 halts, #1 unaffected | |
| V1.8 | `simulated bots only` | ignored, "no actionable verb" note, nothing compiles | |
| **V2 Shapes (7B geometry)** |
| V2.1 | `draw a hexagon 2m sides` | 6 WPs, closed loop, side ≈ 2m, stays in field | |
| V2.2 | `draw a rectangle from (1,1) to (3,2)` | 4 WPs at the given corners | |
| V2.3 | `draw a square with 2m sides starting at (-2,0)` | 4 WPs, 2m sides | |
| V2.4 | `draw a triangle (0,0) (3,0) (1.5,2)` | 3 WPs at given points | |
| V2.5 | `draw a pentagon centered at (0,0) radius 2m` | 5 WPs on the r=2 circle | |
| **V3 Circles** |
| V3.1 | `trace a circle center (0,0) radius 2m` | 8–9 WPs on r=2 circle (watch for truncation!) | |
| **V4 Coords + pauses** |
| V4.1 | `go to (2, 0), then go to (2, 3)` | 2 WPs exact | |
| V4.2 | `go to -2, -3, then pause 2sec, then return` | WP at (-2,-3) with hold≈2s, then START | |
| **V5 Landmarks** |
| V5.1 | `go to the left wing` | WP at (2, 2.5) | |
| V5.2 | `go to the right wing` | WP at (2, -2.5) | |
| V5.3 | `go to own goal, then go to opponent goal` | 2 WPs: (-4.5,0) → (4.5,0) | |
| V5.4 | `go to opponent left corner, pause 3 seconds, go to own right corner` | (4.5,3) hold 3s → (-4.5,-3) | |
| **V6 Ball** |
| V6.1 | `approach the ball into kicking distance` | stops ≈0.3m from ball (up to +0.15m PD deadband) | |
| **V7 Patrols / Paths / Combos** |
| V7.1 | `patrol between (-2,0) and (2,0) three times` | alternating WPs, count 6–12 (count NOT deterministic — record actual) | |
| V7.2 | `go to (3,1) via (1,0) and (2,0)` | 3 WPs in order | |
| V7.3 | `go to (1,1), wait 2 seconds, go to (-1,1), wait 2 seconds, return` | 5 WPs, two holds ≈2s | |
| **V8 Two-bot (2vs0_demo + hardware_mirror)** |
| V8.1 | `blue_2 go to (2,0)` | **#2 moves, #1 stands** (7B prefix compile — first end-to-end) | |
| V8.2 | `blue_1 goto 2,2` | only #1, instant | |
| V8.3 | `all yahbooms goto 2,2` | BOTH bots move | |
| V8.4 | `blue_2 draw a triangle (0,0) (3,0) (1.5,2)` | #2 walks triangle, #1 stands | |
| V8.5 | `stop all bots` | both halt | |
| V8.6 | CLI `show_waypoints` after V8.1 | per-bot paths displayed (`blue_1: (no waypoints…)` / `blue_2 waypath`) | |
| **V9 Latency spot-check** |
| V9.1 | `goto 3,3` vs `go to the wing` | coord task instant; landmark task shows "compiling… done" (~0.5–1.5s) | |
| **V10 Drag-Twin (drag_twin.py, demo only)** |
| V10.1 | move sim blue_1 in Gazebo (drag fast OR slow), ~0.5m+ | `<bot> stop` on detection; after the bot holds still (~0.4s) the sim bot is teleported back to its pre-drag position and `<bot> goto <drop>` is dispatched — the twin MARCHES to the resting position (sim bot walks with it, ends at the drop as the marker) | |
| V10.2 | move sim blue_2 | #2 walks there, #1 unaffected | |
| V10.3 | drag the ball | nothing dispatched (blue bots only) | |
| V10.4 | start a waypath (e.g. hexagon), then move blue_1 | move interrupts #1's waypath, bot parks at the moved spot; other bot continues | |
| V10.5 | rapid re-move right after a drop | follow-up dispatch within ~1s suppressed (cooldown), then the twin catches up | |
| V10.6 | let a waypath FINISH (e.g. `go to (2,0)`, wait for arrival) | evaluator prints `🏁 [blue_1] waypath complete — parked`; bot stands (Hold), no further corrections | |
| V10.7 | move the bot AFTER completion | sim bot teleports back to the twin, then twin + sim march together to the moved position; no further corrections after arrival | |
| V10.8 | SLOW drag while a waypath is active | same abort as fast drags — one unified semantic: the twin always marches to the sim bot's resting position | |

## Defect Log

| # | Case | Command | Observed | Expected | Evaluator-console excerpt |
|---|---|---|---|---|---|
| | | | | | |

## V11 Yahboom Goto Rehearsal (K1 field-test prep, 2026-09-08)

**Purpose:** validate the ENTIRE K1 field-test flow on the Yahbooms (cheap,
replaceable) so the K1 session is a pure repeat. Yahbooms mirror the K1
pipeline: `odom_raw` subscription → `y1_odom.json` state file → closed-loop
Goto (bridge, ±30% encoder odom — coarse arrival BY DESIGN) → trace JSONL →
`calib_results.jsonl` → `results` reader.

**Pre-flight (Phase 0 — VERIFIED 2026-09-08):**
1. Robots powered, stack up (boot order: stack first, THEN power-cycle robots —
   the ESP32 odom frame starts at the robot's boot pose).
2. **Wake-up ritual (2026-09-08):** power-cycle each bot AT its home mark,
   **nose facing NORTH** — boot = `(0,0)` home, `yaw 0` = north (calib
   compass: east = 90° right, west = 90° left, south = 180°).
3. ~~Verify the odom source~~ **DONE:** `ros2 topic info /blue_1/odom_raw -v`
   → `nav_msgs/msg/Odometry`, publisher `YB_Car_Node` (namespace `/blue_1`)
   — matches the bridge subscription exactly.
4. **FINDING: encoder odom streams ONLY when wheels turn** (echo at rest
   times out). The goto therefore drives on the bridge-side ESTIMATE
   (calibration start pose 0,0,0 + commanded-velocity integration; every
   NEW encoder sample resyncs it — odom-as-correction, never permission).
5. Restart evaluator + bridge after any code delivery (running processes keep
   old modules — the documented pitfall).

**Launch (two postures, both validated 2026-09-08):**
```bash
# A) With sim scaffolding (world state + executor available):
./launch_r2k.sh --calib --relay hardware_yahboom --scenario 2vs0_demo
# B) Gazebo-free field stack (K1 field-test posture):
./launch_r2k.sh --nosim --relay hardware_yahboom --scenario 2vs0_demo
```
(`--calib` = direct hardware addressing — y1/y2 slots drive the physical
bots. `--nosim` implies `--calib` and drops gzserver/spawner/aggregator/
Ollama entirely: bridge ticks at 20 Hz off a wall-clock timer, evaluator
polls task_input.json directly. Same flags for the K1 field test with
`--relay hardware_mirror`.) CLI: `python3 tools/calib_cli.py`.

**Live-validated results (Y#1, 2026-09-08):**

| Run | Stack | Out (0.5 m target) | Return drift | Notes |
|---|---|---|---|---|
| …115938 | --calib (headless Gazebo) | parked 0.377 m | 6.6 cm | two-phase rotate+drive visible |
| …121143 | **--nosim** (no Gazebo) | parked 0.363 m | **3 mm** | zero errors post-fix |

Fixes found during live validation: (1) CALIB zero-clobbering — virtual
sim twins published active-brake zeros on the SAME cmd_vel topic as their
hardware twin (~50% zeros to the robot); virtual entries never publish in
CALIB now. (2) seen-then-stale deadlock — the estimator (odom-as-correction)
replaces all stale-gating for yahboom. (3) nosim `ball_pos` None crash —
dist_to_ball computed unconditionally killed every dispatch tick; guarded.

| Case | Cmd (type exactly) | Expect | Result |
|---|---|---|---|
| V11.1 | `y1 go to (0.5, 0)` | CLI: `instant Goto [y1]`; `y1_odom.json` appears + advances; Y#1 drives, parks coarse (~0.35 m) | |
| V11.2 | `y1 go to (0, 0)` | Y#1 returns; odom shows it | |
| V11.3 | `y2 go to (1, 1)` | Y#2 drives (own odom file `y2_odom.json`) | |
| V11.4 | `y1 stop` | Y#1 brakes instantly (Hold reaches the physical bot — CALIB gate fix) | |
| V11.5 | `y1 forward 0.5` | TimedMove unchanged (open-loop; tape-measure) | |
| V11.6 | `exec y_short` | Stepper: initial odom, per-leg drift, origin-drift PASS/FAIL (0.5 m informational), human y/n, record appended | |
| V11.7 | `exec y_square` | 4 legs with turns — coarse square expected (±30%); ABORT with `b` must send stop first | |
| V11.8 | `results` | Summary table lists the runbooks with drift/verdicts | |
| V11.9 | bridge log | `📍 Yahboom odom subscription active for y1 on /blue_1/odom_raw` at boot; mid-run XRCE stall = pause + auto-resume ≤60 s (NOT a freeze) | |
| V11.10 | `k1 go to (1,0)` (K1 online later) | Same flow via `odometer_state`; k1_odom.json + DAMP hint — the actual field test | |

**Reading the log (the analyze leg):**
- `cat src/logs/calib_results.jsonl | python3 -m json.tool` — raw records
  (or CLI `results` for the table).
- `src/logs/k1_trace_<run_id>.jsonl` — per-bot odom time series
  (`{"t_wall", "t_odom", "bot", "pose", "target"}`), joins with world_trace
  by `t_wall`.

**Non-goals (do not "improve" the Yahboom side):** no drift-calibration
campaign, no vision/yaw fusion, no matches-mode twin. ±30% is accepted; the
rehearsal value is exercising the pipeline, not accuracy.

## Watch items (known suspects from the 2026-08-30 probe)

- V3.1 / V7.1: `num_predict 400` ceiling — 12+ WP outputs may truncate → parse fail or cut-off path
- V4.2 / V7.3: `hold_duration` + `resume` interplay never lab-tested (resume holds fresh timer?)
- V8.1/V8.4: 7B prefix semantics first live exercise — watch that the prefix does not leak into compiled coords
- V1.5: `go home` uses per-bot captured START (boot position), not (0,0)
