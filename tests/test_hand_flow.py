"""Complete hands: showdowns, side pots, split pots, and randomized invariants."""

import random

import pytest

from poker import Action, ActionType, HandCategory, Street, Table
from poker.events import (
    BlindPosted,
    BoardDealt,
    HandEnded,
    HandStarted,
    HoleCardsDealt,
    PlayerActed,
    PotAwarded,
    ShowdownRevealed,
)
from poker_helpers import make_hand


def play(hand, *steps):
    for seat, action in steps:
        hand.act(seat, action)


def test_full_hand_to_showdown_with_event_log():
    hand = make_hand(
        [1000, 1000, 1000],
        button=0,
        holes={0: "Ah Kh", 1: "Qc Qd", 2: "7s 2d"},
        board="Kd 9h 4c 2s Kc",
    )
    play(hand, (0, Action.raise_to(30)), (1, Action.call()), (2, Action.fold()))
    assert hand.street is Street.FLOP and len(hand.board) == 3
    play(hand, (1, Action.check()), (0, Action.bet(40)), (1, Action.call()))  # flop
    play(hand, (1, Action.check()), (0, Action.check()))  # turn
    play(hand, (1, Action.check()), (0, Action.bet(100)), (1, Action.call()))  # river

    result = hand.result
    assert result.went_to_showdown
    assert [str(c) for c in result.board] == ["Kd", "9h", "4c", "2s", "Kc"]
    assert result.showdown_values[0].category is HandCategory.THREE_OF_A_KIND
    assert result.showdown_values[1].category is HandCategory.TWO_PAIR
    assert result.winners == {0}
    assert result.net == {0: 180, 1: -170, 2: -10}
    assert sum(result.final_stacks.values()) == 3000

    kinds = [type(e) for e in hand.events]
    assert kinds[:4] == [HandStarted, BlindPosted, BlindPosted, HoleCardsDealt]
    assert [e.street for e in hand.events if isinstance(e, BoardDealt)] == [
        Street.FLOP, Street.TURN, Street.RIVER
    ]
    assert {e.seat for e in hand.events if isinstance(e, ShowdownRevealed)} == {0, 1}
    assert isinstance(hand.events[-1], HandEnded)


def test_three_way_all_in_with_main_and_side_pots():
    hand = make_hand(
        [100, 300, 500],
        button=0,
        holes={0: "Ac Ad", 1: "Kc Kd", 2: "7h 2c"},
        board="2s 5d 9h Js 3s",
    )
    play(hand, (0, Action.all_in()), (1, Action.all_in()), (2, Action.call()))
    assert hand.is_complete
    pots = [e for e in hand.events if isinstance(e, PotAwarded)]
    assert [(p.amount, p.winners) for p in pots] == [(300, (0,)), (400, (1,))]
    assert hand.result.final_stacks == {0: 300, 1: 400, 2: 200}


def test_short_stack_wins_main_pot_while_bigger_stack_wins_side_pot():
    hand = make_hand(
        [1000, 1000, 120],
        button=0,
        holes={0: "Qs Qh", 1: "Jc Td", 2: "Ac Ad"},
        board="Qd 8c 3h 2s 7d",
    )
    play(hand, (0, Action.raise_to(40)), (1, Action.call()), (2, Action.all_in()))
    play(hand, (0, Action.call()), (1, Action.call()))
    assert hand.street is Street.FLOP
    play(hand, (1, Action.bet(200)), (0, Action.call()))
    play(hand, (1, Action.check()), (0, Action.check()))
    play(hand, (1, Action.check()), (0, Action.check()))
    pots = [e for e in hand.events if isinstance(e, PotAwarded)]
    # Seat 2 (aces) loses to seat 0's set of queens: seat 0 wins both pots.
    assert [(p.amount, p.winners) for p in pots] == [(360, (0,)), (400, (0,))]
    assert hand.result.net == {0: 440, 1: -320, 2: -120}


