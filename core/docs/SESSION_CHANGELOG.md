# Session Changelog

> [!info] Purpose
> Append-only log for cross-session continuity. Read this first after a reboot
> to pick up where the last session left off. This is NOT a RAG knowledge file —
> it is project memory for the human and the next opencode session.
>
> **After reading this:** consult `core/AGENTS.md` for run/build/test commands,
> architecture axioms, and the full primary-knowledge-source list.

## 2026-07-13 — v6.1 spec update, doc cleanup, RAG knowledge base v6 migration

**Goal:** Audit v6 implementation status, update specs with checkpoints, migrate
knowledge base from v5 to v6, clean up stale files.

**Done:**

### Phase 0 verification (15 items, 1 deferred)

| # | Spec item | Verified against | Status |
|---|-----------|------------------|--------|
| 1 | Rename 1vs0_default.txt -> strat_default.txt | `strategy/strat_default.txt` exists | ✅ |
| 2 | Update setup_r2k.py strategy mapping | `setup_r2k.py:81` default=strat_aggro | ✅ |
| 3 | ollama pull cosmos | — | ⬜ deferred to Phase 3 |
| 4 | Create 7 scenario JSONs | 9 files in `scenario/3vs3_*.json` (TC-01..09) | ✅ |
| 5 | score_node.py momentum | `score_node.py:16` deque(300), :22-45 OLS+trend | ✅ |
| 6 | reward_node.py (1Hz, -10..+10, foul -1) | `reward_node.py` 6260 bytes | ✅ |
| 7 | referee_node.py fouls+ball-out+last-touch | `referee_node.py` _detect_fouls, _check_ball_out, last_toucher_frames, foul_cooldown | ✅ |
| 8 | state_aggregator.py /tactical_reward | `state_aggregator.py:13` reward_cb | ✅ |
| 9 | launch_r2k.sh --headless/--duration + reward boot | `launch_r2k.sh:48-49` flags, :236 native, :343 Docker | ✅ |
| 10 | rule_evaluator_red.py aggression | `rule_evaluator_red.py:25` AGGRESSION_FACTOR=0.15 | ✅ |
| 11 | r2k_visualizer.py momentum panel | `r2k_visualizer.py:21` momentum_history, :124-128 ax_momentum | ✅ |
| 12 | batch_evaluator.py | `ai_tactics/batch_evaluator.py` 7437 bytes, 6 CLI args (:163-174) | ✅ |
| 13 | Unit tests (momentum, reward, referee, foul) | `tests/test_momentum.py`, `test_reward.py`, `test_referee.py`, `test_foul_detection.py` | ✅ |
| 14 | Integration tests | `tests/test_integration_smoke.py` + bonus `test_kickoff_and_ballout.py` | ✅ |
| 15 | Smoke test (1x1x1x15s) | `results/eval_results_20260709_195609.json` — stub, no KPIs | ✅⚠️ |

> **Item 15 warning:** The smoke test ran but produced no KPI data
> (`elapsed_time: 0.007s`, no goals_for/avg_reward/etc. fields).
> The batch evaluator pipeline executes but does NOT yet collect ROS topic data
> into the results JSON. This must be fixed before Phase 1.

### Spec update: optimization_spec_v6.md -> v6.1

- Renamed to v6.1 (front matter, title, changelog note)
- Added Status column to management summary phase table (Phase 0 = ✅ DONE,
  Phases 1-5 = ⬜)
- Phase 0 checklist: all items marked [x] with per-item code evidence
- Phases 1-5: added `> [!warning]` checkpoint callouts (NOT STARTED / BLOCKED)
- TC-01..09 Mermaid diagrams: replaced 1D node chains with `quadrantChart`
  (true 2D X/Y field layouts, coordinates normalized from scenario JSONs)
- New Section 10a: Implementation Checkpoint Summary (17-row verification table
  mapping spec requirements to code locations)
- Section 10 (Related Files): added v6.1 Status column

### Documentation cleanup

- Deleted 3 stale files from `core/docs/`:
  - `optimization_spec_v6.md~` (pre-v6.1 backup)
  - `optimization_spec.md` (v5.1 predecessor, superseded)
  - `optimization_plan.md` (earliest draft, superseded)
- Kept `optimization_spec_v6.md` (v6.1, authoritative) and
  `spec_taktische_evaluierung.md` (German historical, added "Superseded" header)
- Deleted duplicate at `/home/r-zwei-kickers/ros2k_v5_clean/optimization_spec_v6.md`
- Applied `doc_update_v6.txt` (from USB drive plan/) to 2 user-facing docs:
  - `6_03_CHEATPAGE_CLI_Ergonomics.md`: relay JSON as single source of truth,
    new Section 5 Hardware Sync Stability Notes (hotspot reuse, uros sleep 3)
  - `4_01_INTRODUCTION_Edge_Hardware.md`: relay JSON note, uros agent delay note

### RAG knowledge base migration (v5_release -> v6_active)

Approach: Option A (section-by-section extension, no changelog file).

| File | Lines before | Lines after | What was added |
|------|-------------|-------------|----------------|
| `2_ROS2_PROTOCOLS_AND_FRAMES.md` | 130 | 190 | Foul detection (pushing 0.3m+0.5m/s+0.8m, blocking 0.5m+30deg+0.8m), sideline warp penalty, ball-out detection (debounce+hysteresis), last-touch tracking, restart logic, SPL rationale |
| `3_AI_LOGIC_AND_EDGE_CASES.md` | 114 | 188 | Momentum OLS (deque 300, cold-start gotcha), 1Hz reward node (decision vs foul code paths), red aggression (0.15), kick-in prompt iteration history (4 versions + 2 deprecated assumptions), prompt-injection protection, team-red kick-in behavior (7 steps), kick-in architecture constraints (ball reset NOT LLM, opponent displacement NOT LLM) |
| `6_DATA_SCHEMAS_AND_LIFECYCLE.md` | 140 | 300 | /match_state v6 schema (ball_out_event, restart_team, foul object), /tactical_score v6 (momentum_30s, momentum_trend), /tactical_reward schema (decision + foul examples), eval_results.json full structure, batch_evaluator CLI (6 flags) |
| `META_KNOWLEDGE_ROUTER.md` | 54 | 63 | V6 Reward Node + Batch Evaluator glossary entries, 3 new routing matrix rows for V6 keywords |

Files NOT touched (v6 did not change them): `1_CORE_ARCHITECTURE_AND_SYNC.md`,
`4_EDGE_HARDWARE_SIM2REAL.md`, `5_HYBRID_INFRASTRUCTURE_V5.md`, `ROS2K_GEM_FAQ.md`.

### File hygiene

- Renamed `agent prompt de.txt` -> `agent_prompt_de.txt` (fixes 10+ references
  that already expected underscore)
- Renamed `.ros2k_knowledge` -> `ros2k_knowledge` (fixes Obsidian dotfolder
  hiding — Obsidian cannot display folders starting with a dot)
- Updated all references in: `AGENTS.md`, `.vscode/agents.md`,
  `.vscode/continue.json.current`, `.vscode/continue.expanded.json`
- Added `core/docs/` + `core/user doc/` to `AGENTS.md` primary knowledge sources
- Deleted stale backups: `agents.md~`, `agents.md.inv`, `agents.md.org`,
  `AGENTS.md.v1`, 6 stale `.vscode/continue.json.*` variants

**Files touched (live repo ~/R2K-HSL/):**
- `core/docs/optimization_spec_v6.md` (v6.1: checkpoints + 2D TC diagrams)
- `core/docs/spec_taktische_evaluering.md` (added "Superseded" header)
- `core/AGENTS.md` (docs/ reference added, .ros2k_knowledge -> ros2k_knowledge)
- `core/src/ros2k_knowledge/2_ROS2_PROTOCOLS_AND_FRAMES.md` (v6 addendum)
- `core/src/ros2k_knowledge/3_AI_LOGIC_AND_EDGE_CASES.md` (v6 addendum)
- `core/src/ros2k_knowledge/6_DATA_SCHEMAS_AND_LIFECYCLE.md` (v6 addendum)
- `core/src/ros2k_knowledge/META_KNOWLEDGE_ROUTER.md` (v6 routing entries)
- `core/src/ros2k_knowledge/agent_prompt_de.txt` (renamed from "agent prompt de.txt")
- `core/.vscode/agents.md` (path updated)
- `core/.vscode/continue.json.current` (path updated)
- `core/.vscode/continue.expanded.json` (path updated)
- `core/user doc/rosk2_v5_technical_documentation/6_03_CHEATPAGE_CLI_Ergonomics.md` (v6)
- `core/user doc/rosk2_v5_technical_documentation/4_01_INTRODUCTION_Edge_Hardware.md` (v6)
- `core/docs/SESSION_CHANGELOG.md` (this file, created)

