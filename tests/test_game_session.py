"""GameSession: engine orchestration, presentation replay and view visibility."""

import random

import pytest

from ai import DecisionContext, observe
from poker import Action, ActionType
from poker.events import HoleCardsDealt, PlayerActed
from services.game_session import (
    HUMAN_SEAT,
    GameSession,
    SessionConfig,
    SessionError,
    action_from_request,
    bet_presets,
)
from services.hand_presenter import HandPresenter


def present_all(session):
    while session.next_event() is not None:
        pass


def play_until_human_or_end(session):
    present_all(session)
    while session.opponent_to_act is not None:
        session.play_opponent_action()
        present_all(session)


def new_session(**kw):
    kw.setdefault("seed", 11)
    return GameSession(SessionConfig(**kw))


@pytest.mark.parametrize(
    "changes",
    [
        {"opponents": 0}, {"opponents": 6}, {"small_blind": 0}, {"small_blind": 30},
        {"starting_stack": 5}, {"opponent_style": "wild"}, {"difficulty": "insane"},
        {"human_name": " "},
    ],
)
def test_invalid_configs_are_rejected(changes):
    with pytest.raises(SessionError):
        new_session(**changes)


def test_session_seats_human_and_named_opponents():
    session = new_session(opponents=4, opponent_style="mixed")
    names = [s.name for s in session.table.seats]
    assert names == ["You", "Avery", "Blake", "Casey", "Drew"]
    assert set(session.styles.values()) <= {"conservative", "balanced", "aggressive"}
    assert len(set(session.styles.values())) == 3  # mixed uses every style


def test_view_before_first_hand():
    session = new_session()
    view = session.build_view()
    assert view.session_active and view.can_deal and not view.hand_in_progress
    assert view.hand_number == 0
    assert [s.slot for s in view.seats] == [0, 1, 3, 5]


def test_opponent_cards_hidden_during_hand():
    session = new_session(opponents=3)
    session.start_hand()
    present_all(session)
    view = session.build_view()
    for seat in view.seats:
        if seat.is_human:
            assert len(seat.cards) == 2 and all(seat.cards)
        else:
            assert seat.cards == ("", "")
    # The hidden codes really are absent from the whole snapshot.
    hidden = {c.code for p in session.hand.players if p.seat != HUMAN_SEAT for c in p.hole}
    assert not hidden & set(repr(view).split("'"))


def test_presentation_lags_engine_until_events_are_shown():
    session = new_session()
    session.start_hand()
    assert not session.caught_up
    first = session.build_view()
    assert first.board == () and all(s.cards == () for s in first.seats)
    assert session.human_to_act is False and session.opponent_to_act is None
    present_all(session)
    assert session.caught_up


def test_human_actions_view_and_submission():
    session = new_session(opponents=1, seed=3)
    session.start_hand()
    play_until_human_or_end(session)
    assert session.human_to_act
    view = session.build_view()
    actions = view.actions
    assert actions is not None and actions.step == session.hand.action_count
    labels = [p.label for p in actions.presets]
    assert labels[0] == "Min" and labels[-1] == "All-in"
    session.apply_human_action("call" if actions.can_call else "check", 0, actions.step)
    with pytest.raises(Exception):
        session.apply_human_action("call", 0, actions.step)  # duplicate submission


def test_bet_presets_follow_pot_size():
    session = new_session(opponents=1, seed=3, starting_stack=10_000)
    session.start_hand()
    play_until_human_or_end(session)
    hand = session.hand
    presets = {p.label: p.amount for p in bet_presets(hand)}
    legal = hand.legal_actions()
    pot_after_call = hand.total_pot + legal.call_amount
    assert presets["Pot"] == hand.current_bet + pot_after_call
    assert presets["All-in"] == legal.max_to
    assert all(legal.min_to <= v <= legal.max_to for v in presets.values())


@pytest.mark.parametrize("kind", ["fold", "check", "call", "all_in"])
def test_action_requests_map_to_engine_actions(kind):
    assert action_from_request(kind, 999).type is ActionType(kind)
    assert action_from_request(kind, 999).amount == 0


