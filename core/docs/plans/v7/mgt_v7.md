# v7 Mgt Summary — Consolidated Agenda (10,000 ft)

**Status:** DRAFT (coarse; detailed v7 planning explicitly out of scope)
**Owner:** Prof-Adrian-Mueller | **Date:** 2026-08-28 | **Branch:** docs/v68Planning
**Sources:** docs/v7/* (pit_of_nice_ideas, sp/win experiment plans, vendor audit, rotation design), scrum_tasks.md, ADR-A07, proposal_edge_llm_k1.md, SESSION_CHANGELOG (incl. archive protocol), 100-match benchmark + SP/WIN reports.

---

## The one sentence

The LLM stays the brain (situation assessment, coarse intent); geometry, role assignment, path planning, and hardware skills move to the **CPU planner (TeamCaptain)** + **Booster's own stack** (vision, VisualKick, soccer mode). The justification is empirical, on record: the **SP** (prompt-only spinning fix) and **WIN** (prompt-only win-rate) experiments both ended NEGATIVE with the same verdict — **the prompt channel is closed**; the durable fix is the CPU planner. The 100-match benchmark adds: "3B good at positioning, bad at coordination."

## Workstreams

### 1. TeamCaptain (ADR-A07)
CPU-only ROS 2 node between LLM and bridge: path executor, augmented world model (future projection, velocity decay), watchdog, kick-abort coordinator, `optimized_path.json`. Downward compatible (absent → bridge PID fallback).
- **Requirements doc = SP + WIN findings** (goalie-Y limit cycle, kicker flapping, content-hash jitter, prompt-channel ceiling)
- **W1-W6 watchdog scenarios** (docs/plans/plans/v7/scenarios/, never run): test watchdog re-prompt (Option A) vs second-model monitor (Option B)
- Score-function leftovers: last_toucher possession, non-linear BALL_POSITION_GAIN, goal-bonus race condition (score_node reads Worldstate instead of /world_positions)
- Open questions: replan threshold, Nav2 vs custom planner, K1 kReplayTrajectory format (2028), odom drift handling

### 2. Behavioral priorities (100-match evidence)
| Priority | Evidence |
|---|---|
| Goalie role-lock | 0/100 matches with a goalie kick — Blue plays 2v3 |
| Passing | blue_3 advances 63.6%, never receives |
| Defensive recovery | high_line: 14 red goals/10 matches after turnover |
| Draw rate | 42% — consider 180s+ matches |

→ Role assignment + coordination move to CPU; LLM keeps positioning.

### 3. K1 hardware integration (pending K1-PROBE verification)
- **Kick:** kVisualKick (2038, fw ≥ 1.5.2.1, kV2 recommended by vendor) + evaluate Soccer-mode (4) built-ins (kGoalie, kicking postures) BEFORE custom code; bridge placeholder (2000/mode-1) replaced
- **Head:** kRotateHead 2004/2043/2006 (limits: yaw ±59°, pitch −19°/+49°) — face/yaw split per plans_v68/mgt_demo_ifa.md
- **Odometry-closed loop:** `/Kev1n/odometer_state` + LowState already relayed; `kResetOdometry` (2031) correction path
- **Vision stack:** PR #17 `utils/vision/` (YOLO head camera, PoseEstimator, field lines) — pending merge
- **Fleet:** 2x K1 **Education** (Orin NX 8GB, confirmed) — onboard vision (TRT) plausible. **Professional NOT yet ordered** — acquisition is a budget request, justified by `proposal_edge_llm_k1.md` + Stage 0/1 evidence

### 4. Edge-LLM on-robot
`proposal_edge_llm_k1.md` — the **technical feasibility study** for on-robot LLM inference. It explores whether one K1 **Professional** (AGX Orin 32GB built-in, 200 TOPS; not yet ordered) can host the model chain. Chain: Stage 0 (quality: MoE models vs 3B baseline on the 5090) + Stage 1 (latency: vLLM, ~4.4x bandwidth scaling) produce the evidence -> feasibility verdict -> acquisition -> deployment. The 2 Education units cover hardware-team play + onboard vision in the meantime. MoE candidates (gpt-oss:20b MXFP4, Qwen3-30B-A3B) target ~3B-class latency with 10x knowledge. Emulation first: Stage 0 (quality: same weights via Ollama on 5090, probe_s1.py) + Stage 1 (latency: vLLM, bandwidth-ratio scaling ~4.4x). Success criteria: kicker==nearest ≥75%, goalie overrun ≤25%, parse ≥98%.

### 5. Calibration v7 tasks (from pit_of_nice_ideas.md, Calibration section)
Yaw in Worldstate (scrum 3a, tracker change), visual markers in Gazebo (colcon), `single_k1.json` relay profile, 14B/32B calibration probes, dynamic entity spawning (4 code blockers), async compiler latency. Builds on the v6.8 cure ladder (clamps → odom watch → scaling → vision-corrected odom → localization).

### 6. Tech-debt / benchmark leftovers
- Llama 100-match benchmark — never started
- Text-probe all 15 scenarios — never started
- U22-vs-U24 / Qwen-vs-Llama analysis report — missing
- Dead `prompt_utils.py` (delete/consolidate), untracked `benchmark.sh` + `u22_qwen_150_raw.json`, deleted `umschaltmomente.jsonl` (reconstructable)
- C3: 2vs2 sample artifact (phantom blue_3), emp_restart_006 mislabel

## K1-PROBE — hardware verification (entry condition for the TeamCaptain kick-abort part + K1 integration)

_Mnemonic for the 4-step on-robot verification protocol; detailed in docs/plans/v68_pre_ifa/k1_kick_head_vendor_audit.md, section 'Hardware probe protocol'._

4-step protocol (k1_kick_head_vendor_audit.md, 'Hardware probe protocol'; ~1h, changelog-logged):
1. `GetRobotInfo` (2022) / `booster-cli version`: firmware ≥ 1.5.2.1 per robot (fleet: 2x Education; Professional pending order)
2. On-robot SDK inspection (`ssh booster@…`, `/opt/booster` headers vs repo)
3. Probe matrix in kWalking: VisualKick V1 → V2 → Shoot (expected fail) + head 2004/2043 — motion, termination, abort via 2000
4. Ball-motion experiment: kick triggered, ball rolled away mid-skill → chase or terminate? (the folklore experiment)

Purpose: replace KB folklore with measured behavior BEFORE kick-abort or bridge kick code is written.

## Outstanding v6.7-exit tasks

- GUI PR merge (feature/gzweb-experimental — carries KB annotations + v6.7 wrap docs; v6.7 hygiene, NOT v7 scope)
- PR #17 (vision) + FastDDS branch (fix_network_switch) merges — team-side
- Changelog archival: protocol executed once (30 entries archived; active starts 2026-08-27) but the active file is back at **209 KB** (3× the 100 KB trigger) → next archival due, cutoff per protocol (entries before ~2026-08-27, findings distilled to power files first)
- booster_msgs duplicate-name flag — owner: user (informing kleinSinus/Darkywisard)

## Non-goals

GUI follow-up features, opencode offer rotation, Yahboom trailer hitch, detailed v7 planning.

## Sequencing

v6.8 (clamps → kick placeholder → odom watch) → demo_ifa (fairs) → **K1-PROBE** → TeamCaptain (WS 1+2) ∥ K1 integration (WS 3); Edge-LLM Stage 0/1 whenever the 5090 is free (WS 4); calibration tasks on demand (WS 5); tech debt in the gaps (WS 6).
