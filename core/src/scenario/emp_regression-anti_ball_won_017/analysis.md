# emp_regression-anti_ball_won_017

![field diagram](field_diagram.png)

## Source
- Original match: 3vs3_attack_center_strat_aggro_20260730_035315
- Umschalt type: ball_won — Red won possession
- Tag: regression-anti (red scored)
- Cluster: 1 similar fragments reduced to this representative

## Scope
Red won a ball_won deep in Blue's half — test whether Blue can recover defensively and prevent the concession.

## Expert (Analysis)
Ball at (-4.5, -0.0), deep in Blue's own half, near Blue's goal. Closest blue: blue_2 (1.5m). Closest red: red_3 (1.3m). Possession: RED. Blue goalie (blue_1 at (-4.0, -3.0)) is 3.1m from the ball — far from the action. Umschalt type: ball_won. Red scored — this was a defensive failure for Blue.

## Oracle (Strategy)
To recover defensive shape: Red has possession deep in Blue's half but the nearest red is 1.3m away. The nearest blue (blue_2) challenges for the ball, another blue covers the goal line, and the third blue marks the passing lane.

```
blue_2 move to (-4.5, -0.0)
blue_3 move to (-3.5, -0.0)
blue_1 cover the goal line at (-4.0, -0.0)
```

## Output to bridge

```
blue_2 move to (-4.5, -0.0)
blue_3 move to (-3.5, -0.0)
blue_1 move to (-4.0, -0.0)
```

## Qwen's decision at t_umschalt

```
{
  "assignments": {
    "blue_1": {
      "role": "goalie",
      "action": "Move",
      "x": -4.0,
      "y": -0.2
    },
    "blue_2": {
      "role": "attacker",
      "action": "Kick"
    },
    "blue_3": {
      "role": "defender",
      "action": "Move",
      "x": 1.3,
      "y": -1.4
    }
  }
}
```

## Regression metrics
- Score before: -6.72
- Score after (t+5s): 0.00
- Score delta: +6.72 (positive = good for blue)
- Red behavior: red_midfield
- Match result: red scored (goal #1)

## Score delta

![score chart](score_chart.png)

## Test specification
- Duration: 8s
- Expected outcome: score decreases (red advantage)
- Prediction: ON (matches production)
- Pass criterion: score delta direction matches expected
