"""Computer opponents: hand strength, legality, determinism, style differences."""

import random
import time

import pytest

from ai import DIFFICULTIES, STYLES, create_strategy, legalize, observe
from ai.hand_strength import draws, equity, preflop_strength
from poker import Action, ActionType, LegalActions, Table, parse_cards
from poker.events import PlayerActed, Street
from services.game_session import GameSession, SessionConfig


def cards(text):
    return parse_cards(text)


# --- hand strength ------------------------------------------------------------

def test_preflop_strength_ordering_and_range():
    order = ["AsAd", "KsKd", "AsKs", "AsKd", "QsJs", "8s8d", "5s4s", "Kd7c", "7s2d"]
    values = [preflop_strength(cards(h)) for h in order]
    assert values == sorted(values, reverse=True)
    assert values[0] == 1.0 and 0.0 <= values[-1] < 0.1


def test_suited_beats_offsuit_and_connected_beats_gapped():
    assert preflop_strength(cards("JsTs")) > preflop_strength(cards("JsTd"))
    assert preflop_strength(cards("9s8s")) > preflop_strength(cards("9s5s"))


@pytest.mark.parametrize(
    "hole, opponents, expected",
    [("AsAd", 1, 0.85), ("7s2d", 1, 0.35), ("AsAd", 4, 0.56)],
)
def test_preflop_equity_matches_known_values(hole, opponents, expected):
    estimate = equity(cards(hole), [], opponents, 3000, random.Random(1))
    assert estimate == pytest.approx(expected, abs=0.035)


def test_equity_on_completed_boards():
    # Royal flush on the board: everyone plays it, so the pot is always split.
    assert equity(cards("2c3d"), cards("AsKsQsJsTs"), 1, 200, random.Random(2)) == 0.5
    # The nuts on the river wins every time.
    assert equity(cards("AhKh"), cards("QhJhTh2c3d"), 2, 200, random.Random(3)) == 1.0


def test_equity_is_deterministic_for_a_seed():
    a = equity(cards("AsKd"), cards("Ah7c2d"), 3, 300, random.Random(9))
    b = equity(cards("AsKd"), cards("Ah7c2d"), 3, 300, random.Random(9))
    assert a == b


@pytest.mark.parametrize(
    "hole, board, flush, open_ended, gutshot, outs",
    [
        ("AhKh", "2h7h9c", True, False, False, 9),
        ("8s9d", "7c6h2d", False, True, False, 8),
        ("8s9d", "Tc6h2d", False, False, True, 4),
        ("AsKd", "QcJh2d", False, False, True, 4),  # one-ended broadway draw
        ("As2d", "3c4h9d", False, False, True, 4),  # wheel draw
        ("9h8h", "7h6h2c", True, True, False, 15),
        ("AsKd", "2c7h9d", False, False, False, 0),
        ("AhKh", "2h7h9h", False, False, False, 0),  # already a flush
        ("AhKh", "2h7h9c4d5s", False, False, False, 0),  # river: no draws
    ],
)
def test_draw_detection(hole, board, flush, open_ended, gutshot, outs):
    d = draws(cards(hole), cards(board))
    assert (d.flush_draw, d.open_ended, d.gutshot, d.outs) == (flush, open_ended, gutshot, outs)


# --- legalize -----------------------------------------------------------------

def legal(**changes):
    base = dict(seat=0, can_fold=True, can_check=False, can_call=True, call_amount=20, can_bet=False,
                can_raise=True, can_all_in=True, min_to=40, max_to=1000, stack=980,
                current_bet=20, committed=0)
    base.update(changes)
    return LegalActions(**base)


def test_legalize_clamps_raise_amounts():
    assert legalize(Action.raise_to(25), legal()) == Action.raise_to(40)
    assert legalize(Action.raise_to(5000), legal()) == Action.raise_to(1000)
    assert legalize(Action.bet(30), legal()) == Action.raise_to(40)  # bet when a bet exists -> raise


def test_legalize_falls_back_when_raising_is_closed():
    closed = legal(can_raise=False, min_to=0, max_to=0, can_all_in=False)
    assert legalize(Action.raise_to(300), closed) == Action.call()
    assert legalize(Action.all_in(), closed) == Action.call()


def test_legalize_never_folds_a_free_check():
    free = legal(can_check=True, can_call=False, call_amount=0, can_bet=True, can_raise=False,
                 min_to=20, current_bet=0)
    assert legalize(Action.fold(), free) == Action.check()
    assert legalize(Action.call(), free) == Action.check()


# --- strategies in real hands -------------------------------------------------

