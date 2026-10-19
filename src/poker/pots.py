"""Main/side pot construction and distribution.

Pots are derived from each player's total contribution to the hand, so they can
be recomputed at any point and always account for every chip.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from poker.evaluator import HandValue


@dataclass(frozen=True, slots=True)
class Pot:
    amount: int
    eligible: frozenset[int]  # seats that can win this pot


@dataclass(frozen=True, slots=True)
class PotAward:
    pot_index: int  # 0 = main pot
    amount: int
    winners: tuple[int, ...]  # seats, in odd-chip order
    shares: Mapping[int, int]  # seat -> chips won from this pot
    value: HandValue | None  # winning hand value; None if uncontested


def build_pots(contributions: Mapping[int, int], live: set[int] | frozenset[int]) -> list[Pot]:
    """Layer contributions into a main pot and side pots.

    ``contributions`` maps seat -> chips put into the hand (including folded
    players); ``live`` are the seats that have not folded. Each distinct
    contribution level of a live player closes a pot that live players at or
    above that level are eligible for. Adjacent pots with the same eligible
    players are merged.
    """
    if any(amount < 0 for amount in contributions.values()):
        raise ValueError("Negative contribution")
    live_levels = sorted({contributions.get(seat, 0) for seat in live} - {0})
    pots: list[Pot] = []
    previous = 0
    for level in live_levels:
        amount = sum(
            min(c, level) - min(c, previous) for c in contributions.values()
        )
        eligible = frozenset(s for s in live if contributions.get(s, 0) >= level)
        if pots and pots[-1].eligible == eligible:
            pots[-1] = Pot(pots[-1].amount + amount, eligible)
        elif amount:
            pots.append(Pot(amount, eligible))
        previous = level

    # Chips folded players put in above every live player's level (only possible
    # before uncalled bets are returned) belong to the last pot.
    excess = sum(max(0, c - previous) for c in contributions.values())
    if excess:
        if pots:
            pots[-1] = Pot(pots[-1].amount + excess, pots[-1].eligible)
        else:
            pots.append(Pot(excess, frozenset(live)))
    return pots


def split_amount(amount: int, winners: Sequence[int]) -> dict[int, int]:
    """Split ``amount`` evenly; leftover chips go one each to the earliest winners.

    ``winners`` must already be in odd-chip order (clockwise from the button).
    """
    if not winners:
        raise ValueError("No winners")
    share, remainder = divmod(amount, len(winners))
    return {seat: share + (1 if i < remainder else 0) for i, seat in enumerate(winners)}


def award_pots(
    pots: Sequence[Pot],
    values: Mapping[int, HandValue],
    seat_order: Sequence[int],
) -> list[PotAward]:
    """Distribute pots to the best hands among each pot's eligible seats.

    ``values`` holds showdown hand values (may be empty when one player is
    left); ``seat_order`` is the odd-chip order: seats clockwise starting
    left of the button.
    """
    order = {seat: i for i, seat in enumerate(seat_order)}
    awards = []
    for index, pot in enumerate(pots):
        eligible = sorted(pot.eligible, key=order.__getitem__)
        if len(eligible) == 1:
            winners, value = eligible, values.get(eligible[0])
        else:
            value = max(values[seat] for seat in eligible)
            winners = [seat for seat in eligible if values[seat] == value]
        awards.append(
            PotAward(index, pot.amount, tuple(winners), split_amount(pot.amount, winners), value)
        )
    return awards
