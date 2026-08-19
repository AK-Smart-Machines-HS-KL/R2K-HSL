# AGENTS.md

ROS2K = hybrid robotics testbed where a local LLM (Qwen2.5-Coder:3b via Ollama) drives
Gazebo-simulated and physical robots (Yahboom, Booster K1) via flat-JSON file polling on tmpfs.

> [!warning] Before ending any session: append an entry to `core/docs/SESSION_CHANGELOG.md`
> via `./docs/session_entry.sh`. See "Session continuity protocol" at the bottom of this file.

All work happens under `core/`. The repo root is a thin wrapper (README, `git_rules.md`, `utils/ros2_relay`).

## Primary knowledge sources (read before non-trivial work)

- `core/docs/SESSION_CHANGELOG.md` — **READ THIS FIRST after a reboot.** Append-only session log: what was done, what's next, what's blocking. Cross-session continuity.
- `core/.github/copilot-instructions.md` — architecture axioms and agent persona rules.
- `core/docs/` — developer-facing specs: `optimization_spec_v6.md` (v6.1 spec with phase checkpoints), `spec_taktische_evaluierung.md` (German historical design decisions), `referee_rulebook.md` (complete referee decision catalog with thresholds, field diagrams, state machine — read before changing any rule). C3 inter-lingua work: `c3_phase0_literature_and_plan.md`, `c3_vocabulary_dictionary.md`, `c3_testcase_review.md`, `c3_scenario_generation_playbook.md` (see `7_C3_INTER_LINGUA.md` §9).
- `core/src/ros2k_knowledge/` — RAG power-files (`1_CORE_…` … `8_C3_SOCCER_KNOWLEDGE.md`) + `META_KNOWLEDGE_ROUTER.md` (inverted index of symptoms → which file has the answer). Consult the router before debugging.
- `core/user doc/rosk2_technical_documentation/` — 40-file detailed architecture reference (human-facing).
- `core/src/scenario/README.md` — scenario naming + v5/v6 schema rules.
- `git_rules.md` (repo root) — branch naming + language conventions.

## Run / build / test commands

One entrypoint: `core/launch_r2k.sh`. Always invoke from `core/`. It `cd`s into `core/src/` itself.

```
# First-time setup (builds ros2_ws, micro-ROS agent, venv on U22; Docker image on U24)
# Installs host prerequisites including jq (used by launch_r2k.sh to parse relay JSON)
./install.sh

# Run a match (sim only)
./launch_r2k.sh --scenario 2vs2_default --relay only_sim_bots

# Run with real hardware mirrored
./launch_r2k.sh --scenario 1vs1_defend --relay hardware_mirror

# Batch/headless evaluation
./launch_r2k.sh --headless --duration 30 --scenario 3vs3_attack_center
./launch_r2k.sh --help   # full flag list
```

Teardown is autonomous: closing the Gazebo window (or CTRL+C) triggers the 0.2s watchdog
inside `launch_r2k.sh` which sends Kinematic Freeze (Twist-zero / K1 API 2000) then `pkill -9`.
Do not run `kill_r2k.sh` manually — it is deprecated.

Tests (pytest, `pytest.ini` + `conftest.py` configure markers):

```
# From core/src/ with venv active (U22) or inside the Docker container (U24):

# Fast tier (unit tests only, ~2s) — run after every code change:
python3 -m pytest tests/ --skip-slow -v

# Slow tier (unit + non-functional, ~10min) — run before commit:
python3 -m pytest tests/ -v -s

# Single slow test (real 120s Gazebo match + KPI assertions):
python3 -m pytest tests/test_non_functional.py::test_attack_center_latency -v -s
```

Two-tier test system:
- **Fast** (`--skip-slow`): 91 unit tests (rule logic, parsing, set-piece math). ~2s.
- **Slow** (default): 91 unit + `test_non_functional.py` (real 120s Gazebo matches with
  per-scenario KPI assertions). ~140s per slow test.
- `@pytest.mark.slow` marker registered in `pytest.ini`; `--skip-slow` implemented in
  `conftest.py`.
