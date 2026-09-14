# Prefinal v6.5 Benchmark

> Generated 2026-08-08. Local only — not committed. Snapshot of current state
> before further model changes or Phase W.

---

## 1. Text-Probe Comparison (3 models, 50 scenarios × 10 repeats = 500 probes each)

| Model              | Hard-pass (all 50) | Hard-pass (3vs3, 47) | Clustering | Latency p50 | Notes                                                 |
| ------------------ | ------------------ | -------------------- | ---------- | ----------- | ----------------------------------------------------- |
| **qwen2.5:3b**     | **92%**            | **98%**              | **96.6%**  | **289ms**   | Production model, best overall                        |
| llama3.2:3b        | 46%                | 49%                  | 73.6%      | 322ms       | Cross-family check — fails on coverage + clustering   |
| nemotron-3-nano:4b | N/A                | N/A                  | N/A        | N/A         | Thinking model — hangs on complex prompts, not viable |

**Verdict:** Qwen2.5:3b is the clear production model. Llama3.2:3b fails the
hard-pass gate (46% < 90%) and clustering gate (73.6% < 80%). Nemotron is not
usable (thinking model, stalls on prompt evaluation).

**Llama failure analysis:** Llama's worst scenarios are 2vs2 (100% fail — same
phantom-blue_3 config artifact as Qwen), 3vs3_default (90% fail), and
3vs3_fast_counter (80% fail). The 46% hard-pass is not just the 2vs2 artifact —
Llama genuinely struggles with 3vs3 scenarios (49% vs Qwen's 98%).

---

## 2. Gazebo Score Trajectory Comparison (Qwen vs Llama, 5 scenarios × 5 runs × 4s)

| Scenario | Qwen t0 | Qwen t4 | Qwen delta | Llama t0 | Llama t4 | Llama delta |
|---|---|---|---|---|---|---|
| 3vs3_attack_center | +3.45 | +3.13 | -0.32 | +3.45 | +3.17 | -0.28 |
| 3vs3_defensive_crisis | -3.00 | -3.38 | -0.38 | -3.00 | -3.14 | -0.14 |
| 3vs3_default | +0.88 | +0.48 | -0.40 | +0.88 | +1.37 | +0.49 |
| 3vs3_overload | +2.00 | +1.68 | -0.32 | +1.60 | +0.94 | -0.66 |
| 3vs3_high_line | -2.74 | -6.46 | -3.72 | -2.74 | -7.12 | -4.38 |

**Key finding:** Score trajectories are similar between models because the score
formula is position-based, not LLM-dependent. The LLM affects WHERE bots move,
but the score formula rewards being close to the ball regardless of which LLM
sent the bot there. The real LLM quality difference is visible in the text-probe
(structural correctness), not in Gazebo score trajectories.

**Llama slightly better on:** 3vs3_default (+0.49 vs -0.40), 3vs3_defensive_crisis
(-0.14 vs -0.38)
**Llama worse on:** 3vs3_overload (-0.66 vs -0.32), 3vs3_high_line (-4.38 vs -3.72)

---

## 3. Hand-Crafted Score Trajectories (Qwen, 17 scenarios × 5 runs × 4s, option D)

| Scenario | t0 mean | t4 mean | Delta | Trend |
|---|---|---|---|---|
| 2vs2_default | -0.38 | -3.14 | -2.76 | regress |
| 2vs2_goalie_pass | +0.09 | +0.74 | +0.65 | improve |
| 3vs3_attack_center | +3.45 | +3.13 | -0.32 | stable |
| 3vs3_attack_wing | +3.21 | +0.79 | -2.42 | regress |
| 3vs3_contain_delay | +0.45 | +1.08 | +0.63 | improve |
| 3vs3_deep_cross | +2.88 | +2.44 | -0.44 | stable |
| 3vs3_def_transition | +1.61 | +2.19 | +0.58 | improve |
| 3vs3_default | +0.88 | +0.48 | -0.40 | stable |
| 3vs3_defensive_crisis | -3.00 | -3.38 | -0.38 | stable |
| 3vs3_fast_counter | +1.96 | +0.94 | -1.02 | regress |
| 3vs3_goalie_distribution | -3.55 | -4.19 | -0.64 | regress |
| 3vs3_high_line | -2.74 | -6.46 | -3.72 | regress |
| 3vs3_long_shot | +0.72 | +3.32 | +2.60 | improve |
| 3vs3_overload | +2.00 | +1.68 | -0.32 | stable |
| 3vs3_possession_lost | +1.95 | +2.38 | +0.43 | improve |
| 3vs3_pressing_trap | +0.94 | +2.67 | +1.74 | improve |
| 3vs3_wing_switch | +1.49 | +2.75 | +1.26 | improve |

**Summary:** 7 improving, 5 stable, 5 regressing. The pressing reward (option D)
successfully prevented the catastrophic score crashes seen with the old formula.
Remaining regressions are in high-stress defensive scenarios (high_line,
goalie_distribution) and 2vs2 (config artifact).

---

## 4. Empirical Regression Tests (33 scenarios × 8s, option D)

| Metric | Value |
|---|---|
| Goals in 8s | 21/33 (64%) |
| No goals in 8s | 12/33 (36%) |
| Test pass rate (goal reproduces) | 21/33 |

**Note:** "No goal in 8s" doesn't mean the test failed — Gazebo non-determinism
(CV=90-129%) means the goal may not reproduce in every 8s window. The text-probe
is the primary validation instrument; Gazebo is supplementary.

---

## 5. Score Formula (option D, stateless)

```
score = ball_x × 1.5                        # ball in opp half = positive
      + possession(±2.0)                     # blue within 1m: +2; red: -2
      - cluster_penalty(< 0.5m: -2, < 1.0m: -1)
      - lane_openness(0 blockers: -3)
      + blockers_bonus(≥ 2: +1)
      + max(0, 3.0 - dist_blue) × 1.0        # pressing: continuous proximity reward
      + max(0, 3.0 - nearest_blue_red) × 0.5 # marking: only when red closer to ball
      clamped to [-10, +10]
```

**Constants:** `PRESSING_GAIN=1.0`, `PRESSING_REFERENCE_DIST=3.0`,
`MARKING_GAIN=0.5`, `MARKING_REFERENCE_DIST=3.0`

**Design:** Stateless (no per-frame tracking). Rewards being CLOSE to the ball,
not closing distance. Partially offsets the -2.0 possession flip (+1.6 at 1.4m
from ball).

---

## 6. Scenario Package Status (50 scenarios)

| Category | Count | Scope | Oracle reasoning | Field diagrams | Score charts | Format |
|---|---|---|---|---|---|---|
| Hand-crafted | 17 | Expert section | Scenario-specific | ✓ (ensemble) | ✓ (5×4s) | 8 sections |
| Empirical | 33 | ✓ (33/33) | "to achieve X" (33/33) | ✓ (bar-delta) | ✓ (8s) | 8 sections |

**Known issues:**
- Empirical chart visual bugs (16/33): goal marker position, NO GOAL label
- 2vs2 config artifact (3 scenarios): 0% hard-pass (phantom blue_3)
- 3vs3_default + 3vs3_overload: hard-fail in text-probe (investigate in Phase W)

---

## 7. Infrastructure

| Component | Status |
|---|---|
| Ollama | Running, GPU, flash-attention, q8_0 KV cache |
| qwen2.5:3b | Warm, p50 289ms |
| llama3.2:3b | Warm, p50 322ms |
| nemotron-3-nano:4b | Not viable (thinking model, hangs) |
| Docker (U24) | Running, Gazebo builds OK |
| Warp-and-resume | Built (`tools/warp_and_run.py`), not tested |
| 147 fast tests | Pass |

---

## 8. Knowledge Base Updates

| File | Update |
|---|---|
| `AGENTS.md` | No-hardcoded-thresholds convention |
| `8_C3_SOCCER_KNOWLEDGE.md` | Wing convention, score range, scoring formula |
| `docs/scenario_review_guide.md` | New: review guide for team members |
| `docs/SESSION_CHANGELOG.md` | 4 entries (2026-08-07, 2026-08-08) |

---

## 9. Phase W — Watchdog Divergence Scenarios (DONE)

### 6 synthetic divergence scenarios built

| ID | Failure mode | Qwen hard-pass (F0) | Qwen hard-pass (production K3) |
|---|---|---|---|
| W1 | Goalie abandonment | 100% | 100% |
| W2 | Clustering trap | 100% | 100% |
| W3 | Wrong-direction kick | 100% | 100% |
| W4 | Unmarked attacker | 80% (2/10 drop goalie) | 100% |
| W5 | Boundary violation | 100% | 100% |
| W6 | Passivity trap | 20% (8/10 drop goalie) | 100% |

**Key finding:** The production K3 prompt prevents all 6 failure modes.
The F0 probe config (simpler, no K3 rules) triggers failures on W4 and W6.
The K3 header + rules + samples are load-bearing.

### Option B (second-model monitor) — NOT recommended

| Metric | Value |
|---|---|
| Qwen hard-pass (production prompt) | 30/30 (100%) |
| Monitor (Llama) approved | 0/30 (0%) |
| Monitor corrected | 30/30 (100%) |
| Corrections that fixed a Qwen failure | 0/30 |
| Latency with monitor | 1095ms (vs 334ms Qwen alone) |

**Decision:** Option B rejected. Llama is worse than Qwen (46% vs 92% hard-pass),
can't reliably detect errors. Adds 760ms latency with zero benefit.

**Recommended for v7:** Option A (heuristic checks) — simple Python rules
(count bots, check bounds, check goalie X) catch the "missing blue_1" failure
mode at ~0ms cost. Re-prompt Qwen on heuristic failure (~290ms, only on failure).

Full report: `docs/phase_w_decision_report.md`

---

## 10. What's Next

| Phase | Description | Est. time | Status |
|---|---|---|---|
| Phase W | 6 divergence scenarios + second-model monitor POC | DONE | ✓ |
| Phase 4 | Live Gazebo demos with --analyze | 1h | Not started |
| Phase 5 | Final KPI table, spec → v6.5, code freeze | 1h | Not started |

**Recommendation:** Qwen2.5:3b remains the production model. Llama3.2:3b is
not viable for production (46% hard-pass, 73.6% clustering). Nemotron is not
usable. The inter-lingua approach is Qwen-specific — cross-family portability
is not confirmed. Option B (second-model monitor) rejected — heuristic checks
(Option A) recommended for v7.

**For the team:** The scenario review guide (`docs/scenario_review_guide.md`)
is ready. Tasks 6 and 7 automated work is complete — human review pending.

---

## 11. Pre-freeze experiment: Goalie kicks + passes (DONE, no improvement)

### Experiment design
Played 5 × 120s Gazebo matches, analyzed LLM traces for:
- Goalie (blue_1) kick events
- Pass-like patterns (one kicks, another moves forward)
- Role swaps (goalie → attacker)
- Pattern diversity

### Findings

| Deficiency | Evidence | Root cause |
|---|---|---|
| Goalie never kicks | 0/344 calls in defensive_crisis (goalie was closest 252x) | Role-locking in header_k3.txt: blue_1=goalie=cover line, blue_2=attacker=kick |
| No passes | 0 pass-like patterns in defensive_crisis | blue_3 never moves forward (X>0) |
| Extremely repetitive | 1-3 unique patterns per 120s match | Content-hash skip + deterministic at temp=0.0 |
| No role swaps | blue_1=goalie 100%, blue_2=kicker 100%, blue_3=mover 100% | Roles never swap based on dynamic situation |

### Intervention attempted
Added 3 new samples to `samples_3vs3.txt`:
1. Goalie becomes closest → role swap (blue_1 kicks, blue_2 covers goal line)
2. Pass forward to free bot (blue_3 moves to X=3.5)
3. Ball carrier advances (blue_2 moves to X=2.0 instead of kicking)

### Result: No improvement

| Metric | Before samples | After samples |
|---|---|---|
| Goalie kicks (defensive_crisis) | 0/350 | 0/344 |
| Goalie closest but no kick | 341x | 252x |
| Blue_3 forward | 0 | 0-4 |
| Unique patterns | 1-3 | 1-2 |
| Text-probe hard-pass | 92% | 93% |

**Samples reverted.** The deficiencies are architectural — the LLM is role-locked
by `header_k3.txt` and cannot swap roles mid-match. This requires v7 TeamCaptain
(CPU planner handles role assignment) or stronger prompt engineering (remove
role labels entirely).

### Documented as known limitations for v6.5
1. Goalie never kicks (even when closest to ball)
2. No passes (blue_3 never moves forward to receive)
3. Very few unique decision patterns per match (1-3)

These are **not regressions** — they existed in v6.4 and all prior versions.
The v6.5 improvements (score formula option D, Oracle target fixes, kickoff
rule) do not affect these limitations.
