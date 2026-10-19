"""The next hand is dealt by clicking the table once the current hand is over."""

import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtTest import QTest

from services.application import configure_qt_application, load_ui
from services.game_controller import INSTANT
from services.game_session import SessionConfig


def visual_descendants(item):
    for child in item.childItems():
        yield child
        yield from visual_descendants(child)


def find(window, name):
    return next((i for i in visual_descendants(window.contentItem()) if i.objectName() == name), None)


@pytest.fixture
def ui(qapp, qtbot):
    configure_qt_application()
    context = load_ui(qapp)
    context.controller.timing = INSTANT
    window = context.engine.rootObjects()[0]
    window.showScreen("table")
    qtbot.wait(100)
    yield context, window
    window.close()
    context.shutdown()
    context.engine.deleteLater()


def click_felt(window):
    area = find(window, "dealArea")
    point = area.mapToScene(QPointF(area.width() / 2, area.height() * 0.3))
    QTest.mouseClick(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                     QPoint(int(point.x()), int(point.y())))


def finish_hand(context, qtbot):
    controller = context.controller
    while True:
        qtbot.waitUntil(lambda: controller.session.human_to_act or controller.session.hand_over, timeout=3000)
        if controller.session.hand_over:
            return
        context.game.submitAction("fold", 0, context.game.property("actions")["step"])


def test_next_hand_button_is_gone(ui):
    _, window = ui
    assert find(window, "dealButton") is None


def test_clicking_the_table_deals_after_the_hand(ui, qtbot):
    context, window = ui
    context.controller.start_session(SessionConfig(opponents=2, seed=3))
    qtbot.waitUntil(lambda: context.game.property("handNumber") == 1, timeout=2000)

    # During a hand the table is not clickable.
    if not context.controller.session.hand_over:
        assert not find(window, "dealArea").property("enabled")
        assert not find(window, "dealHint").isVisible()
        click_felt(window)
        assert context.game.property("handNumber") == 1

    finish_hand(context, qtbot)
    qtbot.wait(50)
    assert find(window, "dealArea").property("enabled")
    assert find(window, "dealHint").isVisible()
    click_felt(window)
    qtbot.waitUntil(lambda: context.game.property("handNumber") == 2, timeout=2000)
    assert context.qml_warnings == []


def test_replay_table_does_not_deal(ui, qtbot):
    context, window = ui
    context.controller.start_session(SessionConfig(opponents=1, seed=4))
    finish_hand(context, qtbot)
    hand_id = context.store.list_hands()[0].id
    assert context.replay.load(hand_id)
    window.showScreen("replay")
    qtbot.wait(200)
    replay_area = [i for i in visual_descendants(window.contentItem())
                   if i.objectName() == "dealArea" and i.isVisible()]
    assert replay_area and not any(a.property("enabled") for a in replay_area)
