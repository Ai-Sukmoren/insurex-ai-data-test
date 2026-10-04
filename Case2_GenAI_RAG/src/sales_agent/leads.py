"""Lead data model (Pydantic) and SQLite persistence."""
from __future__ import annotations

import re
import sqlite3
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

REQUIRED_FIELDS = ("name", "occupation", "monthly_income", "phone")
FIELD_LABELS = {
    "en": {"name": "your full name", "occupation": "your occupation", "monthly_income": "your monthly income (THB)",
           "phone": "a contact phone number"},
    "th": {"name": "ชื่อ-นามสกุล", "occupation": "อาชีพ", "monthly_income": "รายได้ต่อเดือน (บาท)",
           "phone": "เบอร์โทรศัพท์ติดต่อ"},
}


def normalise_phone(raw: str) -> str:
    """Thai numbers: '+66 81-234-5678' / '081 234 5678' -> '0812345678'. Raises ValueError if invalid."""
    digits = re.sub(r"\D", "", raw or "")
    if digits.startswith("66") and len(digits) in (11, 10):
        digits = "0" + digits[2:]
    if not re.fullmatch(r"0[689]\d{8}|0[2-7]\d{7}", digits):
        raise ValueError(f"'{raw}' is not a valid Thai phone number")
    return digits


class LeadDraft(BaseModel):
    """What the LLM extracts from the conversation - every field optional (collected over several turns)."""
    name: str | None = Field(None, description="Customer's name as they gave it")
    occupation: str | None = Field(None, description="Customer's job or occupation")
    monthly_income: float | None = Field(None, description="Monthly income in THB as a number, e.g. 45000")
    phone: str | None = Field(None, description="Contact phone number exactly as given")

    def missing(self) -> list[str]:
        return [f for f in REQUIRED_FIELDS if getattr(self, f) in (None, "")]

    def merge(self, other: "LeadDraft") -> "LeadDraft":
        updates = {k: v for k, v in other.model_dump().items() if v not in (None, "")}
        return self.model_copy(update=updates)


class Lead(BaseModel):
    """A complete, validated lead - only this goes into the database."""
    name: str = Field(min_length=2, max_length=120)
    occupation: str = Field(min_length=2, max_length=120)
    monthly_income: float = Field(gt=0, lt=10_000_000)
    phone: str
    interested_product: str | None = None
    session_id: str

    @field_validator("name", "occupation")
    @classmethod
    def strip(cls, v: str) -> str:
        return " ".join(v.split())

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, v: str) -> str:
        return normalise_phone(v)


class LeadRepository:
    """SQLite table of captured leads."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS leads (
                lead_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL, occupation TEXT NOT NULL, monthly_income REAL NOT NULL CHECK (monthly_income > 0),
                phone TEXT NOT NULL, interested_product TEXT, session_id TEXT NOT NULL,
                created_at TEXT NOT NULL)""")

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def save(self, lead: Lead) -> int:
        with self._conn() as c:
            cur = c.execute("""INSERT INTO leads (name, occupation, monthly_income, phone, interested_product, session_id, created_at)
                               VALUES (?, ?, ?, ?, ?, ?, ?)""",
                            (lead.name, lead.occupation, lead.monthly_income, lead.phone, lead.interested_product,
                             lead.session_id, datetime.now().isoformat(timespec="seconds")))
            return int(cur.lastrowid)

    def all(self, limit: int = 100) -> list[dict]:
        with self._conn() as c:
            return [dict(r) for r in c.execute("SELECT * FROM leads ORDER BY lead_id DESC LIMIT ?", (limit,))]
