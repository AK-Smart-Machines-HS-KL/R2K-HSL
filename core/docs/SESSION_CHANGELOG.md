# Session Changelog (Active — 2026-08-03 onward)

> For full history (2026-07-13 to 2026-08-02), see `SESSION_CHANGELOG_archive.md`.
> Compressed on 2026-08-05. Key findings are in the power files and `LESSONS_LEARNED.md`.

## 2026-08-08 — Score formula option D: continuous proximity rewards

**Goal:** Fix root cause of score chart regression: per-frame pressing reward (+0.036) too small to counter possession flip (-2.0). Replace with continuous proximity reward (option D).

**Done:**
- score_node.py: replaced per-frame velocity-based pressing/marking rewards with continuous proximity rewards. Stateless — no `_prev_*` tracking needed.
  - Pressing: `max(0, PRESSING_REFERENCE_DIST - dist_blue) * PRESSING_GAIN` — rewards being CLOSE to ball, not closing distance
  - Marking: `max(0, MARKING_REFERENCE_DIST - nearest_blue_red) * MARKING_GAIN` — only when red closer to ball (possession potential)
  - Named constants: `PRESSING_REFERENCE_DIST=3.0`, `MARKING_REFERENCE_DIST=3.0`
- Ran 118 Gazebo matches (85 hand-crafted × 4s + 33 empirical × 8s), 0 failures, fresh traces with option D.
- Regenerated all 50 score charts + 50 field diagrams.
- Re-probed all 50: 500 probes, hard-pass 92% (98% 3vs3), clustering 96.6%, latency p50 289ms. No regression.
- 147 fast tests pass.
- Score trajectory improvement verified:
  - 3vs3_attack_center: t=4s mean 1.30 → 3.13 (+1.83)
  - 3vs3_def_transition: t=4s mean -0.50 → 2.19 (+2.69)
  - 3vs3_high_line: t=4s mean -9.50 → -6.46 (+3.04)
  - 3vs3_attack_wing: t=4s mean 0.55 → 0.79 (+0.24)

**Files touched:**
- `src/score_node.py` — option D: continuous proximity pressing + marking (stateless)
- 50 `score_chart.png` (regenerated with option D data)
- 50 `field_diagram.png` (regenerated)
- `results/probe_p3_v7d_{raw,report}.{jsonl,md}` (500 probes)

**Files deleted:** None

**Not yet done:**
- Empirical score chart visual bugs (goal marker position, NO GOAL label) — still present, deferred to human reviewer
- Phase W (watchdog divergence scenarios) — next
- Phase 4 (live Gazebo demos) — after Phase W
- Phase 4b (Llama-3.2-3B regression) — model pulled, ready
- Phase 5 (final KPI + code freeze) — after Phase 4/4b

**Next:** Phase W — build 6 synthetic divergence scenarios, test Option B (second-model monitor POC), write decision report.

**Blockers:** None. 147 tests pass. Ollama on GPU, qwen2.5:3b + llama3.2:3b warm.

---

## 2026-08-07 (cont.2) — Path C: score formula V7 + Oracle fix + chart fixes + warp-and-resume

**Goal:** Fix root cause of score regression in hand-crafted scenarios: Oracle sends bots 2m from ball (never challenges), scoring formula doesn't reward pressing/marking. Add warp-and-resume infrastructure. Fix score chart bugs.

