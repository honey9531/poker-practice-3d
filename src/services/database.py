"""SQLite connection, schema migrations and corruption recovery."""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

log = logging.getLogger(__name__)

DB_FILE_NAME = "poker_practice.db"

# Each migration is a list of statements; migration N brings user_version to N.
MIGRATIONS: list[list[str]] = [
    [
        """CREATE TABLE sessions (
            id INTEGER PRIMARY KEY,
            started_at TEXT NOT NULL,
            ended_at TEXT,
            human_name TEXT NOT NULL,
            config TEXT NOT NULL
        )""",
        """CREATE TABLE hands (
            id INTEGER PRIMARY KEY,
            session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
            hand_number INTEGER NOT NULL,
            played_at TEXT NOT NULL,
            small_blind INTEGER NOT NULL,
            big_blind INTEGER NOT NULL,
            board TEXT NOT NULL,
            pot INTEGER NOT NULL,
            went_to_showdown INTEGER NOT NULL,
            summary TEXT NOT NULL,
            events TEXT NOT NULL
        )""",
        """CREATE TABLE hand_players (
            hand_id INTEGER NOT NULL REFERENCES hands(id) ON DELETE CASCADE,
            seat INTEGER NOT NULL,
            name TEXT NOT NULL,
            is_human INTEGER NOT NULL,
            style TEXT NOT NULL,
            hole TEXT NOT NULL,
            starting_stack INTEGER NOT NULL,
            final_stack INTEGER NOT NULL,
            won_amount INTEGER NOT NULL,
            vpip INTEGER NOT NULL,
            pfr INTEGER NOT NULL,
            saw_flop INTEGER NOT NULL,
            showdown INTEGER NOT NULL,
            won_showdown INTEGER NOT NULL,
            PRIMARY KEY (hand_id, seat)
        )""",
        "CREATE INDEX hands_by_session ON hands(session_id)",
        "CREATE INDEX hand_players_by_human ON hand_players(is_human, hand_id)",
        """CREATE TABLE settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )""",
    ],
]

SCHEMA_VERSION = len(MIGRATIONS)


class DatabaseError(RuntimeError):
    pass


class Database:
    """Owns the SQLite connection. Use :meth:`transaction` for every write."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.recovered_from: Path | None = None  # set when a corrupt file was moved aside
        self.conn = self._open()
        self._migrate()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _open(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = self._connect()
        try:
            status = conn.execute("PRAGMA quick_check").fetchone()[0]
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            if status != "ok":
                raise sqlite3.DatabaseError(f"integrity check failed: {status}")
            if version > SCHEMA_VERSION:
                raise DatabaseError(
                    f"Database {self.path} was created by a newer version (schema {version})"
                )
        except sqlite3.DatabaseError as exc:
            conn.close()
            backup = self.path.with_name(
                f"{self.path.stem}.corrupt-{datetime.now():%Y%m%d-%H%M%S}{self.path.suffix}"
            )
            log.error("Database %s is unreadable (%s); moving it to %s", self.path, exc, backup)
            self.path.replace(backup)
            self.recovered_from = backup
            conn = self._connect()
        return conn

    def _migrate(self) -> None:
        version = self.conn.execute("PRAGMA user_version").fetchone()[0]
        for target in range(version + 1, SCHEMA_VERSION + 1):
            with self.conn:
                for statement in MIGRATIONS[target - 1]:
                    self.conn.execute(statement)
                self.conn.execute(f"PRAGMA user_version = {target}")
            log.info("Database migrated to schema %s", target)

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Commit on success, roll back on any error."""
        with self.conn:
            yield self.conn

    @property
    def schema_version(self) -> int:
        return self.conn.execute("PRAGMA user_version").fetchone()[0]

    def close(self) -> None:
        self.conn.close()
