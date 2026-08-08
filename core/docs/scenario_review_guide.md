# Scenario Review Guide — Tasks 6 & 7

> **For new team members.** This guide explains the scenario package structure,
> the concepts introduced this session, and what to look for when reviewing
> the 17 hand-crafted and 33 empirical regression scenarios.

---

## 1. What are scenario packages?

Each scenario is a directory under `src/scenario/` containing:

| File | Purpose |
|---|---|
| `scenario.json` | Entity positions (ball + blue bots + red bots) at the start moment |
| `analysis.md` | Human-readable tactical analysis: Expert + Oracle + Qwen decision + score chart |
| `field_diagram.png` | 2D field view with bots, ball, and yellow dotted arrows showing Oracle targets |
| `score_chart.png` | Score trajectory after the decision (ensemble forecast or bar-delta) |

### Two types of scenarios

**Hand-crafted (17):** Manually designed tactical situations (attack_center,
defensive_crisis, pressing_trap, etc.). Used for prompt validation and
regression testing. Each has an Expert analysis + Oracle recommendation.

**Empirical (33):** Extracted from real Gazebo match traces at "umschaltmomente"
(transition moments — ball_won, clearance, cluster, restart, pass). Each
represents a moment where a tactical decision led to a goal (proven) or a
defensive failure (regression-anti).

---

## 2. Key concepts introduced this session

### Field orientation convention

