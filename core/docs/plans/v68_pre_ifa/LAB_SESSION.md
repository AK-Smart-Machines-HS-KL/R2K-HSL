# Lab Session Runbook — single pre-IFA session (90-120 min)

**Print or open on tablet. Everything below is executed ONCE, in order, changelog-logged.**
**Detailed step-by-step execution (Trello cards): [LAB_SESSION_cards.md](../LAB_SESSION_cards.md)**
Companion docs: [plan_demo_ifa.md](plan_demo_ifa.md) (demo designs) ·
[k1_kick_head_vendor_audit.md](k1_kick_head_vendor_audit.md) (K1-PROBE protocol, section 'Hardware probe protocol') ·
[mgt_demo_ifa.md](mgt_demo_ifa.md) (calibration cure ladder).

## Pre-lab checklist (before leaving the desk)
- [ ] Both K1 Education: battery > 50 % (app or terminal), joints/camera visually OK
- [ ] Yahboom: battery charged; bot1 reachable on 10.42.0.x hotspot
- [ ] Safety stand for K1 kick probes; spotter briefed; e-stop position known
- [ ] 3 ball candidates (sizes) + floor tape + tape measure
- [ ] Laptops: 5090 (bridge + evaluator + Gazebo), SSH to both K1s verified (`ping 10.42.0.122`)
- [ ] This file + `SESSION_CHANGELOG.md` open for logging

## 0 - Safety
K1 probes on the stand unless walking is explicitly required. DAMP → PREP → WALK order
always. PREP ≥ 5 s before WALK. Nothing touches a running robot except the handle.

## Gate agenda
| # | Item | Time |
|---|---|---|
| 1 | Firmware probe (both K1) | 5 min |
| 2 | Head smoke test (2004 in WALKING) | 10 min |
| 3 | Dry-runs: a · b-FAKE · b-LIDAR · d | 30 min |
| 4 | Ball pick (3 sizes) | 15 min |
| 5 | Calibration patterns v1 | 15 min |
| 6 | VisualKick probe (conditional) | 15 min |
| 7 | Changelog logging | 5 min |

## 1 - Firmware probe
`ssh booster@<robot-ip>` then `booster-cli version` → expect `Firmware: 1.x, SDK: 1.3.x`.
Record per robot. Gates: fw ≥ 1.5.2.1 → VisualKick available; fw ≥ 1.6 → RoboCup modules
possible post-IFA. Log both numbers in the changelog.

## 2 - Head smoke test
Goal: does `kRotateHead` (2004) execute while the K1 stands in kWALKING (zero velocity)?
- Sequence: PREP → WALK → send 2004 `{pitch:0, yaw:+0.5}` (≈29°) → observe → 2004 center.
- Via calib_cli if demo task a is already implemented, else direct:
  `ros2 topic pub /Kev1n/LocoApiTopicReq booster_msgs/msg/RpcReqMsg "{header: \"{api_id: 2004}\", body: \"{\\\"pitch\\\": 0.0, \\\"yaw\\\": 0.5}\"}" --once`
- If no motion in WALKING → repeat in PREP (fallback demo path confirmed). Record which.
- Limits sanity: yaw ±59° (1.03 rad), pitch −19°/+49°. Stop at half-range first.

## 3 - Dry-runs
Per demo: set up → run once → note failures → run again. Sim twin visible side-by-side
(hardware_mirror). Record: worked / issue / fix-needed.
- a: "look left" → "say yes" on K1 + Yahboom gimbal (servo_s1/s2; namespaces now /blue_1 + /blue_2)
- b-FAKE: "kick ball" → both bots push simultaneously (mirror)
- b-LIDAR: ball anywhere in front semicircle → detection drives the approach
- d: fork entry 0° push → 45° rotation (choreography only; detection verified in 4)

## 4 - Ball pick
Place each ball at 1 m / 2 m / 3 m in front of the Yahboom → `/scan` returns a cluster?
Record: smallest reliably-detected size + detected diameter vs true diameter (size-gate
calibration). Same for the K1 vision path if the camera stream is up.

## 5 - Calibration patterns
(Procedure details: mgt_demo_ifa.md 'Calibration'.)
- Straight 2 m ×5 at 0.5 m/s → endpoint deviation (tape)
- Rotation 360° ×5 → heading error (toe mark)
- With `calib_cli --odom` (if implemented): CSV per run; else manual table:
  commanded (m, rad) vs odom vs tape-measured — 3 columns per run.

## 6 - VisualKick probe
_CONDITIONAL — only if fw ≥ 1.5.2.1 AND items 1-5 green._
K1 on stand, ball fixed ~0.5 m ahead.
1. `kVisualKick start=true version=0 (V1)` → motion? termination?
2. `version=1 (V2)` → force difference?
3. Ball-motion experiment: trigger kick, roll ball away mid-skill → chase or terminate?
   (THE folklore experiment — `k1_kick_head_vendor_audit.md` §3 step 4.)
4. `Shoot()` → expect state-transition failure; record exact result.
5. Abort test: kChangeMode (2000) mid-skill → does it stop?
Log everything; this feeds the v7 kick-abort design.

## 7 - Changelog logging
One SESSION_CHANGELOG entry: firmware numbers, 2004-in-WALKING result, per-demo status,
ball size decision, calibration table (or CSV path), VisualKick probe results.
Create `LAB_SESSION_RESULTS_<date>.md` next to this file for raw tables.
