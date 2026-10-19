"""Writes sessions and completed hands to the history store.

Persistence problems (disk full, read-only directory, locked database) are
logged and reported through ``on_error``; they never interrupt the game.
"""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Callable
from dataclasses import asdict

from poker import HoldemHand
from services.game_session import HUMAN_SEAT, GameSession
from services.hand_presenter import HandPresenter
from services.history import HistoryStore
from services.view_builder import result_message

log = logging.getLogger(__name__)


class HistoryRecorder:
    def __init__(
        self,
        store: HistoryStore,
        on_error: Callable[[str], None] = lambda message: None,
        on_recorded: Callable[[], None] = lambda: None,
    ) -> None:
        self.store = store
        self.on_error = on_error
        self.on_recorded = on_recorded
        self.session_id: int | None = None

    def _safely(self, what: str, operation: Callable[[], object]) -> object | None:
        try:
            return operation()
        except (sqlite3.Error, OSError) as exc:
            log.exception("Could not %s", what)
            self.on_error(f"Could not {what}: {exc}")
            return None

    def session_started(self, session: GameSession) -> None:
        self.session_ended()
        config = asdict(session.config)
        config.pop("seed", None)
        self.session_id = self._safely(
            "save the session", lambda: self.store.start_session(session.config.human_name, config)
        )
        session.hand_listeners.append(lambda hand: self.hand_completed(session, hand))

    def hand_completed(self, session: GameSession, hand: HoldemHand) -> None:
        if self.session_id is None:
            return
        summary = result_message(HandPresenter.from_events(hand.events))
        styles = {seat: style.capitalize() for seat, style in session.styles.items()}
        recorded = self._safely(
            "save the hand history",
            lambda: self.store.record_hand(
                self.session_id, session.table.hand_number, hand.events,
                human_seat=HUMAN_SEAT, styles=styles, summary=summary,
            ),
        )
        if recorded is not None:
            self.on_recorded()

    def session_ended(self) -> None:
        if self.session_id is not None:
            session_id, self.session_id = self.session_id, None
            self._safely("close the session", lambda: self.store.end_session(session_id))
