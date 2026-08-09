# Phase F Probe Report (2026-08-09 19:15)

Model: `qwen2.5:3b` | Probes: 560

## Per-config aggregate (mean over situations and repeats)

| Config | hard% | parse% | score | vocab | ruleF | analysisQ | oracleQ | contrad | cov | continue | lat p50 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| F0 | 89% | 100% | 88.2 | 1.00 | 0.96 | 0.00 | 0.00 | 0.00 | 1.00 | 0% | 292ms |

## Worst situations per config (hard-fail rate)

- **F0:** 2vs2_default (100%), 2vs2_goalie_pass (100%), emp_empirical-proven_restart_006 (100%), 3vs3_deep_cross (50%), emp_regression-anti_ball_won_014 (30%)

## Raw samples (one per config, first probe)

### F0 — 2vs2_default

```
blue_1 cover the goal line at (-4.0, 0.5)
blue_2 kick
blue_3 move to (2.0, 0.0)
```

