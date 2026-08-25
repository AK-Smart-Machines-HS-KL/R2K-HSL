---
title: "C3 Vocabulary Dictionary (qwen2.5:3b) — Phase 1 Output"
type: KNOWLEDGE_BASE
tags: [c3, inter-lingua, phase-1, dictionary, controlled-vocabulary, qwen2.5-3b, probe-results]
last_modified: 2026-08-23
version: v6.7
---

# C3 Vocabulary Dictionary — qwen2.5:3b

> **Phase 1 output.** Derived from 44 live probes against `qwen2.5:3b`
> (Ollama, temperature 0.0, num_predict 600) logged in
> `core/src/results/vocab_probe_log.md`. Evidence per entry: probe series ID.
>
> **Reading the verdicts:**
> - **Known** — model produced a correct, useful definition/instruction
> - **Partial** — understanding present but with a wrong twist or missing detail
> - **No** — wrong, hallucinated, or absent
> - **Usable / Borderline / Reject** — recommendation for the inter-lingua
>
> This is the *reference* for Phase 2 (`scenario/*/analysis.md` rework) and
> Phase F (fragment/sample design). Human jargon was NOT used as a baseline —
> only what the model itself produced.

---

## 1. Verbs (actions)

| Term                                   | Known?  | In context? | Verdict           | Evidence                              | Notes / Qwen usage                                                                                                                                                                                                                  |
| -------------------------------------- | ------- | ----------- | ----------------- | ------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **move to X,Y**                        | Yes     | Yes         | **Usable**        | B3_move                               | "Blue 2, step to the position at X=1.5 and Y=2.0." Natural rephrase; exact target supported.                                                                                                                                        |
| **receive pass from X**                | Yes     | Yes         | **Usable**        | B3_receive, B1_f1/f3/f4               | "intercept or wait to receive a ball passed to it by Blue_1". Follow-up action left open — pairs well with a second verb.                                                                                                           |
| **support run to X,Y**                 | Yes     | Yes         | **Usable**        | B3_support                            | "continue running to position X=1.0, Y=1.0 for support play".                                                                                                                                                                       |
| **hold position**                      | Yes     | Yes         | **Usable**        | B3_hold, B2_f1                        | "remain stationary in its current position until further instructions". Matches our "stand" action.                                                                                                                                 |
| **mark X**                             | Yes     | Yes         | **Usable**        | B3_mark, A2_marking, D3_mark_vs_cover | "stay close to red_1, track their movements, prevent them from receiving the ball". D3 confirms the distinction: mark = stay close to a *specific player*; cover = position in a *zone* to intercept. Both understood and distinct. |
| **cover a zone / cover position**      | Yes     | Yes         | **Usable**        | D3_mark_vs_cover                      | "positioning yourself within a specific area of the field so you can block shots or intercept passes". Clean, correct — pair with explicit coordinates.                                                                             |
| **clear the ball**                     | Yes     | Yes         | **Usable**        | B3_clear, A2_clearing                 | "move it out of their own defensive area... often in a straight line forward". Aligns with TC-03 emergency clear.                                                                                                                   |
| **press the ball**                     | Yes     | Partial     | **Borderline**    | B3_press, A2_press                    | Definition correct ("contest control, never let up"), but coaching instruction added "use your hands to disrupt" — human-centered, not executable by bots. Needs a robot-safe variant.                                              |
| **cover the goal line**                | Yes     | Yes         | **Usable**        | B3_cover                              | "position itself... close to the goal line... ready to block shots or crosses". Maps to goalie blending.                                                                                                                            |
| **chase the ball**                     | Partial | Yes         | **Borderline**    | B3_chase                              | "somewhat clear but lacks detail... speed or angle". Fine as shorthand if paired with a target ("chase the ball at X,Y").                                                                                                           |
| **kick**                               | Partial | Yes         | **Usable** (rare) | A1                                    | Only appears in "corner-kick"/"free-kick" compounds in A1; did not volunteer plain "kick". Include explicitly — our bridge action name.                                                                                             |
| **pass / shoot / score**               | Yes     | Yes         | **Usable**        | A1, B1_f1/f2                          | Top-of-list verbs. B1_frame2: "pass the ball to blue_1 who is closer to the goal".                                                                                                                                                  |
| **cross**                              | Yes     | Yes         | **Usable**        | A2_wing_play, B1_f3, C2_cross_rule    | Understood as flank delivery; "setting up a cross towards the opposite goal".                                                                                                                                                       |
| **cut inside**                         | Yes     | Yes         | Borderline        | A3_striker_def, B1_f6                 | Human dribbling concept; no dribble action in bridge. Reject for inter-lingua unless used as movement paraphrase.                                                                                                                   |
| **throw-in / corner-kick / free-kick** | Yes | Yes | Reject | A1 | **No "throw-in" exists** (bots have no hands to throw). RoboCup term is **kick-in** (from the sideline). Model also said "indirect free-kick" / "direct free-kick" for restarts — wrong terminology. Restart mechanics are referee-owned, not LLM-owned (see §4). |

