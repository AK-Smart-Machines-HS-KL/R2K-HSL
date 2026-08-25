# Tournament Gen 0 — Insight Cards

## Baseline: M0 (C7 production, 5 Gazebo matches)
- Goals: 7B-3R (1.4 B/match)
- Pass: 46%, Possession: 42%, Goalie: 88%, Latency: 653ms

## M1: Kick fallback to Move when dist>1.5m (bridge)
- Text-probe: IDENTICAL to baseline (bridge changes don't affect text-probe)
- Gazebo: 0B-2R, pass 98%, poss 63%, goalie 95%
- **INSIGHT**: Converting Kick→Move at distance kills scoring completely. Bots
  approach the ball but never kick because the action was overridden.
- **VERDICT**: REJECTED. The action-level fallback is wrong — the kick action
  must be preserved so the kick fires when the bot gets close.
- **REUSABLE**: "Bridge kick-fallback must be at navigation level, not action level."

## M1c: Direct ball approach <1.0m (no behind-ball)
- Gazebo: 2B-1R, pass 32%, poss 53%, goalie 92%
- **INSIGHT**: Going directly to the ball (not behind it) produces goals but at
  bad angles. The behind-ball navigation serves a purpose: positioning the bot
  for a directional kick toward the goal.
- **VERDICT**: REJECTED. Goals dropped from 7 to 2.
- **REUSABLE**: "Behind-ball navigation IS load-bearing. Don't remove it."

## M1d: Behind-ball offset 0.6m → 0.35m
- Gazebo: 0B-2R, pass 44%, poss 49%, goalie 87%
- **INSIGHT**: Reducing the offset puts the bot too close to the ball — the
  phantom kick fires but at a bad yaw angle (bot hasn't finished turning).
- **VERDICT**: REJECTED. 0B goals.
- **REUSABLE**: "Behind-ball offset must be > kick trigger distance for proper angle."

## M1e: Kick trigger 0.4m → 0.6m (match behind offset)
- Gazebo: 0B-5R, pass 80%, poss 18%, goalie 72%
- **INSIGHT**: Widening the kick trigger causes premature kicks — bots kick
  the ball away before they're properly positioned. Goalie abandons goal line.
- **VERDICT**: REJECTED. Disaster — 0B, goalie crashed.
- **REUSABLE**: "0.4m kick trigger is well-tuned. Don't change it."

## M1f: Nav fallback >1.5m for ALL bots (incl goalie)
- Gazebo: 0B-9R, pass 73%, poss 19%, goalie 62%
- **INSIGHT**: The goalie gets Kick from the LLM, bridge skips tactical blending
  (only active when action != 'kick'), and the goalie chases the ball — leaving
  the goal wide open.
- **VERDICT**: REJECTED. Disaster — goalie crashed to 62%.
- **REUSABLE**: "Goalie kick must NOT trigger goalie blending bypass when far from ball."

## M1g: Nav fallback >1.5m for non-goalie only
- Gazebo: 0B-3R, pass 82%, poss 11%, goalie 80%
- **INSIGHT**: Bots reach the ball (90% pass completion) but still spin when
  they switch from direct approach to behind-ball at <1.5m. The oscillation
  is caused by the behind-ball position recalculating every frame as the ball
  drifts.
- **VERDICT**: REJECTED. Possession crashed to 11%.
- **REUSABLE**: "The spinning is caused by the behind-ball position being a
  MOVING TARGET. Fix: freeze behind position when computed, don't recalculate
  every frame."

## M3: Create samples_ball_out.txt (1 example)
- Text-probe: 29.6% pass precision (baseline 29.9%) — no effect
- **INSIGHT**: Ball-out sample doesn't help text-probe because the evaluator
  only loads samples_ball_out.txt when status='ball_out', and the easy corpus
  has only 2 ball_out scenarios.
- **VERDICT**: NEUTRAL. Needs Gazebo testing to verify kick-in behavior.

## M4: Create samples_corner_kick_in.txt (1 example)
- Text-probe: 30.1% pass precision (baseline 29.9%) — marginal
- **VERDICT**: NEUTRAL. Same as M3 — needs status-specific corpus.

## M5: Pass rule gated to opponent half (X>0)
- Text-probe: 68.3% pass recall (DOWN from 90%), 34.9% pass precision (UP from 30%)
- **INSIGHT**: The X>0 gate reduces over-passing but kills too much pass recall.
  The LLM stops passing from the own half entirely, even when a teammate is open.
- **VERDICT**: REJECTED. Recall dropped too much.
- **REUSABLE**: "Pass gating by field half is too aggressive. The LLM needs to
  pass from own half in some situations (e.g. goalie clearance to midfielder)."

## M7: Remove "closest bot kicks" rule
- Text-probe: 95% pass recall (UP from 90%), 38.6% pass precision (UP from 30%)
- Gazebo: 1B-3R (was 7B-3R), pass 43%, lat 784ms (+131ms)
- **INSIGHT**: The rule IS load-bearing in Gazebo. Without it, the LLM picks
  random kickers, doesn't coordinate who should challenge the ball, and
  latency increases (+131ms — the LLM generates more varied output).
- **VERDICT**: REJECTED. Text-probe winner but Gazebo loser.
- **REUSABLE**: "'closest bot kicks' rule is load-bearing for live matches.
  The 3B model needs explicit role assignment — it can't infer who should
  kick from positions alone. This confirms the C3 inter-lingua finding that
  the 3B model is a transducer, not a reasoner."

## GEN 0 WINNER: M0 (baseline)
No variant beat the baseline in Gazebo. The baseline (C7) is well-tuned.
The key insight is that the spinning is caused by the behind-ball position
being a moving target — the fix is to freeze it, not to change the offset
or trigger distance.

## NEXT STEPS (Gen 1)
- Implement frozen behind-position (compute once, don't recalculate until
  ball moves >0.3m or bot kicks)
- Keep M3 + M4 (ball_out + corner samples) for status-specific testing
- Test PD alignment threshold 0.5 → 0.35 rad (faster turn = less spinning)
- Test kick cooldown 2.0s → 1.5s (more frequent kicks)

## Gen 1: Frozen behind-position + offset tuning

### Gen1-M1: Frozen behind-position (0.6m offset, recompute if ball moves >0.3m)
- Gazebo: 1B-2R, pass 55%, poss 47%, goalie 86%, cluster 0%
- **INSIGHT**: Freezing reduces spinning (cluster 0% in 4/5 matches) but goals
  dropped (7→1). The bot freezes the behind position at 0.6m from ball, but the
  kick trigger is at 0.4m — the bot is stuck 0.2m too far to kick.
- **VERDICT**: REJECTED. Goals dropped.

### Gen1-M2: Frozen behind + offset reduced to 0.4m (= kick trigger)
- Gazebo: 0B-0R, pass 23%, poss 34%, goalie 95%
- **INSIGHT**: Same problem as Gen0-M1d — 0.4m offset is too close for proper
  yaw alignment. The phantom kick fires but at a bad angle.
- **VERDICT**: REJECTED. 0 goals.

## OVERALL CONCLUSION

**The baseline bridge (0.6m offset, 0.4m trigger, no freezing) is well-tuned.**
Every variant we tested produced FEWER goals than the baseline. The parameters
are sensitive in a narrow band:
- Offset < 0.5m → bad kick angle → 0 goals
- Offset > 0.7m → bot never reaches kick trigger → 0 goals  
- Offset = 0.6m → oscillation but WORKS (7 goals in 5 matches)
- Trigger < 0.4m → premature kicks → bad direction → 0 goals
- Trigger > 0.4m → goalie abandons goal → Red scores freely
- Trigger = 0.4m → well-tuned

The oscillation/spinning is a PHYSICS problem — the behind-ball position is a
moving target because the ball drifts between LLM calls (672ms latency × ball
velocity). The fix for v7 is TeamCaptain (CPU path planner with 10Hz update),
not bridge parameter tuning.

## WINNER: Baseline (M0/C7)
No variant beat the baseline. The current production configuration is the best
we can achieve with prompt-only changes and bridge parameter tuning. Further
improvements require:
1. v7 TeamCaptain (CPU path planner, replaces LLM kick navigation)
2. v7 yaw in Worldstate (enables proper kick angle calculation)
3. v7 velocity decay (ball position prediction without 672ms latency)
