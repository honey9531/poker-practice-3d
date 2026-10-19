"""Immutable records of everything that happens in a hand.

The event log is the single source for hand history, statistics and UI
animation sequencing.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

from poker.actions import ActionType
from poker.cards import Card
from poker.evaluator import HandValue


class Street(Enum):
    PREFLOP = "preflop"
    FLOP = "flop"
    TURN = "turn"
    RIVER = "river"
    SHOWDOWN = "showdown"


class BlindKind(Enum):
    SMALL = "small"
    BIG = "big"


@dataclass(frozen=True, slots=True)
class HandStarted:
    button: int
    small_blind_seat: int
    big_blind_seat: int
    small_blind: int
    big_blind: int
    stacks: Mapping[int, int]  # seat -> stack before blinds
    names: Mapping[int, str]


@dataclass(frozen=True, slots=True)
class BlindPosted:
    seat: int
    kind: BlindKind
    amount: int
    all_in: bool


@dataclass(frozen=True, slots=True)
class HoleCardsDealt:
    seat: int
    cards: tuple[Card, Card]


@dataclass(frozen=True, slots=True)
class PlayerActed:
    seat: int
    street: Street
    action: ActionType  # never ALL_IN: resolved to CALL/BET/RAISE with all_in=True
    added: int  # chips moved from stack this action
    street_total: int  # player's street commitment after the action
    stack_after: int
    all_in: bool
    full_raise: bool  # bet/raise that reopened the betting


@dataclass(frozen=True, slots=True)
class BoardDealt:
    street: Street
    cards: tuple[Card, ...]  # the newly dealt cards


@dataclass(frozen=True, slots=True)
class CardsExposed:
    """A live hand turned face up before showdown because betting is closed."""

    seat: int
    cards: tuple[Card, Card]


@dataclass(frozen=True, slots=True)
class UncalledBetReturned:
    seat: int
    amount: int


@dataclass(frozen=True, slots=True)
class ShowdownRevealed:
    seat: int
    cards: tuple[Card, Card]
    value: HandValue
    best_five: tuple[Card, ...]


@dataclass(frozen=True, slots=True)
class PotAwarded:
    pot_index: int
    amount: int
    winners: tuple[int, ...]
    shares: Mapping[int, int]
    value: HandValue | None


@dataclass(frozen=True, slots=True)
class HandEnded:
    went_to_showdown: bool
    final_stacks: Mapping[int, int]
    net: Mapping[int, int]  # seat -> final stack minus starting stack


HandEvent = (
    HandStarted | BlindPosted | HoleCardsDealt | PlayerActed | BoardDealt
    | CardsExposed | UncalledBetReturned | ShowdownRevealed | PotAwarded | HandEnded
)
