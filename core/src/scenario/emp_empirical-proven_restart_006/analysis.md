# emp_empirical-proven_restart_006

![field diagram](field_diagram.png)

## Source
- Original match: 2vs2_default_strat_aggro_20260731_194737
- Umschalt type: restart — Set-piece: ball_out
- Tag: empirical-proven (blue scored)
- Cluster: 1 similar fragments reduced to this representative

## Scope
Blue won a restart deep in the opponent half — test whether Blue capitalizes on the turnover and scores.

## Expert (Analysis)
Ball at (4.5, 0.9), deep in the opponent half. Closest blue: blue_2 (1.8m). Closest red: red_2 (1.4m). Possession: RED. Umschalt type: restart. Blue scored — this was a successful transition.

## Oracle (Strategy)
To regain possession deep in the opponent half: the nearest blue (blue_2) presses the ball carrier, another blue cuts off the passing lane, and the goalie holds the goal line.

```
blue_2 move to (4.5, 0.9)
blue_3 move to (3.0, -0.9)
blue_1 cover the goal line at (-4.0, 0.9)
```

## Output to bridge

```
blue_2 move to (4.5, 0.9)
blue_3 move to (3.0, -0.9)
blue_1 move to (-4.0, 0.9)
```

## Qwen's decision at t_umschalt

```
{
  "assignments": {
    "blue_1": {
      "role": "goalie",
      "action": "Move",
      "x": -3.2,
      "y": 1.9
    },
    "blue_2": {
      "role": "attacker",
      "action": "Kick"
    },
    "blue_3": {
      "role": "defender",
      "action": "Move",
      "x": -0.5,
      "y": 1.9
    }
  }
}
```

## Regression metrics
- Score before: 6.79
- Score after (t+5s): 0.00
- Score delta: -6.79 (negative = bad for blue)
- Red behavior: red_midfield
- Match result: blue scored (goal #1)

## Score delta

![score chart](score_chart.png)

## Test specification
- Duration: 8s
- Expected outcome: score increases (blue advantage)
- Prediction: ON (matches production)
- Pass criterion: score delta direction matches expected
