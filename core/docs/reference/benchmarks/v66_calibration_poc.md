# v6.6 — Calibration Scenarios (POC Summary & Findings)

> [!warning] SUPERSEDED — 2026-08-19
> The weg queue, Face action, and direction-name schema described below
> were the original POC design. The **implemented** v6.6 uses a different
> architecture: sequence tracking + raw coordinates (no weg queue, no Face
> action). See:
> - `docs/calibration_cheat_sheet.md` — implemented command reference
> - `docs/LESSONS_LEARNED.md` §v6.6 — why weg/grid/time-index were rejected
> - `docs/plans/v68_pre_ifa/calibration_rotation_design.md` — Face action deferred to v7
> - `SESSION_CHANGELOG.md` 2026-08-19 entry — full implementation details
>
> This document is preserved as a historical record of the POC experiments
> (2026-08-17) that validated the NL→waypoint compilation approach.

> Date: 2026-08-17 · Session: planning + Ollama POC experiments
> Status: **design validated by prompt experiments** — implementation not yet started
> Branch plan: `feature/v6.6-calibration`

## 1. Goal

A new variant of ROS2K scenarios for **bot calibration and interactive showcases**:

- Human users enter tasks in **natural language** into a permanent system prompt
- The LLM solves the task and computes a **"Wegbeschreibung"** (route description) —
  an ordered waypoint sequence with timings, analogous to a Google Maps route
- The **ollama bridge** executes the sequence (re-using the relay mechanism),
  so robots move to computed positions at computed times
- Timing stems from the worldstate `sys_time`

Constraints from the team:

- **No soccer game, no opponent bots, no ball, no time pressure** — stable world
- **One bot at a time** only
- **No ROS 2 path/waypoint libraries** (no nav2 etc.) — the LLM does the path planning
- LLM ideally a 3B model running locally (POC: any model on the 5090;
  last-resort fallback: 235B cloud model)
- New `calib*.json` scenario files, soccer scenarios untouched

## 2. What we did

### 2.1 Module reuse analysis (read-only codebase review)

| Module | Reuse | Change |
|---|---|---|
| `tracker_node.py` | 100% | none (already publishes `sys_time` + positions) |
| `state_aggregator.py` | 100% | none (runs without referee/score → status `"playing"` fallback) |
| `relay/*.json` + `active_relay.json` | 100% | `only_sim_bots` (POC), `hardware_mirror` (K1) |
| `launch_r2k.sh` | ~90% | skip `referee_node`/`score_node` when `mode == calibration` |
| `setup_r2k.py` | ~90% | copy scenario `task` → `strategy/fragments/task_calibration.txt` |
| `r2k_evaluator.py` | ~70% | calibration fragment set, `weg` output schema, sys_time in user prompt, cache key `(status, mode, task_hash)` |
| `ollama_sandbox_bridge.py` | ~75% | **waypoint queue** for one bot, `Face` action, sys_time gating, `CALIB_LIN_X=0.4`; `assignments` path untouched → soccer zero-regression |
| `referee_node.py` / `score_node.py` | — | not started |

**Referee/status prompt injection (Q2):** the `_assemble_prompt(status, mode)`
mechanism (r2k_evaluator.py:282) is status-agnostic and re-usable. Without a
referee, status stays `"playing"` → only `rules_calibration.txt` +
`samples_calibration.txt` load. Soccer rules fragments must NOT be reused
(C3 rule: model-facing text contains only calibration vocabulary).

**ROS 2 actions (Q: "can we use ros2 action lists?"):** technically feasible
(rclpy ActionServer) and not a path-planning library — but the LLM path is
deliberately ROS-free (flat-JSON file polling), and actions don't exist over
micro-ROS (K1 stays RPC/flat-file). Decision: **flat-file `weg` in the bridge
for the POC**; optional ActionServer as a showcase facade in a later version
(shared queue-advance logic).

### 2.2 Prompt experiments on Ollama (2026-08-17)

Models tested: `glm-4.7-flash:latest`, `qwen2.5:3b`, `qwen2.5-coder:7b`,
`qwen2.5:7b` (pulled fresh, universal Instruct).