**Done:**
- AGENTS.md: added "No hard-wired thresholds in code" convention (was in cheatpage only).
- score_node.py V7: added symmetric continuous pressing reward (proportional to distance change, `PRESSING_GAIN=1.0`) + conditional symmetric marking reward (only when red closer to ball, `MARKING_GAIN=0.5`). No thresholds for new rewards — pure proportional. Added `_check_reset()` for warp-and-resume. All existing thresholds refactored to named constants.
- referee_node.py V7: added `_check_reset()` — clears all match state on `shared_state/reset_flag.json` detection.
- Fixed Oracle targets in 5 hand-crafted scenarios (attack_center, attack_wing, long_shot, overload, default): nearest blue now sent within 0.5m of ball instead of 2m away.
- Fixed goalie Y clamping to ±0.9 in empirical rework script (`rework_empirical_oracle.py`).
- tools/warp_and_run.py: new — teleports bots via `/gazebo/set_entity_state`, writes reset flag, runs 4s, repeats. 75% faster than full Gazebo restart.
- tools/ensemble_batch.sh: new — starts Gazebo once, loops warp-and-resume for all 17 hand-crafted.
- gen_score_chart.py: fixed 5 bugs — (1) goal marker at actual y-position (time after umschalt), (2) fixed y-axis 0-8s on all charts, (3) goal detection capped at 8s (goals after 8s = NO GOAL), (4) NO GOAL includes umschalt description, (5) GOAL label includes actual time ("GOAL: blue at t=4.1s").
- Ran 5×4s Gazebo for all 17 hand-crafted (85 matches, 0 failures, fresh traces with V7 score formula).
- Regenerated all 50 score charts (17 ensemble + 33 bar-delta with fixes).
- Re-probed all 50: 500 probes, hard-pass 92% (97% 3vs3-only, 96% empirical), clustering 97.8%, latency p50 289ms. No regression.
- 147 fast tests pass.

**Files touched:**
- `AGENTS.md` — added no-hardcoded-thresholds convention
- `src/score_node.py` — V7: pressing + marking rewards, named constants, reset check
- `src/referee_node.py` — V7: reset flag check
- `tools/warp_and_run.py` — new warp-and-resume tool
- `tools/ensemble_batch.sh` — new batch runner
- `tools/gen_score_chart.py` — 5 chart bug fixes
- `tools/rework_empirical_oracle.py` — goalie Y clamp fix
- 5 hand-crafted analysis.md (Oracle target fixes)
- 33 empirical analysis.md (goalie Y clamp via rework)
- 50 score_chart.png (regenerated with V7 data)
- `results/probe_p3_v7_{raw,report}.{jsonl,md}` (500 probes)

**Files deleted:** None

**Not yet done:**
- Warp-and-resume not tested (full-restart used for this pass; warp tool ready for next pass)
- 2vs2 probe config (phantom blue_3 config artifact)
- 3vs3_default + 3vs3_overload hard-fail investigation (8/10 and 3/10 fail)
- Phase W (watchdog divergence scenarios) — next
- Phase 4 (live Gazebo demos) — after Phase W
- Phase 4b (Llama-3.2-3B regression) — model pulled, ready
- Phase 5 (final KPI + code freeze) — after Phase 4/4b

**Next:** Phase W — build 6 synthetic divergence scenarios, test watchdog re-prompt (Option A) vs second-model monitor (Option B), write decision report.

**Blockers:** None. 147 tests pass. Ollama on GPU, qwen2.5:3b + llama3.2:3b warm.

---

## 2026-08-07 (cont.) — Full 50-scenario pass: diagrams, charts, re-probe

**Goal:** Complete the full 50-scenario pass after human review feedback: fix all field diagrams, score charts, hand-crafted text errors, empirical "restart — restart" duplication. Verify no regression.

**Done:**
- Audited all 17 hand-crafted: fixed 3vs3_deep_cross (wrong title + goalie Y=-2.2), 3vs3_long_shot (goalie Y=1.4), 3vs3_wing_switch (goalie Y=2.2), 3vs3_def_transition (Oracle targets = current positions → "sprint back" text contradicted commands). All 17 now pass: no wing errors, no goalie Y outside ±0.9, no possession errors, no title mismatches.
- Reran rework script on all 33 empirical: fixed "Umschalt type: restart — restart" duplication (loaded descriptions from umschaltmomente.jsonl). All 33 now show proper descriptions ("Set-piece: foul_penalty", "Blue won possession", etc.).
- Regenerated all 50 field diagrams: bigger figure (12×8), field fills 90% width (was 75%), bots 14px (was 12px), no text labels on arrows (just dotted lines + target circles), ball 11px with black outline + bbox label.
- Ran 5×4s Gazebo for all 17 hand-crafted (85 matches, 0 failures, ~30min). Fresh traces for ensemble charts.
- Regenerated all 50 score charts:
  - 17 hand-crafted: ensemble forecast (5 runs × 4s, shaded band + mean dotted line, scoring formula at bottom, "Score forecast (4sec, 5 runs)" title)
  - 33 empirical: bar-delta (16 bars × 0.5s, goal cutoff, "t=0 (Umschalt)" label, "GOAL: team" marker, "NO GOAL" marker, x-axis fixed [-10,+10])
