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

## 2026-07-21 (continued) — RF learning architecture planning: W&B vs custom, Option A scope, dynamic prompt injection

**Goal:** Plan the evolution from manual B-study experiments to a
semi-automated RF learning loop for prompt optimization. Evaluate W&B as
the experiment-tracking framework vs a custom ROS2K-internal solution.
Scope the immediate next step (Option A: redesign `batch_evaluator.py`).
Plan dynamic prompt injection (game-phase-aware fragment switching) and
field-test semi-automation.

**Done:**

### Vision sketch (5 layers)

Drafted a 5-layer architecture for the full RF learning vision:

1. **World Model Evolution** — Kalman filter (1a), predictive world model
   (1b), deviation watchdog (1c), failsafe takeover (1d). Addresses the
   ~800ms LLM latency by forward-simulating world state. Watchdog detects
   divergence between predicted and actual state. Failsafe switches blue
   to rule-based behavior if LLM fails or divergence is critical.
2. **Prompt Optimization Loop** — `batch_evaluator.py` (2a, Option A),
   `prompt_mutator.py` (2b), sweep runner (2c), variant ranker (2d),
   auto-promoter (2e). Closes the loop between prompt variants and KPI
   measurement.
3. **Dynamic Prompt Selection** — game-phase classifier (3a), fragment
   library expansion (3b), runtime prompt switching (3c). Selects
   context-appropriate prompt based on `match_state.status`.
4. **Dashboard & Control** — W&B-style dashboard for run comparison, KPI
   time series, prompt diff viewer, world-model divergence plot, failsafe
   activation log.
5. **Full Automation** — auto-sweep scheduler, active learning
   (scenario generation), promotion gate, continuous operation on A100
   cluster.

### W&B vs custom infrastructure — detailed evaluation

**W&B concepts mapped to ROS2K needs:**

| W&B concept | ROS2K equivalent | W&B gives us |
|-------------|-----------------|--------------|
| `wandb.init(project, config)` | `run_config.json` + batch_evaluator metadata | Hyperparameter tracking, run grouping, auto-naming |
| `run.log(metrics)` | `kpis_flat_*.json` writer | Time-series logging, auto-plotting |
| W&B Dashboard | Streamlit dashboard (~200 lines custom) | Zero-code visualization (scatter, bar, parallel coordinates) |
| W&B Sweeps | `prompt_mutator.py` + `rf_sweep.sh` + `rank_variants.py` | Built-in sweep strategies (grid, random, Bayes), auto-ranking |
| W&B Artifacts | Fragment snapshotting | Versioned artifacts with diff viewer |
| W&B Reports | `results/phase2_summary.md` (manual) | Auto-generated reports with embedded charts |

**What W&B eliminates:** `run_config.json`, `kpis_flat_*.json`, Streamlit
dashboard (~200 lines), custom sweep runner, custom ranker, custom flat
JSON writer. ~400 lines of custom code replaced by `pip install wandb`.

**What W&B cannot do:**
- **Prompt fragment mutation:** W&B Sweeps sweep numeric/discrete parameters,
  not text files. Fragment variant generation requires custom code
  (`prompt_mutator.py`). W&B only tracks WHICH variant won, doesn't
  generate variants.
- **Per-run fragment snapshotting:** W&B logs config dicts, not file trees.
  Would need W&B Artifacts (separate API, more complexity).
- **Cross-run reproducibility:** W&B logs config, not actual fragment content.
  Two runs with same config could have different fragments if someone
  edited them between runs. Mitigated by fragment hash logging.
- **Early termination (Hyperband):** Not directly applicable — our "run" is
  one 120s match, not training epochs. Can't stop a match early based on
  intermediate KPIs.

**W&B offline vs cloud:**
- Offline mode (`WANDB_MODE=offline`): no account, no internet, data stays
  local. View via `wandb server start` at localhost:8080. Recommended
  default for lab setup.
- Cloud mode: optional, for team sharing/mentoring. Senior reviews junior
  runs remotely via wandb.ai.

### Two-tier approach for prompt sweeping

| Tier | What | How | When |
|------|------|-----|------|
| **Tier 1: Parameter sweeps** | scenario × model × temperature × num_ctx × relay | W&B Sweeps (sweep.yaml) — built-in, zero custom code | Phase 2c, Phase 3 — numeric/discrete parameters |
| **Tier 2: Prompt mutation sweeps** | rules_core.txt variants, samples variants | Custom `prompt_mutator.py` + `batch_evaluator.py --variant-dir` | RF learning phase — text mutation |

**Tier 1 uses W&B Sweeps** — zero custom code, just sweep.yaml.
**Tier 2 uses custom code** — W&B can't mutate text files. `--variant-dir`
arg in `batch_evaluator.py` copies a variant's fragments to
`strategy/fragments/` before each run. W&B logs which variant won via
fragment hash.

### System config sweeping (deferred)

Evaluated whether `system_config.json` (node enable/disable, watchdog
on/off, future Layer 1 fields) should be part of Option A. Decision:
**deferred to later project phases.** `launch_r2k.sh` currently hardcodes
which nodes start — no `--disable` flags, no config file. Adding
`system_config.json` would require refactoring `launch_r2k.sh` to read
JSON for each node (~50 lines). The need is real (sweep "Gazebo without
watchdog", "referee off", "predictor on/off") but it's a separate work
stream from Option A.

### Dynamic prompt injection — design correction

Initial assessment was wrong on three points, corrected during discussion:

1. **"No runtime prompt switching"** — WRONG. `r2k_evaluator.py` sends
   `sys_prompt` in every Ollama API call (line 107: `"system": sys_prompt`).
   Ollama is stateless — it doesn't cache the system prompt. We CAN change
   `sys_prompt` between calls without restarting anything.
2. **"Requires new `prompt_selector.py` module"** — WRONG.
   `r2k_evaluator.py` already reads `Worldstate.json` every 20ms, which
   contains `match_state.status`. Dynamic injection is just: read status
   → pick fragment set → assemble prompt → send to Ollama. ~20 lines in
   `r2k_evaluator.py`, no new module.
3. **"setup_r2k.py assembles at boot, not runtime"** — MISLEADING.
   `setup_r2k.py` writes `system_prompt.txt` at boot, but
   `r2k_evaluator.py` reads it into a variable and sends it per-call. We
   just need to stop caching it at startup and re-assemble on status change.

**Fragment taxonomy for dynamic injection:**

| Type | When it loads | When it swaps | Examples |
|------|--------------|---------------|---------|
| **Static** | Boot, stays for entire match | Never | `header.txt`, `rules_core.txt` |
| **Game-phase** | Runtime, when `match_state.status` changes | On status transition | `rules_<status>.txt`, `samples_<status>.txt` |

Game-phase fragment mapping to referee statuses:
- `playing` → `rules_playing.txt` + `samples_playing.txt` (majority of match)
- `ball_out` → `rules_ball_out.txt` + `samples_ball_out.txt`
- `goal_kick` → `rules_goal_kick.txt` + `samples_goal_kick.txt`
- `corner_kick_in` → `rules_corner_kick_in.txt` + `samples_corner_kick_in.txt`
- `kickoff` → `rules_kickoff.txt` + `samples_kickoff.txt` (after goal)
- `foul_penalty` → `rules_foul_penalty.txt` + `samples_foul_penalty.txt`

Backward compatibility: if `rules_<status>.txt` doesn't exist → fall back
to `rules_playing.txt`. If no game-phase fragments at all → current
behavior (static prompt).

**Content authoring task:** Creating the 10 new fragment files
(`rules_<status>.txt` + `samples_<status>.txt` for 5 non-playing statuses)
is a student/intern content task, not a code task.

### Field test semi-automation — assessment

**What works with Option A:**
- `--relay hardware_mirror` supports K1 + Yahboom hardware
- KPI collection via `analyze_trace.py` works on hardware (reads JSON
  traces, not ROS2 topics)
- W&B logging works the same for sim and hardware
- `--runs 1` mode: student runs one match, resets field, runs again

**Fundamental limitation:** Field tests are **semi**-automated, not fully.
A human must place robots in starting positions, place the ball at
kickoff, reset between runs. Hardware can't run 27 times unattended.
K1 ignores `cmd_vel` for freeze — set-piece freezes are sim-only.

### Cross-platform support (U22 + U24)

Identified that `batch_evaluator.py` runs on the host, but on U24 the
ROS2 nodes run inside Docker. Trace files written inside the container
at `/workspace/logs/` are not visible on the host. Fix: mount `logs/`
as a Docker volume in `docker-compose.yml` (~2 lines).

`batch_evaluator.py` is already ROS2-abstracted — it shells out to
`launch_r2k.sh` (which handles ROS2/Docker/native) and calls
`analyze_trace.py` (which reads JSON files, not ROS2 topics). Only
fix needed: auto-detect platform (U22 native vs U24 Docker) for trace
file path.

### Env var accounting (final)

| Env var | Status |
|---------|--------|
| `R2K_OLLAMA_MODEL` | Keep (existing) |
| `R2K_RUN_ID` | Keep (set by launch_r2k.sh) |
| `R2K_OLLAMA_URL` | Keep but don't log (user: won't change) |
| `R2K_RUN_LABEL` | New (set by batch_evaluator for mnemonic IDs) |
| `R2K_INCLUDE_MATCH_STATE` | Remove (→ W&B config if ever needed) |
| `WANDB_MODE` | New, default `offline` |

Net: -1 env var, +2 W&B env vars (both optional), 0 custom config files.

### Option A final scope (LOCKED)

| Step | File | Change | Lines |
|------|------|--------|-------|
| 1 | `launch_r2k.sh:87` | Read `R2K_RUN_LABEL` env var → mnemonic run ID | ~5 |
| 2 | `batch_evaluator.py` | Redesign: W&B logging + `analyze_trace.py` call + `--relay` arg + `--variant-dir` arg + platform auto-detect + fragment hash | ~110 |
| 3 | `docker-compose.yml` | Mount `logs/` as volume | ~2 |
| 4 | `install.sh:50` | Add `wandb` to pip install | ~1 |

Total: ~120 lines. Not implemented yet — planning complete, execution
deferred to next session.

**Deferred (NOT in Option A):**
- `system_config.json` (node enable/disable) — later project phase
- Dynamic prompt injection (~20 lines in `r2k_evaluator.py`) — follow-up,
  independent of Option A
- Game-phase fragment library (10 new fragment files) — content authoring
- `prompt_mutator.py` (Tier 2 sweep) — RF learning phase
- W&B Sweeps (Tier 1 sweep) — Phase 2c
- Layer 1 (Kalman, predictor, watchdog, failsafe) — 6-month internship
- Streamlit/W&B dashboard — after baseline data exists

**Not yet done:**
- Option A NOT implemented — planning complete, code not written
- Dynamic prompt injection NOT implemented — design complete, code not written
- `continue.json.current` `@file` resolution not verified in VSCode
- `student_projects_autumn_fair.md` not committed (user decision)
- Workshop planning (Decision A: deliverable format, Decision B: Module 5
  depth) still open
- opencode DX quick wins (Part 5 of cheat page) not implemented

**Next:**
- **Open question for tomorrow:** which approach has more benefits — doing
  the RF learning infrastructure within ROS2K (custom Python, full control,
  no external dependency) or by exploiting the W&B infrastructure (less
  code, built-in dashboard/sweeps, but can't mutate text files and adds
  a dependency)? See "W&B vs custom — the ultimate question" below.
- Implement Option A (`batch_evaluator.py` redesign, ~120 lines)
- OR implement dynamic prompt injection first (~20 lines in
  `r2k_evaluator.py`) — independent of Option A, can be done in parallel
