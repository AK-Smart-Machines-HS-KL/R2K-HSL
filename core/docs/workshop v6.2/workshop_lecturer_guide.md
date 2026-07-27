---
title: "ROS2K v6.2 Workshop — Lecturer's Guide"
type: GUIDE
tags: [workshop, lecturer, guide, internal, v6.2]
last_modified: 2026-07-22
status: draft
---

# ROS2K v6.2 Workshop — Lecturer's Guide

> [!warning] Internal — for the workshop lecturer only
> This guide contains timing, talking points, expected answers, common
> student mistakes, and fallback strategies. Not distributed to students.
>
> **Design principle:** Describe what we HAVE. Mention Phase 5 for future
> directions. Don't present planned features as existing. See §"Planned but
> NOT yet implemented" at the end of this guide.

---

## Term glossary (introduce these when first used)

| Term | Explanation | Where it appears |
|------|-------------|------------------|
| **deque** | Double-ended queue. A fixed-length sliding window — old entries fall off the back when new ones are added at the front. Used for momentum: `deque(maxlen=300)` = last 300 world states (30s at 10Hz). | `score_node.py`, Module 1 |
| **OLS (Ordinary Least Squares)** | A linear regression method. Fits a straight line through data points by minimizing the sum of squared distances. Used to compute momentum trend (rising/falling/stable) from the deque of score values. | `score_node.py`, Module 1 |
| **Staleness** | The delay between when a world state is measured (tracker reads `/gazebo/model_states`) and when the LLM's decision based on that state takes effect (bridge moves the bot). Currently ~800ms. The LLM is always deciding based on a slightly outdated world. | Module 2 |
| **min_ents** | The stripped-down world state that the LLM receives: entity names + X/Y coordinates rounded to 0.1m. No velocity, no match_state (unless injected), no tactical_score. | `r2k_evaluator.py:88`, Module 2 |
| **Fragment** | A text file in `strategy/fragments/` that contains part of the system prompt: rules, examples, or persona. Assembled by `setup_r2k.py` at boot. | Module 4 |
| **Oracle / Expert** | Human-authored analysis texts in each scenario package. Oracle = strategic (what should happen tactically). Expert = technical (what the LLM should output). NOT fed to the LLM — for human comparison with `--explain` output. | Module 2, Module 5 |
| **RPC (Remote Procedure Call)** | A message format where the sender serializes a command as a JSON string inside a ROS2 message. The K1 uses `booster_msgs/RpcReqMsg` with `api_id` 2001 (move) or 2000 (failsafe). | Module 3 |
| **num_predict** | The Ollama API parameter that caps **how many tokens the model is allowed to generate** in its response. Set in `r2k_evaluator.py:111`. `--no-explain` → 150 tokens (prompt asks for ONLY `assignments`). `--explain` → 600 tokens (prompt asks for `analysis` + `oracle` + `assignments`). If the model's response exceeds this budget, it gets truncated mid-JSON → `fast_parse` fails → no `current_strategy.json` written → dead blue team. 150 is enough for a focused 3B model in steady state but can truncate a verbose cold-start response. | `r2k_evaluator.py:100-111`, Module 1, Module 4 |

---

## Pre-workshop preparation (30 min before participants arrive)

### Checklist

- [ ] All participants have: laptop with GPU, Ollama running, `qwen2.5-coder:3b` pulled, R2K-HSL repo cloned, `./install.sh` completed
- [ ] Run one 60s headless match: `./launch_r2k.sh --headless --duration 60 --scenario 2vs2_default --relay only_sim_bots` — verify it completes
- [ ] Warm up Ollama model: `curl -s http://127.0.0.1:11434/api/generate -d '{"model":"qwen2.5-coder:3b","prompt":"hi","stream":false}' > /dev/null` — prevents cold-boot dead-blue-team on first demo
- [ ] `nvidia-smi` shows Ollama using GPU VRAM (~2-4GB)
- [ ] `python3 tools/analyze_trace.py --help` works
- [ ] `python3 tools/dump_prompt.py --scenario 3vs3_attack_center --no-explain` works
- [ ] `python3 -m pytest tests/ -v` — 62 tests pass
- [ ] `python3 tools/gen_field_diagrams.py --all` — generates PNGs
- [ ] `opencode` launches and can answer "How does the referee detect a foul?"
- [ ] Print or display: `cheatpage_r2k_team_workflow.md` Part 1 (Setup) as reference

