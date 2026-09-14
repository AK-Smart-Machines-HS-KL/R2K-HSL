# K1 Kick / Head / Odometer Vendor-Documentation Audit + Hardware Probe Plan (v7)

> **Date:** 2026-08-28 (kick/head), 2026-09-04 (odom, §5)
> **Status:** Kick/head audit complete — hardware probe REQUIRED before any kick-abort implementation. Odom audit (§5) complete — ROS-bridge probe REQUIRED before any K1 closed-loop code.
> **Trigger:** User challenged the KB claim "kShoot = autonomous shot toward the goal"; no vendor or logged-hardware source could be found. Odom audit triggered by K1 drift/imprecision + user's claim that Booster never exposed odom as a ROS 2 topic.
> **Scope:** Corrects the v6.4-era KB claims about K1 kick skills; documents the odom-topic ground truth; does not change runtime behavior (relay/launch fixes deferred to the K1 phase)

## 1. The claim under audit

Six ROS2K KB/docs sites state (v6.4 era, no source):

> "The K1's kick skills kShoot (2024) / kVisualKick (2038) are **autonomous** —
> the K1 takes over and chases the ball until kick distance is reached. If the
> ball moves away, the K1 follows indefinitely. Game-stopper."

Sites: `4_EDGE_HARDWARE_SIM2REAL.md` §V6.4 (+ capability matrix),
`8_C3_SOCCER_KNOWLEDGE.md` §6 (kick matrix + chase problem),
`ROS2K_GEM_FAQ.md` Q28, `LESSONS_LEARNED.md`, `scrum_tasks.md` (K1 story),
`gui_v67_discussion.md`.

**Audit result (2026-08-28):** the claim exists ONLY inside our own files.
`grep kShoot docs/SESSION_CHANGELOG.md` → **zero hits** — no hardware session
was ever logged observing this behavior. The claim is folklore, not knowledge.

## 2. Vendor ground truth (verified 2026-08-28)

Sources, in order of authority:

| Source                                                                        | What it is                                                                                                                                                                          |
| ----------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **docs.booster.tech** → Developer Guide → C++ SDK → Motion-Control Interfaces | Official vendor docs (K1, T1, T2). URL: `https://docs.booster.tech/docs/developer-guide/cpp/rpc/motion/`                                                                            |
| `src/booster/b1_loco_api.hpp` | Official `B1LocoClient` SDK header — serves **K1, T1, T2** (vendor-confirmed). **Current as of PR #18 (merged 2026-08-28):** repo now carries the newest snapshot incl. `kSoccer`, `kRotateHeadWithTime = 2043`, and `b1_loco_client.hpp` / `move_controller.hpp` / `robot_shared.hpp` |
| `src/booster/T1 Instruction Manuall Fragments.odt`                            | Official manual, title: **"K1 *and* T1 Instruction Manual"** — shared, not T1-only. Contains only `Move`, `Shoot`, `GetMode`, `LowState` descriptions + embedded team console notes |

Note: `T1InstructionManual.html` is a Feishu webpage dump with **no API content** — useless for API questions.

### 2.1 Kick APIs

| API | Models (vendor) | Min firmware | Vendor description (verbatim) |
|---|---|---|---|
| `Shoot()` / kShoot 2024 | **K1**, T1, T2 | — (absent from compat table) | "Request the firmware-configured powerful kick; **current T1 provides the intended motion** and unavailable transitions fail" |
| `VisualKick(start, version)` / kVisualKick 2038 | **K1**, T1, T2 | **≥ v1.5.2.1** | "Request the firmware-configured visual kick using V1 or V2; missing motions return a state-transition error" |
| `VisualKickVersion` | — | — | `kV1=0` base, `kV2=1` stronger kicking force (`kInsideFoot=10` is its historical name) |

