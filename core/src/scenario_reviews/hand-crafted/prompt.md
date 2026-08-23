You are acting as an expert reviewer (Annotator 1) evaluating 17 RoboCup-HSL soccer scenarios for behavior optimization. 

### Task
Evaluate all 17 provided scenarios based strictly on three criteria:
1. **Tactical Correctness (1-5):** Is the tactical response logical and effective given the match state described in Expert/Oracle?
   - 1 = Horrible / Completely wrong tactic
   - 5 = Optimal / Perfect tactical response
2. **Position Reachability (Yes/No):** Are the target coordinates realistically reachable by the robots on a standard field setup without invalid teleports or impossible constraints?
   - "Yes" or "No"
3. **Strategy Clarity (1-5):** Is the strategy clearly communicated and unambiguously translated between Expert Description, Oracle Actions, and Output to Bridge?
   - 1 = Very ambiguous / Confusing
   - 5 = Completely clear and concise

---

### Input Scenarios
```json
{
  {
    "scenario_name": "2vs2_default",
    "mode": "2vs2",
    "tactical_situation": "Red has possession and is attacking — blue_1 and blue_2 are clustered and out of shape",
    "entities": {
      "soccer_ball": {"x": -0.5, "y": 0.5},
      "blue_1": {"x": -1.8, "y": 0.2},
      "blue_2": {"x": -1.5, "y": -0.2},
      "red_1": {"x": -0.4, "y": 0.6},
      "red_2": {"x": 1.0, "y": 1.0}
    }
  },
  {
    "scenario_name": "2vs2_goalie_pass",
    "mode": "2vs2",
    "tactical_situation": "Goalie has the ball in front of it in the goal area — must become active and pass out to blue_2, who re-kicks immediately toward the uncovered red goal",
    "entities": {
      "soccer_ball": {"x": -2.94, "y": 0.19},
      "blue_1": {"x": -3.4, "y": 0.0},
      "blue_2": {"x": -1.0, "y": 1.0},
      "red_1": {"x": -1.2, "y": -0.8},
      "red_2": {"x": 0.3, "y": 0.4}
    }
  },
  {
    "scenario_name": "3vs3_attack_center",
    "mode": "3vs3",
    "tactical_situation": "Blue attacking through the center \u2014 red defenders pulled wide, goalie off-center",
    "entities": {
      "soccer_ball": {"x": 2.2, "y": 0.3},
      "blue_1": {"x": -4.2, "y": 0.0},
      "blue_2": {"x": -0.5, "y": 1.2},
      "blue_3": {"x": -0.5, "y": -1.2},
      "red_1": {"x": 4.2, "y": 0.5},
      "red_2": {"x": 2.8, "y": 2.2},
      "red_3": {"x": 2.8, "y": -2.2}
    }
  },
  {
    "scenario_name": "3vs3_attack_wing",
    "mode": "3vs3",
    "tactical_situation": "Ball on right wing near opponent goal \u2014 crossing opportunity",
    "entities": {
      "soccer_ball": {"x": 3.0, "y": 2.0},
      "blue_1": {"x": -4.0, "y": 0.0},
      "blue_2": {"x": -0.5, "y": 0.0},
      "blue_3": {"x": -4.0, "y": 0.3},
      "red_1": {"x": 4.2, "y": -0.5},
      "red_2": {"x": 1.0, "y": 0.5},
      "red_3": {"x": 2.0, "y": -1.5}
    }
  },
  {
    "scenario_name": "3vs3_contain_delay",
    "mode": "3vs3",
    "tactical_situation": "Red has possession, blue outnumbered — contain and delay",
    "entities": {
      "soccer_ball": {"x": -0.9, "y": 0.45},
      "blue_1": {"x": -3.5, "y": 0.3},
      "blue_2": {"x": -2.0, "y": 0.5},
      "blue_3": {"x": -1.5, "y": -0.8},
      "red_1": {"x": -0.8, "y": 0.5},
      "red_2": {"x": 0.3, "y": 0.0},
      "red_3": {"x": 0.5, "y": -0.3}
    }
  },
  {
    "scenario_name": "3vs3_deep_cross",
    "mode": "3vs3",
    "tactical_situation": "Red delivers a deep cross from the right wing toward the far post — blue must defend the two-man goal-mouth bracket (short post + long post guard)",
    "entities": {
      "soccer_ball": {"x": 3.5, "y": -2.2},
      "blue_1": {"x": -4.0, "y": 0.0},
      "blue_2": {"x": -3.5, "y": 0.7},
      "blue_3": {"x": -3.5, "y": -0.7},
      "red_1": {"x": 3.5, "y": -2.2},
      "red_2": {"x": -2.0, "y": 0.9},
      "red_3": {"x": -1.5, "y": -0.9}
    }
  },
  {
    "scenario_name": "3vs3_def_transition",
    "mode": "3vs3",
    "tactical_situation": "Lost ball in opponent half \u2014 recovery and counter-press",
    "entities": {
      "soccer_ball": {"x": 2.2, "y": 0.0},
      "blue_1": {"x": -3.6, "y": 0.3},
      "blue_2": {"x": -0.5, "y": -0.3},
      "blue_3": {"x": -1.0, "y": 0.2},
      "red_1": {"x": 2.4, "y": 0.0},
      "red_2": {"x": 0.0, "y": 0.3},
      "red_3": {"x": -0.9, "y": 0.9}
    }
  },
  {
    "scene_type": "3vs3",
    "label": "default",
    "entities": {
      "soccer_ball": {"x": 0.0, "y": 0.0},
      "blue_1": {"x": -4.2, "y": 0.0},
      "blue_2": {"x": -1.5, "y": 1.5},
      "blue_3": {"x": -1.5, "y": -1.5},
      "red_1": {"x": 4.2, "y": 0.0},
      "red_2": {"x": 1.5, "y": 1.5},
      "red_3": {"x": 1.5, "y": -1.5}
    }
  },
  {
    "scenario_name": "3vs3_defensive_crisis",
    "mode": "3vs3",
    "tactical_situation": "Ball deep in own zone, under pressure — emergency clear",
    "entities": {
      "soccer_ball": {"x": -3.1, "y": 0.45},
      "blue_1": {"x": -4.0, "y": 0.2},
      "blue_2": {"x": -2.5, "y": 0.5},
      "blue_3": {"x": -1.5, "y": -0.3},
      "red_1": {"x": -3.1, "y": 0.55},
      "red_2": {"x": -0.7, "y": 0.0},
      "red_3": {"x": -1.0, "y": 0.8}
    }
  },
  {
    "scenario_name": "3vs3_fast_counter",
    "mode": "3vs3",
    "tactical_situation": "Won ball in own half, open space ahead — transition opportunity",
    "entities": {
      "soccer_ball": {"x": -1.8, "y": -0.1},
      "blue_1": {"x": -1.6, "y": 0.1},
      "blue_2": {"x": -3.5, "y": 0.5},
      "blue_3": {"x": -4.0, "y": -0.2},
      "red_1": {"x": 0.5, "y": -0.3},
      "red_2": {"x": 2.0, "y": 1.0},
      "red_3": {"x": 3.0, "y": -0.8}
    }
  },
  {
    "scenario_name": "3vs3_goalie_distribution",
    "mode": "3vs3",
    "tactical_situation": "Goalie has the ball at the edge of the box \u2014 must distribute to an open teammate before red presses; blue_2 is open on the left wing, blue_3 is marked in the center",
    "entities": {
      "soccer_ball": {"x": -3.5, "y": 0.0},
      "blue_1": {"x": -3.5, "y": 0.0},
      "blue_2": {"x": -1.0, "y": 2.0},
      "blue_3": {"x": -0.5, "y": 0.0},
      "red_1": {"x": -2.0, "y": 0.5},
      "red_2": {"x": 0.5, "y": 0.5},
      "red_3": {"x": 2.0, "y": 0.0}
    }
  },
  {
    "scenario_name": "3vs3_high_line",
    "mode": "3vs3",
    "tactical_situation": "Red threatening with through ball — high line decision",
    "entities": {
      "soccer_ball": {"x": -2.7, "y": 2.25},
      "blue_1": {"x": -3.0, "y": 1.5},
      "blue_2": {"x": -3.0, "y": 0.0},
      "blue_3": {"x": -3.0, "y": -1.5},
      "red_1": {"x": -2.5, "y": 2.0},
      "red_2": {"x": -1.0, "y": 2.5},
      "red_3": {"x": 0.5, "y": 0.0}
    }
  },
  {
    "scenario_name": "3vs3_long_shot",
    "mode": "3vs3",
    "tactical_situation": "Ball near box, goalie slightly off-center \u2014 shot selection",
    "entities": {
      "soccer_ball": {"x": 3.15, "y": 1.35},
      "blue_1": {"x": -4.0, "y": 0.0},
      "blue_2": {"x": -0.5, "y": 0.0},
      "blue_3": {"x": -4.0, "y": -0.3},
      "red_1": {"x": 4.2, "y": 0.5},
      "red_2": {"x": 2.5, "y": 1.5},
      "red_3": {"x": 3.5, "y": -0.5}
    }
  },
  {
    "scenario_name": "3vs3_overload",
    "mode": "3vs3",
    "tactical_situation": "2-on-1 overload \u2014 blue_1 and blue_2 attack red_1 alone near the opponent goal; red_2 and red_3 are out of position on the far wing",
    "entities": {
      "soccer_ball": {"x": 2.5, "y": 0.0},
      "blue_1": {"x": -4.0, "y": 0.0},
      "blue_2": {"x": -0.5, "y": 0.5},
      "blue_3": {"x": -4.0, "y": 0.0},
      "red_1": {"x": 3.5, "y": 0.0},
      "red_2": {"x": 1.0, "y": 2.5},
      "red_3": {"x": 0.5, "y": -2.5}
    }
  },
  {
    "scenario_name": "3vs3_possession_lost",
    "mode": "3vs3",
    "tactical_situation": "Blue loses possession in the opponent half \u2014 red counters; blue must transition from attack to defense immediately",
    "entities": {
      "soccer_ball": {"x": 1.0, "y": 0.5},
      "blue_1": {"x": -4.0, "y": 0.0},
      "blue_2": {"x": -0.5, "y": 1.5},
      "blue_3": {"x": -1.0, "y": -1.0},
      "red_1": {"x": 1.5, "y": 0.5},
      "red_2": {"x": 0.0, "y": 2.0},
      "red_3": {"x": -1.0, "y": -1.5}
    }
  },
  {
    "scenario_name": "3vs3_pressing_trap",
    "mode": "3vs3",
    "tactical_situation": "Red team pressing high, no clear outlet \u2014 breaking pressure",
    "entities": {
      "soccer_ball": {"x": 0.45, "y": 0.45},
      "blue_1": {"x": -0.5, "y": 0.3},
      "blue_2": {"x": -1.0, "y": 0.8},
      "blue_3": {"x": -2.0, "y": -0.5},
      "red_1": {"x": 0.8, "y": 0.5},
      "red_2": {"x": 0.2, "y": -0.2},
      "red_3": {"x": -0.5, "y": 1.0}
    }
  },
  {
    "scenario_name": "3vs3_wing_switch",
    "mode": "3vs3",
    "tactical_situation": "Blue attack stalled on the left wing \u2014 red overloaded the left side; blue must switch play to the open right wing",
    "entities": {
      "soccer_ball": {"x": 1.5, "y": 2.2},
      "blue_1": {"x": -4.0, "y": 0.0},
      "blue_2": {"x": -0.5, "y": 2.0},
      "blue_3": {"x": 0.0, "y": 0.0},
      "red_1": {"x": 2.5, "y": 2.0},
      "red_2": {"x": 2.0, "y": 1.5},
      "red_3": {"x": 3.5, "y": 0.0}
    }
  }
}
```

---

### Output Format Requirements
Please respond ONLY with a single JSON block containing all scores formatted exactly as follows so it can be parsed programmatically:

```json
{
  "scenario_01: 2vs2_default": {
    "tactical_correctness": 5,
    "position_reachability": "Yes",
    "strategy_clarity": 4,
    "comment": "Brief reason..."
  },
  "scenario_02: 2vs2_goalie_pass": {
    "tactical_correctness": 1,
    "position_reachability": "No",
    "strategy_clarity": 3,
    "comment": "Brief reason..."
  }
}
```