- Then push all unpushed commits to origin

**Blockers:**
- Ollama GPU on U22: user reports resolved ("worx") — removed from blocker
  list
- `batch_evaluator.py` KPI collection: still broken — Option A fixes it
- Visualizer blitting: still untested with live ROS 2 + Gazebo — doesn't
  block Option A (headless runs don't need visualizer)

---

### W&B vs custom — the ultimate question (for tomorrow)

**The question:** Should ROS2K's RF learning infrastructure be built
within ROS2K (custom Python, file-based, no external framework) or by
exploiting W&B (pip install, dashboard + sweeps built-in)?

**Arguments for W&B:**
1. **Dashboard for free** — ~200 lines of Streamlit code eliminated.
   W&B provides runs table, scatter plots, parallel coordinates, sweep
   progress UI out of the box. Students see results immediately in a
   web browser (`wandb server start`).
2. **Sweeps for free** — grid/random/Bayes search strategies built-in.
   `sweep.yaml` is ~20 lines vs ~100 lines of custom sweep logic.
3. **Standard tool** — students may already know W&B from ML courses.
   Transferable skill. Industry-standard for experiment tracking.
4. **Offline mode** — no account, no internet, data stays local. Works
   in the lab without any cloud dependency.
5. **Cloud sync optional** — for team sharing/mentoring, `wandb sync`
   pushes to wandb.ai. Senior can review junior's runs remotely.
6. **Artifact versioning** — W&B Artifacts can track fragment versions
   with diff viewer (though this requires the Artifacts API, more
   complexity).

**Arguments against W&B (for custom ROS2K-internal):**
1. **External dependency** — `wandb` package must be installed, pinned,
   and kept compatible. Adds ~50MB to the venv. If W&B changes their
   API or pricing, we're affected.
2. **Can't mutate text files** — W&B Sweeps sweep numeric/discrete
   parameters, not text fragments. The core RF learning action
   (generating and testing prompt variants) requires custom code
   regardless of whether we use W&B or not. W&B only tracks results,
   doesn't drive the mutation.
3. **Abstraction mismatch** — W&B is designed for ML training loops
   (epochs, loss curves, early termination). ROS2K runs are 120s
   matches with no intermediate checkpoints. W&B's Hyperband early
   termination doesn't apply. The fit is imperfect.
4. **Data leaves the machine** — even in offline mode, W&B writes to
   its own directory format (`wandb/`), not plain JSON. Data is
   locked in W&B's format. If we want to process results with custom
   tools later, we need `wandb` to read them back.
5. **Student complexity** — students must learn W&B's API
   (`wandb.init`, `run.log`, `wandb.agent`, sweep config syntax) in
   addition to ROS2K's architecture. One more thing to learn.
6. **Full control** — a custom solution gives us full control over
   data format, visualization, sweep logic. We can tailor it exactly
   to ROS2K's needs (fragment hashing, game-phase tagging, composite
   score) without working around W&B's abstractions.
7. **ROS2K is not ML training** — the W&B mental model (track training
   metrics over epochs) doesn't match ROS2K's model (run discrete
   matches, compare KPIs). A custom dashboard could show exactly what
   matters: per-scenario KPI matrix, fragment diff viewer, referee
   status timeline, world-model divergence plot. W&B's generic charts
   would need customization anyway.

**The hybrid middle ground:**
- Use W&B for **Tier 1** (parameter sweeps: scenario × model ×
  temperature × num_ctx). These are numeric/discrete — W&B's sweet
  spot. Zero custom code.
- Use **custom** for **Tier 2** (prompt mutation). W&B can't do this
  anyway. `prompt_mutator.py` + `--variant-dir` + fragment hash
  tracking.
- Use W&B for **dashboard** (run comparison, KPI plots) — saves ~200
  lines of Streamlit.
- Use **custom** for **ROS2K-specific visualizations** (referee status
  timeline, world-model divergence, fragment diff) — W&B can't show
  these without custom plugins.

**The real question is:** where on the spectrum from "fully custom" to
"fully W&B" do we want to be? The hybrid answer uses W&B where it's
strong (parameter sweeps, generic KPI dashboard) and custom where it's
weak (prompt mutation, ROS2K-specific visualization). But the hybrid
also means students learn TWO systems (W&B + ROS2K custom), not one.

**For tomorrow's discussion:** consider which matters more — minimizing
code/dependency (→ W&B), or maximizing control/simplicity for students
(→ custom). Also consider the workshop context: if we teach students
W&B, they learn a transferable industry skill. If we teach them a
custom ROS2K dashboard, they learn our architecture but not a
transferable tool.

**Files touched:**
- `core/docs/SESSION_CHANGELOG.md` (this entry)

**Files deleted:**
- (none)

## 2026-07-22 — Optimization spec rewrite (trial-and-error paradigm), scenario packages, field diagrams, workshop docs, framework evaluation, power file updates

**Goal:** Rewrite the v6.2 optimization spec to reflect the chosen paradigm
(local trial-and-error + shared regression tests, no W&B/DSPy/Optuna). Create
scenario packages with field diagrams. Rewrite all workshop docs from scratch
(as-is only, no future features presented as existing). Update power files to
v6.2. Resolve the W&B vs custom framework question.

**Done:**

### Framework evaluation: W&B vs DSPy vs Optuna vs pytest+git

Evaluated four approaches for experiment tracking and prompt optimization:

- **W&B:** Generic ML experiment tracker. Dashboard + sweeps built-in. But
  can't mutate text files (fragments), abstraction mismatch (epochs vs
  matches), data format lock-in. Dropped.
- **DSPy + GEPA (Stanford NLP):** Prompt optimization framework. Automated
  prompt mutation via reflection LM. Best fit for Tier 2 (prompt mutation).
  But requires wrapping `r2k_evaluator.py` as DSPy module (~300 lines),
  synchronous assumption conflicts with async architecture. Deferred to
  Phase 5.9 (conditional — only if manual iteration becomes a bottleneck).
- **Optuna:** Black-box optimization. Better fit than W&B for non-ML
  workflows. Can sweep discrete variant dirs. But still can't mutate text.
  Deferred alongside DSPy.
- **pytest + git (CHOSEN):** Uses tools students already know. Regression
  protection built-in. Git log = experiment history (meaningful improvements
  only). Zero external dependencies. Accepted limitation: may end in local
  minima, requires thoughtful engineering.

**Decision:** pytest + git + local trial-and-error. No W&B, no DSPy, no
Optuna. Engineers iterate locally (no commit per experiment), run shared
regression suite, commit only winners. DSPy/Optuna can be added later
(Phase 5.9) if manual iteration becomes a bottleneck.

### Optimization spec v6.2 — major rewrite

- `optimization_spec_v6.2.md`: 1529 lines (was 789). All version tags
  normalized to v6.2. Key changes:
  - **Paradigm:** Local trial-and-error + shared regression tests + commit
    only winners. No external framework.
  - **Phase 2 restructured:** 2a = goalie fix (HARD prerequisite before
    baseline — 95% idle biases all score KPIs), 2b = write
    `test_non_functional.py`, 2c = pytest markers, 2d = scenario package
    migration, 2e = 27-run baseline, 2f = identify worst scenarios
  - **Phase 2a goalie fix:** Smooth blending (no hardcoded if/else
    thresholds) using `smoothstep()`. LLM keeps 30% influence. All
    parameters are named constants at top of bridge file
    (`GOALIE_TACTICAL_WEIGHT`, `GOALIE_FAR_GOAL_DIST`, etc.) — tunable
    via trial-and-error, part of optimization task (D9 experiment).
    Documented as "temporary crutch" until Phase 5.1 (Kalman) provides
    good data.
  - **§3 Test scenarios:** Reorganized into scenario packages (folders
    with `scenario.json`, `field_diagram.png`, `analysis.md` with
    oracle/expert, `kpi_targets.json`). Added `time_index` field. Focus
    on 3vs3 (primary) + 2vs2 (secondary). Each TC presented one-by-one
    with embedded field diagram, oracle/expert, KPI targets.
  - **§4.2 Fragment taxonomy:** Static + game-phase fragments. Mapping
    to referee statuses. Dynamic injection mechanism explained (Ollama
    is stateless, sends sys_prompt per call).
  - **§4.5 Goalie idle:** Rewritten as critical bias (danger callout).
    Must fix in Phase 2a before any baseline. Tactical positioning rules
    (angle-block, passing buddy, goal-line) for small vs large teams.
  - **§5.1 Phase 5.1:** Renamed "Kalman Filter (and goalie fix
    completion)". Added Option C: once Kalman provides filtered positions
    + velocity + predictions, bridge goalie blending is removed entirely.
  - **§5.10:** 5vs5 scale-up added (prompt complexity, latency, fragments,
    referee thresholds, 3B vs 7B research question).
  - **§5.11:** LLM output quality evaluation (oracle/expert + --explain).
    Manual now, automated LLM-as-judge deferred.
  - **§5.9:** Automated prompt optimization (DSPy/Optuna) — conditional,
    only if manual iteration becomes a bottleneck.
  - **D9 experiment:** Goalie blending parameter sweep added.
  - **§2.4:** Shared regression suite with two-tier speed (fast --skip-slow
    ~2s, slow full suite ~21min). Clarified `@pytest.mark.slow` / `--skip-slow`.

### Scenario packages created (10 packages)

- `tools/gen_field_diagrams.py` (NEW, ~180 lines): generates 2D field
  diagrams with colorized bots (blue/red), goal posts, goal areas, ball,
  center circle, corner flags. Reads `scenario.json`, writes
  `field_diagram.png`.
- 10 scenario packages created (TC-01..09 3vs3 + TC-11 2vs2):
  - `scenario/<name>/scenario.json` (entity positions, copied from flat files)
  - `scenario/<name>/field_diagram.png` (generated by gen_field_diagrams.py)
  - `scenario/<name>/analysis.md` (oracle + expert tactical analysis)
  - `scenario/<name>/kpi_targets.json` (per-scenario acceptable KPI ranges)
- `setup_r2k.py` not yet updated to read from packages (Phase 2d)

### Workshop docs — rewritten from scratch (as-is only)

All three workshop docs rewritten based on the principle: "describe what we
HAVE, mention Phase 5 for future directions, don't present planned features
as existing."

- `workshop_invitation.md` (1-page, team-facing): updated all 5 modules
  with as-is descriptions. K1 described correctly (ROS2 custom message
  type). No ROS_DOMAIN_ID seat numbers. No Streamlit/W&B. Module 5 =
  Phase 5 roadmap walkthrough.
- `workshop_memo.md` (internal planning): all modules updated with as-is
  experiments. No regression suite, no blending demo, no dynamic injection
  experiment (all planned, not implemented). §7: explicit "Planned but
  NOT yet implemented" list with 11 items. No ROS_DOMAIN_ID patch in
  checklist.
- `workshop_lecturer_guide.md` (NEW, lecturer only): term glossary
  (deque, OLS, staleness, min_ents, fragment, oracle/expert, RPC).
  opencode example commands (7 use cases). Per-module timing, talking
  points, expected answers, offline fallbacks. K1 described correctly
  ("IS controlled via ROS2 using a custom message type"). "Planned but
  NOT yet implemented" table at end with 11 items.

### Power files updated to v6.2

- All 7 power files: version tags bumped from v6.1 to v6.2, last_modified
  dates updated to 2026-07-22
- `META_KNOWLEDGE_ROUTER.md`: batch_evaluator entry updated — marked
  DEPRECATED, KPI collection broken noted, replacement referenced
- `6_DATA_SCHEMAS_AND_LIFECYCLE.md`: batch_evaluator section — deprecation
  note added, source reference updated to v6.2 spec