### If Ollama is down for a participant

- Check: `curl -s http://127.0.0.1:11434/api/tags` — if no response, Ollama isn't running
- Fix: `pkill -9 -f "ollama runner"; pkill -9 -f "ollama serve"; sleep 2; nohup ollama serve > /dev/null 2>&1 &; sleep 3; nvidia-smi`
- If GPU still not working: fall back to offline mode (replay traces, `dump_prompt.py`, read saved KPIs)

### Ollama warm-up timeline (cold boot → steady state)

> [!important] The first match after `ollama serve` starts will have a 30-40s
> delay before the model is resident in VRAM and the first LLM response
> arrives. This is a **cold-boot race**: the evaluator's first inference
> request triggers the model load. If the user closes the window or presses
> CTRL+C during this window, the model load aborts (HTTP 499) and blue
> team stays dead for the entire match.

Real timeline measured 2026-07-23 (RTX 5090 Laptop, qwen2.5-coder:3b, 1.8 GiB model):

```
t=0.0s   ollama serve starts (no model in VRAM)
t=5.0s   launch_r2k.sh GET /api/tags (model existence check, 10ms)
t=17.0s  Evaluator starts, first POST /api/generate sent
t=18.0s  Ollama begins loading model: 37 layers, 1.8 GiB → GPU
t=18.0s  "waiting for llama runner to start responding"
         ── model loading (disk → VRAM, CUDA init) ──
t=21.5s  llama runner started (3.47s load time on warm disk cache)
t=21.6s  First POST /api/generate returns 200 (4.59s total — includes load)
t=22.1s  Second POST returns 200 (544ms — steady state begins)
t=22.7s  Third POST returns 200 (513ms)
         ...steady state: 500-650ms per call...
```

**What can go wrong (observed failure mode):**
If the user closes the Gazebo window or presses CTRL+C during the model
load (t=18s to t=21.5s), the cleanup trap fires `pkill -9` on the evaluator
process. The HTTP connection drops. Ollama logs:
```
WARN "client connection closed before server finished loading, aborting load"
"Load failed: timed out waiting for llama runner: context canceled"
HTTP 499 | 33.7s | POST /api/generate
```
The evaluator dies, no `current_strategy.json` is written, the bridge has
no targets → **blue team is dead for the entire match**. The next launch
works because the model is now warm (partially loaded or cached by the
OS file cache), so load time drops to ~3.5s.

**Mitigation (for the lecturer):**
1. Always start Ollama and warm the model **before** launching a match
   in front of participants. Run this once at the start of the workshop:
   ```bash
   curl -s http://127.0.0.1:11434/api/generate \
     -d '{"model":"qwen2.5-coder:3b","prompt":"hi","stream":false}' > /dev/null
   nvidia-smi  # verify ~2-4GB VRAM used
   ```
   This loads the model into VRAM. Subsequent matches start in ~4s, not 30s.
2. If a participant's first match shows dead blue team: check
   `ls logs/llm_trace_*_<run_id>.jsonl` — if the file doesn't exist, the
   evaluator never made a call (cold-boot race). Have them relaunch;
   the second match will work (model is now warm).
3. `keep_alive: "1h"` in `r2k_evaluator.py:108` keeps the model resident
   for 1 hour after the last call, so back-to-back matches are fine.

### opencode quick start (for all modules)

opencode is used throughout the workshop as an AI-gestützter Development-
Assistent. It reads `AGENTS.md` + the knowledge base automatically. All
commands run from `~/R2K-HSL/core`:

```bash
cd ~/R2K-HSL/core
opencode
```

Module-specific opencode examples are inline in each module below. Plan
mode (Tab key) lets opencode suggest changes before making them.

---

## Module 1 — Scoring-Ökosystem (40 min)

### Timing

