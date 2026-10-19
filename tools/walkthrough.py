"""Drive the real application UI through several hands and save screenshots.

Usage:
    python tools/walkthrough.py OUTPUT_DIR [--hands 6] [--size 1280x800] [--policy call|random]

Clicks the same buttons a player would (menu -> setup -> table -> action
buttons -> click the table for the next hand), checks chip conservation after
every hand, and exits
non-zero on QML warnings or inconsistencies.
"""

from __future__ import annotations

import argparse
import os
import random
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("POKER_PRACTICE_DATA_DIR", tempfile.mkdtemp(prefix="poker-walkthrough-"))

from PySide6.QtCore import QEventLoop, QPoint, QPointF, Qt, QTimer  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

from services.application import configure_qt_application, load_ui  # noqa: E402
from services.game_controller import Timing  # noqa: E402


def wait(ms: int) -> None:
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def items(root):
    for child in root.childItems():
        yield child
        yield from items(child)


def find(window, name):
    return next((i for i in items(window.contentItem()) if i.objectName() == name and i.isVisible()), None)


def click(window, name) -> bool:
    item = find(window, name)
    if item is None or not item.isEnabled():
        return False
    item.clicked.emit()
    return True


def click_table(window) -> bool:
    """A real mouse click on the middle of the felt (deals the next hand)."""
    area = find(window, "dealArea")
    if area is None or not area.property("enabled"):  # MouseArea.enabled, not Item.enabled
        return False
    centre = area.mapToScene(QPointF(area.width() / 2, area.height() * 0.3))
    QTest.mouseClick(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                     QPoint(int(centre.x()), int(centre.y())))
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--hands", type=int, default=6)
    parser.add_argument("--size", default="1280x800")
    parser.add_argument("--policy", choices=["call", "random"], default="random")
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)

    configure_qt_application()
    app = QGuiApplication(sys.argv[:1])
    context = load_ui(app)
    context.controller.timing = Timing(scale=0.05)
    window = context.engine.rootObjects()[0]
    window.resize(*(int(v) for v in args.size.split("x")))
    shots = 0

    def shot(label: str) -> None:
        nonlocal shots
        shots += 1
        path = args.output_dir / f"{shots:02d}_{label}.png"
        window.grabWindow().save(str(path))
        print(path)

    assert click(window, "playButton"), "Play button"
    wait(400)
    shot("setup")
    assert click(window, "startSessionButton"), "Start Session button"
    wait(400)

    controller = context.controller
    total = sum(s.stack for s in controller.session.table.seats)
    hands_done = 0
    decisions = 0
    streets_shot: set[str] = set()
    while hands_done < args.hands:
        for _ in range(400):
            wait(25)
            session = controller.session
            if session.human_to_act or (session.hand_over and not controller.busy):
                break
        else:
            print("Timed out waiting for the table", file=sys.stderr)
            return 1
        session = controller.session
        if session.human_to_act:
            street = session.presenter.street.value
            if street not in streets_shot:
                streets_shot.add(street)
                wait(300)
                shot(f"decision_{street}")
            decisions += 1
            legal = session.hand.legal_actions()
            if args.policy == "call":
                name = "checkCallButton"
            else:
                choices = ["checkCallButton"] * 6 + ["foldButton"] * (0 if legal.can_check else 2)
                if legal.can_raise or legal.can_bet:
                    choices += ["betRaiseButton"] * 2
                name = rng.choice(choices)
            assert click(window, name), name
            continue

        hands_done += 1
        result = session.hand.result
        wait(300)
        shot(f"hand{hands_done}_{'showdown' if result.went_to_showdown else 'fold'}")
        stacks = sum(s.stack for s in session.table.seats)
        if stacks != total:
            print(f"Chip total changed: {stacks} != {total}", file=sys.stderr)
            return 1
        if session.session_over:
            print("Session over")
            break
        assert click_table(window), "click on the table to deal"

    print(f"Hands: {hands_done}, human decisions: {decisions}")

    # Persistence screens: statistics, history detail and a replay.
    for screen in ("statistics", "history"):
        window.showScreen(screen)
        wait(500)
        shot(screen)
    if click(window, "replayButton"):
        wait(500)
        for _ in range(4):
            click(window, "replayForward")
        wait(400)
        shot("replay_step")
        replay = context.replay
        replay.seek(replay.property("steps") - 1)
        wait(400)
        shot("replay_end")
    stats = context.store.statistics()
    if stats.hands != hands_done:
        print(f"Recorded hands {stats.hands} != played {hands_done}", file=sys.stderr)
        return 1
    if context.qml_warnings:
        print("QML warnings:", *context.qml_warnings, sep="\n  ", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
