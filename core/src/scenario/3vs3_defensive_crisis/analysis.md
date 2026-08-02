# 3vs3_defensive_crisis — Analysis

## Expert (technical)

The ball is at (-3.1, 0.45), deep in blue's zone, in front of blue's own goal.
Red_1 stands on the ball at (-3.1, 0.55) and can dribble or pass. Blue_1 at
(-4.0, 0.2) is the only blue bot positioned to react to the ball directly —
its move is obvious: intercept. Blue_2 at (-2.5, 0.5) should anticipate
blue_1 coming out for the ball. Blue_3 at (-1.5, -0.3) has its lane toward
the goal blocked by red_2 at (-0.7, 0.0).

## Oracle (strategic)

Blue_1 moves toward red_1 and intercepts the ball at (-3.1, 0.45) directly.
Blue_2 moves down into the center lane to (X≈-2.7, Y≈0.3), to cut off red_1's
dribbling path toward the goal. Blue_3 moves to the left lane at (X≈-1.5,
Y≈-0.6), ready to receive a pass or a rebound after the clear. Keep all blue
bots inside the field boundaries.
