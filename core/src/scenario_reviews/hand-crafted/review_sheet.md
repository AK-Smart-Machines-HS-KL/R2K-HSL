# Review-Sheet: 17 Hand-crafted Scenarios (IAA Validation)

**Project:** R2K-HSL (RoboCup-HSL Team R-ZWEI KICKERS)  
**Goal:** Validation of the 17 manually created scenario descriptions to ensure a sound scientific basis and reduce single-annotator bias (inter-annotator agreement).

---

## 📌 Evaluation Criteria & Scales

Each scenario is evaluated based on the descriptions (**Expert**, **Oracle**, **Output to bridge**) according to the following three criteria:

1. **Tactical Correctness:**  
   *Scale:* `1` (completely incorrect) to `5` (optimal / completely correct)
2. **Position Reachability:**  
   *Scale:* `Yes` (reachable) / `No` (unreachable / unrealistic)
3. **Strategy Clarity:**  
   *Scale:* `1` (very unclear / contradictory) to `5` (very clear / unambiguous)

---

## 📊 Overview table: Overall assessment

> **Note to the reviewer:** Enter your ratings into the table. The columns for **GLM-5.2** will be added—using a blind process—only after you have completed your evaluation.

---

### Template:

| Scenario | Tactical Correctness (1-5) | Position Reachability (Yes/No) | Strategy Clarity (1-5) | Notes |
| :--- | :---: | :---: | :---: | :--- |
| **01. 2vs2_default** |  |  |  |  |
| **02. 2vs2_goalie_pass** |  |  |  |  |
| **03. 3vs3_attack_center** |  |  |  |  |
| **04. 3vs3_attack_wing** |  |  |  |  |
| **05. 3vs3_contain_delay** |  |  |  |  |
| **06. 3vs3_deep_cross** |  |  |  |  |
| **07. 3vs3_def_transition** |  |  |  |  |
| **08. 3vs3_default** |  |  |  |  |
| **09. 3vs3_defensive_crisis** |  |  |  |  |
| **10. 3vs3_fast_counter** |  |  |  |  |
| **11. 3vs3_goalie_distribution** |  |  |  |  |
| **12. 3vs3_high_line** |  |  |  |  |
| **13. 3vs3_long_shot** |  |  |  |  |
| **14. 3vs3_overload** |  |  |  |  |
| **15. 3vs3_possession_lost** |  |  |  |  |
| **16. 3vs3_pressing_trap** |  |  |  |  |
| **17. 3vs3_wing_switch** |  |  |  |  |

**Irregularities:**

---

### Jan:

| Scenario | Tactical Correctness (1-5) | Position Reachability (Yes/No) | Strategy Clarity (1-5) | Notes |
| :--- | :---: | :---: | :---: | :--- |
| **01. 2vs2_default** | 5 | Yes | 5 | - |
| **02. 2vs2_goalie_pass** | 5 | Yes | 5 | - |
| **03. 3vs3_attack_center** | 5 | Yes | 5 | - |
| **04. 3vs3_attack_wing** | 5 | Yes | 5 | - |
| **05. 3vs3_contain_delay** | 5 | Yes | 5 | - |
| **06. 3vs3_deep_cross** | 5 | Yes | 5 | - |
| **07. 3vs3_def_transition** | 5 | Yes | 5 | - |
| **08. 3vs3_default** | 5 | Yes | 5 | - |
| **09. 3vs3_defensive_crisis** | 5 | Yes | 5 | - |
| **10. 3vs3_fast_counter** | 4 | Yes | 3 | blue_1 should wait for better positioning of blue_2 |
| **11. 3vs3_goalie_distribution** | 5 | Yes | 5 | - |
| **12. 3vs3_high_line** | 3 | Yes | 5 | blue_1s target position opens the goal |
| **13. 3vs3_long_shot** | 4 | Yes | 5 | fairly offensive and risky strategy |
| **14. 3vs3_overload** | 3 | Yes | 4 | underestimates red_2 and red_3 |
| **15. 3vs3_possession_lost** | 5 | Yes | 5 | - |
| **16. 3vs3_pressing_trap** | 5 | Yes | 5 | - |
| **17. 3vs3_wing_switch** | 5 | Yes | 5 | - |