| Segment | Time | What |
|---------|------|------|
| Concepts | 10 min | Pipeline, momentum, reward, B-study, goalie idle |
| Experiment 1: Verify stack | 5 min | nvidia-smi, Ollama, 30s match |
| Experiment 2: Live match | 10 min | Visualizer, momentum, referee |
| Experiment 3: Sample-count A/B | 10 min | run_experiment.sh, compare KPIs |
| Experiment 4: 10 errors | 10 min | FAQ audit |
| (if time) Scenario package | 5 min | TC-01 diagram + analysis.md |

### Talking points

**Scoring pipeline (3 min):**
- Draw on whiteboard: `tracker → referee → score → reward → state_aggregator → Worldstate.json`
- Everything flows through flat JSON files on tmpfs, not ROS topics
- Ask: "Why files, not topics?" → Answer: LLM polls mtime, no rclpy needed, atomic os.replace

**Momentum (3 min):**
- `deque(maxlen=300)` — explain: a deque is a fixed-length sliding window. Last 300 world states (30s at 10Hz). Old values fall off.
- OLS (Ordinary Least Squares) — explain: fits a straight line through the score values in the deque. If the line goes up → "rising", down → "falling", flat → "stable".
- 5 trend classes: rising strongly, rising, stable, falling, falling strongly
- Ask: "Why 30s?" → Answer: long enough to see a tactical shift, short enough to react

**Reward (2 min):**
- 1Hz (once per second), -10..+10 scale
- Two code paths: mtime-polling (decision rewards — when LLM responds) + `/match_state` subscription (foul penalties — when referee publishes)
- Ask: "Why two paths?" → Answer: decisions are async (when LLM responds), fouls are event-driven (referee publishes)

**B-study findings (2 min):**
- Show the table from spec §4.3
- Key: 1 sample > 6 samples, `--explain` fixes OOB but +44% latency, rules+samples both needed
- Ask: "Why does 1 sample beat 6?" → Answer: 3B model copies one pattern, doesn't learn from diversity

**Goalie idle (2 min):**
- AS-IS: goalie stands still ~95% of the time
- Why: the bridge PID controller chases the LLM's target Y, which is based on a ball position that's ~800ms old and jittery. By the time the goalie gets there, the ball has moved. Result: micro-oscillations with no positional progress.
- This is a staleness problem (Module 2 covers this in depth)
- Phase 5.1 (Kalman filter) is the planned long-term fix — mention briefly, don't elaborate

### Experiment 1: Verify your stack (5 min)

```bash
nvidia-smi  # Ollama should show ~2-4GB VRAM
curl -s http://127.0.0.1:11434/api/tags  # Ollama running?
cd ~/R2K-HSL/core
./launch_r2k.sh --headless --duration 30 --scenario 2vs2_default --relay only_sim_bots
```

**Common issues:**
- "Ollama not found" → `nohup ollama serve > /dev/null 2>&1 &`
- "Model not pulled" → `ollama pull qwen2.5-coder:3b`
- "Gazebo won't start" → check `ros2 run r2k_world_model tracker` in another terminal

### Experiment 2: Live match with visualizer (10 min)

```bash
./launch_r2k.sh --scenario 3vs3_attack_center --relay only_sim_bots
```

**What to watch:**
- Momentum panel: does the line move? Does it correlate with scoring?
- Referee rows: do set-pieces appear? Ball-out → kick-in?
- HUD: Blue X : Y Red — does the score update?
- Goalie: does it move? (Expected: mostly stays still — this is the known idle issue)

**Offline fallback:** Replay a checked-in world_trace through the visualizer

### Experiment 3: Sample-count A/B (10 min)

```bash
# Run with current config (1 sample — B6a)
./tools/run_experiment.sh A baseline 120 3vs3_attack_center strat_default --no-explain

# Compare KPIs
python3 tools/analyze_trace.py --run-id <ID>
```

**What is `A`?** The first argument to `run_experiment.sh` is the **experiment
name** — a free-form label used for output filenames and console banners. It
has no special meaning to the script itself. The convention from the B-study
(2026-07-15):
- `A` = **baseline** (current fragments, no changes — the reference run)
- `B1`–`B7b` = **experimental variants** (different fragment sets, swapped
  via `swap_fragments.sh`)

