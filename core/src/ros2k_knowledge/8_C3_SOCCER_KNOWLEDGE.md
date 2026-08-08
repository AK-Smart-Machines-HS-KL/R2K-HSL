---
id: 8_C3_SOCCER_KNOWLEDGE
title: "Section 8: Universal Soccer Knowledge (C3 Layer 1)"
type: KNOWLEDGE_BASE_POWER_FILE
tags: [c3, inter-lingua, soccer-knowledge, universal-knowledge, expert-oracle, scenario-generation, coaching-heuristics, position-verbs, v6.3, c3-layer1, qwen2.5]
last_modified: 2026-08-05
version: v6.4
---
# Section 8: Universal Soccer Knowledge (C3 Layer 1)

> [!abstract] LLM Context Anchor
> **CRITICAL AXIOMS FOR RAG RETRIEVAL:**
> 1. **Purpose:** This power-file distills *human soccer coaching knowledge* into a reusable knowledge base for a LARGE generating LLM that writes new scenario packages (Expert + Oracle). It is Layer 1 of the C3 knowledge stack (see `7_C3_INTER_LINGUA.md`).
> 2. **Boundary:** Layer 1 = model-agnostic soccer truths. The generating LLM combines these with **Layer 2 (ROS2K physics/referee facts)** and **Layer 3 (qwen2.5:3b inter-lingua mapping)** to produce executable `analysis.md` files. Never write per-scenario text using Layer 1 alone — universal axioms repeated in every file create contradiction (see §1.6).
> 3. **Evidence base:** Every entry is distilled from the 2026-08-01 walkthrough dialogue (TC-01..TC-06) and is probe-verified against `qwen2.5:3b` (E/F/G series). The session worked examples are INTEGRATED into the entries — this file is the canonical home of that knowledge, not a separate changelog.
> 4. **Authoritative detail:** `c3_scenario_generation_playbook.md` §5 (patterns P1-P10 with per-TC expression), `c3_vocabulary_dictionary.md` (model vocabulary), `c3_testcase_review.md` (P0/P1/P2 table). This file is the retrieval anchor; those hold the full evidence.

## 1. Layer 1 — General Soccer Knowledge (universal, model-agnostic)

This is the knowledge a human coach applies when reading a world state and
prescribing actions. It is written for a generating LLM — NOT for qwen2.5:3b
directly (Layer 3 provides the mapping). Structure per entry:
**Principle** → **Check** (what to look for in the world state) →
**Express (Expert)** / **Express (Oracle)** → **Source** (session TC + probe).

### 1.1 Control & Positioning

#### P-C1 — Whoever controls the center controls the game
- **Check:** Which team has more bots near the center circle / central lanes at kickoff?
- **Express (Expert):** "Blue holds 2 bots near the center line while red has only 1 — blue controls the central space."
- **Express (Oracle):** keep a central bot on the center line as the pivot, others rotate around it.
- **Source:** universal axiom (was in TC-01 pre-fix, moved here by testcase review §2.2).

#### P-C2 — Spacing: don't cluster
- **Check:** distances between own bots; two bots within ~1m of each other and the ball.
- **Express (Expert):** "blue_2 and blue_3 are 0.8 m apart — they duplicate each other's coverage."
- **Express (Oracle):** "blue_2 moves to (X, Y), blue_3 moves to (X', Y') to open spacing."
- **Source:** anti-clustering samples (2026-07-14 3vs3 rewrite), B-study cluster% findings.

#### P-C2a — Competition split (two bots on the ball)
- **Check:** two teammates within 0.5m of the ball → exactly ONE commits, the other exits.
- **Express (Oracle):** "blue_1 kick; blue_2 moves to (X, Y) at least 1.5m from the ball, toward open space."
- **Source:** K3 battery (competition_ball situation, 2026-08-02). **K3 finding:** split requires an explicit RULE (rule form 2/3 vs example form 0/3); the model's default is double-chase standoff. Wire-in: SPLIT RULE in `TEXT_OUTPUT_HEADER` (`r2k_evaluator.py:63-88`), full-battery gapC 30.8% → 60.3%.

#### P-A3b — Pass to the free man (receiver moves forward)
- **Check:** ball in the opponent half (X>0), a teammate unmarked closer to the opponent goal (X=4.5) than the ball → kick forward + receiver moves forward of the ball.
- **Express (Oracle):** "blue_1 kick; blue_2 moves to (4.0, Y) — closer to X=4.5 than the ball."
- **Source:** K3 battery (free_man_pass situation, 2026-08-02). **K3 finding:** the rule alone fixes the kicker but the receiver never runs forward; the PASS EXAMPLE is what makes the receiver move. Rule MUST be gated to the opponent half — ungated it fires in defensive situations and pushes bots forward wrongly. Wire-in: PASS RULE + PASS EXAMPLE in `TEXT_OUTPUT_HEADER`, full-battery gapP 3.8% → 70.5%.

