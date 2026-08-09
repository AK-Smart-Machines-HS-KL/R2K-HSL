# Phase F Probe Report (2026-08-08 22:34)

Model: `llama3.2:3b` | Probes: 500

## Per-config aggregate (mean over situations and repeats)

| Config | hard% | parse% | score | vocab | ruleF | analysisQ | oracleQ | contrad | cov | continue | lat p50 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| F0 | 46% | 100% | 74.5 | 1.00 | 0.81 | 0.00 | 0.00 | 0.00 | 0.82 | 0% | 323ms |

## Worst situations per config (hard-fail rate)

- **F0:** 2vs2_goalie_pass (100%), emp_empirical-proven_restart_006 (100%), 2vs2_default (90%), 3vs3_default (90%), 3vs3_fast_counter (80%)

## Raw samples (one per config, first probe)

### F0 — 2vs2_default

```
blue_1 hold position
blue_2 kick
blue_3 move to (-0.8, 0.2)
```