The name flows into output files: `results/A_r1_prompt.txt`,
`results/A_r1_console.log`, `results/A_r1_summary.txt` (repeat 1 of 3).
When students run their own experiments, they can pick any name (e.g.
`my_rule`, `goalie_test`). The `EXP_DIR` (2nd arg) determines whether
fragments are swapped (`experiments/B3`) or kept as-is (`baseline`).

**Expected:** 1 sample → composite ~0.55, OOB ~16%, best scorer. 0 samples → total failure (empty JSON).

**Teaching point:** "This is how you run experiments today: `run_experiment.sh` + `analyze_trace.py`. You compare KPIs manually."

### Experiment 4: 10 errors in 10 minutes (10 min)

```bash
git show 0566c11:core/src/ros2k_knowledge/ROS2K_GEM_FAQ.md | head -200
# Find factual errors against the actual code
```

**Expected errors found:**
1. `--debug` flag (never existed)
2. Tracker does Yaw (wrong: only X/Y)
3. `/bot1/LocoApiTopicReq` (wrong: `/Kev1n/LocoApiTopicReq`)
4. `os.rename` (now `os.replace`)
5. `pkill -9 ollama` (watchdog kills Gazebo/ROS/Bridge, not Ollama)

### opencode examples for Module 1

```text
How does the referee detect a foul? Show me the threshold values.
```
```text
What does score_node.py momentum calculation do? Explain deque and OLS.
```
```text
Run a 60s headless match with scenario 3vs3_attack_center and show me the KPIs.
```
```text
The goalie is not moving. Check ollama_sandbox_bridge.py for how it handles
the goalie bot. Show me the PID control section.
```

---

## Module 2 — World Model (35 min)

### Timing

| Segment | Time | What |
|---------|------|------|
| Concepts | 8 min | Pipeline, ground truth, tracker, staleness, traces |
| Experiment 1: What does the LLM see? | 8 min | dump_prompt, min_ents vs Worldstate |
| Experiment 2: Staleness measurement | 7 min | Trace timestamp alignment |
| Experiment 3: Oracle/expert comparison | 12 min | --explain output vs analysis.md |

### Talking points

**4-stage pipeline (3 min):**
- Draw: `Gazebo /model_states → tracker (2D X/Y) → state_aggregator → Worldstate.json → r2k_evaluator → Ollama → current_strategy.json → bridge → cmd_vel`
- Ask: "What's missing?" → Answer: velocity, prediction, feedback (all Phase 5)

**Ground truth (2 min):**
- ONLY `/gazebo/model_states`. No `/odom`, no TF2, no IMU.
- Tracker extracts position.x, position.y ONLY. No Yaw, no quaternion.
- Ask: "Why so simple?" → Answer: small LLM can't process 3D quaternions, 2D is sufficient for soccer tactics

**Staleness (2 min):**
- Explain staleness: the delay between when the world state is measured and when the LLM's decision takes effect
- LLM latency ~800ms. Ball at 2 m/s → ball is 1.6m away from where the LLM thinks it is
- This is why the goalie stands still (Module 1): the goalie chases a target based on where the ball WAS, not where it IS

**Trace logging (1 min):**
- Two JSONL files: `llm_trace` (per LLM call) + `world_trace` (per 10Hz tick)
- Non-blocking, append-only, gitignored
- `analyze_trace.py` joins them by `R2K_RUN_ID` → 14 KPIs

### Experiment 1: What does the LLM see? (8 min)

```bash
python3 tools/dump_prompt.py --scenario 3vs3_attack_center --strategy strat_default --no-explain
# See the full system prompt

cat shared_state/Worldstate.json | python3 -m json.tool
# Compare: Worldstate has match_state, tactical_score, all entities
# But r2k_evaluator.py strips it to min_ents (X/Y only, rounded to 0.1)
```

**Expected observation:** The LLM sees a much simpler world than what exists. It doesn't see match_state, tactical_score, or velocity. It sees rounded X/Y positions.

### Experiment 2: Staleness measurement (7 min)

```bash
# Find a trace pair from a previous run
ls logs/llm_trace_*.jsonl logs/world_trace_*.jsonl | head -4

# Pick one run ID, look at timestamps:
head -1 logs/llm_trace_<ID>.jsonl | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'LLM call at t={d[\"t\"]:.3f}')"
head -1 logs/world_trace_<ID>.jsonl | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'World at t={d[\"t\"]:.3f}')"
```

