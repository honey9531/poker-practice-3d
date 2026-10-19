"""Phase 9: window geometry, error reporting, reduced motion, board presentation, icon."""

import struct
import sys

import pytest
from PySide6.QtCore import QObject

from services.application import configure_qt_application, install_exception_hook, load_ui
from services.game_controller import INSTANT
from services.game_session import SessionConfig
from services.paths import assets_dir
from services.preview import preview_table
from services.settings import AppSettings


def visual_descendants(item):
    for child in item.childItems():
        yield child
        yield from visual_descendants(child)


def find(window, name):
    item = next((i for i in visual_descendants(window.contentItem()) if i.objectName() == name), None)
    assert item is not None, name
    return item


def start(qapp):
    configure_qt_application()
    context = load_ui(qapp)
    context.controller.timing = INSTANT
    return context, context.engine.rootObjects()[0]


def stop(context, window):
    window.close()
    context.shutdown()
    context.engine.deleteLater()


@pytest.mark.parametrize(
    "value, expected",
    [
        ({"x": 10, "y": 20, "width": 1300, "height": 820}, {"x": 10, "y": 20, "width": 1300, "height": 820, "maximized": 0}),
        ({"x": 10, "y": 20, "width": 100, "height": 820}, {}),  # too small
        ({"x": "a", "y": 20, "width": 1300, "height": 820}, {}),
        ("garbage", {}),
    ],
)
def test_window_geometry_validation(value, expected):
    assert AppSettings.clean_window(value) == expected


def test_window_size_is_restored_after_restart(qapp, qtbot):
    context, window = start(qapp)
    window.resize(1400, 860)
    qtbot.wait(50)
    stop(context, window)  # closing saves the geometry
    context, window = start(qapp)
    assert (window.width(), window.height()) == (1400, 860)
    stop(context, window)


def test_unexpected_errors_are_logged_and_shown(qapp, qtbot):
    context, window = start(qapp)
    previous = sys.excepthook
    try:
        install_exception_hook(context)
        with qtbot.waitSignal(context.app_bridge.errorReported):
            sys.excepthook(ValueError, ValueError("boom"), None)
        qtbot.wait(100)
        popup = window.findChild(QObject, "errorDialog")
        assert popup.property("opened")
        assert "boom" in popup.property("text") and context.app_bridge.property("logFile") in popup.property("text")
    finally:
        sys.excepthook = previous
    stop(context, window)


def test_toast_reports_errors_from_any_bridge(qapp, qtbot):
    context, window = start(qapp)
    context.settings.errorOccurred.emit("Could not save settings: disk full")
    qtbot.wait(200)
    toast = find(window, "errorToast")
    assert toast.isVisible() and "disk full" in toast.property("text")
    stop(context, window)


def test_existing_board_is_shown_without_replaying_the_deal(qapp, qtbot):
    context, window = start(qapp)
    context.game.set_view(preview_table(6))
    window.showScreen("table")
    qtbot.wait(50)
    cards = [find(window, f"boardCard{i}") for i in range(4)]
    assert all(c.property("showingFace") for c in cards)
    stop(context, window)


def test_reduced_motion_plays_hands_cleanly(qapp, qtbot):
    context, window = start(qapp)
    context.settings.setProperty("animationsEnabled", False)
    window.showScreen("table")
    controller = context.controller
    controller.start_session(SessionConfig(opponents=3, seed=8))
    for _ in range(40):
        qtbot.waitUntil(lambda: controller.session.human_to_act or controller.session.hand_over, timeout=3000)
        session = controller.session
        if session.human_to_act:
            actions = context.game.property("actions")
            context.game.submitAction("check" if actions["canCheck"] else "call", 0, actions["step"])
            # Without animations, hole cards are face up as soon as they appear.
            human_cards = [i for i in visual_descendants(find(window, "seat0")) if i.property("aspect")]
            assert all(c.property("showingFace") for c in human_cards if c.isVisible())
        elif session.table.hand_number >= 3:
            break
        else:
            context.game.deal()
    assert context.qml_warnings == []
    stop(context, window)


def test_icon_files_are_valid(qapp):
    icon_dir = assets_dir() / "icon"
    ico = (icon_dir / "app.ico").read_bytes()
    reserved, kind, count = struct.unpack("<HHH", ico[:6])
    assert (reserved, kind) == (0, 1) and count == 7
    assert (icon_dir / "app.png").read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    sys.path.insert(0, str(assets_dir().parent / "tools"))
    import generate_icon

    assert (icon_dir / "app.svg").read_text(encoding="utf-8") == generate_icon.svg_text()
