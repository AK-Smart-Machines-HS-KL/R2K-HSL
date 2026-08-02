# 3vs3_def_transition — Analysis

## Expert (technical)

Blue just lost the ball in red's half and must recover. The ball is at
(2.2, 0.0) with blue_3 at (2.2, 0.2) 0.2 m from it and red_1 at
(2.4, 0.0) 0.28 m — a 50/50 contest. Blue_3 is close enough to tackle
aggressively; this is a legitimate recovery tackle, not a press.
Red_2 at (0.0, 0.3) and red_3 at (-0.9, 0.9) are behind the ball in
blue's half, out of reach — they can be ignored for the tackle
decision. Blue_2 at (0.5, -0.3) has free space on the right wing
(Y toward -3.0). Blue_1 at (-3.6, 0.3) is well-placed as the goalie.

## Oracle (strategic)

Blue_1, the goalie at (-3.6, 0.3), stays at (-3.6, 0.3). Blue_2 keeps
distance — it does not cluster with the tackle — and moves to the free
right-wing space at (X≈2.0, Y≈-2.0), waiting there for the ball to come
free and giving blue_3 an outlet when the press arrives. Blue_3, closest to
the ball (0.2 m away at (2.2, 0.2)), tackles aggressively for the ball at
(2.2, 0.0). Keep all blue bots inside the field boundaries.
