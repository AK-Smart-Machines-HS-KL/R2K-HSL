---
id: 7_04
title: "Prompt Architecture: Fragments, Assembly & Study Findings"
type: SPECIFICATION
tags: [prompt, fragments, setup_r2k, dump-prompt, b-study, consolidated, strat-artifact, sample-override, explain, goalie-idle, v6, v6.1, v6.2]
last_modified: 2026-07-15
version: v6.2
---
# Prompt Architecture: Fragments, Assembly & Study Findings

> [!info] Human Summary
> This document specifies how the LLM system prompt is assembled from text fragments,
> the findings from the bottom-up prompt engineering study (B1-B7b), and the consolidated
> v6.2 prompt that serves as the current production default.

> [!abstract] LLM Context Anchor
> There is NO static `system_prompt.txt` committed to version control. It is stitched
> together dynamically at boot by `setup_r2k.py` from fragments in `strategy/fragments/`.
> V6.1 removed `strat_*.txt` build artifacts (gitignored). Strategy-specific fragments
> override mode fragments. The B-study found that 1 sample + rules + `--no-explain` is
> the optimal configuration for `qwen2.5-coder:3b`.

---

## 1. Fragment Assembly (`setup_r2k.py:111-136`)

### 1.1 Assembly Order

```
header.txt          → ACT_ON_BOTS line + MODE line + {{EXPLAIN_INSTRUCTION}}
rules_core.txt      → field limits, valid actions, strict laws, kick-in exception
rules_{strat}.txt   → strategy-specific rules (OVERRIDES rules_{mode}.txt if exists)
samples_{strat}.txt → strategy-specific samples (OVERRIDES samples_{mode}.txt if exists)
```

The final prompt is written to `ai_tactics/system_prompt.txt` (transient, overwritten
on every boot).

### 1.2 Override Logic (V6.1 Fix)

Strategy-specific fragments take precedence over mode fragments:

```python
# setup_r2k.py:116-120 (simplified)
if os.path.exists(f"{frag_path}/rules_{clean_strat}.txt"):
    files.append(f"rules_{clean_strat}.txt")    # e.g. rules_recover.txt
else:
    files.append(f"rules_{mode}.txt")           # e.g. rules_3vs3.txt

if os.path.exists(f"{frag_path}/samples_{clean_strat}.txt"):
    files.append(f"samples_{clean_strat}.txt")  # e.g. samples_recover.txt
else:
    files.append(f"samples_{mode}.txt")         # e.g. samples_3vs3.txt
```

> [!warning] V5 bug (fixed in V6.1)
> Previously, both strategy-specific and mode-specific fragments were appended,
> sending contradictory signals (e.g. aggressive + defensive samples in the same
> prompt). Now strategy-specific fragments REPLACE mode fragments.

### 1.3 `strat_*.txt` Build Artifacts Removed

`setup_r2k.py` no longer writes `strategy/strat_*.txt` files. These were build
outputs assembled from fragments. They are:
- Gitignored (`.gitignore`)
- Deleted from version control (`git rm`)
- NOT created on boot

The fragments in `strategy/fragments/` are the sole source of truth.

### 1.4 `{{EXPLAIN_INSTRUCTION}}` Template

`header.txt` contains a `{{EXPLAIN_INSTRUCTION}}` placeholder replaced at runtime:

| Flag | Replacement |
|------|-------------|
| `--no-explain` | `- Output ONLY the 'assignments' key.` |
| `--explain` | `- Include 'analysis' and 'oracle' keys.` |

This controls the LLM's output format (assignments-only vs. with reasoning).

---

## 2. Fragment Files (Current)

### 2.1 `rules_core.txt` (13 lines — universal)

