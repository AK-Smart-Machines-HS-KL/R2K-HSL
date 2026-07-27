---
title: "Workshop Preparation Memo (Internal)"
type: MEMO
tags: [workshop, memo, internal, v6.2, planning]
last_modified: 2026-07-22
status: draft
---

# Workshop Preparation Memo

> [!warning] Internal
> This memo is a detailed task list for the opencode session that produces the
> workshop deliverables. Not team-facing. See `workshop_invitation.md` for the
> team-facing 1-page summary. See `workshop_lecturer_guide.md` for the
> lecturer's material (timing, talking points, answers).

## 1. Open decisions (resolve before producing deliverables)

### Decision A: Deliverable format
- **Option 1 (recommended):** Single German Markdown handout in
  `core/docs/workshop_handout_v6.2.md`. All 5 modules, concept summaries,
  comparison tables, K1 anti-patterns, copy-pasteable experiment commands
  with offline fallbacks. References the existing `cheatpage_r2k_team_workflow.md`
  for setup details (avoids duplication).
- **Option 2:** Handout + ready-to-run `experiments/workshop/` folder with
  one shell script per module.
- **Option 3:** Slides (Mermaid + bullet slides in Markdown) + separate
  hands-on experiment sheet.

### Decision B: Module 5 depth
- **Option 1 (recommended):** Conceptual walkthrough of Phase 5 research
  directions from `optimization_spec_v6.2.md` + one hands-on spike: run
  `3vs3_attack_center` with `--explain`, compare LLM reasoning against
  `analysis.md` oracle/expert.
- **Option 2:** Also demo a parameter tweak (e.g. change a referee threshold
  constant, run a match, observe KPI impact via `analyze_trace.py`). Shows
  the trial-and-error workflow live.
- **Option 3:** Also use `opencode` to explore the codebase live — ask
  opencode to explain a component, edit a fragment, run a match.

## 2. Pre-workshop preparation (REQUIRED before the day)

### 2.1 Verify Ollama + Gazebo
- Run one 60s headless match before the workshop day to confirm the full
  stack works end-to-end:
  ```bash
  cd ~/R2K-HSL/core
  ./launch_r2k.sh --headless --duration 60 --scenario 2vs2_default --relay only_sim_bots
  ```
- Verify Ollama is on GPU: `nvidia-smi` should show an ollama process
  using ~2-4GB VRAM. If not, see `5_HYBRID_INFRASTRUCTURE_V5.md` Xid 31 section.
- If Ollama unreachable: all experiments fall back to offline mode (replay
  checked-in traces, `dump_prompt.py`, reading saved KPI JSONs, `pytest`
  with patched constants).

### 2.1a Warm up Ollama BEFORE the first match (cold-boot race fix)

> [!warning] The first match after `ollama serve` starts will have a 30-40s
> delay before the model is resident in VRAM. If the user closes the window
> or presses CTRL+C during this window, the model load aborts (HTTP 499)
> and blue team stays dead for the entire match. This has been observed in
> the wild (2026-07-23 session: dead blue team on first `--no-explain`,
> worked on second launch because model was warm).

**Timeline (measured 2026-07-23, RTX 5090 Laptop, qwen2.5-coder:3b):**

| Elapsed | Event | Evidence |
|---------|-------|----------|
| 0.0s | `ollama serve` starts (no model in VRAM) | ollama.log: "Listening on [::]:11434" |
| 5.0s | `launch_r2k.sh` checks model exists (GET /api/tags, 10ms) | ollama.log: 200 \| 10ms |
| 17.0s | Evaluator starts, sends first POST /api/generate | ollama.log: POST /api/generate |
| 18.0s | Ollama begins loading model: 37 layers, 1.8 GiB → GPU | ollama.log: "loading model" |
| 18.0s | "waiting for llama runner to start responding" | ollama.log |
| 21.5s | Runner started (3.47s load time, warm disk cache) | ollama.log: "llama runner started in 3.47 seconds" |
| 21.6s | First POST returns 200 (4.59s total — includes load) | ollama.log: 200 \| 4.59s |
| 22.1s | Second POST returns 200 (544ms — steady state) | ollama.log: 200 \| 544ms |
| 22.7s+ | Steady state: 500-650ms per call | ollama.log |

**Failure mode (if user interrupts during load):**
```
17:18:03  WARN "client connection closed before server finished loading"
17:18:03  "Load failed: timed out waiting for llama runner: context canceled"
17:18:03  HTTP 499 | 33.7s | POST /api/generate
```
Evaluator killed → no `current_strategy.json` → bridge has no targets →
**dead blue team**. The llm_trace file for that run will not exist at all.

