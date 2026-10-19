import pytest

from poker import Pot, award_pots, build_pots, parse_cards
from poker.evaluator import evaluate
from poker.pots import split_amount


def test_single_pot_without_all_ins():
    pots = build_pots({0: 100, 1: 100, 2: 100}, {0, 1, 2})
    assert pots == [Pot(300, frozenset({0, 1, 2}))]


def test_folded_contributions_stay_in_pot_but_are_not_eligible():
    pots = build_pots({0: 100, 1: 100, 2: 40}, {0, 1})
    assert pots == [Pot(240, frozenset({0, 1}))]


def test_short_all_in_creates_side_pot():
    # Seat 2 all-in for 50; seats 0 and 1 continue to 200.
    pots = build_pots({0: 200, 1: 200, 2: 50}, {0, 1, 2})
    assert pots == [Pot(150, frozenset({0, 1, 2})), Pot(300, frozenset({0, 1}))]


def test_multiple_side_pots():
    contributions = {0: 25, 1: 100, 2: 300, 3: 300, 4: 60}
    live = {0, 1, 2, 3}  # seat 4 folded after putting in 60
    pots = build_pots(contributions, live)
    assert pots == [
        Pot(125, frozenset({0, 1, 2, 3})),  # 25 x 5
        Pot(75 + 35 + 75 + 75, frozenset({1, 2, 3})),  # 25..100
        Pot(400, frozenset({2, 3})),  # 100..300
    ]
    assert sum(p.amount for p in pots) == sum(contributions.values())


def test_folded_player_above_live_levels_goes_to_last_pot():
    pots = build_pots({0: 50, 1: 80}, {0})
    assert pots == [Pot(130, frozenset({0}))]


def test_negative_contribution_rejected():
    with pytest.raises(ValueError):
        build_pots({0: -1, 1: 10}, {0, 1})


@pytest.mark.parametrize(
    "amount, winners, expected",
    [
        (100, [0, 1], {0: 50, 1: 50}),
        (101, [3, 1], {3: 51, 1: 50}),
        (100, [2, 0, 1], {2: 34, 0: 33, 1: 33}),
        (7, [5], {5: 7}),
    ],
)
def test_split_amount_gives_odd_chips_in_order(amount, winners, expected):
    assert split_amount(amount, winners) == expected


def test_award_main_and_side_pots_to_different_winners():
    board = parse_cards("2c 7d 9h Js Kc")
    values = {
        0: evaluate(board + parse_cards("Ac Ad")),  # best: wins main pot only
        1: evaluate(board + parse_cards("Qd Qs")),  # second: wins side pot
        2: evaluate(board + parse_cards("3c 4d")),
    }
    pots = build_pots({0: 50, 1: 200, 2: 200}, {0, 1, 2})
    awards = award_pots(pots, values, seat_order=[1, 2, 0])
    assert [(a.amount, a.winners) for a in awards] == [(150, (0,)), (300, (1,))]


def test_award_split_pot_with_odd_chip_order():
    board = parse_cards("Ac Kd Qh Js Tc")  # board plays: everyone ties
    values = {s: evaluate(board + parse_cards(h)) for s, h in {0: "2c 3d", 1: "2d 3h", 2: "4c 5d"}.items()}
    pots = [Pot(101, frozenset({0, 1, 2}))]
    awards = award_pots(pots, values, seat_order=[2, 0, 1])
    assert awards[0].winners == (2, 0, 1)
    assert awards[0].shares == {2: 34, 0: 34, 1: 33}


def test_uncontested_pot_needs_no_hand_values():
    awards = award_pots([Pot(60, frozenset({1}))], {}, seat_order=[0, 1])
    assert awards[0].winners == (1,)
    assert awards[0].value is None
