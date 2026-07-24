---
id: 3_04
title: "Team Blue Failsafes and Bounding Boxes"
type: SPECIFICATION
tags: [prompt-engineering, failsafes, bounding-box, safety, json]
last_modified: 2026-05-31
version: v5_release
---
# Team Blue Failsafes and Bounding Boxes

> [!info] Human Summary
> Details the textual boundaries and structural schema constraints enforced upon the LLM to prevent it from driving robots into walls or crashing the ROS 2 parsing bridge.

> [!abstract] LLM Context Anchor
> Safety constraints are enforced via `system_prompt.txt`. The LLM must NEVER output coordinates outside the X/Y bounds, and MUST use strictly FLAT entity structures (e.g., `"blue_1": {...}`) to prevent `ollama_sandbox_bridge.py` parsing paralysis. Nested dictionaries are strictly prohibited.
> **[NEW in v5]:** The target LLM is now `qwen2.5-coder:3b`. Furthermore, `system_prompt.txt` is no longer a purely static file; it is dynamically compiled at runtime by the pre-flight compiler (`setup_r2k.py`) to inject strict bounding box limits based on the active scenario.

## 1. System Topology of Constraint Enforcement

**[DEPRECATED in v4] Original Enforcement Topology:**
~~~mermaid
graph TD
    subgraph Prompt ["system_prompt.txt"]
        Rules["X bounds: -4.5 to 4.5<br>Flat JSON Schema required"]
    end

    subgraph LLM ["Nemotron"]
        Gen["Coordinate Generation"]
    end

    subgraph Bridge ["ollama_sandbox_bridge.py"]
        Parse["Flat Schema Parser"]
        Clamp["Math Clamp Check"]
        PID["Execution"]
    end

    Rules -->|Instructs| Gen
    Gen -->|Raw Output| Parse
    Parse -->|Extract Variables| Clamp
    Clamp -->|Validated Target| PID
~~~

**[NEW in v5] Validated V5 Enforcement Topology:**
Reflects the dynamic prompt compilation step and the updated Qwen2.5 model.

~~~mermaid
graph TD
    subgraph PreFlight ["setup_r2k.py"]
        Compiler["Scenario Bounding Box Injection"]
    end

    subgraph Prompt ["system_prompt.txt (Dynamic)"]
        Rules["X bounds: -4.5 to 4.5<br>Flat JSON Schema required"]
    end

    subgraph LLM ["Qwen2.5-Coder"]
        Gen["Coordinate Generation"]
    end

    subgraph Bridge ["ollama_sandbox_bridge.py"]
        Parse["Flat Schema Parser"]
        Clamp["Math Clamp Check"]
        PID["Execution"]
    end

    Compiler -->|Generates| Rules
    Rules -->|Instructs| Gen
    Gen -->|Raw Output| Parse
    Parse -->|Extract Variables| Clamp
    Clamp -->|Validated Target| PID
~~~

## 2. Architectural Logic & Data Flow
Small-parameter LLMs possess no physical intuition. They will confidently assign robots to drive off the pitch (`X: 100.0`) or hallucinate invalid JSON structures if left unguided. 

**[DEPRECATED in v4] Legacy Constraints:**
1. **Bounding Box Logic:** The prompt dictates absolute limits (`X: [-4.5, 4.5]`). If the LLM violates this, a math clamp in the Bridge forces the target variable back inside the arena.
2. **Schema Paralysis Prevention:** If the LLM nests its output (e.g., `{"blue_team": {"blue_1": ...}}`), the simple Python dictionary `.get()` methods in the Bridge fail silently, paralyzing the team. The prompt must contain examples explicitly demonstrating a 1D, flat entity list.

**[UPDATE in v5] Qwen2.5 Constraints:**
The underlying logic remains identical for `qwen2.5-coder:3b`. However, the spatial limits inside `system_prompt.txt` are now populated by `setup_r2k.py` to match the specific `scenario.json` being loaded (e.g., smaller boundaries for 1vs1 vs full pitch for 3vs3). The math clamps in `ollama_sandbox_bridge.py` serve as the final physical failsafe if the AI hallucinates outside the dynamic prompt constraints.

## 3. Code Reference & Interfaces
> **Source:** [`ai_tactics/system_prompt.txt`](../src/ai_tactics/system_prompt.txt)
> **[NEW in v5] Generator:** [`setup_r2k.py`](../setup_r2k.py)

**[DEPRECATED in v4] Static Prompt Example:**
The explicit spatial and structural constraints passed to Ollama.
~~~text
# snippet from system_prompt.txt
FIELD LIMITS: X is between -4.5 and 4.5. Y is between -3.0 and 3.0.
IMPORTANT: Entity names are flat. Target "blue_1" and "blue_2" directly; there is no "blue_team" key.
~~~

**[NEW in v5] Dynamic Context:**
While the snippet above still accurately reflects the final generated text sent to the LLM, it is now the resulting output of `setup_r2k.py`, which weaves the bounding box data and flat entity names into the template before the system boots.
