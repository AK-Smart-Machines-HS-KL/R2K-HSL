# GUI v6.7 POC — Requirements & Design Decisions

**Date:** 2026-08-27
**Status:** Accepted (for POC implementation)
**Scope:** Simulation pillar only. Deployment and Core pillars deferred.
**Relation to existing docs:** Extends `gui_v67_discussion.md` (roles, workflows,
mockups) with concrete architecture decisions. Supersedes the `ws_backend.py`-based
first-shot GUI. Does NOT change the ROS2K runtime architecture (axioms 1–10 hold).

---

## 1. Lessons from the First Shot (ws_backend.py GUI)

The first GUI iteration (`ws_backend.py` + `gui/index.html`, August 2026) exposed
systemic fragilities that this POC must not repeat. All issues below were observed
live during testing on the U24 Docker machine.

### 1.1 Process Management via pkill Pattern Matching

**Symptom:** `/done` sometimes failed to kill all processes; `gzserver` survived
as a zombie, keeping GPU at 85%. Re-launching started a second `gzserver` that
fought the first for the Gazebo transport port (11345).

**Root cause:** `ws_backend.py` used `pkill -f "gzserver"` to tear down processes.
Pattern matching is racy: `pkill` can miss processes whose command line has changed
(e.g. `gzserver --verbose -s libgazebo_ros_init.so ...`), can kill unintended
targets (e.g. `pkill -f "r2k_world_model"` also kills `r2k_world_model_tracker`),
and provides no confirmation that the process actually died before the 2s sleep
expires.

**Design consequence:** The supervisor MUST track child processes by PID
(`asyncio.subprocess.Process`), not by name pattern. `stop()` sends SIGTERM to a
specific PID, waits, then SIGKILL. No `pkill` anywhere.

### 1.2 Stale State Across Layers

**Symptom:** Selecting scenario `3vs3_default` and launching produced a `2vs2`
match. The 2D widget showed 3vs3 (7 entities from Worldstate.json) but the 3D
GZWeb scene was frozen on the previous 2vs2 frame.

**Root cause (multiple):**
- `active_scenario.json` was not cleaned on launch failure — a failed
  `setup_r2k.py` left the previous match's scenario active, and `gzserver`
  spawned the old bots.
- `loadCatalog()` hardcoded `2vs2_default` as the `selected` option. Every
  page reload reset the dropdown to 2vs2, overriding the user's selection.
- `location.reload()` (added as a workaround to reset JS globals) re-ran
  `loadCatalog()`, flipping the dropdown back to 2vs2.
- The GZWeb iframe kept a stale WebSocket to the old `gzbridge` instance.
  The iframe didn't reload when gzbridge restarted.

**Design consequence:**
- No `location.reload()`. State resets happen through the reactive store, not
  page reloads.
- No hardcoded defaults in `loadCatalog()`. The last selection persists in
  `localStorage`.
- `active_scenario.json` is cleaned before every launch attempt, validated
  against disk before `setup_r2k.py` runs.
- GZWeb iframe is force-reloaded on launch success (delayed, to give gzbridge
  time to start).

### 1.3 Global Variable Fragility

**Symptom:** `/done` returned `{"status":"error","detail":"name '_current_model' is not defined"}`.
The match kept running; GPU stayed at 85%.

**Root cause:** The `_current_model` global was added to track the model name for
Ollama VRAM unload. During iterative edits to `ws_backend.py`, the module-level
declaration was lost — the `global` statement in `handle_done` referenced an
undefined name, raising `NameError`. Python's global-by-convention makes this
class of bug easy to introduce and hard to catch at review.

**Design consequence:** State lives in a typed `SupervisorState` dataclass, not
in bare module globals. The state machine transitions are atomic (asyncio.Lock).
No bare `global` statements.

### 1.4 Ollama Model Not Unloaded

**Symptom:** After `/done`, `nvidia-smi` showed `ollama` still holding 5050 MiB
VRAM. GPU-Util stayed at 34%.

