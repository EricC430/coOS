"""M0.5.5 isolation helpers -- the only way M0.5 opens a SQLite file.

[RISK-24] Synthetic rows must never reach data/coos.db or the paper's N=1 data:
  1. refuse the real DB path (Settings.local_db_path) and any file named coos.db
  2. stamp new files with PRAGMA application_id = SYNTHETIC_APP_ID and refuse
     existing files that carry tables but not the sentinel
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

SYNTHETIC_APP_ID = 0x434F5335  # "COS5"


class RealDatabaseRefused(RuntimeError):
    """Raised when M0.5 is pointed at anything that is not a synthetic DB."""


def _real_db_path() -> Path | None:
    try:
        from config import Settings  # services/config.py (M0.3)
    except ImportError:
        return None
    return Settings(_env_file=None).local_db_path.resolve()


def assert_synthetic_target(path: Path) -> Path:
    resolved = Path(path).resolve()
    if resolved.name.lower() == "coos.db":
        raise RealDatabaseRefused(f"refusing real database name: {resolved}")
    real = _real_db_path()
    if real is not None and resolved == real:
        raise RealDatabaseRefused(f"refusing Settings.local_db_path: {resolved}")
    return resolved


def open_synthetic_db(path: Path) -> sqlite3.Connection:
    resolved = assert_synthetic_target(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(resolved)
    app_id = con.execute("PRAGMA application_id").fetchone()[0]
    has_tables = con.execute("SELECT COUNT(*) FROM sqlite_master WHERE type = 'table'").fetchone()[0] > 0
    if app_id == SYNTHETIC_APP_ID:
        return con
    if app_id == 0 and not has_tables:
        con.execute(f"PRAGMA application_id = {SYNTHETIC_APP_ID}")
        con.commit()
        return con
    con.close()
    raise RealDatabaseRefused(f"not a synthetic database (application_id={app_id:#x}): {resolved}")
