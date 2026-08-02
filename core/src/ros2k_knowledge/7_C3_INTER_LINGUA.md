---
id: 7_C3_INTER_LINGUA
title: "Section 7: C3 Inter-Lingua & Scenario Authoring (V6.3)"
type: KNOWLEDGE_BASE_POWER_FILE
tags: [c3, inter-lingua, controlled-vocabulary, expert-oracle, coordinate-rule, scenario-generation, analysis-md, test-cases, vocabulary, playbook, qwen2.5, position-verbs, soccer-knowledge, v6.3, c3-phase1, c3-phase2]
last_modified: 2026-08-01
version: v6.3
---
# Section 7: C3 Inter-Lingua & Scenario Authoring

> [!abstract] LLM Context Anchor
> **CRITICAL AXIOMS FOR RAG RETRIEVAL:**
> 1. **Inter-Lingua Paradigm:** C3 replaces prompt hacks with a controlled vocabulary. The LLM outputs situation-triggered *position verbs* with explicit coordinates, NOT derived role labels. There is NO rule-based mapper in the bridge — the LLM's instruction sentences drive behavior directly.
> 2. **Semantic Split (corrected 2026-08-01):** In every scenario `analysis.md`, **Expert = analyse the game state** (facts, geometry, angles, reachability, NUMBERS, no imperatives) and **Oracle = things recommended to do** (per-bot commands). **Expert section comes FIRST, Oracle second** — fixed order, all 10 files.
> 3. **Coordinate Rule (probe-verified):** Every positional/negational verb in model-facing text MUST carry explicit X,Y. Qwen2.5:3B guesses wrong without coordinates (E-series: bot placed ON ball for "open space on the wing"; F-series: negation inverted, "stays back" → bot moved FORWARD).
> 4. **Authoritative Docs:** The three `core/docs/c3_*.md` files (dictionary, testcase review, generation playbook) are the source of detail. This power-file is the retrieval anchor; the playbook §11 holds validated exemplars.

## 1. The Inter-Lingua Paradigm

The core problem (Phase 1 finding): the 3B model cannot be steered by semantic roles
("striker", "passer") because (a) it inherits static human-soccer semantics that
contradict our dynamic role definitions, and (b) the exact "contradictive
argumentation" (C2_striker_rule probe: "could be considered... but not necessarily")
originates in the role concept itself. The inter-lingua removes derived role labels
from instructions and replaces them with **situation-triggered position verbs**:

- The LLM states WHAT to do as an instruction sentence, not as a role assignment.
- Coordinates are the ground of communication — every positional verb carries them.
- Referee/restart/foul mechanics are NOT the LLM's job (referee-owned, see §5).
- No new bridge mapper was introduced (corrected framing, 2026-07-31): the LLM
  outputs instruction sentences directly; the existing flat-JSON strategy
  (assignments with role + target X,Y) is the transport.

## 2. Expert vs Oracle Semantics (the core correction)

| Section | Role | Content rules | Probe evidence |
|---|---|---|---|
| **Expert (technical)** | Analyse the game state | Facts only: positions, geometry, angles, reachability, numbers advantage. **NO imperatives** ("should", "must"). Every referenced entity gets its X,Y. | G3: expert-only probe → model *reasoned* (corrected blue_3 toward goal area) but fuzzy targets |
| **Oracle (strategic)** | Things recommended to do | Per-bot commands. **Every positional/negational verb carries explicit X,Y.** | E2/F2: with coords → exact copy; E1/F1: without → degenerate/inverted |

- **Order:** Expert FIRST, Oracle second (Expert is logically prior — it states the
  facts the Oracle acts on). Applied across all 10 `analysis.md` files (2026-08-01).
- **Hybrid ceiling:** G1==G2 (expert adds nothing when oracle already has coords);
  G3 (expert-only) reasons but lacks precision. → The **hybrid** (Expert facts +
  Oracle coords) is the quality ceiling for the 3B validation probe.