**Files deleted:**
- `core/docs/optimization_spec_v6.md~` (old v6 backup)
- `core/docs/optimization_spec.md` (v5.1 predecessor)
- `core/docs/optimization_plan.md` (earliest draft)
- `/home/r-zwei-kickers/ros2k_v5_clean/optimization_spec_v6.md` (duplicate)
- `core/agents.md~`, `core/agents.md.inv`, `core/agents.md.org` (3 stale backups)
- `core/AGENTS.md.v1` (stale backup)
- `core/.vscode/continue.json~`, `.backup`, `.inv`, `.nope`, `.org`, `(Copy).json` (6 stale)
- `core/user doc/4_06_SPECIFICATION_BoosterK1_Integration.md~` (v4 backup)

**Not yet done (deferred):**
- AGENTS.md not yet updated to reference SESSION_CHANGELOG.md (will do this session)
- USB drive (SSK Drive) plan/ files not copied into repo — protokol5.html and
  auto_ref_und_kick_specs.txt contain kick-in lessons + SPL referee rationale
  that was EXTRACTED into the knowledge base, but the source files themselves
  are still only on the USB drive
- User docs (rosk2_v5_technical_documentation/) not updated for v6 (only 2 files
  updated: 4_01 and 6_03. Remaining 33 files still v5_release.)

**Next:**
- Phase 1 baseline (81 runs) — requires live Ollama + Gazebo, ~1.5h compute
- Verify batch_evaluator.py actually collects KPIs (stub run had none — see
  item 15 warning above)
- Optionally: copy protokol5.html + auto_ref_und_kick_specs.txt into core/docs/
  as reference material

**Blockers:**
- Ollama not reachable during session — verify before Phase 1
- batch_evaluator.py may not subscribe to ROS topics for KPI collection
  (smoke test stub had elapsed_time 0.007s, no KPI fields)

## 2026-07-14 — Unified set-piece rules, referee panel text overhaul, visualizer blitting refactor

**Goal:** Complete the unified set-piece implementation (goal kick, corner kick-in,
kickoff countdown), fix referee panel display text for clarity and consistency,
and refactor the visualizer from full-rebuild to blitted artist updates to
eliminate >1s display latency.

**Done:**

### Unified set-piece logic (referee_node.py)
- Added `SET_PIECE_COUNTDOWN = 5.0`, `GOAL_AREA_X = 3.5`, `GOAL_AREA_Y = 1.0`,
  `SET_PIECE_WARP_RADIUS = 1.5`, `WARP_AWAY_DISTANCE = 2.0` (referee_node.py:57-62)
- New `_start_set_piece()` — unified pattern: place ball → warp nearby opponents
  → freeze opponent team → 5s countdown → status (referee_node.py:510-520)
- New `_goal_area_corner()` — ball at (±3.5, ±1.0) for goal kicks (referee_node.py:476-480)
- New `_corner_flag_position()` — ball at (±4.3, ±2.8) for corner kick-ins
  (referee_node.py:482-486)
- New `_warp_opponents_away()` — opponents within 1.5m warped 2m radially
  (referee_node.py:488-501)
- New `_freeze_team()` — freeze all bots on a team for N seconds
  (referee_node.py:503-508)
- Goal-line out classification: Scenario A (attacker over defender's line →
  goal kick) vs Scenario B (defender over own line → corner kick-in)
  (referee_node.py:388-411)
- Kickoff semantics flipped: scoring team frozen 5s (was: conceding team
  frozen 3s) (referee_node.py:164-184)
- No-toucher sideline fallback: `restart_team = "blue" if ball['x'] < 0 else "red"`
  (was: always "blue" — bug) (referee_node.py:367)
- Blocking foul penalty label: `"own_goal_warp"` → `"own_half_warp"`
  (referee_node.py:334)

### Red evaluator sync (rule_evaluator_red.py)
- Added `goal_kick_for_red/against_red`, `corner_kick_in_for_red/against_red`
  context flags (rule_evaluator_red.py:71-74)
- Fixed `red_scored` vs `red_conceded` bug: was using `last_blue_score` for
  red freeze decision, now tracks `last_red_score` (rule_evaluator_red.py:57-75)
- Set-piece behavior override: red plays defensively when blue has restart,
  approaches ball from behind when red has restart (rule_evaluator_red.py:228-234)

### Blue prompt — 3vs3 rewrite (strategy/strat_aggro.txt)
- Switched from 2vs2 (`blue_1, blue_2`) to 3vs3 (`blue_1, blue_2, blue_3`)
- Anti-clustering samples, dynamic goalie tracking, midfield passing examples
- NOTE: `rules_core.txt` and `samples_3vs3.txt` still have NO set-piece
  rules text — blue LLM is unaware of set-piece statuses (deferred, see below)
- NOTE: `r2k_evaluator.py:60` strips `match_state` from the prompt — blue
  LLM never sees referee status at all (deferred)

### Referee panel display overhaul (r2k_visualizer.py)
- "RESTART" → "KICK-IN" → merged into BALL OUT row as
  `BALL OUT: {offender} kick-in {team}` or `BALL OUT: sideline kick-in {team}`
- "PENALTY" rows removed entirely (Gazebo implementation detail, not referee
  speech)
- "BLOCKING_WITHOUT_BALL" → "BLOCK" (fits panel width)
- "own goal warp" → removed (no goal was scored; was misleading)
- Kickoff: `KICKOFF: {conceding_team}` (was: `KICKOFF: {scoring_team} frozen 5s`)
- Kickoff popup: `KICKOFF Red` (was: `🥅 KICKOFF` + "Scoring team frozen"
  subtitle, fontsize 14 → 12, emoji removed)
- Panel title: `Referee Decisions` (was: `⚖️ REFEREE DECISIONS`)
- HUD: `Match: Blue 1 : 0 Red` (was: `MATCH: BLUE 1 : 0 RED`)
- Team names: `Red`/`Blue` (capitalized, not ALL CAPS)
- Event labels: CAPS, no hyphens, no spaces within label
- `clip_on=True` added to event detail text
- Row spacing: 0.16 → 0.14 (fits ~6-7 rows instead of 5-6)
- Blanket `except: pass` at render call → `except Exception as e: print(...)`
- Dead code removed: `if foul_type == 'ball_out'` branch inside `foul_penalty`
  guard was unreachable (ball-out uses `ball_out` status, not `foul_penalty`)

### Visualizer blitting refactor (r2k_visualizer.py — full rewrite)
- Eliminated `fig.clf()` full-rebuild per frame
- New `init_figure()` — creates all axes, static elements (pitch, panel
  backgrounds, titles, legends), and empty dynamic artists ONCE (22 artists)
- New `update_figure()` — updates existing artist data via `set_offsets()`,
  `set_text()`, `set_position()`, `set_visible()`, `set_data()`, `set_color()`
- Bot positions: `scatter.set_offsets()` instead of re-plotting
- Bot labels: 6 pre-created text artists, show/hide + update
- Arrows: 6 pre-created annotations, show/hide + update
- HUD texts: `set_text()` + `set_color()` on 4 fig.text artists
- AI analysis: `set_text()` on 1 text artist
- Referee rows: 8 pre-created row triplets (timestamp/type/detail)
- Kickoff popup: 1 text artist, show/hide + `set_text()`
- Momentum: line via `set_data()`, fills removed+redrawn on small axes,
  markers via `set_offsets()` + `set_color()`
- `plt.pause(0.04)` → `plt.pause(0.01)` (40ms → 10ms loop yield)
- `rclpy.spin_once(timeout_sec=0.01)` → `timeout_sec=0.001` (10ms → 1ms)
- Expected: 200-500ms/frame → 10-30ms/frame (~2-5 FPS → ~30+ FPS)
- `draw_empty_pitch()` function removed (no longer needed)

### Tests
- `test_set_piece.py` (NEW, untracked): goal area corner, corner flag
  position, goal-line out classification (Scenario A/B), warp-opponents-away,
  set-piece countdown, kickoff scoring team, status type distinctness (314 lines)
- `test_kickoff_and_ballout.py` updated: scoring-team-frozen semantics,
  5s countdown, test names updated
- All 62 tests pass (`pytest tests/test_set_piece.py tests/test_kickoff_and_ballout.py tests/test_foul_detection.py -v`)

**Files touched:**
- core/src/r2k_visualizer.py (full rewrite: blitting refactor + display text overhaul)
- core/src/referee_node.py (unified set-piece logic, no-toucher fix, penalty label rename)
- core/src/rule_evaluator_red.py (set-piece context flags, red_scored fix)
- core/src/strategy/strat_aggro.txt (2vs2 → 3vs3 rewrite)
- core/src/tests/test_kickoff_and_ballout.py (scoring-team-frozen semantics)
- core/docs/SESSION_CHANGELOG.md (this entry)

**New files (untracked):**
- core/src/tests/test_set_piece.py (set-piece unit tests)

**Files deleted:**
- (none)

**Not yet done:**
- Blue LLM has NO awareness of set pieces: `r2k_evaluator.py:60` strips
  `match_state` from the prompt, and `rules_core.txt` / `samples_3vs3.txt`
  have no set-piece rules text. Blue doesn't know when `status = "goal_kick"`
  / `"corner_kick_in"` / `"ball_out"` is active.
