# emp_regression-anti_ball_won_015

![field diagram](field_diagram.png)

## Source
- Original match: 3vs3_attack_center_strat_aggro_20260730_031208
- Umschalt type: ball_won — Red won possession
- Tag: regression-anti (red scored)
- Cluster: 1 similar fragments reduced to this representative

## Scope
Red won a ball_won deep in Blue's half — test whether Blue can recover defensively and prevent the concession.

## Expert (Analysis)
Ball at (-4.3, -0.2), deep in Blue's own half, near Blue's goal. Closest blue: blue_1 (4.1m). Closest red: red_1 (1.1m). Possession: RED. Red has a numbers advantage near the ball (1 red vs 0 blue within 2m) — Blue is outnumbered defensively. Blue goalie (blue_1 at (-1.2, -2.9)) is 4.1m from the ball — far from the action. Umschalt type: ball_won. Red scored — this was a defensive failure for Blue.

## Oracle (Strategy)
To recover defensive shape: Red has possession deep in Blue's half but the nearest red is 1.1m away. The nearest blue (blue_1) challenges for the ball, another blue covers the goal line, and the third blue marks the passing lane.

```
blue_1 move to (-4.3, -0.2)
blue_3 move to (-3.3, -0.1)
blue_2 cover the goal line at (-4.0, -0.2)
```

## Output to bridge

```
blue_1 move to (-4.3, -0.2)
blue_3 move to (-3.3, -0.1)
blue_2 move to (-4.0, -0.2)
```

## Qwen's decision at t_umschalt

```
{
  "assignments": {
    "blue_1": {
      "role": "goalie",
      "action": "Move",
      "x": -4.0,
      "y": -1.2
    },
    "blue_2": {
      "role": "attacker",
      "action": "Kick"
    },
    "blue_3": {
      "role": "defender",
      "action": "Move",
      "x": 1.4,
      "y": -0.5
    }
  }
}
```

## Regression metrics
- Score before: -6.52
- Score after (t+5s): -6.77
- Score delta: -0.25 (negative = bad for blue)
- Red behavior: red_midfield
- Match result: red scored (goal #1)

## Score delta

![score chart](score_chart.png)

## Test specification
- Duration: 8s
- Expected outcome: score decreases (red advantage)
- Prediction: ON (matches production)
- Pass criterion: score delta direction matches expected
