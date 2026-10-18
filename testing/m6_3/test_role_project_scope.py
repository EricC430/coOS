"""
M6.3 -- role_projects scoping in the local store (services/main.py)

SPEC: docs/modules/M6_3_role_context_tables_SPEC.md §6 AC-1, AC-2
Risk: RISK-06 (one role's context must never leak into another's)
Research: [R03 §6] role switch must fully reset Persona context

The SPEC examples target the cloud tables, but main.py reads and writes
role_projects in local SQLite (AsyncDBAdapter local-table routing). These tests
build those tables from main.py's own DDL and load projects through the
production loader, M4.3 build_role_context. No sidecar or cloud DB is needed.
"""
import asyncio
import re
import sqlite3
import uuid
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAIN_PY = PROJECT_ROOT / "services" / "main.py"

_MAIN_PY_TABLES = (
    "ai_experts", "role_router_rules", "role_projects",
    "role_settings", "goals", "promises",
)


def _local_ddl(table: str) -> str:
    """Return main.py's CREATE TABLE statement for one local table."""
    source = MAIN_PY.read_text(encoding="utf-8")
    match = re.search(
        rf"CREATE TABLE IF NOT EXISTS {table} \((.*?)\n\s*\)\n\s*\"\"\"",
        source,
        re.DOTALL,
    )
    assert match, f"DDL for {table} not found in services/main.py"
    return f"CREATE TABLE IF NOT EXISTS {table} ({match.group(1)}\n)"


class _SqliteDB:
    """Async fetch/execute surface matching what build_role_context calls."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    async def fetch_all(self, query, params=None):
        return [dict(r) for r in self._conn.execute(query, params or {}).fetchall()]

    async def fetch_one(self, query, params=None):
        row = self._conn.execute(query, params or {}).fetchone()
        return dict(row) if row else None

    async def execute(self, query, params=None):
        query = query.replace("NOW()", "(strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))")
        self._conn.execute(query, params or {})
        self._conn.commit()


@pytest.fixture
def local_db(tmp_path):
    conn = sqlite3.connect(tmp_path / "coos_local.db")
    conn.row_factory = sqlite3.Row
    for table in _MAIN_PY_TABLES:
        conn.execute(_local_ddl(table))
    # role_implicit_states comes from the local Alembic migration, not main.py;
    # build_role_context only needs these columns.
    conn.execute(
        "CREATE TABLE role_implicit_states (id TEXT PRIMARY KEY, user_id TEXT, "
        "role_id TEXT, label TEXT, confidence REAL, inferred_at TEXT, expires_at TEXT)"
    )
    conn.commit()
    yield conn
    conn.close()


def _add_project(conn, role_id: str, name: str) -> None:
    conn.execute(
        "INSERT INTO role_projects (id, role_id, name) VALUES (?, ?, ?)",
        (str(uuid.uuid4()), role_id, name),
    )
    conn.commit()


def _context(conn, user_id: uuid.UUID, role_id: uuid.UUID):
    from services.m4_3_role_isolation.context import build_role_context
    return asyncio.run(build_role_context(user_id, role_id, db=_SqliteDB(conn)))


class TestRoleProjectRelation:
    def test_project_belongs_to_role(self, local_db):
        """AC-1: a project is bound to a role_id and loads in that role's context."""
        user_id, role_id = uuid.uuid4(), uuid.uuid4()
        _add_project(local_db, str(role_id), "微積分")

        ctx = _context(local_db, user_id, role_id)
        assert [p["name"] for p in ctx.projects] == ["微積分"]

        # role_id is NOT NULL: a project cannot exist without a role
        with pytest.raises(sqlite3.IntegrityError):
            local_db.execute(
                "INSERT INTO role_projects (id, role_id, name) VALUES (?, NULL, ?)",
                (str(uuid.uuid4()), "orphan"),
            )

    def test_project_not_visible_across_roles(self, local_db):
        """AC-2: [RISK-06] one role's projects never load into another role's context."""
        user_id = uuid.uuid4()
        role_csie, role_family = uuid.uuid4(), uuid.uuid4()
        _add_project(local_db, str(role_csie), "CSIE專屬")

        csie_ctx = _context(local_db, user_id, role_csie)
        family_ctx = _context(local_db, user_id, role_family)

        # Positive control: the loader does read projects
        assert [p["name"] for p in csie_ctx.projects] == ["CSIE專屬"]
        assert family_ctx.projects == []

        # UNIQUE(role_id, name) is per role: the same name is allowed in another role
        _add_project(local_db, str(role_family), "CSIE專屬")
        assert len(_context(local_db, user_id, role_family).projects) == 1
