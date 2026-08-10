# Phase F Probe Report (2026-08-06 22:10)

Model: `qwen2.5:3b` | Probes: 500

## Per-config aggregate (mean over situations and repeats)

| Config | hard% | parse% | score | vocab | ruleF | analysisQ | oracleQ | contrad | cov | continue | lat p50 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| F0 | 92% | 100% | 89.4 | 1.00 | 0.97 | 0.00 | 0.00 | 0.00 | 1.02 | 0% | 296ms |

## Worst situations per config (hard-fail rate)

- **F0:** 2vs2_default (100%), 2vs2_goalie_pass (90%), emp_empirical-proven_restart_006 (80%), emp_regression-anti_ball_won_019 (80%), 3vs3_default (40%)

## Raw samples (one per config, first probe)

### F0 — 2vs2_default

```
blue_1 cover the goal line at (-4.0, 0.5)
blue_2 kick
blue_3 move to (-0.7, 1.0)
```