**Mitigation:** Warm the model before the first match:
```bash
curl -s http://127.0.0.1:11434/api/generate \
  -d '{"model":"qwen2.5-coder:3b","prompt":"hi","stream":false}' > /dev/null
nvidia-smi  # verify ~2-4GB VRAM used
```
Subsequent matches start in ~4s (model resident, `keep_alive: "1h"`).

### 2.2 Verify tools and tests
- `python3 tools/analyze_trace.py --help` — should print usage
- `python3 tools/dump_prompt.py --scenario 3vs3_attack_center --no-explain` — should print prompt
- `python3 -m pytest tests/ -v --skip-slow` (if slow marker exists) or `python3 -m pytest tests/ -v` — 62 tests should pass
- `python3 tools/gen_field_diagrams.py --all` — should generate field diagram PNGs

### 2.3 Verify opencode
- `opencode` launches in the `core/` directory
- Test: ask "How does the referee detect a foul?" — should reference the knowledge base

## 3. Workshop structure

> [!important] Design principle
> Describe what we HAVE. Mention Phase 5 for future directions.
> Don't present planned features as existing. See §7 for the list of
> planned-but-not-yet-implemented items.

### Module 1 — Scoring-Ökosystem (~40 min)
- **Concepts:** 3 nodes → 3 topics → 1 aggregator → Worldstate.json.
  Referee 6 statuses (playing, ball_out, goal_kick, corner_kick_in, kickoff,
  foul_penalty), unified restart, early termination. Score: tactical -10..+10
  + momentum OLS (deque(300) = 30s sliding window, 5 trend classes).
  Reward: 1Hz, -10..+10, two code paths (decision polling + foul subscription).
  B-study table (0/1/3/6 samples, --explain tradeoff). Goalie idle ~95%
  (staleness + jittery ball-Y → bridge PID chases stale setpoint).
  `num_predict`: Ollama token generation cap (`r2k_evaluator.py:111`).
  `--no-explain` → 150 tokens (ONLY `assignments`). `--explain` → 600 tokens
  (`analysis` + `oracle` + `assignments`). If the response exceeds this
  budget, JSON is truncated → `fast_parse` fails → no strategy written →
  dead blue team. 150 is sufficient in steady state; cold-start responses
  can be verbose and risk truncation (see §2.1a warm-up).
- **Experiments:**
  1. Verify your stack (5 min) — `nvidia-smi`, `curl Ollama`, run 30s headless match.
  2. Live match with visualizer (10 min) — watch momentum panel + referee rows.
     Offline fallback: replay world_trace.
  3. Sample-count A/B (10 min) — `run_experiment.sh` with baseline vs 1 sample
     vs 0 samples. Compare KPIs via `analyze_trace.py`.
  4. "10 errors in 10 minutes" (10 min) — `git show 0566c11:.../ROS2K_GEM_FAQ.md`,
     find factual errors against code. Teaches audit skill.
  5. Scenario package walkthrough (5 min) — show TC-01 `field_diagram.png` +
     `analysis.md` (oracle/expert). Explain how to read a scenario package.

### Module 2 — World Model (~35 min)
- **Concepts:** 4-stage pipeline (Gazebo → tracker → aggregator → evaluator).
  Ground truth = `/gazebo/model_states` only (no `/odom`, no TF2).
  Tracker extracts ONLY position.x/position.y (no Yaw, no quaternion).
  LLM sees min_ents (X/Y only, rounded to 0.1). Staleness: the delay between
  when world state is measured and when the LLM's decision takes effect (~800ms).
  Trace logging: two JSONL files (`llm_trace`, `world_trace`), consumed offline
  by `analyze_trace.py`, correlated via `R2K_RUN_ID`.
- **Experiments:**
  1. "What does the LLM see?" (8 min) — `dump_prompt.py` + min_ents vs full
     Worldstate.json.
  2. Staleness measurement (7 min) — align world_trace + llm_trace timestamps,
     compute effective latency, compare to B-study p50 742-827ms.
  3. Oracle/expert comparison (10 min) — read `analysis.md`, run match with
     `--explain`, compare LLM's `analysis`/`oracle` output against human
     oracle/expert. Did the LLM reason correctly?
  4. opencode exploration (10 min) — ask opencode to explain the world model
     pipeline, find the tracker code, show what min_ents contains.

