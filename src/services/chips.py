"""Visual chip denominations and the breakdown of amounts into chips.

Purely presentational: the engine accounts in integers and never sees chips.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChipDenomination:
    value: int
    color: str  # body
    insert: str  # edge inserts and inner ring
    text: str  # denomination label


DEFAULT_DENOMINATIONS: tuple[ChipDenomination, ...] = (
    ChipDenomination(1, "#e9e4d8", "#2f5fa8", "#1f3f73"),
    ChipDenomination(5, "#b3252d", "#f1ece2", "#7a161c"),
    ChipDenomination(25, "#1f7a45", "#f1ece2", "#145130"),
    ChipDenomination(100, "#25242a", "#f1ece2", "#25242a"),
    ChipDenomination(500, "#6a3a91", "#f3d77e", "#4a2766"),
    ChipDenomination(1000, "#e0b23a", "#2a2a30", "#6b4f10"),
    ChipDenomination(5000, "#a2532b", "#f1ece2", "#6b3317"),
)


def validate_denominations(denominations: Sequence[ChipDenomination]) -> None:
    values = [d.value for d in denominations]
    if not values or min(values) != 1:
        raise ValueError("Denominations must include 1 so every amount can be shown")
    if len(set(values)) != len(values) or any(v <= 0 for v in values):
        raise ValueError("Denomination values must be distinct and positive")


def breakdown(
    amount: int, denominations: Sequence[ChipDenomination] = DEFAULT_DENOMINATIONS
) -> list[tuple[ChipDenomination, int]]:
    """Fewest chips that make ``amount``, largest denomination first."""
    if amount < 0:
        raise ValueError("Amount cannot be negative")
    validate_denominations(denominations)
    result = []
    remaining = amount
    for denomination in sorted(denominations, key=lambda d: d.value, reverse=True):
        count, remaining = divmod(remaining, denomination.value)
        if count:
            result.append((denomination, count))
    return result


def chip_label(value: int) -> str:
    """Short label printed on a chip: 25, 500, 1K, 5K, 2.5K, 1M."""
    for divisor, suffix in ((1_000_000, "M"), (1_000, "K")):
        if value >= divisor:
            whole, rest = divmod(value, divisor)
            if rest == 0:
                return f"{whole}{suffix}"
            return f"{value / divisor:g}{suffix}"
    return str(value)
