"""Startup, QML loading and screen navigation of the real application UI."""

import pytest
from PySide6.QtQuick import QQuickItem, QQuickWindow

from bridge import AppBridge
from bridge.app_bridge import APP_NAME, APP_VERSION
from services.application import configure_qt_application, load_ui

SCREENS = ["table", "statistics", "history", "settings", "gallery", "menu"]


@pytest.fixture
def ui(qapp):
    configure_qt_application()
    context = load_ui(qapp)
    yield context
    for root in context.engine.rootObjects():
        root.close()
    context.engine.deleteLater()


def window_of(ui) -> QQuickWindow:
    (window,) = ui.engine.rootObjects()
    return window


def test_main_window_loads_without_qml_warnings(ui):
    window = window_of(ui)
    assert isinstance(window, QQuickWindow)
    assert window.objectName() == "mainWindow"
    assert window.title() == APP_NAME
    assert window.property("currentScreen") == "menu"
    assert ui.qml_warnings == []


def test_bridge_is_exposed_to_qml(ui):
    window = window_of(ui)
    assert window.findChild(QQuickItem, "playButton") is not None
    bridge = ui.app_bridge
    assert isinstance(bridge, AppBridge)
    assert bridge.property("version") == APP_VERSION


@pytest.mark.parametrize("screen", SCREENS)
def test_every_screen_can_be_shown(ui, qtbot, screen):
    window = window_of(ui)
    window.showScreen(screen)
    qtbot.wait(300)
    assert window.property("currentScreen") == screen
    assert ui.qml_warnings == []


def test_back_navigation_returns_to_menu(ui, qtbot):
    window = window_of(ui)
    window.showScreen("settings")
    qtbot.wait(300)
    back = [b for b in window.findChildren(QQuickItem, "backButton") if b.isVisible()]
    assert len(back) == 1
    back[0].clicked.emit()
    qtbot.wait(300)
    assert window.property("currentScreen") == "menu"


def test_quit_button_requests_quit(ui, qtbot):
    window = window_of(ui)
    quit_button = window.findChild(QQuickItem, "quitButton")
    with qtbot.waitSignal(ui.app_bridge.quitRequested, timeout=1000):
        quit_button.clicked.emit()
