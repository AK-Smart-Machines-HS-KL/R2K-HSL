# emp_regression-anti_restart_032

![field diagram](field_diagram.png)

## Source
- Original match: 3vs3_attack_center_strat_aggro_20260730_032026
- Umschalt type: restart — Set-piece: corner_kick_in
- Tag: regression-anti (red scored)
- Cluster: 1 similar fragments reduced to this representative

## Scope
Red won a restart deep in Blue's half — test whether Blue can recover defensively and prevent the concession.

## Expert (Analysis)
Ball at (-4.4, -0.9), deep in Blue's own half, near Blue's goal. Closest blue: blue_2 (1.1m). Closest red: red_1 (1.7m). Possession: BLUE. Blue has a numbers advantage near the ball (2 blue vs 1 red within 2m). Umschalt type: restart. Red scored — this was a defensive failure for Blue.

## Oracle (Strategy)
To escape the dangerous position: Blue has the ball deep in own half. The nearest blue (blue_2) clears the ball upfield immediately, another blue drops to cover the goal line, and the third blue moves to midfield to receive the clearance.

```
blue_2 kick
blue_3 move to (0.5, 0.9)
blue_1 cover the goal line at (-4.0, -0.9)
```

## Output to bridge

```
blue_2 kick
blue_3 move to (0.5, 0.9)
blue_1 move to (-4.0, -0.9)
```

## Qwen's decision at t_umschalt

```
{
  "assignments": {
    "blue_1": {
      "role": "goalie",
      "action": "Move",
      "x": -4.0,
      "y": -2.8
    },
    "blue_2": {
      "role": "attacker",
      "action": "Kick"
    },
    "blue_3": {
      "role": "defender",
      "action": "Move",
      "x": 1.5,
      "y": -0.8
    }
  }
}
```

## Regression metrics
- Score before: -6.76
- Score after (t+5s): 0.00
- Score delta: +6.76 (positive = good for blue)
- Red behavior: red_midfield
- Match result: red scored (goal #2)

## Score delta

![score chart](score_chart.png)

## Test specification
- Duration: 8s
- Expected outcome: score decreases (red advantage)
- Prediction: ON (matches production)
- Pass criterion: score delta direction matches expected
