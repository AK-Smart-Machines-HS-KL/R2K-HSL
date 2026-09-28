# K1 Kick POC — Status & Todos

> Session 2026-09-25. Kick channel through the relay pair, typed
> `brain/Kick`, bridging host `/{prefix}/kick_ball` to the robot-local
> `/kick_ball` consumed by Booster's vendor soccer agent
> (`com.boosterobotics.soccer`). Predecessor: `k1_kick_head_vendor_audit.md`
> (GATE 0 probe protocol, RPC matrix). Companion for future skill additions:
> a cheat sheet "Adding a new skill as ROS 2 topic to ROS2K" is planned.

## Architecture (verified end-to-end on the relay leg)

```
host bridge (NOT yet built)        K1 robot
──────────────────────            ────────────────────────────────────────
                                   soccer agent (com.boosterobotics.soccer)
                                     ├── subscriber /kick_ball (brain/Kick)
                                     └── vendor kick controller
                                   ▲
  /Kev1n/kick_ball (brain/Kick)    │ robot-local /kick_ball (brain/Kick)
  │   │                            │
  │   │ DDS over maker4            │ UDP 6003 (serialized brain/Kick)
  │   ▼                            │
  │  external_relay.py ──────────► internal_relay.py
  │  (sub /Kev1n/kick_ball)        (pub /kick_ball)
  │  FASTRTPS profile cleared      FastDDS profile (robot-local airgap)
  └── host bridge will publish here (Step 2, not yet built)
```

Key facts (all verified on hardware 2026-09-25 unless noted):

