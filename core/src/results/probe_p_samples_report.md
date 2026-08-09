# Phase F Probe Report (2026-08-09 16:56)

Model: `qwen2.5:3b` | Probes: 560

## Per-config aggregate (mean over situations and repeats)

| Config | hard% | parse% | score | vocab | ruleF | analysisQ | oracleQ | contrad | cov | continue | lat p50 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| F0 | 92% | 100% | 87.8 | 1.00 | 0.97 | 0.00 | 0.00 | 0.00 | 1.02 | 0% | 293ms |

## Worst situations per config (hard-fail rate)

- **F0:** w1_goalie_abandonment (90%), 2vs2_default (80%), 2vs2_goalie_pass (80%), emp_empirical-proven_restart_006 (60%), emp_empirical-proven_ball_won_002 (50%)

## Raw samples (one per config, first probe)

### F0 — 2vs2_default

```
blue_1 cover the goal line at (-4.0, 0.5)
blue_2 kick
blue_3 move to (0.0, -0.5)
```

