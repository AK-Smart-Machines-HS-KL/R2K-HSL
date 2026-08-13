# Redesign Evaluation Project — Project Info

> Management summary document. Version 0.4 — 2026-08-02.
> Phase plan + deep details by phase (Phases 0, 1, L, I, K, F filled).

**Goal:** Redesign ROS2K evaluation to measure soccer semantics (behavior
gaps, competition, passing) via text-only probe/battery analysis — not just
soft scores or unreliable Gazebo win rates — then validate against a
baseline in a short Gazebo pilot.

**Scope note:** this is a summary management doc. Deep details live in the
primary sources:
- `core/docs/c3_phase0_literature_and_plan.md` (phase plan, literature)
- `core/docs/c3_vocabulary_dictionary.md` (controlled vocabulary, probe verdicts)
- `core/docs/c3_scenario_generation_playbook.md` (scenario authoring, validation)
- `core/docs/c3_testcase_review.md` (test-case fixes)
- `core/src/results/prompt_structure_report.md` (V_A/V_B/V_C study)
- `core/src/results/k3_results.md` (competition/pass gaps)
- `core/src/results/probe_f3_structure_report.md`, `probe_f4_content_report.md` (Phase F)

---

## Document status

| Item | Status |
|---|---|
| Origin | C3 inter-lingua work (2026-07-31 → 2026-08-02) |
| Approach | Text-only phases first (~80× faster than Gazebo), Gazebo pilot only after text metrics are stable |
| Phase execution | 0, 1, L, I, K, F DONE — 2/NEXT, 3, W, 4, 4b, 5 pending |
| Commits | Phases L (d115503) + I (7b6b4fa) committed; Phase 0/1 + K/F + this doc uncommitted |
| Blockers | none for text-only phases; Gazebo phases need live Gazebo + Ollama + `ollama pull llama3.2:3b` (Phase 4b) |

---

## Project plan — Phases

### Phase 0: Literature research, corrected framing, model switch — DONE (2026-07-31)
- Literature survey (11 papers: LLCoach, SayCan, RoboMatrix, EmboTeam, SCOPE, HALO, BTGenBot-2, self-verifier, verifier-gaming, orchestration gap) + GitHub search.
- Corrected the initial framing per user: no rule-based bridge mapper, no JSON skill API; LLM outputs controlled-vocabulary instruction sentences. Composite score demoted to diagnostic.
- Model switch qwen2.5-coder:3b → qwen2.5:3b (coder corpus is soccer-out-of-distribution).
- New 27-run Gazebo baseline with qwen2.5:3b (parallel).
- **Artifacts:** `c3_phase0_literature_and_plan.md`; baselines `results/baseline_qwen25_3b_summary.md`.

### Phase 1: Vocabulary probing → dictionary — DONE (2026-08-01)
- 56 Ollama probes (A–G series): free elicitation, instruction formation from real trace frames, comprehension/contradiction, borderline vocabulary.
- Produce controlled-vocabulary dictionary with usable/borderline/reject verdicts.
- Rule (from E/F/G evidence): every positional/negational verb carries explicit X,Y; zone nouns need explicit bounds.
- **Artifacts:** `docs/c3_vocabulary_dictionary.md`, `tools/vocab_probe.py`, probes in `experiments/phase1_probes/`.

### Phase L: Fragment migration — DONE (2026-08-01)
- Aligned prompt fragments with dictionary vocabulary; migrated role/sample fragments.
- **Artifacts:** fragment files under `strategy/fragments/` (committed d115503).

### Phase I: Transform builder — DONE (2026-08-01)
- Build the transform that converts canonical world representation into the inter-lingua sentences.
- **Artifacts:** committed 2026-08-01.

### Phase K: Behavior battery (rule-vs-example) — DONE (2026-08-02)
- Situational battery tests with gap diagnostics (gapC competition / gapP pass) — what the soft score misses.
- Findings: competition split needs a rule; pass needs an example; pass rule gated to X>0; one channel only (rule-file + header regresses).
- **Artifacts:** `tools/i3_battery.py`, `results/k3_results.md`.

### Phase F: Few-shot paradigm rework — DONE (2026-08-02)
- F3 structure sweep (972 probes): F0 (global rules + separate samples) 93% hard — interwoven paradigm loses decisively (56–62%).
- F4 content sweep (1215 probes): 1 sample sufficient (98% hard); K3 rules load-bearing; explain catastrophic (56%).
- **Verdict:** keep F0 structure as-is — production prompt needs no change.
- **Artifacts:** `tools/llm_probe.py`, `tools/build_corpus.py`, 81-state corpus `tests/synthetic_worldstates/corpus.jsonl`, probe reports.

### Phase 2: Rework test case descriptions — NEXT
- Rework `scenario/*/analysis.md` in dictionary vocabulary (position verbs + explicit X,Y, no derived role labels).
- Translate referee rules per code (`referee_node.py`, `rule_evaluator_red.py`), not RoboCup standards.
- Validate textually + situationally via `llm_probe.py`.