- `samples_2vs2.txt` still has stale kick-in sample (old semantics)
- No-toucher goal-line out: falls into `ball_out` status but display says
  "sideline" regardless of `out_type` (display bug — should say "goal line")
- Live countdown popup for set pieces (deferred by user — "later")
- K1 hardware freeze limitation: referee freezes via `/cmd_vel` Twist, K1
  ignores `cmd_vel` — set-piece freezes are sim-only
- `strat_aggro.txt` 2vs2→3vs3 switch: is this the new default or a separate
  experiment? Needs user decision.
- Nothing committed yet — all work is uncommitted on
  `feature/ros2k_behavior_optimization`

**Next:**
- Feed `match_state` to the blue LLM: modify `r2k_evaluator.py:60` to keep
  `match_state` in `min_ents`, add set-piece rules to `rules_core.txt` and
  a set-piece sample to `samples_3vs3.txt` / `samples_2vs2.txt`
- Then commit all work with `feature/unified-set-piece-and-visualizer-refactor`

**Blockers:**
- Ollama not reachable — verify before Phase 1 baseline (carried from 2026-07-13)
- batch_evaluator.py KPI collection still broken (carried from 2026-07-13)
- Visualizer blitting refactor not yet tested with live ROS 2 + Gazebo
  (only tested headless with stubbed rclpy)

## 2026-07-14 (continued) — Referee rulebook, team red analysis, early termination, more fixes

**Goal:** Write authoritative referee rulebook doc, analyze and improve team red
code against all referee rules, implement early restart termination on ball
touch, and fix numerous display and logic bugs found during review.

**Done:**

### Referee rulebook (core/docs/referee_rulebook.md — NEW)
- Created 700-line authoritative reference with YAML frontmatter (type: RULEBOOK,
  27 tags, v6.1)
- 13 sections: field layout (vertical ASCII art), state machine (mermaid),
  decision catalog (7 decision types), unified restart pattern, foul detection
  thresholds, last-touch tracking, tactical scoring, reward system, match score,
  freeze enforcement, published match state, visualizer event labels, decision flow
- Clickable TOC, date/version header
- Field Exit Exception section: bots may leave field up to 1.0m for restart approaches
- Early termination documented: freeze ends on restart team touch (0.3m) or 5s countdown
- Integrated into AGENTS.md primary knowledge sources, META_KNOWLEDGE_ROUTER.md
  glossary + routing matrix, referenced by 2_ROS2_PROTOCOLS_AND_FRAMES.md

### RAG knowledge base updates
- `2_ROS2_PROTOCOLS_AND_FRAMES.md`: V6 addendum fully rewritten with unified restart
  logic, own_half_warp rename, field exit exception, early termination, blitting
- `6_DATA_SCHEMAS_AND_LIFECYCLE.md`: /match_state schema updated with goal_kick,
  corner_kick_in statuses, foul penalty values, out_type field
- `META_KNOWLEDGE_ROUTER.md`: new routing entries for restart, goal kick, corner
  kick-in, blitting, referee rulebook; new glossary entry for rulebook
- `rules_core.txt`: added KICK-IN EXCEPTION rule (bots may leave field 1m for restarts)
- `AGENTS.md`: referee_rulebook.md added to primary knowledge sources

### Referee improvements (referee_node.py)
- `_kickoff_reset`: `restart_team = None` → `restart_team = "red" if scoring_team
  == "blue" else "blue"` — kickoff now explicitly tracks conceding team
- New `_end_restart()` method: clears status to playing, clears frozen_bots
  immediately, logs "BALL FREE (early)"
- New early-termination check in `pos_callback` (step 3b): if restart team's bot
  within 0.3m of ball → `_end_restart()`. Only restart team's touch counts.
- `ball_out` added to `SET_PIECE_COUNTDOWN` timeout (was `BALL_OUT_TIMEOUT=3s`,
  now 5s matching `BALL_OUT_FREEZE_TIME`)
- No-toucher fallback removed (dead code — last_toucher never decays)
- `own_goal_warp` → `own_half_warp` (penalty label rename)

### Team red improvements (rule_evaluator_red.py)
- **Critical bug fix**: `red_scored` one-shot edge detector replaced with
  `restart_team == 'blue'` check. Was: red unfroze after 1 frame because
  `red_scored` was only True on the score-change frame. Now: red stays frozen
  for full 5s during kickoff.
- P1: Boundary clamp expanded to ±1.0m during restarts (was ±0.5m). Normal
  play keeps ±0.5m. `restart_active` flag controls margin.
- P3: Removed `if name != closest_bot` — all red bots hold midfield during
  opponent restart (was: closest bot kept charging)
- P4: Added blocking avoidance — non-closest bots check if their target is
  between a blue opponent and the ball. If so, shift toward nearest sideline
  to open the goal-ward path. Shift = 0.6m - perp_dist.
- P5: `aggression_active` guarded with `not all_red_frozen` — no aggression
  during freeze
- `_check_freeze` refactored: uses `restart_team` from match_state for all
  freeze decisions (was: one-shot `red_scored` for kickoff)

### Visualizer display fixes (r2k_visualizer.py)
- "RESTART" → "KICK-IN" → merged into BALL OUT row as
  `BALL OUT: {offender} >> {team}` (was: `{offender} kick-in {team}` — too long,
  team name was clipped)
- "PENALTY" rows removed entirely (Gazebo implementation detail)
- "BLOCKING_WITHOUT_BALL" → "BLOCK" (fits panel width)
- "own goal warp" → removed (no goal was scored; was misleading)
- Kickoff: `KICKOFF: {conceding_team}` (was: scoring team frozen 5s)
- Kickoff popup: `KICKOFF Red` (was: `🥅 KICKOFF` + subtitle, emoji removed,
  fontsize 14→12)
- Panel title: `Referee Decisions` (was: `⚖️ REFEREE DECISIONS`)
- HUD: `Match: Blue 1 : 0 Red` (was: `MATCH: BLUE 1 : 0 RED`)
- Team names: `Red`/`Blue` (capitalized, not ALL CAPS)
- Event labels: CAPS, no hyphens, no spaces within label
- `clip_on=True` on event detail text
- Row spacing: 0.16 → 0.14 (fits ~6-7 rows instead of 5-6)
- Blanket `except: pass` at render call → `except Exception as e: print(...)`
- Dead code removed: unreachable `if foul_type == 'ball_out'` branch in
  foul_penalty guard

### Tests
- All 62 tests pass throughout session
- `test_set_piece.py` (NEW): set-piece logic, goal kick, corner kick-in,
  warp-opponents-away, countdown, kickoff scoring team, status types

**Files touched:**
- core/docs/referee_rulebook.md (NEW — 700-line authoritative rulebook)
- core/docs/SESSION_CHANGELOG.md (this entry)
- core/AGENTS.md (referee_rulebook.md in primary knowledge sources)
- core/src/referee_node.py (early termination, restart_team for kickoff,
  ball_out timeout, no-toucher removal, own_half_warp rename)
- core/src/rule_evaluator_red.py (freeze bug fix, P1-P5 improvements,
  _check_freeze refactor)
- core/src/r2k_visualizer.py (display text overhaul, ball_out >> team fix)
- core/src/strategy/fragments/rules_core.txt (KICK-IN EXCEPTION rule)
- core/src/ros2k_knowledge/2_ROS2_PROTOCOLS_AND_FRAMES.md (V6 addendum rewrite)
- core/src/ros2k_knowledge/6_DATA_SCHEMAS_AND_LIFECYCLE.md (match_state schema)
- core/src/ros2k_knowledge/META_KNOWLEDGE_ROUTER.md (routing + glossary)

**New files (untracked):**
- core/docs/referee_rulebook.md
- core/src/tests/test_set_piece.py

**Files deleted:**
- (none)

**Not yet done:**
- Blue LLM has NO awareness of restarts: `r2k_evaluator.py:60` strips
  `match_state` from the prompt. Blue doesn't know when `status = "goal_kick"`
  / `"corner_kick_in"` / `"ball_out"` is active. This is the #1 next step.
- `samples_2vs2.txt` still has stale kick-in sample (old semantics)
- Live countdown popup for restarts (deferred by user — "later")
- K1 hardware freeze limitation: referee freezes via `/cmd_vel` Twist, K1
  ignores `cmd_vel` — restart freezes are sim-only
- `strat_aggro.txt` 2vs2→3vs3 switch: is this the new default or a separate
  experiment? Needs user decision.
- Nothing committed yet — all work is uncommitted on
  `feature/ros2k_behavior_optimization`
- opencode TUI switched to Chinese language — check opencode config

**Next:**
- Feed `match_state` to the blue LLM: modify `r2k_evaluator.py:60` to keep
  `match_state` in `min_ents`, add restart rules to `rules_core.txt` and
  a restart sample to `samples_3vs3.txt` / `samples_2vs2.txt`
- Then commit all work with `feature/referee-rules-and-team-red-improvements`

