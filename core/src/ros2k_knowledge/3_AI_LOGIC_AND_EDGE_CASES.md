---
id: 3_AI_LOGIC
title: "Section 3: AI Logic, Failsafes & Edge Cases (V6.1)"
type: KNOWLEDGE_BASE_POWER_FILE
tags: [qwen, team-blue, team-red, failsafes, bounding-box, hysteresis, orbital-singularity, setup_r2k, phantom-kick, flat-json, ollama-tuning, kv-cache, user-space, v6, v6.1, kick-in, prompt-switching, prompt-injection, reward-node, momentum, aggression, prompt-disentanglement, strat-artifact, sample-override, dump-prompt, match-state-injection, goalie-idle, red-p1-p5, blocking-avoidance, freeze-bug]
last_modified: 2026-07-15
version: v6.1
---
# Section 3: AI Logic, Failsafes & Edge Cases

> [!abstract] LLM Context Anchor
> **CRITICAL AXIOMS FOR RAG RETRIEVAL:**
> 1. **Team Paradigm:** Team Blue uses async JSON file multiplexing via REST API[cite: 23]. Team Red bypasses File I/O, acting as a low-latency ROS 2 node[cite: 23]. BOTH teams share parity in utilizing the `/gazebo/set_entity_state` service for Phantom Kicking[cite: 23].
> 2. **Delegation Boundary:** The LLM ONLY outputs flat JSON arrays[cite: 23]. It NEVER outputs Python code (`Twist` messages) or executes motor commands natively[cite: 23].
> 3. **Dynamic Prompting:** There is NO static `system_prompt.txt` committed to version control[cite: 23]. It is stitched together dynamically at runtime by `setup_r2k.py` using text fragments stored in `/strategy/fragments/`[cite: 23].
> 4. **[NEW in v5] LLM Performance Tuning:** The Ollama engine (`qwen2.5-coder:3b`) MUST run strictly in User-Space to allow the `0.2s Asynchronous Watchdog` to execute `pkill -9`. Systemd services are explicitly prohibited.

## 1. Unified System Topology (V5)

This graph illustrates the architectural split between the dynamic cognitive strategy engine (Team Blue) and the deterministic state-machine adversary (Team Red), and how they are constrained by prompts and hardcoded clamps[cite: 23].

~~~mermaid
graph TD
    subgraph S_Tuning ["User-Space Ollama Config"]
        Env["export OLLAMA_KV_CACHE_TYPE=q8_0"]
    end

    subgraph S_Blue ["Team Blue (Cognitive)"]
        Setup["setup_r2k.py<br>(Prompt Compiler)"]
        LLM["qwen2.5-coder:3b (Port 11434)"]
        Bridge["ollama_sandbox_bridge.py<br>Flat JSON Parser (NO OOP HAL)"]
    end

    subgraph S_Red ["Team Red (Algorithmic)"]
        RNode["rule_evaluator_red.py"]
        Clamp["Max Velocity Clamps"]
    end

    subgraph S_Shared ["Kinematic Mitigations"]
        Stage["Algorithmic Staging<br>(0.6m Behind)"]
        Kick["Phantom Kick<br>(set_entity_state)"]
    end

    Env -->|Forces Latency Drop| LLM
    Setup -->|Builds Flat Prompt| LLM
    LLM -->|Flat JSON Target| Bridge
    
    Bridge --> Stage
    RNode --> Clamp
    Clamp --> Stage
    
    Stage -->|Approach cmd_vel| G["Gazebo Engine"]
    Stage -->|Threshold Reached| Kick
    Kick -->|Injects Velocity| G
~~~

## 2. Core Logic & Failsafes