### Module 3 — K1 + Thresholds (~50 min)
- **Concepts:** K1 is controlled via ROS2 using a custom message type
  (`booster_msgs/RpcReqMsg`) on topic `/Kev1n/LocoApiTopicReq` — NOT standard
  `Twist`. API codes: 2001 = locomotion (vx, vy, vyaw), 2000 = failsafe.
  Topic name comes from `relay/hardware_mirror.json`. K1 angular velocity
  clamped to 0.4 rad/s (foot slip mitigation). Anti-patterns: no OOP HALs
  (bridge uses dynamic thread-closures), K1 freeze is sim-only (K1 ignores
  cmd_vel). Threshold/hysteresis/corridor/probability taxonomy (FAQ Q15+Q22).
- **Experiments:**
  1. Relay inspection (8 min) — `hardware_mirror.json` vs `only_sim_bots.json`.
  2. Hysteresis demo (12 min) — `HYSTERESIS_FRAMES=1` vs 3 in
     `tests/test_foul_detection.py` with patched constants. Watch flicker.
  3. opencode K1 exploration (10 min) — ask opencode: "How is the K1
     controlled? Show me the booster_msgs publishing code in the bridge."
  4. Corridor walk (10 min) — plot `momentum_30s` from a world_trace,
     shade trend corridors (stable ±0.5, rising >0.5, falling <-0.5).
  5. Threshold taxonomy discussion (10 min) — reference FAQ Q15+Q22.
     Which does ROS2K use today? (threshold + hysteresis. Corridor = momentum
     trend. Probability = not used.)

