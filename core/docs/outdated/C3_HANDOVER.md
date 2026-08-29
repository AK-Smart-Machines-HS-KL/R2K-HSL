# C3 Handover — Inter-Lingua Approach

> **For the next opencode session.** Read this first, then read the files
> referenced at the bottom. This document is self-contained — it contains
> all decision context from the 2026-07-30/31 session.

---

## 1. Project context

ROS2K is a hybrid robotics testbed where a local LLM (Qwen2.5-Coder:3b
via Ollama) drives Gazebo-simulated and physical robots (Yahboom, Booster
K1) via flat-JSON file polling on tmpfs.

**Architecture:** 10Hz perception → cognition → execution pipeline with
deterministic referee, algorithmic red team, and LLM-driven blue team.

**The 10 axioms** (from `agent_prompt_de.txt`):
1. No OOP HALs — bridge uses dynamic thread-closures (`def task`)
2. Absolute Ground Truth — perception only from `/gazebo/model_states`
3. Decoupled Concurrency — LLM communicates via file polling, not ROS topics
4. Domain Synchronicity — all components use `ROS_DOMAIN_ID=0`
5. User-Space Ollama — must run in user-space, never as systemd service
6. Hybrid OS — U22 native, U24 Docker
7. Hardware-First Teardown — 0.2s watchdog sends Twist-zero + pkill -9
8. Suspend-Bug Diagnostics — Xid 31 MMU fault, not Python scripts
9. Strict Nomenclature — verify every filename/topic against KB
10. Zero-Tolerance for Deviations — correct wrong names immediately

**The C3 shift** (from `c3_revisited.txt`):

The project shifts from "optimize the 3B model's direct waypoint
generation" to "develop an inter-lingua approach." The 3B model is at
its capability ceiling for direct waypoint generation (confirmed
empirically, see §3). The new approach develops a brief, expressive,
semantically rich intermediate language that the 3B model,
team-captain, and human user all understand.

**The chain (a)→(d):**

- **(a) Sensing** — reliable world model (positions only,  prediction ?,
  yaw ?, past frames ?)
- **(b) Analysis** — understanding game state, rules, limitations
- **(c) Expert/Oracle** — suggesting winning strategy (seconds to minutes)
- **(d) Team-captain** — mapping strategy to physical actions

**Key innovations:**

1. **Intermediate language** — brief, expressive, semantically rich,
  understood by 3B model, team-captain, and human
2. **Remove contradictive argumentation** — no more "ball is near
  opponents goal, but also near own goal" or "prioritize defending while
  also attacking"
3. **"Continue" token** — reduce latency by having the 3B model output
  "continue" when strategy hasn't changed (goes beyond content-hash skip)
4. **Monitor C1 (goal) and C9 (prediction) interference** — why do they
  interfere?

---

## 2. Literature findings (full)

### ECoT (Zawalski et al. 2024, arxiv 2407.08693)

**Embodied Chain-of-Thought for VLA.** +28% success from **training**
(not prompting) the model to reason step-by-step.

Key findings:
- Prompt-only CoT on a 7B model gave +4pp (noise)
- The gains came from fine-tuning on synthetic CoT data
- Embodied reasoning steps (visual grounding: bounding boxes, gripper
  positions) were essential; semantic-only CoT (sub-task plans) was
  insufficient
- We can't fine-tune — so prompt-only CoT is our only option, and it
  barely works on 7B, likely worse on 3B

### "Two Calls Beat Five Agents" (Prajapati & Mohite 2026, arxiv 2607.26922)

**Multi-agent LLM pipelines on local models.** Tested on Qwen2.5-7B
(our model family, one size up).

Key findings:
- 5-agent pipeline with JSON communication DROPPED accuracy 30pp
  (75%→45%) — JSON communication fails 30-40% on 7B → error accumulation
- Two-call self-refinement beat the 5-agent pipeline (+4.2%) with 7.4×
  fewer tokens
- But self-refinement actively HARMED tasks where the model was already
  good (>90% accuracy) — it rewrote working code and introduced bugs
- **Critical finding:** "If direct accuracy <85%, self-refinement helps.
  If >90%, it costs extra but yields nothing"
- Our 3B model's accuracy is ~11% (well below 85%) — self-refinement
  could help, but the model is so bad that "check your work" may not be
  meaningful

### Orchestration gap (Galanti et al. 2026, arxiv 2607.21725)

**Separating reasoning from execution gives 4× improvement.** The paper
decomposes robot control into policy/control agent + high-level
orchestrator.

