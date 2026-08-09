# Phase F Probe Report (2026-08-08 23:45)

Model: `llama3.2:3b` | Probes: 60

## Per-config aggregate (mean over situations and repeats)

| Config | hard% | parse% | score | vocab | ruleF | analysisQ | oracleQ | contrad | cov | continue | lat p50 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| F0 | 42% | 95% | 72.4 | 0.95 | 0.77 | 0.00 | 0.00 | 0.00 | 0.74 | 0% | 322ms |

## Worst situations per config (hard-fail rate)

- **F0:** w1_goalie_abandonment (70%), w2_clustering_trap (70%), w4_unmarked_attacker (60%), w6_passivity_trap (60%), w3_wrong_direction_kick (50%)

## Raw samples (one per config, first probe)

### F0 — w1_goalie_abandonment

```
blue_1 cover the goal line at (-4.0, 1.7)
blue_2 kick
blue_3 move to (0.5, -0.8)
```