**Root cause:** The evaluator sets `keep_alive: "30m"` on every Ollama call.
The model stays resident for 30 minutes after the last call. `/done` killed
processes but never sent `keep_alive: 0` to unload the model. Additionally, the
unload targeted the wrong host (`172.17.0.1` instead of `127.0.0.1` — the
container uses `network_mode: host`).

**Design consequence:** `/done` MUST unload ALL loaded Ollama models (queried
via `/api/ps`) with `keep_alive: 0`. The health check queries `/api/ps` to
report VRAM usage.

### 1.5 GZWeb gzbridge Consuming GPU

**Symptom:** Even after killing `gzserver` and unloading the Ollama model,
GPU-Util stayed at 36% and power at 16W.

**Root cause:** `node ./server.js 8080` (the GZWeb gzbridge) was not killed by
`/done`. It polled the dead `gzserver` at high frequency, consuming 199% CPU
and keeping the GPU's display pipeline busy.

**Design consequence:** `/done` MUST kill `server.js 8080` alongside `gzserver`.
The process manager tracks `server.js` as a managed child.

### 1.6 Browser Caching

**Symptom:** After editing `index.html`, the browser served the old version.
`handle_static` didn't set cache-control headers.

**Design consequence:** All static file responses include
`Cache-Control: no-cache, no-store, must-revalidate`.

---

## 2. Architecture Constraints (Non-Negotiable)

### 2.1 ROS2K Runtime Architecture is Untouched

The GUI POC is a **monitor and launcher** — it does not modify the ROS2K
runtime architecture. All axioms from `agent_prompt_de.txt` hold:

| Axiom | GUI consequence |
|-------|-----------------|
| 1. No OOP HALs | GUI doesn't touch the bridge |
| 2. Absolute ground truth from `/gazebo/model_states` | GUI reads `Worldstate.json`, never raw ROS topics |
| 3. Decoupled concurrency via tmpfs file polling | GUI rides the file bus (`Worldstate.json`, `current_strategy.json`) — no ROS in the browser |
| 4. `ROS_DOMAIN_ID=0`, `rmw_fastrtps_cpp` | GUI inherits this; no override |
| 5. Ollama at `0.0.0.0:11434` | GUI health check uses `127.0.0.1:11434` (host network mode) |
| 6. Hybrid OS (U22 native, U24 Docker) | GUI runs inside the `r2k_gzweb` Docker container on U24 |
| 7. Hardware-first teardown (0.2s watchdog, kinematic freeze) | GUI NEVER bypasses teardown. `/done` calls the same teardown sequence. The watchdog in `launch_gzweb.sh` remains authoritative. |
| 8. Suspend bug (Xid 31) — not a Python issue | GUI health panel shows GPU state; doesn't try to fix it |
| 9. Strict nomenclature | GUI uses correct file/topic names from the knowledge base |
| 10. Zero tolerance for deviations | — |

### 2.2 POC Status

This GUI is a **proof of concept only**. It is NOT the production system.
Constraints:
- **No changes to `launch_r2k.sh`** — the production launcher is untouched.
- **No changes to ROS2 node code** — `referee_node.py`, `score_node.py`,
  `state_aggregator.py`, `r2k_evaluator.py`, `ollama_sandbox_bridge.py`,
  `rule_evaluator_red.py`, `r2k_visualizer.py` are all untouched.
- **No changes to `setup_r2k.py`** — the prompt compiler runs as-is.
- **The `launch_gzweb.sh` script** gets one line changed (which backend to start).
  The watchdog, teardown, and Ollama check logic stay identical.
- **Re-use:** Widgets proven in this POC MAY be re-used in the production system
  later. The reactive store, canvas renderer, and system tree are designed to be
  portable. But that decision is deferred — for now, everything is POC.

### 2.3 Docker Container

The supervisor runs inside the `r2k_gzweb` container (`docker-compose.gzweb.yml`).
- `network_mode: host` — all ports (8765, 8080, 11434) are directly reachable.
- `./:/workspace:rw` volume mount — the supervisor reads/writes the same files
  as the ROS2 nodes.
- No new Docker dependencies. The `Dockerfile.gzweb` already has
  `aiohttp`, `aiofiles` installed.

---

## 3. Architecture: r2k_supervisor.py