- `3_AI_LOGIC_AND_EDGE_CASES.md`: goalie idle section — added status note
  (Phase 2a fix designed but not implemented, Phase 5.1 Kalman is
  long-term fix)

**Files touched:**
- `core/docs/optimization_spec_v6.2.md` (major rewrite, 1529 lines)
- `core/docs/workshop_invitation.md` (rewritten from scratch)
- `core/docs/workshop_memo.md` (rewritten from scratch)
- `core/docs/workshop_lecturer_guide.md` (NEW)
- `core/docs/SESSION_CHANGELOG.md` (this entry)
- `core/src/tools/gen_field_diagrams.py` (NEW)
- `core/src/scenario/3vs3_attack_center/` (NEW: 4 files)
- `core/src/scenario/3vs3_attack_wing/` (NEW: 4 files)
- `core/src/scenario/3vs3_defensive_crisis/` (NEW: 4 files)
- `core/src/scenario/3vs3_fast_counter/` (NEW: 4 files)
- `core/src/scenario/3vs3_pressing_trap/` (NEW: 4 files)
- `core/src/scenario/3vs3_long_shot/` (NEW: 4 files)
- `core/src/scenario/3vs3_contain_delay/` (NEW: 4 files)
- `core/src/scenario/3vs3_def_transition/` (NEW: 4 files)
- `core/src/scenario/3vs3_high_line/` (NEW: 4 files)
- `core/src/scenario/2vs2_default/` (NEW: 4 files)
- `core/src/ros2k_knowledge/1_CORE_ARCHITECTURE_AND_SYNC.md` (version bump)
- `core/src/ros2k_knowledge/2_ROS2_PROTOCOLS_AND_FRAMES.md` (version bump)
- `core/src/ros2k_knowledge/3_AI_LOGIC_AND_EDGE_CASES.md` (version bump +
  goalie idle status note)
- `core/src/ros2k_knowledge/5_HYBRID_INFRASTRUCTURE_V5.md` (version bump)
- `core/src/ros2k_knowledge/6_DATA_SCHEMAS_AND_LIFECYCLE.md` (version bump +
  batch_evaluator deprecation note)
- `core/src/ros2k_knowledge/META_KNOWLEDGE_ROUTER.md` (version bump +
  batch_evaluator deprecation)

**New files (untracked):**
- `core/docs/workshop_lecturer_guide.md`
- `core/src/tools/gen_field_diagrams.py`
- `core/src/scenario/3vs3_attack_center/` (4 files)
- `core/src/scenario/3vs3_attack_wing/` (4 files)
- `core/src/scenario/3vs3_defensive_crisis/` (4 files)
- `core/src/scenario/3vs3_fast_counter/` (4 files)
- `core/src/scenario/3vs3_pressing_trap/` (4 files)
- `core/src/scenario/3vs3_long_shot/` (4 files)
- `core/src/scenario/3vs3_contain_delay/` (4 files)
- `core/src/scenario/3vs3_def_transition/` (4 files)
- `core/src/scenario/3vs3_high_line/` (4 files)
- `core/src/scenario/2vs2_default/` (4 files)

**Files deleted:**
- (none)

**Not yet done:**
- Phase 2a goalie fix NOT implemented — smooth blending designed but not
  coded in `ollama_sandbox_bridge.py`
- `test_non_functional.py` NOT created — shared regression suite is planned
  but not implemented
- Dynamic prompt injection NOT implemented — `r2k_evaluator.py` still caches
  `sys_prompt` at startup (line 80)
- `setup_r2k.py` NOT updated to read scenario packages — still reads flat
  JSON files
- Workshop handout NOT written (Decision A: deliverable format not resolved)
- Workshop Decision B (Module 5 depth) not resolved
- `core/docs/optimization_spec_v6.2 1.md` — accidental duplicate file,
  should be deleted before commit
- Nothing committed yet

**Next:**
- Delete accidental duplicate `optimization_spec_v6.2 1.md`
- Commit all work (spec + workshop docs + scenario packages + gen_field_diagrams +
  power file updates + this changelog)
- Implement Phase 2a (goalie smooth blending in bridge, ~25 lines)
- Write `test_non_functional.py` (shared regression suite, ~100 lines)
- Resolve workshop Decision A + B
- Write workshop handout

**Blockers:**
- `batch_evaluator.py` KPI collection still broken (deprecated, replacement
  not yet implemented)
- Visualizer blitting still untested with live ROS 2 + Gazebo
- **NVIDIA driver not responding** — `nvidia-smi` fails with "couldn't
  communicate with the NVIDIA driver." Ollama falls back to CPU (~24s per
  call vs ~800ms on GPU). Bots don't move because the LLM is too slow to
  produce strategies. User will reboot to fix. This is the Xid 31 /
  stale-driver pattern from 2026-07-20. **This machine is Ubuntu 24.04
  (Docker mode), not U22.** After reboot: verify `nvidia-smi` works,
  then `pkill -9 -f "ollama runner"; pkill -9 -f "ollama serve";
  nohup ollama serve > /dev/null 2>&1 &`, warm up model, re-run match.
- Ollama GPU: was reported resolved ("worx") on U22 but regressed on this
  machine (U24). Driver communication lost. Re-adding to blocker list.
## 2026-07-23 — Dead blue team diagnosis, workshop v6.2 material package (diagrams, cheat page, handout, reviewer tar)

**Goal:** Diagnose intermittent dead-blue-team on `--no-explain` launch,
produce complete workshop v6.2 student material package (diagrams + cheat
page + handout + reviewer tar).

**Done:**

### Dead blue team diagnosis (trace log + ollama.log forensics)

User reported: (1) `--no-explain` → dead blue team, (2) `--explain` worked,
(3) second `--no-explain` worked. Diagnosed via trace logs + ollama.log:

- Dead run (17:17:12) had 336 `world_trace` records (33.5s, valid blue
  entities) but **zero `llm_trace` records** — evaluator never logged a
  single LLM call. Ruled out `num_predict` truncation theory.
- `ollama.log` showed cold-boot model load: `ollama serve` started at
  17:17:12, first POST /api/generate at 17:17:29, model load began 17:17:30
  (37 layers, 1.8 GiB), **HTTP 499 at 17:18:03** — "client connection
  closed before server finished loading, aborting load" (33.7s elapsed).
  The evaluator process was killed (window close or CTRL+C during model
  load), HTTP connection dropped, Ollama aborted the load.
- Root cause: **cold-boot race condition**. First match after `ollama serve`
  triggers 30-40s model load. If user interrupts during load → evaluator
  killed → no `current_strategy.json` → bridge has no targets → dead blue.
  Second match works (model warm, `keep_alive: "1h"`).
- `--explain` didn't "fix" anything — it was launched when model was already
  warm from the failed first attempt. `num_predict` (150 vs 600) was NOT
  the cause.
- Warm-up timeline documented: `t=0` ollama starts → `t=17s` first POST →
  `t=21.5s` runner loaded (3.47s) → `t=22s` steady state (500-650ms/call).
- Evidence: `ollama.log` at `core/src/ollama.log`, trace files at
  `core/src/logs/`, `r2k_evaluator.py:123` (timeout=150s), `:108`
  (keep_alive="1h"), `:100-111` (num_predict 150/600).

### `num_predict` + warm-up timeline added to workshop material

- `workshop_lecturer_guide.md` term glossary: added `num_predict` definition
  (line 32) — Ollama token generation cap, 150 (no-explain) / 600 (explain),
  truncation → dead blue team mechanism
- `workshop_lecturer_guide.md`: added "Ollama warm-up timeline (cold boot →
  steady state)" section (lines 57-110) with ASCII timeline, HTTP 499
  failure mode, 3-step lecturer mitigation, pre-workshop warm-up checklist
- `workshop_memo.md`: added §2.1a "Warm up Ollama BEFORE the first match"
  with timeline table (elapsed/event/evidence), failure mode block, curl
  mitigation command
- `workshop_memo.md` Module 1 concepts: added `num_predict` explanation
- `workshop_memo.md` execution checklist: added warm-up step

### Architecture diagrams (Graphviz → PNG/PDF)

Created `core/docs/workshop v6.2/` folder with:

- **`part1_boot_ramp.dot/.png/.pdf`** (7.5×9.9 in, A4 portrait):
  6-phase boot sequence — CLI flags → env wipe → setup_r2k.py (fragment
  assembly) → Ollama check → Gazebo launch + spawner → node ignition.
  Includes fragment library (header/rules_core/rules_{mode}/samples_{mode}),
  strategies (strat_aggro/default/recover), scenarios (2vs2 + 3vs3 ×9 +
  package folders), relay profiles (only_sim_bots/hardware_mirror).
  Handoff marks ①-⑤ at bottom.

- **`part2_running_system.dot/.png/.pdf`** (5.6×10.5 in, A4 portrait):
  Steady state — Gazebo → tracker → engine nodes (referee/score/reward/red)
  → aggregator → evaluator ↔ Ollama → bridge → sim/real bots. All timings
  with ⏱. Watchdog. Handoff marks ①-⑤ at top matching Part 1.

