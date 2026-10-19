"""Hand evaluation: best five-card hand from five to seven cards.

``evaluate`` works directly on rank/suit counts (no 21-combination loop), so it
is fast enough for opponent simulations. ``HandValue`` objects compare with the
normal operators: a greater value is a stronger hand, equal values tie.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from enum import IntEnum
from itertools import combinations

from poker.cards import RANK_NAMES, Card, Rank


class HandCategory(IntEnum):
    HIGH_CARD = 1
    ONE_PAIR = 2
    TWO_PAIR = 3
    THREE_OF_A_KIND = 4
    STRAIGHT = 5
    FLUSH = 6
    FULL_HOUSE = 7
    FOUR_OF_A_KIND = 8
    STRAIGHT_FLUSH = 9

    @property
    def label(self) -> str:
        return _CATEGORY_LABELS[self]


_CATEGORY_LABELS = {
    HandCategory.HIGH_CARD: "High card",
    HandCategory.ONE_PAIR: "One pair",
    HandCategory.TWO_PAIR: "Two pair",
    HandCategory.THREE_OF_A_KIND: "Three of a kind",
    HandCategory.STRAIGHT: "Straight",
    HandCategory.FLUSH: "Flush",
    HandCategory.FULL_HOUSE: "Full house",
    HandCategory.FOUR_OF_A_KIND: "Four of a kind",
    HandCategory.STRAIGHT_FLUSH: "Straight flush",
}


@dataclass(frozen=True, order=True, slots=True)
class HandValue:
    """Category first, then tie-break ranks in significance order.

    For straights the tie-break is the high card, with the wheel (A-2-3-4-5)
    counted as five-high.
    """

    category: HandCategory
    tiebreak: tuple[int, ...]

    @property
    def is_royal_flush(self) -> bool:
        return self.category == HandCategory.STRAIGHT_FLUSH and self.tiebreak[0] == Rank.ACE

    def describe(self) -> str:
        r = [Rank(v) for v in self.tiebreak]
        name = lambda rank: RANK_NAMES[rank]  # noqa: E731
        plural = lambda rank: _plural(RANK_NAMES[rank])  # noqa: E731
        match self.category:
            case HandCategory.STRAIGHT_FLUSH:
                if self.is_royal_flush:
                    return "Royal flush"
                return f"Straight flush, {name(r[0])} high"
            case HandCategory.FOUR_OF_A_KIND:
                return f"Four of a kind, {plural(r[0])}"
            case HandCategory.FULL_HOUSE:
                return f"Full house, {plural(r[0])} full of {plural(r[1])}"
            case HandCategory.FLUSH:
                return f"Flush, {name(r[0])} high"
            case HandCategory.STRAIGHT:
                return f"Straight, {name(r[0])} high"
            case HandCategory.THREE_OF_A_KIND:
                return f"Three of a kind, {plural(r[0])}"
            case HandCategory.TWO_PAIR:
                return f"Two pair, {plural(r[0])} and {plural(r[1])}"
            case HandCategory.ONE_PAIR:
                return f"Pair of {plural(r[0])}"
            case _:
                return f"High card, {name(r[0])}"


def _plural(word: str) -> str:
    return word + ("es" if word == "Six" else "s")


def _straight_high(ranks: set[int]) -> int | None:
    """Highest straight in a set of rank values, treating the ace as low too."""
    if Rank.ACE in ranks:
        ranks = ranks | {1}
    for high in range(Rank.ACE, Rank.FIVE - 1, -1):
        if all(high - offset in ranks for offset in range(5)):
            return high
    return None


def evaluate(cards: Sequence[Card]) -> HandValue:
    """Value of the best five-card hand among 5 to 7 distinct cards."""
    if not 5 <= len(cards) <= 7:
        raise ValueError(f"Expected 5 to 7 cards, got {len(cards)}")
    if len(set(cards)) != len(cards):
        raise ValueError("Duplicate cards in hand")

    by_suit: dict[object, list[int]] = {}
    for card in cards:
        by_suit.setdefault(card.suit, []).append(int(card.rank))
    flush_ranks = next((sorted(r, reverse=True) for r in by_suit.values() if len(r) >= 5), None)

    if flush_ranks is not None:
        high = _straight_high(set(flush_ranks))
        if high is not None:
            return HandValue(HandCategory.STRAIGHT_FLUSH, (high,))

    counts = Counter(int(card.rank) for card in cards)
    # Ranks ordered by (multiplicity, rank), strongest group first.
    groups = sorted(counts.items(), key=lambda item: (item[1], item[0]), reverse=True)
    distinct = sorted(counts, reverse=True)

    top_rank, top_count = groups[0]
    if top_count == 4:
        kicker = max(r for r in distinct if r != top_rank)
        return HandValue(HandCategory.FOUR_OF_A_KIND, (top_rank, kicker))

    if top_count == 3:
        pair_ranks = [r for r, c in groups[1:] if c >= 2]
        if pair_ranks:
            return HandValue(HandCategory.FULL_HOUSE, (top_rank, max(pair_ranks)))

    if flush_ranks is not None:
        return HandValue(HandCategory.FLUSH, tuple(flush_ranks[:5]))

    high = _straight_high(set(distinct))
    if high is not None:
        return HandValue(HandCategory.STRAIGHT, (high,))

    if top_count == 3:
        kickers = [r for r in distinct if r != top_rank][:2]
        return HandValue(HandCategory.THREE_OF_A_KIND, (top_rank, *kickers))

    pairs = sorted((r for r, c in counts.items() if c == 2), reverse=True)
    if len(pairs) >= 2:
        high_pair, low_pair = pairs[:2]
        kicker = max(r for r in distinct if r not in (high_pair, low_pair))
        return HandValue(HandCategory.TWO_PAIR, (high_pair, low_pair, kicker))

    if len(pairs) == 1:
        kickers = [r for r in distinct if r != pairs[0]][:3]
        return HandValue(HandCategory.ONE_PAIR, (pairs[0], *kickers))

    return HandValue(HandCategory.HIGH_CARD, tuple(distinct[:5]))


def best_five(cards: Sequence[Card]) -> tuple[HandValue, tuple[Card, ...]]:
    """Best value plus the five cards that make it (for display/highlighting)."""
    value = evaluate(cards)
    if len(cards) == 5:
        return value, tuple(cards)
    for combo in combinations(cards, 5):
        if evaluate(combo) == value:
            return value, combo
    raise AssertionError("unreachable: some five-card subset has the best value")