### A. Team Blue (Cognitive) & Parsing Paralysis
* **Problem:** Small-parameter LLMs possess zero inherent spatial intuition and often hallucinate nested JSON structures, crashing the Bridge's simple Python dictionary parser (Parsing Paralysis).
* **Constraint:** The JSON schema MUST be strictly flat (e.g., `"blue_1": {...}`). The `setup_r2k.py` compiler ensures the LLM receives exact, flat few-shot examples tailored to the specific match size.
* **Bounding Box Logic:** The prompt dictates absolute limits (`X: [-4.5, 4.5]`). The bridge applies boundary tolerance (±0.5m for turning back, ±1m for kick-in).
* **[V6] Bridge enforces behavior (zero LLM latency cost):** The bridge now handles smoothstep thresholds, ball velocity prediction, freeze compliance, anti-clustering, goalie tiered behavior, and kick-in boundary tolerance. The LLM sets intent ("go here, kick"); the bridge refines execution at 10Hz.
* **[V6] Smoothstep + low-pass on all thresholds:** Same `smooth_membership()` approach as red. Kick zone, staging, alignment, course, and stop are all smooth 0..1 memberships with low-pass filter (alpha=0.35). No hard jumps in speed or behavior.
* **[V6] Ball velocity prediction:** Bridge tracks ball_history (deque maxlen=5), predicts ball position 300ms ahead. Bot leads the ball instead of chasing stale LLM targets.
* **[V6] Freeze compliance:** Bridge subscribes to `/match_state`. Skips publishing when blue is frozen (kickoff conceded, ball-out offending, foul penalty offender). Prevents cmd_vel race with referee.
* **[V6] Anti-clustering:** Non-striker blue bots are nudged to wider Y if within 1.5m of another blue bot. Enforced at 10Hz, not in the prompt.
* **[V6] Goalie tiered behavior:** Bridge enforces X=-4.0 + dynamic Y when ball is in opponent/midfield half. When ball is in own zone (X < -2.0), the LLM's target stands (goalie may advance).
* **[V6] Strategy poll reduced from 500ms to 100ms:** LLM decisions reach motors 400ms faster.

### B. Team Red (Algorithmic) & Engine Cutoffs
* **Problem:** Proportional control errors in the 10Hz Euclidean state machine can command impossible physics (e.g., 50 m/s), causing Gazebo robots to launch into the sky[cite: 23].
* **Constraint:** Team Red intercepts the `Twist` message before publication[cite: 23]. It applies a hard max/min clamp to `linear.x` (1.5) and `angular.z` (2.0)[cite: 23]. 
* **Engine Cutoff:** If the red robot's telemetry crosses the physical arena edge, an explicit stop vector (all zeros) is published to kill the motor immediately[cite: 23].

### C. Shared Kinematics: Orbital Singularities & Kicking
* **Problem:** Driving a rigid collision mesh into the planar-locked ball causes the ball to slide off-center, violently flipping the robot's tracking angle (`math.atan2`) and causing infinite spinning (Orbital Singularity)[cite: 23].
* **Constraint:** BOTH evaluation pipelines intercept raw movement commands to the ball and enforce Algorithmic Staging[cite: 23]:
  * **Phase 1 (Staging):** Calculates a mathematical waypoint strictly 0.6m behind the ball to force a clean approach curve[cite: 23].
  * **Phase 2 (Strike):** Upon reaching a close deadband distance (0.4m), the motors are halted, and the `/gazebo/set_entity_state` service forcefully injects high-speed velocity into the ball[cite: 23].

### D. LLM State Chatter & Hysteresis
* **Problem:** When arriving at the ball, the LLM rapidly alternates between "Move" and "Kick", crashing and respawning the PID threads at 1Hz without physical progress (Hysteresis)[cite: 23].
* **Constraint:** A strict textual override exists in the prompt fragments: "If a Blue Team bot is near the ball, you MUST use the Kick action"[cite: 23].

## 3. Critical Code Interfaces

**Dynamic Prompt Assembly (`setup_r2k.py`):**
~~~python
# The compiler stitches together context-aware fragments[cite: 23]
mode_match = re.search(r'(\d+vs\d+)', args.scenario)
mode = mode_match.group(1) if mode_match else "3vs3"

components = ["header.txt", "rules_core.txt", f"rules_{mode}.txt", f"samples_{mode}.txt"]
for comp in components:
    with open(f"strategy/fragments/{comp}", 'r') as f:
        full_prompt += f.read() + "\n\n"
~~~

**[NEW in v5] User-Space Ollama Latency Tuning (`launch_r2k.sh` / `.bashrc Immunity`):**
~~~bash
# Quantize Attention Cache and block multi-user concurrency for raw speed natively in User-Space
export OLLAMA_NUM_PARALLEL=1
export OLLAMA_KV_CACHE_TYPE=q8_0
export OLLAMA_KEEP_ALIVE=10m

# Start Ollama locally (NOT via systemd) to allow the watchdog to kill it later
nohup ollama serve > ollama.log 2>&1 &
~~~

**Team Red Velocity Clamping (`r2k_algorithmic/rule_evaluator_red.py`):**
~~~python
# Enforced prior to ROS 2 publication[cite: 23]
MAX_LINEAR = 1.5
MAX_ANGULAR = 2.0
msg.linear.x = max(-MAX_LINEAR, min(msg.linear.x, MAX_LINEAR))
msg.angular.z = max(-MAX_ANGULAR, min(msg.angular.z, MAX_ANGULAR))

