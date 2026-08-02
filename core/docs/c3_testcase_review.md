---
title: "C3 Test Case Review (TC-01..09 + 2vs2) — Recommended Adjustments"
type: AUX_DELIVERABLE
tags: [c3, inter-lingua, phase-1, aux-deliverable, testcase-review, analysis-md, role-condensation, scenario]
last_modified: 2026-08-01
version: v6.3
---

# C3 Test Case Review — Recommended Adjustments

> **Aux deliverable to Phase 1 (vocabulary probing).** Reviewed all test-case
> description files (`core/src/scenario/*/analysis.md`) against the current
> architecture. This list feeds Phase 2 (rework descriptions) but can be
> acted on partially already — the flagged *stale references* (roles, KPIs,
> offside) are architecture facts, not vocabulary decisions, so they are
> valid regardless of the Phase 1 probe results.
>
> **UPDATE (2026-08-01, after Phase 1 probing):** The vocabulary dictionary
> (`c3_vocabulary_dictionary.md`) is now available. The single most important
> finding affects every file: **dynamic role definitions do not stick** — the
> 3B model rejects "the striker is the bot closest to the ball" and falls
> back to static soccer semantics with hedging. Phase 2 must prefer
> situation-triggered position verbs (`[bot] move to the ball`, `hold the
> goal line`, `stay between ball and goal`) over derived role labels. The
> P0/P1 fixes below remain valid; the P2 wording rework is now dictionary-
> grounded.
>
> Scope: TC-01..TC-09 (3vs3) + `2vs2_default`. TC-10 (`3vs3_kick_in`) is
> deferred to Phase 5 per `scenario/README.md:33`.
>
> **APPLIED (2026-08-01):** P0/P1 fixes below are now applied to the
> `analysis.md` files (text-only fixes: TC-05 oracle rewritten to
> "deepest blue bot", 2vs2 rewritten to "one bot falls back to goalie
> position", TC-09 offside/role removed, TC-08/2vs2 role_diversity
> references removed, stale roles replaced, TC-01 X=-4.2, TC-06 shot
> range X>2.0/|Y|<1.0). `2vs2_default/scenario.json` migrated to v6
> schema. Remaining: P2 (full dictionary rework, Phase 2) and P3 (TC
> IDs in headers).

---

## 1. Summary table

| TC | Package | Position/ball OK? | Stale roles? | Other findings | Severity |
|----|---------|-------------------|--------------|----------------|----------|
| TC-01 | `3vs3_attack_center` | yes | **striker, supporter** | goalie X -4.0 vs actual -4.2 | medium |
| TC-02 | `3vs3_attack_wing` | yes | no | — | low |
| TC-03 | `3vs3_defensive_crisis` | yes | no | kick-direction assumption | low |
| TC-04 | `3vs3_fast_counter` | yes | **striker, supporter** | — | medium |
| TC-05 | `3vs3_pressing_trap` | **no** | no | "play back to goalie" impossible (no bot in own half) | high |
| TC-06 | `3vs3_long_shot` | yes | **supporter** | X>0.5 vs ball already at 3.15; shot range Y<1.5 vs goal ±0.9 | medium |
| TC-07 | `3vs3_contain_delay` | yes | no | already uses acceptance-criteria wording | low |
| TC-08 | `3vs3_def_transition` | yes | no | **stale KPI: role_diversity dropped** | high |
| TC-09 | `3vs3_high_line` | **no** | no | **offside rule does not exist**; goalie identity ambiguous | high |
| 2vs2 | `2vs2_default` | **no** | **striker** | goalie at X=-4.0 but no bot starts there | high |

---

## 2. Cross-cutting adjustments (apply to ALL test cases)

