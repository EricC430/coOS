"""
M6.3 -- Role Context Tables acceptance tests

SPEC: docs/modules/M6_3_role_context_tables_SPEC.md
Risk: RISK-06 (role_implicit_states must be scoped by (user_id, role_id))
Research: [R03 §6] role switch must fully reset Persona state

Architecture decision (SPEC §9):
- role_projects + role_settings -> cloud PostgreSQL (M6.2 track)
- role_implicit_states          -> local SQLite (M6.1 track)

Cloud tests skip when SUPABASE_DB_URL is not set.
Local implicit-state tests always run.
"""
import os
import sqlite3
import subprocess
import uuid
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SERVICES_DIR = PROJECT_ROOT / "services"
CLOUD_MIGRATION_DIR = SERVICES_DIR / "alembic_cloud" / "versions"

_HAS_CLOUD = bool(os.environ.get("SUPABASE_DB_URL"))
requires_cloud = pytest.mark.skipif(
    not _HAS_CLOUD,
    reason="SUPABASE_DB_URL not set -- skipping cloud integration tests",
)


# ---------------------------------------------------------------------------
# Static migration audit (always runs)
# ---------------------------------------------------------------------------

class TestMigrationAudit:
    def test_cloud_migration_has_role_projects(self):
        """AC: cloud migration must define role_projects table."""
        content = _cloud_migration_content()
        assert "role_projects" in content

    def test_cloud_migration_has_role_settings(self):
        """AC: cloud migration must define role_settings table."""
        content = _cloud_migration_content()
        assert "role_settings" in content

    def test_local_migration_has_role_implicit_states(self):
        """AC: local SQLite migration must define role_implicit_states (SPEC §9)."""
        content = _local_migration_content()
        assert "role_implicit_states" in content

    def test_role_implicit_states_not_in_cloud_migration(self):
        """AC: role_implicit_states must NOT appear as a created table in cloud (privacy)."""
        import re
        table_create_re = re.compile(
            r'(?:op\.create_table\s*\(\s*["\'])(\w+)|'
            r'(?:CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?)(\w+)',
            re.IGNORECASE,
        )
        for f in CLOUD_MIGRATION_DIR.glob("*.py"):
            if f.name == "__init__.py":
                continue
            content = f.read_text(encoding="utf-8")
            created = {
                (m.group(1) or m.group(2)).lower()
                for m in table_create_re.finditer(content)
            }
            assert "role_implicit_states" not in created, (
                f"{f.name} creates role_implicit_states in cloud -- "
                "it must be local SQLite only (SPEC §9 decision)"
            )

    def test_role_implicit_states_has_dual_key_index(self):
        """AC: [RISK-06] role_implicit_states must have (user_id, role_id) composite index."""
        content = _local_migration_content()
        assert "user_id" in content and "role_id" in content
        assert "idx_ris_user_role" in content or (
            "user_id, role_id" in content or "user_id,role_id" in content
        )

    def test_cascade_delete_in_cloud_migration(self):
        """AC: role_projects and role_settings must have ON DELETE CASCADE."""
        content = _cloud_migration_content()
        assert "ondelete" in content.lower() or "ON DELETE CASCADE" in content.upper()


# ---------------------------------------------------------------------------
# Pydantic model tests (always runs)
# ---------------------------------------------------------------------------

class TestPydanticModels:
    def test_role_implicit_state_confidence_range(self):
        """AC: [RISK-06] RoleImplicitState.confidence must be in [0, 1]."""
        import pytest as _pytest
        from services.m6_3_role_context.models import RoleImplicitState

        valid = RoleImplicitState(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            role_id=uuid.uuid4(),
            label="anxiety",
            confidence=0.85,
        )
        assert valid.confidence == 0.85

        with _pytest.raises(Exception):
            RoleImplicitState(
                id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                role_id=uuid.uuid4(),
                label="anxiety",
                confidence=1.5,  # out of range
            )

    def test_role_project_name_max_length(self):
        """AC: RoleProject.name must not exceed 100 chars."""
        import pytest as _pytest
        from services.m6_3_role_context.models import RoleProject

        with _pytest.raises(Exception):
            RoleProject(
                id=uuid.uuid4(),
                role_id=uuid.uuid4(),
                name="x" * 101,
            )

    def test_role_setting_defaults(self):
        """AC: RoleSetting has sane time defaults."""
        from datetime import time

        from services.m6_3_role_context.models import RoleSetting
        s = RoleSetting(id=uuid.uuid4(), role_id=uuid.uuid4())
        assert s.daily_report_time == time(22, 0)
        assert s.focus_hours_start == time(9, 0)
        assert s.focus_hours_end == time(18, 0)


# ---------------------------------------------------------------------------
# Local SQLite tests (implicit state isolation) -- always runs
# ---------------------------------------------------------------------------