**Expected:** ~700-900ms difference (matching B-study p50 742-827ms)

### Experiment 3: Oracle/expert comparison (12 min)

```bash
# Read the scenario's human analysis
cat scenario/3vs3_attack_center/analysis.md

# Run with --explain to get LLM reasoning
./launch_r2k.sh --headless --duration 60 --scenario 3vs3_attack_center --relay only_sim_bots --explain

# After the match, look at the LLM's reasoning in the trace:
# The llm_trace raw_response now contains "analysis" and "oracle" keys
# Compare: does the LLM's analysis match the human oracle?
```

**Discussion questions:**
- "Did the LLM's reasoning match the oracle's tactical intent?"
- "If KPIs are good but reasoning is nonsensical — is that a real improvement?"
- "If KPIs are bad but reasoning is sound — is that a bad prompt or just variance?"

**Teaching point:** "KPIs tell you WHETHER the LLM performed well. Oracle/expert tells you WHY. You need both."

### opencode examples for Module 2

```text
Read the latest world_trace file and tell me: how many frames, what was the
ball position at frame 100, and what was the match_state.status distribution?
```
```text
What does the LLM actually see? Show me the min_ents stripping in
r2k_evaluator.py and compare it to the full Worldstate.json.
```
```text
Why is the LLM producing empty JSON? Check the last llm_trace file for
parse errors.
```

---

## Module 3 — K1 + Thresholds (50 min)

### Timing

| Segment | Time | What |
|---------|------|------|
| Concepts | 12 min | K1 via ROS2 RPC, anti-patterns, threshold taxonomy |
| Experiment 1: Relay inspection | 8 min | hardware_mirror vs only_sim_bots |
| Experiment 2: Hysteresis demo | 12 min | HYSTERESIS_FRAMES, blocking duration |
| Experiment 3: opencode K1 exploration | 10 min | Ask opencode about K1 control |
| Experiment 4: Corridor walk | 8 min | Plot momentum with corridors |

### Talking points

**K1 control via ROS2 (4 min):**
- The K1 IS controlled via ROS2 — but using a custom message type, not standard Twist
- Message type: `booster_msgs/RpcReqMsg` (custom ROS2 msg, built in `ros2_ws/src/booster_msgs`)
- Topic: `/Kev1n/LocoApiTopicReq` (name comes from `relay/hardware_mirror.json`)
- The bridge serializes JSON commands inside the ROS2 message:
  - `api_id: 2001` = locomotion (vx, vy, vyaw)
  - `api_id: 2000` = failsafe (clear_buffer, lock_drive)
- Angular velocity clamped to 0.4 rad/s (prevents bipedal foot slip)
- Ask: "Why not standard Twist?" → Answer: K1's vendor SDK uses RPC-style commands, not continuous velocity streams. The bridge translates LLM assignments into RPC payloads.
- If `booster_msgs` is not built/sourced → bridge logs warning, K1 control silently disabled (`HAS_BOOSTER_MSGS=False`)

**Anti-patterns (3 min):**
- No OOP HALs: bridge uses dynamic thread-closures (`def task`), not `BaseBotDriver` inheritance
- K1 freeze is sim-only: referee freezes via `cmd_vel` Twist-zero, but K1 ignores `cmd_vel` — set-piece freezes don't work on K1 hardware
- Goalie idle is a staleness problem, not a prompt problem — the LLM's data is ~800ms old

**Threshold taxonomy (5 min):**
- Reference FAQ Q15 + Q22
- **Threshold:** single value comparison (e.g. `if dist < 0.3`)
- **Hysteresis:** prevent flickering — must persist for N frames before triggering (e.g. `HYSTERESIS_FRAMES=3`)
- **Corridor:** acceptable range (e.g. momentum trend ±0.5 = "stable" corridor)
- **Probability:** stochastic confidence (not used in ROS2K today)
- Ask: "Which does the referee use?" → Answer: threshold (distance/velocity checks) + hysteresis (frame persistence). Corridor = momentum trend classification. Probability = not used.

### Experiment 1: Relay inspection (8 min)

```bash
cat relay/only_sim_bots.json | python3 -m json.tool
cat relay/hardware_mirror.json | python3 -m json.tool
```

