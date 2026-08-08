# emp_empirical-proven_cluster_005

![field diagram](field_diagram.png)

## Source
- Original match: 3vs3_attack_center_strat_aggro_20260729_231259
- Umschalt type: cluster — Blue bots clustered
- Tag: empirical-proven (blue scored)
- Cluster: 1 similar fragments reduced to this representative

## Scope
Blue won a cluster deep in the opponent half — test whether Blue capitalizes on the turnover and scores.

## Expert (Analysis)
Ball at (4.5, -0.3), deep in the opponent half. Closest blue: blue_2 (0.6m). Closest red: red_1 (0.4m). Possession: RED. Blue clustering: blue_1 and blue_3 are 0.4m apart — tactical congestion limiting options. Red has a numbers advantage near the ball (2 red vs 1 blue within 2m) — Blue is outnumbered defensively. Umschalt type: cluster. Blue scored — this was a successful transition.

## Oracle (Strategy)
To regain possession deep in the opponent half: the nearest blue (blue_2) presses the ball carrier, another blue cuts off the passing lane, and the goalie holds the goal line.

```
blue_2 move to (4.5, -0.3)
blue_3 move to (3.0, 0.3)
blue_1 cover the goal line at (-4.0, -0.3)
```

## Output to bridge

```
blue_2 move to (4.5, -0.3)
blue_3 move to (3.0, 0.3)
blue_1 move to (-4.0, -0.3)
```

## Qwen's decision at t_umschalt

```
{
  "assignments": {
    "blue_1": {
      "role": "goalie",
      "action": "Move",
      "x": -4.0,
      "y": 0.0
    },
    "blue_2": {
      "role": "attacker",
      "action": "Kick"
    },
    "blue_3": {
      "role": "defender",
      "action": "Move",
      "x": -1.5,
      "y": 0.0
    }
  }
}
```

## Regression metrics
- Score before: 4.75
- Score after (t+5s): 0.00
- Score delta: -4.75 (negative = bad for blue)
- Red behavior: red_deep
- Match result: blue scored (goal #2)

## Score delta

![score chart](score_chart.png)

## Test specification
- Duration: 8s
- Expected outcome: score increases (blue advantage)
- Prediction: ON (matches production)
- Pass criterion: score delta direction matches expected
