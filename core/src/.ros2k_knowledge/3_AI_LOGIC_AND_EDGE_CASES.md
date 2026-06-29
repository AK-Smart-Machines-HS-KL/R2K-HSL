---
id: 3_AI_LOGIC
title: "Section 3: AI Logic, Failsafes & Edge Cases (V5)"
type: KNOWLEDGE_BASE_POWER_FILE
tags: [qwen, team-blue, team-red, failsafes, bounding-box, hysteresis, orbital-singularity, setup_r2k, phantom-kick, flat-json, ollama-tuning, kv-cache, user-space]
last_modified: 2026-05-31
version: v5_release
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
* **Problem:** Small-parameter LLMs possess zero inherent spatial intuition and often hallucinate nested JSON structures, crashing the Bridge's simple Python dictionary parser (Parsing Paralysis)[cite: 23].
* **Constraint:** The JSON schema MUST be strictly flat (e.g., `"blue_1": {...}`)[cite: 23]. The `setup_r2k.py` compiler ensures the LLM receives exact, flat few-shot examples tailored to the specific match size[cite: 23].
* **Bounding Box Logic:** The prompt dictates absolute limits (`X: [-4.5, 4.5]`)[cite: 23]. If breached, a math `clamp` in the Bridge forces the target variables back inside the pitch[cite: 23].

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