### Phase 3: Validate detailed comprehension — NEXT (after 2)
- Same method as Phase 2, deeper: game states, edge situations, referee decisions.

### Phase W: Watchdog & closed-loop feedback — NEW (parallel to 2–3, text-only)
- W1: synthetic divergence scenarios (no-div / ball-div / bot-div / score-div / status-div / noise).
- W2: Option A — re-prompt the 3B on divergence.
- W3: Option B — second model (1.5B) as monitor (VRAM contention risk).
- W4: Compare and decide (accuracy, latency, simplicity, GPU).
- **Deliverable:** watchdog design decision report. No implementation yet.

### Phase 4: Pilot test — FIRST GAZEBO RUNS — NEXT (after 2, not affirmed)
- 4a annotated pilot (human-in-the-loop, `--analyze --explain`, gap harvest).
- 5 runs × 120s on `3vs3_attack_center`; measure vs new baseline.
- **Gate:** recurring executable gaps → new battery situations → fix before measurement.

### Phase 4b: Llama-3.2-3B regression test — NEW (parallel to Phase 4, text-only)
- Test inter-lingua model-agnosticism: same sweep with `llama3.2:3b` (needs `ollama pull llama3.2:3b`).
- ≥80% of Qwen metrics → model-agnostic.

### Phase 5: Full evaluation — not affirmed
- If pilot passes: n=30, 9 scenarios, full C3 evaluation.

---

## Deep details by phase

> Filled from the primary sources listed above. One section per phase;
> more phases appended as the project progresses.

### Phase 0 — 2026-07-31: Literature research, corrected framing, model switch

**Trigger/context.** The C-series Gazebo experiments (qwen2.5-coder:3b) had
plateaued at ~11.8% win rate (C1+C9, n=17/153). The question became: is the
*model* the limit, or the *interface* (prompt/instruction language) between
us and the model? The redesign project = test the interface hypothesis with
text-only iteration (probe/battery), not Gazebo win rates.

**1. Literature survey** (11 papers + handover; full tables in
`c3_phase0_literature_and_plan.md` §1).

| Paper | Key finding | What it decided for us |
|---|---|---|
| LLCoach (2406.18285) | LLM-coach architecture valid for RoboCup SPL (plans, not per-tick commands) | Confirms architecture; but they use a large LLM at play-level — we use 3B at tick-level (~750ms). Open question: can a 3B do it? |
| SayCan (2204.01691) | NL action labels + separate affordance layer; constrained vocabulary, not JSON | **Controlled vocabulary = constrain the output space, not the format.** Our bridge IS the affordance function. |
| RoboMatrix (2412.00171) | Named skill verbs + typed args; +50% vs monolithic | "Skill" = our verb+noun+adjective. Decomposition helps even small models. |
| **BTGenBot-2 (2602.01870)** | **1B model, 90% zero-shot, beats GPT-5** when output vocab is small + primitive list given as input | **Most actionable:** Phase 1's job = discover which primitives the 3B *already* knows, then give them back to it. |
| EmboTeam (2601.11063) | LLM→PDDL→planner→BT; planner acts as *verifier*, catches LLM errors (12%→55%) | **No mapper = no verifier** → LLM errors propagate to the bridge. The watchdog (Phase W) is the verifier. |
| SCOPE (2606.02951) | Qwen SLMs for NL tool routing; once SLM capable, *perception* becomes bottleneck | Once vocabulary is right, the world model (perception) becomes the bottleneck → world models stay on the roadmap (Phase 5.1). |
| HALO (2505.13516) | Adaptive prompt refinement + role separation in one model | Role separation can live *within one prompt* — no multi-model needed. |
| Self-verifier (2510.24299) | LLM checks own output via internal activations (75%) | Watchdog Option A idea — but needs `transformers` access, Ollama REST doesn't expose activations. |
| Verifier-gaming (2604.15149) | RLVR models learn to *game* imperfect verifiers | Warning for watchdog Option B — mitigate by checking *world-state consistency*, not output quality. |
| Orchestration gap (2607.21725) | Separating reasoning from execution = 4× (12.8%→53.3%) | **The watchdog IS the orchestrator** (outcome tracking + failure recovery) — this is where the 4× lives. |
| ECoT (2407.08693) | Prompt-only CoT ≈ noise on 7B; gains from *training* on CoT | Our analysis/oracle fields are CoT — don't expect them to *improve* reasoning; they are pattern primers. |
| Two Calls Beat Five (2607.26922) | Multi-agent pipelines drop 30pp on 7B; self-refinement helps only if base <85% | At 11% self-refinement is theoretically justified — but "check your work" may be meaningless at 11%. Low priority. |
| C9 (our run, n=17) | Prediction at t+746ms does not improve win rate | Prediction doesn't help a pattern-copier's *inputs*; its value is *failure detection* (predicted vs actual) — feeds the watchdog. |

