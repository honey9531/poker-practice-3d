"""The table screen rendered by the real application against preview states."""

import pytest
from PySide6.QtQuick import QQuickItem

from services.application import configure_qt_application, load_ui
from services.preview import preview_table


@pytest.fixture
def ui(qapp, qtbot):
    configure_qt_application()
    context = load_ui(qapp)
    window = context.engine.rootObjects()[0]
    yield context, window
    window.close()
    context.engine.deleteLater()


def show_table(ui, qtbot, view):
    context, window = ui
    context.game.set_view(view)
    window.showScreen("table")
    qtbot.wait(300)
    return window


def visual_descendants(item):
    """All items below ``item`` in the visual tree (Repeater delegates are not
    QObject children, so ``findChild`` cannot see them)."""
    for child in item.childItems():
        yield child
        yield from visual_descendants(child)


def find(window, name):
    root = window.contentItem()
    item = next((i for i in visual_descendants(root) if i.objectName() == name), None)
    assert item is not None, name
    return item


def cards_in(item):
    return [c for c in visual_descendants(item) if c.property("card") is not None and c.property("aspect")]


def test_table_shows_every_seat_and_no_warnings(ui, qtbot):
    window = show_table(ui, qtbot, preview_table(6))
    for slot in range(6):
        seat = find(window, f"seat{slot}")
        assert seat.isVisible()
    assert find(window, "seat0").property("name") == "You"
    assert ui[0].qml_warnings == []


def test_opponent_cards_are_face_down_and_human_cards_face_up(ui, qtbot):
    window = show_table(ui, qtbot, preview_table(6))
    human_cards = cards_in(find(window, "seat0"))
    assert sorted(c.property("card") for c in human_cards) == ["Ah", "Kh"]
    assert all(c.property("showingFace") for c in human_cards)
    opponent = cards_in(find(window, "seat1"))
    assert opponent and all(not c.property("showingFace") for c in opponent)


def test_board_and_pot_reflect_state(ui, qtbot):
    view = preview_table(6)
    window = show_table(ui, qtbot, view)
    shown = [find(window, f"boardCard{i}").property("card") for i in range(5)]
    assert shown == list(view.board) + [""]
    assert find(window, "potTotal").property("text") == "Pot  4,410"


def test_action_panel_submits_once_with_step(ui, qtbot):
    window = show_table(ui, qtbot, preview_table(6))
    panel = find(window, "actionPanel")
    received = []
    panel.actionRequested.connect(lambda kind, amount, step: received.append((kind, amount, step)))

    call = find(window, "checkCallButton")
    assert call.isEnabled()
    call.clicked.emit()
    call.clicked.emit()  # double click: ignored until a new decision point
    assert received == [("call", 0, 7)]
    assert not call.isEnabled()


def test_raise_amount_defaults_to_minimum_and_presets_apply(ui, qtbot):
    window = show_table(ui, qtbot, preview_table(6))
    panel = find(window, "actionPanel")
    assert panel.property("raiseTo") == 840
    find(window, "preset_Pot").clicked.emit()
    assert panel.property("raiseTo") == 1960
    received = []
    panel.actionRequested.connect(lambda kind, amount, step: received.append((kind, amount, step)))
    find(window, "betRaiseButton").clicked.emit()
    assert received == [("raise", 1960, 7)]


def test_amount_field_clamps_to_legal_range(ui, qtbot):
    window = show_table(ui, qtbot, preview_table(6))
    panel = find(window, "actionPanel")
    for typed, expected in (("5", 840), ("999999", 1960), ("1000", 1000)):
        field = find(window, "amountField")
        field.setProperty("text", typed)
        field.editingFinished.emit()
        assert panel.property("raiseTo") == expected


def test_controls_disabled_when_not_human_turn(ui, qtbot):
    window = show_table(ui, qtbot, preview_table(6, showdown=True))
    for name in ("foldButton", "checkCallButton", "betRaiseButton", "allInButton"):
        assert not find(window, name).isEnabled()


@pytest.mark.parametrize("size", [(1024, 640), (1280, 800), (1920, 1080)])
def test_seats_stay_inside_the_window(ui, qtbot, size):
    window = show_table(ui, qtbot, preview_table(6))
    window.resize(*size)
    qtbot.wait(200)
    area = find(window, "tableArea")
    for slot in range(6):
        seat = find(window, f"seat{slot}")
        top_left = seat.mapToItem(area, 0, 0)
        assert top_left.x() >= 0 and top_left.y() >= -1
        assert top_left.x() + seat.width() <= area.width() + 1
        assert top_left.y() + seat.height() <= area.height() + 1


def test_panel_unlocks_for_same_step_in_next_hand(ui, qtbot):
    """Regression: the engine step restarts each hand, so the lock must be per hand."""
    from dataclasses import replace

    view = preview_table(6)
    window = show_table(ui, qtbot, view)
    find(window, "checkCallButton").clicked.emit()
    assert not find(window, "checkCallButton").isEnabled()
    ui[0].game.set_view(replace(view, hand_number=43))
    qtbot.wait(50)
    assert find(window, "checkCallButton").isEnabled()


def test_raise_amount_resets_when_new_decision_arrives(ui, qtbot):
    """Regression: the amount must follow the new minimum, not keep a stale value."""
    from dataclasses import replace

    view = preview_table(6)
    window = show_table(ui, qtbot, view)
    panel = find(window, "actionPanel")
    ui[0].game.set_view(replace(view, actions=None))
    qtbot.wait(20)
    new_actions = replace(view.actions, step=9, min_to=1000)
    ui[0].game.set_view(replace(view, actions=new_actions))
    qtbot.wait(20)
    assert panel.property("raiseTo") == 1000
    assert ui[0].qml_warnings == []
