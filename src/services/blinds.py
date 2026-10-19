"""Tournament-style blind levels that rise as a session goes on.

Levels are whole-number multiples of the starting small blind, with the big
blind always twice the small blind, so every level stays an integer:
10/20 -> 20/40 -> 30/60 -> 50/100 -> 100/200 -> 150/300 -> ...
"""

from __future__ import annotations

# Small-blind multipliers per level (level 0 = the starting blinds).
_LADDER = (1, 2, 3, 5, 10, 15, 20, 30, 40, 60, 80, 100, 150, 200, 300, 400, 600, 800, 1000)

# Allowed "increase every N hands" values (0 = blinds never change).
INTERVALS = (0, 5, 10, 20)


def multiplier(level: int) -> int:
    if level < 0:
        raise ValueError("Level cannot be negative")
    if level < len(_LADDER):
        return _LADDER[level]
    # Beyond the table, keep growing by about half each level.
    value = _LADDER[-1]
    for _ in range(level - len(_LADDER) + 1):
        value += value // 2
    return value


def level_for_hand(hands_played: int, every: int) -> int:
    """Level of the next hand after ``hands_played`` completed hands."""
    if every <= 0:
        return 0
    return hands_played // every


def blinds_at(level: int, small_blind: int, big_blind: int) -> tuple[int, int]:
    """Blinds for ``level`` given the starting blinds."""
    factor = multiplier(level)
    return small_blind * factor, big_blind * factor


def hands_until_next_level(hands_played: int, every: int) -> int:
    """Hands left at the current level, counting the next one (0 when blinds are fixed)."""
    if every <= 0:
        return 0
    return every - hands_played % every
