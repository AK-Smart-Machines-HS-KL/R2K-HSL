# ROS2K Scrum Tasks

> Ready for copy/paste into Trello. Updated 2026-08-05.
> Tasks 1 and 4 are done (not shown). Task 3a deferred to v7 (not shown).
> Tasks 9-11 are v7 (after this sprint). Task 8 is not a team task.

---

## Task 2: Build Demo/Calibration Mode for Bot Control

**Roles:** LLM-developer, K1-Developer

**Description:**
As a LLM-developer I need a demo/calibration prompt mode so that bots can be driven to specific positions for calibration and demos, using the existing evaluator-bridge pipeline. The human types commands ("blue_2 move to (1.0, 0.5)"), the LLM reformats them into inter-lingua, and the bridge executes. A standalone JSON calibration script serves as fallback when the LLM is down.

Details:
- Demo prompt: `strategy/fragments/header_demo.txt` (human types commands, LLM reformats to inter-lingua)
- `--demo` flag in launch_r2k.sh loads header_demo.txt instead of header_k3.txt
- Demo prompt contains NO meta-knowledge (no mention of bridge, cmd_vel, RPC, executor, ROS2K internals)
- LLM computes end-point from human command + current world state (e.g. "calibrate 1m" -> move to current_x + 1.0)
- JSON fallback: `tools/calibrate_bot.py` (standalone, no LLM, no bridge) — reads JSON waypoints, publishes cmd_vel/RPC directly
- K1: calibrate_bot.py sends RPC 2001 (vx, vy, vyaw)
- No path planning, no "path-walk-to" command (deferred to v7 — see ADR-A07)
- Dual-use: workshop demos (visitors "drive" a robot) + calibration (K1 follows waypoints, tester measures deviations)

**ToDo:**
```
[ ] Write strategy/fragments/header_demo.txt (demo/calibration prompt, no meta-knowledge)
[ ] Add --demo flag to launch_r2k.sh (loads header_demo.txt)
[ ] Write tools/calibrate_bot.py (standalone: JSON -> cmd_vel/RPC, no LLM, no bridge)
[ ] Create 3 calibration JSON files (1m-stop, 360deg, 5wp-kick)
[ ] Test demo mode: --demo -> human types "blue_2 move to (1.0, 0.5)" -> bot moves
[ ] Test calibration mode: JSON -> calibrate_bot.py -> Gazebo (1m, 360, 5wp+kick)
[ ] Test on K1 hardware: calibrate_bot.py -> RPC 2001
[ ] Document calibration + demo mode in AGENTS.md
```

**Acceptance Criteria:**
```
[ ] --demo flag loads header_demo.txt (demo prompt, no meta-knowledge)
[ ] Demo prompt never mentions bridge, cmd_vel, RPC, executor, or ROS2K internals
[ ] calibrate_bot.py runs standalone (no LLM, no bridge) with JSON input
[ ] 1m-forward calibration: actual distance within +-0.2m of commanded
[ ] 360-degree rotation: final heading within +-10 degrees of start
[ ] 5-waypoint + kick: ball moves >2m after final waypoint
[ ] Works with virtual bots (Gazebo) and K1 (RPC 2001)
[ ] Documented in AGENTS.md
```

---

## Task 3b: Implement Head Rotation for K1, Yahboom, and Gazebo

**Roles:** K1-Developer, LLM-developer

**Description:**
As a K1-Developer I need all bot types to rotate their head (gaze direction) independently from body locomotion. The K1 uses kRotateHead (api_id 2004). The Yahboom uses a pan-tilt servo (lousy quality but functional). Gazebo sim bots need a visual indicator (colored cone or light on the URDF model). This enables future gaze commands in the LLM protocol.

Details:
- K1: api_id 2004 (kRotateHead), parameters: pitch (float), yaw (float) — already in the K1 SDK
- Yahboom: pan-tilt servo control (one-sided, bilateral angle) — lousy camera but head rotation works
- Gazebo: add visual indicator to bot URDF (colored cone or blinking light showing gaze direction)
- Bridge: maps gaze commands to the appropriate hardware interface per bot type
- Failsafe: head returns to forward position on emergency stop (K1: api_id 2000, Yahboom: servo reset)
- Head rotation does not affect body locomotion (separate control path)
- Coordinate with future v7 Task 3a for full LLM protocol integration (gaze in Worldstate.json, "look at" command)

