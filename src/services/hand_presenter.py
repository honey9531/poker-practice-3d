"""Rebuild what the table looks like from a hand's event log.

The engine resolves a hand instantly (an all-in run-out deals every remaining
street inside a single ``act`` call). The presenter folds events one at a time
so the UI can show them at a human pace, and so stored hand histories can be
replayed with exactly the same code.

The presenter knows every hole card (they are in the events); the view builder
decides what each viewer may see.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from poker.actions import ActionType
from poker.cards import Card
from poker.events import (
    BlindKind,
    BlindPosted,
    BoardDealt,
    CardsExposed,
    HandEnded,
    HandEvent,
    HandStarted,
    HoleCardsDealt,
    PlayerActed,
    PotAwarded,
    ShowdownRevealed,
    Street,
    UncalledBetReturned,
)
from poker.pots import Pot, build_pots


@dataclass(slots=True)
class PresentedSeat:
    seat: int
    name: str
    stack: int
    street_bet: int = 0
    total_bet: int = 0
    folded: bool = False
    all_in: bool = False
    hole: tuple[Card, ...] = ()
    last_action: str = ""
    revealed: bool = False
    hand_label: str = ""
    best_cards: tuple[Card, ...] = ()
    won: int = 0


@dataclass(frozen=True, slots=True)
class AwardSummary:
    pot_index: int
    amount: int
    winners: tuple[int, ...]
    hand_label: str  # "" when uncontested


def action_label(event: PlayerActed) -> str:
    if event.all_in and event.action is not ActionType.FOLD:
        return f"All-in {event.street_total:,}"
    match event.action:
        case ActionType.FOLD:
            return "Fold"
        case ActionType.CHECK:
            return "Check"
        case ActionType.CALL:
            return f"Call {event.added:,}"
        case ActionType.BET:
            return f"Bet {event.street_total:,}"
        case ActionType.RAISE:
            return f"Raise to {event.street_total:,}"
    return event.action.value


@dataclass
class HandPresenter:
    seats: dict[int, PresentedSeat] = field(default_factory=dict)
    board: list[Card] = field(default_factory=list)
    street: Street | None = None
    button: int | None = None
    small_blind_seat: int | None = None
    big_blind_seat: int | None = None
    small_blind: int = 0
    big_blind: int = 0
    awards: list[AwardSummary] = field(default_factory=list)
    showdown: bool = False
    complete: bool = False
    events_applied: int = 0

    @classmethod
    def from_events(cls, events: list[HandEvent]) -> "HandPresenter":
        presenter = cls()
        for event in events:
            presenter.apply(event)
        return presenter

    # ---------------------------------------------------------------- folding

    def apply(self, event: HandEvent) -> None:
        self.events_applied += 1
        match event:
            case HandStarted():
                self.seats = {
                    seat: PresentedSeat(seat, event.names[seat], stack)
                    for seat, stack in event.stacks.items()
                }
                self.button = event.button
                self.small_blind_seat = event.small_blind_seat
                self.big_blind_seat = event.big_blind_seat
                self.small_blind = event.small_blind
                self.big_blind = event.big_blind
                self.street = Street.PREFLOP
            case BlindPosted():
                seat = self.seats[event.seat]
                self._commit(seat, event.amount)
                seat.all_in = event.all_in
                kind = "SB" if event.kind is BlindKind.SMALL else "BB"
                seat.last_action = f"{kind} {event.amount:,}"
            case HoleCardsDealt():
                self.seats[event.seat].hole = tuple(event.cards)
            case PlayerActed():
                seat = self.seats[event.seat]
                seat.stack = event.stack_after
                seat.total_bet += event.added
                seat.street_bet = event.street_total
                seat.folded = event.action is ActionType.FOLD
                seat.all_in = event.all_in
                seat.last_action = action_label(event)
            case BoardDealt():
                self.board.extend(event.cards)
                self.street = event.street
                for seat in self.seats.values():
                    seat.street_bet = 0
                    if not seat.folded:
                        seat.last_action = ""
            case CardsExposed():
                seat = self.seats[event.seat]
                seat.revealed = True
                seat.hole = tuple(event.cards)
            case UncalledBetReturned():
                seat = self.seats[event.seat]
                seat.stack += event.amount
                seat.street_bet -= event.amount
                seat.total_bet -= event.amount
            case ShowdownRevealed():
                self.showdown = True
                self.street = Street.SHOWDOWN
                for s in self.seats.values():
                    s.street_bet = 0
                    if not s.folded:
                        s.last_action = ""
                seat = self.seats[event.seat]
                seat.revealed = True
                seat.hole = tuple(event.cards)
                seat.hand_label = event.value.describe()
                seat.best_cards = tuple(event.best_five)
            case PotAwarded():
                for s in self.seats.values():
                    s.street_bet = 0
                for winner, share in event.shares.items():
                    self.seats[winner].stack += share
                    self.seats[winner].won += share
                label = event.value.describe() if event.value is not None and self.showdown else ""
                self.awards.append(AwardSummary(event.pot_index, event.amount, tuple(event.winners), label))
            case HandEnded():
                self.complete = True

    @staticmethod
    def _commit(seat: PresentedSeat, amount: int) -> None:
        seat.stack -= amount
        seat.street_bet += amount
        seat.total_bet += amount

    # ---------------------------------------------------------------- queries

    @property
    def winners(self) -> set[int]:
        return {seat for award in self.awards for seat in award.winners}

    @property
    def live_seats(self) -> set[int]:
        return {s.seat for s in self.seats.values() if not s.folded}

    def total_pot(self) -> int:
        """Chips in the middle and in front of players that are not yet awarded."""
        if self.awards:
            awarded = sum(a.amount for a in self.awards)
            return max(0, sum(s.total_bet for s in self.seats.values()) - awarded)
        return sum(s.total_bet for s in self.seats.values())

    def pots(self) -> list[Pot]:
        """Collected pots (current street bets excluded) that have not been awarded yet."""
        contributions = {s.seat: s.total_bet - s.street_bet for s in self.seats.values()}
        if not any(contributions.values()):
            return []
        pots = build_pots(contributions, self.live_seats)
        awarded = {a.pot_index for a in self.awards}
        return [pot for i, pot in enumerate(pots) if i not in awarded]

    def winning_cards(self) -> set[Card]:
        """Cards forming the winning hand(s), for highlighting."""
        cards: set[Card] = set()
        for seat in self.winners:
            cards.update(self.seats[seat].best_cards)
        return cards
