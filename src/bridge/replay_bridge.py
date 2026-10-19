"""Hand replay exposed to QML as the ``Replay`` singleton.

Subclasses GameBridge so the table screen can render a replay exactly like a
live hand. Read-only: nothing here writes to the database or the live game.
"""

from __future__ import annotations

import logging
import sqlite3

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot
from PySide6.QtQml import QmlNamedElement, QmlSingleton, QQmlEngine

from bridge.game_bridge import GameBridge
from bridge.registry import QML_IMPORT_MAJOR_VERSION, QML_IMPORT_NAME, singleton_instance
from services.history import HistoryStore, RecordError
from services.replay import ReplaySession
from services.table_view import TableView

__all__ = ["ReplayBridge", "QML_IMPORT_NAME", "QML_IMPORT_MAJOR_VERSION"]

log = logging.getLogger(__name__)

PLAY_INTERVAL_MS = 900


@QmlNamedElement("Replay")
@QmlSingleton
class ReplayBridge(GameBridge):
    replayChanged = Signal()

    def __init__(self, store: HistoryStore, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._store = store
        self._replay: ReplaySession | None = None
        self._timer = QTimer(self)
        self._timer.setInterval(PLAY_INTERVAL_MS)
        self._timer.timeout.connect(self._advance)

    @staticmethod
    def create(engine: QQmlEngine) -> "ReplayBridge":
        return singleton_instance(ReplayBridge)

    @Slot(int, result=bool)
    def load(self, hand_id: int) -> bool:
        self._timer.stop()
        try:
            record = self._store.load_hand(hand_id)
        except (RecordError, sqlite3.Error) as exc:
            log.warning("Cannot replay hand %s: %s", hand_id, exc)
            self.errorOccurred.emit(f"This hand cannot be replayed ({exc}).")
            return False
        reveal = self._replay.reveal_all if self._replay else False
        self._replay = ReplaySession(record, reveal_all=reveal)
        self._show()
        return True

    def _show(self) -> None:
        self.set_view(self._replay.build_view() if self._replay else TableView())
        self.replayChanged.emit()

    def _advance(self) -> None:
        if self._replay is None or self._replay.at_end:
            self._timer.stop()
            self.replayChanged.emit()
            return
        self._replay.step(1)
        self._show()

    @Slot()
    def stepForward(self) -> None:
        self._timer.stop()
        if self._replay:
            self._replay.step(1)
            self._show()

    @Slot()
    def stepBack(self) -> None:
        self._timer.stop()
        if self._replay:
            self._replay.step(-1)
            self._show()

    @Slot(int)
    def seek(self, position: int) -> None:
        if self._replay:
            self._replay.seek(position)
            self._show()

    @Slot()
    def togglePlay(self) -> None:
        if self._timer.isActive():
            self._timer.stop()
        elif self._replay:
            if self._replay.at_end:
                self._replay.seek(0)
                self._show()
            self._timer.start()
        self.replayChanged.emit()

    @Slot()
    def stop(self) -> None:
        self._timer.stop()
        self.replayChanged.emit()

    @Property(int, notify=replayChanged)
    def position(self) -> int:
        return self._replay.position if self._replay else 0

    @Property(int, notify=replayChanged)
    def steps(self) -> int:
        return self._replay.steps if self._replay else 0

    @Property(bool, notify=replayChanged)
    def playing(self) -> bool:
        return self._timer.isActive()

    def _get_reveal_all(self) -> bool:
        return self._replay.reveal_all if self._replay else False

    def _set_reveal_all(self, value: bool) -> None:
        if self._replay and self._replay.reveal_all != value:
            self._replay.reveal_all = bool(value)
            self._show()

    # Show every player's hole cards (the hand is over, so nothing is secret).
    revealAll = Property(bool, _get_reveal_all, _set_reveal_all, notify=replayChanged)
