# PLANS v6 → v7 Overview

**Status:** ✅ done · 🔶 in progress · ⬜ to do · **🧪 Lab** = physical hardware required | **Date:** 2026-08-29
**Detail docs:** [plan_v68.md](v68_pre_ifa/plan_v68.md) · [plan_demo_ifa.md](v68_pre_ifa/plan_demo_ifa.md) · [plan_v7_coarse.md](v7/plan_v7_coarse.md) · [mgt_v68](v68_pre_ifa/mgt_v68.md) · [mgt_demo_ifa](v68_pre_ifa/mgt_demo_ifa.md) · [mgt_v7](v7/mgt_v7.md)
**Note:** section links use Obsidian heading anchors (exact heading text).

| # | Ver | Item | Status | Lab |
|---|---|---|---|---|
| 1 | 6.6 | Demo/calibration mode (`--demo`, calib_cli, 3B executor + 7B compiler; POC 3b 73% / 7b 85%) | ✅ | — |
| 2 | 6.7 | n=100 benchmark + `kpi_targets` re-baseline (PR #16 merged) | ✅ | — |
| 3 | 6.7 | Prompt-channel closure — SP + WIN experiments negative → TeamCaptain requirements (`reference/experiments/`) | ✅ | — |
| 4 | 6.7 | GZWeb container isolation + GUI POC (supervisor, frontend, browser-accepted) | ✅ — 🔶 PR pending (user experiments first) | — |
| 5 | 6.7 | opencode model strategy v1.5/1.6 — 14 favorites, offer automation, self-healing Ollama `--ensure` | ✅ | — |
| 6 | 6.7 | K1 vendor-doc audit — chase folklore downgraded, head confirmed, Soccer mode found — [audit](v68_pre_ifa/k1_kick_head_vendor_audit.md) | ✅ | — |
| 7 | 6.7 | Hardware search — Yahboom MicroROS-Pi5 (servo/odom/PID registers), K1 URDF, LIDAR ball pipeline spec — [YAHBOOM_KNOWLEDGE](../../src/yahboom/YAHBOOM_KNOWLEDGE.md) · [ASSETS](../../src/booster/ASSETS.md) | ✅ | — |
| 8 | 6.7 | Docs restructure ([plans](.), [reference](../reference/), outdated/) + KB updates | ✅ | — |
| 9 | 6.7 | Residuals: PR #17 vision merge (team) · booster_msgs flag (user→team) · changelog archival (209 KB) · nemotron demotion (optional) | 🔶 | — |
| — | **6.8 pre-IFA** | *plans written — execution starts here* | | |
| 10 | 6.8 | **V1** Clamp alignment — bridge 2.5→1.5 rad/s, 1.2→1.1 m/s — [plan_v68 › Pre-IFA](v68_pre_ifa/plan_v68.md#Pre-IFA) | ⬜ 0.5 d | — |
| 11 | 6.8 | **A1-A3** Demo a: face/yaw + say-yes/no (K1 2004 + Yahboom servo topics) — [plan_demo_ifa › Task A](v68_pre_ifa/plan_demo_ifa.md#Task-A---Face-vs-Yaw) | ⬜ 1-2 d | — |
| 12 | 6.8 | **B1** Demo b-FAKE: "kick ball" waypoints + mirror simultaneity — [plan_demo_ifa › Task B](v68_pre_ifa/plan_demo_ifa.md#Task-B---Kick-demo) | ⬜ 0.5 d | — |
| 13 | 6.8 | **B2/V4** LIDAR ball-detection node (sim + MS200 identical code) — [plan_v68 › Pre-IFA](v68_pre_ifa/plan_v68.md#Pre-IFA) | ⬜ 1-2 d | — |
| 14 | 6.8 | **V5** calib_cli `--odom` watch (commanded-vs-reported CSV) — [plan_v68 › Pre-IFA](v68_pre_ifa/plan_v68.md#Pre-IFA) | ⬜ 0.5 d | — |
| 15 | 6.8 | **D1** Trailer-FAKE choreography (fork entry, 0° push, 45° rotation) — [plan_demo_ifa › Task D](v68_pre_ifa/plan_demo_ifa.md#Task-D---Trailer) | ⬜ 1 d | — |
| 16 | 6.8 | **D2** Trailer-LIDAR frame/pose detection (pre-IFA; LIDAR-only, decoupled from udp-cam; 2-post fit + known geometry) — [plan_demo_ifa › Task D](v68_pre_ifa/plan_demo_ifa.md#Task-D---Trailer) | ⬜ 1-1.5 d | 🧪 |
| 17 | 6.8 | **Lab-session gate**: fw probe, 2004-in-WALKING, dry-runs 10-16 (incl. trailer with detection), ball pick (3 sizes) — [plan_demo_ifa › Lab session gate](v68_pre_ifa/plan_demo_ifa.md#Lab-session-gate) | ⬜ 90-120 min | 🧪 |
| — | **6.8 post-IFA** | *gated: K1-PROBE results + fw ≥ 1.5.2.1 — [plan_v68 › After IFA](v68_pre_ifa/plan_v68.md#After-IFA)* | | |
| 18 | 6.8 | **V7/V8** kVisualKick bridge action (kV1/kV2) + Soccer-mode (4) evaluation | ⬜ | 🧪 |
| 19 | 6.8 | **V9-V11** Odom-closed control · board-side PID cure · `vy` exploitation | ⬜ | 🧪 |
| 20 | 6.8 | **c-real** camera color tracking + RoboCup vision / goto-ball-and-kick | ⬜ | 🧪 |
| 21 | 6.8 | **d-real** free (x, y, yaw) maneuver library (on top of the pre-IFA LIDAR detection) | ⬜ | 🧪 |
| 22 | 6.8 | udp-cam rework (separate track) | ⬜ | 🧪 |
| — | **v7** | *entry: v6.8 exit* — [plan_v7_coarse.md](v7/plan_v7_coarse.md) · [pit_of_nice_ideas.md](v7/pit_of_nice_ideas.md) · [phase_w_decision_report.md](v7/phase_w_decision_report.md) · [proposal_edge_llm_k1.md](v7/proposal_edge_llm_k1.md) | | |
| 23 | 7 | TeamCaptain core: path executor, world model, W1-W6 watchdog decision, role assignment → CPU — [plan_v7_coarse › Phase 1](v7/plan_v7_coarse.md#Phase-1---TeamCaptain-core-(WS-1+2)) | ⬜ | — |
| 24 | 7 | K1 integration: vision stack in match mode, head control, odom loop — [plan_v7_coarse › Phase 2](v7/plan_v7_coarse.md#Phase-2---K1-integration-(WS-3,-parallel)) | ⬜ | 🧪 |
| 25 | 7 | Edge-LLM: Stage 0/1 emulation (5090) → K1 Professional acquisition decision — [plan_v7_coarse › Phase 3](v7/plan_v7_coarse.md#Phase-3---Edge-LLM-(WS-4,-GPU-budget-permitting)) | ⬜ | — |
| 26 | 7 | Calibration/hardening + tech debt: Llama 100-match, 15-scenario text probe, U22/U24 report, dead-code batch — [plan_v7_coarse › Phase 4](v7/plan_v7_coarse.md#Phase-4---Calibration-&-hardening-(WS-5+6)) | ⬜ | — |

**Parked:** GUI follow-up features · user-docs pass (40-file technical reference).
