"""Built-in self-test for verifying an installed or packaged build.

Run ``PokerPractice --self-test`` (or ``python main.py --self-test``). It loads
the real UI, checks that every bundled resource loads, plays complete hands
against the computer opponents through the game controller, verifies chip
conservation, hand-history recording and replay, then exits with status 0 on
success. It uses the normal user-data directory unless
``POKER_PRACTICE_DATA_DIR`` is set, so running it twice also verifies that the
history persists across restarts.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Callable

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtGui import QGuiApplication, QImage

from poker import FULL_DECK
from services.application import AppContext, configure_qt_application, load_ui
from services.game_controller import INSTANT
from services.game_session import SessionConfig
from services.paths import assets_dir, qml_dir, resource_root, user_data_dir

log = logging.getLogger(__name__)

HANDS = 6


class SelfTestFailure(RuntimeError):
    pass


def _wait_until(condition: Callable[[], bool], timeout_ms: int = 5000) -> None:
    waited = 0
    while not condition():
        if waited >= timeout_ms:
            raise SelfTestFailure("Timed out waiting for the table")
        loop = QEventLoop()
        QTimer.singleShot(10, loop.quit)
        loop.exec()
        waited += 10


def _report(line: str) -> None:
    # Printed for console runs and logged for windowed builds (no console).
    print(line)
    log.info("Self-test: %s", line.strip())


def _check(condition: bool, message: str) -> None:
    if not condition:
        raise SelfTestFailure(message)
    _report(f"  ok  {message}")


def _check_resources() -> None:
    _check((qml_dir() / "Main.qml").is_file(), f"QML found in {qml_dir()}")
    missing = []
    for name in [f"{c.code}.svg" for c in FULL_DECK] + ["back.svg"]:
        image = QImage(str(assets_dir() / "cards" / name))
        if image.isNull() or image.width() == 0:
            missing.append(name)
    _check(not missing, f"all 53 card images render (SVG plugin) {missing[:3] if missing else ''}".rstrip())
    _check(not QImage(str(assets_dir() / "table" / "felt_noise.png")).isNull(), "table texture loads")
    _check(not QImage(str(assets_dir() / "icon" / "app.png")).isNull(), "application icon loads")


SCREENS = ("setup", "statistics", "history", "settings", "gallery", "table", "menu")


def _visit_screens(context: AppContext) -> None:
    """Open every screen so all QML modules and components must load."""
    window = context.engine.rootObjects()[0]
    for name in SCREENS:
        window.showScreen(name)
        loop = QEventLoop()
        QTimer.singleShot(150, loop.quit)
        loop.exec()
        if window.property("currentScreen") != name:
            raise SelfTestFailure(f"Could not open the {name} screen")
    _check(not context.qml_warnings, f"all screens open without QML errors {context.qml_warnings[:2] or ''}".rstrip())


def _play(context: AppContext) -> None:
    controller = context.controller
    controller.timing = INSTANT
    before = context.store.statistics().hands
    controller.start_session(SessionConfig(opponents=3, seed=2024))
    total = sum(s.stack for s in controller.session.table.seats)
    played = 0
    while played < HANDS:
        _wait_until(lambda: controller.session.human_to_act or controller.session.hand_over)
        session = controller.session
        if session.human_to_act:
            actions = context.game.property("actions")
            kind = "check" if actions["canCheck"] else "call"
            if not context.game.submitAction(kind, 0, actions["step"]):
                raise SelfTestFailure(f"Action {kind} was rejected")
            continue
        played += 1
        stacks = sum(s.stack for s in session.table.seats)
        if stacks != total:
            raise SelfTestFailure(f"Chip total changed: {stacks} != {total}")
        if session.session_over:
            break
        context.game.deal()
    _check(played >= 1, f"played {played} complete hand(s) against computer opponents")
    _check(not context.qml_warnings, "no QML warnings during play")
    recorded = context.store.statistics().hands - before
    _check(recorded == played, f"recorded {recorded} hand(s) in {user_data_dir()}")

    hands = context.store.list_hands(limit=1)
    _check(context.replay.load(hands[0].id), "latest hand replays from the database")
    context.replay.seek(context.replay.property("steps") - 1)
    _check(context.store.statistics().hands - before == played, "replay did not modify history")
    controller.end_session()
    _report(f"  ..  hands in database: {context.store.statistics().hands}")


def run_self_test(argv: list[str] | None = None) -> int:
    _report(f"Self-test: resources in {resource_root()}")
    configure_qt_application()
    app = QGuiApplication(argv if argv is not None else sys.argv[:1])
    try:
        _check_resources()
        context = load_ui(app)
        _check(bool(context.engine.rootObjects()), "main window loaded")
        if context.notice:
            _report(f"  !!  {context.notice}")
        _visit_screens(context)
        _play(context)
        context.shutdown()
    except SelfTestFailure as exc:
        print(f"FAILED: {exc}")
        log.error("Self-test failed: %s", exc)
        return 1
    _report("Self-test passed")
    return 0
