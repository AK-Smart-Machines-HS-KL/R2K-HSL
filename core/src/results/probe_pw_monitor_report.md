# Phase W Monitor POC Report (2026-08-08 23:48)

Primary: qwen2.5:3b | Monitor: llama3.2:3b | Probes: 30

## Summary

| Metric | Value |
|---|---|
| Qwen hard-pass (alone) | 30/30 (100%) |
| Monitor approved | 0/30 (0%) |
| Monitor corrected | 30/30 (100%) |
| Corrections that fixed Qwen's failure | 0/30 |
| Avg total latency (Qwen + monitor) | 1095ms |
| Qwen latency alone (for comparison) | 334ms |

## Per-scenario breakdown

| Scenario | Qwen pass | Approved | Corrected | Fixed? |
|---|---|---|---|---|
| w1_goalie_abandonment | 5/5 | 0/5 | 5 | 0 |
| w2_clustering_trap | 5/5 | 0/5 | 5 | 0 |
| w3_wrong_direction_kick | 5/5 | 0/5 | 5 | 0 |
| w4_unmarked_attacker | 5/5 | 0/5 | 5 | 0 |
| w5_boundary_violation | 5/5 | 0/5 | 5 | 0 |
| w6_passivity_trap | 5/5 | 0/5 | 5 | 0 |
