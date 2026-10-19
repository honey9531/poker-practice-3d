"""Opponent decision interface.

Strategies see a :class:`DecisionContext`: public table information plus the
deciding player's own hole cards, never other players' hidden cards.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol

from poker.actions import Action, LegalActions
from poker.cards import Card
from poker.events import PlayerActed, Street
from poker.hand import HoldemHand

from ai.tendencies import Tendency


@dataclass(frozen=True, slots=True)
class PublicAction:
    seat: int
    street: Street
    action: str  # "fold", "check", "call", "bet", "raise"
    street_total: int
    all_in: bool


@dataclass(frozen=True, slots=True)
class DecisionContext:
    seat: int
    hole: tuple[Card, ...]
    board: tuple[Card, ...]
    street: Street
    legal: LegalActions
    pot: int  # all chips committed this hand, including current bets
    big_blind: int
    stack: int
    button: int
    players_in_hand: int  # not folded (including the decider)
    opponents_in_hand: int
    opponents_with_chips: int  # opponents still able to bet
    position: int  # 0 = first to act post-flop ... players_in_hand-1 = last (button side)
    effective_stack: int  # smallest of own stack+bet and the largest live opponent stack+bet
    history: tuple[PublicAction, ...]
    # Public betting habits of every player this session (seat -> Tendency).
    tendencies: Mapping[int, Tendency] = field(default_factory=dict)

    @property
    def to_call(self) -> int:
        return self.legal.call_amount

    @property
    def pot_odds(self) -> float:
        """Share of the final pot the call represents (0 when checking is free)."""
        if self.to_call == 0:
            return 0.0
        return self.to_call / (self.pot + self.to_call)

    @property
    def last_aggressor(self) -> PublicAction | None:
        """The most recent bet or raise on this street, if any."""
        return next(
            (a for a in reversed(self.history) if a.street == self.street and a.action in ("bet", "raise")),
            None,
        )

    @property
    def raises_this_street(self) -> int:
        return sum(1 for a in self.history if a.street == self.street and a.action in ("bet", "raise"))


class Strategy(Protocol):
    """Chooses a legal action. Must be deterministic given its RNG state."""

    name: str

    def decide(self, ctx: DecisionContext) -> Action: ...


def observe(hand: HoldemHand, seat: int, tendencies: Mapping[int, Tendency] | None = None) -> DecisionContext:
    """Build the information available to ``seat``, which must be the player to act."""
    if hand.to_act != seat:
        raise ValueError(f"Seat {seat} is not to act")
    me = hand.player(seat)
    live = hand.live_players
    opponents = [p for p in live if p.seat != seat]
    # Post-flop order: clockwise from the button; position = index among live players.
    order = [p.seat for p in hand.seats_clockwise_from(hand.button) if not p.folded]
    largest_opponent = max((p.stack + p.street_bet for p in opponents), default=0)
    history = tuple(
        PublicAction(e.seat, e.street, e.action.value, e.street_total, e.all_in)
        for e in hand.events
        if isinstance(e, PlayerActed)
    )
    return DecisionContext(
        seat=seat,
        hole=tuple(me.hole),
        board=tuple(hand.board),
        street=hand.street,
        legal=hand.legal_actions(),
        pot=hand.total_pot,
        big_blind=hand.big_blind,
        stack=me.stack,
        button=hand.button,
        players_in_hand=len(live),
        opponents_in_hand=len(opponents),
        opponents_with_chips=sum(1 for p in opponents if p.stack > 0),
        position=order.index(seat),
        effective_stack=min(me.stack + me.street_bet, largest_opponent),
        history=history,
        tendencies=dict(tendencies or {}),
    )