**Blockers:**
- Ollama not reachable — verify before Phase 1 baseline (carried from 2026-07-13)
- batch_evaluator.py KPI collection still broken (carried from 2026-07-13)
- Visualizer blitting refactor not yet tested with live ROS 2 + Gazebo
  (only tested headless with stubbed rclpy)
- opencode TUI in Chinese — may need config reset or language setting

## 2026-07-15 — Prompt engineering study: Phases 0-2 (disentangle, instrument, experiment)

**Goal:** Diagnose erratic blue LLM behavior (clustering, goalie freeze, OOB,
unreflected rules), reorganize the prompt architecture, and run a bottom-up
single-variable study on how to steer Qwen2.5-Coder:3b.

### Phase 0 — Disentangle the build (structural, zero semantic change)
- Removed `strat_*.txt` build-artifact write from `setup_r2k.py:135`
- `git rm` 4 `strat_*.txt` files (build outputs, gitignored going forward)
- Deleted dead `strat_recovers.txt` (truncated, no samples)
- Fixed `samples_recover.txt` format (was 2-line malformed blob → 2 proper
  EXAMPLE/INPUT/ASSISTANT defensive-transition samples)
- Fixed `setup_r2k.py:116-118` sample-append logic: strategy-specific samples
  now override mode samples (was: both appended → contradictory signals for
  strat_recover)
- Created `tools/dump_prompt.py` — dry-run prompt inspector (no ROS/Ollama)
- Updated `test_integration_smoke.py` to check fragments/ instead of strat_*.txt
- Updated AGENTS.md (2 references to strat_*.txt)
- Verification: byte-identical prompts for strat_default and strat_aggro

### Phase 1 — Instrumentation
- LLM trace logger in `r2k_evaluator.py`: every call logged to
  `logs/llm_trace_<run_id>.jsonl` (world snapshot, raw response, parse code,
  latency, model, explain flag)
- World-state trace logger in `state_aggregator.py`: every 10Hz write logged
  to `logs/world_trace_<run_id>.jsonl` (entities, match_state, tactical_score)
- Measurement script `tools/analyze_trace.py`: computes 14 KPIs (goals,
  tactical_score_avg/final, cluster%, goalie_idle%, oob%, possession%,
  latency p50/p95/max, parse_error_rate, role_diversity, status_distribution)
- Auto-tag runs: `launch_r2k.sh` exports `R2K_RUN_ID` env var; propagated
  to Docker evaluator and state_aggregator
- B3 experiment support: `R2K_INCLUDE_MATCH_STATE` env var in r2k_evaluator.py
  optionally includes match_state in the LLM payload

### Gazebo headless optimization
- `soccer_match.launch.py`: added `headless` launch arg — `gzserver` only
  (no gzclient GUI) when `--headless` is set
- `launch_r2k.sh`: passes `headless:=true` to launch file for both native
  and Docker paths
- Synced launch file to Docker install dir via `docker run --rm -v` copy
- Expected: 30-50% faster physics-only simulation (no rendering overhead)

### Phase 2 — Experiment matrix (11 experiments × 3 runs × 120s = 33 runs)

Experiment infrastructure:
- `experiments/baseline/` — frozen snapshot of fragments/ for restore
- `experiments/B1-B7b/fragments/` — per-experiment fragment variants
- `tools/swap_fragments.sh` — swap experiment fragments, run, restore
- `tools/run_experiment.sh` — run 3 repeats with auto-analysis
- `results/experiment_matrix.md` — results template

Results summary (mean of 3 runs):

| Exp | Goals B:R | Cluster% | OOB% | Lat p50 | Roles | Key finding |
|-----|-----------|----------|------|---------|-------|-------------|
| A (baseline) | 0.7:1.0 | 15.7% | 30.6% | 827ms | 4 | High variance |
| B1 (+2 samples) | 0.7:1.7 | 6.9% | 9.3% | 834ms | 4 | Less cluster, more conceded |
| B2 (B1 no rule) | 0.7:0.3 | 17.8% | 39.8% | 825ms | 4 | Within noise |
| B3 (match_state) | 0.7:1.0 | 21.5% | 13.1% | 814ms | 4 | No improvement |
| B4a (goalie -4.0) | 0.0:0.3 | 1.6% | 19.0% | 815ms | 4 | Fewer conceded |
| B4b (goalie -4.5) | 0.0:1.0 | 6.7% | 20.2% | 811ms | 4 | Worse than -4.0 |
| B5 (--explain) | 0.3:1.3 | 24.4% | 1.9% | 1190ms | 7.7 | OOB fixed, latency +44% |
| B6a (1 sample) | 1.7:1.0 | 2.6% | 16.4% | 742ms | 4.3 | **Best scorer** |
| B6b (6 samples) | 0.3:1.7 | 18.7% | 15.2% | 792ms | 4 | Diminishing returns |
| B7a (rules only) | 0.0:2.0 | 0% | 0% | 320ms | 0 | **Total failure** |
| B7b (samples only) | 0.0:1.0 | 4.3% | 46.3% | 744ms | 3 | OOB explosion |

### Research findings

**RQ1 (rules vs. samples):** Both are necessary. Without samples (B7a),
the 3B model produces empty/degenerate JSON. Without mode rules (B7b),
bots leave the field (46% OOB). Samples provide format; rules provide
boundaries.

**RQ2 (sample-count plateau):** 1 sample (B6a) is the sweet spot.
More samples (3, 6) dilute focus and increase latency without improving
behavior. The 3B model copies one pattern; it doesn't learn from diversity.

**RQ3 (alternatives):** Explain mode (B5) reduces OOB to 1.9% via
explicit reasoning, but costs 44% latency. Adding explicit "STAY INSIDE
FIELD" text to rules may achieve similar OOB reduction without the latency
cost (to be tested in Phase 3 consolidation).

**Goalie idle is structural:** 80-100% across all experiments. Not fixable
via prompts — the bridge PD controller chases a jittery ball-Y setpoint.

**Variance is high:** Within-experiment OOB spread up to 50 percentage
points. 3 runs gives directional insight; 10+ needed for statistical
confidence.

**Files touched:**
- `.gitignore` (strat_*.txt + logs/ entries)
- `core/AGENTS.md` (strat_*.txt references updated)
- `core/launch_r2k.sh` (R2K_RUN_ID, gzserver headless, Docker env passthrough)
- `core/src/ai_tactics/r2k_evaluator.py` (trace logger, R2K_INCLUDE_MATCH_STATE)
- `core/src/state_aggregator.py` (trace logger)
- `core/src/setup_r2k.py` (removed strat_*.txt write, fixed sample-append logic)
- `core/src/strategy/fragments/samples_recover.txt` (rewritten)
- `core/src/ros2_ws/src/r2k_scenario_spawner/launch/soccer_match.launch.py` (gzserver)
- `core/src/tests/test_integration_smoke.py` (fragment-based test)
- `core/src/ros2_ws/install/.../soccer_match.launch.py` (synced via Docker)

**New files (untracked):**
- `core/src/tools/dump_prompt.py` (prompt inspector)
- `core/src/tools/analyze_trace.py` (KPI measurement)
- `core/src/tools/swap_fragments.sh` (experiment swap helper)
- `core/src/tools/run_experiment.sh` (experiment runner)
- `core/src/experiments/` (baseline + B1-B7b fragment directories)
- `core/src/results/` (KPI JSONs, prompt dumps, console logs, experiment_matrix.md)
- `core/src/logs/` (gitignored — LLM + world trace JSONL files)

**Files deleted:**
- `core/src/strategy/strat_aggro.txt` (build artifact, gitignored)
- `core/src/strategy/strat_default.txt` (build artifact, gitignored)
- `core/src/strategy/strat_recover.txt` (build artifact, gitignored)
- `core/src/strategy/strat_recovers.txt` (dead file)

**Not yet done:**
- Phase 3 (consolidated v6.1 prompt): reduce to 1 sample, add explicit
  boundary text, standardize goalie x=-4.0, default --no-explain
- C1-C5 stretch experiments (CoT, retrieval, constrained decoding,
  hierarchical, role-specific) — deferred until consolidated prompt
  results disappointing
- 10× repeats for statistical confidence on key experiments
- Blue LLM still has no set-piece awareness (B3 match_state inconclusive)

**Next:**
- Phase 3: implement consolidated v6.1 prompt (B6a-based: 1 sample +
  explicit "STAY INSIDE FIELD" text + goalie x=-4.0 + --no-explain
  default), run 3× 120s validation

**Blockers:**
- None — Ollama reachable, Gazebo headless works, instrumentation pipeline
  end-to-end verified
- Visualizer blitting refactor still untested with live ROS 2 + Gazebo
  (orthogonal to this work)

## 2026-07-15 (continued) — Knowledge base v6.1 update, v6.2 unified spec, user docs overhaul

**Goal:** Update RAG knowledge base to v6.1, write unified v6.2 optimization spec merging
all prior work, overhaul user documentation with new Section 7 (Scoring/Referee,
World Model, Tools, Prompt Architecture, Experiment Guide).

**Done:**

