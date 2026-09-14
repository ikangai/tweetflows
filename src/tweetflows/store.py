"""Single-writer episode journal with atomic command deduplication and state updates."""

import json
import sqlite3
from collections.abc import Callable
from pathlib import Path

from tweetflows.config import canonical_json, digest


class ExecutionError(ValueError):
    """An explicit runtime contract rejection."""


class Store:
    def __init__(self, path: Path, initial: dict | None = None):
        self.db = sqlite3.connect(path, isolation_level=None, timeout=10)
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS state (
                id INTEGER PRIMARY KEY CHECK(id=1), body TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS commands (
                id TEXT PRIMARY KEY, hash TEXT NOT NULL, response TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS events (
                seq INTEGER PRIMARY KEY, kind TEXT NOT NULL, body TEXT NOT NULL);
        """)
        if initial is not None:
            self.db.execute("INSERT OR IGNORE INTO state VALUES (1, ?)", (canonical_json(initial),))
        if self.db.execute("SELECT 1 FROM state").fetchone() is None:
            raise ExecutionError("MISSING_EPISODE_STATE")

    def read(self) -> dict:
        return json.loads(self.db.execute("SELECT body FROM state WHERE id=1").fetchone()[0])

    def apply(self, command_id: str, payload: dict, change: Callable) -> dict:
        self.db.execute("BEGIN IMMEDIATE")
        try:
            previous = self.db.execute(
                "SELECT hash,response FROM commands WHERE id=?", (command_id,)
            ).fetchone()
            fingerprint = digest(payload)
            if previous:
                if previous[0] != fingerprint:
                    raise ExecutionError("IDEMPOTENCY_CONFLICT")
                self.db.execute("COMMIT")
                return json.loads(previous[1])
            state = self.read()
            events = []
            response = change(state, events)
            self.db.execute("UPDATE state SET body=? WHERE id=1", (canonical_json(state),))
            for event in events:
                self.db.execute(
                    "INSERT INTO events(kind,body) VALUES (?,?)",
                    (event["kind"], canonical_json(event)),
                )
            self.db.execute(
                "INSERT INTO commands VALUES (?,?,?)",
                (command_id, fingerprint, canonical_json(response)),
            )
            self.db.execute("COMMIT")
            return response
        except BaseException:
            if self.db.in_transaction:
                self.db.execute("ROLLBACK")
            raise

    def events(self) -> list[dict]:
        return [
            {"seq": row[0], **json.loads(row[1])}
            for row in self.db.execute("SELECT seq,body FROM events ORDER BY seq")
        ]

    def close(self):
        self.db.close()
