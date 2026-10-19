"""Persistent hand history, sessions, statistics and settings (SQLite)."""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from poker.events import BoardDealt, HandEvent, PotAwarded
from services.database import Database
from services.history_codec import RecordError, decode_events, encode_events
from services.statistics import PlayerHandFacts, Stats, hand_facts

log = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True, slots=True)
class HandSummary:
    id: int
    session_id: int
    hand_number: int
    played_at: str
    small_blind: int
    big_blind: int
    board: tuple[str, ...]
    pot: int
    went_to_showdown: bool
    summary: str
    human_cards: tuple[str, ...]
    human_net: int


@dataclass(frozen=True, slots=True)
class PlayerRecord:
    seat: int
    name: str
    is_human: bool
    style: str
    hole: tuple[str, ...]
    starting_stack: int
    final_stack: int
    won_amount: int

    @property
    def net(self) -> int:
        return self.final_stack - self.starting_stack


@dataclass(frozen=True, slots=True)
class HandRecord:
    summary: HandSummary
    players: tuple[PlayerRecord, ...]
    events: tuple[HandEvent, ...]


@dataclass(frozen=True, slots=True)
class SessionSummary:
    id: int
    started_at: str
    ended_at: str | None
    hands: int
    net: int
    config: Mapping[str, Any]


