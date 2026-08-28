# K1 Kick / Head Vendor-Documentation Audit + Hardware Probe Plan (v7)

> **Date:** 2026-08-28
> **Status:** Audit complete — hardware probe REQUIRED before any kick-abort implementation
> **Trigger:** User challenged the KB claim "kShoot = autonomous shot toward the goal"; no vendor or logged-hardware source could be found
> **Scope:** Corrects the v6.4-era KB claims about K1 kick skills; does not change any code

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
| `src/booster/b1_loco_api.hpp`                                                 | Official `B1LocoClient` SDK header — serves **K1, T1, T2** (vendor-confirmed). Our copy is an **older snapshot** (no kSoccer, no RotateHeadWithTime)                                |
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
`Shoot()` may simply **fail** with a state-transition error.

Related firmware action set (discovered, not used by us): `RobotMode::kSoccer = 4`
(supported on K1 and T1) with `kSoccerGait`, `kSoccerLocomotion(4)`,
`kSoccerKicking(5)` postures, actions `kShoot=9` ("Powerful-shot control"),
`kGoalie=11` ("Goalie control"), `kVisualKickV1=14`, and
`RobocupBehaviorStatus RUNNING/SHOOTING/PASSING`. Current firmware line: v1.7.2.

### 2.2 Head APIs — vendor-confirmed for K1

| API | Models | Min firmware | Notes |
|---|---|---|---|
| `RotateHead(pitch, yaw)` (2004) | **K1**, T1, T2 | ≥ v1.0.0 | absolute angles, radians; body `{"pitch": float, "yaw": float}` |
| `RotateHeadWithTime(pitch, yaw, time_ms)` | **K1**, T1, T2 | — | NOT in our hpp snapshot — newer SDK |
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