@pytest.fixture
def local_db_m6_3(tmp_path):
    """Alembic upgrade local SQLite and return an open connection."""
    db_path = tmp_path / "test_m6_3.db"
    env = {
        **os.environ,
        "LOCAL_DB_PATH": str(db_path),
        "GEMINI_API_KEY": "",
        "SUPABASE_URL": "",
        "SUPABASE_KEY": "",
        "NEO4J_URI": "",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "",
    }
    result = subprocess.run(
        ["uv", "run", "alembic", "-c", "alembic_local.ini", "upgrade", "head"],
        cwd=str(SERVICES_DIR),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Alembic local upgrade failed:\n{result.stdout}\n{result.stderr}"
    )
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


class TestLocalImplicitStateIsolation:
    def test_implicit_state_table_exists(self, local_db_m6_3):
        """AC: role_implicit_states table exists in local SQLite."""
        cur = local_db_m6_3.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='role_implicit_states'"
        )
        assert cur.fetchone() is not None

    def test_implicit_state_scoped_by_user_and_role(self, local_db_m6_3):
        """AC: [RISK-06] querying by (user_id, role_id) returns only matching rows."""
        uid = str(uuid.uuid4())
        role_csie = str(uuid.uuid4())
        role_family = str(uuid.uuid4())

        local_db_m6_3.execute(
            "INSERT INTO role_implicit_states "
            "(id, user_id, role_id, label, confidence, source_module) "
            "VALUES (?, ?, ?, 'anxiety', 0.85, 'M4.8')",
            (str(uuid.uuid4()), uid, role_csie),
        )
        local_db_m6_3.commit()

        row = local_db_m6_3.execute(
            "SELECT * FROM role_implicit_states WHERE user_id=? AND role_id=?",
            (uid, role_family),
        ).fetchone()
        assert row is None, "role_family must not see role_csie implicit state (RISK-06)"

    def test_role_switch_does_not_inherit_state(self, local_db_m6_3):
        """AC: [RISK-06] after role switch, querying new role returns no inherited state."""
        uid = str(uuid.uuid4())
        role_a = str(uuid.uuid4())
        role_b = str(uuid.uuid4())

        local_db_m6_3.execute(
            "INSERT INTO role_implicit_states "
            "(id, user_id, role_id, label, confidence, source_module) "
            "VALUES (?, ?, ?, 'flow', 0.9, 'M4.8')",
            (str(uuid.uuid4()), uid, role_a),
        )
        local_db_m6_3.commit()

        # After switching to role_b, query role_b's state
        row = local_db_m6_3.execute(
            "SELECT label FROM role_implicit_states "
            "WHERE user_id=? AND role_id=? ORDER BY inferred_at DESC LIMIT 1",
            (uid, role_b),
        ).fetchone()
        assert row is None, "role_b must not inherit role_a's 'flow' state (RISK-06)"

    def test_implicit_state_confidence_check(self, local_db_m6_3):
        """AC: confidence must be in [0,1] (SQLite CHECK constraint)."""
        uid = str(uuid.uuid4())
        role_id = str(uuid.uuid4())

        with pytest.raises(sqlite3.IntegrityError):
            local_db_m6_3.execute(
                "INSERT INTO role_implicit_states "
                "(id, user_id, role_id, label, confidence, source_module) "
                "VALUES (?, ?, ?, 'anxiety', 1.5, 'M4.8')",
                (str(uuid.uuid4()), uid, role_id),
            )
            local_db_m6_3.commit()


# ---------------------------------------------------------------------------
# Cloud-dependent tests
# ---------------------------------------------------------------------------

@requires_cloud
class TestCloudRoleContextTables:
    @pytest.fixture
    def cloud_conn(self):
        services_dir = PROJECT_ROOT / "services"
        result = subprocess.run(
            ["uv", "run", "alembic", "-c", "alembic_cloud.ini", "upgrade", "head"],
            cwd=str(services_dir),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        from sqlalchemy import create_engine
        engine = create_engine(os.environ["SUPABASE_DB_URL"])
        with engine.connect() as conn:
            yield conn
        engine.dispose()

    def test_role_projects_table_exists(self, cloud_conn):
        """AC-1: role_projects table exists in cloud."""
        from sqlalchemy import text
        r = cloud_conn.execute(text(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_name='role_projects')"
        ))
        assert r.fetchone()[0] is True

    def test_role_settings_table_exists(self, cloud_conn):
        """AC-2: role_settings table exists in cloud."""
        from sqlalchemy import text
        r = cloud_conn.execute(text(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_name='role_settings')"
        ))
        assert r.fetchone()[0] is True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cloud_migration_content() -> str:
    content = ""
    for f in CLOUD_MIGRATION_DIR.glob("*.py"):
        if f.name != "__init__.py":
            content += f.read_text(encoding="utf-8")
    return content


def _local_migration_content() -> str:
    local_dir = SERVICES_DIR / "alembic" / "versions"
    content = ""
    for f in local_dir.glob("*.py"):
        if f.name != "__init__.py":
            content += f.read_text(encoding="utf-8")
    return content
