---
id: 3_05
title: "Team Red Algorithmic Architecture"
type: ARCHITECTURE
tags: [team-red, state-machine, deterministic, baseline, staging, v6, v6.1, v6.2, aggression, p1-p5, freeze-compliance, blocking-avoidance]
last_modified: 2026-07-15
version: v6.2
---
# Team Red Algorithmic Architecture

> [!info] Human Summary
> Explains the design of Team Red, the deterministic control group. It has been upgraded to utilize "Algorithmic Staging" and the "Phantom Kick" service to avoid the orbital singularities that plague physical collision meshes.

> [!abstract] LLM Context Anchor
> `rule_evaluator_red.py` is a self-contained ROS 2 node. It bypasses JSON polling entirely. It calculates a staging point strictly 0.6m behind the ball. Upon reaching the ball, it halts and triggers the `/gazebo/set_entity_state` service, achieving parity with Team Blue.
> **[NEW in v5]:** The script `rule_evaluator_red.py` has been moved to the root directory for a flat process hierarchy. It remains the deterministic mathematical baseline against the new `qwen2.5-coder:3b` LLM.
> **[NEW in v6.1]:** Red adds `AGGRESSION_FACTOR=0.15` (15% chance to attack opponents → generates realistic foul scenarios). Smoothstep + low-pass filter hysteresis replaces all hard thresholds. P1-P5 improvements: boundary clamp (±1.0m restart / ±0.5m normal), all-bots-hold-midfield during opponent restart, blocking avoidance (shift toward sideline to open goal-ward path), aggression guarded during freeze. Freeze bug fix: `red_scored` one-shot edge detector replaced with `restart_team == 'blue'` check. See [[7_01_INTRODUCTION_Scoring_Referee_Gamestate]].

## 1. System Topology of the Deterministic State Machine

**[DEPRECATED in v4] Original Topology:**
~~~mermaid
graph TD
    subgraph ROS ["ROS 2 Middleware"]
        G["Gazebo States"]
        Node["rule_eval_red.py"]
    end

    subgraph Logic ["Algorithmic Staging"]
        Dist["Calc 0.6m Behind Ball"]
        Phase1["Phase 1: Navigate to Staging"]
        Phase2["Phase 2: Phantom Kick"]
    end

    G -->|Direct Sub| Node
    Node --> Dist
    Dist -->|Distance > 0.4m| Phase1
    Dist -->|Distance < 0.4m| Phase2
    Phase1 -->|Publishes cmd_vel| G
    Phase2 -->|Calls set_entity_state| G
~~~

**[NEW in v5] Validated V5 Topology:**
The logical flow remains identical, but the node name is corrected to strictly match the V5 file system (`rule_evaluator_red.py`).

~~~mermaid
graph TD
    subgraph ROS ["ROS 2 Middleware"]
        G["Gazebo States"]
        Node["rule_evaluator_red.py"]
    end

    subgraph Logic ["Algorithmic Staging"]
        Dist["Calc 0.6m Behind Ball"]
        Phase1["Phase 1: Navigate to Staging"]
        Phase2["Phase 2: Phantom Kick"]
    end

    G -->|Direct Sub| Node
    Node --> Dist
    Dist -->|Distance > 0.4m| Phase1
    Dist -->|Distance < 0.4m| Phase2
    Phase1 -->|Publishes cmd_vel| G
    Phase2 -->|Calls set_entity_state| G
~~~

## 2. Architectural Logic & Data Flow
Originally, Team Red blindly drove the collision mesh of its robots into the ball. This caused the ball to slide off-center, violently flipping the robot's tracking angle (`math.atan2`) and causing infinite spinning (Orbital Singularity).

The architecture now forces the red bots to aim at a mathematical waypoint projected *through* the ball towards the goal. It drives to this staging point, aligns itself, and forcefully injects dynamic velocity into the ball's physics engine state, entirely bypassing the physical mesh collision.

**[UPDATE in v5]:** This deterministic "Rule-based State Machine" approach remains fundamentally unchanged in V5. It serves as the ultimate benchmark to measure the zero-shot spatial reasoning and efficiency capabilities of the new `qwen2.5-coder:3b` Team Blue agents.

## 3. Code Reference & Interfaces
> **Source:** [`r2k_algorithmic/rule_evaluator_red.py`](../src/r2k_algorithmic/rule_evaluator_red.py) **[DEPRECATED in v4]**
> **Source:** [`rule_evaluator_red.py`](../rule_evaluator_red.py) **[NEW in v5]**

**[DEPRECATED in v4] Legacy Implementation:**
The core Phase 1 and Phase 2 execution logic.
~~~python
# snippet from rule_evaluator_red.py
# Red Team attacks the Blue Goal at X = -4.5
aim_yaw = math.atan2(0.0 - ball.y, -4.5 - ball.x)

# Calculate staging point 0.6m strictly behind the ball
behind_x = ball.x - math.cos(aim_yaw) * 0.6
behind_y = ball.y - math.sin(aim_yaw) * 0.6

dist_to_ball = math.hypot(ball.x - cx, ball.y - cy)

# PHASE 1: Staging (Drive to the setup point)
if dist_to_ball > 0.4:
    target_x, target_y = behind_x, behind_y
    # ... drive logic ...
# PHASE 2: Strike (Halt and Kick)
else:
    msg.linear.x = 0.0
    self.trigger_phantom_kick(bot_name)
~~~

**[NEW in v5] V5 Execution:**
The algorithmic staging code is identical, but is now executed as a flat script in the root namespace to avoid package discovery issues during the 0.2s Asynchronous Watchdog teardown.