#### P-C3 — Angle to goal beats goalie position
- **Check:** is there a straight lane from ball-carrier to the goal mouth (|Y|≤0.9 at X=4.5)? The goalie position is secondary — the goal mouth is the target.
- **Express (Expert):** "The shooting angle toward the goal mouth is too narrow — blue_1 cannot shoot directly; the ball sits between blue_1 and the goal."
- **Express (Oracle):** "blue_1 moves around the ball to (X, Y) to open a shooting angle toward the goal."
- **Bracketed goal mouth (TC-06):** when the goalie covers the short post AND a second defender covers the long post, the direct shot disappears — the mouth is bracketed, no unguarded corner exists. Check ALL defenders in the goal-mouth cone, not only the goalie. Oracle becomes possess + open a pass lane, not shoot. Expert: "red_1 (4.2, 0.5) guards the short post (goal mouth at Y≈+0.9); red_3 (3.5, -0.5) covers the long post (goal mouth at Y≈-0.9) — no unguarded corner exists."
- **Source:** TC-02 attack_wing, TC-06 long_shot (angle to goal mouth ±0.9, not goalie; bracketed-mouth variant 2026-08-01 TC-06 walkthrough).

#### P-C4 — Defense = between ball and own goal
- **Check:** is each defending bot positioned between an opponent and the own goal?
- **Express (Expert):** "blue_3 is not between the ball and the goal — red_2 has a direct lane."
- **Express (Oracle):** "blue_3 moves to (X, Y), between the ball and the goal mouth."
- **Source:** acceptance phrase "defensive shadowing" (usable, dictionary §5), D6 "between ball and goal" (usable, "dive" rejected).

### 1.2 Attacking Principles

#### P-A1 — Free time = deliberate action
- **Check:** distance from ball-carrier to the nearest opponent. Large distance → maneuver room.
- **Express (Expert):** "Distance from blue_1 to red_1 is large enough that blue_1 has free time to maneuver — red_1 cannot reach the ball quickly."
- **Express (Oracle):** use the free time — take a deliberate action instead of rushing.
- **Source:** TC-04 fast_counter (pattern P1).

#### P-A2 — Out of reach = ignorable
- **Check:** opponents far upfield/side that cannot influence the ball within a few seconds.
- **Express (Expert):** "red_2 and red_3 stand far upfield and can be ignored — they are out of reach."
- **Express (Oracle):** ignore them; commit only the needed number of bots.
- **Source:** TC-04 fast_counter, TC-02 attack_wing ("red_3 cannot defend this wing action") (pattern P2).

#### P-A3 — Pass into space (receiver must be positioned FIRST)
- **Check:** is the intended receiver already in the space the pass will be played into?
- **Express (Expert):** "blue_2 is too far back to receive a pass played into the space behind red's defense."
- **Express (Oracle):** "By the time blue_1 can pass, blue_2 should be positioned in red's half at (X, Y) — blue_2 cannot wait."
- **Source:** TC-02 attack_wing (pattern P6). **Probe rule:** every receiving position carries X,Y (E-series).
- **Interception-avoidance (TC-06):** when the pass lane is covered, the intended receiver repositions FIRST. Expert: "the lane from blue_1 to blue_2 is not straight — red_3 can intercept the assist." Oracle: "blue_2 moves now to open a straight, unobstructed lane to blue_1 (X≈2.0, Y≈0.8), so red_3 cannot intercept the assist."

#### P-A4 — Anticipate the block (act before the opponent responds)- **Check:** which opponent will move to block the ball-carrier, and where the free receiving space will be.
- **Express (Oracle):** "Red_2 will try to block blue_1, so blue_2 must actively move into the receiving position at (X, Y)."
- **Source:** TC-02 attack_wing (pattern P5).

#### P-A5 — Numbers advantage decides press-vs-pass
- **Check:** count blue vs red bots near the ball and in the contested zone.
- **Express (Expert):** "Two blue bots are near the ball; no red bot is within 2 m. Blue has a numbers advantage in the center."
- **Express (Oracle):** press the advantage; two attackers commit, the third holds depth.
- **Source:** TC-01 attack_center (pattern P4).

#### P-A6 — Rebound readiness
- **Check:** after a shot, where will the ball bounce back (restitution high, low friction → ball travels)?
- **Express (Oracle):** "blue_3 moves slightly forward to (X, Y) and stays ready to receive the ball if the shot bounces back."
- **Source:** TC-01 attack_center, TC-06 long_shot (pattern P7).

#### P-A7 — Wing play stretches the defense
- **Check:** is there open space on the wing (Y toward ±3.0) that pulls a defender wide?
- **Express (Expert):** "Wing play stretches the red defense and creates gaps in the center."
- **Express (Oracle):** "blue_2 runs to the wing position (X, Y) to pull red_2 wide."
- **Source:** universal axiom (was in TC-02, moved here), dictionary §5 (usable).

