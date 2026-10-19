"""Playing-card primitives. Pure data; no presentation concerns."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, IntEnum


class Suit(Enum):
    CLUBS = "c"
    DIAMONDS = "d"
    HEARTS = "h"
    SPADES = "s"

    @property
    def is_red(self) -> bool:
        return self in (Suit.HEARTS, Suit.DIAMONDS)


class Rank(IntEnum):
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13
    ACE = 14

    @property
    def char(self) -> str:
        return _RANK_CHARS[self - 2]

    @classmethod
    def from_char(cls, char: str) -> "Rank":
        index = _RANK_CHARS.find(char.upper())
        if index < 0 or len(char) != 1:
            raise ValueError(f"Invalid rank: {char!r}")
        return cls(index + 2)


_RANK_CHARS = "23456789TJQKA"

RANK_NAMES = {
    Rank.TWO: "Two", Rank.THREE: "Three", Rank.FOUR: "Four", Rank.FIVE: "Five",
    Rank.SIX: "Six", Rank.SEVEN: "Seven", Rank.EIGHT: "Eight", Rank.NINE: "Nine",
    Rank.TEN: "Ten", Rank.JACK: "Jack", Rank.QUEEN: "Queen", Rank.KING: "King",
    Rank.ACE: "Ace",
}


@dataclass(frozen=True, slots=True)
class Card:
    rank: Rank
    suit: Suit

    @classmethod
    def from_str(cls, text: str) -> "Card":
        """Parse ``"As"``, ``"Td"``, ``"2c"`` (rank char + suit char)."""
        if len(text) != 2:
            raise ValueError(f"Invalid card: {text!r}")
        try:
            suit = Suit(text[1].lower())
        except ValueError:
            raise ValueError(f"Invalid suit in card: {text!r}") from None
        return cls(Rank.from_char(text[0]), suit)

    @property
    def code(self) -> str:
        return f"{self.rank.char}{self.suit.value}"

    def __str__(self) -> str:
        return self.code

    def __repr__(self) -> str:
        return f"Card({self.code})"


def parse_cards(text: str) -> list[Card]:
    """Parse whitespace-separated or concatenated cards: ``"As Kd"`` or ``"AsKd"``."""
    compact = "".join(text.split())
    if len(compact) % 2:
        raise ValueError(f"Invalid card list: {text!r}")
    return [Card.from_str(compact[i:i + 2]) for i in range(0, len(compact), 2)]


FULL_DECK: tuple[Card, ...] = tuple(Card(rank, suit) for suit in Suit for rank in Rank)
