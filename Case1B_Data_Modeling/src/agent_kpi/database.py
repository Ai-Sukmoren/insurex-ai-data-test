"""SQLite access layer: connection handling, script loading and schema introspection."""
from __future__ import annotations

import re
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


class SqlScript:
    """A .sql file split into individual statements (so each can take bound parameters)."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.text = self.path.read_text(encoding="utf-8")
        self.statements = [s for s in re.split(r";\s*\n", self.text) if self._has_code(s)]

    @staticmethod
    def _has_code(chunk: str) -> bool:
        return any(line.strip() and not line.strip().startswith("--") for line in chunk.splitlines())


@dataclass(frozen=True)
class ColumnInfo:
    name: str
    dtype: str
    not_null: bool
    is_pk: bool
    fk_table: str | None


class Database:
    """Thin wrapper around a sqlite3 connection with foreign keys enforced."""

    def __init__(self, path: str | Path = ":memory:"):
        self.path = str(path)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")

    # ------------------------------------------------------------ lifecycle
    def __enter__(self) -> "Database":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def close(self) -> None:
        self.conn.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Commit on success, roll back everything on any error."""
        try:
            yield self.conn
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    # ------------------------------------------------------------ execution
    def create_schema(self, *scripts: Path) -> None:
        for script in scripts:
            self.conn.executescript(Path(script).read_text(encoding="utf-8"))

    def run_script(self, script: SqlScript, params: dict) -> None:
        with self.transaction() as conn:
            for stmt in script.statements:
                conn.execute(stmt, params)

    def execute(self, sql: str, params: tuple | dict = ()) -> int:
        cur = self.conn.execute(sql, params)
        return cur.lastrowid

    def query(self, sql: str, params: tuple | dict = ()) -> list[sqlite3.Row]:
        return self.conn.execute(sql, params).fetchall()

    # ------------------------------------------------------------ introspection (drives the ERD + data dictionary)
    def tables(self) -> list[str]:
        rows = self.query("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY rowid")
        return [r["name"] for r in rows]

    def columns(self, table: str) -> list[ColumnInfo]:
        fks = {r["from"]: r["table"] for r in self.query(f"PRAGMA foreign_key_list({table})")}
        return [ColumnInfo(r["name"], r["type"], bool(r["notnull"]), r["pk"] > 0, fks.get(r["name"]))
                for r in self.query(f"PRAGMA table_info({table})")]

    def foreign_keys(self, table: str) -> list[tuple[str, str]]:
        """[(child column, parent table)]"""
        return [(r["from"], r["table"]) for r in self.query(f"PRAGMA foreign_key_list({table})")]
