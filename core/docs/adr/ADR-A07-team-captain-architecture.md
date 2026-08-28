# ADR-A07: Extended ROS2K Architecture — TeamCaptain, Watchdog, and Motion Planning

**Date:** 2026-08-05
**Status:** Proposed (for v7 — not implemented in v6.4)

## Glossary

| Term | Meaning |
|---|---|
| **Bridge** | `ollama_sandbox_bridge.py` — the ROS 2 node that translates LLM output into robot commands. Runs at 10Hz. Contains the PD controller, goalie blending, anti-collision, and kick logic. |
| **Evaluator** | `r2k_evaluator.py` — the standalone Python daemon that polls Worldstate.json, calls the LLM via Ollama REST API, and writes current_strategy.json. |
| **TeamCaptain** | A proposed new ROS 2 node (CPU-only) that sits between the evaluator and the bridge. Takes LLM intent (end-points + meta parameters) and produces optimized per-bot execution plans (waypoints, speed, arrival yaw). Also serves as watchdog. |
| **Path executor** | A shared Python module (`ai_tactics/path_executor.py`) that interpolates waypoints from current position to target and outputs velocity commands. Used by both the calibration script (standalone) and TeamCaptain (production). |
| **Phantom kick** | The bridge teleports the ball via `/gazebo/set_entity_state` with velocity — sim-only kick mechanism. |
| **Inter-lingua** | The controlled-vocabulary instruction language the LLM outputs: "blue_2 move to (2.0, 0.5)", "blue_1 kick". The LLM never knows about the bridge, ROS2, cmd_vel, or RPC. |

## Context

### Current architecture (v6.4)

```
LLM (evaluator, ~300-700ms, GPU)
  → current_strategy.json (flat JSON on tmpfs)
  → Bridge (10Hz, PD controller)
  → cmd_vel (sim) / RPC 2001 (K1)
  → bots
```

The bridge currently handles:
- PD velocity control (drive toward LLM target)
- Goalie blending (override LLM goalie target with tactical positioning)
- Anti-collision push (separate bots when within 0.5m)
- Kick triggering (phantom kick for sim, kShoot/kVisualKick for K1)
- Kick direction override (goalie always kicks toward +X)

These are all **motion planning** concerns crammed into a **command parser**. The bridge does two jobs: parse LLM output AND plan motion. This violates separation of concerns.

### Problems with the current architecture

1. **Clustering persists** — the bridge's anti-collision push is a 1m shove, not a coordinated plan. Bots re-converge after the push.

2. **Goalie gets stuck** — the PD controller can't drive the goalie back to X=-4.0 after it's pushed to X=-2.6 by physics. The goalie blending (goal-line mode) is a workaround, not a solution.

3. **K1 kick is autonomous** — `kShoot` (2024) and `kVisualKick` (2038) take over the K1. If the ball moves, the K1 chases indefinitely. No abort mechanism exists.
   > **GATE 0 (2026-08-28):** this premise is UNVERIFIED — no vendor doc or logged hardware session supports the chase claim; vendor notes Shoot's motion is currently T1-provided (may fail on K1) and VisualKick needs firmware ≥ v1.5.2.1. The kick-abort responsibility in this ADR is blocked on the probe in `docs/v7/k1_kick_head_vendor_audit.md` (incl. the firmware Soccer-mode alternative, `RobotMode::kSoccer=4`).

4. **No arrival angle** — the PD controller drives the bot to (X, Y) but doesn't care about the final heading. The bot arrives facing whatever direction it was driving, requiring post-arrival rotation.

5. **No risk awareness** — the bridge doesn't know about fall risk (K1 biped), servo heating, or collision risk. It drives at full speed regardless.

6. **No multi-bot coordination** — the bridge processes each bot independently. It can't plan "blue_2 goes left, blue_3 goes right, they don't cross paths."

7. **No odometry feedback** — the bridge doesn't know if a bot actually reached its target. It just keeps publishing velocity. On real hardware (Yahboom, K1), odometry drift means the bot may be elsewhere than the tracker thinks.

8. **No augmented world model** — the LLM sees raw positions. It doesn't see free pathways, sweet spots, or risk zones. A 3B model can't compute these from raw positions.

## Decision

### Introduce TeamCaptain as an intermediate processing unit

```
LLM (evaluator, ~300-700ms, GPU)
  → current_strategy.json (LLM intent: end-points + meta params)
  → TeamCaptain (CPU, ~10-50ms)
  → optimized_path.json (waypoints, speed, yaw, watchdog status)
  → Bridge (10Hz, executor)
  → cmd_vel (sim) / RPC 2001 (K1)
  → bots
       ↓
  Odometry (via ROS2 topics)
       ↓
  TeamCaptain (compares planned vs actual → watchdog)
```

### TeamCaptain responsibilities

1. **Path computation** — takes LLM end-point per bot, interpolates waypoints, outputs velocity-compatible targets for the bridge. The bridge's PD controller stays — it just reads optimized waypoints instead of raw LLM targets.

