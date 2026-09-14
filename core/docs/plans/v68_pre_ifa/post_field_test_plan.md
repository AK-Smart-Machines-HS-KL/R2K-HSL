# Post-Field-Test Plan — integrated, time-sorted (2026-09-08)

> **Status:** K1 first real field run DONE (9/9 goto legs, arrival fix live-verified,
> zero errors — run `…161450`). This plan integrates everything discussed after
> that run: the code audit (duplicates/stale/refactor), the field-test gaps, and
> the pre-v7 redesigns. It is the single "what's next" reference — the session
> changelog points here.
>
> **Commit gate (user directive 2026-09-08): nothing commits until the formal
> K1 field day passes.** Everything below lands uncommitted until then.

---

## Phase 0 — Cleanup: deletions & doc-truths (next code session, ~30 min, zero risk)

Straight deletions of dead/misleading code found by the audit. No behavior change.

| # | Item | Evidence |
|---|---|---|
| 0.1 | **Delete dead calib shake profile in the bridge** — `Y_CALIB_SHAKE_FREQ_HZ`/`Y_CALIB_SHAKE_AMP_DEG` + the profile-selection branch in `_render_body_gesture`. Unreachable since `y1 say no` routes Seq-side (evaluator), y2 goes servo, demo uses the demo profile. | bridge constants block + `_render_body_gesture` |
| 0.2 | **Delete `read_k1_odom()` alias** — zero callers. | calib_test.py:189 |
| 0.3 | **Fix `y_turns` runbook notes** — say "closed-loop turn (+ = clockwise/right)"; the notes still describe open-loop TimedMove and CCW (sign flipped since). | calib_test.py:63-70 |
| 0.4 | **Fix `_persist_non_llm_assignments` docstring** — still says `k1_bot` slot. | r2k_evaluator.py |
| 0.5 | **Fix CLI bare-coord echo** — in calib, bare `go to (x,y)` routes to the **k1 Goto** (closed loop), but the echo claims "waypath, executor drives". Make the echo match the routing (calib-aware). The same misleading-echo class cost hours live. | calib_cli.py |
| 0.6 | **AGENTS.md truth pass** — "Rotation/Face commands" are listed under "Not yet available (v7)" but were implemented and live-validated 2026-09-08; the demo-mode launch examples still show `--demo` as the calib path (`--calib` is the field posture). | AGENTS.md "Demo / Calibration Mode" section |
| 0.7 | **Rename `_nosim_hw_tick` → `_calib_hw_tick`** + fix 3 stale NOSIM comments in launch_r2k.sh (nosim is a pure alias of --calib since the mode merge). | bridge + launcher |
| 0.8 | **Persist the day's lessons** into `LESSONS_LEARNED.md` §v6.8: the firmware-physics table (encoder odom on-motion-only, yaw gyro-fused ~89% delivery vs distance ±30%, yaw-PID cancels <0.5 s reversals, XRCE no-reconnect, boot contract) + the architecture lessons (subtraction-over-patch at recurrence #3; observability cheaper than correctness; silence is ambiguous → say which of dead-slot/no-op/gate-blocked/quarantined). | new section |
| 0.9 | **DONE 2026-09-12 (both breaks, live-verified): match-mode slot + model-name fixes.** The 09-06/07 relay rename broke TWO lookup layers: (1) executor slots `blue_1` (world names) vs canon relay keys `blue1` — fixed by `_canon_assignments()` at the evaluator's strategy write (ONE convention at the bus boundary); (2) the bridge's model lookup `blue1` vs Gazebo model `blue_1` — fixed by name-domain translation at the bot_idx lookup (both directions, + `import re`). Blue bots braked silently since the rename (last match validation 2026-08-31); latency computed normally both times — a healthy LLM cycle says nothing about the bus. **Regression rule: every relay rename needs a match-mode smoke test, not just demo/calib.** | r2k_evaluator.py + bridge + test |

## Phase 1 — Hardening & tooling (same session, ~2 h, test-covered)