### 3.1 Single Process, PID-Tracked Children

```
r2k_supervisor.py  (single asyncio process, port 8765)
├── HTTP + WebSocket server  (aiohttp)
├── Process Manager          (asyncio.subprocess, PID-tracked)
├── State Machine            (IDLE → LAUNCHING → RUNNING → TEARING_DOWN)
├── Health Monitor            (periodic subsystem checks)
└── File Bus Watcher          (mtime poll on Worldstate.json + current_strategy.json)
```

Replaces `ws_backend.py` entirely. `ws_backend.py` stays on disk as fallback
but is not launched.

### 3.2 Process Manager

Every child process spawned by the supervisor is tracked as an
`asyncio.subprocess.Process` with its PID. No `pkill`, no `setsid`.

Key design rules (see implementation plan §2.1 for full code):
- **Inherits parent environment:** `env=os.environ.copy()` + override vars.
  An empty `env={}` would strip PATH, HOME, ROS_DOMAIN_ID and break
  `source /opt/ros/humble/setup.bash` in the command string.
- **Per-child log files:** stdout/stderr piped to `/tmp/supervisor_<name>.log`.
  `DEVNULL` was a mistake from the first-shot GUI — silent crashes were
  invisible.
- **SIGTERM → wait → SIGKILL:** `stop()` sends SIGTERM to the specific PID,
  polls `is_alive()` every 100ms, escalates to SIGKILL after `timeout`
  seconds. No pattern matching.

### 3.3 State Machine

```
IDLE ──/launch──→ LAUNCHING ──(spawn OK)──→ RUNNING
                     │                           │
                     │ (spawn fail)              │ /done
                     ↓                           ↓
                   IDLE                       TEARING_DOWN ──→ IDLE
```

- Transitions are guarded by `asyncio.Lock` — only one at a time.
- `/launch` returns 409 if state != IDLE. No "force reset" hack.
- `/done` returns 409 if state != RUNNING.
- State changes pushed to all WS clients immediately.
- `/done` uses `asyncio.create_subprocess_exec` (non-blocking) for Ollama
  unload — `subprocess.run` would freeze the event loop for 8s per model.

### 3.4 Health Monitor

Checks every 2–5 seconds (per-subsystem interval), pushes changes via WebSocket.
All checks run **concurrently** via `asyncio.gather()` with per-check timeouts
(2s). If a check hangs (e.g., Ollama timeout, `nvidia-smi` stall), it returns
`{"status":"timeout"}` instead of stalling the loop.

| Subsystem | Check method | Timeout | Interval |
|-----------|-------------|---------|----------|
| Ollama | `GET 127.0.0.1:11434/api/ps` → loaded models + VRAM | 2s | 2s |
| Docker container | `docker ps --filter name=r2k_gzweb` | 2s | 5s |
| gzserver | `proc.is_alive()` (managed child) | instant | 2s |
| ROS2 nodes | `proc.is_alive()` per managed child | instant | 2s |
| GPU | `nvidia-smi --query-gpu=...` | 2s | 5s |
| File bus | `os.path.getmtime(Worldstate.json)` < 2s ago | instant | 1s |

Health data is pushed to the frontend as a structured JSON object. The
frontend renders it as a health card grid on the homepage.

### 3.5 Endpoints (Core Scope)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Static files (index.html, style.css, app.js) with no-cache headers |
| GET | `/catalog` | Scenarios + mode-grouped strategies + models from disk |
| GET | `/state` | Current state machine phase + match state snapshot |
| GET | `/health` | All subsystem health statuses |
| GET | `/launch` | Start a match (scenario, strategy, model, explain, duration) |
| GET | `/done` | Stop match + unload Ollama models + kill gzbridge |
| GET | `/runs` | List recent runs from `logs/` directory (parses `world_trace_*.jsonl` filenames for run_id, extracts scenario + strategy + timestamp; optionally reads last line for final score) |
| GET | `/git/commits` | `git log --oneline -10` |
| GET | `/session/digest` | Last 5 lines of `SESSION_CHANGELOG.md` |
| GET | `/reboot/check` | Check all subsystems, return alive/dead per subsystem |
| GET | `/reboot/bringup/<subsystem>` | One-click bring-up of a dead subsystem |
| WS | `/ws` | Push Worldstate.json + current_strategy.json + health updates |

