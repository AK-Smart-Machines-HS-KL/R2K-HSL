# Phase I3 Battery Report (2026-08-02 12:32)

Model: `qwen2.5:3b` | Situations: 20 | Probes: 40 | Explain: 0

## Per-situation results

| Situation | Status | Encoding | Parse | Code | Coverage | Tokens (user) | Latency ms |
|---|---|---|---|---|---|---|---:|
| kickoff_center | kickoff | json | OK | 0 | 3/3 | 50 | 947 |
| kickoff_center | kickoff | text | OK | 0 | 3/3 | 92 | 476 |
| attack_center | playing | json | OK | 0 | 3/3 | 50 | 676 |
| attack_center | playing | text | OK | 0 | 3/3 | 92 | 460 |
| defensive_crisis | playing | json | OK | 0 | 3/3 | 50 | 676 |
| defensive_crisis | playing | text | OK | 0 | 3/3 | 92 | 466 |
| fast_counter | playing | json | OK | 0 | 3/3 | 50 | 772 |
| fast_counter | playing | text | OK | 0 | 3/3 | 92 | 458 |
| goalie_active_ball_near | playing | json | OK | 0 | 3/3 | 50 | 824 |
| goalie_active_ball_near | playing | text | OK | 0 | 3/3 | 92 | 443 |
| cluster_two_bots | playing | json | OK | 0 | 3/3 | 50 | 934 |
| cluster_two_bots | playing | text | OK | 0 | 3/3 | 92 | 440 |
| boundary_ball_top_right | playing | json | OK | 0 | 3/3 | 50 | 930 |
| boundary_ball_top_right | playing | text | OK | 0 | 3/3 | 92 | 429 |
| ball_out_red_kickin | ball_out | json | OK | 0 | 3/3 | 50 | 948 |
| ball_out_red_kickin | ball_out | text | OK | 0 | 3/3 | 92 | 461 |
| goal_kick_blue | goal_kick | json | OK | 0 | 3/3 | 50 | 846 |
| goal_kick_blue | goal_kick | text | OK | 0 | 3/3 | 92 | 454 |
| corner_kick_in_red | corner_kick_in | json | OK | 0 | 3/3 | 50 | 948 |
| corner_kick_in_red | corner_kick_in | text | OK | 0 | 3/3 | 92 | 457 |
| 2vs1_attack | playing | json | OK | 0 | 3/2 | 35 | 938 |
| 2vs1_attack | playing | text | OK | 0 | 2/2 | 79 | 342 |
| 1vs1_defend | playing | json | OK | 0 | 0/1 | 30 | 904 |
| 1vs1_defend | playing | text | OK | 0 | 1/1 | 74 | 252 |
| 3vs2_extra_blue | playing | json | OK | 0 | 3/3 | 45 | 964 |
| 3vs2_extra_blue | playing | text | OK | 0 | 3/3 | 88 | 313 |
| red_deep_attack | playing | json | OK | 0 | 3/3 | 50 | 928 |
| red_deep_attack | playing | text | OK | 0 | 3/3 | 92 | 432 |
| midfield_scramble | playing | json | OK | 0 | 3/3 | 50 | 711 |
| midfield_scramble | playing | text | OK | 0 | 3/3 | 92 | 441 |
| ball_deep_own_zone | playing | json | OK | 0 | 3/3 | 50 | 827 |
| ball_deep_own_zone | playing | text | OK | 0 | 3/3 | 92 | 438 |
| kickoff_after_goal | kickoff | json | OK | 0 | 3/3 | 50 | 842 |
| kickoff_after_goal | kickoff | text | OK | 0 | 3/3 | 92 | 462 |
| wide_spacing_attack | playing | json | OK | 0 | 3/3 | 50 | 935 |
| wide_spacing_attack | playing | text | OK | 0 | 3/3 | 92 | 438 |
| no_blue_near_ball | playing | json | OK | 0 | 3/3 | 50 | 810 |
| no_blue_near_ball | playing | text | OK | 0 | 3/3 | 92 | 440 |
| high_line_press | playing | json | OK | 0 | 3/3 | 50 | 965 |
| high_line_press | playing | text | OK | 0 | 3/3 | 92 | 451 |

## Summary

**JSON:** 20/20 parse OK, 18/20 full coverage, latency p50 928ms, mean user-prompt tokens 48
**TEXT:** 20/20 parse OK, 20/20 full coverage, latency p50 443ms, mean user-prompt tokens 90

## Failures (raw responses)