- **Model-facing boundary:** `analysis.md` is currently NOT injected into the real
  ROS2K prompt (prompt = fragments only, see `3_AI_LOGIC` §V6.3). It is consumed by
  the human walkthrough and by the validation probe. Future C3 Phase 2/3 decides how
  analysis text reaches the model.

## 3. Coordinate Rule (probe-verified, E/F/G series)

Rule: **every positional/negational verb carries explicit X,Y. The 3B model guesses
wrong without coordinates.**

| Series | Setup | Result |
|---|---|---|
| E1 | Oracle without coords (fast_counter state) | Degenerate: blue_2 ON the ball, blue_1 at goal line |
| E2 | Same oracle with coords | All three copied correctly |
| F1 | Short oracle, "stays back as deep backup" | Negation inverted — blue_3 moved FORWARD |
| F2 | Short oracle with coords | Correct |
| G1 | Oracle only (coords) | Correct copy |
| G2 | Expert + Oracle (coords) | IDENTICAL to G1 — expert redundant when oracle has coords |
| G3 | Expert only | Emergent correction (blue_3 → goal area) but fuzzy targets |

Implication: coordinate-free prose is worse than useless — it actively misleads.
Zone nouns need explicit bounds (D1: "own half" only usable with "X from -4.5 to 0";
"opponent half" broken — model read field as 0..9).

## 4. Vocabulary Constraints

Full reference: `core/docs/c3_vocabulary_dictionary.md` (probe-derived, 56 probes).

- **Roles (only 3 valid):** goalie / attacker / defender. goalie two-mode description
  matches bridge blending (far → positioning, close → intercept). NEVER dynamic
  role definitions ("the striker is the bot closest to the ball" — REJECTED by model).
- **Usable verbs:** move to X,Y, receive pass, support run, hold position, mark X,
  clear the ball, cover the goal line / a zone, pass/shoot/cross (with target),
  kick the ball upfield. "cover a zone" usable (D3).
- **Borderline (care):** press the ball (human "use your hands" twist), chase the
  ball (lacks speed/angle), "own half" (needs explicit bound).
- **Reject:** dynamic roles, "penalty area" (we have a goal area, no box), D5 goal
  area hallucination ("X=-4.5 to -6.5" — off field), "dive" (impossible for bots),
  corner placement (D4 hallucinated flags at (0,-3)/(9,-3); actual ±4.5/±3.0).

## 5. Referee-Owned Concepts (passive awareness only)

All restart/foul mechanics are the referee's job (`referee_node.py` via
`match_state`). The LLM gets PASSIVE awareness only — it never decides placements.

- Ball-out / kick-in: placement logic correct in model terms ("touchline"), but
  terminology wrong ("direct free-kick") → referee-owned.
- Attacker-over-goal-line: model interprets as a goal → referee-owned.
- Kickoff, corner placement, foul classification: all wrong/hallucinated → referee-owned.
- No throw-in exists; **kick-in** is the set piece. No offside rule in `referee_node.py`.
- Field ground truth: 9×6 (X ±4.5, Y ±3.0); goal ±0.9; goal area (±3.5, ±1.0);
  corner flags ±4.3/±2.8. Use concrete coordinates, never zones.

## 6. Distilled Soccer Reasoning Patterns (P1-P10)

Human soccer knowledge distilled in the walkthrough sessions (full text with
check/express/source-TC in `core/docs/c3_scenario_generation_playbook.md` §5):