### RAG knowledge base update (v6_active → v6.1)

Bumped 6 power-files from `v6_active`/`v5_release` to `v6.1`. Titles updated from (V5) to (V6.1).
New content added (experiment findings excluded as transient — stayed in SESSION_CHANGELOG):

- `1_CORE_ARCHITECTURE_AND_SYNC.md`: Trace logging as third decoupled channel (append-only
  JSONL, non-blocking, why not ROS topic, R2K_RUN_ID correlation). v5_release → v6.1.
- `2_ROS2_PROTOCOLS_AND_FRAMES.md`: Content already current from 2026-07-14, tag/title
  bump only. v6_active → v6.1.
- `3_AI_LOGIC_AND_EDGE_CASES.md`: 4 new topics — prompt disentanglement (strat_*.txt
  removal, sample-override, dump_prompt.py), R2K_INCLUDE_MATCH_STATE, goalie idle
  structural limitation, team red P1-P5 (freeze bug fix, boundary clamp, blocking
  avoidance, aggression guard). v6_active → v6.1.
- `5_HYBRID_INFRASTRUCTURE_V5.md`: Headless gzserver, Docker env passthrough (R2K_RUN_ID,
  R2K_OLLAMA_MODEL via docker exec -e). v5_release → v6.1.
- `6_DATA_SCHEMAS_AND_LIFECYCLE.md`: R2K_RUN_ID lifecycle, llm_trace schema, world_trace
  schema, analyze_trace.py 14 KPI definitions, log file lifecycle. v6_active → v6.1.
- `META_KNOWLEDGE_ROUTER.md`: 4 new glossary entries (trace logger, KPI analyzer, prompt
  inspector, run ID), 3 new routing matrix rows. v6_active → v6.1.
- Not touched: `4_EDGE_HARDWARE_SIM2REAL.md` (v5_release, no v6.1 changes),
  `ROS2K_GEM_FAQ.md` (v5_release, no v6.1 changes).

### Unified v6.2 optimization spec (`core/docs/optimization_spec_v6.2.md`)

783-line spec merging v6.1 infrastructure spec + completed prompt study (Phases 0-1) +
new Phase 5 Future Work. Key decisions (user-approved):
- Phase 2 baseline: reduced 27-run (9 scenarios × consolidated prompt × 3b × 3 runs)
- Phase 3 models: pull cosmos (3b + cosmos + nemotron-4b)
- v6.1's 5 named variants (Minimalist, Role-first, etc.): dropped (B-study superseded)
- B6a vs current fragments: keep current (STAY INSIDE + goalie -4.0)

Structure: 12 sections (Management Summary, Architecture, Components, Scenarios,
Prompt Architecture, KPIs, Experiment Catalog, Phases 0-5, Run Budget, Data Format,
Related Files, Open Questions). Phases 0-1 marked DONE, Phase 2 NEXT, Phases 3-4 BLOCKED,
Phase 5 RESEARCH (10 items: Kalman, predictive model, watchdog, failsafe, dynamic prompts,
GUI, sim-to-real, opponent adaptation, temporal reasoning, active learning).

Experiment catalog: B-series DONE (11×3=33 runs), C-series stretch (5 deferred),
D-series new (8 experiments: model size, temperature, context window, dynamic prompt,
opponent adaptation, scenario ranking, temporal context, 10× confidence).

`optimization_spec_v6.md` marked as superseded with frontmatter note.

### User documentation overhaul

- Renamed folder: `rosk2_v5_technical_documentation/` → `rosk2_technical_documentation/`
- Renamed file: `2_04_ARCHITECTURE_V5_Engine_Nodes.md` → `2_04_ARCHITECTURE_Engine_Nodes.md`
- `AGENTS.md` reference updated

**Master index rewritten** (`00_MASTER_INDEX.md`, 231 lines): Fixed heredoc corruption
(duplicated content lines 47-257), added Section 7 TOC, novice reading path, 13 new
glossary entries, 5 new Q&A entries, updated Future Work (10 v6.2 research directions),
version bumped to v6.2.

**5 new Section 7 files (1,220 lines total):**
- `7_01_INTRODUCTION_Scoring_Referee_Gamestate.md` (224 lines, German): unified scoring
  (momentum, reward), referee (fouls, set-pieces, kickoff), game state schema, interaction
  flow, tradeoffs (samples, explain, goalie idle)
- `7_02_ARCHITECTURE_World_Model_Components.md` (229 lines, English): perception-cognition-
  execution pipeline, what LLM sees vs what exists, trace logging layer, ground truth axiom,
  future work
- `7_03_CHEATPAGE_Tools_and_Utils.md` (264 lines, English): dump_prompt, analyze_trace,
  swap_fragments, run_experiment, batch_evaluator, R2K_RUN_ID lifecycle, 14 KPI reference,
  experiment intro example with real B-study numbers
- `7_04_SPECIFICATION_Prompt_Architecture.md` (244 lines, English): fragment assembly,
  override logic, strat_*.txt removal, B-study findings table (RQ1-RQ3), consolidated v6.2
  prompt, goalie idle limitation, dynamic prompt selection roadmap
- `7_05_CHEATPAGE_Experiment_Guide.md` (259 lines, English): step-by-step novice guide —
  run single match, inspect KPIs, run 3-repeat experiment, compare results, run full batch,
  file locations, troubleshooting table

**12 existing files updated (v6.2 bump + v6.1 notes):**
- `1_01`: v6.2 bump, v6.1 abstract note (trace, reward, referee, momentum, headless)
- `2_01`: v6.2 bump, v6 note (new topics: /match_state, /tactical_score, /tactical_reward)
- `2_04`: **Full rewrite** (125→206 lines): added foul detection, set-pieces, momentum,
  reward node, v6.1 schema, updated mermaid topology
- `3_01`: v6.2 bump, v6.1 note (red aggression, P1-P5, trace logging)
- `3_02`: v6.2 bump, Nemotron→qwen in summary + mermaid, v6.1 note (trace, explain, match_state)
- `3_05`: v6.2 bump, v6.1 note (AGGRESSION_FACTOR, smoothstep, P1-P5, freeze bug fix)
- `3_08`: v6.2 bump, v6.1 note (strat_*.txt removed, override logic, dump_prompt.py)
- `4_01`: v6→v6.2 bump, date update
- `5_01`: v6.2 bump, v6.1 note (headless Gazebo, Docker env passthrough)
- `6_01`: **Major update** (161→280+ lines): v6 note, 4 new sections (match_state, tactical_score,
  tactical_reward schemas, trace+eval schemas)
- `6_02`: v6.2 bump, title de-versioned, v6.1 note (R2K_RUN_ID, trace lifecycle, headless)
- `6_03`: v6→v6.2 bump, title de-versioned, added --explain/--headless/--duration/--strategy/
  --model flags, R2K_RUN_ID entry

**Not updated (21 files at v5_release):** hardware docs (ESP32, K1, micro-ROS), unchanged
architecture docs (control loops, state sync, race conditions, thread spawning, coordinate
frames, optional modules, Qwen latency, blue/red failsafes, edge cases, Docker networking,
build scratch, Xid 31) — no v6.1 content to add.

**Files touched:**
- `core/docs/optimization_spec_v6.2.md` (NEW — 783 lines)
- `core/docs/optimization_spec_v6.md` (superseded note added)
- `core/src/ros2k_knowledge/1_CORE_ARCHITECTURE_AND_SYNC.md` (v6.1, trace logging section)
- `core/src/ros2k_knowledge/2_ROS2_PROTOCOLS_AND_FRAMES.md` (v6.1, tag/title bump)
- `core/src/ros2k_knowledge/3_AI_LOGIC_AND_EDGE_CASES.md` (v6.1, 4 new topics)
- `core/src/ros2k_knowledge/5_HYBRID_INFRASTRUCTURE_V5.md` (v6.1, headless + Docker env)
- `core/src/ros2k_knowledge/6_DATA_SCHEMAS_AND_LIFECYCLE.md` (v6.1, trace schemas + KPIs)
- `core/src/ros2k_knowledge/META_KNOWLEDGE_ROUTER.md` (v6.1, 4 glossary + 3 routing rows)
- `core/AGENTS.md` (folder reference updated)
- `core/user doc/rosk2_technical_documentation/00_MASTER_INDEX.md` (rewritten, 231 lines)
- `core/user doc/rosk2_technical_documentation/7_01_INTRODUCTION_Scoring_Referee_Gamestate.md` (NEW)
- `core/user doc/rosk2_technical_documentation/7_02_ARCHITECTURE_World_Model_Components.md` (NEW)
- `core/user doc/rosk2_technical_documentation/7_03_CHEATPAGE_Tools_and_Utils.md` (NEW)
- `core/user doc/rosk2_technical_documentation/7_04_SPECIFICATION_Prompt_Architecture.md` (NEW)
- `core/user doc/rosk2_technical_documentation/7_05_CHEATPAGE_Experiment_Guide.md` (NEW)
- `core/user doc/rosk2_technical_documentation/1_01_INTRODUCTION_Overall_Architecture.md` (v6.2)
- `core/user doc/rosk2_technical_documentation/2_01_INTRODUCTION_ROS2_Protocol_Stack.md` (v6.2)
- `core/user doc/rosk2_technical_documentation/2_04_ARCHITECTURE_Engine_Nodes.md` (full rewrite)
- `core/user doc/rosk2_technical_documentation/3_01_INTRODUCTION_AI_Teams_Overview.md` (v6.2)
- `core/user doc/rosk2_technical_documentation/3_02_ARCHITECTURE_TeamBlue_LLM.md` (v6.2, Nemotron→qwen)
- `core/user doc/rosk2_technical_documentation/3_05_ARCHITECTURE_TeamRed_Algorithmic.md` (v6.2)
- `core/user doc/rosk2_technical_documentation/3_08_ARCHITECTURE_Dynamic_Prompting.md` (v6.2)
- `core/user doc/rosk2_technical_documentation/4_01_INTRODUCTION_Edge_Hardware.md` (v6.2)
- `core/user doc/rosk2_technical_documentation/5_01_INTRODUCTION_Dual_OS_Topology.md` (v6.2)
- `core/user doc/rosk2_technical_documentation/6_01_SPECIFICATION_Data_Schemas.md` (major update)
- `core/user doc/rosk2_technical_documentation/6_02_CHEATPAGE_System_Lifecycle.md` (v6.2)
- `core/user doc/rosk2_technical_documentation/6_03_CHEATPAGE_CLI_Ergonomics.md` (v6.2)
- `core/docs/SESSION_CHANGELOG.md` (this entry)

