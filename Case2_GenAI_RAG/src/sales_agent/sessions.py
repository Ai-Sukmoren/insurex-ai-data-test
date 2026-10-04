"""Server-side index of chat sessions (title, timestamps, message count) so any browser sees the same list."""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path


class SessionIndex:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY, title TEXT NOT NULL, created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL, turns INTEGER NOT NULL DEFAULT 0)""")

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _now() -> str:
        return datetime.now().isoformat(timespec="seconds")

    def touch(self, session_id: str, first_message: str) -> None:
        """Create the session on its first message (title = that message), otherwise bump updated_at and turns."""
        title = " ".join(first_message.split())[:60] or "New chat"
        now = self._now()
        with self._conn() as c:
            c.execute("""INSERT INTO sessions (session_id, title, created_at, updated_at, turns) VALUES (?, ?, ?, ?, 1)
                         ON CONFLICT(session_id) DO UPDATE SET updated_at = excluded.updated_at, turns = turns + 1""",
                      (session_id, title, now, now))

    def list(self, limit: int = 100) -> list[dict]:
        with self._conn() as c:
            return [dict(r) for r in c.execute("SELECT * FROM sessions ORDER BY updated_at DESC LIMIT ?", (limit,))]

    def rename(self, session_id: str, title: str) -> bool:
        with self._conn() as c:
            return c.execute("UPDATE sessions SET title = ? WHERE session_id = ?", (title.strip()[:80], session_id)).rowcount > 0

    def delete(self, session_id: str) -> bool:
        with self._conn() as c:
            return c.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,)).rowcount > 0