### 3.6 Launch Flow (replaces ws_backend.py handle_launch)

1. **Validate** scenario exists on disk. Return 400 if not. No state mutation
   until validation passes.
2. **Acquire state lock.** Return 409 if not IDLE.
3. **Teardown** any existing managed children (SIGTERM → wait → SIGKILL, per PID).
4. **Clean state files:** `Worldstate.json`, `current_strategy.json`,
   `active_scenario.json`, `active_relay.json`, `system_prompt.txt`,
   `waypoints.json`, `task_input.json`.
5. **Run `setup_r2k.py`** as a foreground subprocess (15s timeout). If it fails,
   return 500 and transition back to IDLE.
6. **Start `gzserver`** as a managed child (headless, via `ros2 launch`).
   **Poll for readiness** (up to 15s): check for gzserver process via
   `pgrep -f gzserver` or a ROS2 service. Do NOT use a hardcoded `sleep(6)` —
   on a loaded system (Ollama cold-start, GPU throttled) gzserver may need
   10s+. If not ready after 15s, return 500 and transition back to IDLE.
7. **Spawn bots** via `json_spawner.py` (foreground, 20s timeout).
8. **Start `gzbridge`** (`server.js 8080`) as a managed child.
9. **Start ROS2 nodes** as managed children: tracker, referee, score, reward,
   rule_evaluator_red, state_aggregator. Each child inherits the parent
   environment (`os.environ.copy()`) so ROS_DOMAIN_ID, PATH, and sourced
   setup.bash vars propagate correctly. See implementation plan §2.1.
10. **Start bridge + evaluator** as managed children with env vars
    (`R2K_RUN_ID`, `R2K_OLLAMA_MODEL`, `R2K_EXPLAIN`, etc.) merged on top of
    the inherited parent environment.
11. **Transition to RUNNING.** Push state change via WS.
12. **Auto-terminate** if duration set (asyncio task that calls `/done` logic
    after N seconds).

### 3.7 Done Flow (replaces ws_backend.py handle_done)

1. **Acquire state lock.** Return 409 if not RUNNING.
2. **Transition to TEARING_DOWN.**
3. **Stop all managed children** (SIGTERM → 3s → SIGKILL, per PID). This includes
   `server.js`, `gzserver`, all ROS2 nodes, evaluator, bridge.
4. **Unload Ollama models.** Query `/api/ps`, send `keep_alive: 0` for each
   loaded model. Target: `127.0.0.1:11434` (host network mode).
5. **Transition to IDLE.** Push state change via WS.

---

## 4. Frontend: Reactive Store + Layout

### 4.1 File Structure

| File | Lines (est.) | Purpose |
|------|-------------|---------|
| `tools/gui/index.html` | ~120 | HTML structure only. Links to `style.css` + `app.js`. |
| `tools/gui/style.css` | ~250 | All styles, extracted from old `index.html` + new styles. |
| `tools/gui/app.js` | ~500 | Reactive store + WS handler + canvas renderers + UI controllers. |

### 4.2 Reactive Store

No `location.reload()`. No bare globals. All state in a single store object
with subscribe/notify. The store holds: supervisor state, world, strategy,
momentum, match events, health, catalog, commits, runs, session digest, and
active workflow. Subscriptions fire on `set()` — UI components re-render
automatically. Selections (scenario/strategy/model) persist in `localStorage`.

See implementation plan §3.2 for the store implementation.

### 4.3 Layout

