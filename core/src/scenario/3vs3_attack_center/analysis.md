# 3vs3_attack_center — Analysis

## Expert (technical)

The ball is at X=2.2, inside red's half, close to the center line. Two blue
bots are near the ball: blue_2 at (1.5, 1.2) and blue_3 at (1.5, -1.2). The
red defense is stretched: both red defenders stand wide on the wings (red_2 at
(2.8, 2.2), red_3 at (2.8, -2.2)), so the middle of the field is open. The red
goalie is off-center at (4.2, 0.5), leaving the far side of the goal exposed.
No red bot is within 2 m of the ball. Blue has a numbers advantage in the
center.

## Oracle (strategic)

Blue_2 moves to the ball at (2.2, 0.3) and kicks toward the red goal, aiming
at the open side of the goal (away from the red goalie at Y=0.5). Blue_3 moves
slightly forward and stays ready to receive the ball if the shot bounces back.
Blue_1 moves to the middle of its own half (X=-2.25), ready to intercept the
ball early if red starts a counter attack. Keep all blue bots inside the field
boundaries.