**ToDo:**
```
[ ] Verify kRotateHead (api_id 2004) parameter format in K1 SDK (pitch, yaw range)
[ ] Implement K1 head RPC publisher in bridge (api_id 2004)
[ ] Implement Yahboom pan-tilt servo control for head rotation
[ ] Add head visual indicator to Gazebo bot URDF (colored cone or light)
[ ] Add head reset to failsafe (K1: api_id 2000, Yahboom: servo reset)
[ ] Test on K1 hardware: send kRotateHead, verify head rotates
[ ] Test Yahboom: send servo command, verify pan-tilt rotates
[ ] Test Gazebo: visual indicator shows correct gaze direction
[ ] Document head rotation for all 3 bot types in AGENTS.md
```

**Acceptance Criteria:**
```
[ ] K1 head rotates to commanded yaw angle (+-5 deg accuracy) via api_id 2004
[ ] Yahboom pan-tilt servo rotates head (bilateral angle)
[ ] Gazebo bot shows visual gaze direction indicator
[ ] Head rotation does not affect body locomotion for any bot type
[ ] Head resets to forward on emergency stop (all 3 types)
[ ] Head rotation documented in AGENTS.md (K1, Yahboom, Gazebo sections)
```

---

## Task 5: Yahboom Trailer Hitch Mechanism (Deferred)

**Roles:** K1-Developer, Captain

**Description:**
As a K1-Developer I need a trailer hitch mechanism for the Yahboom platform to transport objects on the field. This is a future hardware feature — not blocking current development. Scope: mechanical design + ROS2 control interface for hitch attach/detach + angle sensor.

Details:
- Deferred to later project phase (post-tournament)
- Mechanical: trailer hitch on Yahboom rear, angle sensor for trailer direction
- Trailer motion model: non-holonomic (car-like), no in-place rotation, no kick, no camera
- Software: new ROS2 topic `/yahboom/hitch` (attach/detach/status)
- Gazebo model: trailer + hitch joint (if simulator supports it)
- No LLM integration needed initially (manual control)

**ToDo:**
```
[ ] Mechanical design sketch for hitch + angle sensor
[ ] Define /yahboom/hitch topic (std_msgs/String: "attach" / "detach" / "status")
[ ] Implement hitch controller on Yahboom (ESP32 or direct GPIO)
[ ] Define trailer motion model (non-holonomic, arc-based paths)
[ ] (Optional) Add trailer model to Gazebo URDF
[ ] Test hitch attach/detach on real hardware
```

**Acceptance Criteria:**
```
[ ] Hitch mechanism physically attaches/detaches trailer
[ ] Angle sensor reports trailer direction
[ ] /yahboom/hitch topic publishes attach/detach status
[ ] Trailer motion model documented (non-holonomic, no rotation in place)
[ ] (Deferred — not blocking tournament preparation)
```

---

## Task 6: Review and Correct Empirical Regression Test Descriptions

**Roles:** LLM-developer, Professor

