"""A 52-card deck that can never deal the same card twice."""

from __future__ import annotations

import random
from collections.abc import Iterable

from poker.cards import FULL_DECK, Card


class DeckError(RuntimeError):
    pass


class Deck:
    """Cards are dealt from the front of ``_cards``."""

    def __init__(self, rng: random.Random | None = None) -> None:
        cards = list(FULL_DECK)
        (rng or random.Random()).shuffle(cards)
        self._cards = cards
        self._position = 0

    @classmethod
    def stacked(cls, top: Iterable[Card], rng: random.Random | None = None) -> "Deck":
        """Deck whose first cards are ``top`` (in order); the rest are shuffled.

        Used for deterministic scenarios and replays.
        """
        top = list(top)
        if len(set(top)) != len(top):
            raise DeckError("Duplicate cards in stacked deck")
        rest = [card for card in FULL_DECK if card not in set(top)]
        (rng or random.Random(0)).shuffle(rest)
        deck = cls.__new__(cls)
        deck._cards = top + rest
        deck._position = 0
        return deck

    @property
    def remaining(self) -> int:
        return len(self._cards) - self._position

    @property
    def dealt(self) -> tuple[Card, ...]:
        return tuple(self._cards[: self._position])

    def deal(self, count: int = 1) -> list[Card]:
        if count < 0:
            raise ValueError("count must be non-negative")
        if count > self.remaining:
            raise DeckError(f"Cannot deal {count} cards; {self.remaining} remain")
        cards = self._cards[self._position: self._position + count]
        self._position += count
        return cards

    def deal_one(self) -> Card:
        return self.deal(1)[0]
