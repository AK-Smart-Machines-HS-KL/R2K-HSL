# 3vs3_attack_wing — Analysis

## Expert (technical)

The ball is at (3.0, 2.0) on the right wing, inside red's half near the goal
line. Blue_1 at (2.5, 1.8) stands close to the ball. The shooting angle toward
the goal mouth (Y from -0.9 to +0.9 at X=4.5) is too narrow — blue_1 cannot
shoot directly from its position, and the ball sits between blue_1 and the
goal. Blue_1 must move around the ball to gain a usable angle, which takes
time. Red_2 at (1.0, 0.5) is far away from the ball and poorly positioned to
defend, but it will move toward blue_1 to block. Red_3 at (2.0, -1.5) stands
on the far side, out of reach, and cannot defend this wing action. Blue_2 at
(0.5, 0.0) stays at midfield — too far back to receive a pass played into the
space behind red's defense.

## Oracle (strategic)

Blue_1 moves around the ball to (X≈3.4, Y≈2.0), goal-side of the ball, to
open a shooting angle toward the goal. If red_2 moves in to block, blue_1
passes instead of shooting. By the time blue_1 can pass, blue_2 should be
positioned in red's half at (X≈2.5, Y≈2.5), standing ready to receive a pass
into the space behind red's defense. Blue_2 must actively move into this
receiving position — red_2 will try to block blue_1, so blue_2 cannot wait.
Blue_3 stays deep at (X≈-4.0, Y≈0.0), near the center of its own half, ready
to intercept if red clears the ball toward a counter attack. Keep all blue
bots inside the field boundaries.