Interwoven few-shot: **no prior work found** (in-context literature covers
*which* examples, not how to structure them vs global rules) → Phase F fills
a research gap. GitHub search: 0 repos on "robot instruction + controlled
vocabulary" — intersection is too niche; our work fills the gap.

**2. Model switch: qwen2.5-coder:3b → qwen2.5:3b.** From the Qwen2.5-Coder
technical report (arxiv 2409.12186): training mix is **70% source code /
20% text-code grounding / 10% math** — soccer vocabulary is not
in-distribution for a code-specific model. The base Qwen2.5-3B-Instruct has
broader web/book exposure where sports vocabulary lives. Same architecture
(36 layers, GQA 16/2, 151,646 vocab, 32K ctx) → evaluator, bridge, trace
logging, dynamic injection, content-hash skip all work identically; only
weights differ. **Consequence: C-series baselines (11.8%) invalidated** —
a new 27-run baseline ran parallel to Phase 1. Regression test with
`llama3.2:3b` later (Phase 4b) tests model-agnosticism + edge deployment
(Jetson AGX/Orin for K1).

**3. Corrected framing** (user feedback, changed the direction of the whole
project):

| Initial assumption | Corrected |
|---|---|
| Rule-based mapper in the bridge | **No new mapper.** LLM outputs instruction sentences directly; bridge already parses assignments. |
| JSON skill API (`press(ball)`) | **Controlled vocabulary** — NL verb+noun+adjective sequences; constrained *output space*, not JSON. |
| Composite score = wrong metric | **Composite = diagnostic** — decomposes win rate into addressable components (what to improve), not the primary metric. |
| World models = overkill | **Not overkill long-term** — just not in C3; Phase 5.1 stays on the roadmap. |
| Gazebo runs needed for Phases F/W | **No Gazebo** — LLM text output analyzed on synthetic world data. ~700-1200ms per probe vs 120s per match (~85-135× faster). |
| qwen2.5-coder:3b as the LLM | **qwen2.5:3b** (see §2 above). |

**4. Baselines** (measured; `results/baseline_qwen25_3b_summary.md`).

- **OLD (invalidated):** C1+C9 qwen2.5-coder:3b — win rate 11.8%, 0.93
  conceded/match, OOB 9.4%, best scenario 35.3% (attack_center).
- **NEW (qwen2.5:3b, 27 runs, 9 scenarios × 3):** 11 scored : 21 conceded
  (0.41 scored / 0.78 conceded per match — better than coder's 0.36/0.93,
  confirms the model hypothesis); avg composite 0.32; avg latency p50 744ms.
  Best scenario: attack_wing composite 0.39; lowest OOB attack_center 7.7%.
- **C3 targets:** win rate > new baseline; conceded <0.78/match; OOB <7.7%;
  best-scenario composite >0.39; latency ≤761ms.

**5. Latency budget (measured for qwen2.5:3b):** no-explain p50 **761ms**
(27-run baseline); explain ~1100ms (estimated from Coder +44%, verify in
Phase F — measured 691ms in F4_explain on short prompts); `format: "json"`
**~2081ms — reverted, never use with any Qwen variant** (C-series confound).

**6. Key decisions taken here:**
1. Text-only iteration loop becomes the standard method for C3 (synthetic
   world states + LLM text analysis; trace data as synthetic source).
2. Vocabulary discovery (Phase 1) comes *before* any prompt rewrite — the
   reference is the model's own language, not human jargon.
3. Phase plan restructured: two new text-only phases inserted — **F**
   (few-shot paradigm rework: interwoven vs separate rules/examples) and
   **W** (watchdog & closed-loop feedback) — before the Gazebo pilot.
4. Phase 4b (Llama regression) added as a parallel text-only test.
5. The watchdog is no longer optional infrastructure: it is the verifier/
   orchestrator that EmboTeam + orchestration-gap literature say produces
   the 4× improvement.

**Artifacts:** `core/docs/c3_phase0_literature_and_plan.md` (799 lines —
the plan this doc summarizes); `core/src/results/baseline_qwen25_3b_summary.md`
+ 27 `kpis_baseline_qwen25_3b_*.json`; model switch in `launch_r2k.sh:12`
(default model) + `tools/run_baseline.sh` (MODEL arg); changelog entries
2026-07-31.

### Phase 1 — 2026-08-01: Vocabulary probing → dictionary, test-case review, prompt-structure study

**Goal.** Discover Qwen2.5-3B-Instruct's *own* soccer vocabulary through
direct conversation, and create a controlled vocabulary of
verb+noun+adjective sequences as the basis for all later prompt work.
The reference is the model's language, NOT human jargon (per Phase 0
decision). Deliverables: dictionary, test-case review with P0-P3 fixes,
scenario-generation playbook, prompt-structure verdict.

