"""Application-level QObject exposed to QML as the ``App`` singleton."""

from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlNamedElement, QmlSingleton, QQmlEngine

from bridge.registry import QML_IMPORT_MAJOR_VERSION, QML_IMPORT_NAME, singleton_instance
from services.logging_setup import LOG_FILE_NAME
from services.paths import log_dir, user_data_dir

__all__ = ["AppBridge", "QML_IMPORT_NAME", "QML_IMPORT_MAJOR_VERSION"]

APP_NAME = "Hold'em Practice"
APP_VERSION = "0.1.0"


@QmlNamedElement("App")
@QmlSingleton
class AppBridge(QObject):
    """Static application information and app-wide commands."""

    quitRequested = Signal()
    # An unexpected internal error (already logged): message for the user.
    errorReported = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)

    @staticmethod
    def create(engine: QQmlEngine) -> "AppBridge":
        return singleton_instance(AppBridge)

    @Property(str, constant=True)
    def name(self) -> str:
        return APP_NAME

    @Property(str, constant=True)
    def version(self) -> str:
        return APP_VERSION

    @Property(str, constant=True)
    def dataDirectory(self) -> str:
        return str(user_data_dir())

    @Property(str, constant=True)
    def logFile(self) -> str:
        return str(log_dir() / LOG_FILE_NAME)

    @Slot()
    def requestQuit(self) -> None:
        self.quitRequested.emit()
