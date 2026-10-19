"""Phase 6 gameplay flow: exposure on all-in, session over, restart, end session, UI flow."""

from dataclasses import replace

import pytest
from PySide6.QtQuick import QQuickItem

from poker.events import BoardDealt, CardsExposed
from services.application import configure_qt_application, load_ui
from services.game_controller import INSTANT, REDUCED_MOTION_SCALE, Timing
from services.game_session import GameSession, SessionConfig
from services.preview import preview_table


def visual_descendants(item):
    for child in item.childItems():
        yield child
        yield from visual_descendants(child)


def find(window, name):
    item = next((i for i in visual_descendants(window.contentItem()) if i.objectName() == name), None)
    assert item is not None, name
    return item


@pytest.fixture
def ui(qapp):
    configure_qt_application()
    context = load_ui(qapp)
    context.controller.timing = INSTANT
    window = context.engine.rootObjects()[0]
    yield context, window
    window.close()
    context.engine.deleteLater()


def test_exposed_cards_visible_before_runout_completes():
    session = GameSession(SessionConfig(opponents=1, seed=9, starting_stack=500))
    for _ in range(20):
        session.start_hand()
        while not session.hand_over:
            while session.next_event() is not None:
                applied = session.presenter.events_applied
                last, pending = session.hand.events[applied - 1], session.hand.events[applied:]
                # Every exposure presented and board cards still to come.
                if isinstance(last, CardsExposed) and pending and isinstance(pending[0], BoardDealt):
                        view = session.build_view()
                        opponent = next(s for s in view.seats if not s.is_human)
                        assert all(opponent.cards), "exposed hand must be face up during run-out"
                        return
            if session.opponent_to_act is not None:
                session.play_opponent_action()
            elif session.human_to_act:
                legal = session.hand.legal_actions()
                kind = "all_in" if legal.can_all_in else ("call" if legal.can_call else "check")
                session.apply_human_action(kind, 0, session.hand.action_count)
        if session.session_over:
            break
    pytest.fail("no all-in run-out happened")


def test_animation_preference_changes_pacing(ui):
    context, _ = ui
    context.controller.timing = Timing()
    context.settings.setProperty("animationsEnabled", False)
    assert context.controller.timing.scale == REDUCED_MOTION_SCALE
    context.settings.setProperty("animationsEnabled", True)
    assert context.controller.timing.scale == 1.0


def test_fold_needs_confirmation_when_check_is_free(ui, qtbot):
    context, window = ui
    view = preview_table(6)
    free_check = replace(view.actions, can_check=True, can_call=False, call_amount=0)
    context.game.set_view(replace(view, actions=free_check))
    window.showScreen("table")
    qtbot.wait(300)
    panel = find(window, "actionPanel")
    received = []
    panel.actionRequested.connect(lambda *args: received.append(args))
    fold = find(window, "foldButton")
    fold.clicked.emit()
    assert received == [] and panel.property("confirmingFold")
    fold.clicked.emit()
    assert received == [("fold", 0, 7)]


def test_fold_is_immediate_when_facing_a_bet(ui, qtbot):
    context, window = ui
    context.game.set_view(preview_table(6))
    window.showScreen("table")
    qtbot.wait(300)
    panel = find(window, "actionPanel")
    received = []
    panel.actionRequested.connect(lambda *args: received.append(args))
    find(window, "foldButton").clicked.emit()
    assert received == [("fold", 0, 7)]


def play_to_session_end(context, qtbot):
    controller = context.controller
    for _ in range(200):
        qtbot.waitUntil(lambda: controller.session.human_to_act or controller.session.hand_over, timeout=3000)
        session = controller.session
        if session.session_over:
            return
        if session.human_to_act:
            actions = context.game.property("actions")
            kind = "all_in" if actions["canAllIn"] else ("call" if actions["canCall"] else "check")
            context.game.submitAction(kind, 0, actions["step"])
        else:
            context.game.deal()
    pytest.fail("session did not end")


def test_session_over_overlay_and_play_again(ui, qtbot):
    context, window = ui
    context.controller.start_session(SessionConfig(opponents=1, seed=4, starting_stack=100))
    window.showScreen("table")
    play_to_session_end(context, qtbot)
    qtbot.wait(100)
    assert find(window, "sessionOverOverlay").isVisible()
    find(window, "playAgainButton").clicked.emit()
    qtbot.waitUntil(lambda: context.game.property("handNumber") == 1, timeout=3000)
    assert not context.game.property("sessionOver")
    assert sum(s.stack for s in context.controller.session.table.seats) == 200
    assert context.controller.session.config.starting_stack == 100


def test_end_session_dialog_returns_to_menu(ui, qtbot):
    context, window = ui
    context.controller.start_session(SessionConfig(opponents=2, seed=5))
    window.showScreen("table")
    qtbot.wait(200)
    find(window, "endSessionButton").clicked.emit()
    qtbot.wait(100)
    find(window, "dialogConfirm").clicked.emit()
    qtbot.waitUntil(lambda: window.property("currentScreen") == "menu", timeout=2000)
    assert not context.game.property("sessionActive")


def test_menu_offers_resume_and_new_session_during_a_session(ui, qtbot):
    context, window = ui
    play = find(window, "playButton")
    assert play.property("text") == "Play"
    context.controller.start_session(SessionConfig(opponents=1, seed=1))
    qtbot.wait(50)
    assert play.property("text") == "Resume Table"
    assert find(window, "newSessionMenuButton").isVisible()
    play.clicked.emit()
    qtbot.waitUntil(lambda: window.property("currentScreen") == "table", timeout=2000)
    assert context.qml_warnings == []