The two goals: make the remaining weak rehearsal leg (exec runbooks) honest, and
make the K1 field day's first 60 seconds answer "is the robot healthy".

| # | Item | Detail |
|---|---|---|
| 1.1 | **Exec-stepper hardening** (designed 2026-09-08, not yet built): per-leg NO-MOVE detection (snapshot pose before/after each leg; identical → `⚠ odom unchanged — bot did not move`), startup stale-odom warning (`t` older than 5 min → "robot online?"), all-legs-no-move → verdict **NO-MOVE** (not FAIL) with `moved:false` in the record, **bot-prefixed exec** (`y1 exec short`) with pure `substitute_runbook_bot(steps, bot)` helper (unit-tested) + per-bot threshold override. Fixes the live failure: `exec short` reported "3.36 m FAIL" against a dead k1 slot fed by a 1.9 h-stale ghost odom file. | calib_cli.py + calib_test.py |
| 1.2 | **`tools/restart_calib.sh`** — one command for the pkill + env-capture/forward + bridge/evaluator restart + log-tail dance (typed 6× during 2026-09-08; each manual repetition risks env drift). | new script |
| 1.3 | **Field-day pre-flight script** (`tools/preflight.sh` or a `preflight` CLI verb): per relay entry — imu rate (expect ~25 Hz yahboom), odom publisher count (k1: exactly 1, garbage-source check — the ghost publisher was real once), one odom sample sanity, bridge-log freshness. Green/red output. | new script |
| 1.4 | **`exec selftest`** runbook: turn ±90° with delivery-ratio report → goto 0.5 m out + home → say yes/no → stop; prints measured-vs-commanded per axis. Turns the day's manual forensics into a 60 s health check. | calib_test.py |
| 1.5 | **Refactor C1 — helper extraction** (`_hw_odom(hw, type)` odom-source fetch incl. stale-brake, `_calib_cap(type)`, `_feed_est(hw, vx, vyaw)`): kills the 3× odom-fetch blocks (seq/face/goto), 4× cap sites, 4× estimator feeds — the copy-paste seams every new hardware bug entered through. Zero behavior change; fast tier must stay 250 passed. | bridge |

## Phase 2 — Next hardware session (K1 + Yahbooms online, ~45 min lab)

| # | Item | Detail |
|---|---|---|
| 2.1 | **Tape-measure the 1 m goto → set `K1_ODOM_FACTOR` from data.** Field data: raw odom parks at a tight 1.30–1.34× target (the 0.8 factor + coast working as designed). If the bot parks physically ~1.0 m: vendor 0.8 is correct (odom over-reads 25-30%). If it parks ~1.3 m: raise the factor toward 1.0. This single measurement decides the last accuracy constant. | bridge constant |
| 2.2 | **K1 `say yes/no` + `face` pass** — the RPC 2004 head path is untested live. Quick verification, then the vocabulary is proven on all three hardware types. | live |
| 2.3 | **Yahboom regression battery** — after Phase 0/1 changes: `y1 go to (0.5,0)` → home → `turn 90` → `say no` → `exec y_short` (with hardened stepper) → `results`. | live |
| 2.4 | **Formal K1 field day** — `--calib --relay hardware_mirror`, wake-up ritual, pre-flight (1.3), selftest (1.4), `exec short/square/triangle`, `results`, tape measurement (2.1). **This is the commit gate** — when it passes, commit the whole 2026-09-05→field-day stretch per git rules. | live + git |
| 2.5 | **K1 kick skill ("goto ball and kick at (x,y)")** — full elaboration in the Phase 2.5 section below (K0 probe → vendor Kick/RLVisionKick port → staged validation). Includes the pass scenario (3B pass semantics + `resolve_pass_target` already built) and the goal-segment/open-path extension of `shoot_lane_open` (deterministic CPU geometry → 3B decision fact). TRUE camera vision = v7, not required. | bridge + live |
| 2.6 | **PS4 teleop wiring** (`ps4_teleop.py`) — exists untracked, never wired/validated against the Yahboom relays; low priority, stub commits with the plan doc as owner. | ps4_teleop.py |

