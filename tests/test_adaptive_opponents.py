"""Opponents read public betting habits and call habitual all-ins."""

import random

import pytest

from ai import create_strategy, observe, tendencies
from ai.hand_strength import equity_vs_range, ranked_combos
from poker import Action, ActionType, parse_cards
from poker_helpers import make_hand
from services.game_session import GameSession, SessionConfig


def test_ranked_combos_cover_every_starting_hand_strongest_first():
    combos = ranked_combos()
    assert len(combos) == 1326 and len(set(combos)) == 1326
    assert {c.rank for c in combos[0]} == {14}  # a pair of aces is first


@pytest.mark.parametrize(
    "hole, fraction, low, high",
    [
        ("AsAd", 0.05, 0.75, 0.95),  # aces against a tight range
        ("Ks7d", 0.05, 0.15, 0.40),  # weak ace-less hand against a tight range
        ("Ks7d", 1.0, 0.50, 0.70),  # the same hand against any two cards
    ],
)
def test_equity_against_ranges(hole, fraction, low, high):
    estimate = equity_vs_range(parse_cards(hole), [], fraction, 1500, random.Random(3))
    assert low <= estimate <= high


def test_tendencies_count_public_preflop_aggression():
    hand = make_hand([1000, 1000, 1000], button=0)
    hand.act(0, Action.all_in())
    hand.act(1, Action.fold())
    hand.act(2, Action.fold())
    stats = {}
    tendencies.update(stats, hand.events)
    assert stats[0] == tendencies.Tendency(hands=1, preflop_raises=1, preflop_all_ins=1)
    assert stats[1] == tendencies.Tendency(hands=1)


def test_estimated_range_starts_tight_and_widens_with_repeated_shoves():
    unknown = tendencies.estimated_range(None, all_in=True, prior_weight=6)
    assert unknown == pytest.approx(tendencies.PRIOR_SHOVE_RANGE)
    habitual = tendencies.Tendency(hands=6, preflop_raises=6, preflop_all_ins=6)
    assert tendencies.estimated_range(habitual, all_in=True, prior_weight=6) > 0.5
    rare = tendencies.Tendency(hands=40, preflop_raises=2, preflop_all_ins=1)
    assert tendencies.estimated_range(rare, all_in=True, prior_weight=6) < unknown


def facing_a_shove(hole, shover_stats):
    """Seat 2 (big blind) decides against seat 0's 100-big-blind all-in."""
    hand = make_hand([2000, 2000, 2000], button=0, sb=10, bb=20, holes={2: hole})
    hand.act(0, Action.all_in())
    hand.act(1, Action.fold())
    ctx = observe(hand, 2, {0: shover_stats} if shover_stats else None)
    calls = 0
    for seed in range(20):
        action = create_strategy("balanced", "normal", random.Random(seed)).decide(ctx)
        calls += action.type is ActionType.CALL
    return calls


def test_medium_hand_folds_to_unknown_shover_but_calls_habitual_one():
    assert facing_a_shove("Ad9c", None) <= 2
    habitual = tendencies.Tendency(hands=8, preflop_raises=8, preflop_all_ins=8)
    assert facing_a_shove("Ad9c", habitual) >= 18


def test_premium_hand_calls_even_an_unknown_shover():
    assert facing_a_shove("KhKd", None) >= 18


def test_session_records_tendencies_after_each_hand():
    session = GameSession(SessionConfig(opponents=2, seed=7))
    session.start_hand()
    while not session.hand_over:
        while session.next_event() is not None:
            pass
        if session.opponent_to_act is not None:
            session.play_opponent_action()
        elif session.human_to_act:
            legal = session.hand.legal_actions()
            session.apply_human_action("all_in" if legal.can_all_in else "call", 0, session.hand.action_count)
    assert session.tendencies[0].hands == 1
    assert session.tendencies[0].preflop_all_ins == 1


def test_shoving_every_hand_is_not_a_winning_strategy():
    """Regression: opponents used to fold to every all-in, so shoving always won."""
    results = []
    # Enough sessions that luck cannot make the average positive (seeded, so stable).
    for seed in range(32):
        session = GameSession(SessionConfig(opponents=3, seed=seed))
        while session.can_start_hand and session.table.hand_number < 40:
            session.start_hand()
            while not session.hand_over:
                while session.next_event() is not None:
                    pass
                if session.opponent_to_act is not None:
                    session.play_opponent_action()
                elif session.human_to_act:
                    legal = session.hand.legal_actions()
                    kind = "all_in" if legal.can_all_in else ("call" if legal.can_call else "check")
                    session.apply_human_action(kind, 0, session.hand.action_count)
        results.append(session.table.seats[0].stack - 2000)
    busted = sum(r == -2000 for r in results)
    assert busted >= len(results) // 2
    assert sum(results) / len(results) < 0
