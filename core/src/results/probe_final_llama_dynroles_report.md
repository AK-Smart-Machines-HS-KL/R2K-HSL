# Phase F Probe Report (2026-08-10 02:10)

Model: `llama3.2:3b` | Probes: 560

## Per-config aggregate (mean over situations and repeats)

| Config | hard% | parse% | score | vocab | ruleF | analysisQ | oracleQ | contrad | cov | continue | lat p50 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| F0 | 73% | 96% | 80.6 | 0.96 | 0.89 | 0.00 | 0.00 | 0.00 | 0.92 | 4% | 303ms |

## Worst situations per config (hard-fail rate)

- **F0:** emp_empirical-proven_restart_006 (100%), 2vs2_default (90%), 2vs2_goalie_pass (90%), 3vs3_attack_wing (50%), emp_empirical-proven_clearance_004 (50%)

## Raw samples (one per config, first probe)

### F0 — 2vs2_default

```
blue_1 cover the goal line at (-4.0, 0.5)
blue_2 kick
blue_3 move to (-2.8, 0.6)
```

