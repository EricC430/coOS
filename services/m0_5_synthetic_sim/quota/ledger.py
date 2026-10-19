"""Quota ledgers: in-memory (tests) and SQLite (data/coos_synthetic.db)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from m0_5_synthetic_sim.isolation import open_synthetic_db

PAID_LATCH_MODEL = "*"


@dataclass(frozen=True)
class CallRecord:
    at: datetime
    tokens_in: int
    tokens_out: int


@dataclass(frozen=True)
class Block:
    reason: str
    until: datetime


class QuotaLedger(Protocol):
    def add_call(self, model: str, at: datetime, tokens_in: int, tokens_out: int) -> None: ...
    def calls_since(self, model: str, since: datetime) -> list[CallRecord]: ...
    def models_with_calls(self) -> list[str]: ...
    def set_learned(self, model: str, field: str, value: int, at: datetime) -> None: ...
    def learned(self, model: str) -> dict[str, int]: ...
    def add_block(self, model: str, reason: str, until: datetime, at: datetime) -> None: ...
    def active_block(self, model: str, now: datetime) -> Block | None: ...
    def set_paid_latch(self, on: bool, at: datetime) -> None: ...
    def paid_latch(self) -> bool: ...


class InMemoryLedger:
    def __init__(self) -> None:
        self._calls: dict[str, list[CallRecord]] = {}
        self._learned: dict[str, dict[str, int]] = {}
        self._blocks: dict[str, list[Block]] = {}
        self._latch = False

    def add_call(self, model, at, tokens_in, tokens_out):
        self._calls.setdefault(model, []).append(CallRecord(at, tokens_in, tokens_out))

    def calls_since(self, model, since):
        return [c for c in self._calls.get(model, []) if c.at > since]

    def models_with_calls(self):
        return list(self._calls)

    def set_learned(self, model, field, value, at):
        self._learned.setdefault(model, {})[field] = value

    def learned(self, model):
        return dict(self._learned.get(model, {}))

    def add_block(self, model, reason, until, at):
        self._blocks.setdefault(model, []).append(Block(reason, until))

    def active_block(self, model, now):
        live = [b for b in self._blocks.get(model, []) if b.until > now]
        return max(live, key=lambda b: b.until) if live else None

    def set_paid_latch(self, on, at):
        self._latch = on

    def paid_latch(self):
        return self._latch


def _ts(t: datetime) -> str:
    return t.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _parse(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=UTC)


class SqliteLedger:
    """Event log in table m0_5_quota_ledger; every row is_synthetic = 1 [RISK-24]."""

    def __init__(self, path: Path) -> None:
        self._con = open_synthetic_db(path)
        self._con.execute("""
            CREATE TABLE IF NOT EXISTS m0_5_quota_ledger (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                model        TEXT NOT NULL,
                kind         TEXT NOT NULL CHECK (kind IN ('call', 'learned', 'block', 'latch')),
                at_utc       TEXT NOT NULL,
                tokens_in    INTEGER,
                tokens_out   INTEGER,
                field        TEXT,
                value        REAL,
                reason       TEXT,
                until_utc    TEXT,
                is_synthetic INTEGER NOT NULL DEFAULT 1 CHECK (is_synthetic = 1)
            )
        """)
        self._con.execute("CREATE INDEX IF NOT EXISTS idx_m0_5_ql_model_kind ON m0_5_quota_ledger(model, kind, at_utc)")
        self._con.commit()

    def _insert(self, **cols) -> None:
        keys = ", ".join(cols)
        marks = ", ".join("?" for _ in cols)
        self._con.execute(f"INSERT INTO m0_5_quota_ledger ({keys}) VALUES ({marks})", tuple(cols.values()))
        self._con.commit()

    def add_call(self, model, at, tokens_in, tokens_out):
        self._insert(model=model, kind="call", at_utc=_ts(at), tokens_in=tokens_in, tokens_out=tokens_out)

    def calls_since(self, model, since):
        rows = self._con.execute(
            "SELECT at_utc, tokens_in, tokens_out FROM m0_5_quota_ledger "
            "WHERE model = ? AND kind = 'call' AND at_utc > ? ORDER BY at_utc",
            (model, _ts(since)),
        ).fetchall()
        return [CallRecord(_parse(a), i or 0, o or 0) for a, i, o in rows]

    def models_with_calls(self):
        return [r[0] for r in self._con.execute(
            "SELECT DISTINCT model FROM m0_5_quota_ledger WHERE kind = 'call'").fetchall()]

    def set_learned(self, model, field, value, at):
        self._insert(model=model, kind="learned", at_utc=_ts(at), field=field, value=value)

    def learned(self, model):
        rows = self._con.execute(
            "SELECT field, value FROM m0_5_quota_ledger WHERE model = ? AND kind = 'learned' ORDER BY id",
            (model,),
        ).fetchall()
        return {f: int(v) for f, v in rows}  # latest wins

    def add_block(self, model, reason, until, at):
        self._insert(model=model, kind="block", at_utc=_ts(at), reason=reason, until_utc=_ts(until))

    def active_block(self, model, now):
        row = self._con.execute(
            "SELECT reason, until_utc FROM m0_5_quota_ledger WHERE model = ? AND kind = 'block' AND until_utc > ? "
            "ORDER BY until_utc DESC LIMIT 1",
            (model, _ts(now)),
        ).fetchone()
        return Block(row[0], _parse(row[1])) if row else None

    def set_paid_latch(self, on, at):
        self._insert(model=PAID_LATCH_MODEL, kind="latch", at_utc=_ts(at), value=1 if on else 0)

    def paid_latch(self):
        row = self._con.execute(
            "SELECT value FROM m0_5_quota_ledger WHERE kind = 'latch' ORDER BY id DESC LIMIT 1").fetchone()
        return bool(row and row[0])