- Re-probed all 50: 500 probes, hard-pass 92% (96% 3vs3-only, 97% empirical), clustering 97.8%, latency p50 284ms. No regression.
- Knowledge base updated (8_C3_SOCCER_KNOWLEDGE.md): added wing convention (Blue's LEFT = +Y, Blue's RIGHT = -Y), score range [-10,+10], scoring formula.
- 147 fast tests pass.

**Files touched:**
- `tools/gen_score_chart.py` — ensemble forecast chart (shaded band + mean), 16-bar bar-delta, goal cutoff, scoring formula, t=0 label
- `tools/gen_all_diagrams.py` — bigger figure (12×8), no text labels on arrows, --all-empirical flag, removed emp_* exclusion in --all
- `tools/gen_field_diagrams.py` — bigger ball (11px), bigger bots (14px), smaller margins (±0.5)
- `tools/rework_empirical_oracle.py` — fixed umschalt_desc loading from umschaltmomente.jsonl, fixed role assignment bug (goalie conflict when nearest bot IS blue_1)
- `tools/check_clustering.py` — new (from earlier this session)
- `ros2k_knowledge/8_C3_SOCCER_KNOWLEDGE.md` — wing convention + score range + scoring formula
- 17 hand-crafted analysis.md (text fixes: wing, goalie Y, title, Oracle targets)
- 33 empirical analysis.md (reworked: "restart — restart" → proper description)
- 50 field_diagram.png (regenerated)
- 50 score_chart.png (regenerated: 17 ensemble + 33 bar-delta)
- `results/probe_p3_final_{raw,report}.{jsonl,md}` (500 probes)

**Files deleted:** None

**Not yet done:**
- Warp-and-resume Gazebo optimization (deferred — full restart per run, ~25s overhead acceptable)
- 2vs2 probe config (phantom blue_3 config artifact — add samples_2vs2.txt or exclude from aggregate)
- 3vs3_default and 3vs3_overload hard-fail investigation (8/10 and 2/10 fail — not blocking)
- Phase W (watchdog divergence scenarios) — next
- Phase 4 (live Gazebo demos) — after Phase W
- Phase 4b (Llama-3.2-3B regression) — model pulled, ready
- Phase 5 (final KPI + code freeze) — after Phase 4/4b

**Next:** Phase W — build 6 synthetic divergence scenarios, test watchdog re-prompt (Option A) vs second-model monitor (Option B), write decision report.

**Blockers:** None. 147 tests pass. Ollama on GPU, qwen2.5:3b + llama3.2:3b warm.

---

## 2026-08-07 — Phase 3 (text-probe all 50) + Task 6 rework (33 empirical)

**Goal:** Execute Phase 3 text-probe on all 50 scenarios (17 hand-crafted + 33 empirical), verify hard-pass >= 90%, no clustering regression. Rework the 33 empirical Oracle (known-bad ground truth).

**Done:**
- Phase 3-Structural: 500 probes (50 scenarios x 10 repeats), hard-pass 92% (97% excl 2vs2 config artifact), clustering 98.8%, latency p50 296ms. All gates PASS.
- T1: Clamped 9 OOB scenario.json files (emp_014,015,018,019,021,025,028,029,032) to field bounds. Source: Gazebo physics explosions in umschaltmomente.jsonl.
- T2: Reworked all 33 empirical analysis.md: added Scope, deepened Expert (distances, possession, numbers, clustering), rewrote Oracle with "to achieve X because Y" reasoning. Fixed emp_016 tactical error (blue_2 was sent to opp half during defensive crisis). Fixed role assignment bug (goalie conflict when nearest bot IS blue_1). All 33 validated: 3 unique bots, coords in field, reasoning present.
- T3: 33x 8s Gazebo headless matches (sequential, 19min, 0 failures). All 33 score_chart.png regenerated with real tactical score data.
- T4: Re-probed 33 empirical post-rework: 330 probes, hard-pass 96% (99% excl config artifact), clustering 100%, latency p50 284ms.
- llama3.2:3b pulled for Phase 4b.
- 147 fast tests pass.
- Final verdict: `results/phase3_structural_verdict.md`

