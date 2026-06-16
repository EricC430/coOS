"""
M0.4 -- Structured Logging acceptance tests

SPEC: docs/modules/M0_4_structured_logging_SPEC.md
No research citations (infrastructure module).
"""
import asyncio
import json
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class TestLogEventSchema:
    def test_log_event_has_required_fields(self):
        """AC-1: LogEvent must contain module, action, timestamp, level."""
        from services.m0_4_logging.schema import LogEvent

        event = LogEvent(
            module="M4.2",
            action="echo_mode_transition",
            level="INFO",
            payload={"from_agency": 0.85, "to_agency": 0.70},
        )
        assert event.module == "M4.2"
        assert event.action == "echo_mode_transition"
        assert event.level == "INFO"
        assert event.timestamp is not None

    def test_log_event_rejects_invalid_module_id(self):
        """AC-2: module ID must match Mx.y format."""
        from services.m0_4_logging.schema import LogEvent

        with pytest.raises(ValueError):
            LogEvent(module="random_name", action="test", level="INFO")

    def test_log_event_rejects_invalid_level(self):
        """AC-2b: level must be one of DEBUG/INFO/WARNING/ERROR/AUDIT."""
        from services.m0_4_logging.schema import LogEvent

        with pytest.raises(ValueError):
            LogEvent(module="M0.4", action="test", level="VERBOSE")

    def test_log_event_level_normalised_to_upper(self):
        """AC-2c: level is normalised to uppercase."""
        from services.m0_4_logging.schema import LogEvent

        event = LogEvent(module="M0.4", action="test", level="info")
        assert event.level == "INFO"

    def test_log_event_defaults_populated(self):
        """AC-1b: id and timestamp have sane defaults."""
        from services.m0_4_logging.schema import LogEvent

        e = LogEvent(module="M0.4", action="boot")
        assert e.id  # non-empty UUID string
        assert e.timestamp is not None
        assert e.level == "INFO"


class TestLogWriter:
    def test_log_writes_to_sqlite(self, tmp_path):
        """AC-3: log event is persisted to SQLite raw_tracking_logs."""
        from services.m0_4_logging.writer import LogWriter

        db_path = tmp_path / "test.db"
        writer = LogWriter(db_path=str(db_path))
        writer.init_table()
        writer.write(
            module="M0.4",
            action="test_write",
            level="INFO",
            payload={"key": "value"},
        )
        rows = writer.query_all()
        assert len(rows) == 1
        assert rows[0]["module"] == "M0.4"
        assert rows[0]["action"] == "test_write"
        payload = json.loads(rows[0]["payload"])
        assert payload["key"] == "value"

    def test_log_multiple_writes(self, tmp_path):
        """AC-3b: multiple events are all stored."""
        from services.m0_4_logging.writer import LogWriter

        writer = LogWriter(db_path=str(tmp_path / "test.db"))
        writer.init_table()
        for i in range(5):
            writer.write(module="M0.4", action=f"event_{i}", level="DEBUG")
        rows = writer.query_all()
        assert len(rows) == 5

    def test_log_async_does_not_block(self, tmp_path):
        """AC-4: async emit returns in < 50 ms (fire-and-forget)."""
        import time

        from services.m0_4_logging.writer import AsyncLogWriter

        db_path = str(tmp_path / "async_test.db")
        writer = AsyncLogWriter(db_path=db_path)

        async def run():
            await writer.start()
            start = time.monotonic()
            await writer.emit(module="M0.4", action="perf_test", level="DEBUG")
            elapsed_ms = (time.monotonic() - start) * 1000
            await writer.stop()
            return elapsed_ms

        elapsed = asyncio.run(run())
        assert elapsed < 50

    def test_query_by_module(self, tmp_path):
        """AC-3c: query_by_module returns only matching rows."""
        from services.m0_4_logging.writer import LogWriter

        writer = LogWriter(db_path=str(tmp_path / "test.db"))
        writer.init_table()
        writer.write(module="M0.4", action="a", level="INFO")
        writer.write(module="M1.1", action="b", level="INFO")
        rows = writer.query_by_module("M0.4")
        assert len(rows) == 1
        assert rows[0]["module"] == "M0.4"


