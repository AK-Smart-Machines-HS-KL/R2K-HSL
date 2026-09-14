# PLANS v6 → v7 Overview — v2

**Status:** ✅ done · 🔶 in progress/partial · ⬜ to do · ❌ retired · **🧪 Lab** = hardware required | **Date:** 2026-09-14
**Superseded:** the 2026-08-29 version (IFA-era planning — archived content below stays valid as history).
**Detail docs:** [post_field_test_plan](v68_pre_ifa/post_field_test_plan.md) (ACTIVE execution plan: Phase 0-2.5 + audit/glossary appendices) · [calib_validation_runbook](v68_pre_ifa/calib_validation_runbook.md) (§V11 + Appendix C U22 runbook in post_field_test_plan) · [k1_kick_head_vendor_audit](v68_pre_ifa/k1_kick_head_vendor_audit.md) (GATE 0) · [plan_v7_coarse](v7/plan_v7_coarse.md) · [ADR-A07](../adr/ADR-A07-team-captain-architecture.md) · [pit_of_nice_ideas](v7/pit_of_nice_ideas.md)
**Session evidence:** SESSION_CHANGELOG 2026-09-08 (calib field day) + 2026-09-12 (match-slot fix) + 2026-09-13/14 (overnight regression + analysis: `overnight_analysis_20260913.md`).

## Binding naming decisions (2026-09-12)

- **"TeamCaptain"** = reserved for the planned ROS 2 node (ADR-A07, v7): path executor + watchdog + augmented world model. The bridge's current flag layer (`R2K_TEAMCAPTAIN*`, Slice 1/2) is **"algorithm-enhanced"** scope and must be renamed/retired in v6.9 (the label is taken).
- **"Watchdog"** = a **v7 module** supervising the LLM: Kalman ball prediction vs reality → failsafe/re-prompt overrides. NOT a v6.9 item.
- **Two launch modes** (`--mode`, v6.9): **`pure-llm`** (bridge scope-reduced — zero tactical constants, the honest 3B baseline) vs **`algorithm-enhanced`** (the current flag-layer behavior, preserved as-is). Blue may underperform slightly in pure-llm; recovery comes via the world-model extensions (yaw, ball velocity, Kalman) and the TC node.

## 6.6–6.7 (history — all done unless noted)

