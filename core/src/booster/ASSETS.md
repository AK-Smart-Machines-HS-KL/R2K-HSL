# Booster Assets & Sources — K1 reference inventory

**Created:** 2026-08-29 | Canonical upstream: `github.com/BoosterRobotics` (official SDK repo —
header truth), `docs.booster.tech` (official docs). Full vendor audit:
`docs/plans/v68_pre_ifa/k1_kick_head_vendor_audit.md`.

## In this directory
- `b1_loco_api.hpp` — official B1LocoClient header, **current as of PR #18 (2026-08-28)**:
  kSoccer=4, kRotateHeadWithTime=2043, VisualKick fallback semantics, Shoot
  "configuration-dependent / StateTransitionFailed"
- `b1_loco_client.hpp`, `move_controller.hpp`, `robot_shared.hpp` — SDK companions (PR #18)

## Upstream assets worth pulling (per task)
| Repo | What | When needed |
|---|---|---|
| `BoosterRobotics/booster_assets` | **K1 URDF + 152 STL meshes** (`robots/K1/K1_22dof.urdf`, K1_locomotion.urdf, MuJoCo XMLs) + motion CSVs | Gazebo K1 twin (teammate, in progress) — vendor URDF is the base; add gazebo_ros plugins; no official Gazebo sim exists (vendor = MuJoCo/Studio) |
| `BoosterRobotics/booster_gym` | RL framework, MuJoCo walking sim | walking-policy reference only — NOT our Gazebo path |
| `BoosterRobotics/robocup_demo` | 5v5 demo (fw 1.6 + SDK 1.3.6): vision+brain+game_controller | post-IFA kick/vision integration (PR #17 carries parts) |
| `BoosterRobotics/sim-3v3-simple-framework` | official 3v3 soccer agent framework (Python agent API, path planner, game codec) | strategy reference; the "goto-ball-and-kick" ecosystem |
| `BoosterRobotics/booster_robotics_sdk_ros2` | official ROS2 interface pkg | PR #17 family |

**UNVERIFIED source — do not use:** `roboticscenter.ai` K1 "software guide" (contradicts
official specs: wrong vx ranges, wrong head limits, nonexistent PyPI SDK + booster_ros2 repo).