```
FIELD LIMITS: X is between -4.5 and 4.5. Y is between -3.0 and 3.0.
Opponent Goal: X=4.5 (Always attack this direction).
Own Goal: X=-4.5 (Never shoot this way).

VALID ACTIONS:
1. {"action": "Move", "x": float, "y": float}
2. {"action": "Kick"}

STRICT LAWS:
- STAY INSIDE FIELD AT ALL TIMES. Never output Move targets with X outside [-4.5, 4.5]
  or Y outside [-3.0, 3.0]. If the ball is near a boundary, approach from inside.
- NO OWN GOALS: Never kick if you are between the ball and your own goal (X=-4.5).
- DYNAMIC GOALIE TRACKING (CRITICAL): The goalie MUST ALWAYS defend by moving to
  X=-4.0. Its Y MUST EXACTLY MATCH the soccer_ball's Y. Never use static Y!
- KICK-IN EXCEPTION: If match_state.status is "ball_out", "goal_kick", or
  "corner_kick_in", the restart bot MAY move up to 1m outside the field boundary.
  After the kick, return inside immediately.
```

### 2.2 `samples_3vs3.txt` (9 lines — 1 sample)

```
--- EXAMPLE 1: MIDFIELD PASSING (NO KICK YET) ---
INPUT: {"soccer_ball": {"x": -1.0, "y": 0.0}, "blue_1": {"x": -4.0, "y": 0.0},
        "blue_2": {"x": -1.5, "y": 0.0}, "blue_3": {"x": 1.0, "y": 2.0},
        "red_1": {"x": 0.0, "y": 0.0}}
ASSISTANT: {
  "assignments": {
    "blue_1": {"role": "goalie", "action": "Move", "x": -4.0, "y": 0.0},
    "blue_2": {"role": "passer", "action": "Kick"},
    "blue_3": {"role": "receiver", "action": "Move", "x": 1.5, "y": 2.0}
  }
}
```

### 2.3 Other Fragment Files

| File | Purpose |
|------|---------|
| `rules_3vs3.txt` | 3vs3-specific rules (anti-clustering, role assignment) |
| `rules_recover.txt` | Recovery strategy rules (defensive transition) |
| `rules_2vs2.txt`, `rules_1vs1.txt`, etc. | Mode-specific rules for other team sizes |
| `samples_recover.txt` | Recovery strategy samples (defensive transition) |
| `samples_2vs2.txt`, `samples_1vs1.txt`, etc. | Mode-specific samples |

---

## 3. B-Study Findings (Phase 1 — Completed)

11 experiments (B1-B7b) × 3 runs × 120s on `3vs3_attack_center` with `qwen2.5-coder:3b`.

### 3.1 Results Table

| Exp | Variable | Goals B:R | Cluster% | OOB% | Lat p50 | Key finding |
|-----|----------|-----------|----------|------|---------|-------------|
| A | Baseline (3 samples) | 0.7:1.0 | 15.7% | 30.6% | 827ms | High variance |
| B1 | +2 anti-cluster samples | 0.7:1.7 | 6.9% | 9.3% | 834ms | Less cluster, more conceded |
| B2 | B1 samples, no rule | 0.7:0.3 | 17.8% | 39.8% | 825ms | Within noise |
| B3 | +match_state injection | 0.7:1.0 | 21.5% | 13.1% | 814ms | No improvement |
| B4a | Goalie x=-4.0 | 0.0:0.3 | 1.6% | 19.0% | 815ms | Fewer conceded |
| B4b | Goalie x=-4.5 | 0.0:1.0 | 6.7% | 20.2% | 811ms | Worse than -4.0 |
| B5 | --explain (600 tokens) | 0.3:1.3 | 24.4% | 1.9% | 1190ms | OOB fixed, +44% latency |
| B6a | 1 sample only | 1.7:1.0 | 2.6% | 16.4% | 742ms | **Best scorer** |
| B6b | 6 samples | 0.3:1.7 | 18.7% | 15.2% | 792ms | Diminishing returns |
| B7a | Rules-only, 0 samples | 0.0:2.0 | 0% | 0% | 320ms | **Total failure** |
| B7b | Samples-only, empty rules | 0.0:1.0 | 4.3% | 46.3% | 744ms | OOB explosion |

### 3.2 Research Conclusions

**RQ1 (rules vs. samples):** Both are necessary. Without samples (B7a), the 3B model
produces empty/degenerate JSON. Without mode rules (B7b), bots leave the field (46% OOB).
Samples provide format; rules provide boundaries.