**Contradiction 1:** the vendor describes kicks as "firmware-configured"
requests — **no autonomy, no ball chasing, no goal aiming is documented
anywhere.** Behavior is firmware-internal by design.
**Contradiction 2:** "current T1 provides the intended motion" — on K1,
`Shoot()` may simply **fail** with a state-transition error. The repo header
(PR #18) phrases it precisely: *"Configuration-dependent. No model-name gate.
A model without the required reachable motion returns
kRpcStatusCodeStateTransitionFailed."*

Related firmware action set (discovered, not used by us): `RobotMode::kSoccer = 4`
(supported on K1 and T1) with `kSoccerGait`, `kSoccerLocomotion(4)`,
`kSoccerKicking(5)` postures, actions `kShoot=9` ("Powerful-shot control"),
`kGoalie=11` ("Goalie control"), `kVisualKickV1=14`, and
`RobocupBehaviorStatus RUNNING/SHOOTING/PASSING`. Current firmware line: v1.7.2.

### 2.2 Head APIs — vendor-confirmed for K1

| API | Models | Min firmware | Notes |
|---|---|---|---|
| `RotateHead(pitch, yaw)` (2004) | **K1**, T1, T2 | ≥ v1.0.0 | absolute angles, radians; body `{"pitch": float, "yaw": float}` |
| `RotateHeadWithTime(pitch, yaw, time_ms)` | **K1**, T1, T2 | — | in repo since PR #18 as `kRotateHeadWithTime = 2043` |
| `RotateHeadWithDirection(pitch_dir, yaw_dir)` (2006) | **K1**, T1, T2 | — | jog via `-1/0/+1` |

K1 joint indices: `kHeadYaw=0`, `kHeadPitch=1` (2 head DoF). **No angle limits
documented** — clamp constants in bridge code must be tuned on hardware.
Required `RobotMode` for head control is undocumented — probe on hardware.

### 2.3 What stands (not affected by the audit)

- `Move(vx, vy, vyaw)` (2001) + `ChangeMode` (2000): K1-supported, ≥ v1.0.0,
  AND empirically verified by the team (console session embedded in the ODT:
  `ssh booster@10.42.0.102`, prepare→walking→move). Bridge behavior is solid.

## 3. Hardware probe protocol (GATE 0 for all kick-abort work)

Per Axiom 9: behavior on the physical robot is the only ground truth. Every
step below MUST be logged in `SESSION_CHANGELOG.md` immediately after execution.

1. **Firmware check:** `GetRobotInfo` (api 2022) → is firmware ≥ v1.5.2.1?
   (Below that, VisualKick is absent entirely.)
2. **On-robot SDK inspection:** `ssh booster@10.42.0.102
   "find /opt/booster -name '*loco_api*' -o -name '*.hpp' | head"` → compare
   the robot's own header against our snapshot (api_id list, kSoccer presence).
3. **Probe matrix** (robot on stand,Prepare mode; then kWalking):
   - `VisualKick(start=true, version=0)` → observe: motion? ball tracking?
     termination condition? reaction to `kChangeMode` (2000)?
   - `VisualKick(start=true, version=1)` → same, note force difference.
   - `Shoot()` → expect possible state-transition failure on K1; record result.
   - Ball-motion test: trigger kick, roll ball away mid-skill → does the K1
     chase? terminate? This is THE experiment for the "chase forever" claim.
4. **Record per row:** behavior, termination, abort success, joint heat.

## 4. Decision gates (after the probe)

| Gate | Options |
|---|---|
| Kick execution | (a) `VisualKick` only (vendor-confirmed K1) · (b) firmware **Soccer mode** evaluation (mode 4 — built-in kicking/goalie may replace our kick handling entirely) · (c) no firmware kick; drive-and-push like Yahboom |
| Chase handling | (a) abort design as planned (`/ball/motion_change` → kChangeMode) — only if chasing is observed · (b) unnecessary if skills self-terminate · (c) avoid autonomous skills entirely (Soccer-mode/gait approach) |
| Head control | Proceed with the calibration head-turn plan (2004 primary, 2006 jog); tune clamp limits on hardware; verify required mode |

**Until Gate results exist:** all six KB sites carry an UNVERIFIED annotation,
and no abort code may be written (scrum GATE 0).

---

## 5. Odometer topic audit (2026-09-04) — "odom is relayed to the fleet"

> **[CORRECTION 2026-09-06 — §5.1/§5.2 conclusions RETRACTED by live test.]**
> `/Kev1n/odometer_state` FLOWS at ~490 Hz (x/y/theta updating). The audit's
> "eternal silence" and "topic does not exist on the robot" were artifacts:
> `booster_interface` was never colcon-built, so every past `ros2 topic echo`
> failed silently — no subscriber could ever exist, making "zero data
> observations" vacuous. The robot's SSH topic list (2026-09-06) shows
> `/odometer_state` exists and the relay forwards it. Lesson: a topic may only
> be called silent after its message type is built and a subscriber attaches.
> Vendor-docs note (user): docs.booster.tech Low-Level Topics = C++ SDK
> transport, NOT the ROS 2 surface. See `src/yahboom/YAHBOOM_KNOWLEDGE.md` §7.

> Folklore-discipline instance #2 (same pattern as §1: a claim exists only in
> our own files, zero logged observations, vendor docs say otherwise).

**Trigger:** K1 drifting + imprecise in demo/calib; user asserted Booster never
exposed odom values as a ROS 2 topic. Verified against vendor docs.

### 5.1 The claim under audit

> "`/Kev1n/odometer_state` (Odometer) + IMU LowState are already relayed to
> the fleet by `external_relay.py` — closing the hardware loop is a
> subscription away."

Sites (all annotated in place, 2026-09-04):

