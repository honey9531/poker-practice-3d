"""Betting rules: positions, legal actions, minimum raises, all-ins, validation."""

import pytest

from poker import (
    Action,
    ActionType,
    HandStateError,
    HoldemHand,
    IllegalActionError,
    SeatSpec,
    StaleActionError,
    Street,
)
from poker.events import BlindPosted, PlayerActed, UncalledBetReturned
from poker_helpers import make_hand

# Three-handed with button 0: seat 1 small blind, seat 2 big blind, seat 0 first pre-flop.


def three_handed(stacks=(1000, 1000, 1000), **kw):
    return make_hand(list(stacks), button=0, **kw)


def test_blinds_and_first_to_act_three_handed():
    hand = three_handed()
    assert [hand.player(s).street_bet for s in (0, 1, 2)] == [0, 5, 10]
    assert hand.current_bet == 10
    assert hand.total_pot == 15
    assert hand.to_act == 0
    assert hand.street is Street.PREFLOP
    assert all(len(p.hole) == 2 for p in hand.players)


def test_heads_up_button_posts_small_blind_and_acts_first_preflop_only():
    hand = make_hand([1000, 1000], button=0)
    blinds = [e for e in hand.events if isinstance(e, BlindPosted)]
    assert [(b.seat, b.amount) for b in blinds] == [(0, 5), (1, 10)]
    assert hand.to_act == 0
    hand.act(0, Action.call())
    hand.act(1, Action.check())
    assert hand.street is Street.FLOP
    assert hand.to_act == 1  # big blind acts first after the flop


def test_postflop_action_starts_left_of_button():
    hand = three_handed()
    hand.act(0, Action.call())
    hand.act(1, Action.call())
    hand.act(2, Action.check())
    assert hand.street is Street.FLOP
    assert len(hand.board) == 3
    assert hand.to_act == 1
    assert hand.current_bet == 0


def test_legal_actions_facing_big_blind():
    legal = three_handed().legal_actions()
    assert legal.seat == 0
    assert legal.can_fold and legal.can_call and not legal.can_check
    assert legal.call_amount == 10
    assert legal.can_raise and not legal.can_bet
    assert (legal.min_to, legal.max_to) == (20, 1000)
    assert legal.can_all_in


def test_big_blind_option_to_raise_when_limped_to():
    hand = three_handed()
    hand.act(0, Action.call())
    hand.act(1, Action.call())
    legal = hand.legal_actions()
    assert legal.seat == 2
    assert legal.can_check and legal.can_raise and not legal.can_call
    assert legal.min_to == 20
    hand.act(2, Action.raise_to(40))
    assert hand.street is Street.PREFLOP
    assert hand.to_act == 0


def test_minimum_raise_tracks_largest_increment():
    hand = three_handed()
    hand.act(0, Action.raise_to(30))  # +20
    assert hand.legal_actions().min_to == 50
    with pytest.raises(IllegalActionError):
        hand.act(1, Action.raise_to(45))
    hand.act(1, Action.raise_to(80))  # +50
    assert hand.min_raise == 50
    assert hand.legal_actions().min_to == 130


def test_postflop_minimum_bet_is_big_blind():
    hand = three_handed()
    hand.act(0, Action.call())
    hand.act(1, Action.call())
    hand.act(2, Action.check())
    legal = hand.legal_actions()
    assert legal.can_bet and legal.can_check and not legal.can_raise
    assert legal.min_to == 10
    with pytest.raises(IllegalActionError):
        hand.act(1, Action.bet(5))
    hand.act(1, Action.bet(10))
    assert hand.legal_actions().min_to == 20


@pytest.mark.parametrize(
    "action",
    [
        Action.check(),  # facing the big blind
        Action.bet(20),  # a bet already exists: must raise
        Action.raise_to(15),  # below minimum
        Action.raise_to(1001),  # above stack
    ],
)
def test_illegal_actions_are_rejected_without_changing_state(action):
    hand = three_handed()
    before = (hand.action_count, hand.player(0).stack, hand.to_act)
    with pytest.raises(IllegalActionError):
        hand.act(0, action)
    assert (hand.action_count, hand.player(0).stack, hand.to_act) == before


def test_acting_out_of_turn_is_rejected():
    hand = three_handed()
    with pytest.raises(IllegalActionError):
        hand.act(1, Action.call())


def test_duplicate_and_stale_submissions_are_rejected():
    hand = three_handed()
    step = hand.action_count
    hand.act(0, Action.call(), expected_action_count=step)
    with pytest.raises(StaleActionError):
        hand.act(1, Action.call(), expected_action_count=step)
    hand.act(1, Action.call(), expected_action_count=step + 1)


def test_fold_to_big_blind_returns_uncalled_chips():
    hand = three_handed()
    hand.act(0, Action.fold())
    hand.act(1, Action.fold())
    assert hand.is_complete
    assert not hand.result.went_to_showdown
    assert hand.result.net == {0: 0, 1: -5, 2: 5}
    assert UncalledBetReturned(2, 5) in hand.events
    with pytest.raises(HandStateError):
        hand.act(2, Action.check())


def test_uncalled_bet_returned_when_everyone_folds_postflop():
    hand = three_handed()
    for seat, action in [(0, Action.call()), (1, Action.call()), (2, Action.check())]:
        hand.act(seat, action)
    hand.act(1, Action.bet(200))
    hand.act(2, Action.fold())
    hand.act(0, Action.fold())
    assert UncalledBetReturned(1, 200) in hand.events
    assert hand.result.final_stacks == {0: 990, 1: 1020, 2: 990}