| Item | Value | Source |
|---|---|---|
| Message type | `brain/msg/Kick` — Header + x, y, dir, goal_x, goal_y, robot_theta_to_field, power (float64 all) | repo `core/src/ros2_ws/src/brain/msg/Kick.msg` ≡ K1 `/opt/booster/booster_agent_data/data/agents/extract/com.boosterobotics.soccer/agent/brain/share/brain/msg/Kick.msg` (byte-identical incl. `disired` typo — shared provenance) |
| Fleet topic | `/{prefix}/kick_ball` (e.g. `/Kev1n/kick_ball`) | external relay subscription |
| Robot-local topic | `/kick_ball` | internal relay publisher; matches vendor controller's expected topic |
| UDP port | 6003 (new; 6000=Req, 6001=Resp, 6002=Odom) | both relay files, PORT_KICK |
| Robot brain source | `/opt/booster/booster_agent_data/data/agents/extract/com.boosterobotics.soccer/agent/local_setup.bash` | verified via `sudo find . -iname Kick.msg` on the K1 (2026-09-25) — this is the **vendor** soccer agent, not a `robocup_demo` checkout (which is reference material only) |
| Controller subscribers | 2 (node name `_CREATED_BY_BARE_DDS_APP_`, BEST_EFFORT QoS — bare-DDS vendor code, not ROS 2 nodes) | `ros2 topic info -v /kick_ball` on the K1, 2026-09-25 |
| Publisher QoS | RELIABLE / VOLATILE (our internal relay) | compatible with the BEST_EFFORT subscribers (RELIABLE pub ≥ BEST_EFFORT sub; reverse would fail) |
| Robot ROS distro | humble (`/opt/ros/humble`) | deploy_vision.sh + relay services |
| SSH user on the K1 | `booster` | `deploy_relay.sh` config |
| K1 current IP | `192.168.0.69` (home/lab subnet — differs from the README's `10.42.0.x` maker4 examples) | user-supplied |
| Robot hostname | `Kevin` (note: not `Kev1n` — systemd unit names use `Kev1n`, the hostname is `Kevin`) | journalctl output `Sep 25 ... Kevin` |
| Deployed relay files | `external_relay.py`, `internal_relay.py` at `/home/booster/Workspace/ros2_relay/` | `deploy_relay.sh` scp step |
| Systemd units | `internal-relay.service`, `external-relay.service` (both `enabled`, `active`) | journalctl post-deploy |

## Step 1 — Relay extension: DONE ✅

Files modified (uncommitted, on `main`):

- `utils/ros2_relay/external_relay.py` — `from brain.msg import Kick`; subscribes `/{prefix}/kick_ball`; `kick_callback` forwards `serialize_message(msg)` to UDP 6003 (pure pass-through, exact Req-leg pattern; no RPC translation).
- `utils/ros2_relay/internal_relay.py` — `from brain.msg import Kick`; UDP 6003 listener → `deserialize_message(data, Kick)` → publishes robot-local `/kick_ball`. No `KICK_API_MAP`/JSON parsing (that was the earlier discarded design — see "Design history" below).
- `utils/ros2_relay/system/external-relay.service` — added `source /opt/booster/booster_agent_data/data/agents/extract/com.boosterobotics.soccer/agent/local_setup.bash` after the BoosterRos2 + BoosterRos2Interface sources.
- `utils/ros2_relay/system/internal-relay.service` — same source line.
- `utils/ros2_relay/README.md` — kick_ball topic documented (vendor soccer agent as brain/controller source; robocup_demo explicitly noted as reference-only).

Deployed to the K1 at 192.168.0.69 via `./deploy_relay.sh 192.168.0.69 Kev1n`. Both services `active` and logged `Relay Active` lines (the RCLError traceback in the journal is the OLD instance's teardown noise — double `rclpy.shutdown()` in the `finally` block; cosmetic, pre-existing pattern, not caused by our change).

## Validation results (2026-09-25)

| Gate | Check | Result |
|---|---|---|
| 1 | Service health (journalctl) | PASS — both `active`; `Relay Active` lines present; brain import succeeded (the log line only prints after `from brain.msg import Kick` resolves at module load) |
| 2 | Kick.msg type identity (robot vs repo) | PASS — byte-identical, including the `disired` vendor typo on both sides → DDS typehash match guaranteed for the host↔robot leg |
| 3 | Kick controller present on `/kick_ball` | PASS — 2 subscribers (vendor soccer agent, bare-DDS participants); our internal relay is the 1 publisher |
| 4 | Host-side fleet topic visible | NOT YET RUN — pending `docker exec core_gazebo ... ros2 topic list \| grep Kev1n` |
| 5 | End-to-end chain round-trip (host pub → robot echo) | **FAILED / INCONCLUSIVE** — the user published a `power: 0.0` test message from the host container; nothing appeared in `ros2 topic echo /kick_ball` on the robot. Cause under investigation — see "Open issues" §A. |
| 6 | Live kick (power 6.0, stand) | NOT YET ATTEMPTED — blocked on Gate 5 resolving first |

## Open issues

### A. End-to-end chain test produced nothing on the robot echo (Gate 5) — INVESTIGATE

Symptom: host published one `brain/Kick` on `/Kev1n/kick_ball`; the robot's `ros2 topic echo /kick_ball` showed nothing.

Candidate causes (in priority order):

1. **Host env / DDS discovery mismatch.** The host `ros2 topic pub` ran inside `docker exec core_gazebo`. If the container's ROS_DOMAIN_ID or rmw profile differs from the relay's fleet-side env, the pub never reaches the external relay's subscription. Verify: `docker exec core_gazebo bash -c "echo DOM=\$ROS_DOMAIN_ID RMW=\$RMW_IMPLEMENTATION"` and compare with the external-relay.service env (FASTRTPS_DEFAULT_PROFILES_FILE is cleared there; DOMAIN defaults to 0). The container compose may set a non-zero domain or CycloneDDS.
2. **The host didn't actually see `/Kev1n/kick_ball` (Gate 4 was skipped).** If `ros2 topic list | grep Kev1n` doesn't show the new topic, the pub went nowhere. Run Gate 4 first before re-attempting the round-trip.
3. **QoS incompatibility on the fleet leg (unlikely but check).** The external relay's subscription uses default QoS (RELIABLE/VOLATILE, depth 10). `ros2 topic pub --once` defaults to RELIABLE. Compatible. Not the prime suspect.
4. **`--once` exit racing the DDS write.** `ros2 topic pub --once` can exit before the writer is matched. Try without `--once` (steady stream, Ctrl+C after a second) or `--times 5` to rule this out.
5. **Type hash mismatch across ROS distros (host container = humble; if the host used jazzy natively the typehash negotiation could drop the sample).** The container uses humble — should be fine. But verify the host pub was issued INSIDE the container, not against the host's `/opt/ros/jazzy` (which would be a different distro → rmw_fastrtps typehash mismatch with the humble-built relay types). The provided command uses `docker exec core_gazebo` — confirm that's where it actually ran.

Recommended next probe (after confirming Gate 4 shows the topic):
- On host: `docker exec core_gazebo bash -c "source /opt/ros/humble/setup.bash && source /workspace/ros2_ws/install/setup.bash && ros2 topic pub --times 5 /Kev1n/kick_ball brain/msg/Kick '{x: 0.0, y: 0.0, dir: 0.0, goal_x: 5.0, goal_y: 0.0, robot_theta_to_field: 0.0, power: 0.0}'"`
- Watch the robot echo in parallel.
- Also check the external relay's own log for any kick_callback hits: `ssh booster@192.168.0.69 "journalctl -u external-relay --since '2 min ago' --no-pager | tail -20"`.

### B. Cosmetic RCLError traceback on relay teardown

The old relay instance's `finally: rclpy.shutdown()` double-calls shutdown and throws `RCLError: rcl_shutdown already called`. Pre-existing pattern (axiom 7 / watchdog teardown noise). Hygiene fix for a future pass: guard with `if rclpy.ok(): rclpy.shutdown()` in both relay `main()` finally blocks. Not a blocker; noted for the cheat sheet's "redeploy hygiene" section.

### C. Hostname vs unit name

The K1's hostname is `Kevin` (journalctl `Sep 25 ... Kevin systemd...`); the systemd unit + topic prefix use `Kev1n`. Not a problem (they're independent strings) but worth documenting in the cheat sheet so future skill additions don't confuse the two.

## Step 2 — Bridge: PENDING

Add a `hw_kick` action to `core/src/ai_tactics/ollama_sandbox_bridge.py` (calib/demo path only — match mode keeps the `{"mode": 1}` placeholder until the GATE 0 probe results land):

- `_ensure_kick_pub(hw_name, hw_info)` — lazy `brain/Kick` publisher on `<ns>/kick_ball`, ns derived from the k1 relay topic like `_ensure_odom_watch` (`rsplit('/', 1)[0]` → `/Kev1n`).
- New dispatch branch `action == 'hw_kick'` (distinct from match-mode `action == 'kick'` at bridge:1498, which requires `self.ball_pos`). Pose-independent, id-keyed one-shot (done-set like `_head_done`). k1-only; other hw types → warn.
- Field fill for the POC: `x=0, y=0, dir=0, goal_x=5.0, goal_y=0.0, robot_theta_to_field=0.0, power=6.0` (ball-at-feet, goalshot force — mirroring `goToBallAndKick.py`'s goalshot power). Real geometry from Worldstate/vision later.
- Match mode untouched (GATE 0: mode-1 placeholder stays until probe results clear).
- "kick stop" verb → bridge sends RPC 2038 `{"start": false}` via the existing `/Kev1n/LocoApiTopicReq` leg (the abort pattern from `goToBallAndKick.py` `manual_cancel_callback`). No relay change needed.

## Step 3 — Evaluator + calib CLI: PENDING

- `core/src/ai_tactics/r2k_evaluator.py`: kick fast-path verbs `kick` / `kick stop`; bare verb → k1 slot (calib convention like bare `turn`); `_demo_set_fast_cmd(bot, {"action": "hw_kick", "kind": "vk1"|"abort", "id": <fresh>}, note)`.
- `core/tools/calib_cli.py`: mirror the verbs, instant feedback, sample list entries (`k1 kick`, `k1 kick stop`), help text. Dead-slot warning when no k1 in relay (existing pattern).
- Sim mode / no k1 in relay → dead-slot warning (existing pattern from `_detect_mode`).

## Step 4 — Tests + docs: PENDING

- Fast tier: extend `core/src/tests/test_head_face.py` pattern with a kick fast-path test (evaluator verb → hw_kick cmd). Run `python3 -m pytest tests/ --skip-slow`.
- `core/docs/calibration_cheat_sheet.md`: kick command section (verbs, probe matrix pointer, safety: `kick stop` + manual RPC 2038 abort, stand/clearance preconditions).
- `core/docs/vocabulary_cheat_sheet.md`: CLI verbs → parsing layers entry for `kick`/`kick stop`.
- Session changelog entry (per AGENTS.md protocol) at session end via `./docs/session_entry.sh`.

## Planned cheat sheet: "Adding a new skill as ROS 2 topic to ROS2K"

The user requested a future cheat sheet with this title, covering the pattern we just walked through — generalized for the NEXT skill addition (head movements are the planned follow-on). It should capture:

1. **Skill contract** — define the ROS 2 message type (existing package or new), the fleet topic `/{prefix}/<skill_topic>`, and the robot-local topic the vendor code consumes.
2. **Robot-side ground truth first** — `ssh` to the robot, `find` the msg definition under `/opt/booster/booster_agent_data/...`, `cat` it, diff against the repo copy. **Never assume the topic/type exists from a branch ReadMe alone** (the robocup_demo folklore cost us a round trip).
3. **Relay extension** — add a UDP port + a subscription (external) and a publisher (internal) in the relay pair; pure pass-through via `serialize_message`/`deserialize_message`, no business logic in the relay.
4. **Robot env chain in the systemd services** — add the `local_setup.bash` source line that provides the msg package; verify the chain imports in an interactive SSH session BEFORE deploying (the `ros2: command not found` trap: non-interactive SSH skips `.bashrc`; `local_setup.bash` never chains the underlay — source `/opt/ros/<distro>/setup.bash` + vendor setups first).
5. **Deploy** — `./deploy_relay.sh <IP> <prefix>`; wait ~45s (ExecStartPre sleeps); `journalctl` health check; the RCLError-on-restart traceback is cosmetic (old instance teardown).
6. **Validation ladder** — service health → msg type identity → controller subscriber present → host topic visible → end-to-end round-trip (pub host / echo robot) → live skill test (operator decision, safety preconditions).
7. **Host-side bridge wiring** — lazy publisher per k1 bot, id-keyed one-shot dispatch action with a distinct name from any match-mode action, calib/demo-gated until the probe gates clear.
8. **Evaluator + CLI mirror** — fast-path verbs in both files (CLI mirrors evaluator rules), dead-slot warnings when the target hw isn't in the relay.
9. **Abort path** — every skill needs a documented abort (kick: RPC 2038 `{"start": false}` via the existing Req leg; head: RPC 2004 zero pose or mode switch).
10. **Naming gotchas** — hostname (`Kevin`) vs topic prefix (`Kev1n`) are independent; fleet topic name mirrors the robot-local topic name (the LocoApiTopicReq convention) to avoid confusion; `local_setup.bash` ≠ `setup.bash` (underlay chaining).

Head movements (the planned follow-on skill) will exercise the same pattern with: message type = vendor head pose msg (TBD — likely `booster_interface` or a soccer-agent msg), fleet topic `/{prefix}/<head_topic>`, robot-local controller = the soccer agent's head controller, abort = RPC 2004 zero pose or mode switch.

## Design history (for the cheat sheet's "lessons" section)

The kick channel went through three designs this session, each correcting a verification gap:

1. **std_msgs/String + JSON api-name map in the internal relay** (vk1/vk2/vk_stop/shoot → RPC 2038/2024). Rejected: user corrected to a custom msg.
2. **A new `kick_ball.msg`** in the brain package. Rejected: no such file exists in any branch (verified across 40 refs) — the user clarified it was the EXISTING `Kick.msg` all along. Lesson: the prior `feature/skill/GoToBallAndKick` branch's `goToBallAndKick.py` already publishes `brain/Kick` to robot-local `/kick_ball` — that's the canonical contract; we match it, not invent one.
3. **Pure `brain/Kick` pass-through** (final design) — the relay carries the same type the vendor controller already consumes; no RPC translation in the relay; the soccer agent IS the kick executor. This made the robot-side deployment trivial (brain already on the K1 via the vendor soccer agent — zero colcon, zero on-robot build) and pushed the "which RPC does the actual kick" question into the vendor controller, which is exactly where GATE 0 wanted the probe to land.

Topic name: started as `/{prefix}/kick_ball`, user changed to `/{prefix}/kick`, then back to `/{prefix}/kick_ball` to mirror the LocoApiTopicReq convention (fleet `/Kev1n/kick_ball` ↔ robot-local `/kick_ball`).

## Blockers / next session entry point

1. **Resolve Gate 5** — why the host→robot round-trip showed nothing. Start with Gate 4 (host topic visibility) and the env-discovery probe in §A. Most likely cause: host container DDS env (domain/rmw) mismatch with the relay's fleet side.
2. Once the chain round-trips, run Phase 7 (live kick, `power: 6.0`, robot on stand, abort command ready) — fills the vendor-audit §3 probe matrix row for the controller path.
3. Then proceed to Step 2 (bridge `hw_kick` action) — the chain being verified first de-risks the bridge work.