### Module 4 — Utils & Fragments (~35 min)
- **Concepts:** Referee rulebook (`docs/referee_rulebook.md`, single source
  of truth). Fragments: `header.txt` → `rules_core.txt` → `rules_{mode}.txt`
  → `samples_{mode}.txt`, assembled by `setup_r2k.py` at boot into
  `system_prompt.txt` (regenerated every boot, don't hand-edit). Override
  logic: strategy fragments replace mode fragments. Tools: `dump_prompt`
  (dry-run prompt inspector), `analyze_trace` (14 KPIs), `gen_field_diagrams`
  (field diagram PNGs), `run_experiment.sh` (3-repeat runner),
  `swap_fragments.sh` (experiment fragment swapper). `batch_evaluator.py`
  exists but KPI collection is broken (TODO line 91).
  `opencode` as AI-gestützter Development-Assistent (AGENTS.md + knowledge
  base auto-loaded).
- **Experiments:**
  1. KPI reading (8 min) — `analyze_trace.py` on own Module 1 run.
  2. Fragment surgery (10 min) — edit `rules_core.txt`, `dump_prompt.py`,
     run match, diff KPIs.
  3. opencode fragment edit (10 min) — ask opencode to edit a fragment,
     run `dump_prompt.py` to verify, then run a match and analyze KPIs.
  4. Field diagram generation (5 min) — `gen_field_diagrams.py --all`,
     inspect the PNGs.

### Module 5 — Forschungs-Roadmap (~45 min)
- **Concepts:** Walkthrough of Phase 5 research directions from
  `optimization_spec_v6.2.md` §7. Each direction is a research topic, not
  implemented yet. The lecturer presents the roadmap and discusses which
  directions interest the team.

  **5.1 Kalman Filter:** Filter noisy ball/bot positions, derive velocity.
  Would also address goalie idle (smoother ball-Y → less PID jitter).
  **5.2 Predictive World Model:** Forward-simulate by ~800ms to compensate
  for LLM latency. LLM decides for the world as it will be.
  **5.3 + 5.4 Watchdog + Failsafe:** Compare predicted vs actual. If
  divergence → switch to rule-based fallback. System never hangs.
  **5.5 Sim-to-Real:** Test on K1/Yahboom hardware via `--relay
  hardware_mirror`. Compare sim vs field KPIs.
  **5.10 5vs5 Scale-Up:** More bots, more roles, larger prompts. Does 3B
  handle 5-bot coordination?
  **5.11 LLM Output Quality:** Automated comparison of `--explain` output
  against oracle/expert texts (LLM-as-judge).
  **5.9 Automated Prompt Optimization:** DSPy/Optuna only if manual
  iteration becomes a bottleneck. Not for now.

- **Experiments:**
  1. "Make it your own" (10 min) — run isolated 60s headless match,
     inspect KPIs with `analyze_trace.py`.
  2. Oracle/expert reasoning comparison (10 min) — run with `--explain`,
     compare LLM reasoning against `analysis.md`.
  3. opencode deep dive (10 min) — ask opencode to explain a Phase 5
     concept, explore the codebase for where it would be implemented.
  4. Phase 5 discussion (15 min) — which directions for internships,
     student projects, September RoboCup?

### Buffer / Q&A (~25 min)

## 4. Offline fallback matrix (if Ollama/Gazebo down)

| Module | Experiment | Fallback |
|--------|-----------|----------|
| 1 | Live match | Replay checked-in world_trace through visualizer |
| 1 | Sample-count A/B | Read pre-existing `results/kpis_B6a*.json`, compare |
| 1 | Scenario package walkthrough | Show `field_diagram.png` + `analysis.md` (no live run needed) |
| 2 | Staleness | Use any existing `logs/*.jsonl` pair |
| 2 | Oracle/expert comparison | Read pre-existing `llm_trace` with `--explain` output |
| 3 | Hysteresis demo | Run `tests/test_foul_detection.py` with patched constants |
| 3 | K1 exploration | Read `4_EDGE_HARDWARE_SIM2REAL.md` + bridge code |
| 3 | Corridor walk | Read any `world_trace`, plot with matplotlib offline |
| 4 | Fragment surgery | `dump_prompt.py` only (no live run), compare prompt text |
| 4 | opencode fragment edit | opencode works without ROS/Ollama for code editing + `dump_prompt.py` |
| 5 | Make it your own | Skip if no live env; discuss conceptually |
| 5 | Oracle/expert comparison | Read pre-existing `llm_trace` + `analysis.md` offline |
| 5 | Phase 5 discussion | Show `optimization_spec_v6.2.md` §7 on screen |

## 5. Deliverable file plan

| File | Path | Audience | Status |
|------|------|----------|--------|
| Memo | `core/docs/workshop_memo.md` | Future opencode session | This file |
| Invitation | `core/docs/workshop_invitation.md` | Team (1-page) | ✅ Updated |
| Lecturer guide | `core/docs/workshop_lecturer_guide.md` | Lecturer | ✅ Created |
| Handout (if Decision A=1) | `core/docs/workshop_handout_v6.2.md` | Team (full) | TBD |
| Cheat page (existing) | `core/docs/cheatpage_r2k_team_workflow.md` | Team (setup reference) | ✅ Done |

## 6. Execution checklist

- [ ] Resolve Decision A (deliverable format)
- [ ] Resolve Decision B (Module 5 depth)
- [ ] Verify Ollama + Gazebo with one 60s headless run
- [ ] Warm up Ollama model (curl /api/generate, verify nvidia-smi VRAM)
- [ ] Verify `nvidia-smi` shows Ollama on GPU
- [ ] Verify `analyze_trace.py`, `dump_prompt.py`, `gen_field_diagrams.py` work
- [ ] Verify `pytest tests/ -v` passes (62 tests)
- [ ] Verify `opencode` launches and can answer architecture questions
- [ ] Write `workshop_handout_v6.2.md` (or slides + scripts per Decision A)
- [ ] Print/send invitation to team

## 7. Planned but NOT yet implemented (do not present as existing)

> [!danger] Lecturer note
> The following items are in the v6.2 spec as planned features but are NOT
> yet implemented. Do not present them as existing during the workshop.
> Mention them only in Module 5 (Phase 5 roadmap) as future work.

- **Goalie fix (Phase 2a):** Smooth blending in bridge is planned but NOT
  implemented. Goalie idle is still ~95%. The fix (bridge blending constants)
  is designed but not coded.
- **Shared regression suite (`test_non_functional.py`, Phase 2b):** Does NOT
  exist. No KPI threshold assertions yet. Current tests are unit tests only.
- **Dynamic prompt injection (Phase 4):** Does NOT exist. `r2k_evaluator.py:80`
  reads `system_prompt.txt` once at startup and caches it. No status-based
  fragment switching.
- **Scenario package integration in `setup_r2k.py` (Phase 2d):** Package
  folders exist with diagrams + analysis + KPI targets, but `setup_r2k.py`
  still reads flat JSON files. Fallback not yet implemented.
- **Kalman filter (Phase 5.1):** Not implemented. Tracker publishes raw
  positions, no velocity, no prediction.
- **Predictive world model (Phase 5.2):** Not implemented.
- **Watchdog + failsafe (Phase 5.3 + 5.4):** Not implemented.
- **5vs5 scenarios (Phase 5.10):** Not implemented. Current modes: 2vs2, 3vs3.
- **LLM-as-judge quality evaluation (Phase 5.11):** Not implemented.
- **Automated prompt optimization DSPy/Optuna (Phase 5.9):** Not implemented.
- **`batch_evaluator.py` KPI collection:** Broken (TODO line 91). The file
  exists and can launch matches but produces no KPI data.