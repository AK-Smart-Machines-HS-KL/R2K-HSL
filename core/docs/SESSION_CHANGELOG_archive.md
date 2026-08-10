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

## 2026-07-29 — Replay nav fix, --nav deprecation, log name display, Phase 2.5f KB + docs update

**Goal:** Fix broken replay `b`-key (off-by-one after `f`-jump), make nav
always-on in replay mode (deprecate `--nav`), add log file name display,
add arrow-key seek + `--live` flag, and complete Phase 2.5f (KB + docs
update to reflect 2.5d/e done state).

**Done:**

### Replay visualizer fixes (`r2k_visualizer.py`)
- **`b`-key off-by-one fix** (`on_key` handler, line 696-712): After an
  `f`-jump to annotation #2, `cur_t` lands at the nearest world record
  (e.g. 26.500s for an annotation at 26.486s). The old `bisect_left(...) - 1`
  re-selected the same annotation (jump_idx=1 = current). Fixed: both `f`
  and `b` now use `bisect_right(...) - 1` + a 0.5s "skip current" check so
  neither no-ops when sitting on an annotation after a jump.
- **`--nav` deprecated** (line 845-846): `argparse.SUPPRESS` hides the flag
  from `--help`. `main_replay()` always called with `nav=True`. Controls
  hint updated to mention `ctrl+f=fullscreen` (since `f` is rebound to
  next-annotation).
- **`--live` flag added** (line 858-862): No-args now defaults to replaying
  the last saved match (was: live mode). `--live` opts into live mode.
  `launch_r2k.sh` untouched (calls `python3 r2k_visualizer.py` with no args
  → now replays instead of live; if live is needed via launcher, add
  `--live` manually).
- **Arrow-key seek** (line 687-695): `←`/`→` seek ∓5 seconds (clamped to
  match duration). Uses existing `seek_target` mechanism — main loop handles
  the jump + clock reset.
- **Log file name display**: Terminal prints `Log: <run_id>` at startup
  (line 617). Window title bar shows `R2K Replay — <run_id>` (line 644).
- **Content-hash skip note**: updated AGENTS.md gotcha to note
  `current_strategy.json` mtime is unreliable with content-hash skip.
- 92 fast tests pass, no regressions.

### Phase 2.5f — KB + docs update (7 files)

**`optimization_spec_v6.3.md`** (spec correction):
- Phase 2.5 table row: ⬜ → ✅ **DONE**
- Phase 2.5 section header: ⬜ NEXT → ✅ DONE
- 2.5d, 2.5e markers: ⬜ → ✅ DONE (commit `532360b`)
- 2.5f marker: ⬜ IN PROGRESS
- Phase 3 header: "BLOCKED BY PHASE 2.5d" → "NEXT (UNBLOCKED)"
- Run budget table: 2.5 re-baseline ⬜ → ✅, total 172 → 145 new runs
- Fixed stale "15 → 19 KPIs" → "15 → 18 KPIs" in 2.5f section
- Noted stored v6.3 baseline JSONs show 0 for 4 new attack KPIs (generated
  before t_wall bugfix; code fix committed, JSONs need re-run)

**`ROS2K_GEM_FAQ.md`** (v6.2 → v6.3, +Q25/Q26):
- Front matter: v6.2 → v6.3, tags updated, addendum header rewritten
- Q16: "15 KPIs" → "18 KPIs", added 4 new attack KPIs to the list,
  removed `role_diversity` and `avg_response_tokens`
- Q19: rewritten — documents dynamic prompt injection (runtime assembly
  from fragments, game-phase additive, `sys_prompt_hash` in trace),
  role condensation (5→3), updated fragment assembly order
- Q20: replaced `R2K_INCLUDE_MATCH_STATE` section with dynamic prompt
  injection reference; added content-hash skip section; updated staleness
  figure (~684ms, was ~800ms)
