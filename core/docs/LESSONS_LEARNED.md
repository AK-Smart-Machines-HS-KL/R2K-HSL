# ROS2K Lessons Learned (v6.4 Session)

> Read this at the start of every new opencode session. These are the
> recurring mistakes and key insights that must not be rediscovered.

## Meta-knowledge axiom (CRITICAL — recurring mistake)

The LLM prompt must NEVER contain: "bridge commands", "bridge executes",
"cmd_vel", "RPC", "path executor", "ROS2K protocols", or any implementation
detail. The LLM's world is: read positions, output per-bot instructions with
X,Y coordinates. Everything else is infrastructure. This mistake recurs —
check every prompt for meta-knowledge before saving.

## Clustering: LLM is correct, bridge/physics is wrong

When bots cluster, the LLM's targets are usually CORRECT. The problem is that
bots can't physically reach their targets (PD controller too weak, collision
physics, stuck against another bot). Fix by making LLM targets RELATIVE to
actual positions, not absolute zones. Relative positioning ("maximize distance
from blue_1 and blue_2") eliminated clustering from 47% → 0-1%.

## Goalie: don't pull from the line

The Phase 2a angle-block mode (pull goalie to X=-2.5 when ball is far) was
the root cause of goalie clustering with blue_3. Disabled via
`R2K_GOALIE_BLEND=0`. The LLM decides when the goalie advances — the bridge
obeys. The bridge's job is execution, not tactical override.

## Gazebo is "more demo than measurement"

Gazebo physics is non-deterministic (CV=90-129% on goals/shots). n=17 can
only detect 3x effects. Text-probe suite (deterministic, n=10, 15min) is
the primary evaluation instrument. Gazebo is for demos and eyeballing, not
statistical claims. This is a spike project — accept minor measurement errors.

## K1 kick is autonomous — needs abort

`kShoot` (2024) and `kVisualKick` (2038) chase the ball indefinitely. If
the ball moves, the K1 is stuck. v7 solution: camera detects ball motion
change → `kChangeMode` (2000) aborts the chase.

## Hardware differs — per-bot capability profiles

K1 (biped, fall risk, autonomous kick), Yahboom (diff-drive, metal-push
kick, lousy pan-tilt cam), trailer (non-holonomic, no kick, no cam), sim
(perfect odometry, phantom kick). The relay JSON is many-to-many (mixed for
testing). RoboCup forbids mixed teams in tournaments.

## No mixed teams in RoboCup

Tournament rule. But relay JSON supports mixed hardware for testing/demos.
Yahboom cam is lousy — cannot rely upon for critical tracking. K1 camera is
the primary visual sensor.

## Demo/calibration mode uses existing pipeline

`--demo` flag loads `header_demo.txt`. Human types commands, LLM reformats
to inter-lingua, same evaluator → bridge pipeline. No separate CLI. JSON
fallback (`calibrate_bot.py`) works when LLM is down. Demo prompt contains
NO meta-knowledge.

## start_ollama.sh path: use ORIGINAL_DIR

`launch_r2k.sh` does `cd src` at line 73. Path resolution for
`start_ollama.sh` must use `ORIGINAL_DIR` (saved before the `cd`). The log
file uses `/tmp/r2k_ollama.log` (not a relative path that breaks after
reboot or CWD change).

## TeamCaptain is v7 — not v6.4

TeamCaptain (CPU-only ROS2 node for motion planning) is designed in
ADR-A07 but NOT implemented in v6.4. The bridge still reads
`current_strategy.json` directly. When TeamCaptain is added (v7), the bridge
reads `optimized_path.json` with fallback to `current_strategy.json`.

## Prompt structure: F0 (global rules + 1 sample) is the optimum

The F3/F4 sweeps proved: global declarative rules + 1 separate JSON sample
beats interwoven rules+samples. Negative examples hurt the 3B model (broke
hard-pass from 93% → 67%). The SPLIT RULE must be a pairwise constraint on
ALL targets, not a ball-proximity trigger.

## Oracle is ground truth — not Qwen output

The `analysis.md` Oracle (GLM-written) is the reference. Qwen's output is
the test subject. Yellow vectors in field diagrams show the Oracle's
recommended positions, not Qwen's attempted positions. Qwen's output goes in
the "Output to bridge" section as text for comparison.

## v6.5: Dynamic roles don't fix role-locking (3B model limitation)

The dynamic-roles prompt ("GOALIE = closest to own goal") failed to make the
goalie kick — 0/100 matches. The 3B model anchors to sample patterns: 4 of 5
samples show blue_1=goalie, so it keeps that assignment regardless of the
header text. Adding a role-swap sample didn't help — the model needs 4+ swap
examples to overcome the pattern anchoring, which adds too many tokens.

**Fix:** v7 TeamCaptain — CPU planner handles role assignment, LLM only
outputs per-bot positions. The LLM's job is "where should each bot go," not
"who is the goalie."

## v6.5: Blue_3 forward movement improved but passing doesn't work

Dynamic-roles prompt caused blue_3 to advance forward 63.6% of calls (was
0.3%). But this didn't convert to goals because:
- When blue_2 kicks, the ball goes toward X=+4.5 (opponent goal)
- Blue_3 moves forward but is never in the ball's path
- The LLM doesn't reason about ball trajectory after kick
- The kick trajectory explanation in the prompt wasn't sufficient

**Fix:** v7 — TeamCaptain positions the receiver along the kick trajectory.
The LLM can't compute trajectories.

## v6.5: All-continuous score formula works

Replacing ALL step thresholds with `max(0, REF - dist) * GAIN` worked:
- Possession, cluster, lane, pressing, marking — all continuous
- No step functions remain anywhere in score_node.py
- Score trajectories improved (end: -0.95 → +0.25)
- No regressions in text-probe or clustering
- Named constants at file top, no magic numbers

## v6.5: Kickoff rule — standard formation, not scenario positions

The referee now warps bots to a standard formation on goal (all in own half,
≥1.5m from center) instead of the scenario start positions. Scenario start
positions may have red in blue's half (mid-game tactical situations) — these
are NOT valid kickoff positions. The standard formation is defined by
KICKOFF_FORMATIONS in referee_node.py (2vs2 and 3vs3 variants).

## v6.5: 100-match baseline — Red outperforms Blue

100 matches (10 scenarios × 10 runs × 120s):
- Blue wins: 19%, Red wins: 39%, Draws: 42%
- Blue scores 43 goals, Red scores 55 goals
- Best Blue scenario: 3vs3_wing_switch (67% win rate)
- Worst Blue scenario: 3vs3_high_line (30% win rate, 14 red goals)
- Blue effectively plays 2v3 (goalie never leaves line)

This is the v6.5 baseline for v7 regression testing.

## v6.5: No thresholds in prompt — qualitative language only

All fixed distances removed from prompt fragments: "within 2m", "within 1m",
"at least 1.5m" → "deep in the own half", "near the goal line", "well spread."
The 3B model reasons by comparison (who is closest), not arithmetic (is dist < 1.5).
Removing thresholds aligns the prompt with the model's capabilities. The model
can't compute distances — telling it "within 1m" is both useless and hypocritical
when the rules also say "do not compute exact distances."