def test_side_pot_eligibility_excludes_short_all_in_winner():
    hand = make_hand(
        [1000, 1000, 120],
        button=0,
        holes={0: "Kc Kd", 1: "Jc Td", 2: "Ac Ad"},
        board="Ah 8c 3h 2s 7d",
    )
    play(hand, (0, Action.raise_to(40)), (1, Action.call()), (2, Action.all_in()))
    play(hand, (0, Action.call()), (1, Action.call()))
    play(hand, (1, Action.bet(200)), (0, Action.call()))
    play(hand, (1, Action.check()), (0, Action.check()))
    play(hand, (1, Action.check()), (0, Action.check()))
    pots = [e for e in hand.events if isinstance(e, PotAwarded)]
    assert [(p.amount, p.winners) for p in pots] == [(360, (2,)), (400, (0,))]
    assert hand.result.final_stacks == {0: 1080, 1: 680, 2: 360}


def test_split_pot_with_odd_chip_to_first_seat_left_of_button():
    hand = make_hand(
        [1000, 1000, 1000],
        button=0,
        holes={0: "2c 3d", 1: "4c 5d", 2: "2d 3h"},
        board="Ac Kd Qh Js Tc",
    )
    play(hand, (0, Action.call()), (1, Action.fold()), (2, Action.check()))
    for _ in range(3):
        play(hand, (2, Action.check()), (0, Action.check()))
    award = next(e for e in hand.events if isinstance(e, PotAwarded))
    assert award.amount == 25
    assert award.winners == (2, 0)
    assert award.shares == {2: 13, 0: 12}
    assert hand.result.final_stacks == {0: 1002, 1: 995, 2: 1003}


def test_every_street_dealt_on_all_in_runout_even_after_flop():
    hand = make_hand([1000, 400], button=0, holes={0: "Ac Kc", 1: "9d 9s"}, board="2c 7c Jd 4h 9c")
    play(hand, (0, Action.call()), (1, Action.check()))
    play(hand, (1, Action.all_in()), (0, Action.call()))
    streets = [e.street for e in hand.events if isinstance(e, BoardDealt)]
    assert streets == [Street.FLOP, Street.TURN, Street.RIVER]
    assert hand.result.showdown_values[0].category is HandCategory.FLUSH
    assert hand.result.final_stacks == {0: 1400, 1: 0}


# --- Table: consecutive hands -------------------------------------------------

def finish_with_checks(hand):
    while not hand.is_complete:
        legal = hand.legal_actions()
        hand.act(legal.seat, Action.check() if legal.can_check else Action.call())


def test_button_rotates_and_skips_busted_players():
    table = Table([("a", 100), ("b", 0), ("c", 100), ("d", 100)], 5, 10, rng=random.Random(1), button=3)
    buttons = []
    for _ in range(4):
        hand = table.start_hand()
        buttons.append(hand.button)
        assert 1 not in {p.seat for p in hand.players}
        finish_with_checks(hand)
    assert buttons == [0, 2, 3, 0]
    assert table.hand_number == 4


def test_table_settles_stacks_and_conserves_chips():
    table = Table([("a", 500), ("b", 500), ("c", 500)], 5, 10, rng=random.Random(5))
    for _ in range(10):
        hand = table.start_hand()
        finish_with_checks(hand)
        table.settle_hand()
        assert sum(s.stack for s in table.seats) == 1500
        assert table.total_chips() == 1500


def test_table_rejects_starting_a_hand_mid_hand_and_after_bust():
    table = Table([("a", 100), ("b", 100)], 5, 10, rng=random.Random(2))
    hand = table.start_hand()
    with pytest.raises(RuntimeError):
        table.start_hand()
    while not hand.is_complete:
        legal = hand.legal_actions()
        hand.act(legal.seat, Action.all_in() if legal.can_all_in else Action.call())
    table.settle_hand()
    if min(s.stack for s in table.seats) == 0:
        assert not table.can_start_hand
        with pytest.raises(RuntimeError):
            table.start_hand()


