---
id: 3_08
title: "Dynamic Prompt Assembly & Scenarios"
type: ARCHITECTURE
tags: [setup_r2k, prompt-engineering, scenarios, dynamic, relay-mapping, v6, v6.1, v6.2, fragments, strat-artifact, dump-prompt, sample-override]
last_modified: 2026-07-15
version: v6.2
---
# Dynamic Prompt Assembly & Scenarios

> [!info] Human Summary
> Explains how the ROS2K environment dynamically builds context-aware system prompts for the LLM based on the active game mode (e.g., 1vs1, 3vs3).

> [!abstract] LLM Context Anchor
> There is NO static `system_prompt.txt` committed to version control. The file is stitched together dynamically at runtime by `setup_r2k.py` using text fragments stored in `/strategy/fragments/` to match the active scenario JSON.
> **[NEW in v5]:** The `setup_r2k.py` script now functions as a comprehensive "Pre-Flight Compiler". Beyond prompt stitching for `qwen2.5-coder:3b`, it also evaluates the `--relay` flag to dynamically generate `ai_tactics/active_relay.json`, routing the AI's execution threads to either simulated Twist topics or physical JSON RPC hardware APIs.
> **[NEW in v6.1]:** `strat_*.txt` build artifacts are removed (gitignored, deleted). Strategy-specific fragments now OVERRIDE mode fragments instead of being appended (fixes contradictory signals). `tools/dump_prompt.py` added for dry-run prompt inspection. See [[7_04_SPECIFICATION_Prompt_Architecture]] for the full specification.

## 1. System Topology of Prompt Assembly

**[DEPRECATED in v4] Original Assembly Topology:**
~~~mermaid
graph TD
    subgraph Input ["User CLI"]
        Launch["./launch_r2k.sh --scenario 2vs1_default"]
    end

    subgraph Builder ["setup_r2k.py"]
        Scene["Read 2vs1_default.json"]
        Match["Match Regex (2vs1)"]
        Stitch["Concatenate Fragments"]
    end

    subgraph Fragments ["/strategy/fragments/"]
        Head["header.txt"]
        Core["rules_core.txt"]
        Spec["rules_2vs1.txt"]
        Samp["samples_2vs1.txt"]
    end

    subgraph Output ["Target File"]
        Out["ai_tactics/system_prompt.txt"]
    end

    Launch --> Scene
    Scene --> Match
    Match --> Stitch
    Head --> Stitch
    Core --> Stitch
    Spec --> Stitch
    Samp --> Stitch
    Stitch -->|Write| Out
~~~

**[NEW in v5] Validated V5 Pre-Flight Compiler Topology:**
The compiler now orchestrates both the cognitive context for the LLM and the physical execution pathways for the Bridge.

~~~mermaid
graph TD
    subgraph Input ["User CLI"]
        Launch["./launch_r2k.sh --scenario 2vs1_default --relay only_sim_bots"]
    end

    subgraph Builder ["setup_r2k.py (Pre-Flight Compiler)"]
        Scene["Read scenario.json"]
        Match["Match Regex & Stitch Fragments"]
        Relay["Evaluate Relay Profile"]
    end

    subgraph Outputs ["Runtime Configuration"]
        OutP["ai_tactics/system_prompt.txt"]
        OutR["ai_tactics/active_relay.json"]
    end

    Launch --> Scene
    Launch --> Relay
    Scene --> Match
    Match -->|Write| OutP
    Relay -->|Write| OutR
~~~

## 2. Architectural Logic & Data Flow
**[DEPRECATED in v4] The Problem:** Small-parameter LLMs like Nemotron-3-nano:4b easily suffer from "context bloat." If you provide a prompt containing rules and examples for 3vs3 formation strategies, but spawn the simulation in a 1vs0 Solo Drill, the LLM will hallucinate phantom teammates and crash the JSON output.

**[UPDATE in v5] The Problem:** Even the highly capable `qwen2.5-coder:3b` suffers from "context bloat." If provided with a prompt containing rules for 3vs3 formation strategies during a 1vs0 Solo Drill, token evaluation latency increases and the LLM may hallucinate phantom teammates.

To solve this, `setup_r2k.py` acts as a pre-flight compiler. It parses the `--scenario` flag, counts the number of blue entities physically requested in the Gazebo scene JSON, and stitches together only the relevant `.txt` fragments to create a lean, highly specific `system_prompt.txt` right before `r2k_evaluator.py` boots up.

**[NEW in v5] Hardware Routing:** Simultaneously, `setup_r2k.py` evaluates the `--relay` parameter to define how the Python execution threads address the target entities. It writes the `ai_tactics/active_relay.json` file, instructing `ollama_sandbox_bridge.py` whether to publish standard `geometry_msgs/Twist` or proprietray `LocoApiTopicReq` JSON RPC payloads for the physical Booster K1.

## 3. Fragment File Structure
* **`header.txt`**: Base AI persona and JSON raw output constraints.
* **`rules_core.txt`**: Universal field limits, X/Y boundaries, and valid actions (Move, Kick).
* **`rules_[MODE].txt`**: Specific tactical assignments (e.g., `rules_2vs2.txt` enforces a Striker and a Goalie role).
* **`samples_[MODE].txt`**: Crucial few-shot JSON examples demonstrating the Flat Entity schema and the Kick override trigger specific to that team size.
* **[NEW in v5] `relay_profiles/*.json`**: Source templates used by `setup_r2k.py` to generate the final `active_relay.json` output.
