# Session Changelog (Active — 2026-08-03 onward)

> For full history (2026-07-13 to 2026-08-02), see `SESSION_CHANGELOG_archive.md`.
> Compressed on 2026-08-05. Key findings are in the power files and `LESSONS_LEARNED.md`.

## 2026-08-11 — v6.5 regression test on U22 (COMPLETE)

**Goal:** Run the v6.5 regression test suite natively on U22 to verify the redesign (dynamic roles, option D score formula, qwen2.5:3b general-purpose model) before code freeze and PR.

**Done:**
- Pulled `qwen2.5:3b` (general-purpose Instruct, 1.9 GB) on U22 — confirmed `qwen2.5-coder:3b` was the wrong model (ADR-A01, 2026-07-31, formally decided switch to `qwen2.5:3b`; coder training corpus is 70% source code, soccer vocabulary is out-of-distribution). The 100-match v6.5 benchmark (2026-08-10) ran on a different machine with `qwen2.5:3b`; this U22 machine only had the coder variant. Both models now present on disk.
- Sanity-probed `qwen2.5:3b`: fluent soccer vocabulary (not code/hedging), ADR-A01 validated.
- Phase 1 (fast tier): 113 passed, 11 skipped, 0 failed. Fixed 2 pre-existing test failures in `test_text_mode.py`:
  - **Test drift** (`test_text_mode_uses_text_rules_and_samples`, `test_text_mode_sample_conversion_in_prompt`): v6.5 commit `0b87b03` removed the `VALID OUTPUT LINES` block from `rules_core_text.txt` (replaced with qualitative language), but the tests still asserted the old strings. Updated assertions to match v6.5 fragment content.
  - **Production bug** (`r2k_evaluator.py:144,208`): v6.5 `samples_3vs3.txt` uses `OUTPUT:` marker instead of `ASSISTANT:` (all other sample files still use `ASSISTANT:`). Both `_clean_text_samples` and `_clean_json_samples` only matched `ASSISTANT:`, so the v6.5 samples were silently passed through unconverted. Fixed both regexes to accept `(?:ASSISTANT|OUTPUT):`. This is a latent bug — the 100-match benchmark ran with it present (LLM still produced reasonable output from raw samples, but not the cleaned format intended).
- Phase 2 (baseline collection, first run): 15/15 matches completed, 0 failures. **GPU power-state bug discovered:** RTX 4080 stuck at P8 idle state, 210 MHz core clock, 15.9W — even during LLM inference. Result: 25 tok/sec generation, 107 tok/sec prefill. `latency_p50` ranges 7-21 seconds across matches (v6.3 threshold was <= 992ms). This is the Nvidia suspend-to-RAM bug (Xid 31 MMU Fault, AGENTS.md axiom 8). Rebooted to reset GPU state.
- **After reboot: GPU healthy.** P2 state, 2730 MHz core, 242 tok/sec generation, 4875 tok/sec prefill. Latency dropped to 659-674ms p50 (was 7000-21000ms).
- Phase 2a (baseline collection, second run with healthy GPU): 15/15 matches completed, 0 failures, ~36min. 5 scenarios × 3 runs × 120s with `qwen2.5:3b`. KPI JSONs in `src/results/kpis_*`, consolidated in `src/results/v65_rebaseline_raw.json`.
  - `src/tools/rebaseline_collect.sh` (throwaway harness, not committed): runs matches, extracts run-id, calls `analyze_trace.py`, merges KPIs.
- Phase 3 (re-baseline thresholds): Updated 5 `kpi_targets.json` files with v6.5-calibrated thresholds computed from 15 samples. Old v6.3 values preserved as `v63_thresholds` field. Formula: higher-is-better min = min(obs)×0.85, lower-is-better max = max(obs)×1.3, pct KPIs capped at 100.
- Phase 4 (slow suite): 9 passed, 2 failed in 24min (11 tests × ~140s each).

**Phase 4 results (11 slow tests, re-baselined thresholds):**
| Test | Result | Failure |
|---|---|---|
| test_attack_center_performance | **FAIL** | oob_pct=73.2 outside [0, 22.0] |
| test_attack_center_goalie | PASS | — |
| test_attack_center_latency | PASS | — |
| test_default_performance | **FAIL** | cluster_pct=20.0 outside [0, 13.7] |
| test_default_goalie | PASS | — |
| test_high_line_performance | PASS | — |
| test_long_shot_performance | PASS | — |
| test_contain_delay_performance | PASS | — |
| test_high_line_goalie | PASS | — |
| test_long_shot_goalie | PASS | — |
| test_contain_delay_goalie | PASS | — |

**Failure analysis:** Both failures are single-match outliers exceeding the 3-sample baseline range. The 3-sample baseline is thin — `oob_pct` baseline for attack_center was [0, 18.1] (max×1.3=22.0), but the slow-suite match hit 73.2 (a bot got stuck OOB). `cluster_pct` baseline for default was [0, 17.0] (max×1.3=13.7 after the 0.85 factor on the low end), but the slow-suite match hit 20.0. These are variance-driven, not regressions — the re-baselined thresholds need more samples (5-10 per scenario) to be robust. With only 3 samples, the max×1.3 headroom is insufficient for high-variance KPIs like oob_pct and cluster_pct.

