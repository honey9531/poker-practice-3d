"""Practice statistics, computed from hand events (never from UI counters).

Definitions (per player, over the hands they were dealt into):

* **Hands played**: hands the player was dealt into.
* **Hands won**: hands in which the player received chips from at least one pot.
* **Net chips**: sum over hands of (stack after the hand - stack before it).
* **VPIP** (voluntarily put money in pot): share of hands with a pre-flop call,
  bet or raise. Posting a blind is not voluntary; checking the big blind is not
  counted.
* **PFR** (pre-flop raise): share of hands with a pre-flop bet or raise.
* **Showdown frequency**: share of hands played in which the player was still
  in the hand at showdown (cards compared).
* **Showdown win rate**: share of those showdowns in which the player won at
  least part of a pot.
* **Biggest pot won**: largest total collected by the player in a single hand.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from poker.actions import ActionType
from poker.events import (
    BoardDealt,
    HandEnded,
    HandEvent,
    HandStarted,
    HoleCardsDealt,
    PlayerActed,
    PotAwarded,
    ShowdownRevealed,
    Street,
)


@dataclass(frozen=True, slots=True)
class PlayerHandFacts:
    seat: int
    name: str
    hole: tuple[str, ...]
    starting_stack: int
    final_stack: int
    won_amount: int
    vpip: bool
    pfr: bool
    saw_flop: bool
    showdown: bool
    won_showdown: bool

    @property
    def net(self) -> int:
        return self.final_stack - self.starting_stack

    @property
    def won_any(self) -> bool:
        return self.won_amount > 0


def hand_facts(events: Sequence[HandEvent]) -> list[PlayerHandFacts]:
    """Per-player facts for one complete hand."""
    started = next(e for e in events if isinstance(e, HandStarted))
    ended = next(e for e in reversed(events) if isinstance(e, HandEnded))
    holes = {e.seat: tuple(c.code for c in e.cards) for e in events if isinstance(e, HoleCardsDealt)}
    folded_before_flop: set[int] = set()
    vpip: set[int] = set()
    pfr: set[int] = set()
    flop_dealt = False
    for event in events:
        if isinstance(event, BoardDealt) and event.street is Street.FLOP:
            flop_dealt = True
        if isinstance(event, PlayerActed) and event.street is Street.PREFLOP:
            if event.action in (ActionType.CALL, ActionType.BET, ActionType.RAISE):
                vpip.add(event.seat)
            if event.action in (ActionType.BET, ActionType.RAISE):
                pfr.add(event.seat)
            if event.action is ActionType.FOLD:
                folded_before_flop.add(event.seat)
    showdown = {e.seat for e in events if isinstance(e, ShowdownRevealed)}
    won: dict[int, int] = {}
    for event in events:
        if isinstance(event, PotAwarded):
            for seat, share in event.shares.items():
                won[seat] = won.get(seat, 0) + share
    return [
        PlayerHandFacts(
            seat=seat,
            name=started.names[seat],
            hole=holes.get(seat, ()),
            starting_stack=stack,
            final_stack=ended.final_stacks[seat],
            won_amount=won.get(seat, 0),
            vpip=seat in vpip,
            pfr=seat in pfr,
            saw_flop=flop_dealt and seat not in folded_before_flop,
            showdown=seat in showdown,
            won_showdown=seat in showdown and won.get(seat, 0) > 0,
        )
        for seat, stack in sorted(started.stacks.items())
    ]


@dataclass(frozen=True, slots=True)
class Stats:
    hands: int = 0
    hands_won: int = 0
    net: int = 0
    vpip_hands: int = 0
    pfr_hands: int = 0
    showdowns: int = 0
    showdowns_won: int = 0
    biggest_pot: int = 0

    @staticmethod
    def _ratio(part: int, whole: int) -> float:
        return part / whole if whole else 0.0

    @property
    def win_rate(self) -> float:
        return self._ratio(self.hands_won, self.hands)

    @property
    def vpip(self) -> float:
        return self._ratio(self.vpip_hands, self.hands)

    @property
    def pfr(self) -> float:
        return self._ratio(self.pfr_hands, self.hands)

    @property
    def showdown_rate(self) -> float:
        return self._ratio(self.showdowns, self.hands)

    @property
    def showdown_win_rate(self) -> float:
        return self._ratio(self.showdowns_won, self.showdowns)


def aggregate(facts: Iterable[PlayerHandFacts]) -> Stats:
    hands = won = net = vpip = pfr = showdowns = showdowns_won = biggest = 0
    for f in facts:
        hands += 1
        won += f.won_any
        net += f.net
        vpip += f.vpip
        pfr += f.pfr
        showdowns += f.showdown
        showdowns_won += f.won_showdown
        biggest = max(biggest, f.won_amount)
    return Stats(hands, won, net, vpip, pfr, showdowns, showdowns_won, biggest)
