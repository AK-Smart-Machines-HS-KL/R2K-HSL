# 2vs2_goalie_pass — Analysis

> _Motivation: in the Gazebo experiments a kicking goalie never happened.
> This scenario forces the goalie to become active — the ball starts in
> front of it and the only safe play is a pass out to blue_2, who
> re-kicks immediately._

## Expert (technical)

The ball is at (-2.94, 0.19), 0.5 m in front of blue_1 (-3.4, 0.0) —
the goalie — with uncontested possession. Blue_2 at (-1.0, 1.0) is the
only teammate, on the left wing, reachable for a pass (2.6 m). A free
shooting lane runs from blue_2 toward red's goal: red_1 at (-1.2, -0.8)
presses the goalie and red_2 at (0.3, 0.4) covers the center, so nobody
guards red's goal (X=+4.5). Red_1 is 2.0 m from the ball and closing in
about 2.5 s; the passing lane from blue_1 to blue_2 is open. The ball
sits just 0.5 m in front of the goal area and 1.5 m from blue's goal
line — blue_1 is the last line of defense.

## Oracle (strategic)

Blue_1, the goalie, kicks the ball out to blue_2 at (-1.0, 1.0) before
red_1 arrives. Blue_2 re-kicks the ball immediately toward the
uncovered red goal — no dribbling. Keep all blue bots inside the field
boundaries.