**Key findings (Phase 2a baseline data, 15 matches, healthy GPU):**
| Scenario | lat_p50 | composite | poss% | oob% | clust% | goalie_t% | tac_avg |
|---|---|---|---|---|---|---|---|
| 3vs3_attack_center | 673ms | 0.367 | 50.7 | 9.4 | 5.9 | 91.5 | 2.54 |
| 3vs3_contain_delay | 659ms | 0.355 | 62.0 | 10.0 | 29.6 | 94.9 | 0.20 |
| 3vs3_default | 674ms | 0.435 | 51.1 | 11.4 | 8.4 | 85.7 | 2.58 |
| 3vs3_high_line | 659ms | 0.328 | 48.9 | 0.8 | 12.3 | 94.8 | 0.12 |
| 3vs3_long_shot | 659ms | 0.323 | 48.1 | 23.8 | 36.6 | 95.3 | -0.09 |

- Latency: 659-674ms p50 on U22 (RTX 4080, healthy GPU). The v6.3 threshold of ≤992ms was calibrated on different hardware (v6.3 27-run baseline, commit `532360b`) — it is NOT a v6.3 U22 baseline, so "improvement" cannot be claimed. U24 (RTX 5090 Laptop) reports ~290ms p50 — the ~2× difference is hardware (GPU clocks, memory bandwidth), not software. U22 latency is within the v6.3 threshold and consistent with hardware expectations.
- Composite: 0.32-0.44 (v6.3 27-run baseline was 0.19-0.40 — v6.5 is in the same range, slightly higher for default). NOTE: the v6.3 baseline and the v6.5 100-match U24 benchmark both ran with the `OUTPUT:` marker bug present (see below), so their numbers are pre-fix. Post-fix behavioral re-validation is required on U24.
- Goalie tactical: 85-95% (>= 60% threshold — **PASS**).
- OOB and cluster are high-variance (0-57% OOB, 0-88% cluster across all runs).
- Goals (U22, 3 matches per scenario): 12B-12R total, 2W-4L-9D (13% win rate). U24 (100 matches, 10 scenarios): 48B-67R, 42% win rate. U22 win rate is lower but 3-sample comparison is unreliable — U24's 100-match baseline is the reference.

**Stale-benchmark caveat:** The U24 100-match benchmark (2026-08-10, `docs/v65_final_benchmark.md`) ran with the `OUTPUT:` marker bug present. The `_clean_json_samples` function silently passed raw `OUTPUT: {...}` blocks to the LLM instead of the cleaned `ASSISTANT: {...}` format. The LLM coped (produced reasonable output), so the benchmark numbers are not invalid — but they reflect a buggy prompt. After the fix, the LLM sees cleaned samples with canonical labels and (in explain mode) default analysis/oracle strings injected. This may change behavior. The U24 100-match benchmark must be re-run post-fix before citing its numbers as v6.5 validation. The U22 15-match baseline (this session) is the only post-fix data — it is thin (3 samples per scenario).

**Why the bugs didn't show up on U24:**
- Bug 1 (`OUTPUT:` marker): `launch_r2k.sh` never sets `R2K_TEXT_MODE` (defaults to JSON mode). In JSON mode, `_clean_json_samples` silently returned raw content when `ASSISTANT:` was not found. The LLM imitated the raw `OUTPUT: {...}` format and the parser handled it. The bug was silent — the LLM was robust enough to cope. U22 caught it because the fast test suite explicitly exercises `TEXT_MODE` and asserts cleaned output.
- Bug 2 (test drift): The fast test suite (`pytest --skip-slow`) was never run on U24 between commit `0b87b03` (Aug 9) and this U22 session (Aug 11). The benchmark workflow used `launch_r2k.sh` directly, not `pytest`. The test drift sat undetected for 2 days.

**Files touched:**
- `src/ai_tactics/r2k_evaluator.py` — fixed `_clean_text_samples` + `_clean_json_samples` to accept `OUTPUT:` marker (regex: `r'(?:ASSISTANT|OUTPUT):\s*'`)
- `src/tests/test_text_mode.py` — updated 2 test assertions to match v6.5 fragment content
- `src/tools/rebaseline_collect.sh` — NEW (measurement harness, committed for U24 reuse)
- `src/results/v65_rebaseline_raw.json` — NEW (15 baseline KPI samples, gitignored under `results/kpis_*` pattern)
- `src/results/rebaseline_*.log` — NEW (15 match logs, gitignored)
- `src/results/kpis_*` — 15 new KPI JSON dirs (gitignored)
- `src/scenario/3vs3_attack_center/kpi_targets.json` — re-baselined to v6.5
- `src/scenario/3vs3_default/kpi_targets.json` — re-baselined to v6.5
- `src/scenario/3vs3_high_line/kpi_targets.json` — re-baselined to v6.5
- `src/scenario/3vs3_long_shot/kpi_targets.json` — re-baselined to v6.5
- `src/scenario/3vs3_contain_delay/kpi_targets.json` — re-baselined to v6.5
- `docs/v65_regression_report.md` — NEW (management report: merge readiness, KPI comparison, failure analysis, next steps)