**Irregularities:**
* Scenario 01: "blue_2 challenges red_1 for the ball", distance = 1.2m
* Scenario 02: "blue_2 is on the wing", which wing?**
* Scenario 03: "blue_2 advances toward the ball", distance = 2.8m
* Scenario 04: "blue_2 advances upfield toward the ball", distance = 4.0m  
-> Expert says to far, oracle still advances towards the ball
* Scenario 06: "red_2 attacks the short post, red_3 attacks the long post", Expert mixed up posts: red_2 attacks long post, red_3 attacks short post
* Scenario 08: "blue_2 advances toward the ball", distance = 2.1m  
faulty scenario.json
* Scenario 13: "blue_2 advances toward the ball", distance = 3.9m
* Scenario 14: "blue_2 advances toward the ball", distance = 3.0m  
"blue has a numbers advantage", blue_2 is alone in midfield
* Scenario 17: "The right wing (Y<0)", redundant

---

## 📝 Detailed assessment of the 17 scenarios

### Scenario 01: 2vs2_default
* **Expert Description:** Ball at (-0.5, 0.5) near midfield. red_1 (-0.4, 0.6) has the ball — 0.1m away. blue_2 (-1.5, -0.2) is 1.2m from the ball, blue_1 (-1.8, 0.2) is 1.3m. Red has possession. blue bots are clustered 0.5m apart — must separate.

* **Oracle Actions:** blue_2 challenges red_1 for the ball. blue_1 drops to the goal line to block the shot lane. Prevent a quick red shot on goal.

```
blue_1 cover the goal line at (-4.0, 0.5)
blue_2 move to (-0.5, 0.5)
```

* **Output to bridge:**
```
blue_1 move to (-4.0, 0.5)
blue_2 move to (-0.5, 0.5)
```

#### ✍️ Evaluation (GLM-5.2):
* **Tactical Correctness (1–5): 4** 
* **Position Reachability (Yes/No): Yes** 
* **Strategy Clarity (1–5): 4** 
* **Comment / Justification: Coherent attacking situation; red in possession with blue clustered out of shape. Positions within field bounds. Tactic implied but not explicitly described.**

---

### Scenario 02: 2vs2_goalie_pass
* **Expert Description:** Ball at (-2.9, 0.2) near blue's goal. blue_1 (-3.4, 0.0) is the goalie, 0.5m from the ball — has possession. blue_2 (-1.0, 1.0) is on the wing, 2.1m away. red_1 (-1.2, -0.8) is 2.0m away. Goalie distribution opportunity — red is too far to press immediately.

* **Oracle Actions:** blue_1 (goalie) has the ball and distributes to blue_2 on the wing. blue_2 moves to a receiving position. Transition from defense to attack.

```
blue_1 kick
blue_2 move to (-0.5, 1.0)
```

* **Output to bridge:**
```
blue_1 kick
blue_2 move to (-0.5, 1.0)
```

#### ✍️ Evaluation (GLM-5.2):
* **Tactical Correctness (1–5): 5** 
* **Position Reachability (Yes/No): Yes** 
* **Strategy Clarity (1–5): 5** 
* **Comment / Justification: Goalie distribution to open blue_2 then re-kick toward uncovered red goal is optimal and clearly communicated. All coordinates reachable.**

---

### Scenario 03: 3vs3_attack_center
* **Expert Description:** Ball at (2.2, 0.3) in red's half. red_1 (4.2, 0.5) and red_2 (2.8, 2.2) are both 2.0m from the ball — marginally closer than blue_2 (-0.5, 1.2) at 2.8m, so red can reach the ball first. blue_3 (-0.5, -1.2) is 3.1m. Red's defense is stretched wide, center is open. Red goalie off-center at Y=0.5.