Test tasks:
- **Task A:** "blue_2 move forward by 1m, stop, after 2sec face west" (bot at (0,0), yaw north)
- **Task B:** "follow the Manhattan path from 0,0 to 4,2" (bot at (0,0), yaw east)

Prompt iterations (4 variants):

| Iteration | Change | Result |
|---|---|---|
| v1: raw rules, no samples | role + field + yaw + grid + speed + `weg` schema | glm ✅ schema, ❌ "forward"→east; qwen ❌ flattened schema (imitated INPUT) |
| v2: + `INPUT:`/`OUTPUT:` samples with timing | 3 examples (move/hold/face with t values, Manhattan, hold-wait) | schema ✅ both models; timing ✅ (travel-time math: 4m→10s, 2m→5s); qwen ❌ west yaw (-1.5708 = south), ❌ distance 0.414m |
| v3: Face by direction NAME | `"direction": "west"`, bridge converts name→yaw | west ✅ on qwen 3b; qwen-coder-7b ✅ everything; qwen 3b distance bug persists |
| v4: relative Move by rel+dist | `{"rel": "forward", "dist": 1.0}`, bridge computes target from yaw | **ALL models ✅ on both tasks** — see §3 |

**v4 schema (validated):**

```json
{"bot": "blue_2", "weg": [
  {"t": 1786893637.5, "action": "Move", "rel": "forward", "dist": 1.0},
  {"t": 1786893640.0, "action": "Hold"},
  {"t": 1786893642.0, "action": "Face", "direction": "west"}]}
```

- `Move`: absolute `{x, y}` OR relative `{rel: forward|backward|left|right, dist: <m>}`
- `Face`: direction names only (8-way: east, north, west, south, NE, NW, SE, SW)
- `Hold`: wait at current position until `t`
- `t` = absolute sys_time from the INPUT when the action STARTS, spaced by
  travel time of the previous action (SPEED 0.4 m/s → 1 m = 2.5 s)

Bridge execution semantics: `Move` advances on arrival (dist < 0.15 m) or
`sys_time >= t`; `Face` advances on yaw reached (< 0.1 rad); `Hold` waits until `t`.
Timing source: Worldstate.json `sys_time` (same tmpfs).

**Sample system prompt (Q3)** — see the POC scripts in `/tmp/opencode/`
(`calib_poc*.py`) for the full working prompt. Structure:

```
[HEADER] You are a calibration navigation planner. No soccer, no opponent, no ball.
         World is stable. Output ONLY raw JSON.
[RULES]  FIELD / BOT HEADING (yaw radians) / GRID / SPEED / TIME semantics /
         MOVES (absolute vs rel+dist) / FACE (direction names) / ACTIONS
### TASK (permanent, entered by the human)          <-- DYNAMIC: task_calibration.txt
{{TASK}}
[SAMPLES] 3x INPUT:/OUTPUT: with t-values
```
Dynamic user prompt per poll: `{"sys_time": ..., "blue_2": {"x": .., "y": .., "yaw": ..}}`.

## 3. What we learned

1. **`think: false` is mandatory for glm-4.7-flash** (top-level payload field,
   NOT inside `options` — there it is silently ignored). Without it the model
   burns the whole `num_predict` budget on its thinking preamble → empty
   `response`, `done_reason: length`. With it: 1.6-3.7 s latency.
2. **3B models imitate the INPUT structure** (qwen2.5:3b v1: flattened
   key-per-waypoint JSON instead of `weg` array). Fix: explicit
   `INPUT:`/`OUTPUT:` sample blocks — same lesson as the soccer
   `samples_3vs3.txt` pipeline (clean sample conversion with the
   `OUTPUT:`/`ASSISTANT:` marker regex).
3. **Samples teach timing math.** Without examples, models emitted `t = now`
   for all waypoints (glm) or 10 s for 1 m (qwen). With examples, both models
   computed travel time correctly (4 m → 10 s at 0.4 m/s).
4. **Small models are unreliable at trig, reliable at names:**
   - "forward by 1m" → glm moved east (ignored heading); qwen 3b computed
     y = 0.414214 (≈ tan 22.5°); "face west" → qwen 3b emitted yaw -1.5708 (south)
   - with **direction names** (`Face direction: "west"`) and **rel+dist moves**
     (`Move rel: "forward" dist: 1.0`), ALL models produce correct plans —
     the bridge (CPU) does the geometry