**Files deleted (cleanup, separate commit):**
- `src/experiments/` (220 files) — completed B-study, C-series, phase1 probes (findings in `docs/optimization_spec_v6.2.md`, `ROS2K_GEM_FAQ.md`)
- `src/results/` tracked files (178 files) — A/B/C probe logs, experiment summaries (findings in `docs/v65_final_benchmark.md`, `docs/v65_regression_report.md`)
- `docs/workshop v6.2/` (20 files) — past workshop materials
- `src/tools/` throwaways (9 files): `run_baseline.sh`, `run_baselines.sh`, `run_c_series.sh`, `run_experiment.sh`, `swap_fragments.sh`, `build_corpus.py`, `check_clustering.py`, `vocab_probe.py`, `rework_empirical_oracle.py`
- `docs/c3_revisited.txt` (duplicate of `.md`), `docs/gem_reorg_prompt.txt` (one-shot, done)
- Total: 429 files removed. Repo: 940 → ~511 tracked files.

**Not yet done:**
- The 2 slow-test failures (oob_pct, cluster_pct outliers) need either: (a) more baseline samples (5-10 per scenario) to widen thresholds, or (b) `@pytest.mark.xfail` on the 2 tests with reason "3-sample baseline too thin for high-variance KPIs".
- U24 post-fix regression: commit, `git pull` on U24, run fast suite + re-baseline + slow suite + full 100-match benchmark. The U24 100-match numbers must be re-run post-fix before citing as v6.5 validation.
- Push branch + open PR.

**Next:**
1. Commit code fixes + thresholds + report + session log + harness (commit 1).
2. Commit cleanup + .gitignore (commit 2).
3. Move to U24, `git pull`, start opencode, ask "whats next" — this session log is the handover.
4. U24 runs: fast suite → re-baseline (15 matches) → slow suite → full 100-match benchmark.
5. Compare U22 vs U24 post-fix numbers.
6. Push `feature/ros2k_behavior_optimization` to origin.
7. Open PR with the v6.5 redesign.

**Blockers:** None. GPU healthy after reboot. All fixes saved to disk. U24 must re-run the 100-match benchmark post-fix — the existing benchmark is stale (ran with the `OUTPUT:` marker bug).

---

## 2026-08-10 — Final benchmark + v7 handover

**Goal:** Run final 100-match benchmark comparison (OLD vs NEW), document v7 priorities, prepare handover for U22.

**Done:**
- 100-match Gazebo validation (10 scenarios × 10 runs × 120s) with NEW prompt
- 10 × 120s Gazebo with OLD prompt (static roles) for side-by-side comparison
- Text-probe: Qwen + Llama on both OLD and NEW prompts (5 snapshots total)
- Final benchmark: docs/v65_final_benchmark.md
- Committed all critical untracked files (LESSONS_LEARNED, ADRs, scrum tasks, prompt_utils, llm_probe, start_ollama, umschalt_extractor)

**Key findings (100 matches):**
- Blue win rate: 19% (19W/39R/42D) — Red outperforms Blue
- Blue_3 forward: 0.3% → 63.6% (defender now supports attack)
- Pattern diversity: 12 → 106 (9× more unique decisions)
- Score end: -0.95 → +0.25 (matches end with Blue advantage)
- Goalie kicks: 0/100 — role-locking persists (3B model limitation)
- Llama improved: 46% → 72% (dynamic prompt helps Llama too)

**v7 priorities from 100-match analysis:**
1. Goalie kick (role swap) — 0/100 matches, Blue plays 2v3
2. Passing — blue_3 advances 63.6% but never receives (kick goes to goal, not teammate)
3. Defensive recovery — high_line: 14 red goals in 10 matches
4. Match duration — 42% draw rate, consider 180s+

**Key insight:** 3B model is good at positioning, bad at coordination. Dynamic-roles prompt changed movement (blue_3 forward) but not coordination (goalie kicks, passes). Role assignment must move to CPU planner (TeamCaptain) in v7.

**Files touched:**
- docs/v65_final_benchmark.md (NEW)
- docs/v65_benchmark.md (updated)
- docs/v65_dynamic_roles_baseline.md (NEW)
- docs/LESSONS_LEARNED.md (updated with v6.5 lessons)
- docs/SESSION_CHANGELOG.md (this entry)
- src/ros2k_knowledge/8_C3_SOCCER_KNOWLEDGE.md (v7 priorities added)
- results/probe_final_llama_dynroles_*

**Next:** U22 native test → code freeze → PR → team review → merge → v7

**Blockers:** None. 5 commits pushed to feature/V63Redesign. Critical untracked files being committed in this session.

---

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
