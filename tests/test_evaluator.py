import random
from collections import Counter
from itertools import combinations

import pytest

from poker import FULL_DECK, HandCategory, best_five, evaluate, parse_cards

C = HandCategory


def ev(text):
    return evaluate(parse_cards(text))


@pytest.mark.parametrize(
    "cards, category, tiebreak",
    [
        ("As Ks Qs Js Ts 2d 3c", C.STRAIGHT_FLUSH, (14,)),
        ("9h 8h 7h 6h 5h Ah Kh", C.STRAIGHT_FLUSH, (9,)),
        ("Ad 2d 3d 4d 5d Kc Qc", C.STRAIGHT_FLUSH, (5,)),  # steel wheel
        ("Qc Qd Qh Qs 2c 3d 9h", C.FOUR_OF_A_KIND, (12, 9)),
        ("7c 7d 7h Kc Kd 2s 3s", C.FULL_HOUSE, (7, 13)),
        ("7c 7d 7h Kc Kd Ks 2s", C.FULL_HOUSE, (13, 7)),  # two trips
        ("7c 7d 7h Kc Kd 2s 2h", C.FULL_HOUSE, (7, 13)),  # trips + two pairs
        ("Ah Jh 9h 6h 3h 2h Kc", C.FLUSH, (14, 11, 9, 6, 3)),
        ("Tc 9d 8h 7s 6c 5d 2h", C.STRAIGHT, (10,)),
        ("Ac 2d 3h 4s 5c 9d Jh", C.STRAIGHT, (5,)),  # wheel
        ("Ac Kd Qh Js Tc 2d 3h", C.STRAIGHT, (14,)),  # broadway
        ("5c 5d 5h Ks 9c 3d 2h", C.THREE_OF_A_KIND, (5, 13, 9)),
        ("Jc Jd 4h 4s 9c 9d 2h", C.TWO_PAIR, (11, 9, 4)),  # three pairs: kicker from third pair
        ("Jc Jd 4h 4s 2c 2d Ah", C.TWO_PAIR, (11, 4, 14)),
        ("Ac Ad 9h 7s 4c 3d 2h", C.ONE_PAIR, (14, 9, 7, 4)),
        ("Ac Jd 9h 7s 4c 3d 2h", C.HIGH_CARD, (14, 11, 9, 7, 4)),
    ],
)
def test_categories_and_tiebreaks(cards, category, tiebreak):
    value = ev(cards)
    assert value.category is category
    assert value.tiebreak == tiebreak


def test_category_order():
    hands = [
        "Ac Jd 9h 7s 4c", "Ac Ad 9h 7s 4c", "Ac Ad 9h 9s 4c", "Ac Ad Ah 9s 4c",
        "Ac 2d 3h 4s 5c", "Ah Jh 9h 6h 3h", "7c 7d 7h Kc Kd", "Qc Qd Qh Qs 2c",
        "Ad 2d 3d 4d 5d",
    ]
    values = [ev(h) for h in hands]
    assert values == sorted(values)
    assert [v.category for v in values] == list(HandCategory)


def test_wheel_is_lowest_straight():
    assert ev("Ac 2d 3h 4s 5c") < ev("2c 3d 4h 5s 6c")
    assert ev("Ad 2d 3d 4d 5d") < ev("2h 3h 4h 5h 6h")
    # A-K-Q-J-T is highest; no wrap-around straights.
    assert ev("Qc Kd Ah 2s 3c").category is C.HIGH_CARD


def test_royal_flush_is_highest_straight_flush():
    royal = ev("As Ks Qs Js Ts")
    assert royal.is_royal_flush
    assert royal.describe() == "Royal flush"
    assert royal > ev("Ks Qs Js Ts 9s")
    assert not ev("Ks Qs Js Ts 9s").is_royal_flush