Key findings:
- The orchestrator does planning, subgoal decomposition, outcome
  tracking, failure recovery
- +4× improvement (12.8% → 53.3%) from adding orchestration on top of
  frozen policies
- The lesson: separating reasoning from execution matters more than
  scaling the reasoner
- For ROS2K: a rule-based orchestrator (verify bot reached target,
  detect failure, re-plan) could be more impactful than a bigger LLM

### VAL and World models (LeCun JEPA, DreamerV3)

**The document mentions "Le Cunn World Model" as one example.** World models
learn a predictive model of environment dynamics and use it to
forward-simulate, plan against the prediction.

Key findings:
- Most papers use learned world models (diffusion/transformer)
- For ROS2K's deterministic Gazebo physics, a lightweight analytical
  forward-sim (constant-velocity ball propagation) captures 80% of the
  value at 1% of the complexity
- C9 (future world model) was tested: no significant improvement at
  n=17 (see §3)

---

## 3. C-series experiment results (full)

### format:json confound — the single biggest methodological error

Enabled `format: "json"` for all models (to fix Phase 3 confound).
Measured impact: latency jumped from 746ms to 2081ms (+1336ms, +180%).
This suppressed offensive behavior (shots dropped 3×) and distorted
all C-series v1 results. **Reverted.** **Never use format:json with
Qwen 3B — it adds 1.8× latency with zero parse error reduction.**

### C1 (state enrichment: velocity/yaw/score)

**n=5:** goals improved 3× (0.4→1.2, p=0.037*), 40% win rate, 0 losses.
**n=17:** win rate 11.1% — the n=5 result was **noise**.

The 3B model CAN use enriched state (velocity/score awareness helps),
but the improvement is small at n=17 and doesn't translate to wins.

### C1+C9 (enrichment + prediction, n=17, 306 runs)

**Win rate: 18/153 = 11.8%** (W/D/L: 18/64/71). This is the baseline
to beat.

**Per-scenario results:**

| Scenario         | C1 W/D/L     | C1+C9 W/D/L  | C1 WR%    | C1+C9 WR% |
| ---------------- | ------------ | ------------ | --------- | --------- |
| attack_center    | 3/7/7        | 6/6/5        | 17.6%     | 35.3%     |
| attack_wing      | 3/8/6        | 1/10/6       | 17.6%     | 5.9%      |
| contain_delay    | 1/10/6       | 3/8/6        | 5.9%      | 17.6%     |
| def_transition   | 2/7/8        | 3/5/9        | 11.8%     | 17.6%     |
| defensive_crisis | 0/6/11       | 0/9/8        | 0%        | 0%        |
| fast_counter     | 1/8/8        | 3/5/9        | 5.9%      | 17.6%     |
| high_line        | 3/8/6        | 0/7/10       | 17.6%     | 0%        |
| long_shot        | 1/6/10       | 2/7/8        | 5.9%      | 11.8%     |
| pressing_trap    | 3/7/7        | 0/7/10       | 17.6%     | 0%        |
| **TOTAL**        | **17/67/69** | **18/64/71** | **11.1%** | **11.8%** |

**C9 prediction does NOT improve win rate at n=17** (11.1% vs 11.8%,
Δ=+0.7pp, n.s.). C9 helps on attack_center (+17.6pp) but hurts on
high_line (-17.6pp) and pressing_trap (-17.6pp). Effects cancel.

### C4 (temporal context: 3-snapshot history)

**Confirmed harmful.** Shots killed (18→0, p=0.014*). The 3B model
can't process 3 snapshots and still produce kick actions. Temporal
context is harmful at 3B scale regardless of latency.

### C9 (future world model: predicted positions at t+746ms)

**No significant improvement.** The LLM was already implicitly
compensating for staleness by aiming at current positions. Prediction
shifts the reference frame but doesn't add capability. Shot conversion
remains ~2% (14.4 shots → 0.3 goals) — the LLM can't kick accurately
regardless of position information quality.

### Key insight: the 3B model is a pattern copier, not a reasoner

Confirmed in the B-study: "copies one pattern; doesn't learn from
diversity." The model copies the format and content of few-shot
examples. It doesn't reason about spatial relationships, ball
trajectory, or opponent behavior. This is the core limitation that the
inter-lingua approach must address.

---

## 4. The C3 vision (from c3_revisited.txt)

### Background

**Information dimensions: the curse of modalities**
- Spatial (static, dynamic): world model
- (written) natural language: knowledge (rules, samples for expert/oracle)
- Physics: noise, jitter
- Time
- Actions: move, kick, stand (enduring or short)