if abs(current_pose.x) > 4.5 or abs(current_pose.y) > 3.0:
    msg.linear.x = 0.0 # Out of Bounds Engine Cutoff
~~~

---

## V6 Addendum: Momentum, Reward & Kick-In

> [!warning] V6 Extension
> V6 adds a 1Hz reward node, momentum tracking via OLS regression, red-team aggression,
> and kick-in prompt-switching. Source: `reward_node.py`, `score_node.py`, `rule_evaluator_red.py`,
> `core/docs/optimization_spec_v6.md`.

### V6 Momentum (score_node.py)

* `deque(maxlen=300)` ringbuffer (30s at 10Hz) stores tactical score samples.
* **OLS linear regression** on the window produces a slope, scaled by `MOMENTUM_SCALE_FACTOR=10.0`, clamped to `-10..+10`.
* Minimum `10` samples required; below that, trend = `"stable"`.
* Trend classification: `>2.0` ascending, `>0.5` improving, `>-0.5` stable, `>-2.0` declining, else collapsing.
* **Cold-start gotcha:** Ringbuffer resets on node restart. Batch runs should account for the first 3 seconds producing `"stable"` momentum.

### V6 Reward Node (reward_node.py)

* **1Hz fixed update rate** (not per-decision).
* **Scale:** `-10` to `+10` (normalized).
* **Decision reward:** Polls `current_strategy.json` mtime for strategy changes. Snapshots score before action, waits `5s` (Move) or `2s` (Kick), snapshots score after. Delta = reward.
* **Foul reward:** Subscribes to `/match_state` for foul events. Fixed `-1.0` penalty on foul detection.
* **Classification:** `> +1.0` positive, `-1.0..+1.0` neutral, `< -1.0` negative.
* **Two code paths — do not mix:** The mtime-polling path (decision rewards) and the `/match_state` subscription path (foul penalties) are separate. Confusing them causes silent reward calculation errors.

### V6 Red Aggression (rule_evaluator_red.py)

* `AGGRESSION_FACTOR = 0.15` — 15% chance per decision to move toward an opponent instead of the ball.
* Aggression has two modes (50/50 split): blocking (position between blue bot and ball) and pushing (move toward blue bot).
* This generates realistic pushing AND blocking foul scenarios for foul detection testing.
* Tune carefully: too high = constant fouls, too low = no foul data for evaluation.

### V6 Red Freeze Compliance (rule_evaluator_red.py)

