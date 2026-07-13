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