2. **Hardware-aware planning** — uses per-bot capability profiles:
   - K1: holonomic walk, fall risk, deceleration needed, kick via kShoot (autonomous, needs abort)
   - Yahboom: differential drive (rotate-then-drive), kick via metal-front push (untested), pan-tilt cam (lousy)
   - Trailer: non-holonomic (car-like), no rotation in place, no kick, no camera
   - Sim: perfect odometry, phantom kick, holonomic

3. **Multi-bot coordination** — sees all 3 bots' targets simultaneously. Plans non-colliding trajectories. Replaces the bridge's hacky anti-collision push.

4. **Augmented world model** — computes free pathways, sweet spots, and risk zones. Injects these into the world state the LLM sees. The 3B model gets richer input without more computation.

5. **Watchdog** — receives odometry from bots via ROS2. Compares actual position vs planned trajectory. If divergence exceeds threshold:
   - Sends failsafe commands (stop bots)
   - Feeds actual positions into the predicted world model
   - Triggers LLM re-prompt with updated world state
   - No hard-wired thresholds or hysteresis — TeamCaptain decides based on context

6. **Kick abort** — listens for ball motion change (published by K1's camera). When ball velocity/direction changes during a K1 kick chase:
   - Sends `kChangeMode` (2000) to abort the autonomous kick skill
   - Bot is free for next LLM assignment

7. **Risk-adjusted scoring** — feeds fall probability, collision risk, and time-to-target into the score function. Score becomes a "team health" indicator, not just ball position.

### What TeamCaptain does NOT do

- **Does not replace the LLM** — the LLM still makes tactical decisions (what to do). TeamCaptain executes them (how to move).
- **Does not replace the bridge** — the bridge still parses inter-lingua and publishes cmd_vel/RPC. TeamCaptain feeds the bridge optimized targets.
- **Does not use GPU** — runs on CPU only. No contention with the LLM.
- **Does not use Nav2** — home-grown Python path interpolation. Nav2 is overkill for a flat field with few obstacles. May be evaluated in the future.
- **Does not contain meta-knowledge in the LLM prompt** — the LLM never knows about TeamCaptain, path planning, waypoints, or odometry. It outputs intents ("blue_2 move to (2.0, 0.5)"); TeamCaptain handles the rest.

### Downward compatibility

| Mode | LLM | TeamCaptain | Bridge | Calibration script |
|---|---|---|---|---|
| Calibration | ❌ | ❌ | ❌ | ✅ (standalone, uses path_executor.py) |
| Current v6.4 | ✅ | ❌ | reads current_strategy.json | — |
| Future v7 | ✅ | ✅ (CPU) | reads optimized_path.json (fallback: current_strategy.json) | — |

The calibration script (`tools/calibrate_bot.py`) uses `path_executor.py` directly — the same module TeamCaptain uses. When TeamCaptain is added in v7, the calibration script already has the shared path executor. No rework.

The bridge reads `optimized_path.json` when TeamCaptain is active. If `optimized_path.json` is stale (>2s old) or missing, the bridge falls back to `current_strategy.json`. No breaking change.

### Demo/Calibration prompt

A third prompt mode (`--demo`) for human-driven bot control:
- Human types commands ("blue_2 move to (1.0, 0.5)")
- LLM reformats into inter-lingua (same format as match mode)
- Same evaluator → bridge pipeline (tests full stack)
- No tactical reasoning, no Expert/Oracle — pure command relay
- Dual-use: workshop demos (visitors "drive" a robot) + calibration (K1 follows waypoints, tester measures)
- JSON + calibrate_bot.py remains as fallback when LLM is down

The demo prompt contains **no meta-knowledge** — no mention of bridge, cmd_vel, RPC, path executor, or ROS2K internals. The LLM sees positions and outputs instructions.

## Hardware capability matrix (per-bot, not per-team)

| Capability | K1 (biped) | Yahboom (cam variant) | Yahboom (standard) | Trailer | Gazebo (sim) |
|---|---|---|---|---|---|
| Kick | ✅ (kShoot 2024, autonomous chase) | ✅ (metal push, untested, short range) | ✅ (metal push, untested) | ❌ | ✅ (phantom kick) |
| Move sideways | ✅ | ❌ (diff-drive) | ❌ | ❌ | ✅ |
| Rotate in place | ✅ | ✅ | ✅ | ❌ (fixed axle) | ✅ |
| Head rotate | ✅ (kRotateHead 2004) | ✅ (pan-tilt servo, lousy) | ❌ | ❌ | ✅ (if modeled) |
| Trajectory replay | ✅ (kReplayTrajectory 2028) | ❌ | ❌ | ❌ | ❌ |
| Odometry | ✅ (IMU + encoders) | ✅ (wheel-spin, drifts) | ✅ (wheel-spin, drifts) | ✅ (wheel-spin, drifts) | ✅ (ground truth) |
| Fall risk | ✅ HIGH | ❌ | ❌ | ❌ | ❌ |
| Servo heating | ✅ HIGH | ❌ | ❌ | ❌ | ❌ |
| Visual ball tracking | ✅ (camera on head) | ⚠️ (pan-tilt, lousy) | ❌ | ❌ | ✅ (if modeled) |
| Arrival angle control | ✅ (can rotate at end) | ✅ | ✅ | ❌ | ✅ |

The relay JSON is many-to-many: a single relay can map blue_1=virtual, blue_2=yahboom, blue_3=k1. RoboCup rules forbid mixed teams in tournaments, but ROS2K testing/demos use mixed hardware.

TeamCaptain reads per-bot capability flags from the relay JSON (extended with `can_kick`, `can_strafe`, `can_rotate_in_place`, `fall_risk`, `motion_model` fields).

## K1 kick abort mechanism

The K1's `kShoot` (2024) and `kVisualKick` (2038) are autonomous skills — the K1 takes over and chases the ball until kick distance is reached. If the ball moves away, the K1 follows indefinitely.

**Solution:** any bot's camera (K1 head cam primarily — Yahboom cam is unreliable) detects ball velocity/direction change. Published as a ROS2 topic. TeamCaptain (or the bridge in v6.4) listens:
- If a K1 is executing kShoot/kVisualKill AND ball motion change detected → send `kChangeMode` (2000) to abort the skill → bot is free for next assignment
- No threshold, no hysteresis — "ball velocity changed → abort chase"

## Open questions (deferred to v7 start)

1. **Path planner: always or threshold-based?** — Short distances (< 1m) may not need path planning (direct PD is sufficient). Long distances (> 1m) benefit from waypoints, obstacle avoidance, arrival angle. What distance triggers the path planner? Or does TeamCaptain always plan?

2. **Head angle: LLM or path planner?** — Does the LLM output "observe the ball" (intent → TeamCaptain controls head during transit), or does the LLM directly output "turn head to 45°" (separate gaze command, independent of movement), or both?

3. **K1 stop behavior** — Does `kMove(0,0)` stop the K1 cleanly (biped balance stabilization)? Or does it need `kChangeMode` (2000) after extended zero-velocity? Requires real K1 hardware test.

4. **Yahboom kick range** — How far does the metal-front push move the ball? Requires real hardware test. Affects whether Yahboom bots are viable kickers.

5. **Odometry on real hardware** — Sim uses Gazebo ground truth (perfect). Real Yahboom/K1 use wheel-spin/IMU odometry (drifts). How much drift over a 120s match? Does TeamCaptain need a Kalman filter (Phase 5.1) to correct?

6. **Trailer motion model** — Non-holonomic (car-like): can't strafe, can't rotate in place, all paths are arc-based. The path executor needs a different interpolation for trailers.

7. **TeamCaptain deployment** — Runs on K1 CPU or laptop CPU. If on K1: which K1? If that K1 fails, how fast can another instance take over? ROS2 discovery time?

8. **Nav2 evaluation** — Should Nav2 replace the home-grown path executor for sim bots? Nav2 provides standard path planning + obstacle avoidance, but adds a full navigation stack (costmaps, planners, controllers). Overkill for a flat field? Or worth the standardization?

9. **K1 trajectory replay integration** — `kReplayTrajectory` (2028) replays from a file on the K1's filesystem. Can we generate trajectory files at runtime (from TeamCaptain's waypoints)? Or must they be pre-recorded with `kRecordTrajectory` (2027)? What is the file format?