**1. Probing campaign (56 probes, A–G series + PS_* + VERIFY_*).**
Tool: `tools/vocab_probe.py` (Ollama wrapper, temperature 0.0,
num_predict 600, keep_alive 1h, batch mode; every probe appended to
`results/vocab_probe_log.md`).

| Series | Content | Count |
|---|---|---|
| A | Free elicitation: word lists, tactical terms, 8 roles | 14 |
| B | Instruction formation from 6 real `world_trace` frames + template verbs (move/receive/support/clear/mark/hold/press/cover/chase) | 18 |
| C | Comprehension: contradiction test, acceptance criteria, referee situations | 12 |
| D | Borderline verdicts: own half, kick-in, mark vs cover, corner placement, goal area, clear near goal | 6 |
| E/F/G | Coordinate rule: with vs without explicit X,Y; expert-only vs oracle-only | 7 |
| PS_* / VERIFY_* | Prompt-structure study V_A/V_B/V_C + fix verification | 37 |

**2. Dictionary verdicts** (`c3_vocabulary_dictionary.md`, 174 lines —
reference for ALL later work):

- **Usable verbs:** move to X,Y · receive pass · support run · hold
  position · mark X · cover a zone/position · clear the ball · cover the
  goal line · pass/shoot/cross. Borderline: press the ball (human "use
  your hands" twist), chase the ball (needs speed/angle). Reject:
  throw-in (no hands — RoboCup term is **kick-in**), cut inside (no
  dribble action).
- **Usable nouns:** goal/goal line · center · field · wing/flank/sideline ·
  passing lane · formation. **Own half** usable ONLY with explicit bound
  ("X from -4.5 to 0"); **"opponent half" broken** (model said "+4.5 to
  9") → rephrase as "the red side of the center line". Goal area:
  model hallucinates off-field coords → always give explicit coordinates
  (±3.5, ±1.0), never rely on the noun.
- **Roles:** only goalie/attacker/defender survive (3-role taxonomy);
  striker/midfielder/sweeper/playmaker/supporter rejected as *derived
  concepts*.
- **CRITICAL finding (C2_striker_rule):** the dynamic role definition
  ("the striker is the bot closest to the ball") is **rejected with
  hedging** ("could be considered… however… not necessarily"). The
  contradiction originates in the *role concept itself* → Phase 2 must
  prefer **situation-triggered position verbs** over role labels.
- **Set-piece concepts: WEAK, referee-owned.** Ball-out direction right
  but mechanics wrong; attacker-over-goal-line interpreted as a blue
  goal; kickoff wrong; corner placement hallucinated (0,-3); goal area
  hallucinated off-field. Decision: **all restart/foul mechanics are
  referee-owned** (emitted via `match_state`); LLM gets passive
  restart-awareness only.
- **Acceptance phrases:** 5 of 6 usable as-is (wing play, cross timing,
  zone-defend, shadowing, center-control); only dynamic-striker fails.
- **Contradiction baseline:** direct unambiguous question →
  contradiction-free. The 73% --explain contradiction rate is a
  *prompt-context* problem, not model incapability.

**3. Coordinate rule (probe-verified, E/F/G series) — one of the two
pillar findings:**

- E1/E2: oracle WITHOUT coordinates → model placed blue_2 ON the ball,
  blue_1 at the goal line (degenerate). With coordinates → all copied
  correctly.
- F1/F2: "stays back as deep backup" (no coords) → model moved blue_3
  FORWARD (negation inverted!).
- G1==G2: expert text adds nothing when oracle has coordinates;
  G3 (expert only): model *reasons* but produces fuzzy targets.
- **Rule:** every positional/negational verb carries explicit X,Y. The
  3B model guesses wrong without coordinates. Hybrid (Expert facts +
  Oracle coords) = quality ceiling.

**4. Test-case review + fixes** (`c3_testcase_review.md`):
P0 architecture facts (TC-05 goalie gap — oracle said "play back to the
goalie" with no bot near own goal; TC-09 offside — no offside rule
exists; TC-08/2vs2 role_diversity KPI dropped; 2vs2 v5→v6 schema
migration). P1 wording (stale roles everywhere, goalie X=-4.2, kick
direction, shot range). P2 dictionary-grounded (remove dynamic role
definitions). P3 (TC IDs, TC-10 kick_in creation). All P0/P1 fixes
applied to the 10 `analysis.md` files + scenario.json (2026-08-01
session); P2 deferred to Phase 2.

**5. TC walkthroughs (human-in-the-loop).** TC-02..05 walked with user:
Expert FIRST (facts, geometry, reachability, NO imperatives) → Oracle
second (per-bot commands, coordinates). Section semantics fixed by user:
**Expert = analyse the game state; Oracle = strategy = things
recommended to do.** Fixed order across all 10 files.

**6. Prompt-structure study V_A/V_B/V_C (33 + 4 probes)** — the second
pillar finding (`results/prompt_structure_report.md`, 376 lines):

- V_A (Oracle-only) = 9.0/11, V_C (1-2 sentence essence + Oracle) =
  9.0/11, **V_B (full Expert + Oracle) = 8.0/11 — the WORST**. Full
  expert text's positional listings *anchor* Qwen to listed numbers
  (attack_center b2 Y-copy, def_crisis b1 goal-line freeze) and its
  forward-cues leak bias (goalie_pass b2 pre-receipt sprint).
- **Fault attribution coined (8 deviations): 5× OUR FAULT (+3 minor),
  1× QWEN'S FAULT (harmless 0.25m rounding), zero model-incapability.
  The 3B is a faithful executor of coordinate-rich instructions.**
- **Output-slot anchoring (mechanism):** Qwen assigns the first
  aggressive action to the first output line (b1), regardless of who
  the Oracle names first. def_transition: pre-fix Oracle already led
  with blue_3, yet the tackle went to the goalie. Fix = list actions
  in **output order b1→b2→b3** with anchor positions.
- Worst scenarios: attack_wing (V_C b3 OOB -6.0,0.1 — bot given NO
  target extrapolates off-field), defensive_crisis (V_B b1 freezes on
  goal line).
- All 4 OUR-FAULT oracles fixed + VERIFY re-probes exact. Playbook
  §10.4 confirmed: V_A is a reliable 3B validation gate (9/11 pass in
  ≥2 of 3 structures).
- Recommendation: **V_A as standard, V_C conditional, V_B dropped.**

**7. 2vs2_default rework.** Red made active (red_1 on the ball with
free pass to red_2); blue_1/blue_2 clustered 0.5m apart; scenario.json
migrated v5→v6 schema; analysis.md completed with new two-man
goal-mouth bracket pattern (P-D6a, added to `8_C3_SOCCER_KNOWLEDGE.md`).

**8. Playbook** (`c3_scenario_generation_playbook.md`, 623 lines):
10 distilled soccer reasoning patterns (P1-P10: reachability/free-time,
out-of-reach ignorable, shooting angle, numbers advantage, anticipate
the block, pass-into-space, rebound readiness, counter-attack cover,
lane/dribble denial, press escape), 5 anti-patterns (A1-A5), section
semantics with probe evidence, vocabulary constraints, forbidden
content, validation protocol (§10), worked exemplars.

**Decisions taken:**
1. Dictionary is the authoritative vocabulary; all model-facing text
   restricted to usable entries, no role-derived instructions.
2. Coordinate rule is mandatory in every oracle/instruction.
3. Referee/restart/foul mechanics referee-owned; LLM passive awareness.
4. Oracle-first structure: V_A standard for validation.
5. Output-slot anchoring → action lists in output order.
6. Test-case P0/P1 fixes applied; P2 (dictionary rework) = Phase 2.

**Artifacts:** `c3_vocabulary_dictionary.md` · `c3_testcase_review.md` ·
`c3_scenario_generation_playbook.md` · `results/prompt_structure_report.md`
· `tools/vocab_probe.py` · `experiments/phase1_probes/{a-g}_series.jsonl` ·
`experiments/prompt_structure/{gen_battery.py,vA,vB,vC,verify_fixed}.jsonl`
· `results/vocab_probe_log.md` (56+ probes) · 10 `analysis.md` fixes +
2vs2 rework · changelog entries 2026-08-01.

### Phase L — 2026-08-01: Fragment migration (committed d115503)

**Goal.** Rewrite all model-facing prompt fragments in dictionary
vocabulary. Pure content migration — no structural experiments (that is
Phase F). Scope: 22 files in `core/src/strategy/fragments/`.

**Key changes:**
- `rules_core.txt`: fixed the dynamic-goalie/static-role contradiction
  (C2_striker_rule) — removed derived role definitions, situation-triggered
  position verbs instead.
- `samples_2vs2.txt`: prose examples → structured coordinate form;
  `samples_recover.txt`: cleaned template (no prose).
- All `rules_<mode>.txt` / `samples_<mode>.txt` / game-phase
  `rules_*.txt`: vocabulary sweep (dictionary-usable entries only, no
  striker/passer/supporter).
- `header.txt` EXCLUDED (fixed template, `{{EXPLAIN_INSTRUCTION}}` only).

**Rules enforced:** coordinate rule (every positional/negational verb
carries X,Y); vocabulary restricted to dictionary-usable; no ROS2K
meta-knowledge in model-facing text (AGENTS.md rule).

**Verification:** `tools/dump_prompt.py` token diff before/after (+5 chars
across 21 files, ~591 tokens 3vs3 prompt); 3B spot-probes LVERIFY_1/2
(closest-bot, midfield, GOAL LINE COVER fired, in-bounds); pytest fast
suite (92 passed).

**Artifacts:** 22 dictionary-compliant fragment files; commit d115503.

### Phase I — 2026-08-01: Transform builder (committed 2026-08-01)

**Goal.** Replace the JSON `min_ents` world encoding in `r2k_evaluator.py`
with a condensed TEXT transform in dictionary vocabulary (~250 tok cap).
This is the "inter-lingua" at the input side: `blue_1 at (x, y)`, ball,
score, status, velocity — rich fact tiers from `8_C3_SOCCER_KNOWLEDGE.md`
patterns (P1-P10) where cheap.

**Method:**
- Content-hash skip now hashes the TRANSFORMED text (not the JSON).
- Output format locked: `blue_1 move to (2.2, 0.3)`, one line per bot,
  regex parse + JSON-style fallback (extended `parse_code`).
- `num_predict` no-explain 150→~200; explain keeps ANALYSIS/ORACLE,
  600.
- Env-gated `R2K_TEXT_MODE=1`.

**I3 battery (20 situations, dual JSON vs TEXT, 3 iterations of fixes):**

| Metric | JSON | TEXT |
|---|---|---|
| Parse OK | 20/20 | 20/20 |
| Full coverage (one line per bot) | 18/20 | 20/20 |
| Latency p50 | 928ms | 443ms (−52%) |
| User-prompt tokens | ~48 | ~90 |

**Key fixes found during the battery (4):**
1. **Example-copy bug:** literal example coords (`move to (2.2, 0.3)`)
   were echoed verbatim → `X, Y` placeholders + "Do NOT copy example
   coordinates" law.
2. **Coverage bug:** model emitted 1 line or repeated a bot → "ONE LINE
   PER BOT — never use the same bot twice" law + "Command: blue_1,
   blue_2, blue_3" enumeration in the user payload.
3. **Restart singularity:** game-phase fragments described only the
   restart bot → "Output one line for every other blue bot too" appended
   to all 4 game-phase fragments.
4. **`hold position` verb added** (dictionary-usable): 4th valid output
   line → `{"action": "Hold"}`, bridge skips movement (new `action ==
   'hold'` branch in `ollama_sandbox_bridge.py`).

**Implementation:** `r2k_evaluator.py` (TEXT_MODE, TEXT_OUTPUT_HEADER,
TEXT_EXPLAIN_INSTRUCTION, `_build_text_world()`, `_clean_text_samples()`,
`text_parse()` regex → assignments + JSON fallback, content-hash on
transformed text, `world_text` in trace); `rules_core_text.txt` (NEW,
VALID OUTPUT LINES + STRICT LAWS); game-phase fragment ONE-LINE-PER-BOT
append; bridge `hold` branch; `tests/test_text_mode.py` (21 tests);
`tools/i3_battery.py` (dual probe battery).

**Note:** temperature 0.0 not bit-exact across KV-cache states — single-run
battery numbers directional, not exact; text latency advantage (short
output) robust.

**Artifacts:** transform implementation + battery results; commit
2026-08-01.

### Phase K — 2026-08-02: Behavior battery (the decision phase)

**Goal.** The experiment that decides whether the inter-lingua works:
dual A/B of current JSON-in/JSON-out vs transformed-text-in/
condensed-text-out, judged by `parse_success`, `vocab_compliance`,
`rule_following`, `contradiction_score`, `role_coverage` + human review.
K4 gate: candidate must close ≥80% of situations with a correct,
parseable, executable instruction. K5: winning config → Phase 2 + F.

**K2 — positive-information sweep (2026-08-02, 1380 probes, ~30 min).**
10 cumulative variants (V0-V9) of positive prompt content (field geometry
→ tactical principles → static roles → decision rules → positive
constraints → output vocabulary → spacing → score/status), dual
TEXT/JSON, n=3, 23-situation corpus.

| Variant | TEXT hard% (score) | JSON hard% (score) |
|---|---|---|
| **v0 (base)** | **100% (76.7)** | 46% (74.2) |
| v1 (+geometry) | 90% (71.7) | 43% (78.8) |
| v2 (+principles) | 65% (65.1) | 67% (77.2) |
| v3 (+roles) | 65% (71.3) | **96% (82.6)** |
| v4 (+decision rules) | 81% (74.6) | 96% (83.5) |
| v5 (+positive constraints) | 77% (72.5) | 96% (84.2) |
| v6 (+output vocabulary) | 62% (69.0) | 94% (82.2) |
| v7 (+spacing) | 70% (73.4) | 96% (83.3) |
| v9 (full) | 67% (71.7) | 96% (83.1) |

**Verdicts:**
- **TEXT (production priority): v0 (current fragments) wins.** Every
  added block reduces hard-pass (100% → 62% at v6). Positive lengthening
  dilutes the 3B model's focus. Latency lowest at v0 (396ms vs 508ms).
- **JSON (fallback): the V3 ROLES block is the only content that
  matters** — hard% jumps 46→96% and holds. If JSON ever returns, adopt
  V3's static-role block (≤1 goalie, never derive roles from positions).
- **Phantom bots persist structurally in JSON** (4% on ALL variants) —
  output-slot anchoring, not fixable by rule content.
- **Conclusion: positive-information lengthening hypothesis REJECTED
  for TEXT mode.** K2 gate already passed by v0 TEXT (100% hard-pass).

**K3 — per-gap rule-vs-example tests (2026-08-02, 7 variants × 26
situations × 2 encodings × 3 repeats).** Two new situations authored
from observed match gaps: `competition_ball` (two blue bots equidistant
on ball, red pressing — double-chase standoff) and `free_man_pass`
(unmarked blue_2 at (4.0,0.8), red pressing the carrier). New gap
diagnostics: `gap_competition` (exactly ONE ball-targeter) and
`gap_pass` (kick present AND ≥1 non-kicker forward target).

| Variant | gapC | gapP | Channel |
|---|---|---|---|
| v0 (baseline) | 0/3 | 0/3 | K2 header only |
| k3a_rule | 2/3 | 0/3 | rules_3vs3.txt |
| k3b_example | 0/3 | 0/3 | samples_3vs3.txt |
| k3c_header | 0/3 | 0/3 | header rules only |
| k3f_header2 | 3/5 | 4/5 | + PASS EXAMPLE |
| k3g_combined | 0/5 | 2/5 | rules file + header (overload) |
| **k3h_ownhalf** | **3/3** | **3/3** | PASS RULE gated X>0 |

**Findings:**
1. Competition split needs a **RULE** (2/3 rule vs 0/3 example); model
   default = double-chase standoff.
2. Pass needs an **EXAMPLE**, not just a rule — rule alone fixes the
   kicker (wrong-bot kick was the real v0 failure) but the receiver
   never runs forward.
3. **PASS RULE gated to opponent half (X>0)** — ungated it fires in
   defensive situations and pushes bots forward wrongly.
4. Combining rule-file + header regresses (k3g) — **one channel only**.
5. Output-slot anchoring reproduces: kick on output line 2 when line 1
   is a Move → wrong-bot kick.

**Regression (n=3):** v0 TEXT 96.2% hard / 76.4 / gapC 30.8% / gapP 3.8%
→ **k3h 93.6% / 75.5 / 60.3% / 70.5%**. Hard-gate dip = phantom-bot
lines in 1vs1/2vs1 (PASS EXAMPLE reinforces 3-line structure) — accepted,
real matches are 3vs3.

**Wire-in:** k3h winner (KICK RULE + SPLIT RULE + PASS RULE gated X>0 +
PASS EXAMPLE) is now part of `TEXT_OUTPUT_HEADER` in
`r2k_evaluator.py:63-88` — the live prompt splits contested balls and
passes to free men. KB gained P-C2a (competition split) + P-A3b (pass to
the free man) in `8_C3_SOCCER_KNOWLEDGE.md`. K4 gate passed.

**Artifacts:** `results/k3_results.md` · `results/sweep_positive_prompts_report.md`
· `experiments/k3_{rule,example}/fragments/` · `experiments/k3_header/`
· `results/i3_sweep_k3{v0,a,b,c,f,g,h}*` · `results/i3_sweep_v{0..9}*` ·
`tests/test_i3_sweep.py` (22 tests).
### Phase F — 2026-08-02: Few-shot paradigm rework (structure + content sweep)

**Goal.** Find the prompt structure that makes the 3B model produce the
best instruction sequences — no Gazebo, pure LLM text-output analysis
with synthetic world data. Decision point resolved with user: F4 = content
sweep on F0 structure; F3 re-run with fixed metrics approved.

**F1 tooling (new):**
- `tools/llm_probe.py` (~540 lines): config registry F0-F4, 9 text
  metrics, semantic (canonicalized-parsed-assignment) determinism
  comparison, `--config/--corpus/--model/--repeat/--tag/--only/
  --frag-dir/--list-configs`. Header variants: `explain_full`,
  `explain_oracle`, `explain_analysis`, `explain_k3h` (+K3 rules via
  `_k3_rules_section()`), `full_nok3h`. Explain detection now
  header-name-derived (`is_explain_style()`).
- `tools/build_corpus.py`: `tests/synthetic_worldstates/corpus.jsonl` —
  **81 states** = 26 battery + 10 hand-crafted edge cases + 45 trace
  frames. Statuses: kickoff 3 / playing 62 / ball_out 10 / goal_kick 2 /
  corner_kick_in 2 / goal 1 / foul_penalty 1.
- `experiments/f_structure/fragments/`: `rules_core_min.txt` + interwoven
  samples `samples_interwoven_{1,3vs3,6}.txt` (ORACLE rewritten as pure
  prose after smoke 1 — "blue_N will move to (X,Y)" collided with the
  ASSISTANT command format).
- `experiments/f4_content/fragments/`: `samples_3vs3_{1,6}.txt`
  (json_blocks format, 1/6 examples — F0's production sample already has 1).

**Explain-mode kick gap fixed (pre-F3 blocker):** explain mode used
`TEXT_EXPLAIN_INSTRUCTION` which had NO K3 rules (they live only in
`TEXT_OUTPUT_HEADER`). `free_man_pass` collapsed (code=2 failures).
Fix: `explain_k3h` header variant → free_man_pass code 2→0, score 0→90.
K3 rules are load-bearing in the user prompt; interwoven samples alone
are not enough.

**Metric fixes mid-sweep:** `i3_battery.py` `text_parse_relaxed()` never
captured ANALYSIS/ORACLE prose → added `PROSE_MARKER_RE`/
`PROSE_MAX_CHARS` (analysisQ/oracleQ/contradiction were 0.00 everywhere).
`llm_probe.py` `compute_continue_accuracy()` compared raw response
strings (0-6% — temp 0.0 is not bit-exact across KV-cache states) →
now compares canonicalized parsed assignments semantically. Records now
store `assignments` for re-scoring.

**F3 structure sweep (972 probes, 13.6 min, 4 configs × 81 × 3):**

| Config | hard% | parse% | score | vocab | ruleF | cov | analysisQ | oracleQ | continue | lat p50 |
|---|---|---|---|---|---|---|---|---|---|---|
| **F0** (global rules + separate samples) | **93%** | **100%** | **64.8** | **1.00** | **0.97** | **1.00** | 0.00¹ | 0.00¹ | 5% | **217ms** |
| F1 (min rules + interwoven) | 62% | 84% | 57.4 | 0.83 | 0.76 | 0.77 | 0.83 | 0.83 | 14% | 932ms |
| F2 (no global, interwoven only) | 56% | 83% | 56.9 | 0.83 | 0.75 | 0.73 | 0.73 | 0.77 | 18% | 978ms |
| F3 (axioms + interwoven, explain) | 81% | 90% | 64.5 | 0.91 | 0.88 | 0.90 | 0.90 | 0.91 | 7% | 939ms |

¹F0 non-explain produces no prose — 0.00 correct, not a metric gap.

**Verdict: interwoven paradigm loses decisively.** The 3B model extracts
rules from global declarative text + separate samples far better than
from inline commentary. Explain mode: +4.3× latency (217 vs ~940ms) for
prose the bridge never consumes.

**F4 content sweep on F0 (1215 probes, 6.8 min, 5 configs × 81 × 3):**

| Config | hard% | parse% | score | ruleF | cov | gapC | gapP | lat p50 |
|---|---|---|---|---|---|---|---|---|
| F0 (1 sample, k3h header) | 94% | 100% | 64.4 | 0.98 | 1.02 | 3/3 | 2/3 | 216ms |
| **F4_s1** (1 sample, explicit) | **98%** | 100% | 64.6 | 0.99 | 1.02 | 3/3 | 3/3 | 221ms |
| F4_s6 (6 samples) | 96% | 100% | 64.1 | 0.99 | 1.02 | 2/3 | 3/3 | 221ms |
| F4_nok3h (no K3 header rules) | 93% | 100% | **69.9** | 0.98 | 1.03 | **0/3** | **0/3** | 269ms |
| F4_explain (F0 + explain header) | **56%** | 97% | 59.0 | 0.97 | 0.83 | 1/3 | 0/3 | 691ms |

**F4 findings:**
1. **1 sample is sufficient** (F4_s1 98% hard, all gaps — B-study RQ2
   replication). 6 samples add nothing.
2. **K3 rules are load-bearing**: F4_nok3h scores HIGHER on the soft
   metric (69.9 — scorer rewards Hold over Kick) but loses EVERY gap
   (0/3, 0/3). The soft score rewards passivity; gap diagnostics capture
   soccer semantics. K3 header rules stay.
3. **Explain mode on F0 is catastrophic** (56% hard, cov 0.79, 691ms) —
   prose crowds out commands. Explain = display-only.
4. **Phantom-bot emission** (K4, known): 1-bot situations get 3-line
   outputs from sample-structure copying — 100% hard-fail in every
   config. Real matches are 3vs3; low priority.
5. `foul_penalty` has no game-phase fragment (falls back to mode rules) —
   model ignores red_2 on the ball, kicks from 7m. Low priority (fouls
   are referee-owned).

**Phase F verdict: F0 structure as-is is the optimum.** Global
rules_core_text + rules_3vs3 + 1 separate json sample + k3h header,
non-explain. Current production prompt needs NO fragment changes.
Semantic determinism at temp 0.0: continue 2-18% — confirms the
2026-08-01 KV-cache finding; identical-input determinism is NOT
bit-exact.

**Tests:** all 147 fast tests pass after metric fixes (147 passed, 11
skipped).

**Artifacts:** `results/probe_f3_structure_{raw.jsonl,_report.md}` ·
`results/probe_f4_content_{raw.jsonl,_report.md}` · `results/probe_smoke_f3{c,d}*`
· `tests/synthetic_worldstates/corpus.jsonl` · plan doc Phase F marked
DONE with full result block · changelog entry 2026-08-02.
