# Minimal Auto-Referee

A lightweight, dependency-free auto-referee for the RoboCup Humanoid Soccer League (HSL).

## Implemented game states

| State    | Description                                   |
|----------|-----------------------------------------------|
| INITIAL  | Game not yet started                          |
| READY    | Robots walk to starting positions (45 s max)  |
| SET      | Robots stand still, kick-off team may kick (5 s) |
| PLAYING  | Normal game play (10 min per half)            |
| FINISHED | Full-time                                     |

## Minimal rules covered

- Half duration (2 × 10 min)
- READY → SET → PLAYING transitions via timeouts
- Goal detection → score update → next kick-off assignment → back to READY
- Half-time handling (swap kick-off team)

## Not yet implemented (out of scope for minimal version)

- Free kicks / penalty kicks
- Out-of-bounds detection
- Robot foul detection
- Game Controller network protocol (GameControlData UDP)
- ROS 2 node wrapping

## Usage

```bash
# Standalone smoke-test (no ROS required):
python3 auto_referee.py
```

## Files

| File            | Purpose                               |
|-----------------|---------------------------------------|
| `game_state.py` | Enums: `GameState`, `Team`            |
| `auto_referee.py` | State machine + demo entry point    |