def test_bet_request_keeps_amount_and_unknown_kind_fails():
    assert action_from_request("raise", 300) == Action.raise_to(300)
    with pytest.raises(SessionError):
        action_from_request("dance", 0)


def test_presenter_replay_matches_engine_result():
    rng = random.Random(8)
    session = new_session(opponents=4, seed=8)
    for _ in range(25):
        if not session.can_start_hand:
            break
        session.start_hand()
        while True:
            play_until_human_or_end(session)
            if not session.human_to_act:
                break
            legal = session.hand.legal_actions()
            kind = rng.choice(["call", "fold", "all_in"] if legal.can_call else ["check", "all_in"])
            session.apply_human_action(kind, 0, session.hand.action_count)
        hand = session.hand
        replay = HandPresenter.from_events(hand.events)
        assert replay.complete
        assert {s: p.stack for s, p in replay.seats.items()} == dict(hand.result.final_stacks)
        assert replay.total_pot() == 0 and replay.pots() == []
        view = session.build_view()
        assert sum(s.stack for s in view.seats) == 5 * 2000


def test_cards_revealed_only_at_showdown():
    session = new_session(opponents=2, seed=21)
    for _ in range(30):
        session.start_hand()
        while True:
            play_until_human_or_end(session)
            if not session.human_to_act:
                break
            legal = session.hand.legal_actions()
            session.apply_human_action("check" if legal.can_check else "call", 0, session.hand.action_count)
        view = session.build_view()
        result = session.hand.result
        for seat in view.seats:
            if seat.is_human or not seat.in_hand or seat.folded:
                continue
            if result.went_to_showdown:
                assert all(seat.cards), "live hand must be shown at showdown"
            else:
                assert not any(seat.cards)
        if session.hand.result.went_to_showdown:
            return
    pytest.fail("no showdown reached")


def test_result_message_names_winner():
    session = new_session(opponents=1, seed=5)
    session.start_hand()
    play_until_human_or_end(session)
    session.apply_human_action("fold", 0, session.hand.action_count)
    present_all(session)
    assert session.hand_over
    assert session.message().startswith("Avery wins")


def test_session_over_when_human_busts():
    session = new_session(opponents=1, seed=2, starting_stack=40, small_blind=10, big_blind=20)
    for _ in range(50):
        if session.session_over:
            break
        session.start_hand()
        while True:
            play_until_human_or_end(session)
            if not session.human_to_act:
                break
            legal = session.hand.legal_actions()
            kind = "all_in" if legal.can_all_in else ("call" if legal.can_call else "check")
            session.apply_human_action(kind, 0, session.hand.action_count)
    assert session.session_over
    assert not session.can_start_hand
    assert session.build_view().session_over


def test_illegal_strategy_action_falls_back_safely():
    class Broken:
        name = "Broken"

        def decide(self, ctx: DecisionContext) -> Action:
            return Action.raise_to(10**9)

    session = GameSession(SessionConfig(opponents=1, seed=4), strategy_factory=lambda *a: Broken())
    session.start_hand()
    present_all(session)
    if session.opponent_to_act is None:
        session.apply_human_action("call", 0, session.hand.action_count)
        present_all(session)
    event = session.play_opponent_action()
    assert event.action in (ActionType.CHECK, ActionType.FOLD)


def test_observe_exposes_only_own_cards():
    session = new_session(opponents=2, seed=1)
    session.start_hand()
    present_all(session)
    hand = session.hand
    seat = hand.to_act
    ctx = observe(hand, seat)
    assert ctx.hole == hand.player(seat).hole
    others = {c for p in hand.players if p.seat != seat for c in p.hole}
    assert not others & set(ctx.hole) and not others & set(ctx.board)
    assert ctx.players_in_hand == 3 and ctx.opponents_in_hand == 2
    with pytest.raises(ValueError):
        observe(hand, (seat + 1) % 3)


def test_hole_cards_dealt_event_present_for_each_player():
    session = new_session(opponents=5)
    hand = session.start_hand()
    assert sum(isinstance(e, HoleCardsDealt) for e in hand.events) == 6
    assert any(isinstance(e, PlayerActed) for e in hand.events) is False