#### P-A8 — Contested possession = time budget
- **Check:** is an opponent within ~1 m of the ball? Then possession is contested and the ball-carrier has a time budget (opponent distance ÷ 0.8 m/s) before being challenged.
- **Express (Expert):** "blue_1 must secure possession immediately — red_2 (2.5, 1.5) is 0.67 m away and will contest in ~0.8 s."
- **Express (Oracle):** "blue_1 claims the ball at (X, Y) immediately, before the opponent contests." Deliberate actions belong to free-time situations (P-A1), not contested ones.
- **Source:** TC-06 long_shot (contested; contrast TC-02 free time).
- **Tackle vs press (TC-08, referee-grounded):** a bot within 0.8 m of the ball (BALL_PROXIMITY_THRESHOLD, `referee_node.py:27`) is contesting the ball — physical contact there is legal, never a foul. "Press" is not a referee concept. Fouls only fire AWAY from the ball: pushing (two opposing bots < 0.3 m apart while BOTH are > 0.8 m from the ball, `referee_node.py:286-291`) and blocking_without_ball (a bot > 0.8 m from the ball standing < 0.5 m from an opponent, between it and the ball, for ≥ 3.0 s, `referee_node.py:303-332`). So: contest aggressively near the ball; never crowd an opponent AWAY from the ball.
- > [!warning] subject to change: the foul model above is the CURRENT simulation referee (`referee_node.py`). It will change when RoboCup rules are adopted more closely in a later phase — re-check `referee_node.py` before relying on these thresholds.

### 1.3 Defending Principles

#### P-D1 — Zone-defend: don't chase the ball, block passing lanes
- **Check:** where can the opponent pass? Position to cut lanes, not to chase the carrier.
- **Express (Expert):** "Zone-defend: do not chase the ball; block the passing lanes."
- **Express (Oracle):** "blue_2 holds the center lane at (X, Y) to intercept passes."
- **Source:** acceptance phrase (usable, dictionary §5), TC-07 contain_delay.
- **Carrier-commitment tunnel (TC-07):** when the opponent carrier commits to the wing, a central lane toward the goal opens for a second opponent. The marking bot steps INTO that vacated lane instead of following the carrier. Expert: "if red_1 commits to the wing, the center lane toward blue's goal opens up — red_2 can run that tunnel." Oracle: "blue_3 blocks the center lane at (X, Y), not chasing red_1; blue_2 stays at (X, Y); blue_1 stays at (X, Y) as deep cover."

#### P-D2 — Lane / dribble denial
- **Check:** where will the opponent's next dribble/pass go? Place a bot to cut it off.
- **Express (Oracle):** "blue_2 moves down into the center lane at (X, Y) to cut off red_1's dribbling path toward the goal."
- **Source:** TC-03 defensive_crisis (pattern P9).

#### P-D3 — The obvious reaction is the one to expect
- **Check:** is only ONE blue bot realistically positioned to react directly? The others must anticipate, not also rush.
- **Express (Expert):** "red_1 is on the ball (0.1 m); blue_1 is the only bot positioned to react directly. blue_2 should anticipate."
- **Express (Oracle):** "blue_1 intercepts, moving closer to red_1; blue_2 cuts the center lane; blue_3 holds the left lane."
- **Source:** TC-03 defensive_crisis (session walkthrough — not yet a numbered P-pattern).

#### P-D4 — Deep cover (counter-attack safety)
- **Check:** if possession is lost, is the deepest bot/goalie positioned to intercept early?
- **Express (Oracle):** "blue_1 moves to the middle of its own half (X=-2.25) ready to intercept early if red counters." / "blue_3 stays back as deep cover at (X=-4.0, Y=0.0)."
- **Source:** TC-01 attack_center, TC-04 fast_counter (pattern P8).

#### P-D5 — Already in position = hold
- **Check:** is a bot already covering its lane / already at the required depth? Then no repositioning — an unnecessary move opens a lane or creates clustering (P-C2).
- **Express (Oracle):** "blue_1 stays at (X, Y) — already the deepest blue bot; blue_2 holds at (X, Y)."
- **Source:** TC-07 contain_delay.

#### P-D6 — Angle-closing first defender (classic)
- **Check:** the ball-carrier has a shot lane to the near post. Position the first defender sideways onto the ball→near-post axis to shorten the angle.
- **Express (Expert):** "blue_1 is off the ball→goal axis — the near-post shot lane is open."
- **Express (Oracle):** "blue_1 moves sideways (perpendicular to facing the ball) to (X, Y), on the ball→short-post axis, to shorten the angle."
- **Source:** TC-09 high_line (classic defender technique — confirmed by user 2026-08-01).

##### P-D6a — Two-man goal-mouth bracket (short-post + long-post)
- **Check:** two defenders defend against a ball-carrier with a passing target. Assign one defender to the ball→near-post axis (angle-closing, slides sideways keeping camera contact on the carrier), the other marks the passing target on the far-post side — together they bracket the goal mouth.
- **Express (Expert):** "red_1 is on the ball with a free pass to red_2; blue_1 is off the near-post axis and blue_2 is not covering the far-post side."
- **Express (Oracle):** "blue_1 moves sideways — keeping facing red_1 — to (X, Y) on the ball→short-post axis to block the short post; blue_2 attacks red_2 in a straight line to (X, Y), goal-side of red_2, covering the long post."
- **Source:** 2vs2_default (2026-08-01 walkthrough — defensive mirror of P-C3 bracketed-mouth attack).