1. **Replace stale role names.** Role condensation (2026-07-28) reduced the
   taxonomy from 5 roles to **goalie / attacker / defender**. The bridge only
   checks `role == 'goalie'`; `striker`, `supporter`, `midfielder`, `passer`,
   `receiver` are dead vocabulary. Every occurrence in `analysis.md` must be
   rewritten:
   - "striker" → "attacker" (the bot closest to the ball)
   - "supporter" → "defender" or "attacker", depending on position
   - Why: the LLM only ever receives the 3-role set in fragments; the
     analysis descriptions must not train the evaluator against a vocabulary
     that the prompt itself forbids (pattern copier — it will echo stale
     role names).

2. **Separate universal soccer knowledge from situation-specific text.**
   `c3_revisited.txt:72-73` mandates: explanatory statements belong in a new
   module "soccer universal knowledge", NOT in test-case descriptions.
   Phrases like "whoever controls the center controls the game" (TC-01) or
   "wing play stretches the defense" (TC-02) are universal knowledge — they
   must move out of `analysis.md` into the knowledge module, leaving
   situation-specific instructions only.
   - Why: `analysis.md` is the *oracle/expert reference per situation*.
     Universal axioms repeated in every file create contradiction potential
     (the exact "wishy-washy" output the inter-lingua must remove).

3. **Add TC IDs to headers.** Files are referenced as TC-01..TC-11 in specs
   but carry no ID in the file itself.
   - Why: traceability — `kpi_targets.json`, `test_non_functional.py`, and
     the Phase 2/3 validation matrix all reference TC numbers.

4. **Align hardcoded positions with `scenario.json`.** Any X/Y mentioned in
   text (goalie X=-4.0, shooting range X>0.5) must match actual entity
   positions.
   - Why: the LLM receives real positions; descriptions that contradict the
     field state teach it wrong spatial priors.

5. **Remove references to dropped KPIs.** `role_diversity` was removed
   (2026-07-28, CV=0% dead metric). `avg_response_tokens` removed. KPI
   count is now 18.
   - Why: descriptions must reference the KPIs we actually assert
     (`composite`, `shots_on_goal`, `pass_completion_pct`,
     `restart_recovery_time_s`, `goalie_tactical_pct`, OOB, cluster).

6. **Referee rules come from ROS2K code, not RoboCup standards.**
   `c3_revisited.txt:76-77` + handover §Phase 2. No offside exists in
   `referee_node.py`. No "fancy passes" penalty, no offside trap.
   - Why: translating a rule the referee does not implement teaches the
     3B model behavior that will never be rewarded.

---

## 3. Per-test-case comments

### TC-01 — `3vs3_attack_center` (medium)

**Current text** (`analysis.md:5-9`): central gap exploit; "assign goalie to
blue_1 at X=-4.0, striker to the bot closest to the ball, supporter to the
third".

**Recommendations:**
- R1: "striker" → "attacker", "supporter" → "defender".
- R2: goalie X=-4.0 → -4.2 (actual `scenario.json:7` position of blue_1).
- R3: Move "whoever controls the center controls the game" to universal
  knowledge module; keep only "push blue_2/blue_3 through midfield while
  blue_1 holds the line".

**Why:** stale roles contradict the 3-role prompt; position mismatch
confuses spatial grounding; universal phrase belongs elsewhere.

---

### TC-02 — `3vs3_attack_wing` (low)

**Current text** (`analysis.md:5-9`): wing space, cross from side, "wing play
stretches the red defense", STAY INSIDE warning.

**Recommendations:**
- R1: Move "wing play stretches the defense and creates gaps in the centre"
  to universal knowledge.
- R2: Keep the OOB warning — this is the only scenario where ball Y=2.0 and
  the wing bot must not cross Y=±3.0.

**Why:** otherwise already consistent with roles and positions (ball at
3.0/2.0, red goalie at 4.2/-0.5 — cross reception feasible).

---

### TC-03 — `3vs3_defensive_crisis` (low)

**Current text** (`analysis.md:5-9`): emergency clear, "kick the ball away
from own goal, toward the sidelines or upfield", closest bot kicks.

**Recommendations:**
- R1: Note the bridge limitation: non-goalie kicks aim at the opponent goal
  (role-aware kick, 2026-07-27). A "clear toward the sideline" is not
  directly executable — text should say "Kick upfield" and accept that the
  ball travels toward +X.