```
┌─ Top Bar (44px) ──────────────────────────────────────────────────┐
│  ROS2K  [status]  [score blue:red]  [possession]  [GPU:38°C]  DONE │
├──────────┬──────────────────────────────────────────────────────┤
│ Sidebar  │  Content Area                                        │
│ (240px)  │                                                      │
│          │  Workflow Bar (title + description)                   │
│ Home     │  ┌────────────────────────────────────────────────┐  │
│ ▼ Play   │  │                                                │  │
│   Game   │  │           Dock / Text Pane                      │  │
│   Demo   │  │     (varies by active workflow)                  │  │
│   Replay │  │                                                │  │
│ ▼ Build  │  │                                                │  │
│   ...    │  │                                                │  │
│ ▼ Analyze│  │                                                │  │
│   ...    │  │                                                │  │
│ ▼ Know   │  │                                                │  │
│   ...    │  └────────────────────────────────────────────────┘  │
│ ───────  │                                                      │
│ ● WS     │  Selector Bar (scenario/strategy/model/launch)        │
│ ● GZWeb  │  (visible only in Play workflows)                     │
│ ● Ollama │                                                      │
└──────────┴──────────────────────────────────────────────────────┘
```

### 4.4 Homepage (Dashboard)

Shown when `activeWorkflow === 'home'`. Four quadrants:

| Quadrant | Content | Data source |
|----------|---------|-------------|
| Top-left | Recent commits (last 10) | `GET /git/commits` |
| Top-right | System health (6 subsystem cards) | `GET /health` (WS push) |
| Bottom-left | Recent runs (last 5, from `logs/`) | `GET /runs` |
| Bottom-right | Quick launch (preset buttons) | `GET /catalog` + click → `/launch` |

Below quadrants: session digest (last 5 lines of `SESSION_CHANGELOG.md`).

Dead subsystem cards show the status icon only in the core build. One-click
bring-up buttons (`[▶ Start]`) are deferred to v7 — the core build shows a gray
"bringup: follow-up" label for dead subsystems.

### 4.5 Play Game Layout (live match)

Same dock grid as the current GUI, but driven by the reactive store:

| Zone | Grid position | Widget | Data |
|------|--------------|--------|------|
| 3D Scene | col 1, row 1 | GZWeb iframe | `http://localhost:8080` |
| 2D World Model | col 1, row 2 | Canvas (pitch, bots, ball, intent arrows) | `Store.world` |
| LLM Stream | col 2, row 1 | Text panel (assignments, latency, model) | `Store.strategy` |
| Referee Events | col 2, row 2 | Text panel (event log) | `Store.matchEvents` |
| Momentum | col 1-2, row 3 | Canvas (score timeline) | `Store.momentum` |

GZWeb iframe: force-reloaded on launch success (3s delay for gzbridge startup).

### 4.6 Scenario-Strategy Coupling

`/catalog` returns:
```json
{
  "scenarios": [
    {"name": "3vs3_default", "mode": "3vs3", "bots": 7, "label": "default"}
  ],
  "modes": {
    "3vs3": {"strategies": ["strat_aggro"]},
    "2vs2": {"strategies": ["strat_aggro"]}
  },
  "models": ["qwen2.5:3b", "qwen2.5:7b"]
}
```

Frontend: scenario select → filter strategy dropdown to `modes[mode].strategies`.
Last selection persisted in `localStorage` (key: `r2k_sel`). No hardcoded defaults.

### 4.7 Canvas Renderers

The 2D world model canvas and momentum chart are reused from the existing
`index.html` with minimal changes — they already work well. The only change
is that they read from `Store.world` / `Store.momentum` instead of bare globals,
and they subscribe to store updates instead of being called imperatively.

---

## 5. Design Decisions (Locked)

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| A | 3D Scene | Keep GZWeb | PoC passed (N4). Fix iframe reload. |
| B | Supervisor | New file `r2k_supervisor.py` | Clean start. `ws_backend.py` stays as fallback. |
| C | Frontend | Vanilla JS + reactive store, 3 files | No build step. Matches ROS2K flat-file philosophy. |
| D | Build sequence | Clean build, no patches | Avoids transitional state. `ws_backend.py` bugs are structural. |
| E | opencode | Direct Ollama, opencode later | Assistant uses `qwen2.5:7b` + META-ROUTER. opencode integration deferred. |
| 1 | System Tree | Sidebar dots + detail panel (follow-up) | Compact liveness dots always visible; click → full panel. |
| 2 | AI Navigation | Toasts + highlighting + assistant (follow-up) | Toasts for alerts, highlighting for guidance, assistant for dialogue. |
| 3 | Reboot | One-click bring-up | `GET /reboot/bringup/<subsystem>` runs the right command. |
| 4 | Ruleset | KISS — minimal scope | Don't build features the ruleset/workflow doesn't need. |
| 5 | Assistant | META-ROUTER (follow-up) | One assistant, router-based. No per-submodule prompts. |
| 6 | Homepage | Approved | Commits + health + runs + quick launch + digest. |
| JS | File split | 3 files | index.html + style.css + app.js. |
| Scope | Build size | Core first, features later | Supervisor + reactive frontend + homepage + health now. System tree, toasts, assistant later. |

