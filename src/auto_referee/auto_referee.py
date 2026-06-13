"""
Minimal Auto-Referee for RoboCup HSL (R2K-HSL).

Implements the core state machine required by the RoboCup Humanoid Soccer League rules:
  INITIAL -> READY -> SET -> PLAYING -> FINISHED

Publishes the current GameControlData on /game_controller_state and reacts to
manual override commands on /referee_command.

Usage (standalone, no ROS):
    python3 auto_referee.py

Usage (as a ROS 2 node):
    ros2 run auto_referee auto_referee
"""

from __future__ import annotations

import time

try:
    from .game_state import GameState, Team
except ImportError:
    from game_state import GameState, Team  # type: ignore[no-redef]

# ---------------------------------------------------------------------------
# Constants (adjust to match your league / rule version)
# ---------------------------------------------------------------------------
HALF_DURATION_S: int = 600          # 10 minutes per half
READY_DURATION_S: int = 45          # time allowed in READY phase
SET_DURATION_S: int = 5             # time in SET before PLAYING
GOAL_CELEBRATION_S: int = 5         # pause (READY delay) after a goal


class GameData:
    """Holds the mutable state of the current game."""

    def __init__(self) -> None:
        self.state: GameState = GameState.INITIAL
        self.first_half: bool = True
        self.score: dict[Team, int] = {Team.RED: 0, Team.BLUE: 0}
        self.kick_off_team: Team = Team.RED
        self.phase_start: float = time.monotonic()
        self.seconds_remaining: int = HALF_DURATION_S
        self.goal_celebration_start: float | None = None

    # ------------------------------------------------------------------
    def elapsed(self) -> float:
        return time.monotonic() - self.phase_start

    def reset_phase_timer(self) -> None:
        self.phase_start = time.monotonic()


class MinimalAutoReferee:
    """
    Minimal auto-referee state machine.

    Call ``tick()`` regularly (e.g. every 100 ms) to advance the game.
    Use ``signal_goal(team)`` and ``signal_kick_off_taken()`` from external
    perception or manual override.
    """

    def __init__(self) -> None:
        self.data = GameData()
        self._kick_off_taken: bool = False

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def start_game(self) -> None:
        """Transition INITIAL -> READY."""
        self._require_state(GameState.INITIAL)
        self._enter(GameState.READY)

    def set_ready(self) -> None:
        """Manual: transition any state -> READY (e.g. after a goal)."""
        self._enter(GameState.READY)

    def signal_goal(self, scoring_team: Team) -> None:
        """Called by perception or manual input when a goal is detected."""
        if self.data.state != GameState.PLAYING:
            return
        self.data.score[scoring_team] += 1
        print(
            f"[AutoReferee] GOAL for {scoring_team.name}! "
            f"Score RED {self.data.score[Team.RED]} : {self.data.score[Team.BLUE]} BLUE"
        )
        # switch kick-off to the team that conceded
        self.data.kick_off_team = (
            Team.BLUE if scoring_team == Team.RED else Team.RED
        )
        # short celebration pause before READY
        self.data.goal_celebration_start = time.monotonic()
        self.data.state = GameState.READY

    def signal_kick_off_taken(self) -> None:
        """Called when the kick-off robot has touched the ball."""
        self._kick_off_taken = True

    def tick(self) -> None:
        """Advance the state machine. Call at least once per second."""
        state = self.data.state

        if state == GameState.READY:
            # Honour GOAL_CELEBRATION_S pause before resetting the READY timer
            if self.data.goal_celebration_start is not None:
                if time.monotonic() - self.data.goal_celebration_start < GOAL_CELEBRATION_S:
                    return
                self.data.goal_celebration_start = None
                self.data.reset_phase_timer()
            if self.data.elapsed() >= READY_DURATION_S:
                self._enter(GameState.SET)

        elif state == GameState.SET:
            if self.data.elapsed() >= SET_DURATION_S:
                self._enter(GameState.PLAYING)

        elif state == GameState.PLAYING:
            elapsed = self.data.elapsed()
            self.data.seconds_remaining = max(
                0, HALF_DURATION_S - int(elapsed)
            )
            if self.data.seconds_remaining == 0:
                self._end_half()

    def get_state_summary(self) -> dict:
        """Return a plain dict snapshot (easy to serialise / publish)."""
        return {
            "state": self.data.state.name,
            "half": 1 if self.data.first_half else 2,
            "score_red": self.data.score[Team.RED],
            "score_blue": self.data.score[Team.BLUE],
            "kick_off_team": self.data.kick_off_team.name,
            "seconds_remaining": self.data.seconds_remaining,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _enter(self, new_state: GameState) -> None:
        print(f"[AutoReferee] {self.data.state.name} -> {new_state.name}")
        self.data.state = new_state
        self.data.reset_phase_timer()
        self.data.goal_celebration_start = None
        self._kick_off_taken = False

    def _end_half(self) -> None:
        if self.data.first_half:
            print("[AutoReferee] Half-time!")
            self.data.first_half = False
            # swap kick-off team for second half
            self.data.kick_off_team = (
                Team.BLUE if self.data.kick_off_team == Team.RED else Team.RED
            )
            self._enter(GameState.READY)
        else:
            print("[AutoReferee] Full-time!")
            self._enter(GameState.FINISHED)

    def _require_state(self, expected: GameState) -> None:
        if self.data.state != expected:
            raise RuntimeError(
                f"Expected state {expected.name}, got {self.data.state.name}"
            )


# ---------------------------------------------------------------------------
# Stand-alone demo / smoke-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    referee = MinimalAutoReferee()

    print("=== Minimal Auto-Referee Demo ===")
    referee.start_game()
    print(referee.get_state_summary())

    # Simulate READY timeout
    referee.data.phase_start -= READY_DURATION_S
    referee.tick()
    print(referee.get_state_summary())

    # Simulate SET timeout
    referee.data.phase_start -= SET_DURATION_S
    referee.tick()
    print(referee.get_state_summary())

    # Signal a goal for RED
    referee.signal_goal(Team.RED)
    referee.data.goal_celebration_start = None  # skip celebration in demo
    print(referee.get_state_summary())