**New files (untracked):**
- `core/docs/optimization_spec_v6.2.md`
- `core/user doc/rosk2_technical_documentation/7_01_INTRODUCTION_Scoring_Referee_Gamestate.md`
- `core/user doc/rosk2_technical_documentation/7_02_ARCHITECTURE_World_Model_Components.md`
- `core/user doc/rosk2_technical_documentation/7_03_CHEATPAGE_Tools_and_Utils.md`
- `core/user doc/rosk2_technical_documentation/7_04_SPECIFICATION_Prompt_Architecture.md`
- `core/user doc/rosk2_technical_documentation/7_05_CHEATPAGE_Experiment_Guide.md`

**Files deleted:**
- `core/user doc/rosk2_v5_technical_documentation/` (folder renamed, all 35 files moved)

**Not yet done:**
- 21 user docs still at v5_release (hardware + unchanged architecture docs) — by design,
  no v6.1 content to add
- `batch_evaluator.py` KPI collection still broken (Phase 2b in v6.2 spec)
- Nothing committed — all work uncommitted on `feature/ros2k_behavior_optimization`
- Visualizer blitting refactor still untested with live ROS 2 + Gazebo

**Next:**
- Phase 2 of v6.2 spec: fix `batch_evaluator.py` KPI collection (2b), then run 27-run
  baseline (2c), then identify 3 worst scenarios (2d)
- Alternatively: commit all documentation work first (separate branch from code work)

**Blockers:**
- None for documentation work — all complete
- Phase 2b (batch_evaluator fix) requires live Ollama + Gazebo to verify
- Phase 2c (27-run baseline) requires ~45min compute + working batch_evaluator

## 2026-07-16 — FAQ v6.2 audit, knowledge-base citation cleanup, os.replace consistency

**Goal:** Audit and update the RAG FAQ (`ROS2K_GEM_FAQ.md`) from v5_release to
v6.2, remove broken citation artifacts across the knowledge base, fix factual
errors against the actual codebase, and make the `os.replace`/`os.rename`
documentation consistent with the code.

**Done:**

### FAQ overhaul (`ROS2K_GEM_FAQ.md`: v5_release → v6.2, 123 → 349 lines)
- Stripped 24 dangling `[cite: 12]`/`[cite: 15]` reference artifacts (no
  bibliography existed in the repo — all `[cite: N]` were broken since v5).
- Removed 1 broken Obsidian embed `![[DOCUMENTATION]]` at Q8 (v5 artifact).
- Removed hallucinated `--debug` flag from Q1 (never existed in
  `launch_r2k.sh:28-41` — supported flags are `--scenario`, `--strategy`,
  `--model`, `--relay`, `--explain`, `--no-explain`, `--headless`, `--duration`).
- Fixed 10 factual errors verified against actual code:
  1. Q1: `--debug` flag removed (never existed)
  2. Q1: "verbre" typo (corruption of "verbose") removed with the flag
  3. Q3: tracker claim "rechnet alles in ein 2D-Raster (X, Y, Yaw)" →
     corrected: only extracts `position.x`/`position.y`, no Yaw, no
     quaternion conversion (`tracker_node.py:31-35`)
  4. Q4: `1vs1_defend` scenario → `1vs1_default` (scenario doesn't exist,
     `ls core/src/scenario/1vs1_defend.json` → not found)
  5. Q6: `/bot1/LocoApiTopicReq` → `/Kev1n/LocoApiTopicReq` (actual topic
     in `relay/hardware_mirror.json`)
  6. Q8: `os.replace` → corrected (code used `os.rename` at the time;
     subsequently fixed the code instead — see below)
  7. Q8: Mermaid diagram `Aggregated_Worldstate.json` → `Worldstate.json`
     (`state_aggregator.py:26`)
  8. Q9: stale "in V5" header removed
  9. Q10: `pkill -9 ollama` claim → corrected: watchdog kills Gazebo, ROS
     nodes, and bridge — NOT Ollama (`launch_r2k.sh:108-110`). Ollama runs
     via `nohup ollama serve` (`launch_r2k.sh:155`).
  10. Q10/Q12: `OLLAMA_NUM_PARALLEL=1`/`OLLAMA_KV_CACHE_TYPE=q8_0` were
      claimed as system-set; actually not set anywhere in `launch_r2k.sh`
      (only in `ollama.log` as user-applied env). Corrected to "optional
      user tuning". Stale "V5" references removed.
- Added Q13-Q23 (11 new Q&As in German with English technical terms):
  - Q13: Scoring (momentum OLS, reward node two code paths)
  - Q14: Set-pieces (unified restart pattern, early termination, field exit exception)
  - Q15: Foul thresholds + threshold/hysteresis/corridor/probability taxonomy
  - Q16: Trace logging + `R2K_RUN_ID` + 14 KPIs
  - Q17: B-study sample-count findings (0/1/3/6 samples, RQ1-RQ3)
  - Q18: Goalie idle structural limitation (not prompt-fixable)
  - Q19: Prompt fragment assembly + override logic + `dump_prompt.py`
  - Q20: What the LLM sees vs what's stripped (`min_ents`, `R2K_INCLUDE_MATCH_STATE`)
  - Q21: Closed-loop feedback gap (open-loop cognition, Phase 5 roadmap)
  - Q22: Threshold vs hysteresis vs corridor vs probability (4-row comparison table)
  - Q23: Multi-GPU isolated-workstation architecture (capabilities + merge problem)
- Added V6.2 axiom-tension warning to Q12: hardcoded `ROS_DOMAIN_ID=0`
  conflicts with N participants on the same LAN (workshop-relevant).

### Knowledge-base citation cleanup (`3_AI_LOGIC_AND_EDGE_CASES.md`)
- Stripped 15 dangling `[cite: 23]` reference artifacts (same broken-bibliography
  issue as the FAQ).
- Removed 4 stale v5 markers: `[NEW in v5]` (×2), `(V5)` section header,
  `v5/v6` → `v5/v6.1` historical reference.
- Bumped frontmatter v6.1 → v6.2 (title, tags, last_modified, version).
- Updated `optimization_spec_v6.md` reference → `optimization_spec_v6.2.md`
  (superseded doc).
- Knowledge base is now `[cite:]`-free (39 total artifacts removed across
  both files).

### `os.replace` consistency fix (`state_aggregator.py:56`)
- `state_aggregator.py:56`: `os.rename` → `os.replace` (one-line code change).
- Rationale: `r2k_evaluator.py:134` already uses `os.replace`. All 20+ doc
  references (AGENTS.md, knowledge base ×11, user docs ×16, docs ×4, FAQ ×3)
  claim `os.replace`. Changing the one code line to match the documented
  convention is cleaner than changing 20+ doc references.
- Both `os.rename` and `os.replace` are POSIX-atomic on the same filesystem;
  `os.replace` is the idiomatic Python choice for atomic swaps.
- All 91 tests pass after the change.

### Pre-existing dirty files committed (leftover from 2026-07-15 v6.2 overhaul)
- `docs/optimization_spec_v6.2.md`: Phase 2b TBD clarification (+7/-1) —
  adds note that `batch_evaluator.py` should wrap `analyze_trace.py` rather
  than re-implement ROS topic subscriptions.
- `user doc/.../7_05_CHEATPAGE_Experiment_Guide.md`: KPI label consistency
  ("Tac Score" → "Score") + 3 "what to look for" bullets (Goals, Score
  Avg/Final, Status Distribution) (+7/-2).