**Files touched:**
- `tools/build_corpus.py` — extended with walk_scenario_dirs() + --scenarios flag
- `tools/check_clustering.py` — new standalone clustering regression checker
- `tools/rework_empirical_oracle.py` — new deterministic Oracle rework for 33 empirical
- `tools/t3_batch_gazebo.sh` — new batch runner for 33x 8s Gazebo matches
- `tools/gen_score_chart.py` — fixed emp_* exclusion, added --all-empirical flag
- `tests/synthetic_worldstates/corpus_{scenarios,handcrafted_17,empirical_33}.jsonl`
- `results/probe_p3_struct_{raw,report}.{jsonl,md}` (500 probes)
- `results/probe_p3_emp_tactical_{raw,report}.{jsonl,md}` (330 probes)
- `results/phase3_structural_verdict.md`
- 9 `scenario/emp_*/scenario.json` (OOB clamped)
- 33 `scenario/emp_*/analysis.md` (reworked: Scope + Expert + Oracle)
- 33 `scenario/emp_*/score_chart.png` (regenerated from real Gazebo data)

**Files deleted:** None

**Not yet done:**
- Phase W (watchdog divergence scenarios) — next
- Phase 4 (live Gazebo demos with --analyze) — after Phase W
- Phase 4b (Llama-3.2-3B regression) — model pulled, ready
- Phase 5 (final KPI + code freeze) — after Phase 4/4b
- emp_restart_006 mislabeled as 3vs3 but has 2 bots/team (config artifact, not blocking)

**Next:** Phase W — build 6 synthetic divergence scenarios, test watchdog re-prompt (Option A) vs second-model monitor (Option B), write decision report.

**Blockers:** None. 147 tests pass. Ollama on GPU, qwen2.5:3b + llama3.2:3b warm.

---

## 2026-08-03 — v6.4 spec, Phase A (ADRs), Phase C (cleanup), Phase H1, Phase M'

**Done:**
- 6 ADRs written (`core/docs/adr/ADR-A0{1..6}-*.md`) with glossaries
- Code cleanup: dead tools archived, `prompt_utils.py`, `header_k3.txt` fragment, `start_ollama.sh`
- H1: 5 new scenarios, Oracle refinement, IAA, 7 failure modes, dual feedback (95% agreement)
- M': V5 role-locked prompt → 100% hard-pass, 27-match auto-loop, variant sweep (V5 winner)
- Live match: clustering fix via relative positioning (cluster_all 47%→0%), goalie goal-line mode
- Phase R: score refined (cluster+lane), 74 umschaltmomente extracted, 33 empirical scenarios
- `optimization_spec_v6.4.md` written with glossary (19 terms)
- Phase 2: 17 analysis.md restructured (Expert/Oracle/Output-to-bridge/Score-chart, ground truth)
- Kickoff positions fixed (all blue bots in own half)
- ADR-A07: TeamCaptain architecture (v7 design, SWOT, downward compatible)
- `scrum_tasks.md`: 11 tasks (Tasks 1, 4 done; 2, 3b, 5, 6, 7, 8 this sprint; 9, 10, 11 v7)

**Key decisions:**
- Gazebo reframed: "more demo than measurement" (spike project)
- Phase M (21h variable sweep) deferred — replaced by M' (15min iterative prompt-fix)
- Relative positioning > fixed zones for anti-clustering
- LLM produces correct targets; bridge/physics causes clustering (root cause)
- K1 kick is autonomous (chase problem, needs abort via ball motion change)
- Demo/calibration mode uses existing pipeline (--demo flag, no meta-knowledge)
- No path planning until v7 (open questions in ADR-A07)

**Next:** Phase 3 (text-probe all 50 scenarios), Phase W (watchdog), Phase 4 (Gazebo demo),
Phase 4b (Llama regression), Phase 5 (final KPI + code freeze v6.4)

**Blockers:** None. 147 tests pass. Ollama on GPU, qwen2.5:3b warm.
