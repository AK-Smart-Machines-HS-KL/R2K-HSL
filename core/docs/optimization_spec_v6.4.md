# Optimization Spec v6.4 — C3 Inter-Lingua Evaluation & Redesign

**Version:** v6.4
**Date:** 2026-08-03
**Supersedes:** `optimization_spec_v6.3.md` (C3 phases restructured; Gazebo reframed)
**Status:** Planning — Phases 0, 1, L, I, K, F DONE (committed: L=d115503, I=7b6b4fa); phases below are NEW or REVISED

---

## Glossary

Terms rare in everyday English but with a dedicated meaning in this project:

| Term | Meaning |
|---|---|
| **Bridge** | `ollama_sandbox_bridge.py` — the ROS 2 node that translates LLM output (JSON or TEXT instructions) into `Twist` commands (sim bots) or `RpcReqMsg` payloads (K1 hardware). Runs at 10Hz. Contains the goalie blending logic. |
| **Goalie blending** | The bridge overrides the LLM's target position for the goalie bot, blending 70% tactical positioning (goal-line hold when ball is near, angle-block when ball is far) with 30% LLM influence. Controlled by `GOALIE_TACTICAL_WEIGHT` in the bridge. |
| **Hedging / to hedge** | The LLM produces a non-committal, qualifying answer instead of a crisp instruction. Example: "blue_3 *could be considered* the striker... *however*... *not necessarily*." Discovered in the C2_striker_rule probe (Phase 1) — the model rejects dynamic role definitions and falls back to static human-soccer semantics with hedging. The C3 inter-lingua removes this by using situation-triggered position verbs instead of role labels. |
| **Inter-lingua** | The controlled-vocabulary intermediate language between the LLM and the bridge: verb+noun+coordinate sentences ("blue_1 move to (2.2, 0.3)") instead of JSON. The LLM outputs inter-lingua; the bridge parses it into robot commands. |
| **Hard pass** | A binary gate from `i3_battery.py` `score_result()`. A probe output "passes hard" if ALL three conditions hold: (1) coverage — every blue bot gets exactly one assignment, (2) in_field — all Move targets within field bounds, (3) roles_ok — roles in {goalie, attacker, defender} and ≤1 goalie. The `hard%` metric in sweep tables is the fraction of probes that pass all three gates. |
| **Soft score** | A 0–100 score from `i3_battery.py` measuring soccer-semantic quality (ball proximity, goalie compliance, spacing, set-piece awareness). Unlike hard pass, it's graded — a 69.9 soft score can still fail hard (e.g. F4_nok3h scored 69.9 but 0/3 gaps because no bot went to the ball). |
| **Gap diagnostic** | A soccer-semantic check in `i3_battery.py` that the soft score misses: `gapC` (competition — exactly ONE bot targets the ball, all others stay ≥1m away) and `gapP` (pass — a kick is present AND ≥1 non-kicker moves forward of the ball). |
| **Content-hash skip** | The evaluator hashes the transformed world-state text and skips the LLM call if positions+status haven't changed since the last call. At temperature 0.0, identical input → identical output → wasted GPU time. Saves 64% of calls per match. The hash uses `:.1f` (1-decimal) quantization, making TEXT mode skip more aggressively than JSON. |
| **Adaptive prediction horizon** | The evaluator projects all entity positions to `t + horizon` before sending the world state to the LLM, so the LLM sees where things *will be* when its command arrives. The horizon tracks an EMA (exponential moving average) of measured LLM round-trip latency, clamped to [0.15, 2.0]s. Updated only on HTTP 200 (cold-load spikes can't poison it). |
| **Phantom kick** | The bridge teleports the ball to its current position and assigns velocity via `/gazebo/set_entity_state` — a "kick" without a physical kicking motion. Single-phase (no 0.6m staging). Cooldown 2s per bot. |
| **Game-phase fragment** | A prompt fragment (`rules_ball_out.txt`, `rules_goal_kick.txt`, etc.) that is additively injected when `match_state.status` changes (e.g. to "ball_out"). The evaluator assembles the prompt at runtime from static + game-phase fragments. |
| **KV-cache non-determinism** | At temperature 0.0, the LLM is *not* bit-exact across calls — identical prompts can produce different token streams (e.g. 118 vs 91 tokens, pretty vs compact JSON) depending on KV-cache state. Semantics stay stable, so content-hash skip is safe, but latency A/B comparisons must control cache state. |
| **Spike project** | A design and architecture exploration project — not a production system. Accepts minor measurement errors. No claim of statistical 100% correctness. Gazebo is "more demo than measurement"; text-probe suite is the primary instrument. |
| **Text-probe** | A synthetic world-state (JSON or TEXT) sent to the LLM via `i3_battery.py` or `llm_probe.py`, with the output parsed and scored (hard pass, soft score, gap diagnostics). No Gazebo needed — pure LLM text-output analysis. The text-probe suite is the primary evaluation instrument (~80× faster than Gazebo, deterministic at temp 0.0 modulo KV-cache). |
| **K2 sweep** | Phase K sub-experiment: a positive-information sweep testing 10 cumulative prompt-content variants (v0–v9) added to the TEXT-mode prompt. Result: **v0 (current fragments, no additions) wins at 100% hard-pass**; every added block (geometry, principles, roles, decision rules, constraints, vocabulary, spacing, score/status) reduced hard-pass. Conclusion: static-context lengthening is rejected for TEXT mode. |
| **F3 sweep** | Phase F sub-experiment: structure sweep comparing 4 prompt architectures (F0 global rules + separate samples, F1 minimal rules + interwoven samples, F2 no global + interwoven only, F3 axioms + interwoven + explain). Result: **F0 wins at 93% hard-pass / 217ms**; interwoven variants (F1/F2) scored 56–62% at 932–978ms. Conclusion: the 3B model extracts rules from global declarative text + separate samples far better than from inline commentary. |
| **F0** | The winning prompt configuration from the F3 sweep: global `rules_core_text.txt` + `rules_3vs3.txt` + 1 separate JSON sample (`samples_3vs3.txt`) + K3 rules in `TEXT_OUTPUT_HEADER`, non-explain mode. This is the current production prompt — Phase F confirmed it needs no changes. |

---

## 0. Management Summary

### Paradigm (unchanged from v6.3)
Local trial-and-error + shared regression tests + commit only winners. No external framework (W&B, DSPy, Optuna — all evaluated and rejected, see ADR-A03).

### Gazebo framing (v6.4 correction)
Gazebo is **more demo than measurement.** This is a design and architecture spike project — no claim of statistical 100% correctness. We accept the risk of minor measurement errors. The text-probe suite remains the primary evaluation instrument; Gazebo provides supplementary quantitative data with caveats (CV=90–129% on goals/shots, n≥17 detects only large effects). Gazebo results are reported as descriptive statistics (means ± ranges, no significance tests) and labeled "directional, not statistical" in all output.

### What changed from v6.3
1. **Gazebo reframed** from "measurement instrument" to "more demo than measurement — supplementary quantitative data with caveats" (user decision 2026-08-03). Text-probe suite is the primary instrument.
2. **Quality assurance review** (2026-08-03) identified methodological gaps: single-annotator rubric (no IAA), n=1–3 (anecdotal), no self-agreement metric, no cross-model validation. Phase M addresses these.
3. **Human-in-the-loop** formalized as Phase H1 (early: scenarios + Oracle refinement + IAA) and H2 (after demo: live coach comments).
4. **Prediction evaluation** folded into Phase M (Part A, text-probe) and Phase 4 (Part B, Gazebo ON/OFF).
5. **Code cleanup** (Phase C): dead tools/experiments archived, duplications extracted, `start_ollama.sh` added.
6. **Roll-backs**: composite-score hard-gate assertions softened to wide-tolerance soft gates (spike-project caveat); invalid attack-KPI thresholds re-calibrated; explain-mode flag stays (debug for user inspection).

### Phase table

| Phase | Name | Status | Type | Est. time |
|---|---|---|---|---|
| 0 | Literature + model switch | ✅ DONE | text | — |
| 1 | Vocabulary probing → dictionary | ✅ DONE | text | — |
| L | Fragment migration | ✅ committed d115503 | text | — |
| I | Transform builder | ✅ committed 7b6b4fa | text | — |
| K | Behavior battery (K2/K3) | ✅ DONE | text | — |
| F | Few-shot paradigm rework (F3/F4) | ✅ DONE | text | — |
| **A** | **ADR authoring** | ✅ DONE | text | — |
| **H1** | **Human-in-the-loop (early)** | ✅ DONE | text + human | — |
| **C** | **Code cleanup + start_ollama.sh** | ✅ DONE | code | — |
| **M'** | **Iterative prompt-fix loop** | ✅ DONE | text | — |
| 2 | Rework analysis.md (dictionary vocab) | ⬜ NEXT | text | ~2h |
| 3 | Validate comprehension | ⬜ REVISED | text | ~1h |
| W | Watchdog & closed-loop feedback | ⬜ parallel | text | ~2h |
| 4 | Gazebo validation + prediction Part B | ⬜ REVISED (gated by M') | demo + supplementary | ~4h |
| **H2** | **Human-in-the-loop (demo coach)** | ⬜ NEW | demo + human | ~1.5h (user) |
| 4b | Llama-3.2-3B regression | ⬜ NEW (deferred to post-M') | text | ~1h |
| 5 | Full text-probe evaluation + demo walkthrough | ⬜ REVISED | text + demo | ~2h |
| **M** | **Variable sweep (DEFERRED)** | ⬜ deferred to post-M' | text | ~21h compute |

### Compute budget
- Phase M': ~15min (iterative text probes, n=10, 25 scenarios, 3 rounds)
- Phase 4: ~4h (demo runs + supplementary quantitative — ONLY if M' hard-pass > 80%)
- Phase 4b: ~1h (Llama cross-model — deferred to after M' gate)
- Phase M (deferred): ~21h (full factorial variable sweep — only if M' results warrant optimization)
- **Total new compute (to M' gate): ~15min** / **(to Phase 5): ~6h** / **(incl. deferred M): ~27h**

### Human budget
- H1: ✅ DONE (~2.5h user: 5 scenarios + Oracle refinement + IAA)
- M': ~3h (user: 10 new scenarios + 2-3 feedback rounds + GLM-5.2 dual feedback)
- H2: ~1.5h (user: live coach comments on 4 demo matches)
- **Total new human time: ~4.5h**

---

## 1. Roll-backs (execute before Phase A)

### RB-1: Composite-score assertions — soften to wide-tolerance soft gates
**Problem:** `test_non_functional.py` asserts composite-score thresholds (0.4·goal_diff + 0.3·tac_score + 0.2·possession + 0.1·latency) as hard gates. The formula was never validated against win/draw/loss ground truth, and Gazebo variance (CV=90–129%) makes tight thresholds unreliable.
**Action:** Keep composite-score in slow tests as a **soft gate with widened tolerances** (±50% margin instead of ±30%). Composite is a diagnostic that can flag gross regressions in the spike project without claiming statistical rigor. Add a comment in `test_non_functional.py` noting the spike-project caveat. Keep smoke-test assertions (scored ≥1? no crash? no OOB > 50%?) as the hard gate; composite becomes the soft gate beneath it.
**Files:** `tests/test_non_functional.py`

### RB-2: Invalid attack-KPI thresholds
**Problem:** 4 attack KPIs (`shots_on_goal`, `shots_on_target`, `pass_completion_pct`, `restart_recovery_time_s`) in 11 `kpi_targets.json` files were calibrated against the all-zeros baseline (t_wall bug, 2026-07-29). The t_wall code fix is committed but the data was never re-collected.
**Action:** Re-calibrate from a 3-run baseline per scenario; set thresholds from observed means ± 50% margin. Label as "directional, not statistical" in the file header.
**Files:** `scenario/*/kpi_targets.json` (11 files)

### RB-3: Explain-mode flag (NO roll-back)
**Decision (user 2026-08-03):** `--explain` stays in `--help`. Explain mode is for user inspection; performance is not an issue there. The F4_explain 56% hard-pass finding is informational ("explain crowds out commands"), not actionable.

---

## 2. Phase A — ADR Authoring

**Goal:** Record architectural decisions that are currently scattered across changelog entries into traceable Architecture Decision Records.

**Scope (6 ADRs):**

| ADR | Decision | Date | Status | File |
|---|---|---|---|---|
| ADR-A01 | Model switch: qwen2.5-coder:3b → qwen2.5:3b | 2026-07-31 | Accepted | `ADR-A01-model-switch.md` |
| ADR-A02 | Role condensation: 5 → 3 (goalie/attacker/defender) | 2026-07-28 | Accepted (no A/B test — Phase M sub-exp 2 tests this) | `ADR-A02-role-condensation.md` |
| ADR-A03 | Framework rejection: W&B, DSPy, Optuna → pytest+git | 2026-07-22 | Accepted | `ADR-A03-framework-rejection.md` |
| ADR-A04 | Gazebo reframing: measurement → more demo than measurement | 2026-08-03 | Accepted | `ADR-A04-gazebo-reframing.md` |
| ADR-A05 | Explain mode: production → debug-only (user inspection) | 2026-08-03 | Accepted | `ADR-A05-explain-mode-debug.md` |
| ADR-A06 | Ollama: user-space axiom vs. systemd override | 2026-08-03 | Needs reconciliation (see §15 Open Questions) | `ADR-A06-ollama-user-space-vs-systemd.md` |

**Format:** each ADR in `core/docs/adr/` with a mnemonic filename (`ADR-A0X-<short-name>.md`), containing sections: Context, Decision, Rationale, Alternatives Considered, Consequences, Status.
**Estimated time:** ~2h
**Notes:** 1 person sufficient.

---

## 3. Phase H1 — Human-in-the-Loop (Early)

**Goal:** Inject human soccer expertise into the evaluation pipeline before the methodology re-do and scenario rework. Four mechanisms, all before Phase M.

### H1.1 — Author 5 new scenarios (~1.5h of the 2.5h budget)
Author 5 scenarios covering missing patterns from `8_C3_SOCCER_KNOWLEDGE.md`:

| # | Scenario | Pattern | Why missing |
|---|---|---|---|
| S1 | 2-on-1 overload | P4 numbers advantage | TC-04 touches weakly |
| S2 | Defensive transition (possession lost) | P8 counter-attack cover | TC-08 Oracle is thin |
| S3 | Wing switch / play switch | P5 anticipate the block | No TC isolates this |
| S4 | Defending a deep cross | P-D6a two-man goal-mouth bracket | Only in 2vs2 |
| S5 | Goalkeeper distribution | (new pattern) | No TC starts with goalie in possession |

**Per scenario:** `scenario.json` (positions) + `field_diagram.png` (`gen_field_diagrams.py`) + `analysis.md` (Expert FIRST, Oracle second, every positional verb carries X,Y) + `kpi_targets.json` (placeholder, calibrated later).
**Verification:** run VERIFY probe (V_A format) against each Oracle, confirm all targets exact.

### H1.2 — Oracle refinement of 10 existing scenarios (~30min)
Re-read the 10 existing Oracles with deeper soccer knowledge. Sharpen coordinates, add conditional branches, remove vague cues (e.g. attack_center b3 "moves slightly forward" → explicit coordinate). Focus on the 3 thinnest: TC-05 pressing_trap, TC-08 def_transition, TC-09 high_line.

### H1.3 — Anti-pattern identification from PS_* logs (~30min)
Review `results/vocab_probe_log.md` PS_* records. Identify repeated tactical mistakes (ball-watching, far-post runner untracked, defenders pressing too high). Each anti-pattern → either a new gap diagnostic in `i3_battery.py` or a new rule in `rules_core_text.txt`.

### H1.4 — IAA second-annotator scoring (~30min)
Re-score 20% of existing ✓/◐/✗ verdicts (≈30 probes) blind, without seeing the original verdicts. Compute Cohen's kappa.
- kappa > 0.6 → original verdicts defensible; Phase M re-do is smaller (n≥30 re-probe only)
- kappa 0.4–0.6 → borderline; re-probe + partial re-annotation
- kappa < 0.4 → original verdicts unreliable; full re-annotation needed

**Notes:** **2 people recommended** for H1.4 — the user (soccer expert) scores blind; a second person (or the AI assistant) computes kappa and manages the blind scoring protocol. H1.1–H1.3 are 1-person work.

---

## 4. Phase M' — Iterative Prompt-Fix Loop (replaces Phase M)

**Goal:** Fix Qwen's fundamental cognitive failures (possession ID, defensive
awareness, goalie confinement) via targeted prompt modifications, validated
by the GLM-5.2 + human dual-feedback loop. Fast iteration — text-probe only,
no Gazebo, no full-factorial sweep.

**Rationale (user decision 2026-08-03):** H1 showed Qwen scores 0/5 in
zero-shot — the failures are fundamental (possession misidentification,
goalie abandons goal, no defensive awareness), not optimization gaps.
Sweeping input variables (yaw, velocity, score) when the model can't identify
which team has the ball is like tuning tire pressure when the engine is
broken. The GLM-5.2 + human dual-feedback loop agreed >95% — this is a
reliable evaluation method that doesn't require n=30 statistical rigor. Gazebo
on current Qwen = dead blue team = waste of time.

**Phase M (full factorial variable sweep) is DEFERRED** to after M' reaches
hard-pass > 80%. If the prompt fixes work, some variables may become
irrelevant. M runs only if optimization (not fundamental fix) is needed.

### M'.1 — Implement 6 prompt fixes

Based on the 7 failure modes from H1 (see `8_C3_SOCCER_KNOWLEDGE.md` §5):

| Fix | Rule | Target file |
|---|---|---|
| F1: Possession determination | "The Expert section MUST state which team has the ball. The bot closest to the ball has possession." | `rules_core_text.txt` |
| F2: Goalie confinement | "The goalie MUST stay within 1m of X=-4.0. Never command the goalie to move to X > -3.0." (refined by D1: in a 1v1 breakaway, the goalie rushes to narrow the angle) | `rules_core_text.txt` |
| F3: Field direction in Expert | "Blue attacks X=+4.5. Blue defends X=-4.5." (repeat in Expert guidance) | `rules_core_text.txt` |
| F4: KICK RULE | (already in `header_k3.txt` — confirmed load-bearing) | — |
| F5: No-hallucination | "Only reference entities listed in the world state. Do not invent bots or positions." | `header_k3.txt` or `rules_core_text.txt` |
| F6: Situation label | "The Expert section MUST begin with 'Situation: attacking / defending / transition'" | `rules_core_text.txt` |
| F7: No distance arithmetic | "Assess proximity qualitatively: close (<1m), nearby (1-2m), far (>2m). Do not compute distances or angles." | `rules_core_text.txt` |

### M'.2 — Probe fixed prompt against 15 existing scenarios (n=10)

Probe the 10 original + 5 H1 scenarios with the fixed prompt at n=10.
Compute: hard-pass %, gapC/gapP, soft score.
**Estimated time:** ~2min (15 scenarios × 10 × ~500ms)

### M'.3 — GLM-5.2 + human dual feedback

For each scenario: GLM-5.2 critiques Expert/Oracle/Output; human reviews
GLM-5.2's critique and adds their own. Compare — identify discrepancies.
**Estimated time:** ~30min (human) per round

### M'.4 — Add 10 more failure-prone scenarios

Focus on the 3 critical failure modes:
- 3× defensive (possession lost, counter-attack, defending a lead)
- 3× transition (attack→defense, defense→attack, set-piece recovery)
- 2× goalie-pressure (goalie under press, goalie distribution under press)
- 2× set-piece (kick-in, goal-kick)

GLM-5.2 authors Expert + Oracle + Output for each; human reviews.
**Estimated time:** ~1-2h (GLM + human)

### M'.5 — Re-probe against expanded 25 scenarios (n=10)

Re-probe with the expanded corpus. Check if hard-pass improved.
**Estimated time:** ~3min (25 scenarios × 10 × ~500ms)

### M'.6 — Iterate M'.1→M'.5 (2-3 rounds)

Repeat the fix → probe → feedback loop until hard-pass > 80%.
Each round: ~5min compute + ~30min human feedback.
**Estimated time:** ~15min compute total (3 rounds × 25 × 10 × 500ms)

### M'.7 — Decision gate

- **If hard-pass > 80%:** proceed to Phase 4 (Gazebo demo validation)
- **If hard-pass 50-80%:** one more iteration round
- **If hard-pass < 50%:** escalate — consider model switch (7B) or architecture change (C3 inter-lingua may not be viable at 3B)

### M'.8 — Zero-shot vs 1-sample test (folded from old sub-exp 2)

As part of the iteration, test whether the zero-shot config (0 samples, rules
only) performs as well as 1-sample. If yes, the sample can be dropped (simpler
prompt, lower latency).
**Estimated time:** ~1min (2 configs × 25 × 10 × 500ms)

### M'.9 — Prediction Part A (folded from old sub-exp 1)

Binary test: does the model produce different output with predicted positions
(t+300ms) vs current positions? If no difference, prediction is dead weight
and Part B (Phase 4 Gazebo) is skipped.
**Estimated time:** ~2min (25 scenarios × 2 × 10 × 500ms)

### Phase M' total budget

| Block | Probes | Time |
|---|---|---|
| M'.2 First probe (15 scenarios) | 150 | ~2min |
| M'.3 Feedback (round 1) | — | ~30min human |
| M'.4 Add 10 scenarios | — | ~1-2h human |
| M'.5 Re-probe (25 scenarios) | 250 | ~3min |
| M'.6 Iterate (2 more rounds) | 500 | ~10min |
| M'.8 Zero-shot test | 500 | ~1min |
| M'.9 Prediction Part A | 500 | ~2min |
| **Total compute** | **~1,900** | **~18min** |
| **Total human** | — | **~3h** |

**Notes:** **2 people recommended** for M'.3/M'.4 — the user (soccer expert)
gives feedback; GLM-5.2 (AI assistant) provides its own feedback for
comparison. The dual-feedback agreement (>95% in H1) is the evaluation metric,
not n or self-agreement.

---

## 4a. Phase M — Variable Sweep (DEFERRED)

**Status:** Deferred to after M' hard-pass > 80%. Full text preserved for
reference; will be activated only if optimization (not fundamental fix) is
needed.

**Deferred sub-experiments:**
- Sub-exp 1: world state richness (32 configs, 144k probes, ~8h 50min)
- Sub-exp 2: prompt structure (folded into M'.8)
- Sub-exp 3: runtime behavior (Gazebo, 40 runs — deferred to Phase 4)
- Cross-day replication (dropped — n=10 text probes reliable)
- Llama cross-model (deferred to Phase 4b, post-M')
- Dynamic GPU cooldown (not needed for M' — 18min of probes won't heat the GPU)

**Activation criteria:** M' hard-pass > 80% AND specific optimization question
identified (e.g. "does yaw help in TEXT mode?" — not answerable by M' alone).

---

## 5. Phase C — Code Cleanup

**Goal:** Remove dead code, extract duplications, add `start_ollama.sh`, archive dead experiments. Tight scope, ~1 session.

### C.1 Archive dead experiments
Move (not delete) to `core/src/experiments/archive/`:
- `B1`–`B7b` (11 dirs) — B-study done 2026-07-15, results in changelog
- `C2`, `C6_3sample` — C-series invalidated by format:json confound
- `cache_layout_ab.py` — one-off A/B, results in changelog
- `run_baselines.sh~` — stale backup

### C.2 Delete dead tools
- `run_baselines.sh` — redundant wrapper around `run_baseline.sh`
- `run_c_series.sh` — C-series done, format:json confound invalidated it
- `run_experiment.sh` — B-series runner, B-series done
- `swap_fragments.sh` — superseded by `i3_battery.py` variant loader
- `probe_kick_headers.py` — one-off K3 header probe
- `batch_evaluator.py` — deprecated (KPI collection broken, 2026-07-13)

### C.3 Extract duplications
- `clean_json_samples()` (~70 lines duplicated in `setup_r2k.py` and `r2k_evaluator.py`) → extract to `ai_tactics/prompt_utils.py`, import in both
- `TEXT_OUTPUT_HEADER` (hardcoded string in `r2k_evaluator.py:63-88`) → move to `strategy/fragments/header_k3.txt`, read at runtime

### C.4 Remove deprecated flags
- `--nav` from `r2k_visualizer.py` (deprecated 2026-07-29, `argparse.SUPPRESS` but still parsed)

### C.5 Add `tools/start_ollama.sh`
Standalone helper script for manual Ollama start. Default env vars (all overridable):
```
OLLAMA_HOST=0.0.0.0:11434
OLLAMA_ORIGINS=*
OLLAMA_FLASH_ATTENTION=1
OLLAMA_KV_CACHE_TYPE=q8_0
OLLAMA_MODELS=$HOME/.ollama/models
OLLAMA_KEEP_ALIVE=-1
```
Logic: command-v guard → if already running, exit 0 → `nohup ollama serve` → poll bind up to 10s → verify `0.0.0.0:11434` reachable → optional `--model` warm-up curl → optional `--check-only`.

`launch_r2k.sh` calls `tools/start_ollama.sh` instead of its inline `nohup ollama serve` (lines 188-190), centralizing env vars in one place.

### C.6 Regression testing
After all cleanup changes, run:
```
python3 -m pytest tests/ --skip-slow -v   # fast tier (~2s, ~92 tests)
python3 -m pytest tests/ -v -s             # slow tier (~21min, +11 slow tests)
```
All tests must pass before committing.

**Notes:** 1 person sufficient. Run regression tests after each sub-step (C.1–C.5), not just at the end.

---

## 6. Phase 2 — Rework analysis.md (REVISED)

**Goal:** Rework the 10+5 (H1) scenario `analysis.md` files in dictionary vocabulary (situation-triggered position verbs, no dynamic roles, every verb carries X,Y).

**Change from v6.3:** add hypothesis pre-registration before rewriting.

### 2.1 Hypothesis pre-registration
Before rewriting any `analysis.md`, state:
- H1: "Dictionary-vocabulary Oracles produce higher model compliance than current Oracles"
- Acceptance metric: VERIFY probe hard-pass ≥ 90% (current baseline: V_A 9.0/11 = 82%)
- Rejection threshold: VERIFY probe hard-pass < 82% (no improvement)

### 2.2 Rework
Rewrite Expert + Oracle sections per `c3_vocabulary_dictionary.md` and `c3_scenario_generation_playbook.md`:
- Expert FIRST (facts, geometry, reachability — NO imperatives)
- Oracle second (per-bot commands, every positional verb carries explicit X,Y)
- No dynamic role definitions (C2_striker_rule)
- Universal soccer axioms NOT repeated per-scenario (refer to `8_C3_SOCCER_KNOWLEDGE.md`)

### 2.3 Verify
Run VERIFY probes (V_A format) on all 15 scenarios. Compare to pre-registration threshold.

**Notes:** 1 person sufficient for 2.1–2.2. **2 people recommended** for 2.3 verification — one writes the Oracle, one judges the VERIFY probe output blind (IAA protocol from H1.4).

---

## 7. Phase 3 — Validate Comprehension

**Goal:** Verify the model comprehends the reworked Oracles across all referee states and edge cases.

**Method:** targeted probes from `c3_testcase_review.md` P2/P3 items:
- Referee-state probes (ball_out, goal_kick, corner_kick_in, kickoff) — does the model produce restart-aware instructions?
- Contradiction probes (ball at center, equidistant) — does the dictionary vocabulary eliminate the 73% contradiction?
- Edge-case probes (1-bot situations, phantom-bot check, OOB prevention)

**Notes:** 1 person sufficient.

---

## 8. Phase W — Watchdog & Closed-Loop Feedback (parallel to 2–3, text-only)

**Goal:** Test whether a watchdog can detect divergence between predicted and actual world state, and whether re-prompting or failsafe takeover improves outcomes.

### W.1 Synthetic divergence scenarios
6 scenarios: no-divergence, ball-divergence, bot-divergence, score-divergence, status-divergence, noise.

### W.2 Option A — re-prompt 3B on divergence
~1190ms per re-prompt. Test on 50 scenarios × 2 models (qwen2.5:3b, llama3.2:3b).

### W.3 Option B — second model (1.5B) as monitor
~400ms per check. VRAM risk (2 models loaded). Test on 50 scenarios × 2 monitor models.

### W.4 Compare
Accuracy, latency, simplicity, GPU contention. Decision report.

**Notes:** 1 person sufficient. **GPU memory is the constraint** — if Option B requires >1 model loaded simultaneously, verify VRAM headroom on the 5090 Laptop (16GB VRAM, 3B model ~2.4GB, 1.5B model ~1.2GB — should fit).

---

## 9. Phase 4 — Gazebo Validation + Prediction Part B (REVISED)

**Goal:** Validate the TEXT-mode system end-to-end in Gazebo. Gazebo is **more demo than measurement** — 3–10 runs per config, eyeball + H2 coach comments + supplementary quantitative data with caveats (directional, not statistical).

### 4.1 Smoke test (3 runs per scenario, 3 scenarios)
- `3vs3_attack_center`, `3vs3_defensive_crisis`, `3vs3_fast_counter`
- Pass criteria: blue moves, scores occasionally, no crash, no OOB > 50%
- Fail → debug, don't proceed

### 4.2 Prediction Part B — ON/OFF (from Phase M sub-exp 3)
- 4 configs (prediction on/off × goalie blending on/off) × 10 runs = 40 runs
- Watch for: does the bot intercept better with prediction ON? Does it overshoot?
- Report goal distributions, OOB %, possession % as means ± ranges (directional, not statistical)
- If a 3× effect appears (e.g. prediction ON vs OFF), note as "likely real" per n=17 power analysis; if <1.5×, note as "within noise"

### 4.3 Tuning (not factorial)
- Goalie weight: 0.5, 0.7, 0.9 (3 levels) × 5 runs = 15 runs
- Kick power: 6.0, 4.0 (2 levels) × 5 runs = 10 runs

### 4.4 Demo recording
Record 2-3 good matches with `--analyze` annotations for H2 and workshop use.

**Notes:** **2 people recommended** — one operates the launch + `match_annotate.py`, one observes and takes coach notes (this IS H2, can run in parallel).

---

## 10. Phase H2 — Human-in-the-Loop (Demo Coach)

**Goal:** Capture qualitative tactical feedback from live Gazebo matches.

**Method:** user watches 4 demo matches (the 4 configs from Phase 4.2), pauses via `match_annotate.py` (live, not replay — user preference), writes tactical comments. Annotations saved to `logs/annotations_<run_id>.jsonl`.

**Categorization (offline):**
- "Positioning error" → new rule or Oracle refinement → feeds Phase 5
- "Missing coverage" → new pattern in `8_C3_SOCCER_KNOWLEDGE.md`
- "Wrong decision" → new scenario isolating that decision → feeds next iteration
- "Good play" → positive evidence

**Estimated time:** ~1.5h (4 matches × ~15min + 30min categorization)
**Notes:** **2 people recommended** — the user (soccer expert) annotates; a second person operates the launch + manages annotations. Can overlap with Phase 4.

---

## 11. Phase 4b — Llama-3.2-3B Regression

**Goal:** Test whether the C3 findings (interwoven loses, 1 sample sufficient, K3 rules load-bearing) generalize across model families.

**Method:** re-run sub-exp 2 (8 configs, prompt structure) on Llama-3.2-3B-Instruct. n=10 (generalization screen, not full rigor).
**Requires:** `ollama pull llama3.2:3b`
**Probes:** 8 × 150 × 10 = 12,000 → ~44min.
**Decision:** if findings hold → generalizable, cite in ADR-A01. If not → Qwen-specific, note in ADR-A01 consequences.

**Notes:** 1 person + 1 machine. Also serves as edge-deployment candidate test (Jetson AGX/Orin for K1 onboard).

---

## 12. Phase 5 — Full Evaluation + Demo Walkthrough

**Goal:** Final text-probe evaluation across all scenarios + curated demo walkthrough.

### 5.1 Full text-probe suite
Run the winning config from Phase M across all 15 scenarios (10 original + 5 H1) × n=30. Produce the final KPI table: hard-pass %, soft score, self-agreement %, gapC/gapP, latency. This is the **primary evaluation result** — text-probe is the primary instrument.

### 5.2 Gazebo supplementary data
Include Gazebo results from Phase 4 as supplementary columns (goal distributions, OOB %, possession % — means ± ranges, directional not statistical). Label columns "directional, not statistical" in all output.

### 5.3 Demo walkthrough
Select 3-5 good matches from Phase 4 (with H2 annotations). Prepare demo scripts for workshop/fair use. Record video if needed.

### 5.4 Spec update
Update `optimization_spec_v6.4.md` → v6.5 with final results. Mark all phases DONE. Write session changelog.

**Notes:** **2 people recommended** for 5.3 — one operates the demo, one presents/narrates.

---

## 13. Dependency Graph

```
RB (roll-backs) — ✅ done
 ↓
A (ADRs) — ✅ done ───────────────────────────────────┐
 ↓                                                     │
H1 (human-in-the-loop: scenarios + Oracle + IAA) — ✅  │
 ↓                                                     │
C (cleanup + start_ollama.sh) — ✅ done                │
 ↓                                                     │
M' (iterative prompt-fix loop, ~18min compute + ~3h human)
 ↓ (GATE: hard-pass > 80%?)
  ├─ YES → 2 (rework analysis.md + hypothesis pre-reg) │
  │        ↓                                           │
  │        3 (validate comprehension)                   │
  │        ↓                                           │
  │        W (watchdog, text-only) ← parallel to 2-3   │
  │        ↓                                           │
  │        4 (Gazebo demo + prediction Part B)         │
  │        ↓                                           │
  │        H2 (coach comments on demos) ← overlaps 4  │
  │        ↓                                           │
  │        4b (Llama cross-model) ← parallel to H2     │
  │        ↓                                           │
  │        5 (full evaluation + demo walkthrough) ←────┘
  │
  └─ NO → one more M' round, or escalate (model switch / architecture change)

M (variable sweep, ~21h) — DEFERRED, only if M' passes AND optimization needed
```

**Critical path:** M' → 2 → 3 → 4 → H2 → 5
**Parallel:** C (with M), W (with 2-3), 4b (with H2)

---

## 14. Variable Matrix (reference)

### World model (input side)
| Variable | Levels | Sub-exp | Status |
|---|---|---|---|
| Prediction (adaptive EMA) | off / on | 1 + 3 | C9 tested JSON only; TEXT untested |
| Yaw | off / on | 1 | Removed 2026-07-31; never tested in TEXT |
| Velocity | off / on | 1 | Always on in TEXT; never ablated |
| Score in world state | off / on | 1 | Always on; never ablated |
| Status in world state | off / on | 1 | Always on; never ablated |
| Position precision | 0.1m / 0.01m | — | Deferred (low soccer value) |
| Content-hash skip | off / on | — | Deferred (infrastructure, not cognition) |

### System prompt (static context)
| Variable | Levels | Sub-exp | Status |
|---|---|---|---|
| Soccer knowledge in static context | none / current / +universal | — | K2 sweep rejected lengthening; don't re-test |
| Sample count | 0 / 1 / 6 | 2 | F4: 1 sufficient; 6 dropped; 0 (zero-shot) NEW |
| K3 rules in header | off / on | — | K3 sweep: k3h wins; don't re-test |
| Expert/Oracle in prompt | none / expert / oracle / both | — | V_A/V_B/V_C: oracle-only wins; don't re-test |
| Game-phase fragments | off / on | 2 | Always present; never ablated |
| Role labels | 0 / 3 | 2 | 5→3 condensation had no A/B test |
| Explain mode | off / on | — | F4_explain: catastrophic; keep off (debug only) |

### Bridge / executor
| Variable | Levels | Sub-exp | Status |
|---|---|---|---|
| Goalie blending | off / on | 3 | C5 tested JSON; TEXT untested |
| Goalie tactical weight | 0.5 / 0.7 / 0.9 | 4 (tuning) | D9 deferred; now in Phase 4 |
| Kick power | 4.0 / 6.0 | 4 (tuning) | Never tuned |
| Kick cooldown | 1.0 / 2.0 | — | Deferred (only if kick power shows effect) |

### Referee / red team (orthogonal to LLM eval)
| Variable | Levels | Status |
|---|---|---|
| SET_PIECE_COUNTDOWN | 5.0 / 3.0 / 7.0 | Deferred (game-balance, not cognition) |
| AGGRESSION_FACTOR | 0.15 / 0.30 | Deferred |
| Foul thresholds | various | Deferred (referee_rulebook.md is authoritative) |

---

## 15. Open Questions

| # | Question | Resolution needed by | Default if unresolved |
|---|---|---|---|
| Q1 | Axiom 5 (user-space Ollama) vs. install.sh systemd override — reconcile? | Phase A (ADR-A06) | Update axiom to "user-space OR systemd with OLLAMA_HOST=0.0.0.0" |
| Q2 | Is the adaptive prediction horizon (EMA) tracking the right latency? Should it track bridge-execution time, not LLM round-trip? | Phase M sub-exp 1 | Track LLM round-trip (current); bridge time is ~10ms, negligible |
| Q3 | Should the `R2K_PREDICT_HORIZON_S` temporary env var be removed after Phase 4? | Phase 4 completion | Remove (user decision: temporary) |
| Q4 | Is n=30 sufficient for detecting 3-way interactions in sub-exp 1 (32 configs)? | Phase M analysis | If CIs are too wide for borderline effects (yaw? score?), re-run those specific configs at n=100 |
| Q5 | Should the dictionary be versioned (v1, v2, ...) as verdicts change? | Phase M | Yes — `c3_vocabulary_dictionary.md` frontmatter `version: v6.4` after re-probe |
| Q6 | Should the `start_ollama.sh` script also handle GPU warm-up (prime the CUDA context)? | Phase C | No — the warm-up curl in `launch_r2k.sh` already handles model warm-up; GPU context is primed by `ollama serve` itself |

---

## 16. Notes — Where Multiple Humans Should Enter

| Phase | 1 person OK? | 2+ people recommended? | Why |
|---|---|---|---|
| A (ADRs) | ✅ | — | Solo writing |
| **H1.4 (IAA)** | ❌ | **✅ 2 people** | Blind scoring requires a second annotator who hasn't seen the original verdicts |
| H1.1–H1.3 | ✅ | — | Solo authoring |
| **M (sub-exp 3, Gazebo)** | ❌ | **✅ 2 people** | One operates launch + annotation, one observes (overlaps with H2) |
| M (sub-exp 1, 2, text-probe) | ✅ | — | Automated, 1 person monitors |
| C (cleanup) | ✅ | — | Solo refactoring |
| 2 (rework) | ✅ | — | Solo writing |
| **2.3 (verify)** | ❌ | **✅ 2 people** | One writes Oracle, one judges VERIFY probe blind (IAA) |
| 3 (validate) | ✅ | — | Solo probing |
| W (watchdog) | ✅ | — | Solo experimentation |
| **4 (Gazebo)** | ❌ | **✅ 2 people** | One operates, one observes + annotates (= H2) |
| **H2 (coach)** | ❌ | **✅ 2 people** | User annotates, second person operates |
| 4b (Llama) | ✅ | — | Automated |
| **5.3 (demo walkthrough)** | ❌ | **✅ 2 people** | One operates, one presents/narrates |

**Summary:** 5 phases benefit from a second person: H1.4 (IAA), M/4 (Gazebo), 2.3 (verify), H2 (coach), 5.3 (walkthrough). The second person's role is always either "blind annotator" (methodology) or "operator while expert observes" (demo).