### Workshop planning (not committed — plan only)
- Drafted a 5-module workshop structure (~3.5h half-day) for team training:
  Module 1 (Scoring-Ökosystem), Module 2 (World Model), Module 3 (K1 +
  thresholds/hysteresis/corridor/probability), Module 4 (Utils/fragments),
  Module 5 (Research: prompt injection, closed-loop feedback, multi-GPU).
- Identified FAQ staleness as a workshop opportunity (FAQ was v5_release).
- Identified `ROS_DOMAIN_ID=0` axiom tension for multi-participant workshops.
- No deliverable produced yet (user deferred format decision).

**Files touched:**
- `core/src/ros2k_knowledge/ROS2K_GEM_FAQ.md` (v5_release → v6.2, +288/-56)
- `core/src/ros2k_knowledge/3_AI_LOGIC_AND_EDGE_CASES.md` (citations + v5 cleanup, +48/-...)
- `core/src/state_aggregator.py` (os.rename → os.replace, +1/-1)
- `core/docs/optimization_spec_v6.2.md` (Phase 2b TBD, +7/-1, leftover from 2026-07-15)
- `core/user doc/rosk2_technical_documentation/7_05_CHEATPAGE_Experiment_Guide.md`
  (KPI labels + bullets, +7/-2, leftover from 2026-07-15)
- `core/docs/SESSION_CHANGELOG.md` (this entry)

**Files deleted:**
- (none)

**Not yet done:**
- Workshop deliverable not produced (user deferred format decision —
  German handout doc vs. handout + experiment scripts vs. keep planning only)
- Module 5 depth not decided (conceptual + one spike vs. add per-bot LLM
  prototype vs. add merge-dashboard stub)
- `AGENTS.md:80` still says `os.replace` — now correct (code matches), but
  worth noting it was part of the consistency fix scope
- `1_CORE_ARCHITECTURE_AND_SYNC.md:89` shows `os.replace(temp_path, final_path)`
  in a code example — this was already correct and needed no change
- Workshop plan itself not committed (plan mode only, no files written)

**Next:**
- Decide workshop deliverable format and Module 5 depth, then produce the
  handout/scripts
- OR: proceed to Phase 2 of v6.2 spec (fix `batch_evaluator.py` KPI
  collection, run 27-run baseline) — orthogonal to the workshop

**Blockers:**
- Ollama reachability untested this session (no live runs attempted)
- Workshop deliverable decision pending (format + Module 5 depth)
- `batch_evaluator.py` KPI collection still broken (Phase 2b, carried from
  2026-07-13/15)
- Visualizer blitting refactor still untested with live ROS 2 + Gazebo
  (carried from 2026-07-14)

## 2026-07-20 — New-machine bootstrap: jq prerequisite fix, apt cleanup, ollama GPU fallback triage

**Goal:** Bring up R2K-HSL on a fresh Ubuntu 22.04 machine (RTX 4080). Fix the
missing-`jq` blocker in `install.sh`/`launch_r2k.sh`, clean up stale apt sources
from the new host, and triage an LLM latency regression (4000-5000ms observed
vs expected ~200-800ms).

**Done:**

### `jq` prerequisite fix (the actual launch blocker)

`launch_r2k.sh` uses `jq` in 4 places (lines 68-75) to parse the relay JSON
(`requires_hardware_sync`, `YAHBOOM_TOPIC`, `K1_TOPIC`, relay bot listing).
On a fresh U22 machine `jq` is not preinstalled, so the launch script printed
`./launch_r2k.sh: line 68: jq: command not found` for every relay read and
could not start.

- `install.sh:14` (U22 branch): added `jq` to `sudo apt install -y curl
  gnupg2 lsb-release jq`
- `install.sh:57` (U24 branch): added `jq` to `sudo apt install -y jq
  docker.io docker-buildx docker-compose-v2` — host needs it even in Docker
  mode because relay parsing at `launch_r2k.sh:68-75` runs on the host
  *before* any `docker exec`
- `launch_r2k.sh:20-23`: added preflight guard immediately after
  `UBUNTU_VERSION=$(lsb_release -rs)`:
  ```bash
  if ! command -v jq >/dev/null 2>&1; then
      echo "❌ 'jq' is required but not installed. Run: sudo apt install jq  (or rerun ./install.sh)"
      exit 1
  fi
  ```
  Exits with a helpful message instead of the raw `command not found` errors
  from each `jq` invocation.
- `AGENTS.md:28`: added one-line note under "First-time setup" that
  `install.sh` installs host prerequisites including `jq` (used by
  `launch_r2k.sh` to parse relay JSON).
- Verified: `bash -n install.sh` and `bash -n launch_r2k.sh` both pass syntax
  check. `grep -n "jq"` confirms the new lines are in place.

### Apache Arrow apt source cleanup (new-machine cruft, not R2K-HSL)

The new machine had a broken third-party apt source left over from some
other tool: `/etc/apt/sources.list.d/apache-arrow.sources` pointing at
`https://packages.apache.org/artifactory/arrow/ubuntu` with a missing GPG
key (`NO_PUBKEY 9E922B2D60E9FD1C`). This produced noisy `W:` warnings on
every `apt update` but was non-fatal (the main Ubuntu jammy archive still
worked, so `install.sh` actually completed and `jq` installed fine).

- `tools/remove_arrow_source.sh` (NEW): one-shot helper script that removes
  the broken Apache Arrow apt source and runs `apt update` to confirm clean.
  Intentionally a self-contained script (not folded into `install.sh`)
  because the Apache Arrow source was added by some other tool already on
  the machine, not by R2K-HSL — keeping the cleanup separate preserves
  clean ownership boundaries.
- Decision: did **not** add Apache Arrow cleanup to `install.sh` or AGENTS.md.
  R2K-HSL owns `install.sh`; the machine owner owns their third-party apt
  sources. Mixing the two would create a maintenance burden.
- User ran the script manually (sudo not available from opencode shell);
  apt warnings silenced.
- Also removed 5 stale opencode config backups from `~/.config/opencode/`
  (`opencode (Copy).jsonc`, `opencode.json.bck`, `opencode.jsonc`,
  `opencode.jsonc~`, `opencode.ok.json`) — leftover from previous opencode
  config iterations on this machine.

### opencode TUI clipboard fix (workflow, not code)

User reported they could not copy/paste between opencode TUI and terminal.
Root cause: `xclip`/`xsel` not installed on the new machine (X11 session,
`$XDG_SESSION_TYPE=x11`). opencode's copy keybind (`Ctrl+X` then `y`,
the `<leader>y` default) silently fails without a clipboard helper.

- Diagnosis: `command -v xclip xsel wl-copy pbcopy` returned nothing.
- Fix instruction given (user-run, sudo not available from opencode shell):
  `sudo apt install -y xclip`
- Also clarified paste-into-opencode: `Ctrl+V` is *not* the standard paste
  key in Linux terminals (it's the readline "literal next char" key and is
  intercepted by the terminal before opencode sees it). Standard paste
  keys are `Ctrl+Shift+V` (GNOME Terminal, Konsole, xterm, Alacritty,
  Kitty, WezTerm) or `Shift+Insert` (universal fallback).
- Verified via `opencode.ai/docs/keybinds/`: `input_paste` defaults to
  `ctrl+v` with `preventDefault: false`, and `messages_copy` defaults to
  `<leader>y`. Both require an OS clipboard helper to actually function on
  X11 Linux.

### Ollama GPU fallback triage (diagnosis only — fix not completed)

After the jq fix, user launched a match and reported LLM latency of
4000-5000ms. Expected on a 4080 with `qwen2.5-coder:3b` is ~200-800ms
(per `3_03_CHEATPAGE_Qwen_Latency.md` and the 2026-07-15 B-study which
measured p50 ~825ms on the same model).

Diagnosis evidence:
- `nvidia-smi` after launch showed only Xorg (293MiB), gnome-shell (81MiB),
  gzserver (7MiB), gzclient (84MiB) on the GPU. **No ollama process.**
  Total VRAM used: 383MiB. A 3B model on GPU would add ~2-4GB.
- `ollama ps` reported `qwen2.5-coder:3b  2.4 GB  100% GPU  4096  59 minutes
  from now` — **stale/lying**. The runner state claimed 100% GPU but
  nvidia-smi showed the model was not resident in VRAM.
- `ps -o pid,etime -p 12590` showed `ollama serve` had been running for
  **11 days 18 hours** (`ELAPSED 11-18:22:18`). The runner was loaded to
  GPU back on July 8 and had been sitting idle since; the driver reclaimed
  the VRAM but ollama's scheduler never noticed. Classic stale-runner
  state — new requests routed to a zombie runner that falls back to CPU.
- `journalctl -t ollama --since "1 hour ago"` returned no entries — the
  systemd journal was silent. Only old May-31 entries existed, showing the
  runner originally loaded correctly (`offloaded 37/37 layers to GPU`,
  `CUDA0 model buffer size = 1834.83 MiB`, per-request latencies 760-980ms
  — i.e. GPU was working back then).