def test_table_reset_and_blind_levels():
    table = Table([("a", 100), ("b", 100)], 5, 10, rng=random.Random(3))
    finish_with_checks(table.start_hand())
    table.set_blinds(10, 20)
    hand = table.start_hand()
    assert (hand.small_blind, hand.big_blind) == (10, 20)
    finish_with_checks(hand)
    table.reset(250)
    assert [s.stack for s in table.seats] == [250, 250]
    assert table.hand_number == 0 and table.button is None
    with pytest.raises(RuntimeError):
        table.set_blinds(20, 10)


# --- Randomized invariants ----------------------------------------------------

def random_action(legal, rng):
    roll = rng.random()
    if legal.can_bet_or_raise and roll < 0.25:
        amount = rng.randint(legal.min_to, legal.max_to)
        return Action(ActionType.BET if legal.can_bet else ActionType.RAISE, amount)
    if legal.can_all_in and roll < 0.30:
        return Action.all_in()
    if roll < 0.40 and not legal.can_check:
        return Action.fold()
    return Action.check() if legal.can_check else Action.call()


@pytest.mark.parametrize("seed", range(8))
def test_random_sessions_preserve_every_invariant(seed):
    rng = random.Random(seed)
    players = [(f"p{i}", rng.randint(20, 2000)) for i in range(rng.randint(2, 6))]
    table = Table(players, 5, 10, rng=rng)
    total = table.total_chips()
    hands = 0
    while table.can_start_hand and hands < 150:
        hand = table.start_hand()
        hands += 1
        steps = 0
        while not hand.is_complete:
            legal = hand.legal_actions()
            step = hand.action_count
            hand.act(legal.seat, random_action(legal, rng), expected_action_count=step)
            steps += 1
            assert steps < 500, "hand did not terminate"
            assert hand.total_chips() == total
            assert all(p.stack >= 0 for p in hand.players)
            assert hand.action_count == step + 1

        result = hand.result
        cards = [c for p in hand.players for c in p.hole] + hand.board + hand.burned
        assert len(cards) == len(set(cards)), "duplicate card dealt"
        if result.went_to_showdown:
            assert len(result.board) == 5
            assert len(hand.live_players) >= 2
        else:
            assert len(hand.live_players) == 1
        awarded = [e for e in hand.events if isinstance(e, PotAwarded)]
        assert all(sum(e.shares.values()) == e.amount for e in awarded)
        contributed = sum(p.total_bet for p in hand.players)
        assert sum(e.amount for e in awarded) == contributed
        assert sum(result.net.values()) == 0
        assert all(e.action is not ActionType.ALL_IN for e in hand.events if isinstance(e, PlayerActed))
        table.settle_hand()
        assert table.total_chips() == total
    assert hands > 0


def test_live_hands_exposed_before_all_in_runout():
    from poker.events import CardsExposed

    hand = make_hand([1000, 400], button=0, holes={0: "Ac Kc", 1: "9d 9s"}, board="2c 7c Jd 4h 9c")
    play(hand, (0, Action.call()), (1, Action.check()))
    play(hand, (1, Action.all_in()), (0, Action.call()))
    kinds = [type(e).__name__ for e in hand.events]
    first_exposed = kinds.index("CardsExposed")
    turn_dealt = max(i for i, e in enumerate(hand.events) if isinstance(e, BoardDealt))
    assert first_exposed < turn_dealt
    exposed = [e for e in hand.events if isinstance(e, CardsExposed)]
    assert {e.seat for e in exposed} == {0, 1}
    assert kinds.count("CardsExposed") == 2


def test_no_exposure_when_hand_reaches_river_with_betting():
    from poker.events import CardsExposed

    hand = make_hand([1000, 1000], button=0)
    play(hand, (0, Action.call()), (1, Action.check()))
    for _ in range(3):
        play(hand, (1, Action.check()), (0, Action.check()))
    assert not any(isinstance(e, CardsExposed) for e in hand.events)
