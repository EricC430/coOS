"""
M6.1 -- Local SQLite Schema acceptance tests

SPEC: docs/modules/M6_1_sqlite_schemas_SPEC.md
Risk: RISK-05 (edge_event_buffer.source_log_id FK must exist)
"""
import os
import sqlite3
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SERVICES_DIR = PROJECT_ROOT / "services"


@pytest.fixture
def local_db(tmp_path):
    """Run Alembic upgrade against a fresh SQLite DB and return a connection."""
    db_path = tmp_path / "test_coos.db"
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
        f"Alembic upgrade failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
    )
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys=ON")
    yield conn
    conn.close()


class TestTableCreation:
    def test_raw_tracking_logs_table_exists(self, local_db):
        """AC-1: raw_tracking_logs table exists after migration."""
        cursor = local_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='raw_tracking_logs'"
        )
        assert cursor.fetchone() is not None

    def test_edge_event_buffer_table_exists(self, local_db):
        """AC-2: edge_event_buffer table exists."""
        cursor = local_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='edge_event_buffer'"
        )
        assert cursor.fetchone() is not None

    def test_chat_transcripts_table_exists(self, local_db):
        """AC-3: chat_transcripts table exists."""
        cursor = local_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='chat_transcripts'"
        )
        assert cursor.fetchone() is not None

    def test_user_consents_table_exists(self, local_db):
        """AC-4: user_consents table exists."""
        cursor = local_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='user_consents'"
        )
        assert cursor.fetchone() is not None


class TestSchemaConstraints:
    def test_raw_tracking_logs_has_required_columns(self, local_db):
        """AC-5: raw_tracking_logs has all required columns."""
        cursor = local_db.execute("PRAGMA table_info(raw_tracking_logs)")
        columns = {row[1] for row in cursor.fetchall()}
        required = {"id", "timestamp", "module", "action", "level", "payload"}
        assert required.issubset(columns)

    def test_edge_event_buffer_has_source_log_id(self, local_db):
        """AC-6: edge_event_buffer must have source_log_id (RISK-05 mitigation)."""
        cursor = local_db.execute("PRAGMA table_info(edge_event_buffer)")
        columns = {row[1] for row in cursor.fetchall()}
        assert "source_log_id" in columns

    def test_chat_transcripts_role_is_constrained(self, local_db):
        """AC-7: chat_transcripts.role only accepts user/assistant/system."""
        with pytest.raises(sqlite3.IntegrityError):
            local_db.execute(
                "INSERT INTO chat_transcripts (id, thread_id, role, content) "
                "VALUES ('test', 'thread_1', 'invalid_role', 'hello')"
            )
            local_db.commit()

    def test_edge_event_buffer_foreign_key_enforced(self, local_db):
        """AC-6b: edge_event_buffer.source_log_id FK must be enforced (RISK-05)."""
        with pytest.raises(sqlite3.IntegrityError):
            local_db.execute(
                "INSERT INTO edge_event_buffer "
                "(id, source_log_id, intent_tag, confidence, model_version) "
                "VALUES ('e1', 'nonexistent_log_id', 'coding', 0.9, 'gemma-4-e4b')"
            )
            local_db.commit()

    def test_all_tables_use_uuid_primary_key(self, local_db):
        """AC-8: All tables must use TEXT (UUID) primary keys, not AUTOINCREMENT."""
        tables = ["raw_tracking_logs", "edge_event_buffer", "chat_transcripts", "user_consents"]
        for table in tables:
            cursor = local_db.execute(f"PRAGMA table_info({table})")
            cols = cursor.fetchall()
            pk_cols = [row for row in cols if row[5] == 1]  # col[5] = pk flag
            assert len(pk_cols) == 1, f"{table} should have exactly one PK"
            assert pk_cols[0][2].upper() == "TEXT", (
                f"{table} PK must be TEXT (UUID), got {pk_cols[0][2]}"
            )


class TestWALMode:
    def test_sqlite_wal_mode_enabled(self, local_db):
        """AC-9: SQLite must use WAL journal mode."""
        cursor = local_db.execute("PRAGMA journal_mode=WAL")
        mode = cursor.fetchone()[0]
        assert mode.lower() == "wal"
