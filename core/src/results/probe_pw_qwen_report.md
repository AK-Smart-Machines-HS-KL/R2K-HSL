# Phase F Probe Report (2026-08-08 23:45)

Model: `qwen2.5:3b` | Probes: 60

## Per-config aggregate (mean over situations and repeats)

| Config | hard% | parse% | score | vocab | ruleF | analysisQ | oracleQ | contrad | cov | continue | lat p50 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| F0 | 83% | 100% | 85.3 | 1.00 | 0.94 | 0.00 | 0.00 | 0.00 | 0.94 | 0% | 279ms |

## Worst situations per config (hard-fail rate)

- **F0:** w6_passivity_trap (80%), w4_unmarked_attacker (20%), w1_goalie_abandonment (0%), w2_clustering_trap (0%), w3_wrong_direction_kick (0%)

## Raw samples (one per config, first probe)

### F0 — w1_goalie_abandonment

```
blue_1 cover the goal line at (-4.0, 0.6)
blue_2 kick
blue_3 move to (0.0, -0.7)
```