- Composite score formula (spec §5.2): `composite = 0.4*goal_diff_norm +
  0.3*tac_score_norm + 0.2*possession_norm + 0.1*latency_factor`. Range [0, 1].
  Computed by `compute_composite()` in `test_non_functional.py`.
- Per-scenario thresholds in `scenario/<name>/kpi_targets.json`. Asserted by
  `test_non_functional.py` slow tests.

Tests gracefully skip when `rclpy` is missing, but the integration smoke tests that
actually exercise the stack require a running ROS 2 + Gazebo environment.

ROS 2 workspace build (only when msg definitions or `r2k_world_model` change):

```
# From core/src/ (U22, native):
source /opt/ros/humble/setup.bash
cd ros2_ws && colcon build && cd ..

# U24 (Docker): container must be running first, then exec colcon inside:
docker compose up -d                    # start container (if not running)
docker exec core_gazebo bash -c "source /opt/ros/humble/setup.bash && cd /workspace/ros2_ws && colcon build"

# If colcon fails with "numpy/ndarrayobject.h not found" (stale cached build):
docker exec core_gazebo bash -c "cd /workspace/ros2_ws && rm -rf build install"
# Then re-run the colcon build command above. The clean build resolves the
# numpy header path via the rosidl CMake fallback (python3 -c "import numpy").
# Do NOT install python3-numpy-dev or set CFLAGS — these are red herrings.
# Do NOT use --packages-select for the first rebuild after editing world files
# or URDFs — a full clean build is needed to propagate installed resources.
```

The `brain` package contains only `.msg` files (`GoToBallAndKickCmd.msg`, `Kick.msg`) — no source.
`r2k_world_model` provides the `tracker` executable used by `launch_r2k.sh`.
Note: `score_node.py` exists in BOTH `ros2_ws/src/r2k_world_model/` and `core/src/`;
`launch_r2k.sh` runs the standalone `core/src/score_node.py`, not the colcon-built one.

