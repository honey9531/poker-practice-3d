"""Hand-strength estimates used by the computer opponents.

Practical heuristics, not a solver:

* ``preflop_strength``: the Chen formula, normalised to 0..1.
* ``equity``: seeded Monte Carlo estimate of winning chances against random
  hands for the remaining opponents (ties count as a share).
* ``draws``: flush and straight draws, with an estimate of outs.
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence
from dataclasses import dataclass

from poker.cards import FULL_DECK, Card, Rank
from poker.evaluator import HandCategory, evaluate

_CHEN_HIGH = {Rank.ACE: 10, Rank.KING: 8, Rank.QUEEN: 7, Rank.JACK: 6}
_CHEN_MIN, _CHEN_MAX = -1.5, 20.0


def chen_score(hole: Sequence[Card]) -> float:
    """Bill Chen's starting-hand score (pairs of aces = 20, worst hands about -1)."""
    a, b = sorted(hole, key=lambda c: c.rank, reverse=True)
    high = _CHEN_HIGH.get(a.rank, a.rank / 2)
    if a.rank == b.rank:
        score = max(5.0, high * 2)
    else:
        score = high
    if a.suit == b.suit:
        score += 2
    gap = a.rank - b.rank - 1
    if a.rank != b.rank:
        score -= {0: 0, 1: 1, 2: 2, 3: 4}.get(gap, 5)
        if gap <= 1 and a.rank < Rank.QUEEN:
            score += 1  # small connectors can make straights
    return math.ceil(score)


def preflop_strength(hole: Sequence[Card]) -> float:
    """Starting-hand strength in 0..1 (AA = 1)."""
    return max(0.0, min(1.0, (chen_score(hole) - _CHEN_MIN) / (_CHEN_MAX - _CHEN_MIN)))


def equity(
    hole: Sequence[Card],
    board: Sequence[Card],
    opponents: int,
    samples: int,
    rng: random.Random,
) -> float:
    """Estimated share of the pot won at showdown against ``opponents`` random hands."""
    if opponents <= 0:
        return 1.0
    known = set(hole) | set(board)
    deck = [c for c in FULL_DECK if c not in known]
    missing = 5 - len(board)
    need = missing + 2 * opponents
    total = 0.0
    for _ in range(samples):
        drawn = rng.sample(deck, need)
        full_board = list(board) + drawn[:missing]
        mine = evaluate(list(hole) + full_board)
        best_other = None
        ties = 0
        beaten = False
        for i in range(opponents):
            start = missing + 2 * i
            theirs = evaluate(drawn[start:start + 2] + full_board)
            if theirs > mine:
                beaten = True
                break
            if theirs == mine:
                ties += 1
            if best_other is None or theirs > best_other:
                best_other = theirs
        if not beaten:
            total += 1.0 / (ties + 1)
    return total / samples


@dataclass(frozen=True, slots=True)
class Draws:
    flush_draw: bool
    open_ended: bool
    gutshot: bool

    @property
    def outs(self) -> int:
        outs = 9 if self.flush_draw else 0
        if self.open_ended:
            outs += 8 if not self.flush_draw else 6  # overlap with the flush outs
        elif self.gutshot:
            outs += 4 if not self.flush_draw else 3
        return outs

    @property
    def any(self) -> bool:
        return self.flush_draw or self.open_ended or self.gutshot


def draws(hole: Sequence[Card], board: Sequence[Card]) -> Draws:
    """Draws that use at least one hole card (meaningful on the flop and turn)."""
    cards = list(hole) + list(board)
    if len(board) < 3 or len(board) >= 5:
        return Draws(False, False, False)
    current = evaluate(cards).category
    flush_draw = False
    if current < HandCategory.FLUSH:
        for suit in {c.suit for c in hole}:
            if sum(c.suit == suit for c in cards) == 4:
                flush_draw = True
    open_ended = gutshot = False
    if current < HandCategory.STRAIGHT:
        def with_low_ace(rs: set[int]) -> set[int]:
            return rs | ({1} if 14 in rs else set())

        ranks = with_low_ace({int(c.rank) for c in cards})
        hole_ranks = with_low_ace({int(c.rank) for c in hole})
        for low in range(1, 12):
            run = set(range(low, low + 4))
            # Four in a row that can be completed at both ends (8 outs).
            if run <= ranks and run & hole_ranks and low - 1 >= 1 and low + 4 <= 14:
                open_ended = True
        for low in range(1, 11):
            window = set(range(low, low + 5))
            have = window & ranks
            # Four of five (inside or one-ended): 4 outs.
            if len(have) == 4 and have & hole_ranks:
                gutshot = True
    return Draws(flush_draw, open_ended, gutshot and not open_ended)


def made_hand_category(hole: Sequence[Card], board: Sequence[Card]) -> HandCategory:
    return evaluate(list(hole) + list(board)).category


_RANKED_COMBOS: list[tuple[Card, Card]] | None = None


def ranked_combos() -> list[tuple[Card, Card]]:
    """All 1,326 starting hands, strongest first by pre-flop strength (computed once)."""
    global _RANKED_COMBOS
    if _RANKED_COMBOS is None:
        from itertools import combinations as _combinations

        combos = list(_combinations(FULL_DECK, 2))
        combos.sort(key=lambda hand: chen_score(hand), reverse=True)
        _RANKED_COMBOS = combos
    return _RANKED_COMBOS


def equity_vs_range(
    hole: Sequence[Card],
    board: Sequence[Card],
    range_fraction: float,
    samples: int,
    rng: random.Random,
) -> float:
    """Share of the pot won against one opponent holding the top ``range_fraction`` of hands."""
    known = set(hole) | set(board)
    combos = ranked_combos()
    top = combos[: max(1, round(len(combos) * range_fraction))]
    candidates = [c for c in top if c[0] not in known and c[1] not in known]
    if not candidates:
        return 0.5
    deck = [c for c in FULL_DECK if c not in known]
    missing = 5 - len(board)
    total = 0.0
    for _ in range(samples):
        villain = rng.choice(candidates)
        remaining = [c for c in deck if c not in villain]
        full_board = list(board) + rng.sample(remaining, missing)
        mine = evaluate(list(hole) + full_board)
        theirs = evaluate(list(villain) + full_board)
        total += 1.0 if mine > theirs else 0.5 if mine == theirs else 0.0
    return total / samples