---

## 6. Follow-Up Scope (Not in Core Build)

These features are designed for but NOT implemented in the core build:

- **System Tree** — sidebar liveness dots per ROS2 node, click → detail panel
  (PID, uptime, topics, log tail, last event)
- **Toast Notifications** — bottom-right popups for system alerts (referee died,
  model loaded, GPU throttled)
- **Button Highlighting** — pulsing border on sidebar items when the assistant
  detects something worth looking at
- **Assistant Panel** — chat UI in rightmost zone, calls `qwen2.5:7b` with
  META-ROUTER system prompt
- **SSE Event Stream** — `GET /events` for external consumers (opencode later)
- **Reboot Bring-Up Buttons** — one-click `GET /reboot/bringup/<subsystem>`
  per dead health card
- **Replay View** — `GET /runs/<run_id>` returns merged trace, frontend renders
  2D replay with timeline scrubber
- **Probe Browser** — text-probe results table (from `probe_*.py`)
- **KPI Dashboard** — traffic lights from `analyze_trace.py` output
- **Prompt Viewer** — fragment bands per status, token counts

### 6.1 AI Integration Modes — To Be Discussed

The assistant panel (follow-up scope) implies three integration modes with
distinct technical requirements. These are proposed for discussion, not yet
committed:

**Mode A — Supervisor (passive monitoring)**

The AI watches the system continuously and raises alerts without being asked.
Renders as toast notifications + button highlighting (the already-decided
follow-up features). Lightweight: threshold checks, rate-of-change, absence
detection — run locally, no LLM call needed for the check itself. The LLM
is only invoked to generate the human-readable alert text.

Technical requirement: SSE event stream (follow-up) + a local rule engine
(~50 lines, no LLM). The LLM call for alert text is optional — pre-written
templates suffice.

**Mode B — Copilot (interactive dialogue)**

The user asks questions in the assistant panel. The AI answers using the
META-ROUTER to find relevant knowledge, plus live system context (current
Worldstate, last LLM trace record, active workflow).

Technical requirement: Assistant panel (follow-up) + Ollama dialogue
(`qwen2.5:7b` + META-ROUTER system prompt, already designed in the
requirements). Context injection: the supervisor attaches the current
Worldstate summary, last trace record, and active workflow name to each
query.

**Mode C — Analyst (offline mining)**

After a match or across many matches, the AI mines trace data for patterns
the user wouldn't find manually. Reads full `llm_trace` + `world_trace`
files, runs `analyze_trace.py`, performs regression analysis across commits.
Renders as written analysis in the assistant panel or a dedicated analysis
view.

Technical requirement: New — not in the current follow-up scope. Needs:
(1) a subprocess task runner in the supervisor (run `analyze_trace.py` +
custom mining scripts), (2) structured output parsing, (3) a results
rendering view. The LLM (qwen2.5:7b) formats raw analysis output into
human-readable text. This is the heaviest mode and may require a larger
model or longer generation timeout.

Discussion points:
- Is Mode A's local rule engine sufficient, or should every alert go through
  the LLM? (Local is faster; LLM is more flexible.)
- For Mode B, should the context injection include the full last prompt
  assembly (fragments + samples) or just the hash + assignment summary?
  (Full prompt = better answers but ~3k tokens per query.)
- For Mode C, should the mining run on demand (user clicks "Analyze this
  match") or automatically after every match? (On-demand is cheaper;
  automatic is more useful but burns GPU after every DONE.)

---

## 7. v7 Use Cases (Future — To Be Discussed)