- R2: Specify the goalie action explicitly (hold goal line, Y tracks ball)
  so the description matches `goalie_tactical_pct` assertion.

**Why:** description promises an action the execution layer cannot produce;
goalie behavior is the single most-asserted KPI and must not be left open.

---

### TC-04 — `3vs3_fast_counter` (medium)

**Current text** (`analysis.md:5-9`): push forward fast, "Striker should go
for goal directly. Supporter trails at midfield".

**Recommendations:**
- R1: "Striker" → "attacker (closest bot to the ball)", "Supporter" →
  "defender".
- R2: Keep "minimize role switches, keep assignments stable" — good, ties
  to latency KPI.

**Why:** stale roles only; the tactical content is sound and matches the
counter scenario (ball at -1.8, red recovery far).

---

### TC-05 — `3vs3_pressing_trap` (HIGH)

**Current text** (`analysis.md:5-9`): maintain spacing, "If trapped on the
sideline, play back to the goalie".

**Position check (`scenario.json`):** blue_1 (0.3/0.3), blue_2 (-1.0/0.8),
blue_3 (-2.0/-0.5). **No blue bot is near the own goal (X=-4.5).** There is
no goalie on the field at kickoff.

**Recommendations:**
- R1: Fix the scenario: move blue_3 to the goalie position (X≈-4.0..-4.3,
  Y=0.0) — OR rewrite the oracle to not reference the goalie ("play back
  to blue_2", "hold the ball and wait for a lane").
- R2: If the goalie is added, the description must name it ("blue_3 is the
  goalie, stays on the line").

**Why:** the oracle references a bot that does not exist in the setup.
The 3B model will look for the goalie, find none, and either cluster or
freeze — both are the exact failure modes this scenario is meant to test.

---

### TC-06 — `3vs3_long_shot` (medium)

**Current text** (`analysis.md:5-9`): "assign Kick when the ball is in
shooting range (X > 0.5, |Y| < 1.5)"; "Supporter should follow up for
rebounds".

**Position check:** ball starts at 3.15/1.35 — already in range. The
`X > 0.5` condition is trivially true at kickoff.

**Recommendations:**
- R1: "Supporter" → "defender".
- R2: Shooting range: align with actual goal geometry — goal mouth is
  ±0.9 m (`referee_rulebook.md:99`); suggest "|Y| < 1.0 at kick time,
  ball X > 2.0" so the condition is discriminating.
- R3: Add "follow up for the rebound" to the *attacker*, not a separate
  supporter role (no third attacking bot available — blue_3 is goalie).

**Why:** stale role + threshold that cannot discriminate at this scenario's
starting state.

---

### TC-07 — `3vs3_contain_delay` (low)

**Current text** (`analysis.md:5-9`): zone-defend, block passing lanes,
defensive shadowing, "position bots between ball and own goal".

**Recommendations:**
- R1: None structural — this file already uses two acceptance-criteria
  phrases verbatim ("don't chase the ball, block passing lanes";
  "position bots between ball and own goal").
- R2: After Phase 1, verify these phrases actually trigger patterns in
  qwen2.5:3b before Phase 2 (they are the templates the whole inter-lingua
  will be built on).

**Why:** this is the reference-quality file; keep it stable.

---

### TC-08 — `3vs3_def_transition` (HIGH)

**Current text** (`analysis.md:5-9`): fall back, re-form defensive line,
"Expect role diversity to spike (rapid switching)".

**Recommendations:**
- R1: **Delete the role_diversity reference** — the KPI was dropped
  (CV=0%, 2026-07-28). Replace with the KPI that actually exists:
  "expect `restart_recovery_time_s` and `shots_on_goal` pressure from
  counter-press".
- R2: "closest bot presses the ball, others fall back" — keep, it maps to
  the attacker/defender role split.

**Why:** referencing a dead KPI in the reference doc will mislead Phase 3
validation scoring.

---

### TC-09 — `3vs3_high_line` (HIGH)

**Current text** (`analysis.md:5-9`): "pressing red offside", "the goalie
sweeps behind the line".

**Position check (`scenario.json`):** blue_1 (-3.0/1.5), blue_2 (-3.0/0.0),
blue_3 (-3.0/-1.5) — all three on the line, none in goal. Ball at
-2.7/2.25, red_2 already at -1.0/2.5 (behind the line).

**Recommendations:**
- R1: **Remove "offside"** — `referee_node.py` implements no offside rule.
  Replace with the actual risk: "red_2 is behind the line already — if the
  ball is passed through, no offside call will stop it".
- R2: Name the sweeper: blue_1 (or whichever bot the referee treats as
  goalie) stays at goal-line height while blue_2/blue_3 hold the line.
  Currently the text says "goalie sweeps" but no bot is identified and none
  starts in goal.
- R3: Note the contradiction with the goalie blending (2026-07-27): the
  bridge pulls the goalie toward the goal line when the ball is near.
  A "sweeper goalie at X=-3.0" is not enforceable for the role goalie —
  the description must either position the goalie normally and have a
  *defender* sweep, or accept that the goalie will not hold the line.

**Why:** three issues in one file — non-existent rule (offside), undefined
goalie identity, and an instruction (sweeper) that the execution layer
actively overrides. This scenario had the worst baseline composite (0.26)
and OOB 26.2%; the description must stop adding load.

---

### 2vs2 — `2vs2_default` (HIGH)

**Current text** (`analysis.md:5-9`): "assign one goalie (X=-4.0) and one
striker".

**Position check (`scenario.json`):** blue_1 (-2.0/1.0), blue_2 (-2.0/-1.0).
Neither bot starts at the goalie position.

**Recommendations:**
- R1: "striker" → "attacker".
- R2: Either move blue_1 to (X≈-4.0, Y=0.0) in `scenario.json`, or change
  the text to "one bot falls back to goalie position after kickoff".
- R3: Drop "expect high role diversity" — dead KPI reference (same as
  TC-08).

**Why:** the goalie instruction cannot be executed from the starting
positions; the described role-switch KPI no longer exists. Note: this
file is the only package whose `scenario.json` still uses the v5 schema
(`scene_type`/`label`) — flag for migration to v6 schema in Phase 2d+.

---

## 4. Adjustment priority

| Priority | Items |
|----------|-------|
| **P0 (fix now, no probing needed)** | TC-05 goalie gap; TC-09 offside + goalie identity; TC-08 role_diversity; 2vs2 role_diversity + goalie position |
| **P1 (fix now, wording)** | All stale roles (TC-01, TC-04, TC-06, 2vs2); TC-01 X=-4.2; TC-03 kick-direction note; TC-06 shot range |
| **P2 (dictionary-grounded, before Phase 2)** | **Remove dynamic role definitions** everywhere ("striker = closest to ball" was REJECTED by qwen2.5:3b in probing — C2_striker_rule); replace with position verbs (move to ball / hold goal line / stay between ball and goal). Verify TC-07 phrases (zone-defend, shadowing — both USABLE per dictionary §5); rephrase everything in Qwen's own vocabulary |
| **P3 (Phase 2/3)** | TC IDs in headers; full rework of all 10 files per dictionary; TC-10 kick_in creation |

---

## 5. Open questions

1. **2vs2_default schema migration** — v5 → v6 (`scenario_name`/`mode`)?
   Affects `setup_r2k.py` mode derivation and `batch_evaluator` run IDs.
2. **TC-05 redesign** — add a goalie to the setup (changes the test's
   tactical character) or keep the no-goalie press (tests a different
   failure mode)? The KPI targets and oracle must match whichever is
   chosen.
3. **"Sweeper goalie" feasibility** — accept the goalie-blending override
   and rephrase TC-09, or extend the bridge with a sweeper mode (out of
   C3 scope)?