No lint/typecheck/format config exists. `r2k_world_model` ships ament lint tests
(`test_flake8.py`, test_pep257.py`, `test_copyright.py`) under `ros2_ws/.../test/`.

## Architecture axioms

See `core/src/ros2k_knowledge/agent_prompt_de.txt` (10 axioms, German, for the LLM)
and `core/.github/copilot-instructions.md` (symlink to the same). Loaded into every
opencode session via `.opencode/opencode.json → instructions`.

## File layout that isn't obvious from names

- `core/src/` is the runtime CWD. All standalone Python nodes
  (`referee_node.py`, `score_node.py`, `reward_node.py`, `state_aggregator.py`,
  `rule_evaluator_red.py`, `r2k_visualizer.py`, `setup_r2k.py`) live here, NOT in `ros2_ws/`.
- `core/src/ai_tactics/` — `r2k_evaluator.py` (LLM driver), `ollama_sandbox_bridge.py` (HAL),
  `batch_evaluator.py`, `json_spawner.py`. Also holds **transient** files regenerated every boot:
  `active_relay.json`, `active_scenario.json`, `system_prompt.txt` — do not hand-edit these.
- `core/src/relay/*.json` — relay profiles selected by `--relay` (e.g. `only_sim_bots`,
  `hardware_mirror`). `hardware_type` ∈ {`virtual`, `yahboom`, `k1`}.
- `core/src/scenario/*.json` — match setups. Filename prefix `<mode>_` selects prompt
  fragments via `setup_r2k.py` (`rules_<mode>.txt` + `samples_<mode>.txt`). v5 schema
  (`scene_type`/`label`) and v6 schema (`scenario_name`/`mode`/`tactical_situation`) coexist;
  see `scenario/README.md`.
- `core/src/strategy/fragments/` — prompt fragments (`header.txt`, `rules_core.txt`,
  `rules_<mode>.txt`, `samples_<mode>.txt`, `rules_ball_out.txt`, `rules_goal_kick.txt`,
  `rules_corner_kick_in.txt`, `rules_kickoff.txt`) assembled by `setup_r2k.py` into
  `ai_tactics/system_prompt.txt` on each boot (for `dump_prompt.py` dry-runs only —
  the evaluator assembles from fragments directly at runtime via dynamic prompt
  injection). `strategy/strat_*.txt` are build artifacts (gitignored) — do NOT hand-edit
  them; edit `fragments/` instead.
- `core/src/shared_state/` — runtime state files (`Worldstate.json`, `current_strategy.json`).
  Should be on tmpfs in production; tracked in git as scaffolding.
- `core/src/ros2_ws/src/brain/msg/` — custom ROS 2 msgs. Rebuild with colcon when changed.
- `core/src/booster/` — Booster K1 vendor headers/manual (reference only, not built).

## Booster K1 hardware specifics

- K1 ignores standard `cmd_vel`/Twist. Commands serialize to `booster_msgs/RpcReqMsg` on
  `<ns>/LocoApiTopicReq`. `header` = JSON with `api_id`: **2001** = move (`vx`, `vy`, `vyaw`),
  **2000** = failsafe (`clear_buffer`, `lock_drive`).
- `booster_msgs` must be built and sourced (`ros2_ws/src/booster_msgs`); if missing, the
  bridge logs a warning and silently disables K1 control (`HAS_BOOSTER_MSGS=False`).

## Conventions (from git_rules.md)

- Branches: `prefix/Name` — prefixes: `feature`, `tools`, `bugfix`, `refactor`, `docs`, `projects`.
  One coherent change per branch. Name in CamelCase, English, no umlauts.
- Code, comments, variables, commit messages: **English**. Team-internal docs/project work: German.
- AI prompts living in code: English. AI prompts used by the team: German.
- **[C3 inter-lingua] No meta-knowledge in model-facing text:** Anything fed to the
  LLM (fragments, transforms, scenario text) contains ONLY soccer/referee knowledge
  in dictionary vocabulary. Never mention ROS2K internals (JSON schema, PID, tmpfs,
  phantom kick, file paths, etc.). Every positional/negational verb carries explicit X,Y.
- **No hard-wired thresholds in code:** Distances, velocities, angles, timeouts must be
  named module constants at file top (e.g. `PRESSING_GAIN = 0.5`, not `if dist < 0.3:`).
  Prefer continuous/proportional functions over step thresholds where avoidable.
  Enables tuning without code archaeology and documents intent.

## Mermaid in docs

Renderer is brittle. Subgraph IDs: alphanumeric + underscores only, no brackets. Node strings
with special chars (`/`, `.`, parens) MUST be double-quoted. `[/.../]` shape syntax crashes the parser.
See `META_KNOWLEDGE_ROUTER.md` §3.

## Gotchas

- `launch_r2k.sh` wipes `shared_state/current_strategy.json` and `Worldstate.json` on every start.
- `setup_r2k.py` overwrites `ai_tactics/system_prompt.txt` on every boot.
  `strategy/strat_*.txt` are no longer written (Phase 0 disentanglement); edit `fragments/` instead.
  **[V6.3]** The evaluator no longer reads `system_prompt.txt` at runtime — it assembles
  the prompt directly from fragments via dynamic prompt injection, based on `match_state.status`.
  `system_prompt.txt` is now only for `dump_prompt.py` dry-runs.
- The `ros2_ws/build` and `ros2_ws/install` dirs are root-owned (created inside Docker) — may need
  `sudo rm -rf` to rebuild natively on U22.
- `numpy<2.0` is pinned (install.sh + Dockerfile) — Gazebo compatibility. Don't bump blindly.
- **Docker colcon rebuild (U24):** After editing files under `ros2_ws/src/`
  (world files, URDFs, msg definitions, `r2k_world_model`), the container must
  be running (`docker compose up -d`) before `docker exec ... colcon build`.
  If `colcon build` fails with `numpy/ndarrayobject.h: No such file or directory`,
  the cause is stale cached artifacts in `ros2_ws/build/` — NOT a missing numpy
  installation. Fix: `docker exec core_gazebo bash -c "cd /workspace/ros2_ws && rm -rf build install"`
  then re-run `colcon build`. Do NOT install `python3-numpy-dev`, set `CFLAGS`,
  or pass `--cmake-args -DNumPy_INCLUDE_DIR=...` — the rosidl CMake fallback
  (`execute_process` calling `python3 -c "import numpy; print(numpy.get_include())"`)
  resolves the path automatically on a clean build. The `docker compose up -d --build`
  flag rebuilds the Docker image (re-copies source) — unnecessary for code edits;
  use plain `docker compose up -d` then `docker exec ... colcon build` instead.
- `r2k_evaluator.py` polls `Worldstate.json` mtime every 20ms; it only POSTs to Ollama when the file
  changes. A stale `Worldstate.json` ⇒ no AI output. Check `state_aggregator.py` is running first.
  **[V6.3]** Content-hash skip: the evaluator also hashes `min_ents` and skips the LLM call if
  positions are unchanged. `current_strategy.json` may not update for seconds during stable
  positions — this is normal, not failure. Effective latency ~684ms (was ~1328ms).
  **[2026-08-01]** `temperature: 0.0` is NOT bit-exact deterministic across KV-cache states
  (measured): identical prompt+options can yield different token streams (e.g. pretty vs
  compact JSON, 118 vs 91 tokens) depending on cache history (fresh prefill vs cached prefix).
  Semantics stay stable, so content-hash skip remains safe; but A/B latency comparisons must
  control cache state (disturb with a different world before both sides, or compare
  steady-state calls).
- `temperature: 0.0` and `num_predict` (150 no-explain / 600 explain) are hardcoded in
  `r2k_evaluator.py` — tune there, not via flags. **[V6.3]** `R2K_EXPLAIN` env var
  (set by `launch_r2k.sh`) controls `{{EXPLAIN_INSTRUCTION}}` replacement in `header.txt`.

## Demo / Calibration Mode (v6.6)

Interactive bot calibration using the existing evaluator→bridge pipeline.
See `docs/calibration_cheat_sheet.md` for the full command reference.

### Launch
```
# Gazebo GUI, no matplotlib visualizer
./launch_r2k.sh --demo --no-visualizer --scenario 1vs0_waypoint --relay single_bot

# Interactive CLI (second terminal)
python3 tools/calib_cli.py
# Type "help" for numbered sample commands, type a number to send
```

### Architecture
- **3B executor** (per-cycle): reads "target" label → looks up coordinates → outputs Move(x,y)
- **7B compiler** (one-shot): reads NL task + world state + landmarks → outputs waypoint list
- **Evaluator**: tracks sequence (arrival detection), injects target label, detects task changes
- **Bridge**: unchanged (PID to x,y). Active brake on Hold (zero velocity, not skip)
- **Fast-path commands**: stop/resume/restart/go home — instant, bypass compiler

### Key files
- `strategy/fragments/rules_demo.txt` — executor system prompt (target→coords lookup)
- `strategy/fragments/rules_demo_core.txt` — clean non-soccer core (field bounds + Move/Hold)
- `shared_state/waypoints.json` — compiled waypoint list (written by 7B compiler)
- `shared_state/task_input.json` — interactive task input (written by calib_cli.py)
- `docs/calibration_cheat_sheet.md` — user-facing command reference with model capabilities
- `docs/v7/calibration_rotation_design.md` — v7 rotation/Face action design (Option D)

### Hardware
- `--relay single_bot` — Gazebo only
- `--relay hardware_mirror` — Yahboom + K1 (both mirror blue_1)
- Active brake works on all hardware types (Twist zeros / RPC 2001 zeros)

### Not yet available (v7)
- Rotation/Face commands (needs bridge Face action — design in `docs/v7/calibration_rotation_design.md`)
- Visual markers in Gazebo (needs colcon build for world file)
- Bot yaw in Worldstate (needs tracker change — v7 Task 3a)
- Relative movement "forward"/"turn left" (needs yaw)

## Session continuity protocol

**Before ending a session**, append an entry to `core/docs/SESSION_CHANGELOG.md`.
Use the stub generator to capture git facts, then fill in the narrative:

```bash
./docs/session_entry.sh    # generates a dated stub with git diff summary
```

Each entry must contain:
1. **Date + one-line goal** (what was this session for?)
2. **Done** — what was accomplished, with file:line evidence for verifiable claims
3. **Files touched** — list of paths modified/created
4. **Files deleted** — list of paths removed (if any)
5. **Not yet done** — deferred work and why
6. **Next** — the single next actionable step
7. **Blockers** — anything that would stop the next session

If the session did no meaningful work, do not append an entry.