def run_hands(style, difficulty, seeds, hands, players=6, record=None):
    for seed in seeds:
        rng = random.Random(seed)
        table = Table([(f"p{i}", 2000) for i in range(players)], 10, 20, rng=rng)
        strategies = {i: create_strategy(style, difficulty, random.Random(seed * 100 + i)) for i in range(players)}
        for _ in range(hands):
            if not table.can_start_hand:
                break
            hand = table.start_hand()
            while not hand.is_complete:
                seat = hand.to_act
                ctx = observe(hand, seat)
                action = strategies[seat].decide(ctx)
                legal_now = hand.legal_actions()
                assert legal_now.allows(action), (style, difficulty, action, legal_now)
                if legal_now.can_check:
                    assert action.type is not ActionType.FOLD, "folded a free check"
                if record is not None:
                    record.append(action)
                hand.act(seat, action)
            table.settle_hand()


@pytest.mark.parametrize("style", sorted(STYLES))
@pytest.mark.parametrize("difficulty", sorted(DIFFICULTIES))
def test_every_style_and_difficulty_acts_legally(style, difficulty):
    run_hands(style, difficulty, seeds=[1, 2], hands=25)


def test_short_stacks_and_heads_up_stay_legal():
    for style in STYLES:
        for seed in range(4):
            rng = random.Random(seed)
            table = Table([("a", 150), ("b", 3000)], 10, 20, rng=rng)
            strategies = [create_strategy(style, "normal", random.Random(seed + i)) for i in range(2)]
            for _ in range(30):
                if not table.can_start_hand:
                    break
                hand = table.start_hand()
                while not hand.is_complete:
                    seat = hand.to_act
                    action = strategies[seat].decide(observe(hand, seat))
                    assert hand.legal_actions().allows(action)
                    hand.act(seat, action)
                table.settle_hand()


def test_decisions_are_deterministic_for_seeds():
    first, second = [], []
    run_hands("balanced", "normal", seeds=[5], hands=10, record=first)
    run_hands("balanced", "normal", seeds=[5], hands=10, record=second)
    assert first == second and len(first) > 20


def preflop_profile(style):
    vpip = pfr = dealt = 0
    for seed in range(3):
        rng = random.Random(seed)
        table = Table([(f"p{i}", 2000) for i in range(6)], 10, 20, rng=rng)
        strategies = {i: create_strategy(style, "easy", random.Random(seed * 10 + i)) for i in range(6)}
        for _ in range(40):
            hand = table.start_hand()
            while not hand.is_complete:
                seat = hand.to_act
                hand.act(seat, strategies[seat].decide(observe(hand, seat)))
            pre = [e for e in hand.events if isinstance(e, PlayerActed) and e.street is Street.PREFLOP]
            for p in hand.players:
                dealt += 1
                acts = [e.action for e in pre if e.seat == p.seat]
                vpip += any(a in (ActionType.CALL, ActionType.RAISE) for a in acts)
                pfr += ActionType.RAISE in acts
            table.settle_hand()
            if not table.can_start_hand:
                break
    return vpip / dealt, pfr / dealt


def test_styles_differ_in_looseness_and_aggression():
    conservative, balanced, aggressive = (preflop_profile(s) for s in ("conservative", "balanced", "aggressive"))
    assert conservative[0] < balanced[0] < aggressive[0]  # hands played
    assert conservative[1] < balanced[1] < aggressive[1]  # pre-flop raises


def test_hard_decisions_fit_the_time_budget():
    """Six-handed, hard difficulty: decisions must stay short enough for the UI thread."""
    table = Table([(f"p{i}", 2000) for i in range(6)], 10, 20, rng=random.Random(3))
    strategies = [create_strategy(style, "hard", random.Random(i))
                  for i, style in enumerate(["balanced", "aggressive", "conservative"] * 2)]
    durations = []
    for _ in range(15):
        if not table.can_start_hand:
            break
        hand = table.start_hand()
        while not hand.is_complete:
            seat = hand.to_act
            ctx = observe(hand, seat)
            start = time.perf_counter()
            action = strategies[seat].decide(ctx)
            durations.append(time.perf_counter() - start)
            hand.act(seat, action)
        table.settle_hand()
    durations.sort()
    assert durations[int(len(durations) * 0.95)] < 0.05, "95th percentile decision over 50 ms"


def test_reasons_are_recorded_and_shown_only_after_the_hand():
    session = GameSession(SessionConfig(opponents=3, seed=6))
    for _ in range(10):
        session.start_hand()
        while not session.hand_over:
            while session.next_event() is not None:
                pass
            assert session.build_view().analysis == () or session.hand_over
            if session.opponent_to_act is not None:
                session.play_opponent_action()
            elif session.human_to_act:
                legal = session.hand.legal_actions()
                session.apply_human_action("check" if legal.can_check else "call", 0, session.hand.action_count)
        analysis = session.build_view().analysis
        if analysis:
            entry = analysis[0]
            assert entry.reason and entry.name != "You" and len(entry.cards) == 2
            return
    pytest.fail("no opponent decisions recorded")