These use cases extend the GUI beyond the v6.7 POC. They are documented here
to ensure the architecture doesn't preclude them, but they are NOT in scope
for the current build. Each is marked with the AI integration mode (A/B/C)
it implies.

### UC11 — Improve the system prompt by watching failures (LLM Designer) [v7]

**Task:** During a match, the LLM produces a bad decision. The designer wants
to see which fragment drove it, which sample matched, and what the alternative
would be. Then edit the fragment with probe coupling (text probe auto-runs
on save).

**Data:** `llm_trace` (raw prompt + response) + `current_strategy.json`
(assignments) + `Worldstate.json` (ball delta before/after) + fragment files.

**Why the GUI helps:** The XAI panel shows the full prompt assembly with
color-coded fragment bands. The AI assistant (Mode C) mines recurring failure
modes across runs: "7/10 goals against blue came from left-wing attacks —
`rules_3vs3.txt` has no left-wing defensive sample." It proposes specific
fragment additions with draft text. The designer edits, the text probe runs
automatically (UC13), and if the probe passes, the designer launches a live
match to verify.

**AI mode:** C (Analyst) for pattern mining + B (Copilot) for draft text.

### UC12 — Evaluate a candidate LLM model (Experimentation, QA) [v7]

**Task:** A new small model is available. Run the same 5 scenarios with both
the current and candidate model, compare KPIs, declare a winner.

**Data:** `/catalog` (model list) + `/launch` (per-model runs) +
`analyze_trace.py` KPIs + `kpi_targets.json` thresholds.