* Red subscribes to `/match_state` and complies with referee freeze orders.
* **Kickoff freeze:** If `status == "goal"` and red conceded, all red bots stop publishing (let referee's zero-twist take effect). Prevents cmd_vel race.
* **Ball-out freeze:** If `status == "ball_out"` and `restart_team == "blue"` (red offended), all red bots frozen.
* **Foul penalty freeze:** If `status == "foul_penalty"` and red is the offender, only the penalized bot stops publishing.
* Without this, red and the referee both publish on `/{bot}/cmd_vel` — they race and the freeze fails.

### V6 Red Kick-In Awareness (rule_evaluator_red.py)

* When `match_state.status == "ball_out"` and `restart_team == "blue"` (blue has kick-in): red bots hold midfield, close pass lanes, play defensively. Do not chase the ball.
* When `match_state.status == "ball_out"` and `restart_team == "red"` (red has kick-in): closest red bot approaches ball from behind for kick-in.

### V6 Red Hysteresis (rule_evaluator_red.py)

* All hard thresholds replaced with **smoothstep + low-pass filter** membership functions (0.0..1.0).
* `smooth_membership(name, key, value, near, far, alpha=0.35)` returns a continuous membership:
  * 1.0 when `value <= near`, 0.0 when `value >= far`, S-curve (smoothstep) between.
  * Low-pass filter (`alpha=0.35`) damps rapid oscillation — implicit hysteresis without boolean flips. Ball bouncing at 0.4↔0.5m produces ~0.03 membership swing instead of a full 0→1 flip.
* **Behavior blending:** Downstream code blends behaviors proportionally instead of boolean switches:
  * Speed: `(1 - stop_factor) * (0.2 + course_factor * 0.6) * base_speed` — smooth ramp from 0.2 to 0.8 as alignment improves. No speed jumps.
  * Target: `behind_ball * stage_factor + ball * (1 - stage_factor)` — target smoothly shifts from behind-ball to ball as bot closes in.
  * Kick readiness: `kick_factor * align_factor > 0.85` — both closeness AND alignment must be high. No kicking while misaligned.
  * Angular velocity: `yaw_diff * 4.0 * (1 - align_factor * 0.5)` — rotation gradually reduces as alignment improves.
* Convergence: ~5-8 frames (0.5-0.8s at 10Hz) for membership to reach target from 0.0. This is the low-pass filter ramp-up time.

### V6 Red Anti-Clustering (rule_evaluator_red.py)

* Non-striker red bots maintain 1.5m minimum distance from each other.
* If within 1.5m of another red bot, the bot pushes to a wider Y position away from the teammate.
* Prevents red bots from converging on the same position.

### Kick-In Prompt Iteration History

Four prompt versions were tried during v5/v6 development. The lessons are critical for any future agent working on kick-in behavior:

| Version | Approach | Result |
|---------|----------|--------|
| v1 | Ad-hoc kick-in prompt + separate samples | Insufficient — teams didn't react cleanly |
| v2 | Prompt-switching in evaluator based on `match_state.status` | Better but fragile — state chain didn't reach LLM reliably |
| v3 | Paired few-shot examples + role assignment + restart positions | Overengineered — too many moving parts |
| v4 | Simplified single kick-in block | Most robust temporary solution |

**Deprecated assumptions (do NOT repeat):**
* "A complete architecture change to multiple prompt files solves it automatically." — In practice, the state chain (referee → aggregator → worldstate → LLM) was more important than the number of prompt files.
* "Bots react automatically to referee events." — Tactic, prompt, reset, and visualization must be EXPLICITLY coupled. A referee event alone does not produce bot behavior.

### Prompt-Injection Protection Principle

* Referee data must be structured JSON facts only — NEVER free-text instructions.
* No mixed roles: data stays data, instructions stay system prompt.
* The tactic LLM must NOT override referee decisions.
* Free text from logs or external sources must NOT act as instructions.
* **Violation example:** Injecting `referee_node.py` log output ("SIDELINE OUT at Y=-3.06") into the system prompt as a sentence. Correct approach: inject `"ball_out_event": {"side": "sideline", "y": -3.06}` as a JSON field in the worldstate.

### Kick-In Architecture Constraints

* **System-prompt exchange is data-driven:** `status == ball_out AND restart_team == blue` → kick-in prompt, else normal prompt.
* **Ball reset is NOT an LLM action.** The referee provides the coordinate; `/gazebo/set_entity_state` places the ball. The LLM never calculates or requests a ball reset.
* **Opponent displacement is NOT an LLM action.** The referee enforces minimum distance to the restart position. The LLM does not move opponents.
* **Scoring stays bound to goals only.** Kick-in changes only possession and restart, not the score.
* **Kick-in exception to field limits:** The restart bot MAY temporarily move outside the field boundary (up to 1m beyond the line) to approach the ball from behind. This is the ONLY case where leaving the field is allowed. After the kick, the bot MUST return inside. This exception is encoded in `rules_core.txt` as `KICK-IN EXCEPTION (BALL-OUT RESTART)`. The bridge does NOT clamp coordinates — the only constraint is the prompt rule.

### Team-Red Kick-In Behavior

Team Red must treat ball-out as a special state, not as normal play:

1. Detect `status == ball_out` in match state.
2. Read `restart_team`.
3. If `restart_team != red` (blue has kick-in): hold distance, secure space, close pass lanes. NO immediate ball attack.
4. One bot covers space, the other blocks simple pass routes.
5. Red must NOT occupy the restart position if rules forbid it.
6. After restart: return to normal defensive behavior.
7. Red needs a state recognition for `ball_out` and a reaction policy for `restart_team != red`.

### V6.1 Prompt Build Disentanglement (setup_r2k.py)

The prompt compilation pipeline was restructured in Phase 0 (2026-07-15) to eliminate build artifacts and fix contradictory sample signals:

* **`strat_*.txt` build artifacts removed:** `setup_r2k.py` no longer writes `strategy/strat_*.txt` files. These were build outputs assembled from fragments — they are now gitignored and deleted from version control. The fragments in `strategy/fragments/` are the sole source of truth.
* **Strategy-specific samples override mode samples:** `setup_r2k.py:117-120` — if `samples_{strategy}.txt` exists (e.g. `samples_recover.txt`), it is used INSTEAD of `samples_{mode}.txt` (e.g. `samples_3vs3.txt`). Previously both were appended, sending contradictory signals to the LLM (e.g. aggressive + defensive samples in the same prompt).
* **Strategy-specific rules override mode rules:** Same pattern at `setup_r2k.py:116` — `rules_{strategy}.txt` takes precedence over `rules_{mode}.txt` when it exists.
* **`tools/dump_prompt.py`** — dry-run prompt inspector that assembles fragments identically to `setup_r2k.py` WITHOUT requiring ROS or Ollama. Usage: `python3 tools/dump_prompt.py --scenario 3vs3_attack_center --strategy strat_default --no-explain`. Prints the full assembled prompt, per-fragment breakdown, and token estimate. Use this to verify prompt changes before launching a match.
* **Fragment assembly order:** `header.txt` → `rules_core.txt` → `rules_{strategy}.txt` (or `rules_{mode}.txt`) → `samples_{strategy}.txt` (or `samples_{mode}.txt`). The `header.txt` contains `{{EXPLAIN_INSTRUCTION}}` which is replaced at runtime with `--explain` / `--no-explain` directives.

### V6.1 R2K_INCLUDE_MATCH_STATE (r2k_evaluator.py)

* **Env var `R2K_INCLUDE_MATCH_STATE=1`** optionally injects `match_state` (status, restart_team) into the LLM payload (`r2k_evaluator.py:91-96`). Default is `0` (excluded).
* By default, `r2k_evaluator.py:88` strips the worldstate to `min_ents` — only X/Y coordinates of entities, no match_state, no tactical_score. The LLM never sees referee status unless this env var is set.
* **Warning:** The `match_state` injection is structured JSON (status string + restart_team string), NOT free-text instructions. This complies with the Prompt-Injection Protection Principle (see above).

### V6.1 Goalie Idle — Structural Limitation

* Goalie idle rate is 80-100% across all experiments. This is NOT fixable via prompt engineering.
* **Root cause:** The bridge PD controller chases a jittery ball-Y setpoint. The LLM outputs a goalie Y target, but the bridge's `smooth_membership` + low-pass filter overreacts to ball position noise, producing micro-oscillations that keep the goalie "moving" without actual positional progress.
* **Implication:** Future agents should NOT attempt to fix goalie behavior by changing prompt text, role descriptions, or goalie position parameters. The fix must be in the bridge's goalie PD controller tuning (smoothing factor, deadband), not in the LLM prompt.
* The goalie X position (default `-4.0`) is set by the LLM and enforced by the bridge when the ball is in the opponent/midfield half. When the ball enters the own zone (X < -2.0), the LLM's target stands and the goalie may advance.

### V6.1 Team Red Improvements (rule_evaluator_red.py)

Beyond the V6 aggression and freeze compliance documented above, V6.1 adds:

* **Freeze bug fix (critical):** The `red_scored` one-shot edge detector was replaced with `restart_team == 'blue'` check (`rule_evaluator_red.py:77-83`). Previously, `red_scored` was only `True` on the score-change frame, causing red to unfreeze after 1 frame. Now red stays frozen for the full 5s during kickoff/set-pieces by checking `restart_team` from `match_state` directly.
* **P1 — Boundary clamp expansion during restarts:** `restart_active` flag (`rule_evaluator_red.py:278-281`) expands the boundary clamp to ±1.0m beyond field limits when red has a restart (kick-in, goal kick, corner kick-in). Normal play keeps ±0.5m. This allows red bots to approach the ball from behind for restarts, matching the blue KICK-IN EXCEPTION rule.
* **P3 — All red bots hold midfield during opponent restart:** `rule_evaluator_red.py:229-232` — when blue has any restart, ALL red bots hold midfield position `(2.0, ball_y * 0.7)`. Previously, the closest bot kept charging, violating the freeze.
* **P4 — Blocking avoidance:** `rule_evaluator_red.py:250-275` — non-closest red bots check if their target is between a blue opponent and the ball. If the perpendicular distance to the opponent-to-ball line is < 0.5m, the bot shifts toward the nearest sideline by `0.6m - perp_dist`. This opens the goal-ward path for the striker instead of accidentally blocking it.
* **P5 — Aggression guarded during freeze:** `rule_evaluator_red.py:171` — `aggression_active = (not all_red_frozen) and (random.random() < self.AGGRESSION_FACTOR)`. No aggression during any freeze state.
* **Set-piece context flags:** `rule_evaluator_red.py:71-74` — `goal_kick_for_red/against_red`, `corner_kick_in_for_red/against_red` added alongside the existing `kick_in_for_red/against_red`. All used by the restart behavior override.