* **Oracle Actions:** blue_2 advances toward the ball to close the distance and set up a possession challenge. blue_3 shifts toward center to cover the passing lane. blue_1 tracks ball Y on the goal line.

```
blue_1 cover the goal line at (-4.0, 0.3)
blue_2 move to (1.8, 0.3)
blue_3 move to (-0.5, -0.5)
```

* **Output to bridge:**
```
blue_1 move to (-4.0, 0.3)
blue_2 move to (1.8, 0.3)
blue_3 move to (-0.5, -0.5)
```

#### ✍️ Evaluation (GLM-5.2):
* **Tactical Correctness (1–5): 2** 
* **Position Reachability (Yes/No): Yes** 
* **Strategy Clarity (1–5): 3** 
* **Comment / Justification: Described as blue attacking through center, but blue_2 and blue_3 are at x=-0.5 far behind the ball at x=2.2. Attackers not positioned to support a central attack — inconsistent with the described situation.**

---

### Scenario 04: 3vs3_attack_wing
* **Expert Description:** Ball at (3.0, 2.0) on the left wing, deep in red's half. red_2 (1.0, 0.5) is closest at 2.5m. blue_2 (-0.5, 0.0) is 4.0m away — too far to challenge this cycle. blue_1 and blue_3 are on the goal line. The shooting angle from the wing is narrow.

* **Oracle Actions:** blue_2 advances upfield toward the ball on the wing. blue_3 shifts to cover the center. blue_1 holds the goal line. Close distance before red can organize.

```
blue_1 cover the goal line at (-4.0, 0.9)
blue_2 move to (2.7, 1.8)
blue_3 move to (-0.5, 0.0)
```

* **Output to bridge:**
```
blue_1 move to (-4.0, 0.9)
blue_2 move to (2.7, 1.8)
blue_3 move to (-0.5, 0.0)
```

#### ✍️ Evaluation (GLM-5.2):
* **Tactical Correctness (1–5): 2** 
* **Position Reachability (Yes/No): Yes** 
* **Strategy Clarity (1–5): 3** 
* **Comment / Justification: Ball at (3.0, 2.0) for a crossing opportunity, but no blue outfield player is near the ball to deliver or receive a cross. Tactical setup contradicts the described situation.**

---

### Scenario 05: 3vs3_contain_delay
* **Expert Description:** Ball at (-0.9, 0.5) at midfield. red_1 (-0.8, 0.5) has the ball — 0.1m away. blue_2 (-2.0, 0.5) is 1.1m from the ball, blue_3 (-1.5, -0.8) is 1.4m. Red has possession and is pressing through the center. blue must contain without overcommitting.

* **Oracle Actions:** blue_2 presses red_1 who has the ball at midfield. blue_3 covers the passing lane to delay the attack. blue_1 holds the goal line. Contain without overcommitting.

```
blue_1 cover the goal line at (-4.0, 0.5)
blue_2 move to (-1.5, 0.5)
blue_3 move to (-1.0, -0.5)
```

* **Output to bridge:**
```
blue_1 move to (-4.0, 0.5)
blue_2 move to (-1.5, 0.5)
blue_3 move to (-1.0, -0.5)
```

#### ✍️ Evaluation (GLM-5.2):
* **Tactical Correctness (1–5): 4** 
* **Position Reachability (Yes/No): Yes** 
* **Strategy Clarity (1–5): 4** 
* **Comment / Justification: Contain-and-delay tactic is logical for blue defending deep. Slight mismatch: described as 'blue outnumbered' but it is 3v3; locally may be valid. Positions all reachable.**

---

### Scenario 06: 3vs3_deep_cross
* **Expert Description:** Ball at (3.5, -2.2) at the corner. red_1 is on the ball — about to cross. red_2 (-2.0, 0.9) attacks the short post, red_3 (-1.5, -0.9) attacks the long post. blue_2 (-3.5, 0.7) and blue_3 (-3.5, -0.7) are goal-side of their markers. blue_1 (-4.0, 0.0) is on the goal line. Defensive crisis — the cross is incoming.