class HistoryStore:
    def __init__(self, db: Database) -> None:
        self.db = db

    # ---------------------------------------------------------------- sessions

    def start_session(self, human_name: str, config: Mapping[str, Any]) -> int:
        with self.db.transaction() as conn:
            cursor = conn.execute(
                "INSERT INTO sessions (started_at, human_name, config) VALUES (?, ?, ?)",
                (_now(), human_name, json.dumps(dict(config))),
            )
            return int(cursor.lastrowid)

    def end_session(self, session_id: int) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE sessions SET ended_at = ? WHERE id = ? AND ended_at IS NULL",
                (_now(), session_id),
            )

    def close_open_sessions(self) -> None:
        """Sessions left open by a crash or forced exit are closed at startup."""
        with self.db.transaction() as conn:
            conn.execute("UPDATE sessions SET ended_at = started_at WHERE ended_at IS NULL")

    def list_sessions(self, limit: int = 50) -> list[SessionSummary]:
        rows = self.db.conn.execute(
            """SELECT s.id, s.started_at, s.ended_at, s.config,
                      COUNT(p.hand_id) AS hands, COALESCE(SUM(p.final_stack - p.starting_stack), 0) AS net
               FROM sessions s
               LEFT JOIN hands h ON h.session_id = s.id
               LEFT JOIN hand_players p ON p.hand_id = h.id AND p.is_human = 1
               GROUP BY s.id ORDER BY s.id DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        result = []
        for row in rows:
            try:
                config = json.loads(row["config"])
            except json.JSONDecodeError:
                config = {}
            result.append(SessionSummary(row["id"], row["started_at"], row["ended_at"],
                                         row["hands"], row["net"], config))
        return result

    # ---------------------------------------------------------------- hands

    def record_hand(
        self,
        session_id: int,
        hand_number: int,
        events: Sequence[HandEvent],
        *,
        human_seat: int,
        styles: Mapping[int, str],
        summary: str,
    ) -> int:
        facts = hand_facts(events)
        started = events[0]
        board = [c.code for e in events if isinstance(e, BoardDealt) for c in e.cards]
        pot = sum(e.amount for e in events if isinstance(e, PotAwarded))
        showdown = any(f.showdown for f in facts)
        with self.db.transaction() as conn:
            cursor = conn.execute(
                """INSERT INTO hands (session_id, hand_number, played_at, small_blind, big_blind,
                                      board, pot, went_to_showdown, summary, events)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (session_id, hand_number, _now(), started.small_blind, started.big_blind,
                 " ".join(board), pot, int(showdown), summary, encode_events(events)),
            )
            hand_id = int(cursor.lastrowid)
            conn.executemany(
                """INSERT INTO hand_players (hand_id, seat, name, is_human, style, hole, starting_stack,
                                             final_stack, won_amount, vpip, pfr, saw_flop, showdown,
                                             won_showdown)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [self._player_row(hand_id, f, human_seat, styles) for f in facts],
            )
        return hand_id

    @staticmethod
    def _player_row(hand_id: int, f: PlayerHandFacts, human_seat: int, styles: Mapping[int, str]) -> tuple:
        return (hand_id, f.seat, f.name, int(f.seat == human_seat), styles.get(f.seat, ""),
                " ".join(f.hole), f.starting_stack, f.final_stack, f.won_amount, int(f.vpip),
                int(f.pfr), int(f.saw_flop), int(f.showdown), int(f.won_showdown))

    _SUMMARY_SQL = """
        SELECT h.id, h.session_id, h.hand_number, h.played_at, h.small_blind, h.big_blind, h.board,
               h.pot, h.went_to_showdown, h.summary, p.hole AS human_hole,
               p.final_stack - p.starting_stack AS human_net
        FROM hands h LEFT JOIN hand_players p ON p.hand_id = h.id AND p.is_human = 1
    """

    @staticmethod
    def _summary(row) -> HandSummary:
        return HandSummary(
            id=row["id"], session_id=row["session_id"], hand_number=row["hand_number"],
            played_at=row["played_at"], small_blind=row["small_blind"], big_blind=row["big_blind"],
            board=tuple(row["board"].split()), pot=row["pot"],
            went_to_showdown=bool(row["went_to_showdown"]), summary=row["summary"],
            human_cards=tuple((row["human_hole"] or "").split()), human_net=row["human_net"] or 0,
        )

    def list_hands(self, limit: int = 300, session_id: int | None = None) -> list[HandSummary]:
        if session_id is None:
            rows = self.db.conn.execute(self._SUMMARY_SQL + " ORDER BY h.id DESC LIMIT ?", (limit,))
        else:
            rows = self.db.conn.execute(
                self._SUMMARY_SQL + " WHERE h.session_id = ? ORDER BY h.id DESC LIMIT ?", (session_id, limit)
            )
        return [self._summary(row) for row in rows.fetchall()]

    def load_hand(self, hand_id: int) -> HandRecord:
        """Full record for replay; raises RecordError if missing or corrupted."""
        row = self.db.conn.execute(self._SUMMARY_SQL + " WHERE h.id = ?", (hand_id,)).fetchone()
        if row is None:
            raise RecordError(f"Hand {hand_id} not found")
        events_text = self.db.conn.execute("SELECT events FROM hands WHERE id = ?", (hand_id,)).fetchone()[0]
        events = decode_events(events_text)
        players = tuple(
            PlayerRecord(r["seat"], r["name"], bool(r["is_human"]), r["style"], tuple(r["hole"].split()),
                         r["starting_stack"], r["final_stack"], r["won_amount"])
            for r in self.db.conn.execute(
                "SELECT * FROM hand_players WHERE hand_id = ? ORDER BY seat", (hand_id,)
            ).fetchall()
        )
        return HandRecord(self._summary(row), players, tuple(events))

    # ---------------------------------------------------------------- stats

    def statistics(self, session_id: int | None = None) -> Stats:
        """Aggregate statistics for the human player (all time or one session)."""
        where = "p.is_human = 1" + (" AND h.session_id = ?" if session_id is not None else "")
        params = (session_id,) if session_id is not None else ()
        row = self.db.conn.execute(
            f"""SELECT COUNT(*) AS hands,
                       COALESCE(SUM(p.won_amount > 0), 0) AS hands_won,
                       COALESCE(SUM(p.final_stack - p.starting_stack), 0) AS net,
                       COALESCE(SUM(p.vpip), 0) AS vpip,
                       COALESCE(SUM(p.pfr), 0) AS pfr,
                       COALESCE(SUM(p.showdown), 0) AS showdowns,
                       COALESCE(SUM(p.won_showdown), 0) AS showdowns_won,
                       COALESCE(MAX(p.won_amount), 0) AS biggest
                FROM hand_players p JOIN hands h ON h.id = p.hand_id
                WHERE {where}""",
            params,
        ).fetchone()
        return Stats(row["hands"], row["hands_won"], row["net"], row["vpip"], row["pfr"],
                     row["showdowns"], row["showdowns_won"], row["biggest"])

    def clear(self) -> None:
        """Delete all sessions, hands and statistics (settings are kept)."""
        with self.db.transaction() as conn:
            conn.execute("DELETE FROM hand_players")
            conn.execute("DELETE FROM hands")
            conn.execute("DELETE FROM sessions")

    # ---------------------------------------------------------------- settings

    def load_settings(self) -> dict[str, Any]:
        result = {}
        for row in self.db.conn.execute("SELECT key, value FROM settings").fetchall():
            try:
                result[row["key"]] = json.loads(row["value"])
            except json.JSONDecodeError:
                log.warning("Ignoring unreadable setting %r", row["key"])
        return result

    def save_settings(self, values: Mapping[str, Any]) -> None:
        with self.db.transaction() as conn:
            conn.executemany(
                "INSERT INTO settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                [(key, json.dumps(value)) for key, value in values.items()],
            )


__all__ = ["HandRecord", "HandSummary", "HistoryStore", "PlayerRecord", "RecordError", "SessionSummary"]