### 1.4 Transition Principles

#### P-T1 — Press escape (hold + outlet)
- **Check:** is the ball-carrier under pressure? Is there a safe passing outlet?
- **Express (Oracle):** "blue_1 keeps the ball under pressure and passes to a teammate instead of forcing forward; blue_2 moves to the center line at (0.0, 0.8) as a backup option."
- **Source:** TC-05 pressing_trap (pattern P10).

#### P-T2 — Cover gap = obligation (do NOT leave it open)
- **Check:** is there a zone between the own goal and the play that no bot covers?
- **Express (Expert):** "blue_3 is too far from the goal area — there is no cover between the play and the own goal."
- **Express (Oracle):** "blue_3 holds the deep backup position at (X, Y)."
- **Source:** TC-05 pressing_trap (session walkthrough — P0 fix: "play back to the goalie" was ILLEGAL, no bot near own goal).

#### P-T3 — Recovery outlet (transition: position BEFORE possession is secured)
- **Check:** after a contested tackle/loss in the opponent half, where can the tackle-winner release the ball when the press arrives? Position the outlet receiver BEFORE possession is secured.
- **Express (Expert):** "red_2 and red_3 are behind the ball — out of reach for the tackle; blue_2 should anticipate the press and move to the free right-wing space."
- **Express (Oracle):** "blue_3 tackles for the ball at (X, Y); blue_2 keeps distance — does not cluster — and moves to the free right-wing position (X, Y) to wait for the ball to come free."
- **Source:** TC-08 def_transition (transition-direction variant of P-A3 receiver-first).

### 1.5 Session Distillation — what the walkthroughs taught us

The following rules emerged directly from the 2026-08-01 dialogue (user's human
feedback on TC-01..TC-06) and are now folded into the entries above. They are
listed here as cross-cutting session lessons:

1. **Expert states facts, Oracle prescribes.** The Expert never uses "should/
   must"; it reports geometry, angles, reachability, numbers (TC-02: "angle too
   narrow, ball between blue_1 and goal, red_2 far off will block"). The Oracle
   gives per-bot commands with X,Y. **Order: Expert first, Oracle second.**