**Expected:** `hardware_mirror.json` maps bots to real hardware topics (`/Kev1n/LocoApiTopicReq`, `/bot1/cmd_vel`). `only_sim_bots.json` has no hardware — all bots are virtual (Gazebo).

### Experiment 2: Hysteresis demo (12 min)

```bash
python3 -m pytest tests/test_foul_detection.py -v -s

# Now patch HYSTERESIS_FRAMES=1 in referee_node.py (or in the test), re-run
# Observe: more fouls detected (less filtering = more sensitive)
```

**Teaching point:** "Hysteresis prevents flickering. A single frame of proximity doesn't make a foul — it must persist for N frames."

### Experiment 3: opencode K1 exploration (10 min)

Ask opencode:
```text
How is the Booster K1 controlled? Show me the booster_msgs publishing code
in ollama_sandbox_bridge.py. What are API codes 2000 and 2001?
```

**Expected:** opencode reads the bridge code and the knowledge base (`4_EDGE_HARDWARE_SIM2REAL.md`), explains the RPC mechanism, shows the relevant code sections.

### Experiment 4: Corridor walk (8 min)

```bash
python3 -c "
import json, matplotlib.pyplot as plt
records = [json.loads(l) for l in open('logs/world_trace_<ID>.jsonl')]
scores = [r.get('tactical_score', {}).get('momentum_30s', 0) for r in records]
times = [r['t'] - records[0]['t'] for r in records]
plt.plot(times, scores)
plt.axhspan(-0.5, 0.5, alpha=0.2, color='gray', label='stable corridor')
plt.axhspan(0.5, 2.0, alpha=0.2, color='green', label='rising')
plt.axhspan(-2.0, -0.5, alpha=0.2, color='red', label='falling')
plt.xlabel('Time (s)'); plt.ylabel('Momentum 30s'); plt.legend()
plt.savefig('momentum_corridor.png')
"
```

### opencode examples for Module 3

```text
How is the Booster K1 controlled? Check the edge hardware power-file.
Show me the booster_msgs publishing code in ollama_sandbox_bridge.py.
What are API codes 2000 and 2001?
```
```text
Run a 30s headless match with --relay hardware_mirror and compare the
relay JSON mapping to what topics actually show up.
```

---

## Module 4 — Utils & Fragments (35 min)

### Timing

| Segment | Time | What |
|---------|------|------|
| Concepts | 10 min | Fragments, tools, opencode as assistant |
| Experiment 1: KPI reading | 8 min | analyze_trace on previous run |
| Experiment 2: Fragment surgery | 10 min | Edit rules_core, dump_prompt, run, diff KPIs |
| Experiment 3: opencode fragment edit | 7 min | Ask opencode to edit a fragment + verify |

### Talking points