**Why the GUI helps:** The A/B benchmark runner (C4) configures two arms,
picks scenarios, launches 10 matches. The KPI merge table shows side-by-side
composite scores. The AI assistant (Mode B) summarizes: "qwen3-coder:4b won
4/5 scenarios. Exception: `3vs3_pressing_trap` — it over-committed and
conceded 2 counter-goals. Latency p50: 712ms (54ms slower)." It also checks
for regressions ("new model never passes to blue_3 — kicker identity samples
may need updating for this model's tokenization").

**AI mode:** B (Copilot) for summary + C (Analyst) for regression detection.

### UC13 — Probe a prompt variant in seconds (LLM Designer) [v7]

**Task:** Edit a fragment, immediately see whether the text probe passes or
fails — no Gazebo, no 120s match.

**Data:** `strategy/fragments/*` (editable) + `probe_*.py` corpus +
predicate results.

**Why the GUI helps:** The Probe panel has a fragment editor on the left
and a probe results table on the right. On save, the supervisor runs the
text probe as a foreground task (~5s). Results: "goalie_kick_own_half: 18/20
PASS, defending_deep: 9/15 FAIL." Iterate at ~10s per cycle. The AI assistant
(Mode B) detects tension between predicates: "Each edit improved
goalie_kick_own_half but degraded pass_teammate_open by 5% — the two are in
tension. Consider splitting the sample by field position."

**AI mode:** B (Copilot) for tension detection + draft sample rewrite.

### UC14 — Benchmark: which fragment actually helped? (QA, Experimentation) [v7]

**Task:** Over months, 8+ fragment changes were committed. Which ones improved
match outcomes? Which bridge improvements helped? Separate prompt
contributions from bridge contributions.

**Data:** `git log` + `logs/world_trace_*.jsonl` + `logs/llm_trace_*.jsonl` +
`kpi_targets.json` (threshold history v63/v65/v67) + `score_node.py`
constants (score function version history).

**Why the GUI helps:** A timeline chart shows composite score per run with
commit markers. The AI assistant (Mode C) performs attribution analysis:
"After commit 67a12a0 (goalie-kick prompt), goalie_tactical_pct jumped 78% →
96%. After 536dc9f (aim-aware kick), shots_on_target +40%. But 8099872 (S1
probes) → composite dropped 0.05 — probe-validated variant didn't survive
live matches." It separates prompt effects from bridge effects ("the PD gain
boost 2ac2a71 improved cluster_pct by 8% — this is a bridge improvement, not
a prompt improvement").

**AI mode:** C (Analyst) — regression across commit history × KPI deltas.

### UC15 — Extend the world model systematically (Experimentation, Admin) [v7]

**Task:** Add a new data source (bot yaw, second camera, K1 image recognition).
Know what breaks, what fragments need updating, what KPIs change meaning.

**Data:** `state_aggregator.py` (schema) + `Worldstate.json` (current schema) +
`tracker_node.py` (perception) + fragment files + `analyze_trace.py` (KPI
dependencies).

**Why the GUI helps:** The system tree shows the world model as a schema
diagram: entities → fields → consumers. Adding `yaw` highlights all downstream
consumers. The AI assistant (Mode B) lists: "(1) tracker — extract yaw from
quaternion (already computed, not published), (2) aggregator — add to JSON,
(3) evaluator — no change (yaw not in prompt today), (4) analyze_trace — new
KPI `avg_bot_orientation_stability` possible. Fragment impact: `rules_demo.txt`
could use yaw for Face command. No breaking changes."

**AI mode:** B (Copilot) for dependency graph analysis + draft code.

### UC16 — Eye-in-the-sky calibration (Support, Experimentation) [v7]

**Task:** Calibrate a physical bot's position using an overhead camera. The
camera sees the bot at (3.2, 1.1) but odometry says (3.0, 1.0). Measure and
correct the discrepancy.

**Data:** Camera feed (MJPEG) + `Worldstate.json` (sim position) + relay
profile (hardware mapping) + calibration offset table.

**Why the GUI helps:** The 2D canvas shows sim position (solid circle) and
camera-detected position (hollow circle with crosshair). The discrepancy is
a red line. The calibration panel: "blue_1: sim (3.0, 1.0), camera (3.2, 1.1),
Δ=(+0.2, +0.1), [Apply]?" The AI assistant (Mode A) monitors drift
continuously: "blue_1 drifted +0.15m over 5 minutes — wheel slip likely."
It detects systematic offsets: "all bots show +0.2m X-offset — camera mount
is off-center. Correct the camera, not the bots."

**AI mode:** A (Supervisor) for continuous drift monitoring.

### UC17 — Video recording review (QA, Experimentation, Admin) [v7]

**Task:** Review a video recording alongside trace data. Sync video timeline
with world_trace timeline to see what the camera saw vs what the world model
recorded at each moment.

**Data:** Video file (MP4) + `world_trace_*.jsonl` + `llm_trace_*.jsonl` +
annotations.

**Why the GUI helps:** The replay view adds a video panel above the 2D
canvas. A sync timeline aligns video timestamps with trace timestamps.
Scrub to t=42s: video shows the bot missing the ball, 2D canvas shows the
kick command, LLM stream shows the prompt that produced it. The AI assistant
(Mode C) performs video-to-trace alignment and detects anomalies: "At t=42s,
video shows contact but world_trace shows no ball velocity change for 0.3s —
phantom kick delay or physics step mismatch." It generates highlight clips.

**AI mode:** C (Analyst) for alignment + anomaly detection.

### 7.1 Additional v7 Use Cases — To Be Discussed

These candidates were raised during the team workshop and design discussion
but are not yet detailed use cases. Listed for future elaboration:

- **TeamCaptain integration** — the v7 CPU planner (ADR-A07) runs at 10Hz
  beside the LLM at 1.5Hz. The GUI must show two decision levels: who has
  control right now? When does the TeamCaptain override the LLM? (EDGE
  section in `gui_v67_discussion.md`.)
- **Robot-to-robot communication** — if bots exchange messages, the GUI needs
  a message stream view. (EDGE section.)
- **STT voice input for demo mode** — voice commands as a demo input channel.
  (EDGE section.)
- **K1 image recognition** — world model becomes multi-source. The view must
  mix Gazebo ground truth with camera-detected positions. (EDGE section.)
- **Scalability ("automatischer Wilhelm")** — new projects attached to the
  dashboard with minimal configuration. Implies a project registry and
  per-project scenario/relay/fragment directories. (Workshop note.)
- **Reboot management** — one-click bring-up of dead subsystems after an OS
  reboot. (Workshop note — partially covered in core build health panel, but
  the full bring-up automation is v7 scope.)