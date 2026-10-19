"""Blinds that rise every N hands, chosen when starting a session."""

import pytest
from PySide6.QtCore import QObject

from services import blinds
from services.application import configure_qt_application, load_ui
from services.game_controller import INSTANT
from services.game_session import GameSession, SessionConfig, SessionError, passive_factory
from services.settings import AppSettings


def test_ladder_is_increasing_whole_numbers_with_double_big_blind():
    levels = [blinds.blinds_at(level, 10, 20) for level in range(30)]
    assert levels[:5] == [(10, 20), (20, 40), (30, 60), (50, 100), (100, 200)]
    assert all(isinstance(sb, int) and bb == 2 * sb for sb, bb in levels)
    assert all(b[0] > a[0] for a, b in zip(levels, levels[1:]))


@pytest.mark.parametrize("small, big", [(5, 10), (25, 50), (50, 100)])
def test_ladder_scales_from_any_starting_blinds(small, big):
    assert blinds.blinds_at(0, small, big) == (small, big)
    assert blinds.blinds_at(3, small, big) == (small * 5, big * 5)


@pytest.mark.parametrize(
    "played, every, level, left",
    [(0, 0, 0, 0), (37, 0, 0, 0), (0, 5, 0, 5), (4, 5, 0, 1), (5, 5, 1, 5), (12, 10, 1, 8)],
)
def test_level_arithmetic(played, every, level, left):
    assert blinds.level_for_hand(played, every) == level
    assert blinds.hands_until_next_level(played, every) == left


def play_hand(session):
    session.start_hand()
    while not session.hand_over:
        while session.next_event() is not None:
            pass
        if session.opponent_to_act is not None:
            session.play_opponent_action()
        elif session.human_to_act:
            legal = session.hand.legal_actions()
            session.apply_human_action("check" if legal.can_check else "call", 0, session.hand.action_count)
    return session.hand


def test_each_hand_is_dealt_at_its_level():
    session = GameSession(SessionConfig(opponents=2, seed=1, starting_stack=100_000, blind_increase_every=5),
                          strategy_factory=passive_factory)
    blinds_by_hand = [play_hand(session).small_blind for _ in range(12)]
    assert blinds_by_hand == [10] * 5 + [20] * 5 + [30] * 2


def test_countdown_during_and_after_hands():
    session = GameSession(SessionConfig(opponents=1, seed=2, starting_stack=100_000, blind_increase_every=5),
                          strategy_factory=passive_factory)
    view = session.build_view()
    assert (view.blind_interval, view.blind_level, view.hands_to_next_level) == (5, 0, 5)
    for _ in range(4):
        play_hand(session)
    view = session.build_view()  # after hand 4: one hand left at this level
    assert (view.blind_level, view.hands_to_next_level) == (0, 1)
    session.start_hand()  # hand 5 in progress: still counts as the last one
    assert (session.build_view().blind_level, session.build_view().hands_to_next_level) == (0, 1)
    while not session.hand_over:
        while session.next_event() is not None:
            pass
        if session.opponent_to_act is not None:
            session.play_opponent_action()
        elif session.human_to_act:
            legal = session.hand.legal_actions()
            session.apply_human_action("check" if legal.can_check else "call", 0, session.hand.action_count)
    assert session.build_view().hands_to_next_level == 0  # blinds go up next hand
    hand = play_hand(session)
    assert hand.small_blind == 20
    assert (session.build_view().blind_level, session.build_view().hands_to_next_level) == (1, 4)


def test_fixed_blinds_never_change():
    session = GameSession(SessionConfig(opponents=1, seed=3, starting_stack=100_000),
                          strategy_factory=passive_factory)
    assert {play_hand(session).small_blind for _ in range(25)} == {10}
    assert session.build_view().blind_interval == 0


def test_invalid_interval_rejected():
    with pytest.raises(SessionError):
        SessionConfig(blind_increase_every=7).validate()


def test_setting_default_round_trips_and_rejects_bad_values():
    settings = AppSettings.from_mapping({"session_defaults": {"blindIncreaseEvery": 10}})
    assert settings.session_defaults["blindIncreaseEvery"] == 10
    assert AppSettings.from_mapping({"session_defaults": {"blindIncreaseEvery": 3}}).session_defaults[
        "blindIncreaseEvery"] == 0


def test_session_started_from_setup_options_uses_rising_blinds(qapp, qtbot):
    configure_qt_application()
    context = load_ui(qapp)
    context.controller.timing = INSTANT
    window = context.engine.rootObjects()[0]
    try:
        assert context.game.blindPreview(10, 20, 4) == ["10/20", "20/40", "30/60", "50/100"]
        window.showScreen("table")
        assert context.game.startSession({"opponents": 1, "startingStack": 2000, "smallBlind": 10,
                                          "bigBlind": 20, "opponentStyle": "balanced",
                                          "difficulty": "easy", "blindIncreaseEvery": 5})
        qtbot.waitUntil(lambda: context.game.property("handNumber") == 1, timeout=2000)
        assert context.controller.session.config.blind_increase_every == 5
        assert context.game.property("blindInterval") == 5
        info = window.findChild(QObject, "handInfo")
        assert "Level 1" in info.property("text") and "next in 5 hands" in info.property("text")
        assert context.qml_warnings == []
    finally:
        window.close()
        context.shutdown()
        context.engine.deleteLater()
