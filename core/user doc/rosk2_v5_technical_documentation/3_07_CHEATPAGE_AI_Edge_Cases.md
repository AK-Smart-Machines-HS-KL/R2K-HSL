---
id: 3_07
title: "AI Edge Cases: Kinematic Hacks and LLM Hysteresis"
type: CHEATPAGE
tags: [hysteresis, orbital-singularity, deadband, failsafe]
last_modified: 2026-05-31
version: v5_release
---
# AI Edge Cases: Kinematic Hacks and LLM Hysteresis

> [!info] Human Summary
> Details empirically derived countermeasures to resolve erratic physical behaviors, specifically orbital singularities and schema parsing paralysis.

> [!abstract] LLM Context Anchor
> To prevent Team Red from infinitely circling the ball (Orbital Singularity), they must utilize Algorithmic Staging and the Phantom Kick. To prevent Team Blue from freezing (Parsing Paralysis), the LLM must generate strictly Flat Entity JSON outputs.
> **[NEW in v5]:** While `r2k_visualizer.py` implements a tolerant fallback parsing cascade for malformed JSON, `ollama_sandbox_bridge.py` strictly does NOT. The `qwen2.5-coder:3b` prompt must continually enforce a flat JSON schema to prevent execution logic paralysis.

## 1. System Topology of Kinematic Stabilization

**[DEPRECATED in v4] Original Stabilization Topology:**
~~~mermaid
graph TD
    subgraph S_Red ["Algorithmic (Red)"]
        R1["Calc Staging (0.6m)"]
        R2["Halt @ 0.4m"]
        R3["Trigger Phantom Kick"]
    end

    subgraph S_Blue ["Cognitive (Blue)"]
        B1["Explicit Kick Override"]
        B2["Flat JSON Schema"]
        B3["Halt @ 0.4m & Kick"]
    end

    S_Red --> S_Engine["Gazebo Engine"]
    S_Blue --> S_Engine
~~~

**[NEW in v5] Validated V5 Stabilization Topology:**
Corrected node names and execution domains based on the V5 file system.

~~~mermaid
graph TD
    subgraph S_Red ["rule_evaluator_red.py (Red)"]
        R1["Calc Staging (0.6m)"]
        R2["Halt @ 0.4m"]
        R3["Trigger Phantom Kick"]
    end

    subgraph S_Blue ["ollama_sandbox_bridge.py (Blue)"]
        B1["Explicit Kick Override"]
        B2["Flat JSON Schema Enforcement"]
        B3["Halt @ 0.4m & Kick"]
    end

    S_Red --> S_Engine["Gazebo Engine"]
    S_Blue --> S_Engine
~~~

## 2. Orbital Singularity (Team Red)
**Symptom:** A red robot approaches the ball, fails to transfer momentum via physical collision, slides off center, and enters an infinite high-speed spin.
**Solution:** Do not rely on Gazebo's rigid body physics for ball strikes. Implement Algorithmic Staging (projecting a target behind the ball), halt at 0.4m, and use the `/gazebo/set_entity_state` service to forcefully set the ball's `Twist` linear vector.

**[UPDATE in v5]:** This mechanism is permanently preserved in the root `rule_evaluator_red.py` logic to benchmark against the LLM's zero-shot spatial capabilities without physical noise.

## 3. Schema Parsing Paralysis (Team Blue)
**[DEPRECATED in v4] Symptom:** The LLM generates tactically brilliant assignments, but the robots stand completely still.
**[DEPRECATED in v4] Solution:** The LLM has hallucinated a nested JSON structure (e.g., `"blue_team": {"blue_1": {"action": "Move"}}`). The Bridge's simple Python `.items()` loop cannot unpack this hierarchy. The `system_prompt.txt` must strictly enforce and exemplify flat entity keys.

**[UPDATE in v5] Symptom & Solution:** While `qwen2.5-coder:3b` is significantly more compliant than the old Nemotron model, rare token degradations can still cause nested dictionaries. As documented in the Post-Mortem, `ollama_sandbox_bridge.py` explicitly does NOT perform data refinement. The compiled dynamic `system_prompt.txt` MUST continuously enforce the flat entity rule.

## 4. State Chatter & Deadbands (Team Blue)
**Symptom:** The LLM rapidly alternates between "Move" and "Kick", causing the PID threads to crash and respawn at 1Hz without making progress.
**Solution:** Implement a strict textual Kick Rule override in the prompt: *"If a Blue Team bot is near the ball, you MUST use the Kick action."*

**[UPDATE in v5]:** With the new `state_aggregator.py` pipeline, the LLM receives hyper-accurate `Worldstate.json` coordinates. However, strict logical prompts remain necessary to override the LLM's tendency to hesitate exactly on the 0.4m physical threshold boundary.