* **Oracle Actions:** red_1 has the ball at the corner and is about to cross. blue_2 and blue_3 hold their goal-side positions marking red_2 and red_3. blue_1 tracks the ball Y on the line. Defend the bracket — do not chase the ball.

```
blue_1 cover the goal line at (-4.0, -0.9)
blue_2 hold position
blue_3 hold position
```

* **Output to bridge:**
```
blue_1 move to (-4.0, -0.9)
blue_2 hold position
blue_3 hold position
```

#### ✍️ Evaluation (GLM-5.2):
* **Tactical Correctness (1–5): 5** 
* **Position Reachability (Yes/No): Yes** 
* **Strategy Clarity (1–5): 5** 
* **Comment / Justification: Red delivers cross from deep right; blue brackets the goal mouth with short/long post guards. Excellent tactical framing and clear coordinate setup.**

---

### Scenario 07: 3vs3_def_transition
* **Expert Description:** Ball at (2.2, 0.0) in red's half. red_1 (2.4, 0.0) has the ball — 0.2m away. blue_2 (-0.5, -0.3) is 2.7m away, blue_3 (-1.0, 0.2) is 3.2m. Both blue bots are caught upfield. blue_1 (-3.6, 0.3) is the goalie, 5.8m from play. Defensive transition — blue must sprint back.

* **Oracle Actions:** blue lost possession — red_1 has the ball. blue_2 and blue_3 must drop back behind the ball to cover the goal. blue_1 holds the goal line. Transition from attack to defense.

```
blue_1 cover the goal line at (-4.0, 0.0)
blue_2 move to (-2.0, -0.3)
blue_3 move to (-1.5, 0.2)
```

* **Output to bridge:**
```
blue_1 move to (-4.0, 0.0)
blue_2 move to (-2.0, -0.3)
blue_3 move to (-1.5, 0.2)
```

#### ✍️ Evaluation (GLM-5.2):
* **Tactical Correctness (1–5): 3** 
* **Position Reachability (Yes/No): Yes** 
* **Strategy Clarity (1–5): 4** 
* **Comment / Justification: Counter-press after losing the ball in opponent half is sound in principle, but all blue robots are in their own half while the ball is at x=2.2 — unrealistic that no blue player is near the lost-ball zone to press.**

---

### Scenario 08: 3vs3_default
* **Expert Description:** Standard 3vs3 kickoff. Ball at center (0.0, 0.0). Both teams in their own half, equidistant from the ball. blue_2 (-1.5, 1.5) and blue_3 (-1.5, -1.5) are 2.1m from the ball. red_2 (1.5, 1.5) and red_3 (1.5, -1.5) mirror. Even setup — contest at midfield.

* **Oracle Actions:** Standard kickoff. blue_2 advances toward the ball at center. blue_3 holds midfield. blue_1 on the goal line. Contest possession at midfield.

```
blue_1 cover the goal line at (-4.0, 0.0)
blue_2 move to (-0.3, 0.3)
blue_3 move to (-0.5, -0.5)
```

* **Output to bridge:**
```
blue_1 move to (-4.0, 0.0)
blue_2 move to (-0.3, 0.3)
blue_3 move to (-0.5, -0.5)
```

#### ✍️ Evaluation (GLM-5.2):
* **Tactical Correctness (1–5): 3** 
* **Position Reachability (Yes/No): Yes** 
* **Strategy Clarity (1–5): 2** 
* **Comment / Justification: Symmetric kickoff default with no described tactical situation. Uses a different JSON schema (scene_type/label instead of scenario_name/mode/tactical_situation), making it inconsistent and ambiguous relative to the other entries.**

---

### Scenario 09: 3vs3_defensive_crisis
* **Expert Description:** Ball at (-3.1, 0.5) — 1.4m from blue's goal. red_1 (-3.1, 0.6) is on the ball — 0.1m away. blue_1 (-4.0, 0.2) is the goalie, 0.9m from the ball. blue_2 (-2.5, 0.5) is 0.6m from the ball. red is about to shoot — immediate crisis.

