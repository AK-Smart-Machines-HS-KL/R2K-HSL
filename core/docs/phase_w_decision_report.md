# Phase W Decision Report — Watchdog Divergence Scenarios

> Generated 2026-08-08. Local only — not committed.

---

## 1. Objective

Test whether a second-model monitor (Llama-3.2-3B) can detect and correct
Qwen-2.5-3B's tactical decision failures on 6 synthetic divergence scenarios.

## 2. Divergence Scenarios

| ID | Scenario | Failure mode | Expected wrong decision |
|---|---|---|---|
| W1 | w1_goalie_abandonment | Goalie leaves goal open | blue_1 rushes forward |
| W2 | w2_clustering_trap | 3 bots stay clustered | No spreading |
| W3 | w3_wrong_direction_kick | Kick toward own goal | blue_2 kicks toward -X |
| W4 | w4_unmarked_attacker | Ignore red near goal | All bots ball-focused |
| W5 | w5_boundary_violation | Bot sent OOB | Target past X=4.5 or Y=3.0 |
| W6 | w6_passivity_trap | Nobody challenges ball | All bots hold |

## 3. Text-Probe Results (llm_probe.py, F0 config, 10 repeats)

| Scenario | Qwen hard-pass | Qwen failure mode | Llama hard-pass | Llama failure mode |
|---|---|---|---|---|
| W1 goalie_abandonment | 100% | — | 30% | missing bots (7/10) |
| W2 clustering_trap | 100% | — | 30% | missing bots (7/10) |
| W3 wrong_direction_kick | 100% | — | 50% | missing bots (5/10) |
| W4 unmarked_attacker | 80% | missing bots (2/10) | 40% | missing bots (6/10) |
| W5 boundary_violation | 100% | — | 60% | missing bots (4/10) |
| W6 passivity_trap | 20% | missing bots (8/10) | 40% | missing bots (6/10) |

**Key finding:** Qwen's primary failure mode is **dropping blue_1 (goalie)** —
outputting only 2 bots instead of 3. This happens most on W6 (passivity trap,
80% fail) and W4 (unmarked attacker, 20% fail).

**Llama fails more often** (40-70% hard-pass) with the same failure mode
(missing bots), but also has structural issues (wrong coverage, bad positions).

## 4. Monitor POC Results (phase_w_monitor.py, 5 repeats)

| Metric | Value |
|---|---|
| Qwen hard-pass (with production prompt) | 30/30 (100%) |
| Monitor (Llama) approved | 0/30 (0%) |
| Monitor corrected | 30/30 (100%) |
| Corrections that fixed a Qwen failure | 0/30 |
| Latency with monitor | 1095ms (vs 334ms Qwen alone) |

**Key finding:** With the production system prompt (K3 header, rules, samples),
Qwen passes 100% on all 6 scenarios — the earlier 20-80% failures were from the
simpler F0 probe config (no K3 rules). The divergence scenarios do NOT trigger
Qwen failures with the production prompt.

**Llama as monitor is useless:** It NEVER approves (0/30), always tries to
correct, but its corrections are never better (0/30 fixed). It adds 760ms
latency with zero benefit. Llama's own hard-pass is 46% — it's worse than Qwen,
so it can't reliably identify Qwen errors.

## 5. Decision

**Option B (second-model monitor) is NOT recommended for production.**

### Reasons:
1. **Qwen doesn't fail on divergence scenarios with the production prompt.**
   The K3 header + rules + samples prevent the failure modes the scenarios
   were designed to trigger. The monitor has nothing to correct.
2. **Llama is worse than Qwen.** A monitor that's worse than the primary
   model can't reliably detect errors — it would flag correct decisions
   as errors (false positives) and miss actual errors (false negatives).
3. **760ms latency cost is unacceptable.** The production system runs at
   ~290ms decision latency. Adding 760ms would triple it to ~1095ms,
   making the system too slow for real-time robot control.
4. **0% correction success rate.** Even when Llama tries to correct, it
   never produces a better result than Qwen's original.

### What WOULD work (deferred to v7):
- **Heuristic checks (Option A):** Simple rules (count bots, check bounds,
  check goalie X) would catch the "missing blue_1" failure mode without a
  second LLM call. Cost: ~0ms (pure Python check). This is the recommended
  approach for v7 (TeamCaptain architecture, Task 10).
- **Re-prompt on heuristic failure:** If the heuristic detects a problem
  (e.g., only 2 bots), re-prompt Qwen with "WARNING: you must assign all 3
  blue bots." Cost: ~290ms (one extra Qwen call, only on failure).

## 6. Scenario Disposition

The 6 divergence scenarios are useful as regression test cases for the
production prompt. They verify that the K3 header prevents:
- Goalie abandonment (W1: 100% pass)
- Clustering (W2: 100% pass)
- Wrong-direction kick (W3: 100% pass)
- Unmarked attacker (W4: 80% pass — 2/10 still drop goalie)
- Boundary violation (W5: 100% pass)
- Passivity (W6: 20% pass with F0, 100% with K3 production prompt)

**Recommendation:** Keep the 6 W-scenarios as permanent regression tests.
Run them with the production prompt (not F0) to verify the K3 header
prevents failure modes.

## 7. Next Steps

- **Phase 4:** Live Gazebo demos (3-5 matches with --analyze)
- **Phase 5:** Final KPI table, spec → v6.5, code freeze
- **v7:** Implement heuristic checks (Option A) in TeamCaptain
