"""
M6.1 -- SQLite connection factory with WAL and FK enforcement

SPEC: docs/modules/M6_1_sqlite_schemas_SPEC.md §7.5
"""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

_DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "coos.db"

_INIT_PRAGMAS = [
    "PRAGMA journal_mode=WAL",
    "PRAGMA synchronous=NORMAL",
    "PRAGMA foreign_keys=ON",
    "PRAGMA busy_timeout=5000",
    "PRAGMA cache_size=-65536",  # ~64 MB
]


def _apply_pragmas(conn: sqlite3.Connection) -> None:
    for pragma in _INIT_PRAGMAS:
        conn.execute(pragma)


def open_sqlite(db_path: str | None = None) -> sqlite3.Connection:
    """Open a SQLite connection with WAL mode and FK enforcement."""
    path = str(db_path or _DEFAULT_DB)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    _apply_pragmas(conn)
    return conn


@contextmanager
def init_sqlite(db_path: str | None = None):
    """Context manager: open connection, apply pragmas, yield, close."""
    conn = open_sqlite(db_path)
    try:
        yield conn
    finally:
        conn.close()