**RQ2 (sample-count plateau):** 1 sample (B6a) is the sweet spot. More samples dilute
focus and increase latency without improving behavior. The 3B model copies one pattern;
it doesn't learn from diversity.

**RQ3 (alternatives):** Explain mode (B5) reduces OOB to 1.9% via explicit reasoning,
but costs 44% latency. Adding explicit "STAY INSIDE FIELD" text to rules achieves similar
OOB reduction without the latency cost (applied in consolidated v6.2 prompt).

> [!warning] High variance
> Within-experiment OOB spread up to 50 percentage points across 3 runs. 3 runs gives
> directional insight only; 10+ runs needed for statistical confidence (D8 experiment).

---

## 4. Consolidated v6.2 Prompt

Based on B-study findings. Current `strategy/fragments/` already matches:

| Element | Value | Source |
|---------|-------|--------|
| Rules | `rules_core.txt` with STAY INSIDE FIELD | B5 finding: explicit boundary text ≈ explain mode for OOB |
| Goalie X | -4.0 | B4a better than B4b (-4.5) |
| Samples | 1 sample (midfield passing) | B6a finding: 1 > 3 > 6 |
| Explain | `--no-explain` (150 tokens) | B5 finding: explain +44% latency not worth it |
| Temperature | 0.0 | Hardcoded in `r2k_evaluator.py` |
| `R2K_INCLUDE_MATCH_STATE` | Off (default) | B3 inconclusive |

---

## 5. Goalie Idle — Structural Limitation

> [!warning] Not fixable via prompt engineering
> Goalie idle rate is 80-100% across ALL experiments. This is structural.
>
> **Root cause:** The bridge PD controller chases a jittery ball-Y setpoint. The
> `smooth_membership` + low-pass filter overreacts to ball position noise.
>
> **Implication:** Do NOT fix goalie behavior by changing prompt text. The fix must
> be in the bridge PD controller (Phase 5.1: Kalman filter → smoother ball-Y).

---

## 6. Verification with `dump_prompt.py`

Always verify prompt changes before launching:

```bash
cd core/src
python3 tools/dump_prompt.py --scenario 3vs3_attack_center --strategy strat_default --no-explain
```

This prints the full assembled prompt, per-fragment breakdown, and token estimate.
See [[7_03_CHEATPAGE_Tools_and_Utils]] for full usage.

---

## 7. Dynamic Prompt Selection (Roadmap — Phase 5.5)

The current prompt is static within a run. The full vision (v6.2 Phase 5.5) is:

- **Status-based:** switch fragment sets based on `match_state.status`
  - `playing` → current `rules_3vs3.txt` + `samples_3vs3.txt`
  - `ball_out` / `goal_kick` / `corner_kick_in` → `rules_restart.txt` + `samples_restart.txt`
  - `goal` → `rules_kickoff.txt` + `samples_kickoff.txt`
- **Game phase:** attacking vs defending vs transitioning
- **Performance-based:** losing by 2+ → aggressive prompt; winning → defensive prompt
- **Opponent adaptation:** detect red strategy, select counter-strategy

Implementation: new `prompt_selector.py` module called by `r2k_evaluator.py` before
each LLM call. See `core/docs/optimization_spec_v6.2.md` §7 Phase 5.5.

---

## 8. Related Documentation

| Topic | Document |
|-------|----------|
| Tools & Utils | [[7_03_CHEATPAGE_Tools_and_Utils]] |
| Experiment guide | [[7_05_CHEATPAGE_Experiment_Guide]] |
| Dynamic prompting (V5) | [[3_08_ARCHITECTURE_Dynamic_Prompting]] |
| Team Blue LLM | [[3_02_ARCHITECTURE_TeamBlue_LLM]] |
| Scoring & game state | [[7_01_INTRODUCTION_Scoring_Referee_Gamestate]] |
| RAG: Prompt & red logic | `ros2k_knowledge/3_AI_LOGIC_AND_EDGE_CASES.md` §V6.1 Addendum |
| Optimization spec | `core/docs/optimization_spec_v6.2.md` §4 Prompt Architecture |