**Reasoning problems**
- Frame problem: the domain is non-deterministic, heuristic reasoning
  is necessary
- Partially explorable: team red's reactions and referee decisions are
  not 100% predictable

**So information must be transformed/transduced/discretized to enhance
the small LLM's comprehension and pattern maching

### The approach

**Long term Target:** Win a 3vs3 match with Booster K1 in a real physical
environment with varying natural conditions (light, carpet).

**Improving simulator matches is a means, not the goal.** Winning is
the most important KPI.
**Short term (project) target:** optimize exploitation of a 3B model as a reasoning engine 

**The LLM chain (a)→(d) must be optimized:**

- **(a) Sensing** — reliable world model (positions only)
- **(b) Analysis** — understanding game state, rules, limitations
- **(c) Expert/Oracle** — suggesting winning strategy
- **(d) Team-captain** — mapping strategy to physical actions

**Keys:**
1. Develop a brief, expressive, semantically rich intermediate language
2. Remove contradictive/wishy-washy argumentation
3. Reduce latency with "continue" token (strategy unchanged → short
   output)
4. Monitor how C1 (goal) and C9 (prediction) interfere

### Acceptance criteria (from the document)

- Soccer tech speech is brief (it is input to 3B model)
- Specialized wordings that trigger patterns in 3B model:
  - "even formation => whoever controls the center controls the game"
  - "striker => #the bot closest to the ball"
  - "wing play => stretches the defense and creates gaps in the centre"
  - "cross reception => Crossing requires timing the Move targets"
  - "zone-defend => don't chase the ball, block passing lanes"
  - "defensive shadowing => position bots between ball and own goal"

---

## 5. Baselines to beat

| Metric           | C1 (enrich)           | C1+C9 (predict)           | C3 target                            |
| ---------------- | --------------------- | ------------------------- | ------------------------------------ |
| Win rate         | 11.1% (17/153)        | **11.8%** (18/153)        | **>11.8%**                           |
| Goals conceded   | 1.03/match            | **0.93/match**            | **<0.93**                            |
| OOB              | 9.4%                  | 11.2%                     | **<9.4%** (C3 mapper eliminates OOB) |
| Best scenario WR | 17.6% (attack_center) | **35.3%** (attack_center) | **>35.3%**                           |

**At n=17, win rate is only interpretable for large effects (>20pp
differences).** Gazebo physics variance (CV=90-129% on goals/shots/OOB)
dominates. For statistical significance, n=30+ is needed. Deterministic
Gazebo seeding would reduce n from 30 to 3 — but "setting gazebo to
deterministic gives us nothing in the end" (real-world transfer is
harder). This tension is accepted.

---

## 6. Phase plan

### Phase 0: Literature research

**Goal:** Extensive literature research on the project topics.

**Search clusters:**
1. **Intent-based robot control** — LLM outputs intent (not waypoints),
   rule-based mapper converts intent to actions. Key papers: RoboMatrix
   (skill-centric hierarchy), orchestration gap (Galanti 2026)
2. **Small model vocabulary probing** — how to systematically test what
   a 3B model understands. "Probing" is a well-established NLP technique
3. **Intermediate language / inter-lingua design** — robot command
   languages, behavior trees as intermediate representations

**Output:** Recommended methods and plan refinements.

### Phase 1: Vocabulary probing

**Goal:** Get an understanding of concepts and words Qwen 3B is capable
of. Create a dictionary (nouns, adjectives, verbs) for all next phases.

**Method:** Interactive experiments. Ask Qwen to present its vocabulary
(not extract from analysis.md — the 3B model's own vocabulary is the
reference, not human-authored descriptions).

**Key experiments:**
1. Ask Qwen 3B to list soccer-related vocabulary it knows
2. Test which words trigger correct behavior patterns
3. Test "continue" token: can Qwen reliably output "continue" vs a new
   strategy when given unchanged vs changed world states?
4. Create dictionary from Qwen's actual vocabulary (natural soccer
   language, not ROS2K jargon)

**Important:** The 3B model is a pattern copier, not a reasoner. The
dictionary words should be chosen to match Qwen's training distribution
(sports commentary, coaching texts, game analysis). Words like
"formation," "wing play," "zone-defend" are likely in the training
data. Words like "phantom kick," "PID controller," "tmpfs" are NOT.

### Phase 2: Rework test case descriptions

**Goal:** Rework `core/src/scenario/*/analysis.md` according to the
new dictionary. Validate Qwen comprehends the refined descriptions.

