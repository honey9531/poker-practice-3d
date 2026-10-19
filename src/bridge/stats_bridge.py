"""Statistics and hand history exposed to QML (``Stats`` and ``History`` singletons)."""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Callable
from datetime import datetime

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlNamedElement, QmlSingleton, QQmlEngine

from bridge.registry import QML_IMPORT_MAJOR_VERSION, QML_IMPORT_NAME, singleton_instance
from poker.events import CardsExposed, ShowdownRevealed
from services.hand_log import describe_events
from services.history import HistoryStore, RecordError
from services.statistics import Stats

__all__ = ["HistoryBridge", "StatsBridge", "QML_IMPORT_NAME", "QML_IMPORT_MAJOR_VERSION"]

log = logging.getLogger(__name__)


def stats_to_qml(stats: Stats) -> dict:
    return {
        "hands": stats.hands,
        "handsWon": stats.hands_won,
        "winRate": stats.win_rate,
        "net": stats.net,
        "vpip": stats.vpip,
        "pfr": stats.pfr,
        "showdowns": stats.showdowns,
        "showdownRate": stats.showdown_rate,
        "showdownWinRate": stats.showdown_win_rate,
        "biggestPot": stats.biggest_pot,
    }


def local_time(iso: str | None) -> str:
    if not iso:
        return ""
    try:
        return datetime.fromisoformat(iso).astimezone().strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return iso


@QmlNamedElement("Stats")
@QmlSingleton
class StatsBridge(QObject):
    changed = Signal()
    errorOccurred = Signal(str)

    def __init__(self, store: HistoryStore, current_session: Callable[[], int | None],
                 parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._store = store
        self._current_session = current_session
        self._session = stats_to_qml(Stats())
        self._all_time = stats_to_qml(Stats())
        self._sessions: list[dict] = []
        self.refresh()

    @staticmethod
    def create(engine: QQmlEngine) -> "StatsBridge":
        return singleton_instance(StatsBridge)

    @Slot()
    def refresh(self) -> None:
        try:
            session_id = self._current_session()
            self._session = stats_to_qml(self._store.statistics(session_id) if session_id else Stats())
            self._all_time = stats_to_qml(self._store.statistics())
            self._sessions = [
                {"id": s.id, "startedAt": local_time(s.started_at), "hands": s.hands, "net": s.net,
                 "opponents": s.config.get("opponents", 0),
                 "blinds": f"{s.config.get('small_blind', '?')}/{s.config.get('big_blind', '?')}"}
                for s in self._store.list_sessions()
            ]
        except sqlite3.Error as exc:
            log.exception("Could not load statistics")
            self.errorOccurred.emit(f"Could not load statistics: {exc}")
        self.changed.emit()

    @Slot()
    def resetAll(self) -> None:
        """Delete all recorded sessions, hands and statistics."""
        try:
            self._store.clear()
        except sqlite3.Error as exc:
            self.errorOccurred.emit(f"Could not clear history: {exc}")
        self.refresh()

    @Property(bool, notify=changed)
    def hasSession(self) -> bool:
        return self._current_session() is not None

    @Property("QVariantMap", notify=changed)
    def session(self) -> dict:
        return self._session

    @Property("QVariantMap", notify=changed)
    def allTime(self) -> dict:
        return self._all_time

    @Property("QVariantList", notify=changed)
    def sessions(self) -> list[dict]:
        return self._sessions


@QmlNamedElement("History")
@QmlSingleton
class HistoryBridge(QObject):
    changed = Signal()
    selectionChanged = Signal()

    def __init__(self, store: HistoryStore, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._store = store
        self._hands: list[dict] = []
        self._detail: dict = {}
        self._error = ""
        self._reveal_all = False
        self._selected: int | None = None

    @staticmethod
    def create(engine: QQmlEngine) -> "HistoryBridge":
        return singleton_instance(HistoryBridge)

    @Slot()
    def refresh(self) -> None:
        try:
            self._hands = [
                {"id": h.id, "handNumber": h.hand_number, "playedAt": local_time(h.played_at),
                 "board": list(h.board), "cards": list(h.human_cards), "net": h.human_net,
                 "pot": h.pot, "summary": h.summary, "showdown": h.went_to_showdown,
                 "sessionId": h.session_id, "blinds": f"{h.small_blind}/{h.big_blind}"}
                for h in self._store.list_hands()
            ]
            self._error = ""
        except sqlite3.Error as exc:
            log.exception("Could not load hand history")
            self._hands = []
            self._error = f"Could not load hand history: {exc}"
        self.changed.emit()

    @Slot(int)
    def select(self, hand_id: int) -> None:
        self._selected = hand_id
        try:
            record = self._store.load_hand(hand_id)
        except (RecordError, sqlite3.Error) as exc:
            log.warning("Hand %s unreadable: %s", hand_id, exc)
            self._detail = {"id": hand_id, "error": f"This hand record is damaged and cannot be shown ({exc})."}
            self.selectionChanged.emit()
            return
        s = record.summary
        # Opponents' cards are listed only if they were shown at the table,
        # unless the viewer explicitly asks to see every hand.
        shown = {e.seat for e in record.events if isinstance(e, (ShowdownRevealed, CardsExposed))}

        def cards(p) -> list[str]:
            if p.is_human or p.seat in shown or self._reveal_all:
                return list(p.hole)
            return [""] * len(p.hole)

        self._detail = {
            "id": s.id,
            "title": f"Hand #{s.hand_number} · {local_time(s.played_at)} · blinds {s.small_blind}/{s.big_blind}",
            "board": list(s.board),
            "summary": s.summary,
            "pot": s.pot,
            "players": [
                {"name": p.name, "cards": cards(p), "net": p.net, "style": p.style, "isHuman": p.is_human}
                for p in record.players
            ],
            "log": [{"street": line.street, "text": line.text} for line in describe_events(record.events)],
            "error": "",
        }
        self.selectionChanged.emit()

    @Slot()
    def clearSelection(self) -> None:
        self._selected = None
        self._detail = {}
        self.selectionChanged.emit()

    def _get_reveal_all(self) -> bool:
        return self._reveal_all

    def _set_reveal_all(self, value: bool) -> None:
        if value != self._reveal_all:
            self._reveal_all = bool(value)
            if self._selected is not None:
                self.select(self._selected)
            self.selectionChanged.emit()

    revealAll = Property(bool, _get_reveal_all, _set_reveal_all, notify=selectionChanged)

    @Property("QVariantList", notify=changed)
    def hands(self) -> list[dict]:
        return self._hands

    @Property(str, notify=changed)
    def error(self) -> str:
        return self._error

    @Property("QVariantMap", notify=selectionChanged)
    def detail(self) -> dict:
        return self._detail
