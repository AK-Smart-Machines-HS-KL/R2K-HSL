# Overnight Regression & Match Analysis — 2026-09-13/14 (morning report)

> Trigger: user match `…205617` (3vs3_default) "both teams weird behavior".
> Run: `tools/overnight_regression.sh` (branch `docs/v68Planning` @ `14179d2`),
> slow tier 26:51 min + 4-match battery. Raw report: `overnight_20260914_081439.md`.

## 1. Platform regression — VERDICT: green (platform), red (3 threshold gates)

| Tier | Result | Assessment |
|---|---|---|
| Fast tier | **251 passed / 20 failed / 6 skipped** | the 20 = documented pre-existing i3_sweep (backlog origin) — no U24 delta |
| Sim battery | **12/12** | clean |
| Slow tier | **8 passed / 3 failed** — all `*_performance` (attack_center, default, contain_delay); ALL 6 `*_goalie` + latency + high_line + long_shot pass | see below |

**Slow-tier infra finding (fixed during the run):** `run_match_headless`
hardcoded `--relay only_sim_bots` — deleted in the 09-06/07 rename → the slow
tier could not launch at all. Patched to `sim_only` (test_non_functional.py).
`batch_evaluator.py` + `tournament.py` + `rebaseline_collect.sh` still carry
the stale relay (batch_evaluator is documented-deprecated; tournament/rebaseline
are tools — cleanup-list items).

## 2. The 3 failures are the composite threshold, not broken robots

Recomputed composite from the on-disk KPI JSONs across **6 × 3vs3_default runs**
(2 slow-tier + 4 battery):

| Run | Goals | Composite | Verdict (≥0.4) |
|---|---|---|---|
| …082204 | 0-0 | 0.325 | FAIL |
| …082430 | 2-0 | 0.420 | PASS |
| …084134 | 1-0 | 0.354 | FAIL (oob 68.7%) |
| …084400 | 0-1 | 0.308 | FAIL |
| …084616 | 3-0 | 0.505 | PASS |
| …084843 | 1-1 | 0.334 | FAIL |

**Pattern: composite correlates with goals.** Weight analysis: `goal_diff_norm`
(1 goal = +0.1 normalized) × 0.4 weight = only +0.04/goal — but scoring also
lifts `tactical_score_avg` (momentum), which is where the real composite
movement comes from (goal-runs show tac +1.0..+2.8 vs 0-0-runs −0.7..−1.0).

**A balanced 0-0 match mathematically lands at ~0.33** (tac_norm 0.5 × 0.3 +
poss 0.5 × 0.2 + latency 0.08) — **structurally below the 0.4 gate**. The
0.4 threshold was calibrated from the v6.7 10-sample baseline (obs
0.470–0.636) — a goal-rich sample. Single-sample assertions on a metric with
this much goal-luck variance (same prompt+model: 0.296–0.505) are flaky by
construction: every scenario ran TWICE in the slow tier and the pairs differ
by up to 0.12.

**Verdict: not a code regression — a threshold-structure problem.** All
sub-KPIs passed in every run (possession 39–64%, goalie_tactical 72–97%,
latency ~670 ms, parse errors 0).

## 3. The behavioral finding: kick aims

Aggregate kick-target distribution across the 6 runs (915 Kick assignments):

| Target class | Share | Note |
|---|---|---|
| center (|x| ≤ 2) | **~60%** | kicks toward/behind midfield |
| own-side (x < −2) | ~14% | kicks toward own goal |
| goal-side (x > 2) | ~25% | correct |
| no target | ~15% | bridge resolves to goal center |

Run variance is large (goal-side 7–79 per run). When blue DID kick goal-side
abundantly (…084616: 79 goal-side kicks), it won 3-0 with composite 0.505 —
**the kick-aim teaching is the highest-leverage behavioral fix.** The goalie
wander (blue_1 |x| up to 4.2–6.0 m) persists across runs but correlates with
the LLM's goalie assignments, not the bridge.

## 4. Issues in the harness itself (fixed / queued)

1. **`run_match_headless` relay** — `only_sim_bots` → `sim_only` (the slow
   tier could not launch; fixed in test_non_functional.py during this run).
   Same stale reference remains in `batch_evaluator.py` (×2),
   `tools/tournament.py`, `tools/rebaseline_collect.sh` → cleanup list.
2. **Run-ID extraction bug in the battery loop** — the dual-expression sed
   fails on the emoji-prefixed `Run ID:` line; `awk '{print $4}'` works.
   Fixed pattern for the script's next revision (all 4 launches actually ran;
   analyzed from traces post-hoc).
3. **Single-sample composite gates are flaky** — recommend: 3-sample median
   for composite assertions, OR recalibrate the 0-0 baseline (the formula's
   goal weight 0.4 × /10 makes one goal only +0.04 — spec §5.2 review).

## Recommended actions (priority order)

1. **Fix the kick-aim teaching** (samples/prompt): the 3B must prefer goal-side
   Kick targets — 74% center/own-side kicks is possession donation. Then re-run
   the default-performance gate.
2. **Composite gate repair**: assert the sub-KPIs (all PASS) as the hard gate;
   treat composite as a 3-sample trend metric, not a single-match pass/fail.
3. Keep the overnight script; add the trace-filename run-id fallback
   (`awk '{print $4}'` or newest-trace glob) so stdout parsing can't zero it.