def test_incomplete_all_in_raise_does_not_reopen_betting():
    hand = three_handed(stacks=(1000, 140, 1000))
    hand.act(0, Action.raise_to(100))  # +90
    hand.act(1, Action.all_in())  # to 140: +40, incomplete
    acted = [e for e in hand.events if isinstance(e, PlayerActed)][-1]
    assert acted.action is ActionType.RAISE and acted.all_in and not acted.full_raise
    assert hand.current_bet == 140 and hand.min_raise == 90

    bb = hand.legal_actions()  # big blind has not acted yet: may raise
    assert bb.seat == 2 and bb.can_raise and bb.min_to == 230
    hand.act(2, Action.fold())

    opener = hand.legal_actions()
    assert opener.seat == 0
    assert opener.can_call and opener.call_amount == 40
    assert not opener.can_raise and not opener.can_all_in
    with pytest.raises(IllegalActionError):
        hand.act(0, Action.raise_to(300))
    with pytest.raises(IllegalActionError):
        hand.act(0, Action.all_in())
    hand.act(0, Action.call())
    assert hand.is_complete  # one player all-in, board runs out
    assert len(hand.board) == 5


def _four_handed_flop(seat3_stack):
    """Seat 1 opens the flop; seats 2 and 3 have short stacks."""
    hand = make_hand([1000, 1000, 160, seat3_stack], button=0)
    for seat, action in [(3, Action.call()), (0, Action.call()), (1, Action.call()), (2, Action.check())]:
        hand.act(seat, action)
    assert hand.street is Street.FLOP and hand.to_act == 1
    hand.act(1, Action.bet(100))
    hand.act(2, Action.all_in())  # 150: +50, incomplete
    hand.act(3, Action.all_in())
    hand.act(0, Action.call())
    return hand


def test_short_all_ins_that_add_up_to_a_full_raise_reopen_betting():
    hand = _four_handed_flop(seat3_stack=220)  # all-in to 210: total +110 over the 100 bet
    legal = hand.legal_actions()
    assert legal.seat == 1 and legal.can_raise
    assert legal.min_to == 310


def test_short_all_ins_below_a_full_raise_keep_betting_closed():
    hand = _four_handed_flop(seat3_stack=190)  # all-in to 180: +80 over the 100 bet
    legal = hand.legal_actions()
    assert legal.seat == 1 and not legal.can_raise and legal.call_amount == 80


def test_all_in_request_resolves_to_call_when_stack_is_short():
    hand = make_hand([1000, 300], button=0)
    hand.act(0, Action.raise_to(500))
    legal = hand.legal_actions()
    assert legal.call_amount == 290 and not legal.can_raise and legal.can_all_in
    hand.act(1, Action.all_in())
    called = [e for e in hand.events if isinstance(e, PlayerActed)][-1]
    assert called.action is ActionType.CALL and called.all_in
    assert UncalledBetReturned(0, 200) in hand.events
    assert hand.is_complete and len(hand.board) == 5


def test_lone_player_with_chips_cannot_raise_all_in_players():
    hand = make_hand([1000, 1000, 50], button=0)
    hand.act(0, Action.fold())
    hand.act(1, Action.call())
    hand.act(2, Action.all_in())
    legal = hand.legal_actions()
    assert legal.seat == 1
    assert legal.can_call and legal.call_amount == 40
    assert not legal.can_raise and not legal.can_bet and not legal.can_all_in
    hand.act(1, Action.call())
    assert hand.is_complete


def test_short_blinds_post_all_in():
    hand = make_hand([1000, 3, 1000], button=0)
    blinds = [e for e in hand.events if isinstance(e, BlindPosted)]
    assert (blinds[0].seat, blinds[0].amount, blinds[0].all_in) == (1, 3, True)
    assert hand.current_bet == 10
    hand.act(0, Action.call())
    assert hand.to_act == 2  # small blind is all-in and skipped


def test_both_blinds_all_in_completes_hand_immediately():
    hand = make_hand([5, 8], button=0, sb=5, bb=10)
    assert hand.is_complete
    assert hand.to_act is None
    assert UncalledBetReturned(1, 3) in hand.events
    assert len(hand.board) == 5
    assert sum(hand.result.final_stacks.values()) == 13


def test_big_blind_covers_short_small_blind_with_no_action_needed():
    hand = make_hand([4, 1000], button=0, sb=5, bb=10)
    assert hand.is_complete  # nobody left to bet against
    assert UncalledBetReturned(1, 6) in hand.events


def test_invalid_hand_setup():
    with pytest.raises(HandStateError):
        HoldemHand([SeatSpec(0, "a", 100)], 0, 5, 10)
    with pytest.raises(HandStateError):
        HoldemHand([SeatSpec(0, "a", 100), SeatSpec(1, "b", 0)], 0, 5, 10)
    with pytest.raises(HandStateError):
        HoldemHand([SeatSpec(0, "a", 100), SeatSpec(0, "b", 100)], 0, 5, 10)
    with pytest.raises(HandStateError):
        HoldemHand([SeatSpec(0, "a", 100), SeatSpec(1, "b", 100)], 0, 10, 5)
    with pytest.raises(HandStateError):
        HoldemHand([SeatSpec(0, "a", 100), SeatSpec(1, "b", 100)], 5, 5, 10)