## Phase 3 — Pre-v7 refactor (post-commit, ~1 day)

| # | Item | Detail |
|---|---|---|
| 3.1 | **Shared vocabulary module OR mirror-parity test** (audit A5): the CLI mirrors evaluator logic (compass map, turn/coord/home regexes, alias tuples) — mirror drift caused two live bugs. Cheap version: parity unit test importing both, asserting maps/regexes match. Better: extract `calib_vocab.py` (accept the tools/↔src import boundary). | CLI + evaluator |
| 3.2 | **Pause semantics in calib** (audit B8/C4): decide + implement — lean calib should ignore Gazebo pause entirely (the hw loop owns motion); today a calib-with-Gazebo hybrid freezes hardware if Gazebo pauses. ~15 min once decided. | bridge |
| 3.3 | **`yN recenter` verb** — re-zero the estimator at the current pose; kills the "home silently moved after a mid-session power-cycle" trap (the estimator re-arms at (0,0,0) on bridge restart while the encoder frame persists — first sample heals it, but until then home ≠ mark). Also document the restart asymmetry. | evaluator + bridge |
| 3.4 | **Unified command ledger** — the id-keyed done-set pattern exists in 4 branches (timedmove, head, seq, gestures); one `_done[bot]=id` set with TTLs replaces per-branch state and makes the strategy file a real command stream. | bridge |
| 3.5 | **Trapezoidal turn profile** — pure-P-saturate works but slams the yaw PID; a ramp is gentler (matters more for K1's biped gait). Optional: also revisit effective straight-line speed (~0.1–0.2 m/s observed vs 0.7 cap — distance gain 0.8 and accel dominate; raise if the field day needs pace). | bridge |
| 3.6 | **K1 DAMP recovery checks** (re-phrased 2026-09-12: the chassis Damping button is vendor hardware; ours is only the diagnostic hint) — (a) with the robot in button-damping, fire a goto → the evaluator's DAMP hint (r2k_evaluator.py:97-108) should fire; (b) recovery damping→prepare→walking via ChangeMode(2000). | live |
| 3.7 | **Vendor-inventory picks** (robocup_demo capability inventory, 2026-09-12): set-piece/goalie placement math as CPU skills (`GoToReadyPosition`/`GoToFreekickPosition`/`GoToGoalBlockingPosition` patterns), obstacle-aware navigation flag (`avoidObstacle` concept), `penalized/alive` array in the match payload (referee-truth roster awareness for the 3B), K1 head-tracking skill (CamTrackBall pattern — after head probes). Full inventory: session 2026-09-12 analysis; locator/vision/team-protocol = v7 real-field autonomy, documented not scheduled. | bridge + evaluator |

## Phase 4 — v7 proper (parked; designs exist)

- **External start pose** (K1 camera / AprilTag) replacing the wake-up ritual — the (0,0,0) boot contract is the last piece of calibration theater a real robot shouldn't need. Design sketch exists in the estimator comments ("external start info later").
- **Bot yaw in the Worldstate** (tracker change, v7 Task 3a) — unlocks relative motion, makes the 7B compiler hardware-aware.
- **Per-bot state unification** (audit C5/A4: 5 dicts keyed by hw_name → one record) — deliberately deferred past the field day; medium risk, cosmetic payoff.
- **Sim-puppet twin / R2K_HW_CLOSED_LOOP for matches mode** — still a non-goal (declared 2026-09-08).

## Non-goals (explicit, per user directives 2026-09-08)

- No Yahboom accuracy campaign (±30% distance accepted; yaw closed-loop is enough).
- No firmware changes (all fixes host-side).
- No matches-mode integration of calib verbs.
- No commit before the formal field day passes.

---

**Verification discipline** (every phase): fast tier
`pytest tests/ --skip-slow -q --ignore=tests/test_adaptive_horizon.py --ignore=tests/test_chart_specs.py`
— expected 250 passed / 20 pre-existing i3_sweep failures (documented, uncommitted-backlog
origin); sim battery `calib_test.run_sim_battery()` 12/12; py_compile each touched file.
After any code drop into a running session: use `tools/restart_calib.sh` (1.2) — running
processes keep old modules.

---

## Phase 2.5 — K1 kick skill ("goto ball and kick at (x,y)") [PROJECT P1]

> Full elaboration from the 2026-09-12 session; pattern source = the K1 goto saga
> (folklore challenge → infrastructure → vendor recipe port → probe-before-code →
> staged validation). Vendor recipe source: `~/Workspace/robocup_demo/src/brain`
> (read 2026-09-12, cited below).

### The pattern (from the goto saga)

| Stage | Goto saga | Kick mapping |
|---|---|---|
| 1. Folklore challenge | "no odom exists" vs "a subscription away" — both unverified | "kShoot/kVisualKick chase autonomously" — ALREADY audited 2026-08-28: exists only in our own files; vendor docs describe firmware-configured requests, no autonomy |
| 2. Infrastructure | booster_msgs built | DONE — the same generic RpcReqMsg carries any LocoApi call (kVisualKick = api 2038, kShoot = 2024, head = 2004); NO new msg needed |
| 3. Vendor recipe port | robot_client.cpp moveToPoseOnField → our two-phase goto | brain_tree.cpp Kick node (drive-and-push + abort gates) + RLVisionKick node (decelerate → kVisualKick → head dance) |
| 4. Probe before code | "a topic may only be called silent after its msg type is built and a subscriber attaches" | GATE 0: no kick code before the hardware probe matrix |
| 5. Staged validation | Yahboom rehearsal → sim_k1 → real K1 9/9 legs | approach = proven goto machinery; kick gesture = K1-only, staged |

### Vendor recipe findings (brain_tree.cpp / robot_client.cpp, read 2026-09-12)

- **Kick node (drive-and-push, the vendor's workhorse):** chase = `crabWalk(ball.yawToRobot, speed)` each cycle, speed ramps +0.1/cycle to cap; vy/vx limits + vxFactor/yawOffset calibration constants; **abort** when ball range grows > 0.3 m from the minimum seen or ball lost > 1000 ms (config `abort_kick_when_ball_moved` — exists in code, default OFF); time budget `min_msec_kick + range/speed*1000`; avoid-pushing retreat.
- **RLVisionKick node (firmware kick):** decelerate 500 ms → kVisualKick (api 2038, `{"start": true}`) → head dance (pitch 0.4→0.7 over 550 ms — feeds the firmware ball tracking) → exit on flag/ball-out/ball > 5 m/budget.
- **Vendor config defaults all firmware kicks OFF** (enable_shoot / enable_directional_kick / enable_auto_visual_kick = false in brain.cpp) — consistent with the audit: Shoot() may fail on K1, VisualKick needs fw ≥ 1.5.2.1, RobotMode::kSoccer=4 (with kSoccerKicking) exists as the heavyweight alternative.

### Stages

| Stage | Content | Gate |
|---|---|---|
| **K0 — GATE 0 probe** (K1 on stand, ~45 min, blocks all else) | audit §3 matrix + sample findings: fw check (api 2022, ≥ v1.5.2.1 expected ✓ v1.7.2); on-robot header diff vs PR-#18 snapshot; probe: kVisualKick V1/V2 (motion? termination? head behavior? abort via kChangeMode?), Shoot() (expect state-transition fail on K1), ball-moved test (chase? — settles the folklore), Soccer-mode-4 dependency? | results → audit doc §6, gates decided |
| **K1 — constants + RPC plumbing** (host, ~1 h) | K1_KICK_* constants (vendor-named): APPROACH_OFFSET, RANGE_GATE, DECELERATE_MS=500, BALL_MOVED_M=0.3, BALL_LOST_MS=1000, TIME_BUDGET_S, VISUALKICK_API=2038, version; `_k1_rpc(api_id, body)` helper (goto's RPC path generalized) | K0 gate decisions |
| **K2 — bridge skill** (GotoBallAndKick, ~3-4 h) | extend the `kick` action for k1 as a state machine: **A approach** = proven K1 goto loop on the dynamic behind-ball target (`kick_skill_target`, sim-proven) + arrival on dist AND aim-heading (deliberately NOT dist-only — the kick heading aims at a far point, geometrically stable, unlike park bearings); **B decelerate** 500 ms; **C kick** = kVisualKick + head dance; **D abort/exit** (ball moved/lost/budget) → brake + kWalking reset + outcome log (KICK fired / ABORTED: ball moved). Per-bot state `_k1_kick_state[hw]`; per-bot exception isolation (Phase 1.6) first. Sim phantom-kick path untouched. | K1 |
| **K3 — staged validation** (K1 live) | 1 approach-only → 2 approach+decelerate (kick suppressed) → 3 full V1 (ball 1 m goal-ward) → 4 V2 + abort test → 5 vocabulary check ("k1 kick at (x,y)", match-mode Kick assignment from the 3B) | — |
| **K4 — telemetry + KB** | outcome records (approach time, fired/aborted, ball displacement) into trace/results; update the six folklore-annotated KB sites + capability matrix; audit doc §6 closes GATE 0 | — |

### Kick semantics (confirmed)

- "kick at (x,y)" = aim direction (existing Kick `target_x/target_y` semantics)
- ONE approach + ONE kick attempt with abort — NOT autonomous chase (our CPU owns the loop)
- Pass scenario: the 3B already emits `Kick` with pass `target_x/target_y` today; `_resolve_kick_aim` resolves pass-vs-goal aim; `resolve_pass_target` picks open-lane receivers — the pass scenario needs only the same execution leg
- Open-path/goal-segment analysis: extend `shoot_lane_open` to goal-mouth segments (deterministic CPU geometry, already built for the center lane); feed the 3B a decision fact (`lane_open_left/center/right`) — proven LLM-decides/CPU-computes split. TRUE camera vision = v7 (vendor ships ONNX segmentation; separate project)

### Sequencing + risks

Slots as Phase 2.5 (after 2.1 tape measure, same hardware sessions). Risks ranked: (1) K0 gate = the only true unknown; fallback ladder pre-planned (VisualKick → Soccer-mode-4 eval → drive-and-push — the vendor's own workhorse). (2) Multi-kick coordination: single-kicker-per-cycle already the 3B contract. (3) Goal-segment granularity: trivial geometry; cost is validating 3B exploitation (match regression suite).

---

## Appendix A — code audit catalog (traceability: audit item → phase)

**A. Duplicated**

| # | What | Where | Phase |
|---|---|---|---|
| A1 | Odom-source fetch (est-tick/k1-odom + stale-brake) ×3 | bridge seq:1180, face:1245, goto:1312 | 1.5 (C1) |
| A2 | Calib spin-cap `if CALIB and yahboom: vyaw_cap = Y_CALIB_VYAW` ×4 | bridge 904/1267/894/… | 1.5 (C1) |
| A3 | Estimator feed `_goto_state[hw]={last_vx,…}` ×4 | bridge 922/929/1286/1452 | 1.5 (C1) |
| A4 | Parallel per-bot stores: _k1_odom/_y_odom/_y_est/_y_last_raw_t/_y_last_pub_t (5 dicts) | bridge init | 4 (C5, parked) |
| A5 | CLI mirrors of evaluator logic (compass map, turn/coord/home regexes, alias tuples ×2) | calib_cli 57-70/285/327-340 | 3.1 |
| A6 | k1 alias sets overlap (DEMO_K1_ALIASES ⊂ DEMO_GOTO_BOTS) | evaluator 161/165 | 0 (cosmetic) |
| A7 | Restart boilerplate (typed 6× on 09-08) | session log | 1.2 (restart_calib.sh) |

**B. Stale / dead / misleading**

| # | What | Where | Phase |
|---|---|---|---|
| B1 | Dead calib shake profile (Y_CALIB_SHAKE_* + branch) — unreachable after say-no→Seq | bridge 60-68/879-928 | 0.1 |
| B2 | CLI bare-coord echo contradicts calib routing | calib_cli ~345 | 0.5 |
| B3 | AGENTS.md "Not yet available" face row + stale demo launch examples | AGENTS.md 214/241 | 0.6 |
| B4 | `_nosim_hw_tick` name + 3 NOSIM comments | bridge 1027, launch 291/313/461 | 0.7 |
| B5 | y_turns runbook notes (TimedMove framing, CCW sign) | calib_test 63-70 | 0.3 |
| B6 | `k1_trace_*.jsonl` name holds all bots' records | bridge 310 | KEEP (run-id inference + analyze compat) — document only |
| B7 | `read_k1_odom` alias, zero callers | calib_test 189 | 0.2 |
| B8 | check_pause_state in lean calib (no /clock) + Gazebo-pause freeze risk in hybrid | bridge 381 | 3.2 (decision needed) |
| B9 | `_persist_non_llm_assignments` docstring says k1_bot | evaluator 1067 | 0.4 |
| B10 | Mixed-prefix dead writes ("y1 and blue_1 go to (1,1)" → dead blue waypath in calib) | evaluator 978-985 | 0 (edge; reject or skip) |

**C. Refactors**

| # | What | Kills | Phase |
|---|---|---|---|
| C1 | `_hw_odom(hw,type)` + `_calib_cap(type)` + `_feed_est(hw,vx,vyaw)` helpers | A1/A2/A3 | 1.5 |
| C2 | Shared vocab module or mirror-parity test | A5 | 3.1 |
| C3 | `tools/restart_calib.sh` | A7 | 1.2 |
| C4 | Pause semantics decision (lean calib ignores Gazebo pause) | B8 | 3.2 |
| C5 | Per-bot state unification (5 dicts → 1 record) | A4 | 4 (deferred) |
| C6 | Deletions pass (B1/B7/B5/B9/B2/B3/B4) | — | 0.1-0.7 |

## Appendix B — glossary (team terms)

- **Dead reckoning + encoder resync** — the bridge keeps a best-guess position per Yahboom, advancing it by the COMMANDED speeds (dead reckoning), and overwrites it with real wheel-sensor data whenever the wheels turn (encoder resync — "physical truth wins"). Start pose assumed (0,0) facing north (the operator places the bot at a marked spot before power-on). Design rule: odometry is CORRECTION, never PERMISSION — the bot never waits for odom before moving.
- **Calib vocabulary freeze** — calib accepts only the proven command set (go to (x,y), home, face…, say yes/no, turn, forward/back, stop, exec, results); everything else (landmarks/shapes/waypaths = demo-mode) is rejected with the accepted list. No command can silently do nothing.
- **Results reader** — CLI `results`: prints calib_results.jsonl as a table (when, runbook, bot, drift, auto PASS/FAIL, human verdict) — the persistent measurement log.
- **Routing-only evaluator** — in calib the evaluator ONLY parses typed commands and writes assignments; the 3B executor cycle (LLM decides assignments for sim bots) is off — no model warm-up, no Worldstate need, and the executor can never clobber operator assignments (that clobbering happened live). One writer per command.
- **Shared trace JSONL** — one append-only log (k1_trace_<run-id>.jsonl, name historical) recording every bot's odom sample: time, bot, pose, source (start/odom_raw/integrated), current target. One file answers "where was bot X at time T and why".
- **Belief feedback** — on goto/home/face commands the CLI prints what the bot itself believes (position + distance to target) and warns "ALREADY THERE" when inside the deadband — a no-op is distinguishable from a failure.
- **Exec-stepper** — the interactive part of `exec <runbook>`: walks a predefined route leg by leg (command → Enter → reads the bot's odom → drift), ends with one result record (auto PASS/FAIL + human y/n). Hardening = per-leg no-move detection, stale-odom warning, NO-MOVE verdict, bot-prefixed exec.
- **restart_calib.sh** — one command to stop+relaunch evaluator & bridge with the captured environment (a running Python process keeps its old code — the restart is required after every code change and was a 4-line manual dance typed 6× on 09-08).
- **TeamCaptain / algorithm-enhanced / pure-llm** (naming decisions 2026-09-12) — "TeamCaptain" is RESERVED for the planned ROS 2 node (ADR-A07, v7): path executor + watchdog + augmented world model. The bridge's current flag layer (R2K_TEAMCAPTAIN*, Slice 1/2) = "algorithm-enhanced" scope, to be scope-reduced in v6.9's `--mode pure-llm` (zero tactical constants — the honest 3B baseline). Watchdog = a v7 module: Kalman ball prediction vs reality → divergence-triggered failsafe/re-prompt.
- **R2K_TEAMCAPTAIN** — master switch for the bridge's CPU-side skill layer (kick state machine: behind-ball stand-off 0.6→0.45 m shrinking, execute gate 0.4 m + behind-hemisphere ±1.2 rad; goalie-Y smoothing; idle facing). =1: the bridge recomputes kick approach/aim from LIVE ball positions every 10 Hz tick instead of trusting the ~700 ms-stale LLM snapshot. Validated: 0.20 → 0.94 blue goals/match. Default OFF in the launcher (legacy) — flip ON for match quality.
- **R2K_PASS_RESOLVE** (pass resolve, Slice 2, requires TEAMCAPTAIN) — rewrites degenerate LLM kick targets: shoot-first gate (ball beyond X=3.0 AND no red bot in the 0.7 m corridor to the goal mouth → shot), else redirect to the best forward teammate (open space + clear lane, `resolve_pass_target`). Fixes the measured 74% center/own-side kick aims.
- **R2K_WING_STAGE** (Slice 2, requires TEAMCAPTAIN) — wing staging: ball deep in attack + no wide blue bot → send the farthest field bot to the wing (bridge:1580). Formation change, opt-in.
- **Goalie wandering** — the LLM assigns its goalie non-goalie behavior (chase/move upfield): measured blue_1 |x| 0.01–6.0 m across runs (goal line is |x|=4.5). The TC goalie-Y smoothing only stabilizes lateral wobble ON the line — it cannot prevent upfield orders. Deterministic fix (goalie position gate) = TeamCaptain node scope (role locks, ADR-A07).
- **kick-FAKE (B1)** — the IFA demo kick: `kick ball` fast-path → waypoints with push-through overshoot (the bot walks INTO the ball — looks like a kick, is a drive-through). **Worked at the IFA**; tuning note: the Yahboom needs high speed for a nicely moving ball (calib speeds too slow for the demo push).

---

## Appendix C — U22 regression runbook (native Ubuntu 22.04 + ROS 2 Humble)

> Purpose: the cross-platform regression gate before any merge into `main`.
> U22 = native (no Docker); U24 = Docker (both pull the same origin refs).
> Run after `git fetch origin && git checkout <branch>` on U22.

### C.1 Session preconditions (once per U22 machine)

```bash
lsb_release -d                          # must read: Ubuntu 22.04 LTS
ros2 --help >/dev/null 2>&1 && echo "ROS 2 ok" || echo "ROS 2 missing -> step C.2"
```

### C.2 Environment (first U22 provision only)

```bash
cd ~/R2K-HSL/core && ./install.sh
```

Installs: ROS 2 Humble + Gazebo (`ros-humble-desktop`, `gazebo`,
`ros-humble-gazebo-ros-pkgs`), colcon, `numpy<2.0` (Gazebo pin — do not
bump), builds `ros2_ws` AND the native `uros_ws` (micro-ROS agent — the
Yahboom leg; Docker is banned here by architecture axiom 6 — FastDDS SHM).

### C.3 Build the workspace — **the regression's core step**

```bash
source /opt/ros/humble/setup.bash
cd ~/R2K-HSL/core/src/ros2_ws
colcon build
source install/setup.bash
```

**This is the first native build of `booster_msgs` + `booster_ros2_interface`**
(the vendor interface package that unblocked `/Kev1n/odometer_state`).

Known failure mode: `numpy/ndarrayobject.h: No such file or directory` →
stale cached `build/`/`install/` → `rm -rf build install` and rebuild.
Do NOT install `python3-numpy-dev`, do NOT set CFLAGS (documented red
herrings). On a fresh clone this should not occur.

### C.4 Fast tier (the core regression, ~30 s)

```bash
cd ~/R2K-HSL/core/src
python3 -m pytest tests/ --skip-slow -q \
  --ignore=tests/test_adaptive_horizon.py \
  --ignore=tests/test_chart_specs.py
```

**Expected: `251 passed, 20 failed, 6 skipped`** — the 20 are the
documented pre-existing `test_i3_sweep` breakage (origin: the uncommitted
09-05→09-08 backlog, NOT a platform issue). **Any failure outside
i3_sweep = a U22 finding** → fix-forward commit on the same branch,
push, re-pull, re-run.

### C.5 Sim battery (offline routing, ~5 s)

```bash
cd ~/R2K-HSL/core && python3 -c "
import sys; sys.path.insert(0, 'tools')
import calib_test
ok, total, _ = calib_test.run_sim_battery()
print(f'SIM BATTERY: {ok}/{total}')"
```

**Expected: `12/12`.**

### C.6 Full tier (real 120 s Gazebo matches — needs services up)

Bring-up, in order:

```bash
# 1. Ollama, reachable at 0.0.0.0:11434 (Docker/other hosts need the 0.0.0.0 bind)
OLLAMA_HOST=0.0.0.0 nohup ollama serve > /tmp/r2k_ollama.log 2>&1 &
#    or the systemd override (Environment="OLLAMA_HOST=0.0.0.0").
#    First U22 provision: ollama pull qwen2.5:3b
curl -s http://localhost:11434/api/tags | head -3   # verify up + model listed

# 2. Gazebo test world is launched BY the slow tests themselves (headless) —
#    no manual gzserver needed. ROS 2 env must be sourced:
source /opt/ros/humble/setup.bash
source ~/R2K-HSL/core/src/ros2_ws/install/setup.bash

# 3. Full suite (slow tests included, ~2-3 min each, real matches):
cd ~/R2K-HSL/core/src
python3 -m pytest tests/ -v
```

**Expected:** fast-tier results as C.4 (i3_sweep failures included), plus
the non-functional slow tests (`test_non_functional.py`) — real 120 s
matches with per-scenario KPI assertions. A slow-test failure on U22 is a
finding: compare against the U24 baseline (same commit), fix-forward or
document platform deltas.

**Slow-tier skips:** tests gracefully skip when `rclpy` is missing —
if they skip wholesale, the ROS env was not sourced in the SAME shell as
pytest.

### C.7 Record + close the loop

- Append a dated changelog entry: `U22 regression: fast tier X passed /
  20 i3_sweep, battery Y/12, full tier Z, findings …`
- U22-specific fixes → commit on the SAME topic branch → `git push` →
  U24 `git pull` → both platforms green
- **Merge gate:** only when BOTH platforms pass → PRs per topic branch
  into `main` → tag the merge state (pattern: `v6.8-field-day`)

### C.8 U22 platform deltas to watch (not failures, differences)

- micro-ROS/Yahboom: `uros_ws` native on U22 (FastDDS SHM axiom — never
  Docker) vs absent on U24
- Docker-owned build dirs: if this U22 clone ever ran Docker-side builds,
  root-owned `build/`/`install/` may need `sudo rm -rf` first
- Gazebo GPU: slow tests run headless gzserver — fine without a display,
  but an NVIDIA suspend-bug history (Xid 31) means after a suspend/resume,
  re-verify Gazebo before blaming the suite