| # | Pattern | Source TC |
|---|---|---|
| P1 | Reachability & free time — closest bot reacts; distance = maneuver time | TC-01, TC-04 |
| P2 | Out of reach = ignorable (bot can't affect the play in time) | TC-04 |
| P3 | Shooting angle — compute vs goal mouth ±0.9, not the goalie position | TC-01, TC-06 |
| P4 | Numbers advantage — local blue > local red decides press/pass | TC-01 |
| P5 | Anticipate the block — act before the opponent responds | TC-02 |
| P6 | Pass into space — receiver must take position BEFORE the pass | TC-02 |
| P7 | Rebound readiness — a non-shooting bot moves toward the box | TC-01, TC-06 |
| P8 | Counter-attack cover — a deep bot drops to mid own half (X≈-2.25) | TC-01 |
| P9 | Lane / dribble denial — cut the opponent's path, not the ball | TC-03 |
| P10 | Press escape — back-pass or hold under pressure; don't dribble into it | TC-05 |

## 7. Anti-Patterns (probe-verified failures)

| # | Anti-pattern | Evidence |
|---|---|---|
| A1 | Coordinate-free positional prose | E1, F1 (degenerate / inverted) |
| A2 | Negation without coordinates ("stays back") | F1 |
| A3 | Dynamic role definitions | C2_striker_rule (model hedges, falls back to static semantics) |
| A4 | Imperatives in Expert section | TC-01..05 pre-fix drafts |
| A5 | Model-facing referee mechanics (placements, fouls, restarts) | C-series, D2/D4/D5 |

## 8. Scenario Package Structure & Validation

- **Package layout:** `scenario/<name>/{scenario.json, field_diagram.png, analysis.md, kpi_targets.json}`.
  v6 schema (`scenario_name` / `mode` / `tactical_situation` + `entities`). Flat
  `<name>.json` still read as fallback by `setup_r2k.py` (backward compatible).
- **`analysis.md` skeleton:** `# <name> — Analysis` → `## Expert (technical)` FIRST
  → `## Oracle (strategic)` SECOND.
- **Validation protocol (playbook §10, 4 steps):**
  1. Regenerate `field_diagram.png` and byte-compare vs committed PNG (world↔diagram congruence).
  2. Grep every positional verb in analysis.md for a coordinate in the same sentence.
  3. Cross-TC consistency (no contradictory instructions between scenarios).
  4. 3B probe with the exact query format: system = "You are a soccer analyst... output
     blue_1/2/3 target X,Y positions, only the three lines"; prompt = world-state
     entities verbatim + "Tactical instruction: <Oracle>" + "Output the three target
     positions"; Ollama: `qwen2.5:3b`, temperature 0.0, num_predict 600, keep_alive 1h,
     via `tools/vocab_probe.py`. Verified: coordinates in oracle → correct copy.

## 9. Authoritative Documents (retrieve for detail)

| Topic | File |
|---|---|
| Universal soccer knowledge (Layer 1, session-distilled) | `8_C3_SOCCER_KNOWLEDGE.md` |
| Controlled vocabulary (probe-derived) | `core/docs/c3_vocabulary_dictionary.md` |
| P0/P1/P2/P3 test-case review table | `core/docs/c3_testcase_review.md` |
| Scenario generation playbook (§5 patterns, §9 anti-patterns, §10 validation, §11 exemplars) | `core/docs/c3_scenario_generation_playbook.md` |
| Raw probe evidence (56 probes, A-G series) | `core/src/results/vocab_probe_log.md` |
| Probe batteries (reproducible) | `core/src/experiments/phase1_probes/{a..g}_series.jsonl` |
| Probe tool | `core/src/tools/vocab_probe.py` |

## 10. Model & Tooling Context

- **Model:** `qwen2.5:3b` (general-purpose; qwen2.5-coder:3b rejected — corpus is 70%
  source code, soccer vocabulary out-of-distribution). Latency p50 ≈ 744-761ms full
  pipeline; conversational probe ≈ 550ms mean.
- **Validation tool:** `tools/vocab_probe.py` (thin Ollama wrapper, appends every
  probe to `results/vocab_probe_log.md`).
- **Phase status:** Phase 1 (vocabulary probing) DONE — 56 probes. Phase 2 (rework
  `analysis.md` in dictionary vocabulary) in progress. Phase F (few-shot paradigm
  rework, text-only) and Phase W (watchdog & closed-loop, text-only) follow; full
  plan in `core/docs/c3_phase0_literature_and_plan.md`.
