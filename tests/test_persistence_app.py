"""Persistence through the running application: restart, settings, history UI, replay."""

import pytest
from PySide6.QtQuick import QQuickItem

from services.application import configure_qt_application, load_ui
from services.database import DB_FILE_NAME
from services.game_controller import INSTANT
from services.game_session import SessionConfig
from services.paths import user_data_dir


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


def play_hands(context, qtbot, count):
    controller = context.controller
    controller.start_session(SessionConfig(opponents=2, seed=21))
    played = 0
    while played < count:
        qtbot.waitUntil(lambda: controller.session.human_to_act or controller.session.hand_over, timeout=3000)
        session = controller.session
        if session.human_to_act:
            actions = context.game.property("actions")
            context.game.submitAction("check" if actions["canCheck"] else "call", 0, actions["step"])
            continue
        played += 1
        if session.session_over:
            break
        context.game.deal()
    return played


def test_history_and_statistics_survive_restart(qapp, qtbot):
    context, window = start(qapp)
    played = play_hands(context, qtbot, 5)
    stats_before = context.store.statistics()
    assert stats_before.hands == played
    stop(context, window)

    assert (user_data_dir() / DB_FILE_NAME).exists()
    context, window = start(qapp)
    assert context.store.statistics() == stats_before
    assert len(context.store.list_hands()) == played
    assert context.store.list_sessions()[0].ended_at is not None
    assert context.stats.property("allTime")["hands"] == played
    assert not context.stats.property("hasSession")
    stop(context, window)


def test_settings_persist_and_apply(qapp, qtbot):
    context, window = start(qapp)
    context.settings.setProperty("animationsEnabled", False)
    context.settings.setProperty("chipScheme", "vivid")
    context.settings.saveSessionDefaults({"opponents": 5, "difficulty": "hard"})
    assert context.chips.property("denominations")[0]["color"] == "#f4f1ea"
    stop(context, window)

    context, window = start(qapp)
    assert context.settings.property("animationsEnabled") is False
    assert context.settings.property("chipScheme") == "vivid"
    assert context.settings.property("sessionDefaults")["opponents"] == 5
    assert context.chips.property("denominations")[0]["color"] == "#f4f1ea"
    stop(context, window)


def test_corrupt_database_shows_notice_and_app_still_works(qapp, qtbot):
    (user_data_dir() / DB_FILE_NAME).write_bytes(b"garbage" * 500)
    context, window = start(qapp)
    assert "damaged" in context.settings.property("recoveryNotice")
    assert find(window, "startupNotice").isVisible()
    assert play_hands(context, qtbot, 2) == 2
    assert context.store.statistics().hands == 2
    stop(context, window)


def test_history_screen_detail_and_replay(qapp, qtbot):
    context, window = start(qapp)
    play_hands(context, qtbot, 3)
    window.showScreen("history")
    qtbot.wait(300)
    assert len(context.history.property("hands")) == 3
    detail = context.history.property("detail")
    assert detail["log"] and detail["players"]
    find(window, "replayButton").clicked.emit()
    qtbot.waitUntil(lambda: window.property("currentScreen") == "replay", timeout=2000)
    replay = context.replay
    assert replay.property("steps") > 1 and replay.property("position") == 0
    find(window, "replayForward").clicked.emit()
    assert replay.property("position") == 1
    find(window, "backButton")  # top bar present
    assert not find(window, "actionPanel").isVisible()
    assert context.qml_warnings == []
    stop(context, window)


def test_history_detail_hides_unshown_opponent_cards(qapp, qtbot):
    context, window = start(qapp)
    play_hands(context, qtbot, 6)
    history = context.history
    history.refresh()
    for row in history.property("hands"):
        history.select(row["id"])
        players = history.property("detail")["players"]
        hidden = [p for p in players if not p["isHuman"] and not any(p["cards"])]
        if hidden:
            history.setProperty("revealAll", True)
            revealed = {p["name"]: p for p in history.property("detail")["players"]}
            assert all(all(revealed[p["name"]]["cards"]) for p in hidden)
            history.setProperty("revealAll", False)
            stop(context, window)
            return
    stop(context, window)
    pytest.skip("every opponent hand was shown in these hands")