Blue attacks toward X=+4.5 (red's goal). Blue defends X=-4.5 (own goal).

- **Blue's LEFT wing = positive Y** (Y > 0)
- **Blue's RIGHT wing = negative Y** (Y < 0)

When reviewing Expert text, check that "left wing" / "right wing" matches
the ball's Y coordinate. A ball at (3.0, 2.0) is on Blue's LEFT wing.

Documented in: `src/ros2k_knowledge/8_C3_SOCCER_KNOWLEDGE.md`

### Oracle commands (inter-lingua)

The Oracle uses a controlled vocabulary with explicit coordinates:

| Command | Meaning | Bridge translation |
|---|---|---|
| `blue_N cover the goal line at (X, Y)` | Goalie on goal line | `blue_N move to (X, Y)` |
| `blue_N move to (X, Y)` | Reposition | unchanged |
| `blue_N kick` | Shoot/clear | unchanged |
| `blue_N hold` | Stay in place | unchanged |

Every positional command MUST have explicit X,Y coordinates within field
bounds (X: -4.5 to 4.5, Y: -3.0 to 3.0).

### Goalie Y clamping

The goalie (`blue_1` with `cover the goal line at`) must always have Y
within ±0.9 (the goal post range). A goalie at Y=2.2 leaves 90% of the
goal open — this is a tactical error.

### "To achieve X because Y" reasoning

Every Oracle section must explain WHY the recommended positions are correct.
The format is: "To [achieve/prevent/capitalize/recover/escape] [X]:
[bot action] because [Y]."

Example: "To capitalize on the turnover: blue_2 kicks on goal, blue_3
provides a passing option, and the goalie covers the goal line for
counter-attack safety."

### No hard-wired thresholds in code

Per `AGENTS.md` §Conventions: distances, velocities, angles must be named
module constants at file top (e.g. `PRESSING_GAIN = 1.0`, not `if dist < 0.3:`).
Prefer continuous/proportional functions over step thresholds.

### Score formula (V7)

```
score = ball_x × 1.5                        # ball in opp half = positive
      + possession(±2.0)                     # blue within 1m: +2; red: -2
      - cluster_penalty(< 0.5m: -2, < 1.0m: -1)
      - lane_openness(0 blockers: -3)        # ball in own half, no blue between ball and goal
      + blockers_bonus(≥ 2: +1)
      + pressing_delta × PRESSING_GAIN(1.0)   # V7: reward for closing distance to ball
      + marking_delta × MARKING_GAIN(0.5)    # V7: reward for closing distance to nearest red (when red has possession potential)
      clamped to [-10, +10]
```

**Known issue:** The pressing/marking rewards are per-frame (velocity-based),
making them too small (+0.036) to counter the possession flip (-2.0). A fix
using continuous proximity rewards (option D) is designed but not yet
implemented. Score charts may show regression even when the Oracle is
tactically correct — the issue is in the scoring formula, not the Oracle.

### Ensemble score charts (hand-crafted)

Hand-crafted scenarios show a "weather forecast" style chart:
- 5 Gazebo runs × 4 seconds
- Shaded blue band = min-max range across runs
- Dotted line = mean
- Title: "Score forecast (4sec, 5 runs)"
- Scoring formula displayed at bottom

### Bar-delta score charts (empirical)

Empirical scenarios show a horizontal bar chart:
- 16 bars at 0.5s intervals (0.5s to 8.0s)
- Y-axis: "t=0 (Umschalt)" at bottom, time going up
- Cutoff at goal event (goal marker at actual time: "GOAL: blue at t=4.1s")
- "NO GOAL in 8s — [umschalt description]" if no goal
- X-axis: fixed [-10, +10]

**Known visual bugs (16/33 charts):** Goal marker y-position may be wrong
for very early goals (t<1.0s). Some NO GOAL labels may be truncated.
Goals after 8s are now correctly treated as NO GOAL but charts need
regeneration.

### Warp-and-resume

New infrastructure (`tools/warp_and_run.py`) allows teleporting bots to
start positions without restarting Gazebo — 75% faster than full restart.
Uses `shared_state/reset_flag.json` to reset referee + score_node state.
Not yet tested in production (full restart used for current data).

---

## 3. What to review

### Task 6: Empirical scenarios (33 files in `src/scenario/emp_*/`)

**Review 5 scenarios (one per umschalt type):**

| Scenario | Umschalt type | What to check |
|---|---|---|
| `emp_empirical-proven_ball_won_000` | ball_won (Blue) | Does blue_2 kick on goal? Is the support position tactically sound? |
| `emp_empirical-proven_clearance_004` | clearance | Does the nearest blue press correctly? Is the passing-lane cut correct? |
| `emp_regression-anti_ball_won_011` | ball_won (Red) | Is the emergency kick correct? Is the blocker between ball and goal? |
| `emp_regression-anti_cluster_022` | cluster | Does the cluster-break logic work? Is the spread position open space? |
| `emp_regression-anti_restart_029` | restart (foul_penalty) | Is the set-piece response correct? Who takes the kick? |

**For each scenario, check:**

1. **Scope** — does the one-sentence scope correctly describe the tactical situation?
2. **Expert** — are distances, possession, and numbers advantage correct? (recompute from `scenario.json`)
3. **Oracle** — does the "to achieve X because Y" reasoning make tactical sense?
4. **Oracle commands** — are all 3 blue bots assigned? Are coordinates in field bounds? Is goalie Y within ±0.9?
5. **Field diagram** — do the yellow dotted arrows point to sensible positions? Is the ball visible?
6. **Score chart** — does the trajectory make sense? (known bugs may cause visual issues)

### Task 7: Hand-crafted scenarios (17 files in `src/scenario/{2vs2,3vs3}_*/`)

**Review all 17 blind (without seeing the authoring process).**

**For each scenario, score on:**

| Criterion | Scale | What to check |
|---|---|---|
| Tactical correctness | 1-5 | Is the Oracle recommendation what a soccer coach would say? |
| Position reachability | yes/no | Can the bots physically reach the target positions from their current positions? |
| Strategy clarity | 1-5 | Is the reasoning clear and unambiguous? |

**Specific things to verify:**

1. **Wing direction** — if the Expert says "left wing", the ball Y should be positive
2. **Goalie on goal line** — `blue_1 cover the goal line at` should have Y within ±0.9
3. **Challenger within 0.5m** — if the Oracle says "advance toward the ball", the target should be close to the ball (not 2m away)
4. **No bot assigned twice** — each blue bot appears exactly once in the Oracle
5. **Possession claims** — if the Expert says "Red has possession", verify red is actually closer to the ball
6. **Ensemble chart** — does the mean score trajectory make sense? (known: may show regression due to score formula bug)

### Cohen's kappa (Task 7)

After both annotators (GLM-5.2 + human) score all 17:
1. Compute Cohen's kappa for each criterion (tactical correctness, reachability, clarity)
2. If kappa < 0.6 for any criterion, identify discrepant scenarios
3. Rework discrepant scenarios with both annotators present

---

## 4. Where to find everything

| What | Path |
|---|---|
| 17 hand-crafted analysis.md | `src/scenario/{2vs2,3vs3}_*/analysis.md` |
| 33 empirical analysis.md | `src/scenario/emp_*/analysis.md` |
| 50 scenario.json | `src/scenario/*/scenario.json` |
| 50 field diagrams | `src/scenario/*/field_diagram.png` |
| 50 score charts | `src/scenario/*/score_chart.png` |
| Probe results (500 probes, hard-pass 92%) | `src/results/probe_p3_v7_{raw,report}.{jsonl,md}` |
| Clustering check tool | `src/tools/check_clustering.py` |
| Corpus files (50 scenarios) | `src/tests/synthetic_worldstates/corpus_{scenarios,handcrafted_17,empirical_33}.jsonl` |
| Umschalt source data (74 entries) | `src/results/umschaltmomente.jsonl` |
| Score formula | `src/score_node.py` (V7 with pressing/marking) |
| Chart generator | `tools/gen_score_chart.py` |
| Diagram generator | `tools/gen_all_diagrams.py` |
| Empirical rework tool | `src/tools/rework_empirical_oracle.py` |
| Knowledge base (wing convention, score range) | `src/ros2k_knowledge/8_C3_SOCCER_KNOWLEDGE.md` |
| No-hardcoded-thresholds convention | `AGENTS.md` §Conventions |
| Session changelog | `docs/SESSION_CHANGELOG.md` (2026-08-07 entries) |
| LESSONS_LEARNED.md | `docs/LESSONS_LEARNED.md` |

---

## 5. Known issues and blockers

| Issue | Impact | Status |
|---|---|---|
| Score formula per-frame bug | All charts show regression (pressing +0.036 vs possession -2.0) | Fix designed (option D: continuous proximity), not yet implemented |
| Empirical chart visual bugs (16/33) | Goal marker position, NO GOAL label truncation | Regenerate after score formula fix |
| 2vs2 config artifact (3 scenarios) | 0% hard-pass (F0 probe uses 3vs3 samples → phantom blue_3) | Add samples_2vs2.txt or exclude from aggregate |
| Warp-and-resume not tested | Infrastructure ready but not validated | Test in next session |

---

## 6. How to regenerate after fixes

After the score formula fix (option D):

```bash
# Rebuild corpus
cd src && python3 tools/build_corpus.py --scenarios

# Rerun Gazebo for 17 hand-crafted (5x4s each)
cd .. && for s in 2vs2_default 2vs2_goalie_pass 3vs3_attack_center 3vs3_attack_wing \
    3vs3_contain_delay 3vs3_deep_cross 3vs3_default 3vs3_def_transition \
    3vs3_defensive_crisis 3vs3_fast_counter 3vs3_goalie_distribution 3vs3_high_line \
    3vs3_long_shot 3vs3_overload 3vs3_possession_lost 3vs3_pressing_trap 3vs3_wing_switch; do
    for i in 1 2 3 4 5; do
        ./launch_r2k.sh --headless --duration 4 --scenario $s --relay only_sim_bots
    done
done

# Regenerate charts
python3 tools/gen_score_chart.py --all         # all 50 (ensemble for HC, bar-delta for emp)
python3 tools/gen_all_diagrams.py --all         # all 50 field diagrams

# Re-probe
cd src && python3 tools/llm_probe.py --config F0 --corpus tests/synthetic_worldstates/corpus_scenarios.jsonl --repeat 10 --tag p3_final
python3 tools/check_clustering.py results/probe_p3_final_raw.jsonl --split
```