## Consequences

### Positive

- Clean separation: LLM = tactics, TeamCaptain = motion, Bridge = execution
- Hardware-aware planning (fall risk, diff-drive, non-holonomic)
- Augmented world model (free pathways, sweet spots → richer LLM input)
- Watchdog embedded naturally (planned vs actual comparison)
- Multi-bot coordination (non-colliding trajectories)
- Risk-adjusted scoring
- Downward compatible (bridge falls back to current_strategy.json)
- Calibration script shares path_executor.py with TeamCaptain

### Negative

- Added pipeline stage (3-node: LLM → TC → Bridge)
- More ROS2 topics (odometry in, optimized paths out)
- Testing burden (TC needs own test suite)
- Debugging complexity (3-node pipeline)
- Scope creep risk (TC could grow to Nav2 + SLAM + vision)

### Neutral

- CPU-only (no GPU contention with LLM)
- Dynamic re-routing (TC instance can move to another bot)
- Portable (runs on any K1 or laptop CPU)

## References

- `optimization_spec_v6.4.md` — current project plan
- `8_C3_SOCCER_KNOWLEDGE.md` — soccer knowledge + H2 feedback
- `agent_prompt_de.txt` axiom 5 — user-space Ollama (TC runs on CPU, not affected)
- `booster/b1_loco_api.hpp` — K1 API reference (api_id 2000-2042)
- Scrum tasks `scrum_tasks.md` — Task 2 (path executor), Task 3a/3b (gaze), Task 8 (v7 phases)
- Session changelog 2026-08-05 — clustering fix, TeamCaptain discussion