* **Oracle Actions:** red_1 has the ball 0.1m away — imminent shot. blue_2 challenges the ball carrier. blue_1 stays on the goal line to block the shot. blue_3 drops to cover the deflection. Prevent a goal.

```
blue_1 cover the goal line at (-4.0, 0.5)
blue_2 move to (-3.0, 0.5)
blue_3 move to (-2.0, -0.3)
```

* **Output to bridge:**
```
blue_1 move to (-4.0, 0.5)
blue_2 move to (-3.0, 0.5)
blue_3 move to (-2.0, -0.3)
```

#### ✍️ Evaluation (GLM-5.2):
* **Tactical Correctness (1–5): 4** 
* **Position Reachability (Yes/No): Yes** 
* **Strategy Clarity (1–5): 4** 
* **Comment / Justification: Ball deep in own zone under pressure with red_1 contesting — emergency clear is the correct response. Goalie and defenders positioned logically.**

---

### Scenario 10: 3vs3_fast_counter
* **Expert Description:** Ball at (-1.8, -0.1) in blue's half. blue_1 (-1.6, 0.1) is on the ball — 0.3m away — has possession. red_1 (0.5, -0.3) is 2.3m away. red_2 and red_3 are far upfield. blue_1 has free time — counter-attack opportunity.

* **Oracle Actions:** blue_1 has the ball and a counter-attack opportunity — red is far away. blue_1 kicks the ball forward toward the opponent half. blue_2 supports the counter. blue_3 holds the goal line. Exploit the free time.

```
blue_1 kick
blue_2 move to (-2.0, 0.5)
blue_3 cover the goal line at (-4.0, -0.1)
```

* **Output to bridge:**
```
blue_1 kick
blue_2 move to (-2.0, 0.5)
blue_3 move to (-4.0, -0.1)
```

#### ✍️ Evaluation (GLM-5.2):
* **Tactical Correctness (1–5): 5** 
* **Position Reachability (Yes/No): Yes** 
* **Strategy Clarity (1–5): 5** 
* **Comment / Justification: Blue_1 next to the ball after winning possession with open space ahead and red pushed up — textbook transition counter. Clear and reachable.**

---

### Scenario 11: 3vs3_fast_counter
* **Expert Description:** Ball at (-3.5, 0.0) — 1m from blue's goal. blue_1 (-3.5, 0.0) is the goalie, on the ball — has possession. red_1 (-2.0, 0.5) is pressing, 1.6m away. blue_2 (-1.0, 2.0) is unmarked on the left wing. blue_3 (-0.5, 0.0) is in midfield. Goalie must distribute before red_1 arrives.

* **Oracle Actions:** blue_1 (goalie) has the ball. red_1 is pressing, 1.6m away. blue_1 distributes to blue_2 on the left wing — the open lane. blue_3 moves to a secondary outlet. Quick transition from defense to attack.

```
blue_1 kick
blue_2 move to (-0.5, 2.0)
blue_3 move to (0.0, 0.5)
```

* **Output to bridge:**
```
blue_1 kick
blue_2 move to (-0.5, 2.0)
blue_3 move to (0.0, 0.5)
```

#### ✍️ Evaluation (GLM-5.2):
* **Tactical Correctness (1–5): 5** 
* **Position Reachability (Yes/No): Yes** 
* **Strategy Clarity (1–5): 5** 
* **Comment / Justification: Goalie at the ball with blue_2 open on the wing and blue_3 marked centrally — distribution to the open wing is optimal and unambiguous.**

---

### Scenario 12: 3vs3_high_line
* **Expert Description:** Ball at (-2.7, 2.2) — deep in blue's half, left wing. red_1 (-2.5, 2.0) is on the ball — 0.3m away. blue_1 (-3.0, 1.5) is 0.8m from the ball but too high in Y. blue_2 (-3.0, 0.0) covers center. blue_3 (-3.0, -1.5) is on the far post. red_2 (-1.0, 2.5) is a through-ball threat. The line is too deep — blue must press and reorganize.