| #   | Item                                                                                                                                                                                                                              | Status            |
| --- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------- |
| 1   | Demo/calibration mode (3B executor + 7B compiler)                                                                                                                                                                                 | ✅                 |
| 2   | n=100 benchmark + kpi_targets re-baseline (PR #16)                                                                                                                                                                                | ✅                 |
| 3   | Prompt-channel closure (SP/WIN negative) → TC requirements                                                                                                                                                                        | ✅                 |
| 4   | GZWeb/GUI POC                                                                                                                                                                                                                     | ✅ — 🔶 PR pending |
| 5   | opencode model strategy v1.5/1.6                                                                                                                                                                                                  | ✅                 |
| 6   | K1 vendor-doc audit (chase folklore retracted, GATE 0 installed)                                                                                                                                                                  | ✅                 |
| 7   | Hardware search (Yahboom MicroROS-Pi5 registers, K1 URDF, LIDAR spec)                                                                                                                                                             | ✅                 |
| 8   | Docs restructure + KB updates                                                                                                                                                                                                     | ✅                 |
| 9   | Residuals: ~~booster_msgs~~ DONE 09-12 · **PR #17 vision merge (team — still open)** · changelog archival (→ cleanup session) · nemotron demotion (optional — drop from opencode favorites; underperformed, format:json confound) | 🔶                |
|     |                                                                                                                                                                                                                                   |                   |

## 6.8 — IFA prep + pivot (demo work = the IFA prep; field-day pivot replaced trailer/LIDAR)

| # | Item | Status |
|---|---|---|
| 10 | V1 clamp alignment (bridge 1.5 rad/s / 1.1 m/s) | ✅ |
| 11 | A1-A3 demo face/yaw + say-yes/no — Yahboom live ✅; K1 RPC 2004 ready → **v6.9 (item 20)** | ✅/🔶 |
| 12 | **B1 kick-FAKE demo** — **WORKED at the IFA** (drive-through push staged as kick). Tuning note: the Yahboom needs **high speed** for a nicely moving ball (calib speeds are too slow for the demo push) | ✅ |
| 13a | A2bot two-bot demo (per-bot labels + 2vs0_demo) | ✅ |
| 13 | B2/V4 LIDAR ball node | ❌ displaced → **v7 pit** |
| 14 | V5 --odom watch | 🔶 superseded in shape: per-bot odom state files + belief feedback + results reader (CSV watch → v7 pit) |
| 15 | D1 trailer choreography | ❌ displaced → **v7 pit** |
| 16 | D2 trailer LIDAR | ❌ displaced → **v7 pit** |
| 17 | Lab-session gate | 🔶 replaced by the 09-08/12/13 lab days (see 17a-17g); fw/K1 probe → v6.9 K0 |

## 6.8 — FIELD DAY (not planned, achieved: 09-05→09-12; commits c471b3e/98fe001/9cf61ee/c2cb226, tag `v6.8-field-day`)

| # | Item | Status |
|---|---|---|
| 17a | Yahboom closed-loop goto: estimator (dead reckoning + encoder resync), rear-target reverse, dist-only arrival — live (round-trip drift 3-66 mm) | ✅ |
| 17b | **K1 closed-loop goto** — real K1, 9/9 legs, dist-only arrival (arrival-spin fix live-verified) | ✅ |
| 17c | Calib field stack: mode merge (`--calib` lean stack, `--nosim` alias), vocabulary freeze, exec/results, wake-up ritual (boot = (0,0) home, nose north) | ✅ |
| 17d | Match-mode slot fix (canon `_canon_assignments` + name-domain translation) — blue bots drive again | ✅ |
| 17e | Say yes/no on hardware (y1 = Seq of closed-loop swings, y2 = servo), compass (+ = clockwise) | ✅ |
| 17f | Overnight regression harness + analysis — verdict: platform green; composite gate structurally flaky on 0-0 (goal-weight 0.4); kick-aims 74% non-goalward with flags OFF | ✅ |
| 17g | Field-day docs: runbook §V11, cheat-sheet overhaul, post_field_test_plan v2 (glossary/audit/kick plan), U22 runbook (Appendix C) | ✅ |
| 17h | **U22 regression** (Appendix C) — fast tier 255/0/11 (rclpy native → bridge tests run), battery 12/12, slow tier 6/5 (KPI platform deltas — both platforms miss → recalibration = item 22); 3 test-file bugs fixed & integrated; report: `u22_regression_20260913.md` | ✅ |
| 17i | **Merge to main** — BOTH platforms green (U24 overnight + U22 native) → PR `docs/v68Planning` → `main` ready to file (GitHub web; gh unauthenticated here). Tag `v6.8-field-day` = the regression reference | ⬜ **READY — file the PR** |

## 6.9 — two modes + K1 skills (entry: 17h green)

| #   | Item                                                                                                                                                                                                                                                         | Status       |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------ |
| 18  | **--mode flag**: `pure-llm` (bridge scope-reduced — zero tactical constants; Slice 1/2 flag layer retired, TeamCaptain label freed) vs `algorithm-enhanced` (current behavior preserved). pure-llm KPI baseline = the v7 control group                       | ⬜ 1-2 d      |
| 19  | **K1 kick** ("goto ball and kick at (x,y)"): K0 probe (GATE 0) → kVisualKick(2038) port (vendor Kick/RLVisionKick recipe) → staged validation — [Phase 2.5](v68_pre_ifa/post_field_test_plan.md#phase-25--k1-kick-skill-goto-ball-and-kick-at-xy-project-p1) | ⬜ 1-2 d + 🧪 |
| 20  | **K1 head movement** (say yes/no via RPC 2004, RotateHead probes)                                                                                                                                                                                            | ⬜ 0.5 d + 🧪 |
| 21a | Kick-aim quality: algorithm-enhanced defaults ON (R2K_TEAMCAPTAIN=1/R2K_PASS_RESOLVE=1 — validated 0.20→0.94 B/match); pure-llm accepts raw aims (measured: 74% non-goalward)                                                                                | ⬜ 0.5 d      |
| 21b | Goalie-distribution sub-rule (merged from the pit 2026-09-14): `resolve_pass_target` never covers the goalie — 0 goalie passes in 200 matches (5,090 kicks, all clearances); sub-rule: unpressured goalie clearance becomes a pass to the open buddy (feeds the only productive lane blue_2→blue_3→goal) | ⬜ 0.5 d      |
| 22  | Composite gate repair (sub-KPIs hard gate, composite = 3-sample trend) + relay-rename cleanup (tournament/batch_evaluator/rebaseline still reference only_sim_bots)                                                                                          | ⬜ 0.5 d      |
| 23  | Exec-stepper hardening + selftest + preflight + restart_calib.sh (post_field_test_plan Phase 1)                                                                                                                                                              | ⬜ 1 d        |
| 24  | Phase 0 cleanup batch (0.1-0.8) + LESSONS_LEARNED write-back (firmware-physics table + architecture lessons)                                                                                                                                                 | ⬜ 0.5 d      |

## v7 — entry: v6.9 exit (modes stable, K1 kick/head live)

| #   | Item                                                                                                                                                                                                                                                                                        | Status |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| 25  | **Watchdog module** (NEW, 09-12 directive): supervises the LLM — Kalman ball prediction vs reality → divergence-triggered failsafe/re-prompt (W1-W6 scenarios from [phase_w_decision_report](v7/phase_w_decision_report.md))                                                                | ⬜      |
| 26  | **TeamCaptain ROS 2 node** (ADR-A07, name reserved): path executor + optimized_path.json + arrival yaw, role locks (goalie), augmented world model (lane facts → LLM payload), bridge fallback compat                                                                                       | ⬜      |
| 27  | World model extensions (mode-independent): bot yaw (tracker 3a), ball velocity, Kalman filter — pure-llm improves with zero rules                                                                                                                                                           | ⬜      |
| 28  | K1 integration: vision stack (PR #17), Soccer-mode-4 eval, odom refinement                                                                                                                                                                                                                  | ⬜ 🧪   |
| 29  | Edge-LLM: quality probes → Professional acquisition decision                                                                                                                                                                                                                                | ⬜      |
| 30  | Calibration/hardening: Llama 100-match, 15-scenario probe, U22/U24 parity, dead-code batch                                                                                                                                                                                                  | ⬜      |
| 31  | **Pit of nice ideas** — consolidated table P1-P12: LIDAR ball node, trailer choreography + LIDAR, K1 camera vision, score leftovers, per-bot state unification, team-message protocol, Yahboom camera (udp-cam) rework, silent prompt-change detection, opencode favorites cleanup, GUI follow-ups, user-docs pass, behavioral-priorities reference — [pit §9](v7/pit_of_nice_ideas.md) | ⬜      |

## Planning-doc cleanup (separate session — task list)

| Doc | Action |
|---|---|
| mgt_v68.md, plan_v68.md, plan_demo_ifa.md, mgt_demo_ifa.md, LAB_SESSION.md | IFA-era — archive to `outdated/` (keep: B1 high-speed note extracted first) |
| post_field_test_plan.md + PLANS_v6_v7_overview.md | the only living plans going forward |
| k1_kick_head_vendor_audit.md, ADR-A07, phase_w_decision_report.md, proposal_edge_llm_k1.md | keep as references |
| SESSION_CHANGELOG.md | archival pass (item 9: 209 KB → archive file) |

**Parked:** GUI follow-ups · user-docs pass (40 files) · udp-cam rework.
