"""Application logging: rotating log file plus stderr, with Qt/QML messages forwarded."""

from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path

from PySide6.QtCore import QtMsgType, qInstallMessageHandler

from services.paths import log_dir

LOG_FILE_NAME = "poker_practice.log"

_QT_LEVELS = {
    QtMsgType.QtDebugMsg: logging.DEBUG,
    QtMsgType.QtInfoMsg: logging.INFO,
    QtMsgType.QtWarningMsg: logging.WARNING,
    QtMsgType.QtCriticalMsg: logging.ERROR,
    QtMsgType.QtFatalMsg: logging.CRITICAL,
}

_qt_logger = logging.getLogger("qt")


def _qt_message_handler(msg_type, context, message: str) -> None:
    location = f" ({context.file}:{context.line})" if context.file else ""
    _qt_logger.log(_QT_LEVELS.get(msg_type, logging.WARNING), "%s%s", message, location)


def configure_logging(level: int = logging.INFO, log_file: Path | None = None) -> Path:
    """Configure root logging once and route Qt messages through it.

    Returns the path of the log file.
    """
    log_file = log_file or (log_dir() / LOG_FILE_NAME)
    root = logging.getLogger()
    root.setLevel(level)
    for handler in list(root.handlers):
        if getattr(handler, "_poker_practice", False):
            root.removeHandler(handler)
            handler.close()

    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    handlers: list[logging.Handler] = [
        logging.handlers.RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    ]
    # Windowed (GUI) executables on Windows have no console: sys.stderr is None.
    if sys.stderr is not None:
        handlers.append(logging.StreamHandler())
    for handler in handlers:
        handler.setFormatter(fmt)
        handler._poker_practice = True  # type: ignore[attr-defined]
        root.addHandler(handler)

    qInstallMessageHandler(_qt_message_handler)
    return log_file
