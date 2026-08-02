# 3vs3_long_shot — Analysis

## Expert (technical)

The ball is at (3.15, 1.35) in red's half, close to the goal mouth.
Blue_1 at (2.8, 1.2) is the nearest blue bot, 0.38 m from the ball, but
possession is contested — red_2 at (2.5, 1.5) is 0.67 m away and will
contest in about 0.8 s. The goal mouth is bracketed: red_1 (goalie) at
(4.2, 0.5) guards the short post (goal mouth at Y≈+0.9), red_3 at
(3.5, -0.5) covers the long post (goal mouth at Y≈-0.9). No unguarded
corner exists. Blue_2 at (1.0, 0.0) is 2.5 m from the ball and cannot
assist in time. Blue_3 at (-4.0, -0.3) is the deepest blue bot.

## Oracle (strategic)

Blue_1 claims the ball at (3.15, 1.35) immediately, before red_2
contests it. Blue_2 moves now to open a straight, unobstructed passing
lane to blue_1, taking position at (X≈2.0, Y≈0.8), so that red_3 at
(3.5, -0.5) cannot intercept the assist. Blue_3 moves closer to the
middle of its own half, to (X≈-2.25, Y≈0.0), as deep cover against a
counter-attack. Keep all blue bots inside the field boundaries.