- **`rqt_graph_mockup.dot/.png`** (2048×1604 px): rqt_graph-style ROS2 node
  graph — 7 nodes (ovals, color-coded) + 9 topics (squares), blue=publish,
  green=subscribe, dark theme (#2b2b2b).

- **`runtime_architecture.dot/.png/.pdf`**: original combined diagram
  (superseded by part1+part2 split, kept for reference).

- **`rviz2_mockup.png`**: matplotlib-generated RViz2 look-alike (dark theme,
  soccer field grid, 4 bots as cylinders, TF frames, Displays tree panel,
  topic info overlay). Not referenced in handout (visual aid for lecturer).

Diagram conventions: cylinder=Gazebo, rounded box=.py, hexagon=.json,
note=.txt, component=Ollama, box3d=sim bot, doubleoctagon=real bot.
⏱=timing, ▶=pub, ◀=sub. Font: FreeSerif (has all unicode glyphs).
Edge fonts: 8pt (readable on A4 print).

### Cheat page (`workshop v6.2/cheatpage.md`, 187 lines)

6 sections:
1. Launch flags (8 flags with 1-2 line explanations)
2. Testing (7 test files, 91 tests, what each covers, how to run)
3. 14 KPIs (source, target, what it measures) + composite score formula
4. 10 test scenarios (oracle, KPI targets, what to watch)
5. Quick-test recipes (11 one-liners)
6. File locations (where things live in the repo)

### Student handout (`workshop v6.2/handout.md`, 555 lines)

German with English technical terms. 5 modules + front/back matter:
- Glossary (14 terms: deque, OLS, staleness, min_ents, fragment,
  oracle/expert, RPC, num_predict, Twist, tmpfs, R2K_RUN_ID, composite
  score, cold-boot-race, PID-controller)
- Warm-up box (curl command + cold-boot warning)
- Diagram reading guide (Part 1 + Part 2, ①-⑤ marks)
- 5 modules × 3-4 experiments each, with fill-in KPI tables + blank lines
  for personal observations
- opencode examples per module (2-4 prompts each, experiment-focused)
- Key Take-Aways per module (4-6 bullets each)
- Troubleshooting table (4 common problems)
- "Wo finde ich was?" index (12-row cross-reference table)

### Lecturer guide updates (`workshop_lecturer_guide.md`)

- Removed central "opencode example commands" section (was lines 114-169)
- Distributed opencode examples inline per module (Module 1-5)
- Added `num_predict` to term glossary
- Added Ollama warm-up timeline section
- Added warm-up step to pre-workshop checklist
- Module 3 Experiment 3 already had K1 opencode example
- Module 4 Experiment 3 expanded: fragment edit + dump_prompt + run match
  + analyze_trace + compare to baseline + Plan mode demo
- 6 of 13 opencode examples now involve running experiments (was 2 of 9)
- Updated Q&A cross-reference

### Invitation update (`workshop_invitation.md`)

- Module 4: added `run_experiment.sh` naming convention (`A`=baseline,
  `B1`-`B7b`=variants, determines output filenames)

### Reviewer tar package

- `workshop v6.2/README.md` (reviewer orientation: package contents,
  review questions, exclusions, file dependency map, conventions)
- Copied `workshop_invitation.md` into `workshop v6.2/`
- Tar at `/tmp/opencode/ros2k_workshop_v6.2_review.tar.gz` (344 KB, 7 files):
  README.md, handout.md, cheatpage.md, workshop_invitation.md,
  part1_boot_ramp.pdf, part2_running_system.pdf, rqt_graph_mockup.png
- Excluded: lecturer guide, memo, .dot sources, runtime_architecture.*
  (superseded), rviz2_mockup.png, .png versions of diagrams

**Files touched:**
- core/docs/workshop_lecturer_guide.md (opencode redistribution, num_predict,
  warm-up timeline, checklist, Q&A update)
- core/docs/workshop_memo.md (num_predict, warm-up §2.1a, checklist)
- core/docs/workshop_invitation.md (run_experiment.sh naming)
- core/docs/SESSION_CHANGELOG.md (this entry)

**New files (untracked):**
- core/docs/workshop v6.2/cheatpage.md
- core/docs/workshop v6.2/handout.md
- core/docs/workshop v6.2/README.md
- core/docs/workshop v6.2/part1_boot_ramp.dot
- core/docs/workshop v6.2/part1_boot_ramp.pdf
- core/docs/workshop v6.2/part1_boot_ramp.png
- core/docs/workshop v6.2/part2_running_system.dot
- core/docs/workshop v6.2/part2_running_system.pdf
- core/docs/workshop v6.2/part2_running_system.png
- core/docs/workshop v6.2/rqt_graph_mockup.dot
- core/docs/workshop v6.2/rqt_graph_mockup.png
- core/docs/workshop v6.2/runtime_architecture.dot
- core/docs/workshop v6.2/runtime_architecture.pdf
- core/docs/workshop v6.2/runtime_architecture.png
- core/docs/workshop v6.2/rviz2_mockup.png
- core/docs/workshop v6.2/workshop_invitation.md (copied from docs/)
- /tmp/opencode/ros2k_workshop_v6.2_review.tar.gz (reviewer package)

**Files deleted:**
- (none)

**Not yet done:**
- Nothing committed — all work uncommitted on
  `feature/ros2k_behavior_optimization`
- `rviz2_mockup.png` not referenced in handout or cheat page (visual aid
  only — could add to handout if desired)
- Workshop Decision A (deliverable format) and Decision B (Module 5 depth)
  from `workshop_memo.md` §1 are now effectively resolved: handout is
  written (Decision A=1: single Markdown handout), Module 5 depth is
  Option 1 (conceptual + one spike). But these decisions haven't been
  explicitly marked as resolved in `workshop_memo.md`.
- Warm-up call fix NOT implemented in `launch_r2k.sh` — only documented
  in workshop material. The actual code fix (curl warm-up after Ollama
  check, ~3 lines) is deferred.
- Evaluator retry on HTTP 499/non-200 NOT implemented — only diagnosed.
- `batch_evaluator.py` KPI collection still broken (carried from
  2026-07-13/15)
- Visualizer blitting refactor still untested with live ROS 2 + Gazebo
  (carried from 2026-07-14)
- `runtime_architecture.*` (combined diagram) should be deleted from
  `workshop v6.2/` since it's superseded by part1+part2 — currently kept
  for reference but not in the reviewer tar

**Next:**
- Commit all workshop v6.2 material on a dedicated branch
  (`docs/workshop-v6.2-material`), separate from the larger uncommitted
  `feature/ros2k_behavior_optimization` body of work
- Implement the warm-up call fix in `launch_r2k.sh` (~3 lines after
  Ollama model check at line 176): `curl -s ... /api/generate -d
  '{"model":"qwen2.5-coder:3b","prompt":"hi","stream":false}' > /dev/null`
  to prevent cold-boot dead-blue-team for all future users

**Blockers:**
- `batch_evaluator.py` KPI collection still broken (Phase 2b, carried
  from 2026-07-13/15)
- Visualizer blitting still untested with live ROS 2 + Gazebo (carried
  from 2026-07-14)
- Ollama GPU on U24: was diagnosed this session (cold-boot race), warm-up
  mitigation documented but NOT coded in `launch_r2k.sh` yet

## 2026-07-27 — Phase 2 complete: goalie blending, test suite, kick fix, 27-run baseline

**Goal:** Implement Phase 2 (goalie fix + shared test suite + 27-run baseline +
threshold calibration). Fix broken kicks discovered during baseline. Document
test infrastructure across KB, FAQ, and user docs.

**Done:**

### Phase 2a — Goalie smooth blending (commit `b5fb120`)
- `ollama_sandbox_bridge.py`: 10 field-size-relative `GOALIE_*` blending
  parameters (as % of field half-length/width), `smoothstep()` helper at
  module scope. Goalie blending block in `state_cb`: smooth transition
  between goal-line positioning (ball near) and angle-block (ball far),
  70% tactical + 30% LLM influence, deadband eliminates micro-oscillations.
  Skips when `action=='kick'` (Part A). Role-aware kick direction: goalie
  clears upfield, non-goalie bots aim at opponent goal (Part B).
- `tools/analyze_trace.py`: new `goalie_tactical_pct` KPI — distinguishes
  "tactically positioning" from "stuck." Ball far → goalie should be
  forward; ball near → goalie near line + tracking Y.
- `robocup.world`: removed hardcoded `soccer_ball` model (was always at
  0,0, blocking scenario-specified ball positions). Ball now spawned solely
  by `json_spawner.py` from scenario JSON.
- `football.urdf`: ported world-ball physics (mass 0.4, restitution 1.0,
  friction 0.01, velocity_decay 0.002, contact kp/kd/max_vel/min_depth).
- `scenario/3vs3_goal_kick_blue.json`: goal-kick test scenario (ball at
  -3.5,1.0, goalie at -4.0,1.0, red in own half).

### Phase 2b+2c — Test infrastructure (commit `3266b40`)
- `tests/test_non_functional.py`: 5 slow tests (2 scenarios), 4 helpers
  (`run_match_headless`, `compute_composite`, `load_kpi_targets`,
  `assert_kpi_in_range`). Composite score formula (spec §5.2):
  `0.4*goal_diff + 0.3*tac_score + 0.2*possession + 0.1*latency`.
- `pytest.ini`: registers `@pytest.mark.slow` marker.
- `conftest.py`: `--skip-slow` flag implementation.
- `scenario/3vs3_default/`: new package (same positions as TC-01).
- Two-tier: fast (`--skip-slow`, ~2s, 91 unit tests) + slow (~140s/test,
  real Gazebo matches with KPI assertions).

### Documentation (commit `3266b40`, 19 files)
- KB power files: `6_DATA` (V6.2 Addendum — test system, composite formula,
  kpi_targets schema), `META_ROUTER` (2 new routing rows), `3_AI` (goalie
  idle status update), `5_HYBRID` (Docker colcon rebuild procedure with
  full numpy/ndarrayobject.h diagnosis).
- FAQ: Q3 rewritten (batch_evaluator → regression suite), Q16 (14→15 KPIs),
  Q18 (Phase 2a implemented), Q24 new (regression suite + pytest marker
  explanation).
- User docs: `7_03` §6.5 (full pytest marker explanation, two-tier table,
  composite formula, kpi_targets schema), `7_05` §5.5 (regression suite
  commands), `00_MASTER_INDEX` (4 new glossary entries), `1_01` (v6.2 note).
- `AGENTS.md`: test section expanded (two-tier, composite formula), build
  section expanded (U24 Docker colcon + stale cache fix), gotchas expanded
  (Docker colcon rebuild with full diagnosis).
- `Dockerfile`: comment near numpy pin (stale cache fix, cross-refs AGENTS.md).

### Kick fix — Critical bug (commit `1fc480c`)
- `football.urdf`: removed `libgazebo_ros_planar_move.so` plugin. The plugin
  was overriding ball velocity to zero every physics tick, killing phantom
  kicks (ball moved only ~6cm per kick). No code publishes to `/ball/cmd_vel`,
  so the plugin was dead code that actively harmed the kick mechanism.
- Verified: 7 kick events in 60s, max ball speed 1.56m/frame (~15m/s),
  referee ball resets (corner_kick_in, ball_out) work correctly.

### Phase 2d — Scenario package migration (commit `1fc480c`)
- `setup_r2k.py`: reads `scenario/<name>/scenario.json` (package) first,
  falls back to `scenario/<name>.json` (flat). Backward compatible.

### Phase 2e — 27-run baseline (commit `1fc480c`)
- `tools/run_baseline.sh`: 27-run baseline runner (9 scenarios × 3 × 120s).
  `set +e` (don't exit on watchdog kill), container restart between runs.
- Run via `systemd-run --user` to survive shell session timeouts.
- **Before kick fix (broken kicks):** 2 goals scored, 0 conceded, avg
  composite 0.35, avg goalie idle 95.5%, avg OOB 0.5%.
- **After kick fix (working kicks):** 8 goals scored, 20 conceded, avg
  composite 0.33, avg goalie idle 86.5%, avg OOB 12.6%.
- Composite scores per scenario: attack_center 0.38, attack_wing 0.37,
  def_transition 0.35, fast_counter 0.32, contain_delay 0.32,
  defensive_crisis 0.29, pressing_trap 0.30, high_line 0.26,
  long_shot 0.38.

### Phase 2f — 3 worst scenarios + threshold calibration (commit `1fc480c`)
- `test_non_functional.py`: +6 slow tests for 3 worst by composite:
  `3vs3_high_line` (0.26), `3vs3_contain_delay` (0.32), `3vs3_long_shot`
  (0.38). Tests composite, OOB, cluster, goalie_idle, goalie_tactical_pct.
- All 11 `kpi_targets.json` recalibrated from post-kick-fix baseline with
  30-50% margin. min/max semantics fixed: "lower is better" metrics have
  min=0; "higher is better" metrics have max=upper bound.
- `def_transition` OOB max 67.3% (high but realistic — bots push forward
  without defensive cover). `long_shot` OOB max 37% (long kicks fly out).

### Docker colcon rebuild error (diagnosed + documented)
- `colcon build` failed with `numpy/ndarrayobject.h: No such file or directory`.
- Root cause: stale cached artifacts in `ros2_ws/build/`. NOT a missing
  numpy installation.
- Fix: `rm -rf build install`, then re-run `colcon build`. The rosidl CMake
  fallback (`python3 -c "import numpy; print(numpy.get_include())"`)
  resolves the path automatically on a clean build.
- Red herrings documented: do NOT install `python3-numpy-dev`, set `CFLAGS`,
  or pass `--cmake-args -DNumPy_INCLUDE_DIR=...`.
- Full diagnosis documented in AGENTS.md, KB `5_HYBRID_INFRASTRUCTURE_V5.md`,
  and Dockerfile comment.

**Files touched:**
- `core/src/ai_tactics/ollama_sandbox_bridge.py` (goalie blending, role-aware kick)
- `core/src/tools/analyze_trace.py` (goalie_tactical_pct KPI)
- `core/src/ros2_ws/src/box_bot_description/worlds/robocup.world` (removed ball)
- `core/src/ros2_ws/src/r2k_scenario_spawner/urdf/football.urdf` (physics port + plugin removal)
- `core/src/setup_r2k.py` (package folder support)
- `core/src/tests/test_non_functional.py` (NEW — 11 slow tests)
- `core/src/pytest.ini` (NEW — slow marker)
- `core/src/conftest.py` (NEW — --skip-slow)
- `core/src/tools/run_baseline.sh` (NEW — 27-run baseline runner)
- `core/src/scenario/3vs3_goal_kick_blue.json` (NEW — goal-kick test scenario)
- `core/src/scenario/3vs3_default/` (NEW — package: scenario.json, field_diagram.png, analysis.md, kpi_targets.json)
- `core/src/scenario/*/kpi_targets.json` (11 files — recalibrated thresholds)
- `core/src/ros2k_knowledge/3_AI_LOGIC_AND_EDGE_CASES.md` (goalie idle status)
- `core/src/ros2k_knowledge/5_HYBRID_INFRASTRUCTURE_V5.md` (Docker rebuild procedure)
- `core/src/ros2k_knowledge/6_DATA_SCHEMAS_AND_LIFECYCLE.md` (V6.2 Addendum — test system)
- `core/src/ros2k_knowledge/META_KNOWLEDGE_ROUTER.md` (routing rows + glossary)
- `core/src/ros2k_knowledge/ROS2K_GEM_FAQ.md` (Q3/Q16/Q18/Q24)
- `core/AGENTS.md` (test + build + gotchas sections expanded)
- `core/src/Dockerfile` (numpy cache comment)
- `core/user doc/rosk2_technical_documentation/00_MASTER_INDEX.md` (glossary)
- `core/user doc/rosk2_technical_documentation/1_01_INTRODUCTION_Overall_Architecture.md` (v6.2 note)
- `core/user doc/rosk2_technical_documentation/7_03_CHEATPAGE_Tools_and_Utils.md` (§6.5)
- `core/user doc/rosk2_technical_documentation/7_05_CHEATPAGE_Experiment_Guide.md` (§5.5)
- `.gitignore` (results/kpis_baseline_*.json + baseline logs)
- `core/docs/SESSION_CHANGELOG.md` (this entry)

**New files (untracked):**
- `core/src/tests/test_non_functional.py`
- `core/src/pytest.ini`
- `core/src/conftest.py`
- `core/src/tools/run_baseline.sh`
- `core/src/scenario/3vs3_goal_kick_blue.json`
- `core/src/scenario/3vs3_default/` (4 files)

**Files deleted:**
- (none)

**Not yet done:**
- Warm-up call fix in `launch_r2k.sh` (curl warm-up after Ollama check,
  ~3 lines) — prevents cold-boot dead-blue-team. Deferred from 2026-07-23.
- Visualizer blitting refactor still untested with live ROS 2 + Gazebo
  (carried from 2026-07-14).
- Goalie-kick prompt rule (Phase 4b — `rules_goal_kick.txt` +
  `samples_goal_kick.txt`) — deferred to Phase 4 per spec.
- `run_baseline.sh` container restart between runs is fragile (watchdog
  kills gzserver, `docker compose down` destroys container). `systemd-run`
  workaround works but is not robust for unattended runs.
- Push 3 unpushed commits to origin.

**Next:**
- Phase 3: Model Comparison — `ollama pull cosmos`, run 135 runs (9 scenarios
  × 3 models × 5 runs), compare via regression suite, commit winning model.
- The user asked about which cosmos model is closest to qwen2.5-coder:3b
  by size — this needs to be resolved before Phase 3 (check Ollama registry
  for cosmos model sizes).

**Blockers:**
- `run_baseline.sh` reliability: watchdog + `docker compose down` race
  condition makes unattended baseline runs fragile. The `systemd-run`
  approach works but the script needs hardening (e.g., longer sleep after
  container restart, or suppress watchdog during baseline runs).
- Phase 3 requires `ollama pull cosmos` — cosmos model size/variant not
  yet determined. Need to check Ollama registry for available cosmos models
  closest to qwen2.5-coder:3b (~2GB).

## 2026-07-27 (continued) — Ollama bind-address bug: root cause + permanent fix

**Goal:** Diagnose recurring "blue bots don't move" on new U24 machine
(RTX 5090). Find the actual root cause (not the cold-boot race from
2026-07-23). Implement a permanent fix so future fresh installs don't hit
this.

**Done:**

### Root cause analysis (in-depth)

Symptom: blue bots frozen at start positions, zero `llm_trace` records,
no `current_strategy.json`, red bots move (algorithmic). Identical
symptom to 2026-07-23 cold-boot race — but different root cause.

**Forensic evidence chain:**
1. `world_trace` showed 490 records over 48.9s with valid blue entities
   at start positions — world model working, blue just not moving.
2. **Zero `llm_trace` records** — evaluator never logged a single LLM
   call. Not a parse error, not a timeout — the call never happened.
3. `ollama` journal (`journalctl -t ollama`): only ONE `/api/generate`
   call at 16:16:36 (my diagnostic curl from the previous session,
   30.587s cold load). During the match window (16:37-16:38): only
   `/api/tags` calls (model existence check from `launch_r2k.sh:155`),
   **zero `/api/generate` calls**. Evaluator never POSTed.
4. `shared_state/current_strategy.json` missing — evaluator never wrote
   a strategy → bridge had no targets → blue frozen.
5. `ss -tlnp | grep 11434`: `LISTEN 0 4096 127.0.0.1:11434` — Ollama
   bound to **loopback only**, not `0.0.0.0`.
6. `curl http://172.17.0.1:11434/api/tags` from host: **exit 7
   (connection refused)**. Ollama not listening on the Docker bridge
   gateway.
7. `curl http://172.17.0.1:11434/api/tags` from inside container:
   **connection refused**. Container cannot reach host's loopback.

**Root cause:** Ollama was started by the official installer's systemd
service (`ollama.service`, `Restart=always`, user `ollama`). The unit
file has no `OLLAMA_HOST` env var, so Ollama defaults to `127.0.0.1`
(loopback). The Docker container cannot reach the host's loopback — it
needs `172.17.0.1` (Docker bridge gateway), which requires
`OLLAMA_HOST=0.0.0.0`.

**Why `launch_r2k.sh` didn't catch it:** The Ollama check at
`launch_r2k.sh:155` only tests `127.0.0.1` (host loopback), which
succeeds. It prints "✅ Ollama ist bereits online" and moves on. The
container-reachability check (`172.17.0.1`) didn't exist. The evaluator
inside the container then silently fails with `ConnectionError` on every
poll loop → dead blue team.

**Why it wasn't the cold-boot race (2026-07-23):** That session had an
HTTP 499 (model load aborted by client disconnect). This session had
zero `/api/generate` calls at all — the evaluator never reached Ollama.
Same symptom, different cause. The cold-boot race is a *timing* issue;
this is a *network binding* issue.

**Why previous machines didn't hit this:** On U22 (native), the evaluator
runs on the host where `127.0.0.1` works. On U24 machines where
`launch_r2k.sh` started Ollama itself, the `export OLLAMA_HOST=0.0.0.0`
(line 159, inside the `else` branch) set the bind correctly. This machine
had Ollama started by systemd (not by `launch_r2k.sh`), so the `else`
branch was never taken, and the env var was never set.

### Immediate fix (user-applied)
- `sudo systemctl edit ollama` → added drop-in:
  `[Service]\nEnvironment="OLLAMA_HOST=0.0.0.0"`
- `sudo systemctl daemon-reload && sudo systemctl restart ollama`
- Verified: `ss -tlnp` now shows `*:11434` (all interfaces, was
  `127.0.0.1:11434`). Container can reach `172.17.0.1:11434` ✅.

### Permanent fix (code)

**`install.sh` (U24 branch, after `docker compose down`):**
- New block: detects `ollama.service` via `systemctl cat`. If present,
  creates systemd drop-in override at
  `/etc/systemd/system/ollama.service.d/override.conf` with
  `Environment="OLLAMA_HOST=0.0.0.0"`, reloads daemon, restarts
  service, verifies bind is `0.0.0.0:11434`. If `ollama.service` not
  found, prints warning to start Ollama manually with
  `OLLAMA_HOST=0.0.0.0`.
- Fully automated — no manual step needed on future fresh U24 installs.
- Idempotent — running `install.sh` twice doesn't break anything.

**`launch_r2k.sh` (two changes):**
1. Moved `export OLLAMA_HOST=0.0.0.0` from inside the `else` branch
   (line 159) to before the check (line 155). Now always set, so if
   `launch_r2k.sh` ever starts Ollama itself, it inherits the bind
   address. (Minor improvement — the main fix is the install.sh block.)
2. New container-reachability guard (after line 177, U24 only): tests
   `curl http://172.17.0.1:11434/api/tags`. If refused, prints
   actionable error (systemd fix + manual fix commands) and exits 1.
   This makes the failure **loud** instead of silent dead-blue-team.

**What this does NOT change:**
- Does NOT disable the systemd service (keeps auto-restart, aligns with
  AGENTS.md axiom 5 in spirit — service runs as user `ollama`, watchdog
  `pkill -9 ollama` still works, systemd just restarts it).
- Does NOT touch U22 (native mode, `127.0.0.1` works fine there).
- Does NOT require any manual step on future fresh installs.

### Three distinct "dead blue team" root causes (now disambiguated)

| Session | OS | Root cause | Fix |
|---|---|---|---|
| 2026-07-20 | U22 native | Stale GPU runner / CPU fallback (Xid 31) | `pkill -9 ollama` + restart |
| 2026-07-23 | U24 Docker | Cold-boot race (model still loading, HTTP 499) | Warm-up curl before launch (deferred) |
| 2026-07-27 | U24 Docker | Ollama bound to `127.0.0.1`, container needs `172.17.0.1` | `OLLAMA_HOST=0.0.0.0` systemd override (this session) |

All three produce the same symptom (dead blue, no `llm_trace`). The
`launch_r2k.sh` container-reachability guard now catches the third one
loudly. The first two require different mitigations (GPU restart,
warm-up curl) and are not fixed by this change.

**Files touched:**
- `core/install.sh` (U24 branch: +24 lines, Ollama bind-override block)
- `core/launch_r2k.sh` (OLLAMA_HOST export moved, +18 lines
  container-reachability guard)
- `core/docs/SESSION_CHANGELOG.md` (this entry)

**New files (untracked):**
- (none)

**Files deleted:**
- (none)

**Not yet done:**
- Warm-up call fix in `launch_r2k.sh` (curl warm-up after Ollama check,
  ~3 lines) — prevents cold-boot dead-blue-team (2026-07-23 root cause).
  Still deferred. Now distinct from the bind-address fix (this session).
- Visualizer blitting refactor still untested with live ROS 2 + Gazebo
  (carried from 2026-07-14).
- Slow test tier not run this session (user chose fast-only earlier).
- Live match not yet re-run after the bind fix — user should verify
  blue bots now move.
- Push unpushed commits to origin.

**Next:**
- User re-launches match to verify blue bots move with the bind fix.
- Implement warm-up call fix in `launch_r2k.sh` (~3 lines) for the
  cold-boot race (2026-07-23 root cause) — independent of this fix.
- Commit on `feature/ollama-bind-address-fix` (separate from the larger
  uncommitted body of work).

**Blockers:**
- `run_baseline.sh` reliability (carried from 2026-07-27).
- Phase 3 requires `ollama pull cosmos` — model size/variant not yet
  determined (carried from 2026-07-27).

## 2026-07-27 (continued) — Phase 2.5 spec amendment + code (KPIs, dynamic injection, hardening)

**Goal:** Insert Phase 2.5 between Phase 2 and Phase 3 — add 4 attack/passing/restart
KPIs, implement dynamic prompt injection (moved from Phase 4a), create minimal
game-phase fragments, harden `launch_r2k.sh` (warm-up curl) and `run_baseline.sh`
(container readiness). Phase 3 `cosmos` model dropped (technically too divergent
from Ollama architecture); replacement lineup TBD. Update v6.2 spec to reflect
the new phase ordering.

**Done:**

### Spec update — `optimization_spec_v6.2.md` (+351/-94 lines)
- Frontmatter: `last_updated: 2026-07-27`, new tags (phase-2.5, attack-kpis,
  shot-on-goal, pass-completion, restart-recovery)
- §0 Management Summary: 6→7 phases, Phase 2 ✅ DONE, Phase 2.5 ⬜ Next,
  Phase 3 ⬜ Blocked by 2.5, Phase 4 reworked (45→~10 runs), total 207→232 runs
- §0 Key metrics: 14→19 KPI table with Phase-added column + composite-bias
  warning callout (27-run baseline showed blue scores ~0.3 goals/match with
  77% possession — composite is dominated by `goal_diff_norm` but blue can't
  score; adding `shots_on_goal` / `pass_completion_pct` first makes Phase 3
  model comparison soccer-meaningful)
- §1 Architecture diagram: "Phase 4" → "Phase 2.5b/2.5"
- §4.2 Fragment taxonomy: "Phase 4 introduces" → "Phase 2.5b implements";
  ~20 lines → ~35 lines; clarified game-phase fragments are ADDITIVE to mode
  fragments (not replacements); no rename of `rules_3vs3.txt` needed
- §4.5 TC-10: "Phase 4a" → "Phase 2.5b"
- §5.1 KPI table: 15→19 rows, 4 new KPIs marked **[2.5]**:
  - `shots_on_goal` — Kick actions (kicker in opp half, ball ≤2m) where ball
    moves toward opp goal after kick (world+llm join)
  - `shots_on_target` — subset where ball Y at x=4.5 within ±1.3m (goal posts)
  - `pass_completion_pct` — % Pass actions where different blue bot closest to
    ball within 2s (world+llm join)
  - `restart_recovery_time_s` — mean time from `status != "playing"` to
    restart-team bot within 0.35m of ball (pure world_trace)
- §7 Phases: Phase 2 marked DONE with checkpoint; **new Phase 2.5**
  (lines 1110-1290, 8 sub-steps: pre1, pre2, a, b, c, d, e, f); Phase 3
  reworked (cosmos dropped, lineup TBD, v6.3 baseline reference, 4 new KPIs
  used for comparison); Phase 4 reworked (4a→2.5b, 4b→2.5c, now fragment
  iteration + TC-10, ~10 runs)
- §8 Run Budget: updated with Status column, 172 new runs (excl. done)
- §10 Related files: `test_non_functional.py` ✅, evaluator "Phase 2.5b",
  TC-10 "Phase 4b"
- §11 Open Questions: Q2 updated (cosmos dropped), Q5 updated (2.5b
  implemented), new 2026-07-27 decisions block (Q12-Q16)

### 2.5-pre1: Warm-up curl in `launch_r2k.sh` (+13 lines)
- After the model-availability check (line 177), added a warm-up curl:
  `curl -s --max-time 120 "${OLLAMA_LOCAL}/api/generate" -d
  '{"model":"$MODEL","prompt":"hi","stream":false}' > /dev/null 2>&1`
- Prevents the cold-boot dead-blue-team race (2026-07-23 root cause): first
  match after `ollama serve` starts triggers a 30-40s model load; if the user
  interrupts during load → evaluator killed → no `current_strategy.json` →
  dead blue. The warm-up blocks until the model is resident in VRAM.
- `bash -n launch_r2k.sh` passes syntax check.

### 2.5-pre2: Harden `run_baseline.sh` (+81/-40 lines, full rewrite)
- New `wait_for_container()` function: waits for any in-flight `docker compose
  down` from the previous run's EXIT trap to complete (up to 15s, then forces
  down), then brings the container up and waits for `ros2 topic list` to
  respond inside the container (up to 60s). Eliminates the watchdog +
  `docker compose down` race that made unattended 27-run sweeps fragile.
- Added `[prefix]` CLI argument: `bash tools/run_baseline.sh baseline_v63`
  for the Phase 2.5d v6.3 re-baseline (default: "baseline"). All output
  filenames use the prefix.
- `bash -n run_baseline.sh` passes syntax check.

### 2.5a: 4 attack/passing/restart KPIs in `analyze_trace.py` (+248 lines)
- New `compute_attack_kpis(world_records, llm_records)` function — joins
  `llm_trace` (Kick/Pass actions + `world_snapshot` at decision time) with
  `world_trace` (ball position deltas after the action).
- 10 new named constants at module top (Phase 2.5a thresholds):
  `OPP_GOAL_X=4.5`, `GOAL_HALF_WIDTH=1.3`, `SHOT_KICKER_OPP_HALF=0.0`,
  `SHOT_BALL_NEAR_KICKER=2.0`, `SHOT_BALL_VX_THRESHOLD=0.5`,
  `SHOT_FOLLOW_FRAMES=5`, `PASS_FOLLOW_FRAMES=20`, `RESTART_TOUCH_DIST=0.35`
  (0.35 not 0.3 to account for tracker noise — referee uses 0.3m for early
  termination, tracker rounds to 0.1m precision), `SHOT_EXTRAPOLATE_FRAMES=10`.
- Binary-search time-indexed lookup (`find_world_frame_after`) for efficient
  post-action frame scanning.
- `shots_on_goal`: Kick action where kicker x > 0, ball within 2m of kicker,
  AND ball x-velocity > 0.5 m/s in the 5 frames (0.5s) after the LLM call.
- `shots_on_target`: subset of shots where ball Y extrapolated to x=4.5 is
  within ±1.3m (goal posts).
- `pass_completion_pct`: Kick by passer/receiver/midfielder (not in opp half)
  where a DIFFERENT blue bot is closest to ball within 20 frames (2s).
- `restart_recovery_time_s`: mean time from `status != "playing"` transition
  to first frame where restart-team bot within 0.35m of ball. `restart_events`
  count also returned. Pure `world_trace` computation.
- Updated `extract_assignments()` to use module-level `re` import (was
  `__import__('re')` inline — cleaner).
- `main()` calls `compute_attack_kpis()` and merges results into `world_kpis`
  dict (backward-compatible output structure).
- Human-readable summary now prints shots/passes/restarts section.
- **Verification gate passed:** Ran against existing baseline trace files:
  - `3vs3_attack_center`: 6 shots on goal (1 on target), 142 pass attempts
    (88.0% completed), 2 restart events (4.4s mean recovery)
  - `3vs3_high_line`: 3 shots on goal (1 on target), 135 pass attempts
    (88.9% completed), 4 restart events (10.0s mean recovery)
  - All 4 KPIs produce sensible numbers, no crashes, no NaN.

### 2.5b: Dynamic prompt injection in `r2k_evaluator.py` (+89 lines)
- New constants: `FRAGMENTS_DIR`, `SCENARIO_PATH` (reads
  `ai_tactics/active_scenario.json` written by `setup_r2k.py` at boot).
- New `_determine_mode()`: reads mode from `active_scenario.json`, falls back
  to "3vs3" if unavailable. Called once at startup, cached in `_active_mode`.
- New `_read_fragment(name)`: reads a fragment file, returns empty string if
  missing (no crash on FileNotFoundError).
- New `_assemble_prompt(status, mode)`: assembles prompt from fragments:
  1. `header.txt` (static)
  2. `rules_core.txt` (static)
  3. `rules_<status>.txt` (game-phase, ADDITIVE — only if status != "playing"
     and file exists)
  4. `rules_<mode>.txt` (mode rules — always loaded; IS the playing rules
     when status == "playing")
  5. `samples_<status>.txt` (game-phase, ADDITIVE — only if status != "playing"
     and file exists)
  6. `samples_<mode>.txt` (mode samples — always loaded)
  No rename of `rules_3vs3.txt` needed — the mode fragment IS the playing
  fragment. Game-phase fragments are additive for non-playing statuses only.
- New `_get_sys_prompt(status)`: caches by `(status, mode)` tuple. Re-reads
  fragment files only on status transitions (rare — <10 per match). Without
  caching, fragment file reads would add I/O latency to every 20ms poll.
- Main loop: replaced `with open(PROMPT_PATH, 'r') as f: sys_prompt = f.read()`
  with `sys_prompt = _get_sys_prompt(status)` where `status` comes from
  `world_data.get("match_state", {}).get("status", "playing")`.
- `PROMPT_PATH` / `system_prompt.txt` still written by `setup_r2k.py` at boot
  for `dump_prompt.py` dry-runs. The evaluator just no longer reads it at
  runtime — it assembles from fragments directly.
- **Verification gate passed:** Standalone test confirmed:
  - `playing` prompt = 2015 chars (mode fragment only, no game-phase)
  - `ball_out` prompt = 2226 chars (mode + `rules_ball_out.txt` stub)
  - `STATUS: ball_out` correctly present in ball_out prompt, absent in playing
  - All 91 fast tests pass, all 7 integration smoke tests pass.

### 2.5c: Minimal game-phase fragments (4 new files, ~8 lines total)
- `strategy/fragments/rules_ball_out.txt` (2 lines)
- `strategy/fragments/rules_goal_kick.txt` (2 lines)
- `strategy/fragments/rules_corner_kick_in.txt` (2 lines)
- `strategy/fragments/rules_kickoff.txt` (2 lines)
- No `samples_<status>.txt` stubs — mode samples serve as base for all
  statuses. Game-phase samples deferred to Phase 4.
- No rename of `rules_3vs3.txt` / `samples_3vs3.txt` — the evaluator's
  additive design means mode fragments are the base "playing" rules.
- `setup_r2k.py` requires NO changes.
- `test_integration_smoke.py::test_strategy_files_exist`: added 4 new
  fragments to the required-files list. Test passes.

### Tests
- All 91 fast tests pass (`python3 -m pytest tests/ --skip-slow -v`).
- All 7 integration smoke tests pass.
- `analyze_trace.py` verified on 2 existing baseline trace files — 4 new KPIs
  produce sensible numbers.
- `r2k_evaluator.py` dynamic injection verified standalone — prompt changes
  on status transition, no crash on missing game-phase fragment.

**Files touched:**
- core/docs/optimization_spec_v6.2.md (spec amendment, +351/-94)
- core/launch_r2k.sh (warm-up curl, +13)
- core/src/ai_tactics/r2k_evaluator.py (dynamic injection, +89)
- core/src/tools/analyze_trace.py (4 new KPIs, +248)
- core/src/tools/run_baseline.sh (hardening, +81/-40 full rewrite)
- core/src/tests/test_integration_smoke.py (4 new fragments in required list)
- core/docs/SESSION_CHANGELOG.md (this entry)

**New files (untracked):**
- src/strategy/fragments/rules_ball_out.txt
- src/strategy/fragments/rules_goal_kick.txt
- src/strategy/fragments/rules_corner_kick_in.txt
- src/strategy/fragments/rules_kickoff.txt
- docs/student_projects_autumn_fair.md (carried from prior session, not this session's work)

**Files deleted:**
- (none)

**Not yet done:**
- **2.5d: v6.3 re-baseline** — requires live Gazebo + Ollama environment to
  run 27 unattended matches (~45min). All code prerequisites are in place
  (warm-up curl, hardened `run_baseline.sh`, 4 new KPIs, dynamic injection,
  game-phase fragments). This is compute work, not code work.
- **2.5e: Regression suite update** — add 4 new KPI targets to all 11
  `kpi_targets.json` (calibrated from 2.5d baseline) + 4 assertions to slow
  tests. Blocked by 2.5d (need real data to calibrate thresholds).
- **2.5f: KB + docs update** — FAQ Q16 (15→19 KPIs), `META_ROUTER` routing
  entries, `6_DATA` KPI table, `3_AI` dynamic injection status, `AGENTS.md`
  KPI count. Blocked by 2.5e (spec already updated; KB update follows the
  regression suite).
- **Live match not yet re-run** — the dynamic injection + warm-up curl +
  game-phase fragments need a live match to verify the `llm_trace` shows
  `sys_prompt_hash` changing on status transitions. Standalone test
  confirmed the prompt assembly works, but end-to-end with ROS 2 + Gazebo
  is the real gate.

**Next:**
1. **Run a live match** to verify dynamic injection end-to-end: launch
   `./launch_r2k.sh --scenario 3vs3_attack_center --relay only_sim_bots`,
   check `logs/llm_trace_*.jsonl` for `sys_prompt_hash` changes when
   `match_state.status` transitions.
2. **Run 2.5d v6.3 re-baseline**: `bash tools/run_baseline.sh baseline_v63`
   (~45min unattended). Verify all 27 runs produce KPIs (warm-up curl
   prevents dead-blue).
3. **2.5e: Calibrate 4 new KPI targets** from v6.3 baseline + 30-50% margin,
   add assertions to `test_non_functional.py`.
4. **2.5f: KB + docs update**.
5. Commit on `feature/phase-2.5-attack-kpis-dynamic-injection` (separate
   from the larger uncommitted body of work). Suggested commit boundaries:
   - `fix: warm-up curl + run_baseline.sh hardening` (pre1 + pre2)
   - `feat: add 4 attack/passing/restart KPIs to analyze_trace.py` (2.5a)
   - `feat: dynamic prompt injection + minimal game-phase fragments` (2.5b + 2.5c)
   - `docs: Phase 2.5 spec amendment` (spec, already done)
   - `test: v6.3 baseline + regression thresholds for 4 new KPIs` (2.5d + 2.5e, after compute)
   - `docs: Phase 2.5 KB update` (2.5f, after 2.5e)

**Blockers:**
- **Live Gazebo + Ollama required** for 2.5d (27-run re-baseline). All code
  is ready; this is compute work. Ollama GPU state unverified this session
  (carried from 2026-07-27: user must restart ollama with
  `OLLAMA_HOST=0.0.0.0` if not already configured via the install.sh
  systemd override fix from the prior session).
- `batch_evaluator.py` KPI collection still broken (deprecated, Phase 2b
  regression suite is the replacement — orthogonal to Phase 2.5).
- Visualizer blitting refactor still untested with live ROS 2 + Gazebo
  (carried from 2026-07-14, orthogonal to Phase 2.5).

## 2026-07-28 — Role condensation, explain-mode fix, visualizer labels, content-hash skip

**Goal:** Condense LLM roles from 5 to 3 (KISS), fix `--explain` flag broken
by Phase 2.5b dynamic injection, fix visualizer labels + copyable output,
and eliminate 64% wasted LLM calls via content-hash skip.

**Done:**

### Role condensation: 5 → 3 (goalie/attacker/defender)

Replaced `striker`/`midfielder`/`passer`/`receiver`/`supporter` with
`goalie`/`attacker`/`defender` across all fragments. The bridge only
checks `role == 'goalie'` — all other roles were cosmetic noise the 3B
model had to generate without any consumer caring.

- `rules_3vs3.txt:3`: Striker/Midfielder/Goalie → Attacker/Defender/Goalie
- `rules_3vs1.txt`, `rules_2vs2.txt`, `rules_2vs1.txt`, `rules_1vs1.txt`:
  striker/supporter → attacker/defender
- `samples_3vs3.txt`: passer/receiver → attacker/defender
- `samples_3vs1.txt`, `samples_2vs2.txt`, `samples_2vs1.txt`,
  `samples_1vs1.txt`, `samples_1vs0.txt`, `samples_recover.txt`: all
  role names updated
- `analyze_trace.py:217`: pass detection changed from role-based
  (`role in ('passer','receiver','midfielder')`) to position-based
  (kicker NOT in opponent half = pass attempt). Role-independent.
- `analyze_trace.py`: dropped `role_diversity` KPI (dead metric, CV=0%
  across 27 v6.3 baseline runs, always 5.0). Kept `roles` counter as
  diagnostic only.
- `r2k_visualizer.py:303`: auto-adapts (role[0].lower() → g/a/d)

### Explain-mode flag fix (broken by Phase 2.5b dynamic injection)

**Root cause:** Phase 2.5b's `_assemble_prompt()` reads fragments
directly, bypassing `setup_r2k.py`'s `clean_json_samples()`. The
`header.txt` had no `{{EXPLAIN_INSTRUCTION}}` placeholder (removed during
Phase 0 disentanglement). The evaluator detected explain mode by
string-matching `"analysis" in sys_prompt.lower()` — always False →
`num_predict` always 150 → `--explain` silently ignored.

- `strategy/fragments/header.txt`: restored `{{EXPLAIN_INSTRUCTION}}`
  placeholder (line 4)
- `r2k_evaluator.py:_assemble_prompt()`: replaces
  `{{EXPLAIN_INSTRUCTION}}` using `R2K_EXPLAIN` env var (0 → assignments-
  only, 1 → analysis+oracle+assignments)
- `r2k_evaluator.py:190`: replaced string-matching detection with
  `os.getenv("R2K_EXPLAIN", "0") == "1"` (direct env var check)
- `launch_r2k.sh:60`: `export R2K_EXPLAIN=$([[ "$EXPLAIN_FLAG" == "--explain" ]] && echo 1 || echo 0)`
- `launch_r2k.sh:402`: added `-e R2K_EXPLAIN="$R2K_EXPLAIN"` to Docker
  evaluator exec
- `r2k_evaluator.py`: duplicated `clean_json_samples()` from
  `setup_r2k.py` (~70 lines) — needed at runtime to inject default
  analysis/oracle strings into samples. Without this, Qwen 3B fills
  oracle with JSON strategy data instead of text.
- Applied `_clean_json_samples()` to sample fragments in
  `_assemble_prompt()` (mode + game-phase samples)

### Visualizer labels + copyable output

- `r2k_visualizer.py:432`: renamed labels — `### AI ANALYSIS ###` →
  `### STRATEGY ###`, `### STRATEGY ORACLE ###` → `### ORACLE ###`.
  Semantics: STRATEGY = analysis field (what to do), ORACLE = oracle
  field (what will happen).
- `r2k_visualizer.py:429-434`: guard against JSON in oracle/analysis
  fields — if dict/list, shows `(invalid - JSON in oracle field)` instead
  of raw JSON blob
- `r2k_visualizer.py:517-520`: print `[STRATEGY]` / `[ORACLE]` to terminal
  on each strategy update (copyable from terminal scrollback)

### Content-hash skip (64% LLM call reduction)

**Root cause:** Aggregator writes Worldstate.json at 10Hz unconditionally
(67% of writes have identical positions) → mtime changes → evaluator
triggers LLM call → identical input at temperature:0.0 → identical output
→ 64% of calls wasted (153s GPU time per 120s match). Repetitive
visualizer output was the visible symptom.

- `r2k_evaluator.py:240`: `last_ents_hash = 0` initialization
- `r2k_evaluator.py:259-266`: hash entities JSON, skip LLM call if
  identical to previous call. ~7 lines.
- Impact: ~62 calls per match (was 171), no repetition, ~153s GPU saved.
- **Game changer:** effective delay (situation change → strategy output)
  drops from ~1328ms to ~684ms (~50%). Evaluator is idle 64% of the time
  instead of busy — reacts to real changes within ~20ms (one poll cycle)
  instead of waiting up to 664ms for a redundant call to finish.

### Test case: oracle-is-string validation

- `tests/test_prompt_assembly.py` (NEW): `test_oracle_is_string_in_trace`
  — validates that oracle and analysis fields in the latest llm_trace
  are strings, not JSON dicts. Catches the regression where Qwen 3B
  fills oracle with assignments JSON.

### Soccer tech speech experiment (reverted)

Attempted to reduce `--explain` latency by replacing verbose
analysis/oracle defaults with terse "soccer tech speech" (e.g.
`"ball pos, formation, threat"` / `"assign roles, execute"`). Expected
~25 tokens instead of 93. However: the LLM copied the oracle default
verbatim (131/132 calls), and the labels broke (user reported JSON in
oracle field). Reverted all changes to the last working state (verbose
defaults, oracle injection, no markdown stripping in fast_parse).

### Identified but not fixed

- **Qwen 3B spatial reasoning hallucination:** 73% of `--explain` calls
  produce "ball is near the opponent's goal, but it's also close to our
  own goal" even when ball is at center (x=0.0, equidistant from both
  goals at x=±4.5). This is a model capability limitation, not a prompt
  bug. The `analysis`/`oracle` fields are display-only — the bridge only
  reads `assignments`. Decision deferred.
- **Further latency reduction:** The 664ms LLM inference is 97% of the
  remaining delay. Only Phase 5.1 (Kalman + predictive world model)
  can offset it — send the LLM where the ball WILL BE in 664ms. That's
  a 6-month internship project.

**Files touched:**
- core/src/strategy/fragments/header.txt (restored {{EXPLAIN_INSTRUCTION}})
- core/src/strategy/fragments/rules_3vs3.txt (roles: Attacker/Defender/Goalie)
- core/src/strategy/fragments/rules_3vs1.txt (roles)
- core/src/strategy/fragments/rules_2vs2.txt (roles)
- core/src/strategy/fragments/rules_2vs1.txt (roles)
- core/src/strategy/fragments/rules_1vs1.txt (roles)
- core/src/strategy/fragments/samples_3vs3.txt (roles: attacker/defender)
- core/src/strategy/fragments/samples_3vs1.txt (roles)
- core/src/strategy/fragments/samples_2vs2.txt (roles)
- core/src/strategy/fragments/samples_2vs1.txt (roles)
- core/src/strategy/fragments/samples_1vs1.txt (roles)
- core/src/strategy/fragments/samples_1vs0.txt (roles)
- core/src/strategy/fragments/samples_recover.txt (roles: attacker/defender)
- core/src/ai_tactics/r2k_evaluator.py (explain fix, clean_json_samples
  duplication, content-hash skip, R2K_EXPLAIN env var)
- core/src/r2k_visualizer.py (labels rename, JSON guard, terminal print)
- core/src/setup_r2k.py (no net change — soccer tech speech reverted)
- core/src/tools/dump_prompt.py (no net change — reverted)
- core/src/tools/analyze_trace.py (position-based pass detection,
  drop role_diversity)
- core/launch_r2k.sh (R2K_EXPLAIN export + Docker passthrough)
- core/docs/SESSION_CHANGELOG.md (this entry)

**New files (untracked):**
- core/src/tests/test_prompt_assembly.py (oracle-is-string test)

**Files deleted:**
- (none)

**Not yet done:**
- Soccer tech speech for analysis/oracle defaults — attempted, reverted.
  The LLM copies terse oracle verbatim (131/132 calls). Need a different
  approach (e.g. multiple samples with varying oracle, or drop oracle
  from sample and let LLM generate freely). Decision deferred.
- Markdown wrapper stripping in fast_parse — attempted, reverted. The
  ` ```json ` wrapper doesn't actually break fast_parse (it finds
  `{` and `}` correctly). The labels issue was a semantic
  misunderstanding, not a parse bug.
- KPI cleanup (2.5e): drop 3 dead KPIs + lat_mean from
  kpi_targets.json + test_non_functional.py assertions. Regression
  analysis complete, application deferred.
- KB + docs update (2.5f): FAQ Q16 (15→16 KPIs), routing entries,
  dynamic injection status, AGENTS.md KPI count. Deferred.
- Nothing committed — all work uncommitted on
  `feature/ros2k_behavior_optimization`.

**Next:**
- Live `--explain` run to verify: (1) content-hash skip eliminates
  repetition, (2) visualizer shows `### STRATEGY ###` / `### ORACLE ###`
  with text, (3) terminal prints `[STRATEGY]` / `[ORACLE]` copyable
  text, (4) ~62 LLM calls per match (was 171)
- Then commit all work (role condensation + explain fix + visualizer
  labels + content-hash skip + test case)

**Blockers:**
- Ollama GPU state unverified (carried from 2026-07-27)
- `batch_evaluator.py` KPI collection still broken (deprecated, carried
  from 2026-07-13)
- Visualizer blitting refactor still untested with live ROS 2 + Gazebo
  (carried from 2026-07-14)

## 2026-07-28 (continued) — Replay system: match annotator, trace replay, visualizer --replay mode

**Goal:** Build a replay system for saved and annotated ROS2K sim games —
freeze Gazebo during a live match to annotate moments, then replay the
saved match with the visualizer showing annotations + LLM decisions +
ball trajectory. Recover from an interrupted session (license limit).

**Done:**

### Match annotator (`tools/match_annotate.py`, NEW — 327 lines)
- Run alongside a live match. Press ENTER to pause Gazebo (via
  `/gazebo/pause_physics`), record game state + last LLM decision + your
  comment, then unpause.
- Writes `logs/annotations_<run_id>.jsonl` for post-match replay.
- Supports both native (U22) and Docker (U24) `ros2` invocations via
  `get_ros2_prefix()` detection (checks `shutil.which("ros2")`, falls
  back to `docker exec core_gazebo bash -c "source ... && ros2"`).
- `atexit` cleanup unpauses Gazebo if interrupted while paused.
- Reads `R2K_RUN_ID` from env, falls back to latest `world_trace_*` file.
- Records: `t_sim`, `t_wall`, `paused`, `score`, `status`, `snapshot`
  (all entity positions), `last_llm_decision` (assignments + analysis +
  oracle + latency), `comment`, `annotation_index`.

### Trace replay tool (`tools/replay_trace.py`, NEW — 251 lines)
- Post-match CLI review: loads annotations + `llm_trace` + `world_trace`,
  shows for each annotation the LLM decision before it, game state
  snapshot, and ball trajectory + events (goals, status changes) in the
  5 seconds after.
- Interactive mode (ENTER for next annotation, q to quit) or `--all`
  (dump all to stdout for markdown piping).
- `--forward N` controls scan window (default 5s).
- Binary-search time-indexed lookup for efficient frame scanning.

### Visualizer `--replay` mode (`r2k_visualizer.py`)
- **`--replay RUN_ID`** CLI arg: replays a saved match from trace files
  with no ROS 2 required. Loads `world_trace`, `llm_trace`, `annotations`
  from `logs/`.
- **`--speed N`**: playback speed multiplier (default 1.0 = real time).
  `--speed 5` plays 5x faster.
- **`--start N`**: seek to N seconds from match start (default 0.0).
- `main_replay()` function: normalizes all timestamps to "seconds from
  first world_trace record" using `t_wall` (wall-clock). Sim-time (`t`)
  is 0.0 in all existing traces (the `/clock` subscription +
  `libgazebo_ros_init.so` was added but not yet rebuilt/deployed when
  these traces were recorded — the sim-time field exists but is always 0).
- Pre-parses all LLM decisions once at load time (`_parse_llm_decision`
  extracts assignments/analysis/oracle/latency from each `llm_trace`
  record). Avoids re-parsing on every frame.
- Replay loop: advances `w_idx` through `world_trace` records based on
  real elapsed wall-time x speed. For each world frame, finds the latest
  LLM decision at or before that timestamp via `bisect.bisect_right`.
  Prints `[STRATEGY]` / `[ORACLE]` to terminal on new LLM decision
  (matches live mode behavior).
- Annotation overlay: yellow text bar at top-center, shown for 5s when
  replay crosses an annotation timestamp. Prints annotation to terminal.
- Reuses `init_figure` + `update_figure` + `process_match_state` — no
  duplicate rendering code. `process_match_state` was extracted from the
  ROS callback into a standalone function (parameterized by `t_sim`)
  so both live and replay modes can call it.
- `HAS_ROS2` import guard: `rclpy` import wrapped in try/except. When
  unavailable (replay mode on a machine without ROS 2), a `Node` stub
  class is defined so the `VisualizerROSNode` class definition doesn't
  raise `NameError`. The live `main()` checks `HAS_ROS2` and exits with
  a helpful message if rclpy is missing.
- `argparse` in `main()`: routes to `main_replay()` if `--replay` is set,
  otherwise starts live mode (requires rclpy).

### Supporting changes

- `state_aggregator.py`: added `/clock` subscription (`Clock` from
  `rosgraph_msgs.msg`) and records `sim_time` in `world_trace` `t`
  field (was wall-time `time.time()`). `t_wall` retained for correlation.
  Required so paused annotations don't create time gaps in replay.
- `soccer_match.launch.py`: added `libgazebo_ros_init.so` to both
  `gzserver` (headless) and `gazebo` (GUI) launch commands — needed for
  `/clock` topic and pause/unpause services.
- `reward_node.py`: zero-delta skip — if `reward == 0` and score hasn't
  changed, clear the pending action and return immediately (was logging
  a spurious "neutral" reward every timeout).
- `r2k_visualizer.py` `update_figure`: JSON guard for oracle/analysis
  fields (if dict/list, shows `(invalid - JSON in oracle field)` instead
  of raw JSON blob). Label rename: `AI ANALYSIS` -> `STRATEGY`,
  `STRATEGY ORACLE` -> `ORACLE`.
- `r2k_visualizer.py` `init_figure`: added `annotation_overlay` text
  artist (top-center, yellow text on dark background, shown in replay
  mode).

### Verification
- All 3 files compile (`py_compile`).
- Replay data loading verified: 531 world records, 31 LLM records, 2
  annotations loaded from a real run.
- Replay loop verified headless (Agg backend): played through 53s match
  at 20x speed, printed 46 STRATEGY/ORACLE lines (explain-mode run) and
  annotation overlays. Exited cleanly.
- 92 fast tests pass (was 91 + 1 new `test_prompt_assembly.py`), 11
  skipped. No regressions.
- `--help` output correct for all 3 args (`--replay`, `--speed`,
  `--start`).

**Files touched:**
- `core/src/r2k_visualizer.py` (`--replay` mode, `main_replay()`,
  `process_match_state` extraction, annotation overlay, JSON guard,
  label rename, `HAS_ROS2` import guard, `Node` stub, argparse in main)
- `core/src/state_aggregator.py` (`/clock` subscription, sim-time in
  world_trace, `t_wall` retained)
- `core/src/reward_node.py` (zero-delta skip)
- `core/src/ros2_ws/src/r2k_scenario_spawner/launch/soccer_match.launch.py`
  (`libgazebo_ros_init.so`)
- `core/docs/SESSION_CHANGELOG.md` (this entry)

**New files (untracked):**
- `core/src/tools/match_annotate.py` (live match annotation tool)
- `core/src/tools/replay_trace.py` (post-match annotation review CLI)

**Files deleted:**
- (none)

### `--analyze` flag and annotator Docker fix (continuation)

- `launch_r2k.sh`: added `--analyze` flag. Spawns `match_annotate.py` in a
  new terminal (gnome-terminal/xterm/konsole auto-detected) after the
  container and all nodes are up. Passes `PROJECT_NAME`,
  `COMPOSE_PROJECT_NAME`, `R2K_RUN_ID` as inline env vars. Moved from
  early-boot (container not yet running) to right before visualizer
  launch in both native (U22) and Docker (U24) branches.
- `match_annotate.py` `get_ros2_prefix()`: fixed container detection.
  Was: hardcoded `"core_gazebo"` fallback + host `source /opt/ros/humble/setup.bash`
  (fails on U24 where ROS 2 is only in the container). Now: reads
  `PROJECT_NAME` or `COMPOSE_PROJECT_NAME` env var → derives
  `${project}_gazebo` container name, validates against `docker ps`,
  sources both `setup.bash` AND `ros2_ws/install/setup.bash` inside the
  container. Returns `None` (with clear error) if no container found.
- `replay_trace.py` `find_run_id()`: changed default from newest
  `annotations_*` to newest `world_trace_*` — annotations are optional,
  the last game should always be found.
- `r2k_visualizer.py` `--replay`: made RUN_ID optional (`nargs="?"`).
  `--replay` alone defaults to the last game (newest `world_trace_*`).

### Verification (additional)
- `replay_trace.py` with no args: loads last game (229 world records,
  14 LLM records, 0 annotations) — works without annotations.
- `r2k_visualizer.py --replay` (no RUN_ID): prints
  "Replaying last game: <run_id>" and plays the match.
- `--analyze` flag: `bash -n` passes, annotator opens after container
  is up. Debug output confirms `PROJECT_NAME='core'`, container found.
- Annotator Docker detection still needs live verification (container
  was down during testing — debug showed `containers=[]`).

**Files touched (additional):**
- `core/launch_r2k.sh` (`--analyze` flag, `launch_annotator()` function,
  moved annotator spawn to post-container-up)
- `core/src/tools/match_annotate.py` (container detection fix,
  `PROJECT_NAME`/`COMPOSE_PROJECT_NAME` env, `ros2_ws/install` source,
  `ROS2_PREFIX=None` handling, debug output)
- `core/src/tools/replay_trace.py` (default to newest `world_trace_*`)
- `core/src/r2k_visualizer.py` (`--replay` RUN_ID optional, defaults to
  last game)

**Not yet done:**
- `libgazebo_ros_init.so` added to launch file but NOT rebuilt into the
  Docker container — existing traces all have `t=0.0` (sim-time not
  flowing). Needs `docker exec ... colcon build` to deploy, then a new
  match to record traces with working sim-time.
- Replay not tested with live TkAgg backend (only headless Agg). The
  visualizer window should display the match playback, but no human has
  watched it yet.
- `--analyze` annotator Docker detection needs live verification (run
  with a running container to confirm `ROS2_PREFIX` finds it and
  `/gazebo/pause_physics` works).
- Nothing committed — all work uncommitted on
  `feature/ros2k_behavior_optimization`.

**Next:**
- Commit the replay system on a dedicated branch
  (`feature/replay-system`) or fold into the next commit on
  `feature/ros2k_behavior_optimization`.
- Rebuild Docker container with `libgazebo_ros_init.so` and record a new
  match with working sim-time, then verify replay uses sim-time
  correctly.
- Live TkAgg test: run `python3 r2k_visualizer.py --replay <run_id>`
  on a machine with display, verify the visualizer window plays the
  match with annotation overlays.

**Blockers:**
- Ollama GPU state unverified (carried from 2026-07-27)
- `batch_evaluator.py` KPI collection still broken (deprecated, carried
  from 2026-07-13)
- Visualizer blitting refactor still untested with live ROS 2 + Gazebo
  (carried from 2026-07-14 — now also applies to replay mode TkAgg)
