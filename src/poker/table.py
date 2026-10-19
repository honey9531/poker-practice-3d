"""A table that plays consecutive hands: stacks, button rotation, blind levels."""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass

from poker.deck import Deck
from poker.hand import HoldemHand, SeatSpec


class TableError(RuntimeError):
    pass


@dataclass(slots=True)
class Seat:
    seat: int
    name: str
    stack: int

    @property
    def busted(self) -> bool:
        return self.stack == 0


class Table:
    """Owns the stacks between hands.

    The button moves to the next seat that still has chips ("moving button"):
    busted players are skipped and no dead blinds are used.
    """

    def __init__(
        self,
        players: Sequence[tuple[str, int]],
        small_blind: int,
        big_blind: int,
        *,
        rng: random.Random | None = None,
        button: int | None = None,
    ) -> None:
        if not 2 <= len(players) <= 10:
            raise TableError("A table seats 2 to 10 players")
        if any(stack < 0 for _, stack in players):
            raise TableError("Stacks cannot be negative")
        self.seats = [Seat(i, name, stack) for i, (name, stack) in enumerate(players)]
        self.rng = rng or random.Random()
        self.button: int | None = button
        self.hand: HoldemHand | None = None
        self.hand_number = 0
        self._settled = True
        self.set_blinds(small_blind, big_blind)

    def set_blinds(self, small_blind: int, big_blind: int) -> None:
        """Change blind levels; takes effect from the next hand."""
        if not 0 < small_blind <= big_blind:
            raise TableError("Blinds must satisfy 0 < small blind <= big blind")
        self.small_blind = small_blind
        self.big_blind = big_blind

    @property
    def active_seats(self) -> list[Seat]:
        return [s for s in self.seats if not s.busted]

    @property
    def can_start_hand(self) -> bool:
        return len(self.active_seats) >= 2 and (self.hand is None or self.hand.is_complete)

    def total_chips(self) -> int:
        if self.hand is not None and not self._settled:
            in_hand = {p.seat for p in self.hand.players}
            return self.hand.total_chips() + sum(
                s.stack for s in self.seats if s.seat not in in_hand
            )
        return sum(s.stack for s in self.seats)

    def _next_button(self) -> int:
        active = [s.seat for s in self.active_seats]
        if self.button is None:
            return self.rng.choice(active)
        return next((s for s in active if s > self.button), active[0])

    def start_hand(self, deck: Deck | None = None) -> HoldemHand:
        if self.hand is not None and not self.hand.is_complete:
            raise TableError("The current hand is still in progress")
        self.settle_hand()
        if len(self.active_seats) < 2:
            raise TableError("At least two players with chips are required")
        self.button = self._next_button()
        self.hand = HoldemHand(
            [SeatSpec(s.seat, s.name, s.stack) for s in self.active_seats],
            self.button,
            self.small_blind,
            self.big_blind,
            deck=deck if deck is not None else Deck(self.rng),
        )
        self.hand_number += 1
        self._settled = False
        return self.hand

    def settle_hand(self) -> None:
        """Copy final stacks from a completed hand back to the seats (idempotent)."""
        if self._settled or self.hand is None:
            return
        if not self.hand.is_complete:
            raise TableError("Cannot settle a hand in progress")
        for seat, stack in self.hand.result.final_stacks.items():
            self.seats[seat].stack = stack
        self._settled = True

    def reset(self, stacks: Sequence[int] | int) -> None:
        """Start a new session with fresh stacks (abandons nothing mid-hand)."""
        if self.hand is not None and not self.hand.is_complete:
            raise TableError("Cannot reset during a hand")
        values = [stacks] * len(self.seats) if isinstance(stacks, int) else list(stacks)
        if len(values) != len(self.seats) or any(v < 0 for v in values):
            raise TableError("Invalid stacks")
        for seat, stack in zip(self.seats, values):
            seat.stack = stack
        self.hand = None
        self._settled = True
        self.button = None
        self.hand_number = 0