**Method:** Pair-programming (GLM + human). No Gazebo runs needed.

**Important:** The existing `analysis.md` vocabulary is NOT a reference.
The reference is Qwen's own vocabulary (from Phase 1). We rewrite the
descriptions using Qwen's language, not human jargon.

**Include:** Translate referee rules into the intermediate language.
The reference for referee rules is the ROS2K Python code
(`referee_node.py`, `rule_evaluator_red.py`), not RoboCup standards.
RoboCup standards are not part of this experiment.

**Validation methods:**
- Textual: ask questions about the refined descriptions
- Situational: present game state, check answers

### Phase 3: Validate detailed comprehension

**Goal:** Validate Qwen comprehends the refined descriptions in game
states, edge situations, referee decisions.

**Method:** Same as Phase 2 (textual + situational), but more detailed.

**Test:** Game states, edge situations, referee decisions. Translate
referee rules. Validate Qwen understands.

### Phase 4 (not affirmed yet): Pilot test

**Goal:** 5 Gazebo runs with the new inter-lingua. Sanity check: does
it beat 11.8% win rate?

### Phase 5 (not affirmend yet): Full evaluation

**Goal:** If pilot passes: n=30, 9 scenarios, full C3 evaluation.

---

## 7. Hard-won lessons from this session

1. **format:json is a trap.** +1336ms latency with zero benefit. Never
   use it with Qwen 3B. The parse error rate is already 0% without it.

2. **Small-sample results are noise.** C1's 40% win rate at n=5 was
   11.1% at n=17. Always use n≥17 for win rate, n≥30 for significance.

3. **The 3B model is a pattern copier, not a reasoner.** It copies
   few-shot examples verbatim. It doesn't reason about spatial
   relationships or ball trajectory. The inter-lingua must trigger
   patterns, not ask for reasoning.

4. **C1 and C9 interfere.** C1 (enrichment) helps goals. C9
   (prediction) helps positioning. Together, they cancel. The
   inter-lingua must find a way to integrate both without interference.

5. **The composite score doesn't detect goal improvements.** The
   `goal_diff_norm` divisor (10) makes a 0.8-goal improvement
   contribute only +0.024 to the composite. Win rate is the primary
   metric, not composite.

6. **U22 and U24 are now identical.** No Docker-specific env var
   passthrough. The evaluator runs the same code on both platforms.

7. **The content-hash skip makes file-mtime staleness checks
   unreliable.** `current_strategy.json` may not update for seconds
   during stable positions. Phase 5.4 failsafe must check `llm_trace`
   records, not file mtime.

8. **Gazebo physics variance dominates.** CV=90-129% on
   goals/shots/OOB. Infrastructure is perfectly reliable (latency
   CV=0.7%). All variance is Gazebo physics, not LLM.

---

## 8. Files to read in the next session

**Read first:**
- `core/docs/SESSION_CHANGELOG.md` — append-only session log (read
  the 2026-07-30/31 entries)
- `core/docs/c3_revisited.txt` — the C3 vision document
- `core/docs/optimization_spec_v6.3.md` — the full spec (1910 lines)
- `core/AGENTS.md` — architecture axioms and run/build/test commands

**Read for context:**
- `core/src/ros2k_knowledge/1_CORE_ARCHITECTURE_AND_SYNC.md` —
  architecture axioms
- `core/src/ros2k_knowledge/3_AI_LOGIC_AND_EDGE_CASES.md` — AI logic,
  failsafes, edge cases
- `core/src/ai_tactics/r2k_evaluator.py` — the current evaluator (with
  hardwired prediction)
- `core/src/ai_tactics/ollama_sandbox_bridge.py` — the current bridge
- `core/src/referee_node.py` — referee rules (for Phase 2 translation)
- `core/src/scenario/*/analysis.md` — 9 scenario descriptions (to be
  reworked in Phase 2)

**Read for baselines:**
- `core/src/results/baselines.log` — the baseline run log
- `core/src/results/kpis_C1_3vs3_*.json` — C1 baseline KPI files (153)
- `core/src/results/kpis_C1C9_3vs3_*.json` — C1+C9 baseline KPI files
  (153)

**Tools available:**
- `core/src/tools/analyze_trace.py` — offline KPI computation (with
  `--stats` flag for Mann-Whitney U)
- `core/src/tools/run_c_series.sh` — C-series experiment runner
- `core/src/tools/run_baselines.sh` — solid baseline runner
- `core/src/tools/dump_prompt.py` — dry-run prompt inspector