- 47% GPU util in the post-launch `nvidia-smi` was transient (browser/
  display compositing), not the LLM.

This matches the documented "silent CPU fallback" pattern
(`5_HYBRID_INFRASTRUCTURE_V5.md` Xid 31 section,
`3_03_CHEATPAGE_Qwen_Latency.md`).

**Fix attempted but aborted:** `pkill -9 -f "ollama runner"; pkill -9 -f
"ollama serve"` — user aborted the command twice (the `pkill -9` against
ollama may have looked scary, and the shell session was non-interactive
so sudo/password prompts would have failed anyway). The fix was never
executed. **The model is still running on CPU as of session end.**

**Files touched:**
- core/install.sh (jq added to both U22 and U24 apt install lines)
- core/launch_r2k.sh (jq preflight guard at lines 20-23)
- core/AGENTS.md (jq note under First-time setup)
- core/docs/SESSION_CHANGELOG.md (this entry)

**New files (untracked):**
- core/tools/remove_arrow_source.sh (apt source cleanup helper)

**Files deleted:**
- (none in repo) — 5 stale opencode config backups removed from
  `~/.config/opencode/` outside the repo

**Not yet done:**
- **Ollama GPU restart NOT executed.** The `pkill -9` was aborted both
  attempts. User needs to restart ollama and verify GPU load. See "Next".
- No live match verified after the jq fix (latency issue blocked a real
  test). Once ollama is back on GPU, re-run a match and confirm p50
  latency drops back to ~200-800ms.
- `install.sh` / `launch_r2k.sh` / `AGENTS.md` / `tools/remove_arrow_source.sh`
  edits are **uncommitted** (still on `feature/ros2k_behavior_optimization`).
- opencode TUI was switched to Chinese language at some prior point
  (carried from 2026-07-14) — not investigated this session.

**Next:**
1. **Restart ollama on the new machine** (user must run; opencode shell is
   non-interactive and can't sudo):
   ```
   pkill -9 -f "ollama runner"; pkill -9 -f "ollama serve"; sleep 2
   nohup ollama serve > /dev/null 2>&1 &
   sleep 3
   curl -s http://127.0.0.1:11434/api/generate -d \
     '{"model":"qwen2.5-coder:3b","prompt":"hi","stream":false}' > /dev/null
   nvidia-smi
   ```
   The `nvidia-smi` at the end should now show an ollama process using
   ~2-4GB VRAM. If not, the GPU fallback will recur.
2. **Run a match** (`./launch_r2k.sh --scenario 2vs2_default --relay
   only_sim_bots`) and confirm LLM latency is back to ~200-800ms via the
   trace logger (`logs/llm_trace_<run_id>.jsonl`, see
   `6_DATA_SCHEMAS_AND_LIFECYCLE.md` §v6.1 Addendum).
3. **Commit the jq prerequisite fix** — branch suggestion:
   `feature/jq-prerequisite-fix` (separate from the larger uncommitted
   `feature/ros2k_behavior_optimization` body of work, since this is a
   small standalone infra fix that every new-machine bootstrap needs).

**Blockers:**
- **Ollama stuck on CPU** — the stale runner state was diagnosed but the
  fix (`pkill -9` + restart) was aborted and never executed. This blocks
  any live match test on the new machine until resolved.
- `batch_evaluator.py` KPI collection still broken (Phase 2b, carried from
  2026-07-13/15)
- Visualizer blitting refactor still untested with live ROS 2 + Gazebo
  (carried from 2026-07-14)

## 2026-07-21 — Machine transfer, prompt dedup, cheat page, student projects

**Goal:** Transfer opencode setup to a new U22 machine, unify the agent
prompt source across opencode/Continue/Copilot (eliminate 3-way duplication),
and produce team-facing docs (cheat page + student project descriptions).

**Done:**

### Machine transfer (opencode → U22)
- Pushed 2 unpushed commits (`a418bba`, `fb131bb`) to origin
- Pulled 1 new commit from remote (`f251147` — jq prerequisite fix from U22
  session on 2026-07-20)
- Created `opencode_takeover.tar.gz` (12 MB) at `/home/r-zwei-kickers/`:
  `~/.config/opencode/` (API keys + config), `~/.local/share/opencode/`
  (session DB + auth + snapshot). Excludes node_modules, binary, logs,
  cache, workshop drafts
- Verified no machine-specific paths in configs (all use `~/`, `127.0.0.1`,
  or HTTPS endpoints). Session DB contains historical `/home/r-zwei-kickers`
  paths in metadata only (immutable history, no runtime impact)

### Prompt source dedup (3 tools → 1 canonical source)
- `core/.github/copilot-instructions.md`: regular file → **symlink** to
  `../src/ros2k_knowledge/agent_prompt_de.txt` (was byte-identical copy, no
  sync mechanism — drift risk eliminated)
- `core/.vscode/continue.json.current`: `systemMessage` field replaced with
  `@file ~/R2K-HSL/core/src/ros2k_knowledge/agent_prompt_de.txt` (was 68-line
  inline copy in `continue.expanded.json` + 3-line summary in
  `continue.json.current`)
- `.opencode/opencode.json`: added `agent_prompt_de.txt` as 3rd entry in
  `instructions` array (opencode now loads all 10 axioms + RAG directive +
  formatting rules + persona, was missing 3 axioms #7/#9/#10)
- `core/AGENTS.md`: replaced 7-axiom section (lines 73-89) with 3-line
  cross-reference to `agent_prompt_de.txt` (eliminates redundancy: 7 axioms
  were appearing twice per opencode session — English from AGENTS.md +
  German from agent_prompt_de.txt)
- `core/.vscode/continue.expanded.json`: kept as-is (not documented)

### Team docs
- `core/docs/cheatpage_r2k_team_workflow.md` (NEW, 5 parts):
  1. Setup: configs, prompts, providers, startup-chain, impact-isolation
  2. Applied concepts: session memory, RAG knowledge base, skills alternative
  3. Knowledge base: when to consult, 10 axioms, anti-patterns (KB + code)
  4. Best practices: sessions, git, cross-tool, team-workflow
  5. opencode DX: quick wins (custom commands, permissions, watcher.ignore,
     small_model, {file:}/{env:} keys) + "bewusst nicht genutzt" (Agent
     Skills, MCP, plugins, server mode)
- `core/docs/student_projects_autumn_fair.md` (NEW, untracked — not committed
  per user decision): 4 student project descriptions (P1 voice interface, P2
  manufacturing/storage, P3 Yahboom+A0 stand, P4 eye in the sky) with
  self-contained "Über das Projekt" intro block for physical distribution

### Project planning
- 13-topic priority grouping for September RoboCup + autumn fair + 6-month
  internship (v6.2 assumed done): K1 locomotion/kick/walk (Sep dev team),
  referee robustness (Sep dev team), 4 fair demos (2-mo students), 4 research
  topics (6-mo intern)
- Knowledge architecture discussion: audited opencode native features
  (Agent Skills, custom commands, permissions, agents, LSP, MCP), decided
  to keep current setup (Option B — power-files as canonical source, no
  migration to Skills — not portable to Continue)

**Files touched:**
- `.opencode/opencode.json` (agent_prompt_de.txt added to instructions)
- `core/AGENTS.md` (axiom section → cross-reference)
- `core/.github/copilot-instructions.md` (file → symlink)
- `core/.vscode/continue.json.current` (systemMessage → @file reference)
- `core/docs/SESSION_CHANGELOG.md` (this entry)

**New files (untracked):**
- `core/docs/cheatpage_r2k_team_workflow.md` (committed in 3c2382d)
- `core/docs/student_projects_autumn_fair.md` (not committed — user decision)
- `core/docs/workshop_invitation.md` (not committed — stays local)
- `core/docs/workshop_memo.md` (not committed — stays local)

**Files deleted:**
- (none)

**Not yet done:**
- `continue.json.current` `@file` resolution not verified in live VSCode
  (needs user to launch Continue and test — if `@file` doesn't resolve,
  fall back to inline systemMessage)
- `student_projects_autumn_fair.md` not committed (user decision — may
  commit later)
- Workshop planning (Decision A: deliverable format, Decision B: Module 5
  depth) still open — workshop_invitation.md + workshop_memo.md stay local
- opencode DX quick wins (Part 5 of cheat page) not implemented — custom
  commands, permissions, watcher.ignore, small_model, {file:}/{env:} keys
- Session changelog entry was nearly forgotten — opencode must remind to
  append before committing (protocol reinforced this session)

**Next:**
- Verify `continue.json.current` `@file` resolution in VSCode (launch
  Continue, say "Hallo", check if onboarding greeting appears with 10 axioms)
- Then push commit `3c2382d` + this changelog commit to origin

**Blockers:**
- Ollama stuck on CPU on U22 (carried from 2026-07-20 — `pkill -9` not executed)
- `batch_evaluator.py` KPI collection still broken (Phase 2b, carried from
  2026-07-13/15)
- Visualizer blitting refactor still untested with live ROS 2 + Gazebo
  (carried from 2026-07-14)