| Site | Form of the claim |
| --- | --- |
| `launch_r2k.sh:320, :449` | **Production code**: K1-ready gate greps topic **existence** — matches our own relay's silent publisher; proves "relay alive", never "odom available" |
| `docs/outdated/ifa_planning/mgt_v68.md` | "already relayed... a subscription away" + claims LowState IMU relayed (**false** — no LowState leg exists in either relay) |
| `docs/outdated/mgt_v7.md`, `plan_v7_coarse.md` | Propagated into v7 closed-loop planning |
| `docs/outdated/ifa_planning/plan_v68.md`, `mgt_demo_ifa.md` (same dir) | calib_cli `--odom` watch mode designed against the topic |
| `user doc/.../4_06_SPECIFICATION_BoosterK1_Integration.md` | `/odometer_state` listed as PRODUCTION API |
| `utils/ros2_relay/README.md` | Odometer_States listed among relayed topics (refresh-rate field empty) |
| `utils/ros2_relay/internal_relay.py`, `external_relay.py` | Subscribe/publish `/odometer_state` typed `booster_interface.msg.Odometer`; both carry an authoring TODO ("match the actual message type") — the assumption was never verified |
| `SESSION_CHANGELOG:411` (2026-08-26) | Only logged "observation": host saw no odometer_state — **mis-attributed** to FastDDS NIC routing; the deeper cause is that the internal relay subscribes a topic that does not exist on the robot |

**Audit result (2026-09-04):** `grep odometer SESSION_CHANGELOG*.md` → zero
sessions ever observed DATA on `/Kev1n/odometer_state`. The topic is a silent
placeholder created by our own relay. Folklore, not knowledge.

### 5.2 Vendor ground truth (verified 2026-09-04)

Source: **docs.booster.tech** → Developer Guide → C++ SDK →
**Low-Level Topics** (`https://docs.booster.tech/docs/developer-guide/cpp/low-level-topics/`):

1. `rt/odometer_state` (`b1::kTopicOdometerState`, type
   `booster_interface::msg::Odometer`, fw ≥ v1.3.1.1) is an **SDK-internal DDS
   channel** — subscribable ONLY via the SDK's `ChannelSubscriber` /
   `ChannelFactory`, **not a ROS 2 topic**. Our relays assume a plain ROS 2
   topic named `/odometer_state` of the same type — wrong name and wrong
   transport layer. Hence: eternal silence.
2. The ONLY ROS-standard odom path is `rt/odom` (`b1::kTopicRosOdometer`,
   type `nav_msgs/msg/Odometry`) — vendor doc: **"requires the ROS bridge"**,
   firmware **≥ v1.7.1.0**.
3. No odom **query RPC** exists in the API enum (only `kResetOdometry` 2031).
4. Verified on the robot's ROS surface today: `/Kev1n/LocoApiTopicReq/Resp`
   (Move empirically verified, §2.3) — a ROS-facing wrapper exists, so the
   ROS-bridge probe (§5.4) is plausibly positive — **plausibility is not
   evidence**.
5. **Kev1n firmware = v1.7.2.0** (user-verified live via `booster-cli
   --version`, 2026-09-04) — the `rt/odom` firmware gate is **GREEN**.

### 5.3 Adjacent finding — bridge K1 velocity profile (same session)

The bridge sends sim-tuned velocities to the K1 with no hardware clamp
(`ollama_sandbox_bridge.py:531-552`): yaw up to **2.5 rad/s** (gain 3.0),
binary `vx` **0.8/0.2 m/s**, no terminal braking, drive+turn simultaneous.
The vendor's own K1-safe reference (`src/booster/move_controller.hpp`,
`MoveToTarget`): yaw **≤ 1.0 rad/s** (gain 1.2), **two-phase** (rotate first
when heading error ≥ 0.2 rad, then translate holding heading, yaw ± 0.5),
**distance-proportional braking** (dist < 0.2 m → limit = max(0.1, dist);
dist < 0.1 m → ≥ 0.05 m/s crawl), success tolerance 0.20 m, 20 ms command
period. This is a root cause of the observed drift/imprecision independent of
the missing feedback. Fix belongs to the K1 phase (Step 4 of the
hardware-closed-loop plan, `mgt` 2026-09-04).

### 5.4 Probe gate (GATE — before any K1 closed-loop code)

On Kev1n (powered, on the maker4 network):

1. `ros2 topic list | grep -i odom` → is `rt/odom` live (ROS bridge running)?
2. If live: `ros2 topic echo /rt/odom --once` (or `rt/odom`) → confirm
   `nav_msgs/Odometry` data + note rate. Then: rewire `internal_relay.py` to
   subscribe `rt/odom` (**plain ROS type — the booster_interface import
   assumption dies**), external relay publishes it, k1 relay entry gets
   `odom_topic` → identical closed-loop path as the Yahboom (Phase 2 design,
   shared seams: odom_topic contract / alignment / velocity profile).
3. If NOT live: K1 stays open-loop with the fixed velocity profile (§5.3);
   external feedback becomes a v7 decision (SDK channel app on the host =
   heavier fallback, ChannelFactory subscribes from an external machine).

**Until Gate results exist:** every site above carries the folklore
annotation, no K1 closed-loop code may rely on odom, and the
`launch_r2k.sh` K1-ready gate keeps its current semantics (relay-alive) —
explicitly NOT an odom availability signal.
