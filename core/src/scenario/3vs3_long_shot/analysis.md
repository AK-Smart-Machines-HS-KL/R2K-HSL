# 3vs3_long_shot — Analysis

## Oracle (strategic)

Blue should exploit distance — if red's goalie is out of position, a long-range shot can score. Look for opportunities where the ball is in open space at X > 1.0 and the red goal is exposed.

## Expert (technical)

Blue LLM should assign Kick when the ball is in shooting range (X > 0.5, |Y| < 1.5). Accuracy is low at distance but the element of surprise matters. Supporter should follow up for rebounds.
