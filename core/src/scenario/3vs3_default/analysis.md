# 3vs3_default — Analysis

Baseline 3vs3 kickoff scenario. Ball at exact center, mirrored formation —
this is the pre-kickoff state (no attacking advantage). Retained under the
legacy v5 filename for backward compatibility with existing launch configs
and documentation references. Distinct from TC-01 (`3vs3_attack_center`),
which is a pro-blue attack variant (2026-08-01).

## Expert (technical)

Even formation, ball at center. Blue should exploit the central gap between red
bots. Push blue_2 and blue_3 forward through midfield while blue_1 holds the
defensive line. Quick central passing is key — the even formation means whoever
controls the center controls the game.

## Oracle (strategic)

Blue LLM should assign goalie to blue_1 at X=-4.2, attacker to the bot closest
to the ball (blue_2 or blue_3), and defender to the third. Expect 2-3 role
switches as the ball moves. Central positioning and short passes should
dominate.