@pytest.mark.parametrize(
    "better, worse",
    [
        ("Ac Ad Kh 7s 4c", "Ac Ad Qh 7s 4c"),  # pair, first kicker
        ("Ac Ad Kh 7s 5c", "Ac Ad Kh 7s 4c"),  # pair, third kicker
        ("Jc Jd 4h 4s Ac", "Jc Jd 4h 4s Kc"),  # two pair kicker
        ("Jc Jd 5h 5s 2c", "Jc Jd 4h 4s Ac"),  # second pair beats kicker
        ("5c 5d 5h As 2c", "5c 5d 5h Ks Qc"),  # trips kicker
        ("Ah Jh 9h 6h 4h", "Ah Jh 9h 6h 3h"),  # flush fifth card
        ("Qc Qd Qh Qs Ac", "Qc Qd Qh Qs Kc"),  # quads kicker
        ("8c 8d 8h 2s 2c", "7c 7d 7h As Ac"),  # full house: trips first
        ("Ac Kd 9h 7s 5c", "Ac Kd 9h 7s 4c"),  # high card fifth card
    ],
)
def test_kicker_comparisons(better, worse):
    assert ev(better) > ev(worse)


def test_ties_ignore_suits_and_unused_cards():
    board = "Ac Kd Qh Js 9c"
    assert ev(board + " 2d 3h") == ev(board + " 2s 4h")  # board plays
    assert ev("Ah Ad Kh Qc 9d 3s 2s") == ev("As Ac Ks Qd 9h 4c 2c")


def test_best_five_returns_cards_making_the_hand():
    cards = parse_cards("Ah Kh Qh Jh Th 2c 2d")
    value, five = best_five(cards)
    assert value.is_royal_flush
    assert set(five) == set(parse_cards("Ah Kh Qh Jh Th"))
    assert evaluate(five) == value


def test_describe():
    assert ev("7c 7d 7h Kc Kd").describe() == "Full house, Sevens full of Kings"
    assert ev("6c 6d 6h Kc 2d").describe() == "Three of a kind, Sixes"
    assert ev("Ac 2d 3h 4s 5c").describe() == "Straight, Five high"
    assert ev("Jc Jd 4h 4s Ac").describe() == "Two pair, Jacks and Fours"
    assert ev("Ac Jd 9h 7s 4c").describe() == "High card, Ace"


@pytest.mark.parametrize("cards", ["As Ks Qs Js", "As Ks Qs Js Ts 9s 8s 7s", "As As Ks Qs Js"])
def test_invalid_input(cards):
    with pytest.raises(ValueError):
        ev(cards)


# --- Cross-check against an independent brute-force reference ------------------

def reference_five(cards):
    """Straightforward 5-card scorer written independently of the engine."""
    ranks = sorted((int(c.rank) for c in cards), reverse=True)
    flush = len({c.suit for c in cards}) == 1
    unique = sorted(set(ranks), reverse=True)
    straight_high = None
    if len(unique) == 5:
        if unique[0] - unique[4] == 4:
            straight_high = unique[0]
        elif unique == [14, 5, 4, 3, 2]:
            straight_high = 5
    counts = Counter(ranks)
    shape = sorted(counts.values(), reverse=True)
    by_count = sorted(counts, key=lambda r: (counts[r], r), reverse=True)
    if straight_high and flush:
        return (9, (straight_high,))
    if shape == [4, 1]:
        return (8, tuple(by_count))
    if shape == [3, 2]:
        return (7, tuple(by_count))
    if flush:
        return (6, tuple(ranks))
    if straight_high:
        return (5, (straight_high,))
    if shape == [3, 1, 1]:
        return (4, tuple(by_count))
    if shape == [2, 2, 1]:
        return (3, tuple(by_count))
    if shape == [2, 1, 1, 1]:
        return (2, tuple(by_count))
    return (1, tuple(ranks))


def reference_best(cards):
    return max(reference_five(combo) for combo in combinations(cards, 5))


@pytest.mark.parametrize("size", [5, 6, 7])
def test_matches_reference_on_random_hands(size):
    rng = random.Random(size)
    for _ in range(3000):
        cards = rng.sample(FULL_DECK, size)
        value = evaluate(cards)
        assert (int(value.category), value.tiebreak) == reference_best(cards), cards


def test_pairwise_comparisons_match_reference():
    rng = random.Random(99)
    for _ in range(2000):
        cards = rng.sample(FULL_DECK, 9)
        board, a, b = cards[:5], cards[5:7], cards[7:]
        ours = (evaluate(board + a) > evaluate(board + b)) - (evaluate(board + a) < evaluate(board + b))
        ref_a, ref_b = reference_best(board + a), reference_best(board + b)
        theirs = (ref_a > ref_b) - (ref_a < ref_b)
        assert ours == theirs
