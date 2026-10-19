"""Persistent application settings exposed to QML as the ``Settings`` singleton."""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Callable
from dataclasses import replace

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlNamedElement, QmlSingleton, QQmlEngine

from bridge.registry import QML_IMPORT_MAJOR_VERSION, QML_IMPORT_NAME, singleton_instance
from services.history import HistoryStore
from services.settings import CHIP_SCHEMES, AppSettings

__all__ = ["SettingsBridge", "QML_IMPORT_NAME", "QML_IMPORT_MAJOR_VERSION"]

log = logging.getLogger(__name__)


@QmlNamedElement("Settings")
@QmlSingleton
class SettingsBridge(QObject):
    changed = Signal()
    errorOccurred = Signal(str)

    def __init__(self, store: HistoryStore, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._store = store
        self._listeners: list[Callable[[AppSettings], None]] = []
        try:
            self._settings = AppSettings.from_mapping(store.load_settings())
        except sqlite3.Error:
            log.exception("Could not load settings; using defaults")
            self._settings = AppSettings()
        self.recovery_message = ""

    @staticmethod
    def create(engine: QQmlEngine) -> "SettingsBridge":
        return singleton_instance(SettingsBridge)

    @property
    def settings(self) -> AppSettings:
        return self._settings

    def subscribe(self, listener: Callable[[AppSettings], None]) -> None:
        """Call ``listener`` now and whenever settings change."""
        self._listeners.append(listener)
        listener(self._settings)

    def _update(self, **changes) -> None:
        updated = replace(self._settings, **changes)
        if updated == self._settings:
            return
        self._settings = updated
        try:
            self._store.save_settings(updated.to_mapping())
        except sqlite3.Error as exc:
            log.exception("Could not save settings")
            self.errorOccurred.emit(f"Could not save settings: {exc}")
        for listener in self._listeners:
            listener(updated)
        self.changed.emit()

    # Each property is read/write; writes persist immediately.
    def _get_animations(self) -> bool:
        return self._settings.animations_enabled

    def _set_animations(self, value: bool) -> None:
        self._update(animations_enabled=bool(value))

    animationsEnabled = Property(bool, _get_animations, _set_animations, notify=changed)

    def _get_analysis(self) -> bool:
        return self._settings.analysis_mode

    def _set_analysis(self, value: bool) -> None:
        self._update(analysis_mode=bool(value))

    analysisMode = Property(bool, _get_analysis, _set_analysis, notify=changed)

    def _get_auto_deal(self) -> bool:
        return self._settings.auto_deal

    def _set_auto_deal(self, value: bool) -> None:
        self._update(auto_deal=bool(value))

    autoDeal = Property(bool, _get_auto_deal, _set_auto_deal, notify=changed)

    def _get_chip_scheme(self) -> str:
        return self._settings.chip_scheme

    def _set_chip_scheme(self, value: str) -> None:
        if value in CHIP_SCHEMES:
            self._update(chip_scheme=value)

    chipScheme = Property(str, _get_chip_scheme, _set_chip_scheme, notify=changed)

    @Property("QStringList", constant=True)
    def chipSchemes(self) -> list[str]:
        return list(CHIP_SCHEMES)

    @Property("QVariantMap", notify=changed)
    def sessionDefaults(self) -> dict:
        return dict(self._settings.session_defaults)

    @Slot("QVariantMap")
    def saveSessionDefaults(self, values: dict) -> None:
        cleaned = AppSettings.clean_session_defaults(values)
        self._update(session_defaults={**self._settings.session_defaults, **cleaned})

    @Property("QVariantMap", notify=changed)
    def windowGeometry(self) -> dict:
        return dict(self._settings.window)

    @Slot("QVariantMap")
    def saveWindowGeometry(self, geometry: dict) -> None:
        cleaned = AppSettings.clean_window(geometry)
        if cleaned:
            self._update(window=cleaned)

    @Property(str, constant=True)
    def recoveryNotice(self) -> str:
        """Non-empty when the database had to be recreated at startup."""
        return self.recovery_message
