"""Minimal game-state definitions for the R2K auto-referee (RoboCup HSL)."""

from enum import IntEnum


class GameState(IntEnum):
    INITIAL  = 0
    READY    = 1
    SET      = 2
    PLAYING  = 3
    FINISHED = 4


class Team(IntEnum):
    RED  = 0
    BLUE = 1