**Fragments (3 min):**
- `header.txt` → persona ("You are an aggressive soccer AI")
- `rules_core.txt` → universal rules (STAY INSIDE, goalie -4.0)
- `rules_{mode}.txt` → mode-specific (3vs3, 2vs2)
- `samples_{mode}.txt` → few-shot examples (1 sample — B-study finding)
- `setup_r2k.py` assembles at boot → `system_prompt.txt` (regenerated every boot, don't hand-edit)
- Override: strategy fragments replace mode fragments if they exist

**Tools (3 min):**
- `dump_prompt.py` — dry-run prompt inspector (no ROS/Ollama needed)
- `analyze_trace.py` — 14 KPIs from trace files
- `gen_field_diagrams.py` — generates field diagram PNGs for scenario packages
- `run_experiment.sh` — 3-repeat experiment runner
- `swap_fragments.sh` — experiment fragment swapper
- `batch_evaluator.py` — exists but KPI collection is broken (TODO line 91)

**opencode (2 min):**
- AI-gestützter Development-Assistent. Reads `AGENTS.md` + knowledge base automatically.
- Can answer architecture questions, run shell commands, edit files, debug
- Can run in Plan mode (Tab key) to suggest changes before making them
- Examples inline in each experiment below

### Experiment 1: KPI reading (8 min)

```bash
python3 tools/analyze_trace.py --run-id <ID from Module 1>
# Show: goals_for_blue, cluster_pct, oob_pct, goalie_idle_pct,
# latency_p50, composite_score
```

### Experiment 2: Fragment surgery (10 min)

```bash
python3 tools/dump_prompt.py --scenario 3vs3_attack_center --strategy strat_default --no-explain
# Edit rules_core.txt — add a rule (e.g. "ALWAYS pass to the bot closest to the goal")
# Re-inspect:
python3 tools/dump_prompt.py --scenario 3vs3_attack_center --strategy strat_default --no-explain
# Run match:
./launch_r2k.sh --headless --duration 60 --scenario 3vs3_attack_center --relay only_sim_bots
python3 tools/analyze_trace.py --run-id <ID>
# Compare: did the change help or hurt?
```

**Teaching point:** "This is how you iterate today: edit fragments, run a match, analyze KPIs. If KPIs improve, you can commit the change."

### Experiment 3: opencode fragment edit + experiment run (7 min)

Ask opencode:
```text
Edit rules_core.txt to add a rule: "ALWAYS pass to the bot closest to the
goal" if it's not already there. Then run dump_prompt.py to verify the prompt
includes the new rule.
```

**Expected:** opencode edits the file, runs dump_prompt.py, shows the updated prompt.

Now ask opencode to run the experiment and compare:
```text
Run a 60s headless match with scenario 3vs3_attack_center and --no-explain,
then run analyze_trace.py on the result and show me the KPIs. Compare
goals_for_blue and cluster_pct to the baseline run from Module 1.
```

**Plan mode demo (Tab key):**
```text
<Tab> to switch to Plan mode
"I want to add a new rule to rules_core.txt that prevents bots from clustering.
Show me a plan before making changes."
<Tab> to switch back to Build mode
"Go ahead."
```

**Expected:** Participants see that opencode can do fragment surgery + verification + experiment execution + KPI comparison in one conversation.

---

## Module 5 — Forschungs-Roadmap (45 min)

### Timing

| Segment | Time | What |
|---------|------|------|
| Phase 5 roadmap walkthrough | 20 min | Kalman, predictive, watchdog, failsafe, sim-to-real, 5vs5, LLM quality |
| Experiment 1: Make it your own | 10 min | Isolated run, KPI inspection |
| Experiment 2: Oracle/expert comparison | 10 min | --explain reasoning vs analysis.md |
| Discussion | 5 min | Which directions for internships/projects? |

### Talking points — Phase 5 from `optimization_spec_v6.2.md` §7

> [!important] These are research directions, NOT implemented features.
> Present them as "here's where the project is heading." Don't say "we have"
> — say "we plan."

**5.1 Kalman Filter (4 min):**
- Filter noisy ball/bot positions. Derive velocity (direction + speed).
- Would address goalie idle: smoother ball-Y → less PID jitter → goalie moves
- Implementation: `tracker_node.py` — add Kalman filter per entity
- This is the planned long-term fix for the goalie idle problem from Module 1

**5.2 Predictive World Model (3 min):**
- Forward-simulate world state by ~800ms (matching LLM latency)
- LLM decides for the world as it WILL be, not as it WAS
- Reduces effective staleness to near-zero
- Requires Kalman velocity (5.1)

**5.3 + 5.4 Watchdog + Failsafe (4 min):**
- Compare predicted vs actual state each 10Hz tick
- If divergence > threshold → flag anomaly
- If critical → switch blue to rule-based behavior (mirror `rule_evaluator_red.py`)
- System never hangs, never produces dangerous commands

**5.5 Sim-to-Real (3 min):**
- Test on K1/Yahboom hardware via `--relay hardware_mirror`
- Compare sim KPIs vs field KPIs
- Known limitation: K1 ignores cmd_vel for freeze (set-piece freezes sim-only)

**5.10 5vs5 Scale-Up (3 min):**
- 5 blue bots = 5 role assignments per LLM call
- More roles, larger JSON, higher latency
- Research question: does 3B model handle 5-bot coordination, or need 7B?

**5.11 LLM Output Quality (3 min):**
- Today: manual comparison of `--explain` output against `analysis.md` oracle/expert
- Future: automated LLM-as-judge produces `reasoning_quality_score`
- Deferred: `--explain` costs 44% latency, LLM-as-judge is circular

### Experiment 1: Make it your own (10 min)

```bash
./launch_r2k.sh --headless --duration 60 --scenario 3vs3_attack_center --relay only_sim_bots
python3 tools/analyze_trace.py --run-id <ID>
# Inspect your KPIs — this is your personal dataset from the workshop
```

### Experiment 2: Oracle/expert comparison (10 min)

```bash
cat scenario/3vs3_attack_center/analysis.md
./launch_r2k.sh --headless --duration 60 --scenario 3vs3_attack_center --relay only_sim_bots --explain
# After match: compare LLM reasoning (from llm_trace) against oracle/expert
```

**Discussion:**
- "Did the LLM's reasoning match the oracle?"
- "Which Phase 5 direction interests you for a 6-month internship?"
- "Which could be a 2-month student project?"

### opencode examples for Module 5

```text
Run a 60s headless match with scenario 3vs3_attack_center and --explain,
then extract the LLM's analysis and oracle fields from the llm_trace and
compare them to the oracle text in scenario/3vs3_attack_center/analysis.md.
```
```text
Explain the Phase 5.1 Kalman filter plan. Where in tracker_node.py would
it be implemented? Show me the current code that would need to change.
```

---

## Buffer / Q&A (25 min)

### Likely questions

**"Why is the goalie not moving?"**
→ The bridge PID controller chases the LLM's target Y, which is based on a ball position that's ~800ms old (staleness) and jittery. By the time the goalie arrives, the ball has moved. The result is micro-oscillations with no positional progress. The planned fix is a Kalman filter (Phase 5.1) that provides smoother, predicted positions.

**"Can I use opencode instead of reading the code myself?"**
→ Yes. opencode reads the knowledge base and AGENTS.md automatically. Ask it architecture questions, let it run experiments, edit fragments. It's especially useful for understanding code you didn't write. See the inline opencode examples in each module.

**"What if I don't have a GPU?"**
→ Ollama falls back to CPU (very slow, ~4000-5000ms latency). Alternatively, use Ollama Cloud or Uni Mainz as the LLM backend — configure in `~/.config/opencode/opencode.json`.

**"How is the K1 different from the Yahboom?"**
→ The K1 is a bipedal robot controlled via ROS2 custom messages (`booster_msgs/RpcReqMsg`) with JSON-serialized RPC commands (api_id 2001=move, 2000=failsafe). The Yahboom is a wheeled rover controlled via standard ROS2 `Twist` messages on `cmd_vel`. The bridge handles both — routing is determined by `relay/*.json` hardware_type.

---

## Planned but NOT yet implemented (lecturer reference)

> [!danger] Do NOT present these as existing during the workshop.
> Mention only in Module 5 as Phase 5 future work.

| Item                                                       | Spec reference | Status                                                             |
| ---------------------------------------------------------- | -------------- | ------------------------------------------------------------------ |
| Goalie fix (bridge blending)                               | Phase 2a       | Designed, NOT coded. Goalie idle still ~95%.                       |
| Shared regression suite (`test_non_functional.py`)         | Phase 2b       | Does NOT exist. Unit tests only.                                   |
| Dynamic prompt injection (status-based fragment switching) | Phase 4        | NOT implemented. `r2k_evaluator.py` caches prompt at startup.      |
| `setup_r2k.py` reads scenario packages                     | Phase 2d       | NOT implemented. Still reads flat JSON files.                      |
| Kalman filter                                              | Phase 5.1      | NOT implemented.                                                   |
| Predictive world model                                     | Phase 5.2      | NOT implemented.                                                   |
| Watchdog + failsafe                                        | Phase 5.3+5.4  | NOT implemented.                                                   |
| 5vs5 scenarios                                             | Phase 5.10     | NOT implemented. Current: 2vs2, 3vs3.                              |
| LLM-as-judge quality evaluation                            | Phase 5.11     | NOT implemented.                                                   |
| Automated prompt optimization (DSPy/Optuna)                | Phase 5.9      | NOT implemented.                                                   |
| `batch_evaluator.py` KPI collection                        | Phase 2b       | Broken (TODO line 91). File exists, launches matches, no KPI data. |