- Q24: fixed stale threshold note ("estimates" → "calibrated from v6.3
  27-run baseline, commit `532360b`")
- Q25 (NEW): Dynamic Prompt Injection — mechanism, fragment taxonomy,
  why it replaces R2K_INCLUDE_MATCH_STATE, 4 game-phase stubs
- Q26 (NEW): Content-Hash Skip — 64% fewer calls, ~684ms effective
  latency, why safe at temperature:0.0

**`META_KNOWLEDGE_ROUTER.md`** (v6.2 → v6.3):
- Front matter: v6.2 → v6.3, tags updated, duplicate version lines removed
- 6 new glossary entries: Dynamic Prompt Injection, Content-Hash Skip,
  Role Condensation, Replay System, Attack KPIs, R2K_EXPLAIN env var
- 2 new routing matrix rows (V6.3): dynamic injection/content-hash/replay/
  role-condensation, attack KPIs/R2K_EXPLAIN/R2K_RUN_LABEL

**`6_DATA_SCHEMAS_AND_LIFECYCLE.md`** (v6.3 addendum):
- New "V6.3 Addendum" section: 4 new attack KPIs table, dynamic prompt
  injection (fragment assembly order, caching, `sys_prompt_hash`),
  `R2K_EXPLAIN` env var, content-hash skip (mtime staleness note),
  v6.3 baseline table (9 scenarios × 3 runs, with B:R/comp/shots/
  passCmp/restartRecovery)
- Fixed stale threshold note: "estimates" → "calibrated from v6.3 baseline"

**`3_AI_LOGIC_AND_EDGE_CASES.md`** (v6.2 → v6.3):
- Front matter: v6.2 → v6.3, tags updated
- New "V6.3 Addendum" section: dynamic prompt injection (status update
  from "planned Phase 4a" to "implemented Phase 2.5b"), content-hash skip,
  role condensation, explain-mode fix (R2K_EXPLAIN), replay system

**`AGENTS.md`** (gotchas + file layout):
- Fragment list: added 4 game-phase fragment names, noted evaluator
  assembles at runtime (system_prompt.txt now only for dump_prompt.py)
- Gotcha: setup_r2k.py note updated for dynamic injection
- Gotcha: r2k_evaluator.py note updated for content-hash skip + R2K_EXPLAIN

**`workshop v6.2/cheatpage.md`** (v6.2 → v6.3):
- Title/header: v6.2 → v6.3
- Launch flags: added `--analyze` flag
- Testing: rewritten for two-tier system (fast/slow, 92 tests, 9 files,
  `--skip-slow` flag, `test_non_functional.py` 11 slow tests,
  `test_prompt_assembly.py` 1 test)
- KPIs: "14 metrics" → "18 metrics", added `goalie_tactical_pct`,
  `shots_on_goal`, `shots_on_target`, `pass_completion_pct`,
  `restart_recovery_time_s`; removed `role_diversity`, `avg_response_tokens`
- File locations: tools list updated (added `match_annotate`,
  `replay_trace`), test count 7→9 files / 91→92 tests, spec reference
  v6.2→v6.3, added replay entry

**Files touched:**
- `core/src/r2k_visualizer.py` (b-key fix, --nav deprecated, --live flag,
  arrow-key seek, log name display, window title)
- `core/docs/optimization_spec_v6.3.md` (Phase 2.5 status corrections,
  run budget update, 15→18 KPI typo fix)
- `core/src/ros2k_knowledge/ROS2K_GEM_FAQ.md` (v6.3, Q16/Q19/Q20/Q24
  updated, Q25/Q26 added)
- `core/src/ros2k_knowledge/META_KNOWLEDGE_ROUTER.md` (v6.3, 6 glossary
  entries, 2 routing rows)
- `core/src/ros2k_knowledge/6_DATA_SCHEMAS_AND_LIFECYCLE.md` (v6.3
  addendum, baseline table, threshold note fix)
- `core/src/ros2k_knowledge/3_AI_LOGIC_AND_EDGE_CASES.md` (v6.3 addendum)
- `core/AGENTS.md` (gotchas + file layout updates)
- `core/docs/workshop v6.2/cheatpage.md` (v6.3, testing + KPIs + tools)
- `core/docs/SESSION_CHANGELOG.md` (this entry)

**New files (untracked):**
- (none)

**Files deleted:**
- (none)

**Not yet done:**
- Stored v6.3 baseline KPI JSONs (`results/kpis_baseline_v63_*.json`) show
  0 for the 4 new attack KPIs (generated before t_wall bugfix). Code fix
  is committed; JSONs need a re-run to reflect correct values. The commit
  message table and spec contain the correct post-fix numbers.
- Lecturer guide (`workshop_lecturer_guide.md`) intentionally NOT updated
  per user instruction — left as-is.
- Nothing committed — all work uncommitted in working tree on
  `feature/ros2k_behavior_optimization` (or whatever branch is current).
- `libgazebo_ros_init.so` still not rebuilt into Docker container —
  sim-time (`/clock`) not flowing. Replay falls back to `t_wall`.
- Phase 3 `format: "json"` confound in `r2k_evaluator.py:303-304` not
  fixed — different models get different Ollama options. Must be
  unified before Phase 3.

**Next:**
- Commit the visualizer fixes + Phase 2.5f KB/docs update
- Phase 3: fix `format: "json"` confound, pull 2 new models, run 135 runs

**Blockers:**
- `batch_evaluator.py` KPI collection still broken (deprecated, carried
  from 2026-07-13)
- Phase 3 requires live Gazebo + Ollama + 2 new models pulled

## 2026-07-30 — C-Series experiments, literature survey, format:json confound discovery, architecture research

**Goal:** Validate project design decisions against scientific literature,
run pre-Phase-3 experimental probes (C1-C6), discover and fix a critical
methodological confound (format:json), and research architecture
alternatives (task decomposition, problem space transformation).

**Done:**

### Literature survey (breadth-first, arxiv)

Searched 6 arxiv clusters: "LLM robot control survey", "multi-robot
cooperative LLM", "world model robot learning", "chain of thought robot
control planning", "hierarchical LLM planning", "problem reformulation LLM".
Deep-read 2 papers:

- **ECoT (Zawalski et al. 2024, arxiv 2407.08693):** Embodied CoT for VLA.
  +28% success from training (not prompting) the model to reason step-by-step.
  Prompt-only CoT on a 7B model gave +4pp (noise). The gains came from
  fine-tuning on synthetic CoT data, not from prompt design. Embodied
  reasoning steps (visual grounding: bounding boxes, gripper positions) were
  essential; semantic-only CoT (sub-task plans) was insufficient.
- **"Two Calls Beat Five Agents" (Prajapati & Mohite 2026, arxiv 2607.26922):**
  5-agent pipeline on Qwen2.5-7B DROPPED accuracy 30pp (JSON communication
  fails 30-40% on 7B → error accumulation). Two-call self-refinement beat the
  5-agent pipeline (+4.2%) with 7.4× fewer tokens. But self-refinement
  actively HARMED tasks where the model was already good (>90% accuracy).
  Key finding: "If direct accuracy <85%, self-refinement helps. If >90%,
  it costs extra but yields nothing."

### Codebase audit (2 explore agents, parallel)

- **Prompt architecture audit:** Catalogued 20+ magic numbers, 6 known
  contradictions (prompt says goalie Y must match ball Y; bridge damps to
  30-50%. Prompt says goalie X=-4.0; bridge uses -4.32. Game-phase fragments
  have rules but no samples, contradicting B-study RQ1. Content-hash skip
  ignores status changes. LLM never sees score/status/velocity/orientation.
  format:json only for some models.)
- **KPI/calibration evidence audit:** B-study "1-sample is best" based on
  n=3 with 50pp OOB variance. Role condensation has NO A/B test. Goalie
  blending parameters never swept (D9 deferred). Composite score weights
  (0.4/0.3/0.2/0.1) never validated. kpi_targets.json for 4 new attack KPIs
  calibrated against invalid baseline data (all zeros, t_wall bug).
  experiment_matrix.md (179 lines) never filled in — only means exist.

### Phase 0: Re-baseline (27 runs, commit-ready)

- Re-ran `tools/run_baseline.sh baseline_v63_revalidate` (9 scenarios × 3 × 120s).
- Attack KPIs now non-zero (t_wall fix confirmed working): shots_on_goal
  4-22 per scenario, pass_completion 42-93%.
- Recalibrated 9 `kpi_targets.json` from valid baseline data.

### C6: 1-sample vs 3-sample (n=10 vs n=10) — NO SIGNIFICANT DIFFERENCE

All p > 0.05. The B-study "1-sample is best" finding does NOT replicate at
n=10. The 3-sample config shows slightly more goals (0.7 vs 0.2, p=0.20)
and less cluster (23.9% vs 40.5%, p=0.15) — directional but not significant.

### Critical discovery: format: "json" confound

Enabled `format: "json"` for all models (to fix Phase 3 confound). Measured
impact: latency jumped from 746ms to 2081ms (+180%). This suppressed
offensive behavior (shots dropped 3×) and distorted all C-series results.
Reverted to model-specific (nemotron/llama only). Re-ran clean baseline
(C6_clean, n=10) at 746ms.

### C-Series v1 (with format:json — INVALID, all confounded)

| Exp | v1 verdict | Why invalid |
|-----|-----------|-------------|
| C1 (enrichment) | No improvement | +1606ms latency masked the effect |
| C5 (no-blending) | Goalie -22pp | Latency, not blending removal, caused most of the drop |
| C2 (schema) | OOB increased | Latency-driven OOB, not schema-driven |
| C4 (temporal) | Shots killed + goals_red up + goalie down | Shots finding holds; others were latency artifacts |

### C-Series v2 (clean, no format:json — VALID)

| Exp | v2 verdict | Key finding |
|-----|-----------|-------------|
| **C1** | **Goals improved significantly** | 0.4→1.2 goals/match (p=0.037*). +40ms latency. The 3B model CAN use velocity/yaw/score. |
| C5 | Goalie borderline regression | -7.8pp tactical (p=0.058, borderline). OOB improved (17%→4.2%, p=0.086). Blending still helps but side effects are interesting. |
| C2 | No significant change | Schema-only works as well as 1-sample at clean latency. +21ms latency. |
| C4 | Shots still killed | 0 vs 18 shots (p=0.014*). But only +70ms latency (was +1606ms). Temporal context confirmed harmful for 3B regardless of latency. |

### Baseline reliability analysis (C6_clean, n=10)

| KPI | CV | Reliability |
|-----|----|-------------|
| latency_p50 | 0.7% | Rock-solid (infrastructure deterministic) |
| llm_calls | 0.8% | Rock-solid |
| goalie_tactical_pct | 12.1% | Moderate |
| possession | 27.1% | Moderate |
| pass_completion_pct | 67.6% | Poor |
| cluster_pct | 91.2% | Terrible (1.7% to 73.2%) |
| oob_pct | 90.1% | Terrible (0% to 44.6%) |
| shots_on_goal | 83.9% | Terrible (0 to 47) |
| goals_blue | 129.1% | Terrible (0 or 1, basically random) |

Infrastructure is perfectly reliable (latency CV=0.7%). Variance comes
entirely from Gazebo physics (ball restitution=1.0, friction=0.01 → chaotic).
At n=10: latency/goalie/possession are interpretable. Goals/shots/OOB need
large effects (3× on goals) for significance.

### Code changes (uncommitted)

- `r2k_evaluator.py`: content-hash skip bug fix (include status in hash,
  prevents missed status transitions). C1 state enrichment (velocity/yaw/score,
  env: `R2K_ENRICH_STATE=1`). C4 temporal context (3-snapshot history,
  env: `R2K_HISTORY_DEPTH=3`). format:json reverted to model-specific.
- `ollama_sandbox_bridge.py`: goalie weights env-var controlled
  (env: `R2K_GOALIE_TACTICAL_WEIGHT`, `R2K_GOALIE_LLM_WEIGHT`).
- `tracker_node.py`: yaw extraction from quaternion (for C1, needs colcon
  rebuild — done).
- `launch_r2k.sh`: env var passthrough for `R2K_ENRICH_STATE`,
  `R2K_HISTORY_DEPTH`, `R2K_GOALIE_TACTICAL_WEIGHT`, `R2K_GOALIE_LLM_WEIGHT`.
- `tools/analyze_trace.py`: `--stats` flag for statistical comparison
  (mean ± std, 95% CI, Mann-Whitney U, significance markers).
- `tools/run_c_series.sh`: C-series experiment runner (N repeats, single
  scenario, optional fragment swap, env var passthrough).
- `optimization_spec_v6.3.md`: 3 KPI threshold corrections (cluster 1.5m→0.5m,
  OOB 0.5m→0.1m, goalie_idle 0.1m→0.05m). Phase 2.5 marked DONE. Run budget
  updated. 15→18 KPI typo fixed.
- 9 `kpi_targets.json` recalibrated from v6.3 re-baseline.

### Experiment infrastructure

- `experiments/C6_3sample/fragments/samples_3vs3.txt`: 3-sample variant (3
  examples with current 3-role taxonomy).
- `experiments/C2/fragments/`: schema-first fragments (rules_core.txt with
  JSON schema, empty samples_3vs3.txt).

**Files touched:**
- `core/src/ai_tactics/r2k_evaluator.py` (content-hash fix, C1 enrichment,
  C4 history, format:json revert)
- `core/src/ai_tactics/ollama_sandbox_bridge.py` (env-var goalie weights)
- `core/src/ros2_ws/src/r2k_world_model/r2k_world_model/tracker_node.py`
  (yaw extraction)
- `core/launch_r2k.sh` (env var passthrough)
- `core/src/tools/analyze_trace.py` (--stats flag)
- `core/src/tools/run_c_series.sh` (NEW — C-series runner)
- `core/docs/optimization_spec_v6.3.md` (KPI threshold corrections, Phase 2.5
  status, run budget)
- `core/src/scenario/*/kpi_targets.json` (9 files recalibrated)
- `core/docs/SESSION_CHANGELOG.md` (this entry)

**New files (untracked):**
- `core/src/tools/run_c_series.sh`
- `core/src/experiments/C6_3sample/fragments/samples_3vs3.txt`
- `core/src/experiments/C2/fragments/` (rules_core.txt, samples_3vs3.txt,
  + copies of header/rules_3vs3/game-phase fragments)

**Not yet done:**
- C1/C5/C2/C4 v1 results still in `results/` (invalid, confounded by
  format:json). v2 results are valid. Should delete or clearly label v1
  files to avoid confusion.
- Sample-design experiment (analysis→strategy→waypoints chain embedded in
  a single few-shot sample, 1 call) — designed but not yet run. Next step.
- 3C architecture (LLM for intent + rule-based mapper for waypoints) —
  deferred per user decision ("we go for full 3c later").
- C6 1-vs-3-sample re-run at clean latency — lower priority (n=10 already
  showed no significant difference, 3-sample has inherent latency confound
  from larger prompt).
- Nothing committed — all work uncommitted in working tree.

**Next:**
1. Run the sample-design experiment (n=10, ~20min) against C6_clean baseline.
2. If sample-design shows directional improvement → invest in n=30 for
   significance on goals/shots/OOB.
3. Design the 3C architecture (LLM intent + code mapper) for later
   implementation.
4. Investigate Gazebo deterministic seeding to eliminate simulator variance.

**Blockers:**
- Gazebo physics variance (CV=90-129% on goals/shots/OOB) limits
  statistical power. n=10 can only detect large effects on these KPIs.
  Gazebo seeding investigation needed.
- Visualizer blitting + replay TkAgg untested with live ROS 2 + Gazebo
  (carried from 2026-07-14)
- `batch_evaluator.py` KPI collection still broken (deprecated, carried
  from 2026-07-13)

## 2026-07-30 (continued) — C9: Future World Model, predicted positions

**Goal:** Test whether feeding the LLM predicted positions at t+746ms
(where things will be when the command takes effect) improves decision
quality. Ball uses exponential velocity decay (k=1.26, empirically
measured). Bots use linear motion capped at max speed (0.8 m/s). Blue
bot prediction is valid — at t+746ms they're still executing the
previous command, not the one being generated now.

**Done:**

### C9 experiment (n=10, `3vs3_attack_center`, horizon=746ms)

| KPI | C6_clean (n=10) | C9 (n=10) | Δ | p |
|---|---|---|---|---|
| goals_blue | 0.40 | 0.30 | -0.10 | 0.55 (n.s.) |
| goals_red | 0.60 | 0.90 | +0.30 | 0.38 (n.s.) |
| shots_on_goal | 18.0 | 14.4 | -3.6 | 0.55 (n.s.) |
| cluster_pct | 23.0% | 13.8% | -9.2 | 0.29 (n.s.) |
| pass_completion | 45.8% | 63.4% | +17.5 | 0.21 (n.s.) |
| goalie_tactical | 89.7% | 94.0% | +4.3 | 0.24 (n.s.) |
| latency_p50 | 746ms | 749ms | +3ms | 0.26 (n.s.) |

**Result: no significant improvement on any KPI.** Goals slightly worse
(0.40→0.30, n.s.). Secondary KPIs directionally improved (cluster -9.2pp,
pass_completion +17.5pp, goalie_tactical +4.3pp) but none significant
at n=10.

**Why goals didn't improve:** C1 (enrichment) gave the LLM *new
information* (velocity direction, score awareness) → 3× goal
improvement. C9 (prediction) gives the LLM *better positions* of the
same information type. The LLM was already implicitly compensating for
staleness by aiming at the ball's current position. Prediction shifts
the reference frame but doesn't add capability. Shot conversion remains
~2% (14.4 shots → 0.3 goals) — the LLM can't kick accurately regardless
of position information quality.

**C1 vs C9 comparison:**
- C1 (enriched): goals 1.2 (p=0.037*), shots 20.2, cluster 29.5%
- C9 (predicted): goals 0.30 (n.s.), shots 14.4, cluster 13.8%
- C1 helps goals (velocity/score awareness). C9 helps positioning (less
  stale world). Complementary — C1+C9 combined is the natural follow-up.

**Code changes:**
- `r2k_evaluator.py`: `import math` added; C9 prediction block (~25
  lines) after content-hash check, before `min_ents` construction. C1/C9
  isolation guard (C1 velocity computation disabled when C9 is active
  to avoid predicted-vs-actual velocity confusion). `prev_ents` saved
  before prediction so next cycle's velocity is computed from actual
  positions.
- `launch_r2k.sh`: `R2K_PREDICT_HORIZON_MS` env var passthrough added.

**Files touched:**
- `core/src/ai_tactics/r2k_evaluator.py` (C9 prediction, import math)
- `core/launch_r2k.sh` (env var passthrough)

**Not yet done:**
- C1+C9 combined experiment (enrichment + prediction, n=10)
- Sample-design experiment (analysis→strategy→waypoints chain in sample)
- 3C architecture design (LLM for intent + rule-based mapper)
- Gazebo deterministic seeding investigation

**Blockers:**
- Gazebo physics variance (CV=90-129% on goals/shots/OOB) — n=10 only
  detects large effects. Seeding investigation needed.
- Visualizer blitting + replay TkAgg untested with live ROS 2 + Gazebo
  (carried from 2026-07-14)
- `batch_evaluator.py` KPI collection still broken (deprecated, carried
  from 2026-07-13)

## 2026-07-30 (final session) — C1/C9 baselines launched for C3 evaluation

**Goal:** Establish solid statistical baselines (n=17) for C1 (enrichment) and
C1+C9 (enrichment + prediction) across all 9 scenarios, to evaluate the
upcoming C3 architecture (LLM for intent + rule-based mapper for waypoints).

**Context from earlier today:**
- C1 enrichment (velocity/yaw/score): goals improved 3× (p=0.037*), 40% win
  rate, 0 losses at n=5
- C9 prediction (future world model): no goal improvement, but OOB -10pp,
  pass completion +25pp. Future referee rules may penalize OOB with
  time-outs, making OOB reduction a direct win-rate contributor
- C1+C9 combined: 50% win rate (best), only 0.2 goals conceded (best
  defense), but interference with C1's goal-scoring benefit
- format: "json" confound discovered and reverted (+1336ms latency)

**Fix applied:**
- C1/C9 isolation guard removed. When both are active, C1 now uses the
  `velocities` dict from C9 (computed from actual positions) instead of
  recomputing from `prev_ents` (which would use predicted positions and
  give wrong velocities). ~10 lines changed in `r2k_evaluator.py`.

**Baselines launched:**
- Config C1 (enrichment only, `R2K_ENRICH_STATE=1`): n=17 per scenario
- Config C1+C9 (enrichment + prediction, `R2K_ENRICH_STATE=1` +
  `R2K_PREDICT_HORIZON_MS=746`): n=17 per scenario
- All 9 scenarios × 2 configs × 17 runs = 306 runs total (~12h)
- Script: `tools/run_baselines.sh` (launched detached via `setsid`)
- Output: `results/kpis_C1_<scenario>_r*.json` and
  `results/kpis_C1C9_<scenario>_r*.json`

**Status at session end:**
- Running: C1 on `3vs3_attack_center` run 3/17, C1C9 on
  `3vs3_attack_center` complete (10/10)
- ~12h total compute expected, runs overnight

**To check progress:**
```bash
# Count completed runs
ls ~/R2K-HSL/core/src/results/kpis_C1_*.json | wc -l
ls ~/R2K-HSL/core/src/results/kpis_C1C9_*.json | wc -l

# Check log
tail -20 ~/R2K-HSL/core/src/results/baselines.log
```

**To analyze results (after completion):**
```bash
cd ~/R2K-HSL/core/src
# Per-scenario comparison
python3 tools/analyze_trace.py \
  --stats-a "results/kpis_C1_3vs3_attack_center_r*.json" \
  --stats-b "results/kpis_C1C9_3vs3_attack_center_r*.json"

# Win rate analysis (per scenario)
python3 -c "
import json, glob
for scen in ['attack_center','attack_wing','contain_delay','def_transition','defensive_crisis','fast_counter','high_line','long_shot','pressing_trap']:
    c1 = [json.load(open(f)) for f in sorted(glob.glob(f'results/kpis_C1_3vs3_{scen}_r*.json'))]
    c1c9 = [json.load(open(f)) for f in sorted(glob.glob(f'results/kpis_C1C9_3vs3_{scen}_r*.json'))]
    c1_wins = sum(1 for d in c1 if d['world_kpis']['goals_for_blue'] > d['world_kpis']['goals_for_red'])
    c1c9_wins = sum(1 for d in c1c9 if d['world_kpis']['goals_for_blue'] > d['world_kpis']['goals_for_red'])
    c1_draws = sum(1 for d in c1 if d['world_kpis']['goals_for_blue'] == d['world_kpis']['goals_for_red'])
    c1c9_draws = sum(1 for d in c1c9 if d['world_kpis']['goals_for_blue'] == d['world_kpis']['goals_for_red'])
    print(f'{scen:25s} C1: {c1_wins}W/{c1_draws}D/{len(c1)-c1_wins-c1_draws}L  C1+C9: {c1c9_wins}W/{c1c9_draws}D/{len(c1c9)-c1c9_wins-c1c9_draws}L')
"
```

**Next session:**
1. Check if baselines completed (~12h from launch)
2. Analyze C1 vs C1+C9 win rates per scenario
3. Design C3 architecture (LLM for intent + rule-based mapper)
4. Run C3 experiments against baselines
5. Gazebo deterministic seeding investigation (if time)

**Blockers:**
- Gazebo physics variance (CV=90-129% on goals/shots/OOB) — n=17 only
  detects large effects. Seeding investigation needed.
- `batch_evaluator.py` KPI collection still broken (deprecated, carried
  from 2026-07-13)

## 2026-07-31 — Infrastructure cleanup, single commit, baseline results

**Goal:** Reduce infrastructure complexity, commit clean state, summarize
baseline results for C3 evaluation.

### Cleanup performed

**Evaluator (`r2k_evaluator.py`):**
- Removed C1 state enrichment (velocity/yaw/score injection, ~20 lines)
- Removed C4 temporal context (3-snapshot history, ~8 lines)
- Removed C1/C9 isolation guard (~5 lines)
- Removed `format: "json"` Ollama grammar constraint entirely (~4 lines)
- Hardwired future world model prediction: `PREDICT_HORIZON_S = 0.746`
  (always on, no env var, no Docker passthrough needed)
- Kept: content-hash fix (status in hash), `import math`, prediction block
- Net: ~35 lines removed, 3 `os.getenv` calls removed

**Bridge (`ollama_sandbox_bridge.py`):**
- Reverted goalie weights to hardcoded 0.7/0.3 (removed 2 `os.getenv` calls)

**Tracker (`tracker_node.py`):**
- Removed yaw extraction (reverted to position-only x, y)
- Colcon rebuilt in Docker container (clean build, 5 packages, 2.35s)

**Visualizer (`r2k_visualizer.py`):**
- Removed predicted-position overlay (dotted circles, ~40 lines)
- Kept: b-key fix, --nav deprecation, --live flag, arrow seek, log name

**Launch script (`launch_r2k.sh`):**
- Removed 5 C-series env var `-e` passthroughs (ENRICH, HISTORY, PREDICT ×2, GOALIE ×2)
- U22 and U24 are now identical: no Docker-specific env vars for C-series

**Total:** 11 env vars removed, ~90 lines of code removed

### Commit

Single commit: `e3d01b0` on `feature/v6.3-replay-and-optimization`
- 21 files changed, 1441 insertions, 632 deletions
- Includes: evaluator, bridge, tracker, visualizer, launch script, 9 kpi_targets.json, 4 KB power files, spec, AGENTS.md, cheatpage, session changelog

### Baseline results (n=17, 306 runs, 9 scenarios)

**C1 (enrichment only):**
- Win rate: 17/153 = 11.1% (W/D/L: 17/67/69)
- Goals: 57:158 (0.37/match scored, 1.03 conceded)
- OOB avg: 9.4%
- Best scenario: attack_center (3W/7D/7L = 17.6%), high_line (3W/8D/6L = 17.6%)

**C1+C9 (enrichment + prediction):**
- Win rate: 18/153 = 11.8% (W/D/L: 18/64/71)
- Goals: 55:142 (0.36/match scored, 0.93 conceded)
- OOB avg: 11.2%
- Best scenario: attack_center (6W/6D/5L = 35.3%)

**Key finding:** C9 prediction does NOT improve win rate at n=17
(11.1% vs 11.8%, Δ=+0.7pp, n.s.). C9 helps on attack_center (+17.6pp)
but hurts on high_line (-17.6pp) and pressing_trap (-17.6pp). Effects
cancel in aggregate.

**C1's earlier 40% win rate (n=5) was small-sample noise.** At n=17,
C1's true win rate is 11.1% — close to the raw baseline. The 3B model
with any combination of enrichment/prediction wins ~11% of matches.

### What C3 needs to beat

- **Win rate: >11.8%** (C1+C9 baseline)
- **Goals conceded: <0.93/match** (C1+C9 baseline)
- **OOB: <9.4%** (C1 baseline; C3's deterministic mapper should eliminate OOB)
- **Win rate on attack_center: >35.3%** (C1+C9 best scenario)

### Next session

1. Design C3 architecture (LLM for intent + rule-based mapper for waypoints)
2. Implement C3 mapper (~50 lines Python)
3. Run C3 experiments against baselines (n=17, 9 scenarios, ~12h)
4. Gazebo deterministic seeding investigation

### Blockers

- Gazebo physics variance (CV=90-129% on goals/shots/OOB) — n=17 only
  detects large effects. Seeding investigation needed.
- `batch_evaluator.py` KPI collection still broken (deprecated, carried
  from 2026-07-13)

## 2026-07-31 (continued) — C3 Phase 0: Literature research, phase plan rework (Phases F + W, text-only)

**Goal:** Conduct Phase 0 literature research for the C3 inter-lingua
approach. Correct the initial analysis based on user feedback (no
rule-based mapper, controlled vocabulary not JSON API, composite score
as diagnostic, world models long-term). Re-plan with two new phases
(Phase F: few-shot paradigm rework, Phase W: watchdog & closed-loop
feedback) — both text-only (no Gazebo, synthetic world data, LLM output
analysis). Write the plan document.

**Done:**

### Literature surveyed (Phase 0)

- **LLCoach** (Brienza 2024, arxiv 2406.18285): RoboCup SPL + multi-role
  LLM generating soccer plans. Closest domain analog. Validates LLM-coach
  architecture for RoboCup. Key difference: they use large LLM at
  play-level granularity; we use 3B at tick-level (~750ms).
- **SayCan** (Ahn 2022, arxiv 2204.01691): NL action labels + affordance
  function. Validates controlled-vocabulary-in-NL form. The "affordance"
  = feasibility check is separate from the LLM.
- **RoboMatrix** (Mao 2024, arxiv 2412.00171): Skill-centric 3-layer
  hierarchy. +50% over monolithic. Validates decomposition > monolithic
  for small models.
- **BTGenBot-2** (Izzo 2026, arxiv 2602.01870): 1B model generates BTs
  from NL + action primitive list. 90% zero-shot, beats GPT-5. **Most
  actionable:** small models work when (a) vocab is small and
  pre-specified, (b) primitive list given as input.
- **EmboTeam** (Zeng 2026, arxiv 2601.11063): LLM→PDDL→planner→BT.
  12%→55%. The classical planner is a *verifier* — catches LLM errors.
  We don't have one (no rule-based mapper) → watchdog (Phase W) addresses
  this.
- **SCOPE** (Hindsbo 2026, arxiv 2606.02951): Qwen3 SLMs for NL tool
  routing. "Once SLM is capable enough, perception becomes the
  bottleneck" → connects to "world models not overkill long-term."
- **HALO** (Hou 2025, arxiv 2505.13516): Hierarchical multi-agent prompt
  design. Adaptive Prompt Refinement = our dynamic prompt injection.
  Role separation can be within one prompt, not multiple models.
- **Correlation matrix rank self-verifier** (Liu 2025, arxiv 2510.24299):
  LLM checks own output via internal activations. 75% accuracy. Relevant
  to watchdog Option A (but needs direct transformers access, not Ollama
  REST).
- **LLMs gaming verifiers** (Helff 2026, arxiv 2604.15149): Imperfect
  verifiers admit false positives. Warning for watchdog Option B
  (mitigated: monitor checks world consistency, not output quality).
- **Orchestration gap** (Galanti 2026, arxiv 2607.21725): Separating
  reasoning from execution = 4× improvement. The watchdog IS the
  orchestrator — outcome tracking + failure recovery.
- From handover: ECoT, Two-Calls-Beat-Five-Agents, C9 (all re-read with
  corrected framing).

### GitHub search

- 0 results for "robot instruction + controlled vocabulary + intermediate
  representation" and "LLM robot soccer instruction natural language."
  This intersection is too niche for public repos. Our work fills the gap.

### Corrected framing (from user feedback)

| Initial assumption | Corrected |
|---|---|
| Rule-based mapper in bridge | No new mapper. LLM outputs instruction sentences directly. |
| JSON skill API | Controlled vocabulary: verb+noun+adjective NL sequences |
| Composite = wrong metric | Composite = diagnostic (what to improve, not whether won) |
| World models = overkill | Not overkill long-term. Phase 5.1 stays on roadmap. |
| Gazebo runs for F/W | No Gazebo. Text-only LLM analysis with synthetic world data. |

### Two new phases designed

**Phase F: Few-shot paradigm rework** (text-only, after Phase 1)
- F1: Build `tools/llm_probe.py` + ~100 synthetic world-states (from
  existing trace data + hand-crafted edge cases)
- F2: Define 9 text-analysis metrics (parse_success, vocab_compliance,
  rule_following, analysis_quality, oracle_quality, contradiction_score,
  role_coverage, continue_accuracy, latency)
- F3: Structure sweep (F0=baseline separate, F1=rules-inline, F2=no-
  global-text extreme, F3=axioms-only-global) — ~1200 probes, ~21.5 min
- F4: Content sweep (sample count 1/3/6, roles 0/3/5, rule density,
  analysis/oracle presence) — ~1500 probes, ~20 min
- F5: Qualitative deep-dive on top 2–3 configs
- **No Gazebo.** LLM text output analyzed directly. ~80× faster iteration.

**Phase W: Watchdog & closed-loop feedback** (text-only, parallel to
Phase 2–3)
- W1: Synthetic divergence scenarios (no-div, ball-div, bot-div, score-
  div, status-div, noise)
- W2: Test Option A — re-prompt 3B on divergence (~1190ms per re-prompt,
  ~2 min for 50 scenarios)
- W3: Test Option B — second model (1.5B) as monitor (~400ms per check,
  ~40 sec for 50 scenarios × 2 models)
- W4: Compare and decide (accuracy, latency, simplicity, GPU contention)
- **No Gazebo.** Synthetic world data + LLM output analysis.

### Model switch: qwen2.5-coder:3b → qwen2.5:3b

Investigated Qwen2.5-Coder training data via technical report (arxiv
2409.12186). The training corpus is 70% source code, 20% text-code
grounding, 10% math. Soccer vocabulary is not in-distribution for a
code-specific model. Switched to Qwen2.5-3B-Instruct (general-purpose)
which has broader web/book/multilingual text exposure.

Consequences:
- C-series Gazebo baselines (11.8% WR) invalidated — new baseline
  with qwen2.5:3b runs parallel to Phase 1
- Architecture continuity preserved (same Qwen2.5 arch, evaluator/
  bridge/trace/logging all work identically)
- Llama-3.2-3B added as regression test (Phase 4b) to test inter-lingua
  generalizability across model families. Also candidate for Phase 5
  edge deployment (Jetson AGX/Orin for K1 onboard).

### Latency budget (corrected for qwen2.5:3b)

| Mode | num_predict | Est. p50 | Impact on F/W |
|---|---|---|---|
| `--no-explain` | 150 | ~700ms | F0 baseline, no-analysis configs |
| `--explain` | 600 | ~1100ms | F1–F3 interwoven, watchdog re-prompt |

Estimates from Coder model (same architecture). Verify on first probe.

Total text-only phases (1 + F + W + 4b): ~3100 probes, ~76 min. Compare:
one 27-run Gazebo baseline = ~45 min + container restart overhead.

### Phase plan written

`core/docs/c3_phase0_literature_and_plan.md` (~530 lines):
- §0: Corrected framing (incl. model switch)
- §1: Literature table (11 papers + handover papers)
- §1.1: Model switch analysis (Qwen2.5-Coder training data → qwen2.5:3b)
- §2: 9 key takeaways (incl. model choice + Llama 3.2 regression)
- §3: Latency budget (corrected for qwen2.5:3b)
- §4: Text-only iteration loop
- §5: Phase plan (Phases 0–5 + F + W + 4b, all text-only except Phase 4–5)
- §6: Phase dependency graph (with parallel baseline + Llama regression)
- §7: Time budget summary
- §8: Baselines to beat (old invalidated + new TBD)
- §9: Gaps our work fills (novelty, incl. cross-model validation)
- §10: Files to read (with arxiv references)

**Files touched:**
- `core/docs/c3_phase0_literature_and_plan.md` (NEW — ~530 lines, updated with model switch)
- `core/docs/SESSION_CHANGELOG.md` (this entry + model switch update)

**New files (untracked):**
- `core/docs/c3_phase0_literature_and_plan.md`

**Files deleted:**
- (none)

**Not yet done:**
- Phase 1 (vocabulary probing) — interactive, next session
- `tools/llm_probe.py` — to be built in Phase F1
- `tests/synthetic_worldstates/` — to be built in Phase F1
- `tests/synthetic_divergence/` — to be built in Phase W1
- Interwoven sample fragments (`samples_interwoven_3vs3.txt` etc.) — to
  be authored in Phase F3
- User must `ollama pull qwen2.5:3b` before Phase 1
- New Gazebo baseline (27 runs, qwen2.5:3b) must run parallel to Phase 1
- Nothing committed

**Next:**
- User: `ollama pull qwen2.5:3b`
- User: launch `bash tools/run_baseline.sh baseline_qwen25_3b` in
  background (27 runs, ~45min)
- Phase 1: Interactive vocabulary probing with qwen2.5:3b via Ollama API.
  Discover soccer verb+noun+adjective sequences the model already knows.
  Output: controlled vocabulary + few-shot template sketches.
- Then Phase F1: build `llm_probe.py` + synthetic world-state dataset.
- Then Phase F3: structure sweep (~20 min, no Gazebo).

**Blockers:**
- Ollama must be reachable on GPU. User must `ollama pull qwen2.5:3b`
  and verify GPU load before Phase 1.
- `batch_evaluator.py` KPI collection still broken (deprecated, carried
  from 2026-07-13 — orthogonal to C3 text-only phases)

## 2026-07-31 (final) — Model switch, baseline run, Phase 0 plan updates

**Goal:** Switch from qwen2.5-coder:3b to qwen2.5:3b (general-purpose),
run a new 27-run Gazebo baseline, and update the Phase 0 plan with real
measured data.

**Done:**

### Model switch: qwen2.5-coder:3b → qwen2.5:3b

Investigated Qwen2.5-Coder training data via technical report (arxiv
2409.12186). The corpus is 70% source code, 20% text-code grounding,
10% math. Soccer vocabulary is not in-distribution for a code-specific
model. Switched to Qwen2.5-3B-Instruct (general-purpose) which has
broader web/book/multilingual text exposure.

- `launch_r2k.sh:12`: default model changed from `qwen2.5-coder:3b`
  to `qwen2.5:3b`. Help text at line 40 updated.
- `tools/run_baseline.sh`: added `MODEL` variable (2nd CLI arg, default
  `qwen2.5:3b`). `launch_r2k.sh` call now passes `--model "$MODEL"`.
  Usage comment updated.
- `bash -n` syntax check passes on both files.

### Ollama bind-address fix (recurring)

- Ollama was started manually (not via systemd), bound to `127.0.0.1`
  instead of `0.0.0.0`. Container-reachability guard in `launch_r2k.sh`
  caught it: "Ollama ist vom Docker-Container aus nicht erreichbar!"
- Fix: killed all ollama processes, restarted with
  `OLLAMA_HOST=0.0.0.0:11434 OLLAMA_ORIGINS=* OLLAMA_FLASH_ATTENTION=1
  OLLAMA_KV_CACHE_TYPE=q8_0 OLLAMA_MODELS=/home/r-zwei-kickers/.ollama/models
  OLLAMA_KEEP_ALIVE=-1 nohup ollama serve`
- Verified: `ss -tlnp` shows `*:11434` (all interfaces). Container
  can reach `172.17.0.1:11434/api/tags`.
- This is the 4th time this bug recurred (2026-07-20, 07-23, 07-27,
  07-31). The systemd override exists but only works if ollama is
  started via systemd. Manual starts need the env var.

### New baseline: 27 runs with qwen2.5:3b (COMPLETE)

`bash tools/run_baseline.sh baseline_qwen25_3b qwen2.5:3b`

All 27/27 runs produced KPIs (4279s = 71min). Summary saved to
`results/baseline_qwen25_3b_summary.md`.

| Scenario | Goals B:R | Composite | OOB% | Cluster% | Goalie Idle% | Possession% | Latency p50 |
|---|---|---|---|---|---|---|---|
| attack_center | 2:1 | 0.34 | 7.7% | 7.4% | 78.1% | 49.3% | 751ms |
| attack_wing | 3:1 | 0.39 | 10.6% | 30.1% | 73.9% | 53.4% | 743ms |
| contain_delay | 2:3 | 0.32 | 16.7% | 20.3% | 77.4% | 32.9% | 742ms |
| def_transition | 2:5 | 0.34 | 13.7% | 13.2% | 77.3% | 53.0% | 745ms |
| defensive_crisis | 0:3 | 0.25 | 4.5% | 12.2% | 93.9% | 26.3% | 740ms |
| fast_counter | 0:1 | 0.33 | 13.2% | 43.7% | 91.6% | 63.8% | 741ms |
| high_line | 2:4 | 0.27 | 26.2% | 22.1% | 89.8% | 36.2% | 744ms |
| long_shot | 0:1 | 0.31 | 23.4% | 49.6% | 83.5% | 49.1% | 743ms |
| pressing_trap | 0:2 | 0.33 | 2.9% | 37.5% | 89.7% | 55.5% | 744ms |

**Aggregate:** 11 goals scored, 21 conceded. Avg composite 0.32.
Avg latency p50: 744ms.

**vs old C-series baseline (qwen2.5-coder:3b):**
- Old C1+C9: 55 goals scored, 142 conceded across 153 runs (0.36/match
  scored, 0.93 conceded). Win rate 11.8%.
- New qwen2.5:3b: 11 goals scored, 21 conceded across 27 runs (0.41/match
  scored, 0.78 conceded).
- Goal-scoring rate slightly improved (0.41 vs 0.36/match). Concession
  rate improved (0.78 vs 0.93/match). The general model is marginally
  better at soccer than the coder model — confirms the training-data
  hypothesis.
- Latency: 744ms (new) vs 746ms (old C1) — essentially identical.

### Phase 0 plan updated with real data

`core/docs/c3_phase0_literature_and_plan.md` (~590 lines):
- §3: Latency budget updated — p50=761ms (measured, was estimate)
- §8: Baselines to beat — replaced TBD with measured 27-run table.
  New C3 targets: goals conceded <0.78/match, OOB <7.7%, best scenario
  composite >0.39, latency ≤761ms.

**Files touched:**
- `core/launch_r2k.sh` (default model: qwen2.5-coder:3b → qwen2.5:3b)
- `core/src/tools/run_baseline.sh` (added MODEL variable + --model arg)
- `core/docs/c3_phase0_literature_and_plan.md` (§3 latency, §8 baselines)
- `core/docs/SESSION_CHANGELOG.md` (this entry)

**New files (untracked):**
- `core/src/results/kpis_baseline_qwen25_3b_*.json` (27 KPI files)
- `core/src/results/baseline_qwen25_3b_*.log` (27 run logs)
- `core/src/results/baseline_qwen25_3b_summary.md`
- `core/src/results/baselines_qwen25_3b.log` (runner log)

**Files deleted:**
- (none)

**Not yet done:**
- Phase 1 (vocabulary probing) — interactive, next session
- `tools/llm_probe.py` — to be built in Phase F1
- Interwoven sample fragments — to be authored in Phase F3
- Nothing committed

**Next:**
- Phase 1: Interactive vocabulary probing with qwen2.5:3b via Ollama API.
  Discover soccer verb+noun+adjective sequences. Output: controlled
  vocabulary + few-shot template sketches.
- Then Phase F1: build `llm_probe.py` + synthetic world-state dataset.
- Then Phase F3: structure sweep (~20 min, no Gazebo).

**Blockers:**
- None — Ollama on GPU (3128MiB VRAM), qwen2.5:3b warm, baseline complete.
- `batch_evaluator.py` KPI collection still broken (deprecated, carried
  from 2026-07-13 — orthogonal to C3 text-only phases)

## 2026-08-01 — C3 Phase 1: vocabulary probing (44 probes), test case review, dictionary

**Goal:** Execute Phase 1 (vocabulary probing with qwen2.5:3b), produce the
controlled-vocabulary dictionary, and deliver the auxiliary test-case review
(TC-01..09 + 2vs2) with recommended adjustments.

**Done:**

### Phase 1 probing tool (`tools/vocab_probe.py`, NEW — 117 lines)
- Thin Ollama wrapper: `--prompt`, `--series`, `--system`, `--batch <jsonl>`.
  temperature 0.0, num_predict 600, keep_alive 1h, stream false.
- Appends every probe (series, prompt, latency, full response) to
  `results/vocab_probe_log.md` — evidence-based, no memory dependence.
- Batch files in `experiments/phase1_probes/`: `a_series.jsonl` (14 probes),
  `b_series.jsonl` (18), `c_series.jsonl` (12). Total 44 probes.

### Probe battery (all 44 run, logged)
- **A-series (free elicitation):** A1 word-list categorization; A2 tactical
  terms (formation, wing play, zone defense, marking, press, high line,
  counter-attack, defensive shadowing, passing lane, clearing); A3 roles
  (8 roles, striker task, goalie task).
- **B-series (instruction formation):** 6 real `world_trace` frames
  extracted from the qwen2.5:3b baseline runs (7-31) → single-bot
  instructions; 3 frames with all-3-bot coverage; 10 template-verb probes
  (move/receive/support/clear/mark/hold/press/cover/chase).
- **C-series (comprehension):** contradiction test (ball at center),
  6 acceptance-criteria phrases from `c3_revisited.txt`, 5 referee-situation
  probes (ball-out, goal-kick, corner, kickoff, foul).
- Latency: conversational probes mean ≈550ms (range 196–1009ms); warm
  trivial prompt ~110–140ms. Spec §3's 761ms is the full-pipeline figure —
  unchanged.

### Dictionary (`core/docs/c3_vocabulary_dictionary.md`, NEW)
- Verbs: **usable** — move to X,Y, receive pass, support run, hold
  position, mark X, clear the ball, cover the goal line, pass/shoot/cross.
  Borderline — press the ball (human "use your hands" twist), chase the
  ball (lacks speed/angle detail).
- Nouns/zones: formation, goal/goal line, center, wing/flank/sideline,
  passing lane all usable. "penalty area" borderline (our field has a goal
  area, not a box).
- Roles: goalie/attacker/defender usable (goalie two-mode description
  matches our blending: far → positioning, close → intercept).
- **CRITICAL FINDING (C2_striker_rule):** the dynamic-role definition
  "the striker is the bot closest to the ball" is **rejected** by
  qwen2.5:3b — it hedges ("could be considered... but not necessarily")
  and falls back to static human-soccer semantics. This is the exact
  "contradictive argumentation" pattern the inter-lingua must remove,
  and it originates in the role concept itself. **Phase 2 must prefer
  situation-triggered position verbs over derived role labels.**
- Acceptance phrases: 5 of 6 usable as-is (center-control, wing play,
  cross timing, zone-defend, shadowing). Only the dynamic-striker phrase
  fails.
- Referee/set-piece concepts: **weak** — ball-out partial (direction right,
  mechanics wrong), attacker-over-goal-line interpreted as a goal, kickoff
  wrong, corner placement wrong, foul partial. Decision: all restart/foul
  mechanics stay referee-owned (via `match_state`); LLM only needs passive
  restart-awareness.
- Contradiction baseline: direct unambiguous question → contradiction-free
  answer. The 73% contradiction failure is prompt-context, not model
  incapability.

### Test case review (`core/docs/c3_testcase_review.md`, NEW — aux deliverable)
Reviewed all 10 `analysis.md` files + `scenario.json` positions against the
current architecture:

**P0 (fix now, architecture facts):**
- **TC-05 pressing_trap:** no blue bot near own goal in `scenario.json`
  (blue_1 0.3/0.3, blue_2 -1.0/0.8, blue_3 -2.0/-0.5) but oracle says
  "play back to the goalie" — impossible instruction.
- **TC-09 high_line:** "pressing red offside" — **no offside rule exists**
  in `referee_node.py`; goalie identity undefined (no bot starts in goal);
  "sweeper goalie" conflicts with goalie blending override.
- **TC-08 def_transition + 2vs2:** reference dropped `role_diversity` KPI.
- **2vs2_default:** goalie at X=-4.0 but no bot starts there; still v5
  schema (`scene_type`/`label`).

**P1 (wording):** stale roles everywhere (striker/supporter in TC-01,
TC-04, TC-06, 2vs2); TC-01 goalie X=-4.2 actual; TC-03 kick-direction
(role-aware kick aims at opponent goal, "clear to sideline" not
executable); TC-06 shot range X>0.5 trivial (ball starts at 3.15),
goal mouth ±0.9 not ±1.5.

**P2 (dictionary-grounded):** remove dynamic role definitions everywhere;
verify TC-07 zone-defend/shadowing phrases (both USABLE per dictionary).

**P3:** TC IDs in headers; full rework; TC-10 kick_in creation.

**Files touched:**
- `core/src/tools/vocab_probe.py` (NEW — Phase 1 probe tool)
- `core/src/experiments/phase1_probes/a_series.jsonl` (NEW)
- `core/src/experiments/phase1_probes/b_series.jsonl` (NEW)
- `core/src/experiments/phase1_probes/c_series.jsonl` (NEW)
- `core/src/results/vocab_probe_log.md` (NEW — 44 probe records)
- `core/docs/c3_vocabulary_dictionary.md` (NEW)
- `core/docs/c3_testcase_review.md` (NEW)
- `core/docs/SESSION_CHANGELOG.md` (this entry)

**Files deleted:**
- (none)

**Not yet done:**
- P0/P1 test-case fixes (TC-05 goalie gap, TC-09 offside, TC-08/2vs2
  role_diversity, stale roles) — applied only in the review doc, NOT yet
  to `scenario/*/analysis.md` files.
- Phase 2 (rework `analysis.md` with dictionary vocabulary) — next.
- New probes for borderline entries: "own half / opponent half",
  "kick-in", "mark vs cover", corner placement.
- `llm_probe.py` (Phase F1) — not built.
- Nothing committed — all work uncommitted on
  `feature/v6.3-replay-and-optimization` (branch from session_entry.sh
  output; previously `feature/ros2k_behavior_optimization` body of work
  was committed in e3d01b0).

**Next:**
- Apply P0/P1 fixes to `scenario/*/analysis.md` (architecture facts —
  no probing needed), then run Phase 2 with the dictionary: rework the
  10 description files in Qwen's vocabulary (position verbs, no dynamic
  roles), translate referee rules per `referee_node.py`.
- Run the ~5 new borderline probes first to complete dictionary §8.

**Blockers:**
- None for text-only phases. Ollama on GPU, qwen2.5:3b warm.
- `batch_evaluator.py` KPI collection still broken (deprecated, carried
  from 2026-07-13 — orthogonal to C3 text-only phases).
- `session_entry.sh` generated the stub with a minor error (`[: 0
  0: integer expression expected`) and only prints to stdout — entry
  appended manually.

## 2026-08-01 (continued) — D-series probes, P0/P1 test-case fixes applied

**Goal:** Complete the borderline probe battery (D-series), then apply the
P0/P1 fixes from `c3_testcase_review.md` to the scenario `analysis.md` files.

**Done:**

### D-series probes (6 new, total 50 probes in Phase 1)
- `experiments/phase1_probes/d_series.jsonl` (NEW): D1 own half, D2 kick-in,
  D3 mark vs cover, D4 corner placement, D5 goal area, D6 clear near goal.
  All run, logged to `results/vocab_probe_log.md`.
- **Verdicts (merged into dictionary §1/§2/§4/§8):**
  - D1 "own half": usable only with explicit bound ("X from -4.5 to 0");
    "opponent half" broken (model said "+4.5 to 9" — treats field as 0..9
    range) → rephrase as "the red side of the center line".
  - D2 kick-in placement: placement logic **correct** ("touchline at
    Y=3.0" matches referee warp); terminology wrong ("direct free-kick")
    → referee-owned.
  - D3 mark vs cover: both understood AND distinct → both Usable.
    "cover a zone" added as new verb entry.
  - D4 corner placement: **hallucinated** ("corner flags at (0,-3) and
    (9,-3)"; actual ±4.5/±3.0) → referee-owned.
  - D5 goal area: **hallucinated** ("X=-4.5 to -6.5" — off the field) →
    Reject; concrete coordinates only.
  - D6 clear: defender "position yourself between the ball and the
    goalmouth" correct; goalie "dive left" impossible for bots → "between
    ball and goal" phrasing usable, "dive" never.
- Dictionary §8 updated: new-probes item → DONE with results.

### P0/P1 fixes applied (scenario `analysis.md` + `scenario.json`)
- **TC-01 attack_center:** striker→attacker, supporter→defender, goalie
  X=-4.0→-4.2 (actual scenario.json position).
- **TC-03 defensive_crisis:** "clear toward the sidelines" → "kick the
  ball upfield" (role-aware kick aims at opponent goal — sideline clear
  not executable); goalie action specified explicitly (hold goal line,
  track ball in Y).
- **TC-04 fast_counter:** striker→attacker, supporter→defender.
- **TC-05 pressing_trap:** oracle rewritten — "play back to the goalie"
  → "play back to the deepest blue bot" (no bot near own goal at
  kickoff; user chose text-only fix, scenario.json unchanged).
- **TC-06 long_shot:** supporter→attacker (rebound follow-up on the
  attacker); shot range X>0.5/|Y|<1.5 → ball X>2.0/|Y|<1.0 (aligned to
  goal mouth ±0.9, discriminating at this scenario's starting state).
- **TC-08 def_transition:** role_diversity reference removed → replaced
  with "`shots_on_goal` and `restart_recovery_time_s` are the KPIs to
  watch".
- **TC-09 high_line:** offside removed (no offside rule in
  `referee_node.py`); red_2-behind-line risk stated in fact; sweeper
  contradiction resolved — cover bot (blue_1) drops back, note that
  goalie blending pulls it to the line when ball is near.
- **2vs2_default:** "one goalie (X=-4.0)" → "one bot falls back to
  goalie position (X≈-4.0)"; striker→attacker; role_diversity reference
  removed. **scenario.json migrated v5 → v6 schema** (`scenario_name`/
  `mode`/`tactical_situation`; user approved).
- **3vs3_default:** same stale-role fix as TC-01 (legacy clone of TC-01
  positions; X=-4.0→-4.2, striker/supporter→attacker/defender).
- Verification: 92 fast tests pass, no stale role/KPI references remain
  in `scenario/` (grep clean).

**Files touched:**
- `core/src/experiments/phase1_probes/d_series.jsonl` (NEW)
- `core/src/results/vocab_probe_log.md` (6 more probe records, total 50)
- `core/docs/c3_vocabulary_dictionary.md` (§1 cover-a-zone verb, §2 own
  half, §4 D2/D4/D5/D6 rows, §8 DONE)
- `core/src/scenario/3vs3_attack_center/analysis.md` (roles, X=-4.2)
- `core/src/scenario/3vs3_default/analysis.md` (roles, X=-4.2)
- `core/src/scenario/3vs3_defensive_crisis/analysis.md` (upfield clear,
  goalie action)
- `core/src/scenario/3vs3_fast_counter/analysis.md` (roles)
- `core/src/scenario/3vs3_pressing_trap/analysis.md` (oracle rewrite)
- `core/src/scenario/3vs3_long_shot/analysis.md` (roles, shot range)
- `core/src/scenario/3vs3_def_transition/analysis.md` (KPI reference)
- `core/src/scenario/3vs3_high_line/analysis.md` (offside, sweeper)
- `core/src/scenario/2vs2_default/analysis.md` (goalie fallback text)
- `core/src/scenario/2vs2_default/scenario.json` (v6 schema migration)
- `core/docs/c3_testcase_review.md` (APPLIED note added)
- `core/docs/SESSION_CHANGELOG.md` (this entry)

**Files deleted:**
- (none)

**Not yet done:**
- P2 (full dictionary rework of all 10 files — position verbs, no dynamic
  roles) — Phase 2, next.
- P3: TC IDs in headers; TC-10 kick_in creation (Phase 5).
- TC-05/2vs2 open questions resolved: text-only fixes chosen, scenario
  positions unchanged.
- `llm_probe.py` (Phase F1) — not built.
- Nothing committed — all work uncommitted.

**Next:**
- Phase 2: rework the 10 `analysis.md` files in dictionary vocabulary
  (situation-triggered position verbs, no role-derived instructions,
  universal-knowledge phrases moved to a knowledge module per review
  cross-cutting item 2).

**Blockers:**
- None for text-only phases. Ollama on GPU, qwen2.5:3b warm.
- `batch_evaluator.py` KPI collection still broken (deprecated, carried
  from 2026-07-13 — orthogonal to C3 text-only phases).

## 2026-08-01 (continued) — TC-02..05 walkthrough, Expert/Oracle semantics fixed, coordinate rule probed, scenario-generation playbook

**Goal:** Walk all test scenarios with human-in-the-loop feedback, fix the
Expert/Oracle section semantics, empirically verify that oracle text requires
explicit coordinates, and hand over the session decisions + human soccer
knowledge into a reusable scenario-generation playbook.

**Done:**

### TC walkthrough (human feedback → translated → verified)

- **TC-02 attack_wing:** Expert first (angle too narrow, ball between blue_1
  and goal, red_2 far off will block, red_3 out of reach, blue_2 too far back
  for a backcourt pass); Oracle (blue_1 moves around ball, passes if blocked;
  blue_2 must actively take receiver position before the pass; blue_3 deep
  cover).
- **TC-03 defensive_crisis:** Expert (red_1 ON the ball, blue_1 only bot
  positioned to react directly, blue_2 anticipates, blue_3 lane blocked by
  red_2); Oracle (blue_1 intercepts, blue_2 cuts the dribble lane, blue_3 to
  left lane for pass/rebound).
- **TC-04 fast_counter:** Expert (free time to maneuver, blue_2 too far back,
  red_2/red_3 ignorable); Oracle with coordinates (blue_2 → -1.5,-2.5 left
  wing, blue_1 → -1.8,-0.4 kicking position, blue_3 stays back -4.0,0.0).
- **TC-05 pressing_trap:** Expert (red press, blue_3 too far from goal area);
  Oracle (blue_1 keeps ball/passes, blue_2 → 0.0,0.8 center line backup,
  blue_3 stays back).

### Section semantics fixed (user correction)

- **Oracle = strategy = things recommended to do.**
- **Expert = analyse the game state** (facts, geometry, reachability, NO
  imperatives).
- **Expert FIRST, Oracle second** — fixed order across all 10 files
  (re-sorted 9 files on 2026-08-01, attack_center/attack_wing already done).

### Coordinate rule — empirically verified (probes E/F/G)

- **E1/E2 (attack_center style, fast_counter state):** oracle WITHOUT
  coordinates → model placed blue_2 on the ball, blue_1 at the goal line
  (degenerate). With coordinates → all three copied correctly.
- **F1/F2 (pressing_trap, short description):** "stays back as deep backup"
  → model moved blue_3 FORWARD (negation inverted). With coordinates → correct.
- **G1/G2/G3 (expert/oracle balance):** G1==G2 (expert adds nothing when
  oracle has coords); G3 (expert only) → model *reasons* (moved blue_3 to goal
  area on its own) but fuzzy targets. → hybrid is the quality ceiling.
- **Rule:** every positional/negational verb carries explicit X,Y. The 3B
  model guesses wrong without coordinates.
- Batteries saved: `experiments/phase1_probes/{e,f,g}_series.jsonl`; all
  logged to `results/vocab_probe_log.md` (Phase 1 total now 56 probes:
  A14+B18+C12+D6+E2+F2+G3).

### Scenario-generation playbook (`core/docs/c3_scenario_generation_playbook.md` — NEW)

Model-agnostic handover doc (works as human spec AND as LLM prompt context):
- §2 field ground truth, §3 package structure (v6 schema), §4 section
  semantics with probe evidence, §5 **10 distilled soccer reasoning patterns**
  (P1 reachability/free-time, P2 out-of-reach=ignorable, P3 shooting angle,
  P4 numbers advantage, P5 anticipate the block, P6 pass-into-space, P7
  rebound readiness, P8 counter-attack cover, P9 lane/dribble denial, P10
  press escape — each with source TC), §6 vocabulary constraints, §7
  referee-owned concepts, §8 forbidden content, §9 anti-patterns table (A1-A5),
  §10 validation protocol (world↔diagram cmp, coordinate grep, cross-TC
  consistency, 3B probe with exact query format), §11 worked exemplars
  (4 validated TCs verbatim + placeholders for remaining 6), §12 extension
  notes (free-form, adding exemplars, future gen_scenario.py).

**Files touched:**
- `core/src/scenario/3vs3_attack_wing/analysis.md` (rewritten, Expert first)
- `core/src/scenario/3vs3_defensive_crisis/analysis.md` (rewritten)
- `core/src/scenario/3vs3_fast_counter/analysis.md` (rewritten + coords)
- `core/src/scenario/3vs3_pressing_trap/analysis.md` (rewritten + coords)
- `core/src/scenario/*/analysis.md` (9 files re-sorted Expert-first)
- `core/docs/c3_scenario_generation_playbook.md` (NEW)
- `core/docs/SESSION_CHANGELOG.md` (this entry)

**New files (untracked):**
- `core/docs/c3_scenario_generation_playbook.md`
- `core/src/experiments/phase1_probes/e_series.jsonl`
- `core/src/experiments/phase1_probes/f_series.jsonl`
- `core/src/experiments/phase1_probes/g_series.jsonl`

**Files deleted:**
- (none)

**Not yet done:**
- TC walkthrough: remaining TCs (TC-02 draft needs final coords + probe;
  TC-06 long_shot, TC-07 contain_delay, TC-08 def_transition, TC-09
  high_line, 2vs2_default). Append each to playbook §11 after validation.
- Playbook §5 patterns reference only TC-01..05; later TCs may add patterns.
- Generator tool `tools/gen_scenario.py` NOT built (deferred — user chose
  doc-only deliverable).
- "Shortening the prompt" experiment deferred (user flagged as later sidestep).
- 2vs2_default v6 schema migration done (2026-08-01 earlier session) —
  but its analysis.md walkthrough still pending.
- Nothing committed — all work uncommitted.

**Next:**
1. Continue TC walkthrough (TC-06 long_shot) with user feedback → translate
   → validate → append to playbook §11.
2. After all 10 TCs validated: re-baseline TC-01 kpi_targets.json for the new
   pro-blue setup (Phase 2.5d).

**Blockers:**
- None for text-only phases. Ollama on GPU, qwen2.5:3b warm.
- `batch_evaluator.py` KPI collection still broken (deprecated, carried
  from 2026-07-13 — orthogonal to C3 text-only phases).

## 2026-08-01 (continued) — 2vs2_default rework + prompt-structure study (V_A/V_B/V_C, 33+4 probes)

**Goal:** Rework 2vs2_default per user feedback (red active, blue_1/blue_2
clustered), run a prompt-structure study (Oracle-only vs full-Expert vs
condensed-ESSENCE) across all 11 scenarios, coin deviations OUR FAULT vs
QWEN'S FAULT, apply Oracle fixes, and rewrite the study report for readability.

**Done:**

### 2vs2_default rework
- `scenario/2vs2_default/scenario.json`: red active — red_1 (-0.4, 0.6) on the
  ball with free pass to red_2 (1.0, 1.0); blue_1 (-1.8, 0.2) / blue_2 (-1.5, -0.2)
  clustered (0.5 m apart); ball (-0.5, 0.5). `field_diagram.png` regenerated.
- `analysis.md` completed (Expert + Oracle). New two-man goal-mouth bracket
  pattern (short-post + long-post guard) added to `8_C3_SOCCER_KNOWLEDGE.md`
  as P-D6a.

### Prompt-structure study (33 probes)
- `experiments/prompt_structure/gen_battery.py` (NEW): reads
  `scenario/<name>/scenario.json` (world line: ball → blue_N → red_N) +
  `analysis.md` (Expert/Oracle sections) → `v{A,B,C}.jsonl` (11 probes each).
  V_A = Oracle only; V_B = full Expert + Oracle; V_C = 1–2 sentence hand-written
  ESSENCE + Oracle. System prompt template adapts bot count (two/three lines).
- All 33 run via `vocab_probe.py --batch` (series `PS_*`), logged to
  `results/vocab_probe_log.md` (lines 640–1385).
- **Result matrix:** V_A = V_C = 9.0/11 (F/P/D 8/2/1 each) > V_B = 8.0/11
  (7/2/2). The full-expert variant is the WORST, not an improvement — expert
  text anchors Qwen to listed positions and leaks forward bias (goalie_pass:
  blue_2 marked on ball, unmarked red_1 free on goal). Condensed essence is
  free (no cost vs Oracle-only).
- **Fault coin (8 deviations):** 5× OUR FAULT (+3 minor), 1× QWEN'S FAULT
  (high_line V_A b1 1.75 vs 2.0 — harmless 0.25 m rounding). Zero
  model-incapability cases. 2 scenarios clean (contain_delay, fast_counter).
- **Key mechanism discovered — output-slot anchoring:** def_transition Oracle
  already led with blue_3, yet V_A failed (tackle went to goalie). Qwen assigns
  the aggressive action to the FIRST output line (blue_1), regardless of who
  the Oracle names first. Fix = list actions in OUTPUT ORDER b1→b2→b3, not
  role-lead order. Verified: V_B/C fixed it because expert text named blue_1
  as goalie.
- **Worst cases:** attack_wing (V_C b3 OOB (-6.0, 0.1) — Oracle gave b3 no
  target; V_B b1 below ball = zero shooting angle); defensive_crisis (V_B b1
  freezes on goal line (-4.0, 0.55), fails to intercept).

### §6 Oracle fixes applied + verified (VERIFY_* probes, 4/4 exact)
- `3vs3_attack_center`: Oracle "moves to the ball at (2.2, 0.3)" (b2 now exact).
- `3vs3_attack_wing`: explicit targets — b1 (3.4, 2.0), b2 (2.5, 2.5), b3 (-4.0, 0.0).
- `3vs3_defensive_crisis`: b1 intercept (-3.1, 0.45), b2 (-2.7, 0.3), b3 (-1.5, -0.6).
- `3vs3_def_transition`: output-order action list with anchors — b1 (-3.6, 0.3),
  b2 (2.0, -2.0), b3 (2.2, 0.0).
- Regenerated vA/vB/vC.jsonl (14:48); `verify_fixed.jsonl` (NEW, 4 probes,
  series `VERIFY_*`) re-probed in V_A format — all targets exact. Report §7
  verification table.
- All 92 fast tests pass.

### Report rewritten for readability (`results/prompt_structure_report.md`)
- Per-scenario sections: embedded `field_diagram.png` (all 11 exist), world
  state, TC reference verbatim (Expert + Oracle), Qwen output table
  (V_A/V_B/V_C + VERIFY row), discrepancies BOLD, fault coined with soccer
  pattern reference (P3/P4/P6/P8/P-D6a).
- §4 deviation double-check table (8 rows), §5 rankings, §6 recommendations
  (V_A as standard, V_C conditional, V_B dropped), §7 verification.
- Residual OUR FAULT minor: attack_center b3 still outputs (1.5, -1.4) for
  "moves slightly forward" — vague cue needs a coordinate.

**Files touched:**
- `core/src/scenario/2vs2_default/scenario.json` (rework), `field_diagram.png`
  (regenerated), `analysis.md` (completed)
- `core/src/ros2k_knowledge/8_C3_SOCCER_KNOWLEDGE.md` (P-D6a)
- `core/src/experiments/prompt_structure/gen_battery.py` (NEW)
- `core/src/experiments/prompt_structure/vA.jsonl` / `vB.jsonl` / `vC.jsonl`
  (regenerated 14:48)
- `core/src/experiments/prompt_structure/verify_fixed.jsonl` (NEW)
- `core/src/results/vocab_probe_log.md` (33 PS_* + 4 VERIFY_* records)
- `core/src/results/prompt_structure_report.md` (NEW, rewritten readability pass)
- `core/src/scenario/3vs3_attack_center/analysis.md` (Oracle fix)
- `core/src/scenario/3vs3_attack_wing/analysis.md` (Oracle fix)
- `core/src/scenario/3vs3_defensive_crisis/analysis.md` (Oracle fix)
- `core/src/scenario/3vs3_def_transition/analysis.md` (Oracle fix)
- `core/docs/SESSION_CHANGELOG.md` (this entry)

**New files (untracked):**
- `core/src/experiments/prompt_structure/` (gen_battery.py, vA/vB/vC.jsonl, verify_fixed.jsonl)
- `core/src/results/prompt_structure_report.md`

**Files deleted:**
- (none)

**Not yet done:**
- attack_center b3 "slightly forward" cue needs a coordinate (residual OUR
  FAULT minor).
- Playbook §11 exemplars not yet appended (only §5 P-D6a knowledge-side done);
  playbook §10.4 V_A confirmed as reliable validation gate.
- TC-01 kpi_targets re-baseline still pending (Phase 2.5d).
- "remind me of 3" open item: `rules_core.txt` dynamic-goalie/static-role
  contradiction (dictionary C2_striker_rule finding) — not yet addressed.
- Nothing committed — all work uncommitted on
  `feature/v6.3-replay-and-optimization`.

**Next:**
1. New session: read this changelog, then fix attack_center b3 coordinate
   (1-line Oracle edit + VERIFY re-probe).
2. Append validated TCs to playbook §11 exemplars (4 fixed TCs ready verbatim).
3. Address "remind me of 3" (rules_core.txt contradiction) per dictionary.
4. Re-baseline TC-01 kpi_targets (needs Gazebo/Ollama, Phase 2.5d).

**Blockers:**
- None for text-only phases. Ollama on GPU, qwen2.5:3b warm.
- `batch_evaluator.py` KPI collection still broken (deprecated, carried
  from 2026-07-13 — orthogonal to C3 text-only phases).

## 2026-08-02 — K3 battery: competition & pass gaps, explain-text pipeline fix, gap diagnostics

**Goal:** Execute K3 (per-gap rule-vs-example tests for ball competition and
passing) with two new battery situations + gap diagnostics, and fix the
ANALYSIS:/ORACLE: explain-text pipeline (visualizer + annotator + evaluator
parse) that was silently dropped in TEXT mode.

**Done:**

### Explain-text pipeline fix (one change set, user-requested bundling)
- **Root cause:** `text_parse()` in `r2k_evaluator.py` deliberately discarded
  `ANALYSIS:`/`ORACLE:` lines; `fast_parse` (JSON) kept them, so explain
  fields showed only in JSON mode. The visualizer showed "FAST EXECUTION
  MODE" in TEXT mode; the annotator's `read_last_llm_decision` had the same
  JSON-only limitation.
- `r2k_evaluator.py`: `PROSE_MARKER_RE` (case-insensitive `(\*\*)?(ANALYSIS|ORACLE)\s*:`),
  `PROSE_MAX_CHARS = 600`. `text_parse()` now captures `data["analysis"]` /
  `data["oracle"]` (marker → next marker/first `blue_N` line, continuation
  lines joined, trimmed, capped 600 chars). `TEXT_LINE_RE` extended: accepts
  `stay at` and trailing prose (`move to (1.5, -1.1) and intercept the pass
  from red_3`, `stay at (-2.4, -0.7)`).
- `r2k_visualizer.py`: `_parse_llm_decision` falls back to `text_parse()`
  when no JSON dict / no `assignments` key. Also guards `data.get(...) if
  data else {}`.
- `tools/match_annotate.py`: `read_last_llm_decision` same text fallback
  (`sys.path.insert(0, str(BASE_DIR))` for the lazy import).
- **Verification:** real explain trace (`logs/llm_trace_3vs3_attack_center_*
  20260802_190059.jsonl`) — 29/30 records now parse (was ~0: the old strict
  regex also failed on the evaluator side, so explain-mode runs sent no
  commands at all). Visualizer fallback verified; annotator fallback verified.
- Tests: +5 in `tests/test_text_mode.py` (prose captured, multiline joined,
  no-prose → no keys, prose after bot lines, trailing prose). Suite: 147
  passed / 11 skipped.

### K3 battery — 2 new situations + gap diagnostics (`tools/i3_battery.py`)
- New situations: `competition_ball` (ball (1.0,0.0); blue_1 (0.7,0.3) +
  blue_2 (1.3,-0.3) both within 0.5m; red_1 (1.6,0.0) pressing) and
  `free_man_pass` (ball (2.5,-1.0); blue_1 on ball; blue_2 unmarked at
  (4.0,0.8) — 0.5m from opponent goal line; red_1 pressing the carrier).
- `score_result()` diagnostics (diagnostic-only, do NOT change the 0-100
  score): `gap_competition` (exactly ONE ball-targeter: kick or Move ≤1.5m
  from ball; all other Move targets ≥1.0m from ball) and `gap_pass` (kick
  present AND ≥1 non-kicker's Move target x > ball.x — a receiving position
  forward of the ball; excludes only kickers so receivers within
  BALL_PROXIMITY still count).
- CLI: `--only <situations>` (filter by label) and `--header <file>`
  (replaces `ev.TEXT_OUTPUT_HEADER`). Report table gains Gap-C / Gap-P
  columns.

### K3 experiment run (7 variants × 25 situations × 2 encodings × 3 repeats)
| Variant | competition gapC | free_man gapP | Channel |
|---|---|---|---|
| v0 (baseline) | 0/3 | 0/3 | K2 header only |
| k3a_rule | 2/3 | 0/3 | rules_3vs3.txt SPECIAL SITUATIONS |
| k3b_example | 0/3 | 0/3 | samples_3vs3.txt EXAMPLE 2 |
| k3c_header | 0/3 | 0/3 | SPLIT+PASS rules in header |
| k3f_header2 | 3/5 | 4/5 | + PASS EXAMPLE in header |
| k3g_combined | 0/5 | 2/5 | rules file + header (overload) |
| **k3h_ownhalf** | **3/3** | **3/3** | PASS RULE gated to X>0 |

**Findings:**
1. Competition split needs a RULE (rule form 2/3 vs example form 0/3); the
   model's default is the double-chase standoff (both bots hold equidistant).
2. Pass needs an EXAMPLE, not just a rule — the rule alone (k3c) fixes the
   kicker (wrong-bot kick was the real v0 failure: blue_2 kicks from 2.6m)
   but the receiver never runs forward; the PASS EXAMPLE makes blue_2 run to
   (4.0, Y).
3. PASS RULE must be gated to the opponent half (X>0) — ungated it fires in
   defensive situations (ball at -3.1) and pushes bots forward wrongly.
4. Combining rule-file + header regresses (k3g): rule text in two channels
   degrades kicker selection. One channel only.
5. Output-slot anchoring (prompt-structure study) reproduces: kick on output
   line 2 (blue_2) when line 1 is a Move — the header rules push kick to
   line 1.

**Full-battery regression check (25 situations):**
| Variant | TEXT hard | TEXT score | gapC% | gapP% |
|---|---|---|---|---|
| v0 | 96.2% | 76.4 | 30.8% | 3.8% |
| k3h | 93.6% | 75.5 | 60.3% | 70.5% |

Hard-gate dip (96.2→93.6) = phantom-bot lines in 1vs1/2vs1 situations
(PASS EXAMPLE reinforces the 3-line structure) — accepted, real matches are
3vs3 where 3 lines are correct.

### Wire-in + knowledge
- `r2k_evaluator.py` `TEXT_OUTPUT_HEADER` (lines 63-88): now contains KICK
  RULE + SPLIT RULE + PASS RULE (gated X>0) + PASS EXAMPLE. This is the K3
  winner — the live system prompt now splits contested balls and passes to
  free men.
- `ros2k_knowledge/8_C3_SOCCER_KNOWLEDGE.md`: new patterns P-C2a
  (competition split) and P-A3b (pass to the free man) with K3 evidence.
- `results/k3_results.md` (NEW): full K3 report with variant table, findings,
  wire-in, next steps.

**Files touched:**
- core/src/tools/i3_battery.py (+2 situations, gap diagnostics, --only/--header, Gap-C/Gap-P columns, gap_pass refinement)
- core/src/ai_tactics/r2k_evaluator.py (explain prose capture, TEXT_LINE_RE relaxed, K3 header wire-in)
- core/src/r2k_visualizer.py (_parse_llm_decision text fallback + guard)
- core/src/tools/match_annotate.py (read_last_llm_decision text fallback)
- core/src/tests/test_text_mode.py (+5 tests)
- core/src/ros2k_knowledge/8_C3_SOCCER_KNOWLEDGE.md (P-C2a, P-A3b)
- core/docs/SESSION_CHANGELOG.md (this entry)

**New files (untracked):**
- core/src/experiments/k3_rule/fragments/ (rule-form variant)
- core/src/experiments/k3_example/fragments/ (example-form variant)
- core/src/experiments/k3_header/header.txt, header_h.txt (header variants)
- core/src/results/k3_results.md (K3 report)
- core/src/results/i3_sweep_k3{v0,a,b,c,f,g,h}*_raw.jsonl + reports (7 variant batteries)

**Files deleted:**
- (none) — k3_combined temp dir removed (k3g variant kept as raw evidence)

**Not yet done:**
- Explain pipeline fix verified on trace but NOT on a live match — user
  played a match during the session (run 20260802_191721) after the
  `--analyze`/annotator discussion but the annotator interaction "works now"
  was reported for the annotator itself; visualizer/replay live check still
  pending.
- K4 if needed: phantom-bot leakage in 1-bot situations (low priority — real
  matches are 3vs3).
- Phase F4 (content sweep) should include the k3h header as a content
  variant.
- Nothing committed — all work uncommitted (5 change sets now: 4 previous +
  this K3/explain session).

**Next:**
1. Wire-in verification live: run a match with `--explain`, confirm
   visualizer shows STRATEGY/ORACLE text and llm_trace carries analysis/oracle
   in TEXT mode; confirm the SPLIT/PASS rules appear in the live prompt.
2. Phase F1 (llm_probe.py + synthetic world-states) or continue K-series
   (K4 phantom fix) per user priority.
3. Re-ask about committing (5 change sets uncommitted).

**Blockers:**
- None for text-only phases. Ollama on GPU, qwen2.5:3b warm (session start:
  OK; annotator run 191721 played fine).
- `batch_evaluator.py` KPI collection still broken (deprecated, carried
  from 2026-07-13 — orthogonal to C3 text-only phases).

## 2026-08-02 (continued) — Phase F executed: structure sweep F0-F3, content sweep F0-based, paradigm verdict

**Goal:** Execute Phase F (few-shot paradigm rework) per plan: build the probe
instrument + synthetic corpus, run the F3 structure sweep (interwoven vs
separate samples), then the F4 content sweep on the winner. Decision point
resolved with user: F4 = content sweep on F0 structure; F3 re-run with fixed
metrics approved.

**Done:**

### Explain-mode kick gap fixed (pre-F3 blocker)
- Smoke tests (F3 on free_man_pass) showed code=2 failures: explain mode uses
  `TEXT_EXPLAIN_INSTRUCTION`, which contains NO K3 rules (KICK/SPLIT/PASS) —
  those live only in `TEXT_OUTPUT_HEADER` (non-explain). The kick-sensitive
  `free_man_pass` situation collapsed without them.
- `llm_probe.py`: new user_header variants `explain_full` (=TEXT_EXPLAIN_INSTRUCTION),
  `explain_oracle` / `explain_analysis` (new `EXPLAIN_ORACLE_HEADER` /
  `EXPLAIN_ANALYSIS_HEADER` constants), `explain_k3h` (= explain + K3 rules
  section appended via new `_k3_rules_section()`), `full_nok3h`
  (= TEXT_OUTPUT_HEADER without the KICK RULE section, for F4). Explain
  detection is now header-name-derived (`is_explain_style()`), replacing the
  removed `explain` config key.
- Verification: F4_k3h (F3 structure + K3 rules in explain header) fixed
  free_man_pass (code 2→0, score 0→90) — K3 rules are load-bearing in the
  user prompt; interwoven samples alone are not enough.

### F1 tooling (per plan)
- `tools/llm_probe.py` (NEW, ~540 lines): config registry F0-F4, 9 text
  metrics, `--config/--corpus/--model/--repeat/--tag/--only/--frag-dir/
  --list-configs`, outputs `results/probe_<tag>_raw.jsonl` + report.
- `tools/build_corpus.py` (NEW): builds `tests/synthetic_worldstates/
  corpus.jsonl` — **81 states** = 26 battery + 10 hand-crafted edge cases
  + 45 trace frames (wildcard globs across 6 scenario prefixes; first build
  only had 9 frames due to non-wildcard globs). Statuses: kickoff 3 /
  playing 62 / ball_out 10 / goal_kick 2 / corner_kick_in 2 / goal 1 /
  foul_penalty 1.
- `experiments/f_structure/fragments/`: `rules_core_min.txt`, interwoven
  samples `samples_interwoven_1/3vs3/6.txt` (ORACLE lines rewritten as pure
  prose after smoke 1 — "blue_N will move to (X,Y)" collided with the
  ASSISTANT command format and produced empty/merged output).
- `experiments/f4_content/fragments/`: `samples_3vs3_1.txt` + `samples_3vs3_6.txt`
  (json_blocks format, 1/6 examples — F0's samples_3vs3.txt already has 1).

### Metric fixes mid-sweep (found via F3 report)
- `i3_battery.py` `text_parse_relaxed()` returned assignments only — it never
  captured ANALYSIS/ORACLE prose, so `analysisQ`/`oracleQ`/`contradiction`
  were 0.00 everywhere. Added `PROSE_MARKER_RE`/`PROSE_MAX_CHARS` prose
  capture (mirrors `ev.text_parse`), returned as `data['analysis']`/
  `data['oracle']`.
- `llm_probe.py` `compute_continue_accuracy()` compared raw-response strings
  (0-6% — temp 0.0 is not bit-exact across KV-cache states, 2026-08-01
  finding). Now compares canonicalized parsed assignments semantically.
- Records now store `assignments` (for re-scoring from raw files).

### F3 structure sweep (972 probes, 13.6 min, 4 configs × 81 × 3)

| Config | hard% | parse% | score | vocab | ruleF | cov | analysisQ | oracleQ | continue | lat p50 |
|---|---|---|---|---|---|---|---|---|---|---|
| **F0** (global rules + separate samples) | **93%** | **100%** | **64.8** | **1.00** | **0.97** | **1.00** | 0.00¹ | 0.00¹ | 5% | **217ms** |
| F1 (min rules + interwoven) | 62% | 84% | 57.4 | 0.83 | 0.76 | 0.77 | 0.83 | 0.83 | 14% | 932ms |
| F2 (no global, interwoven only) | 56% | 83% | 56.9 | 0.83 | 0.75 | 0.73 | 0.73 | 0.77 | 18% | 978ms |
| F3 (axioms + interwoven, explain) | 81% | 90% | 64.5 | 0.91 | 0.88 | 0.90 | 0.90 | 0.91 | 7% | 939ms |

¹F0 non-explain produces no prose — 0.00 correct, not a metric gap.

**Verdict: interwoven paradigm loses decisively.** 3B extracts rules from
global declarative text + separate samples far better than from inline
commentary. Explain mode: +4.3× latency (217 vs ~940ms) for prose the bridge
never consumes.

### F4 content sweep on F0 (1215 probes, 6.8 min, 5 configs × 81 × 3)

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
2. **K3 rules are load-bearing**: F4_nok3h scores higher on the soft metric
   (69.9 — scorer rewards Hold over Kick) but loses EVERY gap (0/3, 0/3).
   The soft score rewards passivity; gap diagnostics capture soccer
   semantics. K3 header rules stay.
3. **Explain mode on F0 is catastrophic** (56% hard, cov 0.79, 691ms) —
   prose crowds out commands. Explain = display-only.
4. **Phantom-bot emission** (K4, known): 1-bot situations (1vs1_defend) get
   3-line outputs from sample-structure copying — 100% hard-fail in every
   config. Real matches are 3vs3; low priority.
5. `foul_penalty` has no game-phase fragment (falls back to mode rules) —
   corpus's 1 such state shows the model ignoring red_2 on the ball,
   kicking from 7m. Low priority (fouls are referee-owned).

### Phase F verdict
**F0 structure as-is is the Phase F optimum**: global rules_core_text +
rules_3vs3 + 1 separate json sample + k3h header, non-explain. The current
production prompt needs NO fragment changes. Semantic determinism at temp 0.0:
continue 2-18% — confirms 2026-08-01 KV-cache finding; identical-input
determinism is NOT bit-exact.

### Tests
- All 147 fast tests pass (147 passed, 11 skipped) after metric fixes.
- Plan doc `c3_phase0_literature_and_plan.md`: Phase F marked DONE, full
  result block appended (both sweep tables, verdict, artifacts).

**Files touched:**
- core/docs/c3_phase0_literature_and_plan.md (Phase F DONE + results block)
- core/src/tools/llm_probe.py (header variants, semantic determinism,
  F4 configs, assignments in records)
- core/src/tools/i3_battery.py (prose capture in text_parse_relaxed)
- core/src/tools/build_corpus.py (NEW)
- core/src/tests/synthetic_worldstates/corpus.jsonl (NEW — 81 states)
- core/src/experiments/f_structure/fragments/ (rules_core_min.txt,
  samples_interwoven_1/3vs3/6.txt — ORACLE prose rewrite)
- core/src/experiments/f4_content/fragments/ (samples_3vs3_1/6.txt)
- core/docs/SESSION_CHANGELOG.md (this entry)

**New files (untracked):**
- core/src/tools/llm_probe.py, core/src/tools/build_corpus.py
- core/src/tests/synthetic_worldstates/corpus.jsonl
- core/src/experiments/f4_content/ (fragments)
- core/src/results/probe_f3_structure_raw.jsonl + _report.md
- core/src/results/probe_f4_content_raw.jsonl + _report.md
- core/src/results/probe_smoke_f3{c,d}_raw.jsonl + reports

**Files deleted:**
- (none)

**Not yet done:**
- K4 phantom-bot fix (1-bot situations emit 3 lines) — deferred, low
  priority (real matches are 3vs3). If done: gate the line count to
  `n_blue` bots in the prompt or pad 1vs1 situations.
- `foul_penalty` game-phase fragment — deferred (referee-owned; LLM gets
  passive awareness only).
- Explain-mode visualizer/replay live check (carried from earlier session).
- Nothing committed — all work uncommitted (6 change sets now: 4 previous +
  K3/explain + Phase F).

**Next:**
1. Append Phase F result to the changelog-adjacent artifacts if needed;
   consider wiring Phase F winner (F0 = current production) as
   `R2K` default — no code change required.
2. Phase 2 (rework `analysis.md` files with dictionary vocabulary) or
   Phase W (watchdog & closed-loop feedback, text-only) per user priority.
3. Re-ask about committing (6 change sets uncommitted).

**Blockers:**
- None for text-only phases. Ollama on GPU, qwen2.5:3b warm (sweeps ran
  cleanly at 216-1000ms/probe).
- `batch_evaluator.py` KPI collection still broken (deprecated, carried
  from 2026-07-13 — orthogonal to C3 text-only phases).
## 2026-08-02 (continued) — redesign_eval_project_info.md: deep-detail sections for all executed phases

**Goal:** Build `core/docs/redesign_eval_project_info.md` (management summary
doc: project plan + per-phase deep details), fill deep-detail sections for
all six executed phases (0, 1, L, I, K, F) from the primary C3 sources.

**Done:**

### Doc creation + user decisions
- Created `core/docs/redesign_eval_project_info.md` (user-approved location;
  user chose full phase list as-is over high-level grouping).
- Removed "Reserved sections (filled later)" stub block on user request
  (Hypotheses/Methodology/Setbacks/Architectural Decisions/Results) — header
  keeps "More sections to come later."
- `core/docs/redesing_eval.txt` (and `redesing_prompts.txt`) are the user's
  private notes files — not part of the project doc.

### Deep-detail sections (v0.4, 597 lines)
- **Phase 0** (2026-07-31): 13-paper literature table with "what it decided
  for us", model switch evidence (qwen2.5-coder:3b → qwen2.5:3b, 70/20/10
  corpus split), corrected framing table, old (11.8% WR invalidated) vs new
  27-run baseline (11:21 goals, 0.41/0.78 per match, composite 0.32, p50
  744ms), latency budget (no-explain ~744ms / explain ~1100ms / format:json
  ~2081ms reverted), 6 key decisions.
- **Phase 1** (2026-08-01): 56-probe campaign table (A 14 / B 18 / C 12 /
  D 6 / E-G 7 + PS/VERIFY), dictionary verdicts, coordinate rule (E/F/G
  evidence), contradiction baseline, test-case review P0-P3 + walkthroughs
  (Expert FIRST / Oracle second), V_A/V_B/V_C study (9.0 vs 8.0/11,
  output-slot anchoring), 2vs2 rework, playbook.
- **Phase L** (d115503): 22-fragment dictionary migration, LVERIFY_1/2
  probes, token diff +5 chars across 21 files.
- **Phase I** (7b6b4fa): text transform, I3 battery (JSON 928ms vs TEXT
  443ms, −52%), 4 key fixes (example-copy → X,Y placeholders + DO NOT COPY
  law; coverage → ONE LINE PER BOT law; restart singularity → every-other-
  bot append; hold position verb + bridge skip branch).
- **Phase K** (2026-08-02): K2 positive-information sweep (1380 probes, v0
  TEXT 100% wins, lengthening REJECTED; JSON V3 ROLES block is the only
  content that matters), K3 gap tests (k3h_ownhalf 3/3+3/3 winner, one
  channel only), regression v0→k3h (96.2/76.4/30.8/3.8 → 93.6/75.5/60.3/
  70.5), wire-in to TEXT_OUTPUT_HEADER.
- **Phase F** (2026-08-02): F1 tooling (llm_probe.py, build_corpus.py,
  81-state corpus), explain-mode kick gap fix (explain_k3h header variant),
  metric fixes (prose capture in text_parse_relaxed, semantic determinism
  in continue_accuracy), F3 interwoven REJECTED (F0 93% hard/217ms vs F1/F2
  56-62%/932-978ms), F4 content (F4_s1 98% — 1 sample sufficient; F4_nok3h
  soft-score 69.9 but 0/3+0/3 gaps — K3 rules load-bearing; F4_explain 56%
  catastrophic), verdict F0 = production optimum, no fragment changes needed.

### Status table correction
- `redesign_eval_project_info.md` Document status: "Nothing committed"
  row corrected → Phases L (d115503) + I (7b6b4fa) committed; Phase 0/1 +
  K/F + this doc uncommitted. (Verified against `git log`.)

**Files touched:**
- `core/docs/redesign_eval_project_info.md` (NEW — v0.4, 597 lines)
- `core/docs/SESSION_CHANGELOG.md` (this entry)

**New files (untracked):**
- `core/docs/redesign_eval_project_info.md`

**Files deleted:**
- (none)

**Not yet done:**
- Deep-detail sections for pending phases (2, 3, W, 4, 4b, 5) — not executed
  yet, no deep details exist; doc keeps plan-level rows only.
- `redesing_eval.txt` / `redesing_prompts.txt` (user's private notes) not
  reviewed — user said the .txt is for their notes.
- Nothing committed for Phases 0/1/K/F + this doc (L/I already committed).

**Next:**
- Phase 2 (rework test case descriptions with dictionary vocabulary) per
  plan, or user direction.
- Optionally commit this doc + Phase K/F artifacts when user asks.

**Blockers:**
- None for text-only phases. Ollama on GPU, qwen2.5:3b warm.
- `batch_evaluator.py` KPI collection still broken (deprecated, carried
  from 2026-07-13 — orthogonal to C3 text-only phases).

---
Full history. Active changelog contains entries from 2026-08-03 onward.