## 2. Nouns (entities, zones)

| Term | Known? | In context? | Verdict | Evidence | Notes |
|---|---|---|---|---|---|
| **goal / goal line** | Yes | Yes | **Usable** | A1, C1, B3_cover | Spatial anchor the model reasons with. |
| **center (of the field)** | Yes | Yes | **Usable** | C1 | "equidistant from both... neither near your own goal nor near the opponent's goal" — clean contradiction-free answer when asked directly. |
| **field / pitch** | Yes | Yes | **Usable** | A2_zone_defense, B1 | Geometry understood. |
| **wing / flank / sideline** | Yes | Yes | **Usable** | A2_wing_play, C3_ballout | "attacking moves that occur from the sides of the field". |
| **passing lane** | Yes | Yes | **Usable** | A2_passing_lane | "space or line of sight through which a teammate can pass... position yourself directly between the passer and the target". Exactly our zone-defend concept. |
| **formation** | Yes | Yes | **Usable** | A2_formation | Gave a sensible 3v3 "2-1 formation". |
| **own half / opponent half** | Partial | Partial | Borderline | C2_center_rule, D1_own_half | D1: own half "between -4.5 to 0" **correct**; opponent half "+4.5 to 9" **wrong** (treats field as 0..9 range). Use "own half" only with explicit bound ("own half = X from -4.5 to 0"), avoid "opponent half" — prefer "the red side of the center line". |
| **goal area / penalty zone** | Yes | Yes | **Usable** | A3_striker_def, C3_ballout, D5_goal_area | **Convention (2026-08-01): treat goal-area == penalty zone, for now — subject to later refinement.** Canonical term: **goal area**, coordinates (±3.5, ±1.0) in front of each goal (`referee_node.py:59-60`). D5 showed the model hallucinates off-field coords for "goal area" — always give explicit coordinates, never rely on the noun alone. |
| **striker / attacker / midfielder / defender / goalie / sweeper / playmaker / supporter** | Yes | Yes | **Usable (3 of 8)** | A3_roles | All 8 defined correctly in isolation. Only goalie/attacker/defender survive role condensation — see §3. |

## 3. Roles (the 3-role taxonomy)

| Role | Known? | Model's definition | Verdict |
|---|---|---|---|
| **goalie / goalkeeper** | Yes | "saves shots on target"; far ball → "positioning to anticipate passes/corners", close ball → "intercepting shots, ready to dive for crosses" (A3_goalie_task) | **Usable.** Matches our goalie blending (tactical positioning vs line-hold). |
| **attacker** | Yes | "helps create scoring chances and support strikers" (A3_roles) | **Usable.** Model natively uses "attacker(s)" in instructions (B1_f4, B2_f3). |
| **defender** | Yes | "primarily stops opposition players from scoring" | **Usable.** |
| striker / midfielder / sweeper / playmaker / supporter | Yes (isolated) | Correct one-liners, but see **critical finding** below | **Reject in inter-lingua.** |

### CRITICAL finding — dynamic role definitions do NOT stick (C2_striker_rule)

Probe: *"the striker is the bot closest to the ball"* + "blue_3 is closest — who is the striker?"

> "blue_3 **could be considered** the striker... **however**... typically in soccer
> strategy... a 'striker' refers to the designated player who primarily looks to
> score... blue_3 as the closest to the ball is **not necessarily** the striker."

**The model rejected the acceptance-criteria dynamic-role definition and fell
back to the static, human-soccer meaning — with wishy-washy hedging.** This is
the exact "contradictive argumentation" the inter-lingua must remove
(`c3_revisited.txt:48-53`), and it originates in the *role concept itself*,
not in the prompt wording.

**Consequence for Phase 2/3:**
- Do NOT phrase roles dynamically ("the attacker is the bot closest to the ball")
  — the model defaults to static soccer semantics and hedges.
- Prefer **situation-triggered position verbs** over role labels: "blue_2 move
  to the ball", "blue_1 hold the goal line", "blue_3 stay between ball and
  goal". The B-series shows these produce crisp instructions with no hedging.
