# emp_empirical-proven_clearance_004

![field diagram](field_diagram.png)

## Source
- Original match: 3vs3_attack_center_strat_aggro_20260729_223615
- Umschalt type: clearance — Ball cleared to opponent half
- Tag: empirical-proven (blue scored)
- Cluster: 3 similar fragments reduced to this representative

## Scope
Blue won a clearance deep in the opponent half — test whether Blue capitalizes on the turnover and scores.

## Expert (Analysis)
Ball at (4.4, -0.6), deep in the opponent half. Closest blue: blue_2 (0.9m). Closest red: red_1 (0.6m). Possession: RED. Red has a numbers advantage near the ball (2 red vs 1 blue within 2m) — Blue is outnumbered defensively. Umschalt type: clearance. Blue scored — this was a successful transition.

## Oracle (Strategy)
To regain possession deep in the opponent half: the nearest blue (blue_2) presses the ball carrier, another blue cuts off the passing lane, and the goalie holds the goal line.

```
blue_2 move to (4.4, -0.6)
blue_3 move to (2.9, 0.6)
blue_1 cover the goal line at (-4.0, -0.6)
```

## Output to bridge

```
blue_2 move to (4.4, -0.6)
blue_3 move to (2.9, 0.6)
blue_1 move to (-4.0, -0.6)
```

## Qwen's decision at t_umschalt

```
{
  "assignments": {
    "blue_1": {
      "role": "goalie",
      "action": "Move",
      "x": -4.0,
      "y": -0.4
    },
    "blue_2": {
      "role": "attacker",
      "action": "Kick"
    },
    "blue_3": {
      "role": "defender",
      "action": "Move",
      "x": 1.6,
      "y": -0.1
    }
  }
}
```

## Regression metrics
- Score before: 4.66
- Score after (t+5s): 0.00
- Score delta: -4.66 (negative = bad for blue)
- Red behavior: red_deep
- Match result: blue scored (goal #1)

## Score delta

![score chart](score_chart.png)

## Test specification
- Duration: 8s
- Expected outcome: score increases (blue advantage)
- Prediction: ON (matches production)
- Pass criterion: score delta direction matches expected