2. **Every positional/negational verb carries explicit X,Y.** Coordinate-free
   prose actively misleads qwen2.5:3b (E1: bot placed ON the ball for "open
   space on the wing"; F1: "stays back" → bot moved FORWARD). This is the
   single most important inter-lingua rule (→ Layer 3, `7_C3_INTER_LINGUA.md`).
3. **Short oracles are fine — with coordinates.** TC-05's short oracle worked
   once coords were added (F2). Verbosity is not quality; coordinates are.
4. **A recommened action must be executable from the actual starting state.**
   "Play back to the goalie" is illegal when no blue bot starts near the goal
   (TC-05 P0). The generating LLM must read `scenario.json` before writing the
   Oracle.
5. **Expert is redundant when the Oracle already has coordinates (G1==G2), but
   Expert-only produces emergent reasoning with fuzzy targets (G3).** The hybrid
   (both sections, coords in Oracle) is the quality ceiling.
6. **Dynamic roles are rejected by qwen2.5:3b** (C2_striker_rule: "could be
   considered... not necessarily"). Prefer situation-triggered position verbs
   over derived role labels (→ Layer 3).

### 1.6 How to use Layer 1 (for the generating LLM)

1. Read the world state (`scenario.json` entities) and the ROS2K facts (Layer 2).
2. Select the applicable principles from §1.1-§1.4.
3. Write the **Expert** (facts from §Check) then the **Oracle** (commands with
   explicit X,Y from §Express Oracle), mapping every verb through Layer 3.
4. Do NOT repeat universal axioms verbatim inside per-scenario text — the
   principles here are the canonical module; per-scenario files reference
   situations, not axioms (testcase review §2.2).
5. Validate: world↔diagram congruence, coordinate grep, cross-TC consistency,
   3B probe (playbook §10).

## 2. Layer 2 — ROS2K Specifics (subject to change — VERIFY before generating)

> [!warning] **This layer changes with the codebase.** Always re-verify these
> facts against the sources before generating scenario text.

- **Field & goal:** 9×6 (X ±4.5, Y ±3.0); goal mouth ±0.9 at X=±4.5; goal area
  (±3.5, ±1.0); corner flags ±4.3/±2.8. Source: `referee_rulebook.md` §3.3,
  `gen_field_diagrams.py` constants.
- **Ball physics:** mass 0.4, restitution 1.0, friction mu 0.01, velocity_decay
  0.002 → ball rolls far, kicks travel long. Source: `football.urdf`.
- **Bots:** max ~0.8 m/s. Reachability = distance / 0.8. Source:
  `ollama_sandbox_bridge.py`.
- **Kick:** phantom kick (velocity reset); non-goalie kicks aim at the opponent
  goal ("clear to sideline" NOT executable). Source: bridge role-aware kick.
- **Referee:** NO offside; kick-in (NOT throw-in), goal-kick, corner kick-in,
  kickoff; set-piece freeze + 5s countdown; foul thresholds push 0.3m/0.5m/s/
  0.8m, block 0.5m/30°/0.8m; restart placements. Source: `referee_rulebook.md`,
  `referee_node.py`.
- **Roles:** goalie/attacker/defender only. Goalie blending 70/30 tactical/LLM,
  Y tracks ball, ~-4.0 limit. Source: bridge goalie constants.
- **Goalie role = two meanings (league-specific):** (A) a *designated* bot that
  gets exclusive privileges (e.g., RoboCup dive-catching); a substitute does NOT
  inherit the privileges. (B) a *pure tactical assignment* — the bot simply
  sticks near the goal. **ROS2K today implements meaning B**: the LLM may
  reassign the goalie role mid-play (recovery action); the bridge's goalie
  blending then applies to the newly assigned bot. Reassigning this way also
  reduces walking time/effort to re-form the standard formation later. Source:
  TC-09 high_line walkthrough (2026-08-01).
- Full detail: `referee_rulebook.md`, `AGENTS.md` Gotchas, power-files
  `2_ROS2_PROTOCOLS_AND_FRAMES.md` + `4_EDGE_HARDWARE_SIM2REAL.md`.

## 3. Layer 3 — Inter-lingua Mapping (short — see KB)

The qwen2.5:3b translation rules. Full evidence: `7_C3_INTER_LINGUA.md` (anchor),
`c3_vocabulary_dictionary.md` (per-term verdicts), `c3_scenario_generation_playbook.md`
§6 (usable/borderline/reject), §9 (anti-patterns A1-A5), §10 (validation + probe query).

| Soccer concept (Layer 1) | qwen2.5:3b expression (inter-lingua) |
|---|---|
| "stays back as backup" | "holds position at (X, Y)" (negation inverts — F1) |
| "open space on the wing" | "moves to (X, Y) on the wing" (no-coord → ON ball — E1) |
| "the attacker (closest bot)" | "blue_2 moves to the ball" (dynamic role rejected — C2) |
| "goal area / penalty box" | concrete coordinates only (hallucinated — D5) |
| "throw-in" | "kick-in" (no hands; referee-owned placement) |
| "dive" (goalie) | "positions between ball and goal" (impossible — D6) |
| "short post / long post" | "goal mouth at Y≈+0.9 / Y≈-0.9" (human jargon, not in dictionary — TC-06) |

Verbs usable: move to X,Y, receive pass, support run to X,Y, hold position,
mark X, cover a zone, clear the ball, cover the goal line, pass/shoot/cross/kick.
Borderline: press, chase (need targets). Reject: throw-in, free-kick, dive,
penalty area, sweeper, dynamic roles.

**Validation query** (per generated package, playbook §10.4):
system = "You are a soccer analyst. Given a world state and a tactical
instruction, output target X,Y positions for each blue bot. Format:
blue_1: (X, Y), blue_2: (X, Y), blue_3: (X, Y). Output only the three lines.";
prompt = scenario.json entities verbatim + "Tactical instruction: <Oracle>" +
"Output the three target positions."; Ollama `qwen2.5:3b`, temperature 0.0,
num_predict 600.

## 4. Relation to other power-files

- `7_C3_INTER_LINGUA.md` — the inter-lingua paradigm anchor (Layer 2+3 rules,
  vocabulary constraints, validation protocol, P1-P10 summary).
- `6_DATA_SCHEMAS_AND_LIFECYCLE.md` — scenario package schema (`scenario.json`
  v6, `analysis.md` layout, `kpi_targets.json`).
- `2_ROS2_PROTOCOLS_AND_FRAMES.md` — referee mechanics detail.
- `3_AI_LOGIC_AND_EDGE_CASES.md` — role condensation, goalie blending, kick
  mechanics.

## 5. H1 scenario-probe lessons (2026-08-03)

Five new scenarios were probed with qwen2.5:3b (zero-shot, no fragments, no
few-shot examples — just a system prompt asking for Expert/Oracle/Recommended
Actions). Two reviewers (GLM-5.2 and the human soccer expert) gave feedback.
The model's output was **catastrophically poor** (0/5 scenarios produced a
correct Oracle). Seven recurring failure modes were identified:

### F1 — Possession misidentification (CRITICAL)

The model says "Blue has the ball" when red has it, or vice versa. It does not
compute which bot is closest to the ball to determine possession. In S2
(possession lost) and S4 (deep cross), the model treated defensive situations
as attacking — producing attacking commands when blue should be defending.

**Lesson:** The Expert section MUST begin with an explicit possession
determination: "The bot closest to the ball is X_N at distance D. X team has
possession." Without this, the model defaults to "blue has the ball" regardless
of the world state. This must be a rule in `rules_core_text.txt`, not just a
pattern in the knowledge base — the model cannot infer it.

### F2 — Goalie abandons goal (CRITICAL)

In 4 of 5 scenarios, the model sent the goalie (blue_1 at X=-4.0) to the
opponent's half, the corner, or a midfield position. The "GOALIE HOLD VS CLOSE"
rule added in H1.3 addresses this for the case where the ball is near the own
goal — but the model also abandons the goal when the ball is far away. The
goalie should NEVER move more than 1m from the goal line (X=-4.0) unless
intercepting a crisis ball within 1.5m of the goal.

**Lesson:** The goalie blending in the bridge (`ollama_sandbox_bridge.py`)
already overrides the LLM's goalie target to stay near the goal line. But the
LLM's command is still logged and displayed — a goalie command to (4.5, 0.0)
is confusing in the visualizer and undermines trust. The prompt should
explicitly state: "The goalie (blue_1) MUST stay within 1m of X=-4.0 at all
times. Never command the goalie to move to X > -3.0."

### F3 — Wrong goal direction (CRITICAL)

The model sends blue bots to X=+4.5 (opponent goal) when defending and to
X=-4.5 (own goal) when attacking. This compounds with F1 (possession
misidentification): if the model thinks blue has the ball, it sends bots
toward the opponent goal — even in a defensive scenario.

**Lesson:** The field direction ("Blue attacks toward X=+4.5") is in the
system prompt, but the model doesn't internalize it. The Expert section
should explicitly state: "Blue attacks toward X=+4.5. Blue defends X=-4.5."
Repeating this in every Expert analysis forces the model to anchor on the
correct direction.

### F4 — No kick/pass command (MAJOR)

In 3 of 5 scenarios, the ball carrier did not receive a `kick` command. The
model produced only `move to` commands — bots ran to positions but no one
actually played the ball. This is the "receiver passivity" anti-pattern (H1.3
#6) in a more severe form: not even the ball carrier kicks.

**Lesson:** The KICK RULE in `TEXT_OUTPUT_HEADER` ("the bot closest to the
ball outputs 'blue_N kick'") addresses this in the production prompt. But the
zero-shot probe had no KICK RULE — confirming that the rule is load-bearing
(F4_nok3h finding: 0/3 gaps without K3 rules). The rule MUST stay in the
header.

### F5 — Expert hallucinates entities (MAJOR)

In S3 (wing switch), the model invented a "red ball carrier at X=-4.5, Y=2.2"
that does not exist in the world state. The Expert section should only
reference entities that are explicitly listed in the world state input.

**Lesson:** The Expert section must be grounded in the provided world state.
A rule "Only reference entities listed in the world state above. Do not
invent bots or positions." should be in the system prompt.

### F6 — No defensive awareness (CRITICAL)

In S2 and S4, the model treated defensive scenarios as attacking. It produced
"attack the red bots," "score a goal," "aggressively utilize their possession"
— all wrong when blue is defending. The model has no concept of defensive
shape, recovery runs, or goal-mouth bracket defense.

**Lesson:** This is the deepest gap. The model's default mode is "attack" —
it needs explicit signaling to switch to defense. The Expert section should
always include: "Situation: attacking / defending / transition." This
situation label primes the model for the correct mode. Without it, the model
defaults to attacking regardless of the world state.

### F7 — Meaningless distance/angle calculations (MINOR)

In S5, the model produced "distance: 7.16 units at angle -75 degrees" —
numbers that don't match the field geometry. The model attempts arithmetic
but gets it wrong. This is cosmetic (the Oracle commands are what matter)
but undermines the Expert section's credibility.

**Lesson:** Do not ask the model to compute distances or angles. Instead, ask
for qualitative assessments: "close" (<1m), "nearby" (1-2m), "far" (>2m).
The model can judge proximity qualitatively but not quantitatively.

### Summary: required prompt additions

Based on these 7 failure modes, the following additions to the production
prompt (fragments + header) are needed:

1. **Possession determination rule** (rules_core_text.txt): "The Expert
   section MUST state which team has the ball. The bot closest to the ball
   has possession. If the closest bot is red, blue is defending."
2. **Situation label rule** (rules_core_text.txt): "The Expert section MUST
   begin with 'Situation: attacking / defending / transition' based on
   possession and ball position."
3. **Goalie confinement rule** (rules_core_text.txt): "The goalie (blue_1)
   MUST stay within 1m of X=-4.0. Never command the goalie to move to X > -3.0."
4. **No-hallucination rule** (header): "Only reference entities listed in
   the world state. Do not invent bots or positions."
5. **KICK RULE** (already in `TEXT_OUTPUT_HEADER`): confirmed load-bearing.
6. **Field direction repetition** (rules_core_text.txt): "Blue attacks
   X=+4.5. Blue defends X=-4.5." — already present but needs to be in the
   Expert section guidance, not just the rules.

**Field orientation convention (wing mapping):**
- Blue attacks toward X=+4.5. Blue defends X=-4.5.
- Blue's LEFT wing = positive Y (Y > 0). Blue's RIGHT wing = negative Y (Y < 0).
- Red's perspective is mirrored: Red's LEFT wing = negative Y, Red's RIGHT wing = positive Y.
- Expert text and analysis.md MUST use this convention when referencing
  "left wing" or "right wing." A ball at (3.0, 2.0) is on Blue's LEFT wing
  (positive Y), NOT the right wing. This error was found in 3vs3_attack_wing
  (2026-08-07 review) — "right wing" was written for a ball at Y=+2.0.

**Tactical score range:**
- The tactical score (`current_numerical_score` from `score_node.py`) is
  clamped to [-10.0, +10.0]. Positive = Blue advantage, negative = Red
  advantage. Score charts must use this fixed range on the x-axis.

These are in addition to the "GOALIE HOLD VS CLOSE" rule already added in
H1.3. The rules should be tested in Phase M sub-exp 2 (prompt structure
residual — zero-shot vs current).

### H1 user-feedback discrepancies (2026-08-03)

When the human soccer expert's feedback was compared to GLM-5.2's, two
discrepancies produced new lessons:

**D1 — Goalie rushes the ball carrier in a 1v1 (S2 possession lost).**
GLM-5.2 said "goalie should stay on the goal line." User corrected: the goalie
must COME OUT to shorten the kick angle — this is a 1v1 where the goalie
rushes the ball carrier. Lesson: in a defensive crisis where ONLY the goalie
is between the ball carrier and the goal, the goalie must advance to narrow
the angle, not hold the line. This refines the "GOALIE HOLD VS CLOSE" rule:
the 1.5m threshold applies to *interception*, but in a 1v1 breakaway the
goalie rushes regardless of distance.

**D2 — Blocked switch escape (S3 wing switch).**
GLM-5.2 said "switch play from overloaded left to open right." User corrected:
yes, but no chance to do so — the double-team is too tight, blue_2 cannot
escape to make the switch pass. The realistic play is to kick the ball deep
out of pressure toward the opponent half and accept a set-piece restart
(kick-in or goal kick for red) rather than attempt an impossible switch.

This is a new pattern: **P5b — blocked switch escape**: when the switch pass
is not executable due to immediate pressure, kick the ball deep out of danger
and reset. The ideal tactical pattern (P5) must be gated by an executability
check: can the ball carrier actually release the ball before being
dispossessed? If not, the escape kick is the correct play.

### H2 live-demo feedback (2026-08-03)

First live Gazebo match with V5 role-locked prompt (3vs3_attack_center,
--no-explain). User observed 5 issues + noted many actions are OK:

**F8 — Passive non-tackling bot (MAJOR).** When blue_2 (attacker) kicks, the
other two bots (blue_1 goalie, blue_3 defender) are passive — they hold
position instead of supporting the play. The non-tackling bot should move to
support: the defender shifts toward the ball for a rebound, the goalie tracks
the ball trajectory. V5's role-locked labels ("DEFENDER: mark, cover, hold
midfield") make the defender too passive.

**F9 — Goalie and defender same responsibility → clustering (MAJOR).** In
defense, both blue_1 (goalie) and blue_3 (defender) cover the goal line at the
same Y. The role-locked header says "blue_3 DEFENDER: mark, cover lanes, hold
midfield" but the model sends blue_3 to the goal line too. Need explicit
separation: goalie = goal line, defender = in front of goal, NOT on the line.

**F10 — Yellow dotted arrows in visualizer don't match bot actions (MINOR).**
The visualizer draws arrows from bot positions to LLM targets, but the bridge
overrides some targets (goalie blending, PD controller). The arrows show the
LLM intent, not the actual executed movement. This is cosmetic but confusing.
Note: the visualizer arrows are from the live ROS data, not the H1 diagrams.

**F11 — Goalie fails to kick from own half (MAJOR).** When the goalie has the
ball in its own half (e.g. after a save), it should kick the ball upfield
toward the opponent half. The V5 relaxed goalie rule allows kicking when
closest to the ball, but the model still outputs "cover the goal line" instead
of "kick" when the goalie has the ball. The role label "GOALIE: cover the
goal line" dominates over the KICK RULE.

**F12 — Defending bots too passive (MAJOR).** When defending, blue bots hold
position and wait rather than pressing the ball carrier. The DEFENSIVE
AWARENESS rule says "move behind the ball" but doesn't say "press the ball
carrier." Defending bots should actively challenge, not just retreat.

**F13 — Goal kick red → chaotic behavior (MAJOR).** During a goal kick for
red, the blue bots behave chaotically — likely because the game-phase fragment
(rules_goal_kick.txt) is a 2-line stub with no tactical guidance. The model
doesn't know what to do during a goal kick. Need substantive game-phase rules.

**Positive:** many actions of blue are OK — the role-locked header produces
structurally correct output (3 bots, in-field, valid roles, kicks present).
The issues are tactical, not structural.

## 6. v6.4 Session Lessons (2026-08-05)

### Clustering root cause and fix

**Root cause:** The LLM produces CORRECT, non-clustered targets (blue_1 →
-4.0, blue_2 → kick, blue_3 → -2.7). But blue_1 gets physically stuck at
X=-2.6 (PD controller too weak to return 1.8m) and blue_3 is sent to -2.7
(where blue_1 is stuck). They cluster at X≈-2.6 because the LLM doesn't know
blue_1 can't reach its target.

**Fix (prompt only, no bridge hacks):** Changed blue_3 from a fixed zone
("X=-2.0 to -3.0") to relative positioning ("maximize distance from blue_1
and blue_2, stay at least 1.5m from both"). Changed SPLIT RULE from
"if near the ball" to "never put two bots within 1.5m of each other" — a
pairwise constraint that's always active.

**Result:** cluster_all dropped from 47% → 0-1% in live Gazebo (6 matches).
The own-right clustering pattern (X≈-2.6, Y≈-1.4) was eliminated because
blue_3 now goes to X≈-0.5 (midfield), far from the goalie stuck zone.

**Lesson:** When the LLM's targets are correct but bots can't reach them,
the fix is to make the LLM's targets RELATIVE to actual positions, not
absolute zones. The LLM can't know about physics limitations.

### P-C2b — Bridge anti-collision (supplementary to P-C2)

The bridge pushes non-kicker bots 1m away from the kicker when within 0.5m.
This is a physics-level supplement to the SPLIT RULE — it catches cases
where the LLM's targets are correct but bots physically converge during
execution. Reduced pair clustering from 58-80% → 20% avg.

### Goalie goal-line mode (R2K_GOALIE_BLEND=0)

The bridge's goalie blending (Phase 2a angle-block mode) was pulling the
goalie from X=-4.0 to X=-2.5 during normal play, causing clustering with
blue_3. Disabled via `R2K_GOALIE_BLEND=0` env var (default off). When
disabled: goalie stays at line_x=-4.32 with damped Y (0.5 × ball_y).
The LLM decides when the goalie advances (crisis, 1v1) — the bridge obeys.

### Kick direction override (goalie)

When blue_1 (goalie) kicks, the bridge overrides the kick direction to
always aim toward +X (opponent goal), regardless of the bot's yaw. This
prevents the goalie from kicking the ball sideways out of bounds.

### Score function refined (Phase R)

`score_node.py` extended with two new metrics:
- **Cluster penalty:** -2 if blue bots within 0.5m, -1 if within 1.0m
- **Lane openness:** -3 if no blue bot between ball and own goal (ball in own half)

Score range still [-10, +10]. A1 (winning matches have higher score) and
A2 (positive slope before good outcomes) both verified on 793 existing
matches.

### Per-bot kick capability matrix

Different hardware types have different kick capabilities:

| Bot | Can kick? | Mechanism | Abort needed? | Range |
|---|---|---|---|---|
| K1 | Yes | kShoot (2024) / kVisualKick (2038) — autonomous chase | Yes (follows ball) | Long |
| Yahboom (both types) | Yes (try) | Metal front push | No | Short, untested |
| Trailer | No | Never | N/A | N/A |
| Gazebo sim | Yes | Phantom kick (set_entity_state) | No (instant) | Full |

The relay JSON is many-to-many (mixed hardware for testing). RoboCup rules
forbid mixed teams in tournaments. Per-bot `can_kick` flag needed for v7.

### K1 kick chase problem

The K1's kShoot (2024) and kVisualKick (2038) are autonomous skills — the
K1 takes over and chases the ball until kick distance is reached. If the
ball moves away (kicked by self or opponent), the K1 follows indefinitely.
This is a game-stopper for real matches.

**Solution (v7):** any bot's camera (K1 head cam — Yahboom cam is lousy)
detects ball velocity/direction change. Published as ROS2 topic. TeamCaptain
(or bridge) sends kChangeMode (2000) to abort the chase. No thresholds, no
hysteresis.

### Meta-knowledge axiom (recurring lesson)

The LLM prompt must NEVER contain: "bridge commands", "bridge executes",
"cmd_vel", "RPC", "path executor", "ROS2K protocols", or any implementation
detail. The LLM's world is: read positions, output per-bot instructions with
X,Y coordinates. Everything else is infrastructure. This is a recurring
mistake — add it to the C3 axioms permanently.

### Empirical scenarios (Phase R)

74 umschaltmomente extracted from 467 matches with goals. Clustered to 33
representative scenarios at 3.0m threshold. Types: ball_won (17), restart
(8), cluster (4), pass (3), clearance (1). Tags: empirical-proven (9),
regression-anti (24). Each has: Source / Expert / Oracle / Output to bridge
/ Qwen decision / Regression metrics / Score chart / Test spec.

### Demo/calibration mode

A third prompt mode (--demo) for human-driven bot control. Human types
commands, LLM reformats to inter-lingua, same evaluator-bridge pipeline.
Dual-use: workshop demos + calibration. JSON fallback (calibrate_bot.py)
works when LLM is down. Demo prompt contains NO meta-knowledge.