* **Oracle Actions:** red_1 has the ball near blue's penalty area. blue_1 steps up to press the ball carrier — the line is too deep. blue_2 drops to the goal line as cover. blue_3 marks the through-ball threat. Press and reorganize the defense.

```
blue_1 move to (-2.5, 1.5)
blue_2 move to (-4.0, 0.0)
blue_3 move to (-2.0, -1.0)
```

* **Output to bridge:**
```
blue_1 move to (-2.5, 1.5)
blue_2 move to (-4.0, 0.0)
blue_3 move to (-2.0, -1.0)
```

#### ✍️ Evaluation (GLM-5.2):
* **Tactical Correctness (1–5): 4** 
* **Position Reachability (Yes/No): Yes** 
* **Strategy Clarity (1–5): 4** 
* **Comment / Justification: High defensive line with a through-ball threat from red_2 behind the line is a coherent scenario. Ball at y=2.25 is near the touchline but within bounds; decision framing is clear.**

---

### Scenario 13: 3vs3_long_shot
* **Expert Description:** Ball at (3.1, 1.4) in red's half. red_2 (2.5, 1.5) is closest at 0.7m — red has possession. blue_2 (-0.5, 0.0) is 3.9m away. blue_1 and blue_3 are on the goal line. The shooting distance is short for red — blue must close distance to challenge.

* **Oracle Actions:** blue_2 advances toward the ball for a long shot opportunity — the goal is 3.9m away. blue_3 shifts to midfield support. blue_1 holds the goal line. Close the distance for a shot.

```
blue_1 cover the goal line at (-4.0, 0.9)
blue_2 move to (2.8, 1.2)
blue_3 move to (-0.5, 0.0)
```

* **Output to bridge:**
```
blue_1 move to (-4.0, 0.9)
blue_2 move to (2.8, 1.2)
blue_3 move to (-0.5, 0.0)
```

#### ✍️ Evaluation (GLM-5.2):
* **Tactical Correctness (1–5): 4** 
* **Position Reachability (Yes/No): Yes** 
* **Strategy Clarity (1–5): 4** 
* **Comment / Justification: Ball near the box with the goalie off-center presents a valid shot-selection scenario. Red attackers well-positioned to shoot. Clear.**

---

### Scenario 14: 3vs3_overload
* **Expert Description:** Ball at (2.5, 0.0) in red's half. red_1 (3.5, 0.0) is the sole defender, 1.0m from the ball. red_2 and red_3 are on the far wings — 2.9m and 3.2m away. blue_2 (-0.5, 0.5) is 3.0m from the ball. blue_1 (-4.0, 0.0) is the goalie. 2v1 overload — blue has a numbers advantage near the ball.

* **Oracle Actions:** blue has a 2v1 overload — only red_1 defends. blue_2 advances toward the ball to draw red_1 out. blue_3 moves wide as the free man for a pass. blue_1 holds the goal line. Exploit the numbers advantage.

```
blue_1 cover the goal line at (-4.0, 0.0)
blue_2 move to (2.2, 0.0)
blue_3 move to (0.0, -0.5)
```

* **Output to bridge:**
```
blue_1 move to (-4.0, 0.0)
blue_2 move to (2.2, 0.0)
blue_3 move to (0.0, -0.5)
```

#### ✍️ Evaluation (GLM-5.2):
* **Tactical Correctness (1–5): 2** 
* **Position Reachability (Yes/No): No** 
* **Strategy Clarity (1–5): 2** 
* **Comment / Justification: Described as blue_1 and blue_2 attacking in a 2-on-1, but blue_1 is at (-4.0, 0.0) — a goalie position far from the ball — and blue_3 occupies the identical coordinates as blue_1, an invalid overlap. Setup contradicts the described overload.**

---

### Scenario 15: 3vs3_possession_lost
* **Expert Description:** Ball at (1.0, 0.5) in red's half. red_1 (1.5, 0.5) has the ball — 0.5m away. blue_2 (-0.5, 1.5) is 1.8m away, blue_3 (-1.0, -1.0) is 2.5m. Both blue bots are caught upfield. blue_1 (-4.0, 0.0) is the goalie, 5.0m from play. Red is counter-attacking — blue must recover.

