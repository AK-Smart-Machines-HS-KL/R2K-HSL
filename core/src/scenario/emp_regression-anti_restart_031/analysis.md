# emp_regression-anti_restart_031

![field diagram](field_diagram.png)

## Source
- Original match: 3vs3_attack_center_strat_aggro_20260729_230229
- Umschalt type: restart — Set-piece: corner_kick_in
- Tag: regression-anti (red scored)
- Cluster: 2 similar fragments reduced to this representative

## Scope
Red won a restart deep in Blue's half — test whether Blue can recover defensively and prevent the concession.

## Expert (Analysis)
Ball at (-4.5, 1.0), deep in Blue's own half, near Blue's goal. Closest blue: blue_3 (0.5m). Closest red: red_2 (1.7m). Possession: BLUE. Blue has a numbers advantage near the ball (2 blue vs 1 red within 2m). Umschalt type: restart. Red scored — this was a defensive failure for Blue.

## Oracle (Strategy)
To escape the dangerous position: Blue has the ball deep in own half. The nearest blue (blue_3) clears the ball upfield immediately, another blue drops to cover the goal line, and the third blue moves to midfield to receive the clearance.

```
blue_3 kick
blue_2 move to (0.5, -1.0)
blue_1 cover the goal line at (-4.0, 0.9)
```

## Output to bridge

```
blue_3 kick
blue_2 move to (0.5, -1.0)
blue_1 move to (-4.0, 0.9)
```

## Qwen's decision at t_umschalt

```
{
  "assignments": {
    "blue_1": {
      "role": "goalie",
      "action": "Move",
      "x": -4.0,
      "y": 2.8
    },
    "blue_2": {
      "role": "attacker",
      "action": "Kick"
    },
    "blue_3": {
      "role": "defender",
      "action": "Move",
      "x": -4.5,
      "y": 0.0
    }
  }
}
```

## Regression metrics
- Score before: -4.82
- Score after (t+5s): 0.00
- Score delta: +4.82 (positive = good for blue)
- Red behavior: red_midfield
- Match result: red scored (goal #1)

## Score delta

![score chart](score_chart.png)

## Test specification
- Duration: 8s
- Expected outcome: score decreases (red advantage)
- Prediction: ON (matches production)
- Pass criterion: score delta direction matches expected
