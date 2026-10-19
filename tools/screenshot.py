"""Render the application offscreen and save screenshots for visual QA.

Usage:
    python tools/screenshot.py OUTPUT_DIR [--sizes 1280x800,1920x1080] [--screens menu,table]
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# Never touch the real user data (database, settings) from a QA tool.
os.environ.setdefault("POKER_PRACTICE_DATA_DIR", tempfile.mkdtemp(prefix="poker-screenshot-"))

from PySide6.QtCore import QEventLoop, QTimer  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402

from services.application import configure_qt_application, load_ui  # noqa: E402

ALL_SCREENS = ["menu", "setup", "table", "statistics", "history", "settings", "gallery"]


def wait(ms: int) -> None:
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--sizes", default="1024x640,1280x800,1920x1080")
    parser.add_argument("--screens", default=",".join(ALL_SCREENS))
    parser.add_argument(
        "--preview", choices=["none", "hand", "showdown", "headsup"], default="hand",
        help="sample table state to display (no engine involved)",
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    configure_qt_application()
    app = QGuiApplication(sys.argv[:1])
    context = load_ui(app)
    window = context.engine.rootObjects()[0]
    if args.preview != "none":
        from services.preview import preview_table

        players = 2 if args.preview == "headsup" else 6
        context.game.set_view(preview_table(players, showdown=args.preview == "showdown"))

    for size in args.sizes.split(","):
        width, height = (int(v) for v in size.split("x"))
        window.resize(width, height)
        for screen in args.screens.split(","):
            window.showScreen(screen)
            wait(1000)  # let screen transitions and card animations finish
            image = window.grabWindow()
            suffix = f"_{args.preview}" if screen == "table" and args.preview != "none" else ""
            path = args.output_dir / f"{screen}{suffix}_{width}x{height}.png"
            image.save(str(path))
            print(path)
    window.showScreen("menu")

    if context.qml_warnings:
        print("QML warnings:", *context.qml_warnings, sep="\n  ")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