- If roles must appear, use only the 3 condensed names as *labels of a
  previous assignment*, never as *derived concepts* ("blue_2 is the attacker
  — move to the ball").

## 4. Set-piece / referee concepts (C3-series) — WEAK, referee-owned

| Concept | Known? | Model said | Verdict |
|---|---|---|---|
| Ball out over sideline, blue last touch | Partial | "indirect free kick to the opposing team" (direction right: red restarts; mechanics wrong: our referee = kick-in, 5s freeze) | Reject (referee-owned). |
| Attacker over opponent goal line | **No** | Interpreted as a blue **goal** + indirect free kick for red (our referee = goal kick for red) | Reject. |
| Defender over own goal line | Partial | "corner kick for the opposing team" (right!) but placement "nearest point on the touchline" (wrong: corner flag ±4.3/±2.8) | Reject. |
| Kickoff after a goal | **No** | "indirect free kick from where the goal was scored" (our referee = center kickoff by conceding team, 5s freeze) | Reject. |
| Push without ball | Partial | "caution the blue player" (our referee = foul_penalty, 3s freeze, -1 reward) | Reject. |
| Kick-in placement (D2_kick_in) | Partial | Placement **correct** ("touchline at Y=3.0" — our referee warps to (±3.0, ±3.0)); terminology wrong ("direct free-kick" instead of kick-in) | Reject (referee-owned). Placement logic itself is right — passive awareness only. |
| Corner flag position (D4_corner_placement) | **No** | "corner flags at (0,-3) and (9,-3)" — hallucinated; actual field corners (±4.5, ±3.0) | Reject. Reinforces §4 decision: positions are referee-owned, never LLM. |
| Goal area position (D5_goal_area) | **No** | "own goal area X=-4.5 to -6.5" (off the field!); "opponent's X=0 to 4.5" | Reject. Use concrete coordinates, never "goal area"/"penalty area" nouns. |
| Clear near own goal (D6_clear) | Partial | Defender: "position yourself between the ball and the goalmouth" **correct**; goalie: "dive left" — human move, impossible for bots | Partial. "Between ball and goal" phrasing usable; "dive" never. |
| High line / counter-press | Yes | Correct risk/reward (A2_high_line) | Borderline — see TC-09 review (offside absent in our rules). |

**Decision:** All restart/foul mechanics are referee-owned. The LLM must
NOT produce them; the referee emits them via `match_state`. Inter-lingua
only needs passive restart-awareness ("ball out — blue restarts, take the
kick-in"), to be verified in Phase 3.

**RoboCup terminology convention (2026-08-01, integrated):**
| Restart | Correct term | Placement (referee) |
|---|---|---|
| Ball over sideline | **kick-in** (NEVER "throw-in" — bots have no hands to throw) | on the sideline at the exit point (±3.0, ±3.0) |
| Attacker over defender's goal line | **goal-kick** | nearer corner of the goal area: (±3.5, ±1.0) nearest the ball exit Y |
| Defender over own goal line | **corner kick-in** | corner flag (±4.3, ±2.8) |
| After a goal | **kickoff** | center (0,0), conceding team |

All four are referee-owned; the LLM receives only passive awareness via
`match_state.status`. Source: `referee_rulebook.md` §3.3-3.4,
`referee_node.py:59-60,481-486`.

## 5. Acceptance-criteria phrases (from `c3_revisited.txt:80-86`) — verdicts

| Phrase | Known? | Model's take | Verdict |
|---|---|---|---|
| "even formation => whoever controls the center controls the game" | Yes | Agreed, but example was corner-kick aerial-duel — not our game | **Borderline** — concept sticks, example must be rewritten |
| "striker => the bot closest to the ball" | **No** | Hedged, rejected (see §3) | **Reject** |
| "wing play => stretches the defense and creates gaps in the centre" | Yes | Correct + used correctly | **Usable** |
| "cross reception => crossing requires timing the Move targets" | Yes | "anticipate and react quickly... predict direction... adjust positions" | **Usable** |
| "zone-defend => don't chase the ball, block passing lanes" | Yes | Correct + gave a concrete zone example | **Usable** |
| "defensive shadowing => position bots between ball and own goal" | Yes | Correct (plus "one step ahead" anticipation) | **Usable** |

**5 of 6 acceptance phrases are usable as-is. Only the dynamic-striker
definition fails.** The three zone/timing phrases (wing play, cross timing,
zone-defend) are the strongest candidates for the inter-lingua core.

## 6. Contradiction baseline (C1)

Ball at center (X=0): *"It is equidistant from both the opponent's goal... and
your own goal... neither near your own goal nor near the opponent's goal."*

**Contradiction-free when the question is direct and unambiguous.** The
"near own goal but also near opponent goal" failure (73% of --explain calls,
2026-07-28 session) is a *prompt-context* problem (ambiguous framing +
few-shot pressure), not a model incapability. Phase F should test whether
removing role-derived wording eliminates it.

## 7. Latency measurement

| Metric | Value | vs spec §3 |
|---|---|---|
| Conversational probes (600 num_predict) | mean ≈ 550ms, range 196–1009ms | Spec's 761ms is the *ROS2K pipeline* figure (full fragment prompt); conversational probing is shorter-prompt. Spec §3 stays valid for pipeline. |
| Warm trivial prompt | ~110–140ms | — |

## 8. Deliverables / next steps

1. **Phase 2 impact:** Rework `analysis.md` files per `c3_testcase_review.md`
   P0/P1 items now; P2 wording changes use THIS dictionary (esp. TC-01
   dynamic-role removal, TC-09 offside removal, TC-06 shot range).
2. **Phase F:** Template sketch basis — prefer
   `[bot] [verb] [target] [qualifier]` with verbs from §1 (move/receive/
   support/hold/mark/cover/clear), NO role-derived instructions (§3).
3. **D-series borderline probes — DONE (2026-08-01, 6 probes, D1-D6):**
   - "own half" (D1): usable only with explicit bound ("X from -4.5 to 0");
     "opponent half" broken → rephrase as "the red side of the center line"
   - "kick-in" (D2): placement logic correct, terminology wrong → referee-owned
   - "mark vs cover" (D3): both understood and distinct → both usable
   - "corner placement" (D4): hallucinated → referee-owned
   - "goal area" (D5): hallucinated off-field → never use, concrete coords only
   - "clear near own goal" (D6): "between ball and goal" usable; "dive" never

---

## 9. S1 strategy-vocabulary extension (2026-08-22, ~1000 probe calls)

Probed against the full production prompt assembly (JSON mode, temp 0.0,
KV-cache controlled). Evidence: `src/results/probe_s1_report.md`. These
verdicts extend §1/§2 — cite them like B/D-series entries.

### 9.1 Term verdicts (10 terms, A1 definitions + A3 steering)

| Term | Known? | Steers? | Verdict | Notes |
|---|---|---|---|---|
| **free man** | Yes | **YES** | **Usable — the ONLY steering term** | Model computed blue_3's coordinates from "pass to the free man blue_3" (A3 pc_01: exact Kick target at teammate position) |
| **self-pass (kick and run)** | Yes | No | Usable as concept, coords required | "kicking the ball back to themselves… to create space and time" |
| **rebound** | Yes | No | Usable as concept, coords required | "position at the expected bounce point" |
| **wing** | Yes | No | Usable as concept, coords required | Matches dictionary §2 |
| **cover** | Yes | No | Usable as concept, coords required | Matches dictionary §1 |
| **through ball** | Partial | No | Concept only | Gets "break defenses", misses space-behind-line-for-runner |
| **midfield** | Partial | No | With explicit bounds only | Matched by coincidence (default center) in A3 |
| **shorten the angle** | **Partial-INVERTED** | No | **Reject** | Model describes the ATTACKER narrowing their own angle — inverted semantics |
| **last man** | **No** | No | **Reject** | Model thinks it's a stoppage/offside concept |
| **goal area** | **No** | No | **Reject — reconfirms D5** | Hallucinated geometry again ("extends from penalty box outward to sideline") |

### 9.2 The A3 rule (generalizes E/F/G coordinate rule)

**Explicit coordinates steer 100% (10/10 concepts); tactical terms steer 20%
(2/10).** Jargon is noise, coordinates are signal — now proven across the
full attacking/defensive concept set, not just the original E/F/G series.

### 9.3 Method lessons

- `...`-placeholder schemas in bare prompts → 62% literal-echo garbage;
  format anchoring REQUIRES one filled concrete example
- Persona is a real dial: aggressive header = −21pp last-man holding,
  +0.75m forward bias (A4)
- Canary KV-cache sensitivity: byte-identical prompts flip predicate-level
  canaries across sessions — same-session controls are MANDATORY (confirmed
  again in SP)

### 9.4 Consequence for scenario generation

- "free man" may be used as the lone tactical noun in Oracle text; every
  other concept MUST carry explicit X,Y (Layer 1 principle unchanged,
  now with measured coverage)
- "shorten the angle" and "last man" must be rewritten as coordinate
  prescriptions (e.g. P-D6's ball→near-post axis phrasing)