* **Oracle Actions:** red_1 won the ball — blue is caught upfield. blue_2 and blue_3 sprint back behind the ball. blue_1 holds the goal line. Recover defensive shape.

```
blue_1 cover the goal line at (-4.0, 0.5)
blue_2 move to (-0.5, 0.5)
blue_3 move to (-1.0, -0.5)
```

* **Output to bridge:**
```
blue_1 move to (-4.0, 0.5)
blue_2 move to (-0.5, 0.5)
blue_3 move to (-1.0, -0.5)
```

#### ✍️ Evaluation (GLM-5.2):
* **Tactical Correctness (1–5): 3** 
* **Position Reachability (Yes/No): Yes** 
* **Strategy Clarity (1–5): 4** 
* **Comment / Justification: Transition-to-defense concept is valid, but blue_1 at (-4.0, 0.0) and blue_3 at (-1.0, -1.0) are far from the ball at (1.0, 0.5). A team that just lost the ball in the opponent half should have players near the turnover — only blue_2 is remotely close.**

---

### Scenario 16: 3vs3_pressing_trap
* **Expert Description:** Ball at (0.5, 0.5) at midfield. red_1 (0.8, 0.5) is 0.4m from the ball, red_2 (0.2, -0.2) is 0.7m — double-team. blue_1 (-0.5, 0.3) is 1.0m away, under pressure. blue_2 (-1.0, 0.8) is 1.5m. blue_3 (-2.0, -0.5) is deep. red_3 (-0.5, 1.0) blocks the passing lane. blue_1 is trapped — must escape.

* **Oracle Actions:** blue_1 is under double-team pressure from red_1 and red_2. blue_1 passes back to blue_2 to escape the press. blue_3 holds deep cover. Reset possession and play wide.

```
blue_1 kick
blue_2 move to (-0.5, 0.8)
blue_3 move to (-2.5, -0.5)
```

* **Output to bridge:** 
```
blue_1 kick
blue_2 move to (-0.5, 0.8)
blue_3 move to (-2.5, -0.5)
```

#### ✍️ Evaluation (GLM-5.2):
* **Tactical Correctness (1–5): 4** 
* **Position Reachability (Yes/No): Yes** 
* **Strategy Clarity (1–5): 4** 
* **Comment / Justification: Red high press with blue having no clear outlet is a well-formed pressure-breaking scenario. Blue is surrounded and positions are realistic.**

---

### Scenario 17: 3vs3_wing_switch
* **Expert Description:** Ball at (1.5, 2.2) on the left wing. blue_2 (-0.5, 2.0) is 2.0m from the ball but double-teamed by red_1 (2.5, 2.0) and red_2 (2.0, 1.5). The right wing (Y<0) is open. blue_3 (0.0, 0.0) is at center. blue_1 (-4.0, 0.0) holds the goal line. The switch pass is not executable — double-team is too tight.

* **Oracle Actions:** blue_2 is double-teamed on the wing — the switch pass is not executable. blue_2 kicks the ball deep toward the opponent half to escape pressure. blue_3 moves to block the resulting set-piece. blue_1 holds the goal line. Escape the double-team.

```
blue_1 cover the goal line at (-4.0, 0.9)
blue_2 kick
blue_3 move to (-0.5, -1.0)
```

* **Output to bridge:**
```
blue_1 move to (-4.0, 0.9)
blue_2 kick
blue_3 move to (-0.5, -1.0)
```

#### ✍️ Evaluation (GLM-5.2):
* **Tactical Correctness (1–5): 4** 
* **Position Reachability (Yes/No): Yes** 
* **Strategy Clarity (1–5): 4** 
* **Comment / Justification: Stalled left-wing attack with red overloaded on that side — switching to the open right wing is the correct tactical response. blue_3 centrally placed to facilitate the switch. Clear.**

---