class TestLogPrivacy:
    def test_raw_tracking_logs_table_is_local_only(self):
        """AC-5: raw_tracking_logs must NOT appear in cloud migration files."""
        # Cloud alembic config should not reference raw_tracking_logs table
        # (table creation happens only in local migration)
        local_migration_dir = PROJECT_ROOT / "services" / "alembic" / "versions"
        local_files = list(local_migration_dir.glob("*.py"))
        # At least one local migration file must exist
        assert len(local_files) >= 1
        # No cloud-specific migration file should create raw_tracking_logs
        # (cloud migrations live in a separate directory if present)
        import re
        table_create_re = re.compile(
            r'(?:op\.create_table\s*\(\s*["\'])(\w+)|'
            r'(?:CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?)(\w+)',
            re.IGNORECASE,
        )
        cloud_migration_dir = PROJECT_ROOT / "services" / "alembic_cloud" / "versions"
        if cloud_migration_dir.exists():
            for f in cloud_migration_dir.glob("*.py"):
                content = f.read_text(encoding="utf-8")
                created = {
                    (m.group(1) or m.group(2)).lower()
                    for m in table_create_re.finditer(content)
                }
                assert "raw_tracking_logs" not in created, (
                    f"Cloud migration {f.name} must not CREATE raw_tracking_logs"
                )

    def test_payload_does_not_contain_raw_text_marker(self):
        """AC-6: payload must not contain L1 plaintext field names."""
        from services.m0_4_logging.schema import LogEvent

        event = LogEvent(
            module="M1.1",
            action="keystroke_captured",
            level="DEBUG",
            payload={"event_type": "keypress", "count": 42},
        )
        forbidden_keys = {"raw_text", "raw_code", "transcript", "browsing_content"}
        assert not forbidden_keys.intersection(event.payload.keys())

    def test_payload_with_forbidden_keys_raises(self):
        """AC-6b: LogEvent should warn/raise if forbidden keys present in payload."""
        from services.m0_4_logging.schema import LogEvent

        # The schema validator strips or raises on forbidden L1 keys
        with pytest.raises(ValueError):
            LogEvent(
                module="M1.1",
                action="bad_log",
                level="INFO",
                payload={"raw_text": "user typed secret"},
            )


class TestSeparatedLogging:
    def test_llm_inference_log_writes_to_sqlite(self, tmp_path):
        """Verify that LLM calls are written directly to llm_inference_logs table."""
        import sqlite3
        from services.m0_4_logging.writer import LogWriter

        db_path = tmp_path / "test_llm.db"
        writer = LogWriter(db_path=str(db_path))
        writer.init_table()

        writer.write_llm_log(
            model_name="gemini-3.5-pro",
            caller_module="M4.1",
            prompt_text="What is 2+2?",
            response_text="4",
            prompt_tokens=10,
            completion_tokens=2,
            latency_ms=150,
            temperature=0.7,
            status="success"
        )

        conn = sqlite3.connect(str(db_path))
        try:
            rows = conn.execute("SELECT * FROM llm_inference_logs").fetchall()
            assert len(rows) == 1
            row = rows[0]
            assert row[2] == "gemini-3.5-pro"
            assert row[3] == "M4.1"
            assert row[4] == "What is 2+2?"
            assert row[5] == "4"
            assert row[6] == 10  # prompt_tokens
            assert row[7] == 2   # completion_tokens
            assert row[8] == 150 # latency_ms
            assert row[9] == 0.7 # temperature
            assert row[10] == "success"
        finally:
            conn.close()

    def test_system_execution_log_writes_to_sqlite(self, tmp_path):
        """Verify that system execution logs are written directly to system_execution_logs table."""
        import sqlite3
        from services.m0_4_logging.writer import LogWriter

        db_path = tmp_path / "test_exec.db"
        writer = LogWriter(db_path=str(db_path))
        writer.init_table()

        writer.write_execution_log(
            module="main",
            action="db_error",
            level="ERROR",
            message="Database connection timed out",
            exception_trace="Traceback: ...",
            payload={"retry_attempt": 3}
        )

        conn = sqlite3.connect(str(db_path))
        try:
            rows = conn.execute("SELECT * FROM system_execution_logs").fetchall()
            assert len(rows) == 1
            row = rows[0]
            assert row[2] == "main"
            assert row[3] == "db_error"
            assert row[4] == "ERROR"
            assert row[5] == "Database connection timed out"
            assert row[6] == "Traceback: ..."
            import json
            payload = json.loads(row[7])
            assert payload["retry_attempt"] == 3
        finally:
            conn.close()

    def test_async_multi_table_batch_write(self, tmp_path):
        """Verify that AsyncLogWriter can write to all three tables concurrently and asynchronously."""
        import sqlite3
        from services.m0_4_logging.writer import AsyncLogWriter

        db_path = str(tmp_path / "async_multi.db")
        writer = AsyncLogWriter(db_path=db_path)

        async def run():
            await writer.start()
            await writer.emit(module="M0.4", action="RTL_event")
            await writer.emit_llm_log(
                model_name="gemini-flash",
                caller_module="M4.1",
                prompt_text="Hello prompt",
                response_text="Hello response"
            )
            await writer.emit_execution_log(
                module="main",
                action="test_error",
                message="Test error message"
            )
            await writer.stop()

        import asyncio
        asyncio.run(run())

        conn = sqlite3.connect(db_path)
        try:
            rtl = conn.execute("SELECT * FROM raw_tracking_logs").fetchall()
            assert len(rtl) == 1
            assert rtl[0][3] == "RTL_event"

            lil = conn.execute("SELECT * FROM llm_inference_logs").fetchall()
            assert len(lil) == 1
            assert lil[0][2] == "gemini-flash"
            assert lil[0][4] == "Hello prompt"

            sel = conn.execute("SELECT * FROM system_execution_logs").fetchall()
            assert len(sel) == 1
            assert sel[0][2] == "main"
            assert sel[0][5] == "Test error message"
        finally:
            conn.close()

