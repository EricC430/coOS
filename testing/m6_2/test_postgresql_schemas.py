"""
M6.2 -- Cloud PostgreSQL schema acceptance tests

SPEC: docs/modules/M6_2_postgresql_schemas_SPEC.md
Risk: RISK-12 (no L1 plaintext in cloud tables)
Research: [R03 §1.1] BDI personality_prompt structure

Cloud-dependent tests skip automatically when SUPABASE_DB_URL is not set.
Local-verifiable tests (migration file audits, privacy boundary) always run.
"""
import os
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CLOUD_MIGRATION_DIR = (
    PROJECT_ROOT / "services" / "alembic_cloud" / "versions"
)

_HAS_CLOUD = bool(os.environ.get("SUPABASE_DB_URL"))

requires_cloud = pytest.mark.skipif(
    not _HAS_CLOUD,
    reason="SUPABASE_DB_URL not set -- skipping cloud integration tests",
)


# ---------------------------------------------------------------------------
# Local-verifiable: migration file audit (always runs)
# ---------------------------------------------------------------------------

class TestMigrationFileAudit:
    def test_cloud_migration_dir_exists(self):
        """AC: alembic_cloud/versions directory must exist."""
        assert CLOUD_MIGRATION_DIR.exists(), (
            "alembic_cloud/versions not found -- run M6.2 migration setup"
        )

    def test_cloud_migration_exists(self):
        """AC: at least one cloud migration file must exist."""
        migrations = list(CLOUD_MIGRATION_DIR.glob("*.py"))
        non_init = [f for f in migrations if f.name != "__init__.py"]
        assert len(non_init) >= 1, "No cloud migration files found"

    def test_cloud_migration_contains_expected_tables(self):
        """AC: cloud migration defines all required L3 tables."""
        content = ""
        for f in CLOUD_MIGRATION_DIR.glob("*.py"):
            if f.name != "__init__.py":
                content += f.read_text(encoding="utf-8")
        for table in ("users", "ai_experts", "roles", "xp_ledger", "badge_definitions"):
            assert table in content, f"Table '{table}' missing from cloud migration"


class TestPrivacyBoundaryStatic:
    """AC: cloud migrations must NEVER define L1 tables."""

    L1_TABLES = {"raw_tracking_logs", "chat_transcripts", "edge_event_buffer"}

    def test_no_l1_tables_in_cloud_migration(self):
        """AC-7: L1 plaintext tables must not be CREATED in cloud migrations."""
        import re
        # Only scan create_table() calls and CREATE TABLE statements, not docstrings.
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
            for table in self.L1_TABLES:
                assert table not in created, (
                    f"Cloud migration {f.name} creates L1 table '{table}' "
                    f"-- this violates the privacy layer principle (CLAUDE.md)"
                )

    def test_xp_ledger_has_nonzero_check_in_migration(self):
        """AC: xp_ledger.amount CHECK != 0 must be present (RISK-12 audit trail)."""
        content = ""
        for f in CLOUD_MIGRATION_DIR.glob("*.py"):
            if f.name != "__init__.py":
                content += f.read_text(encoding="utf-8")
        assert "amount != 0" in content or "chk_xp_nonzero" in content, (
            "xp_ledger missing CHECK amount != 0 constraint"
        )

    def test_ai_experts_personality_prompt_length_limited(self):
        """AC: personality_prompt must be limited (4096 chars per SPEC §7.2)."""
        content = ""
        for f in CLOUD_MIGRATION_DIR.glob("*.py"):
            if f.name != "__init__.py":
                content += f.read_text(encoding="utf-8")
        assert "4096" in content, (
            "ai_experts.personality_prompt 4096 char limit not found in migration"
        )


class TestEngineModule:
    def test_get_cloud_engine_returns_none_without_url(self, monkeypatch):
        """AC: engine factory returns None gracefully when URL not set."""
        monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
        # Reset module singleton
        import importlib

        import services.m6_2_postgresql.engine as eng_mod
        eng_mod._engine = None
        importlib.reload(eng_mod)

        engine = eng_mod.get_cloud_engine()
        assert engine is None

    def test_is_cloud_available_returns_false_without_url(self, monkeypatch):
        """AC: is_cloud_available() returns False when URL not set."""
        monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
        import importlib

        import services.m6_2_postgresql.engine as eng_mod
        eng_mod._engine = None
        importlib.reload(eng_mod)

        assert eng_mod.is_cloud_available() is False


# ---------------------------------------------------------------------------
# Cloud-dependent tests (skip when no Supabase URL)
# ---------------------------------------------------------------------------

@requires_cloud
class TestCloudTableCreation:
    @pytest.fixture
    def cloud_db(self):
        """Run Alembic cloud upgrade and return a raw psycopg2 connection."""
        import subprocess
        services_dir = PROJECT_ROOT / "services"
        result = subprocess.run(
            ["uv", "run", "alembic", "-c", "alembic_cloud.ini", "upgrade", "head"],
            cwd=str(services_dir),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"Cloud Alembic upgrade failed:\n{result.stdout}\n{result.stderr}"
        )
        from sqlalchemy import create_engine
        engine = create_engine(os.environ["SUPABASE_DB_URL"])
        with engine.connect() as conn:
            yield conn
        engine.dispose()

    def test_users_table_exists(self, cloud_db):
        """AC-1: users table exists after cloud migration."""
        result = cloud_db.execute(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_name = 'users')"
        )
        assert result.fetchone()[0] is True

    def test_ai_experts_table_exists(self, cloud_db):
        """AC-2: ai_experts table exists."""
        result = cloud_db.execute(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_name = 'ai_experts')"
        )
        assert result.fetchone()[0] is True

    def test_xp_ledger_table_exists(self, cloud_db):
        """AC-3: xp_ledger table exists."""
        result = cloud_db.execute(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_name = 'xp_ledger')"
        )
        assert result.fetchone()[0] is True

    def test_no_l1_tables_in_cloud(self, cloud_db):
        """AC-7: L1 tables must not be present in cloud DB."""
        result = cloud_db.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public'"
        )
        table_names = {row[0] for row in result.fetchall()}
        l1_tables = {"raw_tracking_logs", "chat_transcripts", "edge_event_buffer"}
        assert l1_tables.isdisjoint(table_names), (
            f"L1 tables found in cloud DB: {l1_tables & table_names}"
        )