**Description:**
As a LLM-developer I need the 33 empirical-proven regression test descriptions reviewed and corrected. Current issues: scope is missing (what tactical situation does this test cover?), image layout is poor/varies (ball icon hidden, arrow labels overlap), strategic argumentation is thin (Oracle doesn't explain why the decision is correct/incorrect).

Details:
- Scope: 33 empirical scenarios from umschaltmomente extraction (reduced from 74 by 3m clustering)
- Each scenario's analysis.md needs: clear scope statement, corrected field diagram, deeper Expert analysis, Oracle with strategy explanation ("to achieve X because Y")
- GLM-5.2 authors the corrections; human reviews
- Score charts need real data (run 8s tests first)
- Field diagrams: fix ball icon (smaller, semi-transparent), fix arrow label overlap
- Yellow vectors show Oracle positions (ground truth), NOT Qwen output
- Format: Source / Expert / Oracle / Output to bridge / Qwen decision / Regression metrics / Score chart / Test spec

**ToDo:**
```
[x] Run 33x 8s Gazebo regression tests to generate score data
[x] Regenerate 33 score charts with real data
[x] Fix field diagram ball icon (bigger, always visible — user instruction supersedes original spec)
[x] Fix arrow label overlap (removed text labels, kept dotted lines only)
[x] GLM-5.2: write scope statement for each of 33 scenarios
[x] GLM-5.2: deepen Expert analysis (why is this moment critical?)
[x] GLM-5.2: add strategy explanation to Oracle ("to achieve X because Y")
[ ] Human review: spot-check 5 scenarios for tactical correctness
```

**Acceptance Criteria:**
```
[x] All 33 analysis.md files have a "Scope" section
[x] All 33 field diagrams show ball icon clearly (not hidden by bot)
[x] All 33 Oracle sections include strategy explanation ("to achieve X")
[x] All 33 score charts have real data (not placeholder)
[x] Yellow vectors show Oracle positions (ground truth), not Qwen output
[ ] 5 spot-checked scenarios pass human review for tactical correctness
[x] 147 fast tests still pass
```

---

## Task 7: Second Human-in-the-Loop Review for 17 Hand-Crafted Scenarios

**Roles:** Professor, LLM-developer, Captain

**Description:**
As a Professor I need a second human reviewer to validate the 17 hand-crafted scenario descriptions (Expert/Oracle), ensuring scientific soundness and removing single-annotator bias. The first annotator (GLM-5.2) wrote the content; a second human reviews blind. This addresses the IAA (inter-annotator agreement) gap identified in the QA review.

Details:
- 17 hand-crafted scenarios: each has Expert + Oracle + Output to bridge
- Oracle uses only: "cover the goal line at (X,Y)" / "move to (X,Y)" / "kick" / "hold position"
- Output to bridge translates "cover the goal line at" to "move to" (what the bridge receives)
- Reviewer sees Expert and Oracle, scores each on: tactical correctness (1-5), position reachability (yes/no), strategy clarity (1-5)
- Reviewer does NOT see GLM-5.2's authoring process — blind review
- Compute Cohen's kappa between GLM-5.2's self-assessment and human review
- If kappa < 0.6: rework the scenarios with discrepancies
- Setup: shared document (markdown), reviewer fills in scores, Captain computes kappa

**ToDo:**
```
[ ] Prepare review sheet: 17 scenarios, Expert + Oracle per scenario
[ ] Write GLM-5.2 prompt: "Score this Expert/Oracle on tactical correctness, reachability, clarity"
[ ] GLM-5.2 scores all 17 (first annotator)
[ ] Setup interview with second human (Professor or team member)
[ ] Human reviews all 17 blind (second annotator)
[ ] Compute Cohen's kappa per criterion
[ ] If kappa < 0.6: identify discrepant scenarios, rework with both annotators
[ ] Document IAA result in session changelog
```

**Acceptance Criteria:**
```
[ ] Review sheet covers all 17 hand-crafted scenarios
[ ] GLM-5.2 scored all 17 (recorded)
[ ] Human scored all 17 blind (recorded)
[ ] Cohen's kappa computed for: tactical correctness, reachability, clarity
[ ] Scenarios with kappa < 0.6 identified and reworked
[ ] IAA result documented in SESSION_CHANGELOG.md
```

---

## Task 8: C3 Validation, Gazebo Demo, and Final KPI Report

**Roles:** LLM-developer, Captain, Presenter of Demos

**Note:** This is an individual execution task, not a team task. The LLM-developer executes the remaining v6.4 phases with support from the Captain (git, QA) and Presenter (demo selection).

**Description:**
As a LLM-developer I need the remaining C3 evaluation pipeline executed: validate the inter-lingua comprehension across all scenarios, run live Gazebo demonstrations with human coaching feedback, cross-validate against a second model family (Llama), and produce the final KPI report and demo package for tournament and academic presentation.

Details:
- Phase 3: text-probe all 17 hand-crafted + 33 empirical scenarios, confirm hard-pass >= 90%, no clustering regression
- Phase W: synthetic divergence scenarios, test watchdog re-prompt vs second-model monitor
- Phase 4: 3-5 live Gazebo matches with `--analyze`, collect H2 coach annotations, run prediction ON/OFF comparison
- Phase 4b: pull Llama-3.2-3B, run prompt-structure sub-experiment, compare to Qwen-2.5-3B
- Phase 5: compute final KPI table (text-probe primary, Gazebo supplementary), select best demo matches, update spec to v6.5
- Code freeze on v6.4 after Phase 5
- Selective commits based on phase results (not everything at once)

**ToDo:**
```
[ ] Phase 3: text-probe 50 scenarios x n=10, verify hard-pass >= 90%
[ ] Phase 3: verify no clustering regression (min target dist >= 1.0m)
[ ] Phase W: build 6 synthetic divergence scenarios
[ ] Phase W: test re-prompt (Option A) and second-model (Option B)
[ ] Phase W: write decision report
[ ] Phase 4: run 5 live Gazebo matches with --analyze
[ ] Phase 4: collect H2 coach annotations
[ ] Phase 4: run prediction Part B (ON/OFF eyeball)
[ ] Phase 4b: ollama pull llama3.2:3b
[ ] Phase 4b: run sub-exp 2 (8 configs x 150 states x n=10)
[ ] Phase 5: compute final KPI table (text-probe primary, Gazebo supplementary)
[ ] Phase 5: select 3-5 best demo matches
[ ] Phase 5: update spec to v6.5, mark all phases DONE
[ ] Phase 5: code freeze on v6.4
[ ] Phase 5: selective commits based on phase results
```

**Acceptance Criteria:**
```
[ ] Phase 3: hard-pass >= 90% across all 50 scenarios
[ ] Phase 3: no clustering regression (min target dist >= 1.0m in >= 80% of scenarios)
[ ] Phase W: decision report recommends Option A or B with evidence
[ ] Phase 4: 5 live matches completed, H2 annotations collected
[ ] Phase 4: prediction Part B result documented (ON vs OFF)
[ ] Phase 4b: Llama-3.2-3B results compared to Qwen-2.5-3B
[ ] Phase 5: final KPI table produced
[ ] Phase 5: spec updated to v6.5 with all phases marked DONE
[ ] Phase 5: v6.4 code freeze (no new features, only bugfixes)
[ ] 147 fast tests pass at completion
```

---

## Task 9: Resolve Technical Debt — Clustering, Score Metrics, and Commit Backlog (v7)

**Roles:** LLM-developer, K1-Developer, Captain

**Description:**
As a Captain I need the accumulated technical debt from the C3 development sprint resolved before v7 architecture work begins. This covers: residual clustering in the bridge, incomplete score metrics, missing scenario test data, the 2vs2 phantom-bot issue, axiom documentation drift, and the full commit of all uncommitted work.

Details:
- Pair clustering (blue_2 + blue_3 near ball): increase anti-collision push distance, refine blue_3 positioning prompt
- blue_3 passivity: add wingman pattern to header
- Score chart data: run Gazebo matches for 5 scenarios lacking traces
- Ball velocity metric: add deque-based tracking to score_node
- 2vs2 phantom-bot: gate output line count to n_blue
- Goalie PD tuning: further gains for stuck-at-X=-2.6 recovery
- Axiom 5 reconciliation: update agent_prompt_de.txt per ADR-A06
- Commit backlog: all work from Phases A through 2 + empirical reduction + bridge fixes
- Game-phase fragments: validate in live matches (goal kick, ball out, kickoff, foul penalty)
- Per-bot kick capability: relay JSON needs can_kick flag for v7

**ToDo:**
```
[ ] Increase anti-collision push distance 1.0m -> 1.5m, re-test clustering
[ ] Add wingman pattern to header_k3.txt
[ ] Run 5x 120s Gazebo matches for missing score chart scenarios
[ ] Add ball velocity deque to score_node.py
[x] Gate output line count to n_blue (done via _text_output_header function, header_k3.txt deleted as dead code)
[ ] Tune PD gains: test 1.5x boost when distance > 1.0m
[x] Update agent_prompt_de.txt axiom 5 per ADR-A06
[ ] Commit all work: Phase A, H1, C, M', H2, R, 2, empirical, bridge fixes
[ ] Run 3 live matches focusing on set-pieces
```

**Acceptance Criteria:**
```
[ ] Pair clustering rate <= 10% (measured by cluster_experiment.py, 3 matches)
[ ] blue_3 advances to X >= 0 when blue_2 has ball in opponent half (text-probe)
[ ] All 17+33 scenarios have score chart with real data
[ ] Ball velocity metric produces non-zero values in score_node
[ ] 2vs2_default hard-pass >= 80% (phantom-bot fixed)
[ ] agent_prompt_de.txt axiom 5 matches install.sh behavior
[ ] All work committed to git (clean working tree)
[ ] Game-phase fragments tested in >= 1 live match per type
[ ] 147 fast tests pass
```

---

## Task 10: Implement TeamCaptain Architecture (v7)

**Roles:** LLM-developer, K1-Developer, Captain, Professor

**Description:**
As a Captain I need the TeamCaptain architecture implemented in ROS2K v7 to separate tactical intent (LLM) from motion planning (TeamCaptain) and command execution (Bridge). TeamCaptain is a CPU-only ROS2 node that takes LLM end-points and produces optimized per-bot execution plans. It also serves as watchdog, augmented world model provider, and kick-abort coordinator. See ADR-A07 for full design.

Details:
- TeamCaptain sits between evaluator and bridge: LLM -> current_strategy.json -> TeamCaptain -> optimized_path.json -> Bridge
- CPU-only (no GPU contention with LLM)
- Hardware-aware: per-bot capability profiles (K1 fall risk, Yahboom diff-drive, trailer non-holonomic)
- Multi-bot coordination: non-colliding trajectories (replaces bridge anti-collision hack)
- Augmented world model: computes free pathways, sweet spots, risk zones -> injects into world state for LLM
- Watchdog: receives odometry via ROS2, compares planned vs actual, triggers failsafe or LLM re-prompt
- Kick abort: listens for ball motion change (K1 camera) -> sends kChangeMode (2000) to abort autonomous kick chase
- Risk-adjusted scoring: feeds fall probability, collision risk into score function
- Downward compatible: bridge falls back to current_strategy.json when TeamCaptain is down
- Open questions (v7 start): path planner threshold, head angle control, K1 stop behavior, Yahboom kick range, odometry drift, trailer motion model, Nav2 evaluation, K1 trajectory replay format

**ToDo:**
```
[ ] Write ai_tactics/path_executor.py (shared with calibrate_bot.py from Task 2)
[ ] Define hardware capability profiles in relay JSON
[ ] Implement TeamCaptain ROS2 node (reads current_strategy.json, writes optimized_path.json)
[ ] Implement multi-bot coordination (non-colliding trajectory planning)
[ ] Implement augmented world model (free pathways, sweet spots, risk zones)
[ ] Implement watchdog (odometry comparison, failsafe, LLM re-prompt trigger)
[ ] Implement kick abort (ball motion change -> kChangeMode for K1)
[ ] Bridge: read optimized_path.json when available, fall back to current_strategy.json
[ ] Test TeamCaptain in Gazebo (sim bots)
[ ] Test on K1 hardware (CPU performance, kick abort)
[ ] Document TeamCaptain architecture in AGENTS.md
```

**Acceptance Criteria:**
```
[ ] TeamCaptain runs as CPU-only ROS2 node
[ ] Bridge reads optimized_path.json when TeamCaptain active, falls back to current_strategy.json
[ ] Multi-bot trajectories are non-colliding (no clustering in sim)
[ ] Augmented world model fields visible in Worldstate.json
[ ] Watchdog detects divergence > threshold and triggers failsafe
[ ] Kick abort: ball motion change -> K1 stops chasing within 1s
[ ] Hardware profiles: K1, Yahboom, trailer, sim each get correct motion model
[ ] Downward compatible: disabling TeamCaptain reverts to current behavior
[ ] Documented in AGENTS.md
```

---

## Task 11: Implement K1 Kick Abort via Ball Motion Detection (v7)

**Roles:** K1-Developer, LLM-developer

**Description:**
As a K1-Developer I need the K1's autonomous kick skill (kShoot 2024 / kVisualKick 2038) to be abortable when the ball moves away. The K1 follows the ball indefinitely during the kick skill — this is a game-stopper for real matches. A ball motion change sensor (K1 camera) detects when the ball velocity/direction changes, and the bridge (or TeamCaptain) sends kChangeMode (2000) to abort the chase.

> **GATE 0 (2026-08-28):** the autonomous-chase premise is UNVERIFIED — no
> vendor doc or logged hardware session supports it; vendor notes Shoot's
> motion is currently T1-provided (may fail on K1) and VisualKick needs
> firmware ≥ v1.5.2.1. Run the probe protocol in
> `docs/plans/v68_pre_ifa/k1_kick_head_vendor_audit.md` FIRST. Probe outcomes re-scope this
> story: (a) chase observed → abort design as described, (b) skills
> self-terminate → story drops, (c) evaluate firmware Soccer mode (mode 4,
> K1+T1) as the kick mechanism instead.

Details:
- K1 kick skills (kShoot 2024, kVisualKick 2038) are autonomous: K1 chases ball until kick distance
- If ball moves (kicked away, opponent kicks) -> K1 follows indefinitely -> bot is stuck
- Detection: K1 camera detects ball velocity/direction change -> publishes on ROS2 topic
- Abort: bridge (or TeamCaptain) receives ball motion change -> sends kChangeMode (2000) -> K1 stops chasing -> free for next assignment
- No thresholds, no hysteresis — "ball velocity changed -> abort chase"
- Yahboom cam is lousy — cannot rely on it for ball detection. K1 camera only.
- Sim bots: phantom kick is instant (no chase) -> no abort needed

**ToDo:**
```
[ ] Define ROS2 topic for ball motion change (/ball/motion_change)
[ ] Implement ball motion detector (K1 camera -> velocity/direction change -> publish)
[ ] Implement kick abort in bridge: receive /ball/motion_change -> send kChangeMode (2000) if K1 is kicking
[ ] Test: K1 starts kick chase, ball moves away, K1 stops within 1s
[ ] Test: K1 starts kick chase, ball stays, K1 completes kick normally
[ ] Document kick abort mechanism in AGENTS.md
```

**Acceptance Criteria:**
```
[ ] K1 kick chase aborts within 1s of ball motion change
[ ] K1 kick completes normally when ball stays still
[ ] /ball/motion_change topic publishes on ball velocity/direction change
[ ] Sim bots unaffected (phantom kick is instant, no chase)
[ ] Kick abort documented in AGENTS.md
```

---

## Overview

| # | Title | Roles | Sprint | Status |
|---|---|---|---|---|
| 1 | Establish Definition of Done with GLM-5.2 | Captain, LLM-dev, Professor | v6.4 | DONE |
| 2 | Build Demo/Calibration Mode for Bot Control | LLM-dev, K1-dev | v6.4 | Not started |
| 3a | Add Gaze Direction to ROS2K World Model | LLM-dev, Captain | v7 | DEFERRED |
| 3b | Implement Head Rotation for K1, Yahboom, and Gazebo | K1-dev, LLM-dev | v6.4 | Not started |
| 4 | Evaluate and Decide Simulator Platform | Captain, Professor, LLM-dev | v6.4 | DONE |
| 5 | Yahboom Trailer Hitch Mechanism | K1-dev, Captain | Deferred | Not started |
| 6 | Review and Correct Empirical Regression Test Descriptions | LLM-dev, Professor | v6.4 | Not started |
| 7 | Second Human-in-the-Loop Review for 17 Scenarios | Professor, LLM-dev, Captain | v6.4 | Not started |
| 8 | C3 Validation, Gazebo Demo, and Final KPI Report | LLM-dev (individual) | v6.4 | Not started |
| 9 | Resolve Technical Debt — Clustering, Score, Commits | LLM-dev, K1-dev, Captain | v7 | Not started |
| 10 | Implement TeamCaptain Architecture | LLM-dev, K1-dev, Captain, Professor | v7 | Not started |
| 11 | Implement K1 Kick Abort via Ball Motion Detection | K1-dev, LLM-dev | v7 | Not started |