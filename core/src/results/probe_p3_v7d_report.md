# Phase F Probe Report (2026-08-08 17:38)

Model: `qwen2.5:3b` | Probes: 500

## Per-config aggregate (mean over situations and repeats)

| Config | hard% | parse% | score | vocab | ruleF | analysisQ | oracleQ | contrad | cov | continue | lat p50 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| F0 | 92% | 100% | 88.8 | 1.00 | 0.97 | 0.00 | 0.00 | 0.00 | 1.02 | 0% | 289ms |

## Worst situations per config (hard-fail rate)

- **F0:** 2vs2_default (100%), 2vs2_goalie_pass (90%), emp_empirical-proven_restart_006 (90%), 3vs3_default (70%), 3vs3_overload (30%)

## Raw samples (one per config, first probe)

### F0 — 2vs2_default

```
blue_1 cover the goal line at (-4.0, 0.5)
blue_2 kick
blue_3 move to (-0.75, 0.25)
```

