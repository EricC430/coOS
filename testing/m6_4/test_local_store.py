"""
M6.4 -- Daily reflections in the local SQLite store (services/main.py)

SPEC: docs/modules/M6_4_daily_reflections_SPEC.md §6 AC-1, AC-7
Risk: RISK-01 (drafts never auto-approved), RISK-10 (mood_score baseline)
Research:
  [R08 §五] AI fills the objective part; the draft waits for the user

test_daily_reflections.py covers the dataclass and Pydantic layers. Segments are
actually persisted to the local SQLite tables that main.py creates at startup,
so these tests build those tables from main.py's own DDL in a temp file and run
the production AsyncDBAdapter against them. No sidecar or cloud DB is needed.
"""
import asyncio
import re
import sqlite3
import uuid
from datetime import date
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAIN_PY = PROJECT_ROOT / "services" / "main.py"


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


@pytest.fixture
def local_db(tmp_path):
    path = tmp_path / "coos_local.db"
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute(_local_ddl("daily_reflections"))
    conn.execute(_local_ddl("daily_reflection_segments"))
    conn.commit()
    yield conn, path
    conn.close()


class TestDraftCreation:
    def test_new_reflection_is_draft(self, local_db):
        """AC-1: [R08 §五] a reflection created by the draft path is stored as a draft."""
        from services.main import AsyncDBAdapter

        conn, path = local_db
        adapter = AsyncDBAdapter(conn, pg_engine=None, sqlite_path=str(path))
        created = asyncio.run(adapter.create_draft_reflection(
            user_id=str(uuid.uuid4()),
            role_id=str(uuid.uuid4()),
            reflection_date=date.today(),
            ai_description="VS Code 寫了 3 小時 Rust",
            ai_analysis="專注度高，但最後 30 分鐘效率下降",
            activity_minutes=180,
        ))

        assert created.is_draft is True
        assert created.is_reviewed is False
        assert created.user_feeling is None
        assert created.user_action_plan is None

        rows = conn.execute(
            "SELECT is_draft, is_reviewed, xp_settled, user_feeling, user_action_plan "
            "FROM daily_reflection_segments WHERE reflection_id = ?",
            (created.id,),
        ).fetchall()
        assert len(rows) == 1
        row = rows[0]
        assert row["is_draft"] == 1
        assert row["is_reviewed"] == 0  # [RISK-01] never auto-approved
        assert row["xp_settled"] == 0
        assert row["user_feeling"] is None
        assert row["user_action_plan"] is None


class TestMoodScoreConstraints:
    @pytest.mark.xfail(
        strict=True,
        reason=(
            "BUG: the local SQLite daily_reflection_segments table created in "
            "services/main.py has no mood_score column, so the 1-10 range is not "
            "enforced where segments are stored. PATCH /api/m6_4/reflections/{id} "
            "with mood_score fails inside AsyncDBAdapter.execute, which logs and "
            "swallows the error, so the whole update (including is_reviewed) is lost."
        ),
    )
    def test_mood_score_range(self, local_db):
        """AC-7: [RISK-10] the stored mood_score must be within 1-10."""
        conn, _ = local_db
        cols = {r[1] for r in conn.execute("PRAGMA table_info(daily_reflection_segments)")}
        assert "mood_score" in cols

        base = {
            "reflection_id": str(uuid.uuid4()),
            "user_id": str(uuid.uuid4()),
            "role_id": str(uuid.uuid4()),
            "start_time": "09:00",
            "end_time": "10:00",
        }
        insert = (
            "INSERT INTO daily_reflection_segments "
            "(id, reflection_id, user_id, role_id, start_time, end_time, mood_score) "
            "VALUES (:id, :reflection_id, :user_id, :role_id, :start_time, :end_time, :mood)"
        )
        conn.execute(insert, {**base, "id": str(uuid.uuid4()), "mood": 7})
        for bad in (0, 11):
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(insert, {**base, "id": str(uuid.uuid4()), "mood": bad})
