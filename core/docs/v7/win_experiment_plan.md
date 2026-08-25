# WIN Experiment Plan — "Make Blue Win in Gazebo Live Matches" (8h budget)

> **Status:** EXECUTED 2026-08-22/23 — **NEGATIVE, CLOSED EARLY by pre-registered
> kill criteria.** All six round-1 arms killed (report:
> `src/results/probe_win_report.md`). No Phase 2/3/4 (zero round-1 winners).
> B13 stays applied. Phase 4 harness `tools/win_live_eval.sh` built but unused.
> **Original design below, kept for the record.**
> **Budget:** ~7.5h of 8h · **Model:** qwen2.5:3b (stays) · **Bridge/CPU: NO
> changes (user decision)** · **No commits.**
> **Baseline:** B13 samples (currently applied to `samples_3vs3.txt`;
> V1 backup at `samples_3vs3_v1_backup.txt`, sha1 ff9359a…).

## Pre-registered success criterion

**Win rate ≥35% over 21 matches** (7 scenarios × 3: attack_center, attack_wing,
wing_switch, def_transition, default, high_line, defensive_crisis — the FULL
set including blue's worst). Challenger must also outscore B13 fresh baseline
in aggregate goals. Draw-reduction alone = partial success, documented as such.

## Phases

| Phase | Time | Content |
|---|---|---|
| 0 — Pre-register | 30m | Freeze criteria + arm specs; verify `tools/s1_live_eval.sh` harness (adapt: 7 scenarios × 3 reps, 120s each, both arms incl. fresh B13 baseline — existing B13 data used a different scenario mix, NOT comparable) |
| 1 — Round 1: single levers | ~2h | W1-W6 below; each arm: build + lint (`s1_variants.lint_samples`) + sequence probe (`probe_s1.py sp` phase: flap rate, freeze drift, goalie-Y cycle) + full canary suite (`probe_s1.py b`). Kill criteria: ff_gk >20%, last_man <90%, parse <98% |
| 2 — Round 2: adaptive combos | ~1h | 2-3 combos ONLY from round-1 winners (e.g. W1+W4), each fully re-probed (S1 finding 3: no free combos) |
| 3 — Finalist confirmation | 30m | Top-1 arm at 5 reps (beats KV-cache canary flip-noise, SP finding 6) |
| 4 — Live decider | 2.5h | Challenger + FRESH B13 baseline, 21 matches each, background (`nohup`), same 7-set |
| 5 — Report | 30m | `src/results/probe_win_report.md` + changelog + power-file update |

## Round-1 arms (6 single levers)

| Arm | Lever | Evidence hook | Build notes |
|---|---|---|---|
| W1 | Kicker-anchor samples: concentrate ALL field kicks (with-target AND plain) on blue_2, keep B13 goalie anchors (2× blue_1 Kick) | V0 scored 0.73 B/match with blue_2-anchored kicking; SP: kicker flapping 8-15%/step, 0.47m target jumps | Rework B13 samples: new2b/new3b kickers → blue_2 if not already; ex6 (blue_3 plain kick) → rewrite with blue_2 kicker? CAREFUL: linter requires all 3 bots kick somewhere; if only 2 kickers, note lint exception or rotate ONE plain kick to blue_3. Kicker-dose: blue_2 ≈5, blue_1 2 (goalie), blue_3 ≤1 |
| W2 | Goalie-Y quantization rule in rules_3vs3: "The goalie's Move target Y equals the ball's Y multiplied by 0.5, rounded to one decimal place. The goalie never uses any other Y." | SP: goalie Y limit cycle ±0.1-0.5m alternation every call (THE dominant spinning noise); never tested quantization | Rule-append only; samples untouched. Sequence probe freeze test is the decisive metric (goalie Y must become constant) |
| W3 | Shoot-on-sight rule, GATED: "When the ball is in the opponent half (X>0), the closest blue bot kicks toward the opponent goal immediately — do not reposition first." | A4 persona = +0.75m forward dial; V1's goals partly from aggression; B3 risk: ungated space-kick rule inverted kickers — the X>0 gate is the fix | Rule-append; canary-gate: if ff_gk or pass canary breaks, kill |
| W4 | Latency diet: 6 examples (drop rebound new3b + one goalie anchor ex2 → 2 goalie anchors, 4 field examples incl. wing? NO: drop new3b and ex5-defending, keep ex1/ex2/ex6/ex7/new1/new2b) | B13 2842 tok / 658ms p50; ~2300 tok → ~600ms → ~15% less ball drift per LLM call (attacks the 672ms moving-target problem prompt-side) | Verify goalie-anchor ratio stays ≥2:4 (B9 lesson: 2:2 = canary death; B13 has 2:5 → dropping ex5 keeps 2:4) |
| W5 | Wing-attack sample: NEW example where the pass/kick target is on the wing (|Y|≥1.5) in the opponent half, carrier kicks wide-forward, runner attacks the wing space | wing_stretch 0-17% in ALL arms; blue's best scenarios are attack_wing (0.9:0.5) + wing_switch — converting draws there is the highest win-ROI; ALSO make W5 the 9th sample in the W4-arm? NO — W5 replaces ex5 (defending) to hold n=8 | New example body: ball center, blue_2 carrier, blue_3 wing target (3.5, -2.0), reds center-crowded; kicker=blue_2 with target (keeps with-target on blue_2); lint must pass |
| W6 | Aggressive persona header + B13 samples unchanged | A4 measured +0.75m forward bias / -21pp last_man. UNTESTED for goals — the -21pp last_man cost may be acceptable when chasing wins | Header line 1 → "You are a highly aggressive, offensive soccer AI…" stays (it IS the current header!). So W6 = "maximal aggression" variant: additionally append a FINISHING rule ("prefer kicking over passing when the goal is within reach") — distinct from W3 (immediacy) |

NOTE on W3/W6 overlap: W3 = when to kick (immediately, opp half); W6 = kick vs pass preference. Keep both in round 1; they answer different questions. If both win, combo W3+W6 = "finishing package".

## Canary requirements (every arm, same session)

ff_gk ≤20% · goalie canary ≥67% · last_man ≥90% · pass canary ≥25% (B13 level) ·
parse ≥98% · self_pass ≥67% (B13 level). Sequence probe: flap ≤8%, freeze
drift ≤0.05m (SP0 level), goalie-Y cycle amplitude <0.1m (W2 only: ≈0).

## Honest expectation (on record)

Prompt-channel ceiling: draw-reduction + more goals. 35% wins is ambitious
(V0 hit 26% with broken-but-aggressive goalie). If short → deliverable =
definitive prompt-channel closure + strongest variant + TeamCaptain
requirements doc (SP findings + this run's).

## Key tooling facts for the next session

- `tools/probe_s1.py` — phases: a1/a2/a3/a4/b/lint/**sp** (sequence probe).
  b-phase now merges `sp_variants.get_sp_variants()` into the variant pool;
  same pattern for win_variants (add `{**V.get_variants(), **SP.get_sp_variants(), **WIN.get_win_variants()}`).
- `tools/sp_variants.py` — SP arm builder pattern to copy for W arms
- `tools/s1_variants.py` — `lint_samples()`, `compose_samples()`, EX_BODIES
  (ex1,ex2,ex5,ex6,ex7,new1,new2b,new3b = B13 set as SAMPLES_B13_KEYS — NOTE:
  B13 keys live in sp-variants? NO: B13 = ["ex1","ex2","ex5","ex6","ex7","new1","new2b","new3b"], defined in s1_variants.SAMPLES_B13_KEYS)
- `tools/s1_live_eval.sh` + `src/tools/s1_record_writer.py` — debugged live
  harness; adapt MATCHES array to 7 scenarios × 3 (21 matches/arm) and the
  fragment-swap source (staging file per challenger)
- `tools/benchmark.sh` — alternative generic harness (10 fixed scenarios)
- KV-cache control: distractor call + first-call discard per arm; same-session
  comparisons ONLY (SP finding 6: byte-identical prompt flipped goalie canary
  100%→0% across sessions)
- Production samples = B13 on disk; probe arms assemble INLINE from
  `get_*_variants()` — never edit production files for arms
- GPU: Ollama on 127.0.0.1:11434, qwen2.5:3b warm; Gazebo via
  `./launch_r2k.sh --headless --duration 120 --scenario X --relay only_sim_bots`
- 502 fast tests pass pre-experiment (rerun after any file change)

## Phase 0 — Pre-registration (FROZEN 2026-08-22, pre-execution)

**Environment verified at freeze time:**
- GPU boosts correctly under load (P0 / 1837 MHz / 214 tok/s sustained, 200-token
  probe) — no U24-style clock freeze. Ollama up at 127.0.0.1:11434, qwen2.5:3b warm.
- `samples_3vs3.txt` = B13 (sha1 `44795270bf98832aff114d2a38371c8a2726e494`), verified
  byte-identical to `compose_samples(SAMPLES_B13_KEYS)` — arms can be assembled from
  `s1_variants` keys with confidence. V1 backup intact (sha1 `ff9359a…`).
- All 7 decider scenarios exist as packages. 502 fast tests passed pre-experiment.

**Frozen arm specs (round 1):**
- **W1** kicker-anchor: sample keys `[ex1, ex2, ex5, ex6, ex7, new1, new2b, new3]`
  (B13 with new3b→new3: rebound kicker back to blue_2). Kicker dose: blue_1=2 (goalie),
  blue_2=5, blue_3=1 (ex6 only, keeps linter's all-bots-kick rule).
- **W2** goalie-Y quantization rule appended to rules_3vs3 (samples = B13):
  "GOALIE Y: The goalie's Move target Y equals the ball's Y multiplied by 0.5, rounded
  to one decimal place. The goalie never uses any other Y value."
- **W3** gated shoot-on-sight rule appended (samples = B13):
  "SHOOT ON SIGHT: When the ball is in the opponent half (X from 0 to 4.5), the blue
  bot closest to the ball kicks toward the opponent goal (X=4.5) immediately. Do not
  reposition first."
- **W4** latency diet: sample keys `[ex1, ex2, ex6, ex7, new1, new2b]` (6 examples;
  drops new3b rebound + ex5 defending; goalie-anchor ratio stays 2:4).
- **W5** wing-attack sample: keys `[ex1, ex2, wing1, ex6, ex7, new1, new2b, new3b]`
  (wing1 replaces ex5, n=8). wing1 = ball center-ish, blue_2 carrier kicks with
  target on the wing in opponent half, blue_3 runs the wing space, reds center-crowded.
- **W6** finishing rule appended (samples = B13, header unchanged — already aggressive):
  "FINISHING: When the ball is inside the opponent goal area (X from 3.5 to 4.5, Y
  from -1.0 to 1.0), the blue bot with the ball kicks at the opponent goal immediately
  instead of passing."

**Lint outcome (post-build, pre-probe):** W4 clean. Two accepted exceptions:
W1 kicker imbalance blue_2 5/8 (the deliberate lever); W5 role stereotype
blue_3 attacker 6/8 (consequence of wing-runner design; ex5 replacement is
pre-registered, defending stays covered by new1, last_man kill criterion
guards the risk). All other checks pass on all arms.

**Frozen evaluation protocol (round 1):** every arm, same probe session, in this order:
lint (`s1_variants.lint_samples`) → canary suite (`probe_s1.py b --reps 3`, control =
B13, 28 situations incl. canaries) → sequence probe (`probe_s1.py sp --reps 1`, control
= SP0, 10 situations × 5 steps × drift+freeze). Kill criteria: ff_gk >20%, last_man
<90%, parse <98%. Canary floor: goalie canary ≥67%, pass canary ≥25%, self_pass ≥67%.
Sequence floor: flap ≤8%, freeze drift ≤0.05m (SP0 level); W2 additionally: goalie-Y
cycle amplitude ≈0 in freeze test.

**Frozen live-decider protocol (Phase 4):** `tools/win_live_eval.sh <tag> <staging>` —
21 matches/arm (7 scenarios × 3 × 120s, round-robin order), arm-blocked: fresh B13
baseline first (current disk state), then challenger swap. Trap + normal end restore
B13. Win rate ≥35% for challenger AND aggregate goal advantage vs fresh B13 = success.

## Post-run state commitments

- No commits (per user instruction)
- `samples_3vs3.txt`: revert to B13 unless challenger WINS the live decider
- All raw data → `src/results/` (probe_win_*, live eval jsons)
- Changelog entry `2026-08-23 — WIN experiment`
