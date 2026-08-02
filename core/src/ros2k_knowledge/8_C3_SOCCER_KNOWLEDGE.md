---
id: 8_C3_SOCCER_KNOWLEDGE
title: "Section 8: Universal Soccer Knowledge (C3 Layer 1)"
type: KNOWLEDGE_BASE_POWER_FILE
tags: [c3, inter-lingua, soccer-knowledge, universal-knowledge, expert-oracle, scenario-generation, coaching-heuristics, position-verbs, v6.3, c3-layer1, qwen2.5]
last_modified: 2026-08-01
version: v6.3
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

#### P-A4 — Anticipate the block (act before the opponent responds)
- **Check:** which opponent will move to block the ball-carrier, and where the free receiving space will be.
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