5. **Division of labor is the winning design:** LLM = semantics + planning
   (which sequence, which names, which timings); bridge = geometry + timing
   gates (yaw conversion, target computation, arrival detection). This mirrors
   the soccer C3 lesson (explicit coordinates for 3B) — but for *relative*
   geometry the bridge must compute, the LLM must not.
6. **Latency (5090, warm):** qwen2.5:3b 0.7-1.9 s, qwen2.5:7b 1.2-3.1 s,
   glm-4.7-flash 1.5-3.4 s (with think:false). All fine for calibration
   (no time pressure).
7. **qwen2.5-coder:7b worked, but the universal `qwen2.5:7b` is the right
   choice** (ADR-A01: coder corpus is 70% source code — soccer/calibration
   vocabulary out-of-distribution). 7b universal was pulled fresh (4.7 GB)
   and validated.
8. **Schema quirks handled by the existing `fast_parse`:** ```json markdown
   wrappers, `Face` entries carrying extra x/y — brace-match + ignore extras.

## 4. Suggestions to continue

### 4.1 Implementation (branch `feature/v6.6-calibration`)

1. **Fragments** (new files in `strategy/fragments/`):
   - `header_calibration.txt` (role + output-only-JSON)
   - `rules_calibration.txt` (field/heading/grid/speed/time/actions + rel+dist + direction names)
   - `samples_calibration.txt` (the 3 validated INPUT/OUTPUT examples, incl. timing)
   - task injected via `task_calibration.txt` (written by `setup_r2k.py` from the scenario `task` field)
2. **Scenarios:** `scenario/calib_grid.json` (task a), `scenario/calib_manhattan.json`
   (task b) — schema `{scenario_name, mode: "calibration", task, entities}`,
   **one blue bot, no ball, no red**
3. **Evaluator (`r2k_evaluator.py`):** mode `calibration` → new fragments;
   `weg_parse()` (validate t/x/y/rel/dist/direction); sys_time into user
   prompt; content-hash includes task; prompt cache key `(status, mode, task_hash)`
4. **Bridge (`ollama_sandbox_bridge.py`):** single waypoint queue + `Face`
   (ang_z-only PD) + rel/dist resolution + sys_time gating + `CALIB_LIN_X=0.4`;
   `assignments` path untouched (soccer zero-regression — verify with fast suite)
5. **`launch_r2k.sh`:** skip referee/score for `mode == calibration`
6. **Tests:** `tests/test_calibration.py` (weg_parse unit tests, queue-advance
   as pure functions, prompt assembly) + `tools/calib_verify.py`
   (waypoint order/timing from world_trace)
7. **POC run:** `./launch_r2k.sh --scenario calib_manhattan --relay only_sim_bots
   --headless --duration 60` → verify via `calib_verify.py`; then
   `--relay hardware_mirror` on the K1

### 4.2 Follow-ups

- **K1 on-bot 3B:** deferred — after the sim POC works end-to-end
  (hardware unknowns: compute, memory, arm64 build)
- **Interactive showcase CLI** (`tools/calib_task_cli.py`): rewrite the task
  file live + invalidate the prompt cache → visitors type tasks, bots execute
- **ROS 2 ActionServer facade** for the `weg` execution (goal/feedback/result)
  — optional, later, sim-only
- **8-way diagonals + `rel` "left"/"right"** already in schema, untested —
  add sample coverage if used
- **Timing edge case:** bridge is arrival-driven with `t` as start gate —
  confirm Hold semantics against real sim physics in the POC run

## 5. Session state

- Ollama server running on `127.0.0.1:11434` (started this session);
  models resident: `qwen2.5:3b` + `qwen2.5:7b` (+ glm-4.7-flash previously)
- `qwen2.5:7b` pulled (universal Instruct, 4.7 GB) — **do not delete**
- POC scripts in `/tmp/opencode/calib_poc{1..4}.py` (throwaway, /tmp only)
- No repository files changed during the POC (working tree clean except
  pre-existing state files)
- Session changelog entry pending at end of session (per continuity protocol)
