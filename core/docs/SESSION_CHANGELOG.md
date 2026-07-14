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