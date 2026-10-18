"""
M6.5 -- XPGatekeeper wired to the production LiveXPStore (services/main.py)

SPEC: docs/modules/M6_5_acid_gatekeeper_SPEC.md §6 AC-2, AC-4, §9 anti-patterns 2 and 4
Risk: RISK-01 (XP only after approval), RISK-14 (current_xp + lifetime_xp)

AC-2 is covered in-memory by test_acid_gatekeeper.py. This file runs the same
checks through the store that /api/m4_5/grant_xp actually builds: first with a
fake async DB adapter, then with the production AsyncDBAdapter against the
local tables built from main.py's own DDL in a temp file (no sidecar, no cloud).
"""
import asyncio
import re
import sqlite3
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAIN_PY = PROJECT_ROOT / "services" / "main.py"


class FakeAsyncDB:
    """Minimal AsyncDBAdapter stand-in: one approved segment, one user."""

    def __init__(self, claim_succeeds: bool = True):
        self.claim_succeeds = claim_succeeds
        self.atomic_batches: list[list[tuple[str, dict, bool]]] = []

    async def fetch_one(self, query, params=None):
        if "daily_reflection_segments" in query:
            return {
                "id": params["sid"],
                "reflection_id": None,
                "is_draft": 0,
                "is_reviewed": 1,
                "user_feeling": "focused",
                "xp_settled": 0,
            }
        if "FROM users" in query:
            return {"id": params["uid"], "current_xp": 0, "lifetime_xp": 0}
        return None

    async def execute_atomic(self, statements):
        self.atomic_batches.append(statements)
        return self.claim_succeeds


def test_live_store_settles_approved_segment():
    """AC-2 via LiveXPStore: an approved segment settles XP in one guarded transaction."""
    from services.m6_5_acid_gatekeeper.gatekeeper import XPGatekeeper
    from services.main import LiveXPStore

    db = FakeAsyncDB()
    gk = XPGatekeeper(LiveXPStore(db))
    result = gk.settle_segment_xp(uuid.uuid4(), uuid.uuid4(), 20)
    assert result.success is True

    assert len(db.atomic_batches) == 1
    claim, user_update, ledger = db.atomic_batches[0]
    # [SPEC §9 anti-pattern 2] claim is conditional and re-checks approval in SQL
    assert "xp_settled = 0" in claim[0] and "is_draft = 0" in claim[0]
    assert claim[2] is True
    # [SPEC §9 anti-pattern 4, RISK-14] relative increment on both columns
    assert "current_xp = current_xp + :dc" in user_update[0]
    assert "lifetime_xp = lifetime_xp + :dl" in user_update[0]
    assert user_update[1]["dc"] == 20 and user_update[1]["dl"] == 20
    assert "INSERT INTO xp_ledger" in ledger[0]


def test_live_store_lost_claim_reports_already_settled():
    """AC-3/AC-4: if the conditional UPDATE matches no row, settlement fails with GATEKEEPER_002."""
    from services.m6_5_acid_gatekeeper.gatekeeper import XPGatekeeper
    from services.main import LiveXPStore

    gk = XPGatekeeper(LiveXPStore(FakeAsyncDB(claim_succeeds=False)))
    result = gk.settle_segment_xp(uuid.uuid4(), uuid.uuid4(), 20)
    assert result.success is False
    assert result.error_code == "GATEKEEPER_002"


def test_live_store_refuses_use_inside_event_loop():
    """The store is sync; calling it on the event loop thread must fail loudly, not hang."""
    from services.main import LiveXPStore

    async def call_on_loop():
        LiveXPStore(FakeAsyncDB()).users.get(uuid.uuid4())

    with pytest.raises(RuntimeError, match="asyncio.to_thread"):
        asyncio.run(call_on_loop())


# ---------------------------------------------------------------------------
# Production AsyncDBAdapter on a temp SQLite file
# ---------------------------------------------------------------------------

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
def live_db(tmp_path):
    """Local users / xp_ledger / reflection tables with one user and one approved segment."""
    from services.main import AsyncDBAdapter

    path = tmp_path / "coos_local.db"
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    for table in ("users", "xp_ledger", "daily_reflections", "daily_reflection_segments"):
        conn.execute(_local_ddl(table))

    user_id = uuid.uuid4()
    conn.execute(
        "INSERT INTO users (id, username, current_xp, lifetime_xp) VALUES (?, 'u', 100, 300)",
        (str(user_id),),
    )

    def add_segment(is_draft=0, is_reviewed=1, user_feeling="focused"):
        seg_id = uuid.uuid4()
        conn.execute(
            "INSERT INTO daily_reflection_segments (id, reflection_id, user_id, role_id, "
            "start_time, end_time, activity_minutes, user_feeling, is_draft, is_reviewed) "
            "VALUES (?, ?, ?, 'r1', '09:00', '10:00', 60, ?, ?, ?)",
            (str(seg_id), str(uuid.uuid4()), str(user_id), user_feeling, is_draft, is_reviewed),
        )
        conn.commit()
        return seg_id

    conn.commit()
    adapter = AsyncDBAdapter(conn, pg_engine=None, sqlite_path=str(path))
    yield SimpleNamespace(conn=conn, adapter=adapter, user_id=user_id, add_segment=add_segment)
    conn.close()


def _state(db, seg_id):
    user = db.conn.execute(
        "SELECT current_xp, lifetime_xp FROM users WHERE id = ?", (str(db.user_id),)
    ).fetchone()
    seg = db.conn.execute(
        "SELECT xp_settled, is_reviewed FROM daily_reflection_segments WHERE id = ?", (str(seg_id),)
    ).fetchone()
    ledger = db.conn.execute(
        "SELECT amount FROM xp_ledger WHERE segment_id = ?", (str(seg_id),)
    ).fetchall()
    return user["current_xp"], user["lifetime_xp"], seg["xp_settled"], [r["amount"] for r in ledger]


def test_live_settlement_persists(live_db):
    """AC-2 + RISK-14 on real SQLite: XP, lifetime XP, ledger and xp_settled written together."""
    from services.m6_5_acid_gatekeeper.gatekeeper import XPGatekeeper
    from services.main import LiveXPStore

    seg_id = live_db.add_segment()
    result = XPGatekeeper(LiveXPStore(live_db.adapter)).settle_segment_xp(seg_id, live_db.user_id, 20)
    assert result.success is True
    assert _state(live_db, seg_id) == (120, 320, 1, [20])


def test_live_draft_segment_not_settled(live_db):
    """AC-1 / RISK-01 on real SQLite: a draft segment awards nothing and is_reviewed is untouched."""
    from services.m6_5_acid_gatekeeper.gatekeeper import XPGatekeeper
    from services.main import LiveXPStore

    seg_id = live_db.add_segment(is_draft=1, is_reviewed=0)
    result = XPGatekeeper(LiveXPStore(live_db.adapter)).settle_segment_xp(seg_id, live_db.user_id, 20)
    assert result.error_code == "GATEKEEPER_001"
    current, lifetime, settled, ledger = _state(live_db, seg_id)
    assert (current, lifetime, settled, ledger) == (100, 300, 0, [])
    reviewed = live_db.conn.execute(
        "SELECT is_reviewed FROM daily_reflection_segments WHERE id = ?", (str(seg_id),)
    ).fetchone()[0]
    assert reviewed == 0


def test_live_concurrent_settlement_awards_once(live_db):
    """AC-4 on real SQLite: two to_thread settlements, as /api/m4_5/grant_xp runs them."""
    from services.m6_5_acid_gatekeeper.gatekeeper import XPGatekeeper
    from services.main import LiveXPStore

    seg_id = live_db.add_segment()

    async def run_both():
        return await asyncio.gather(*[
            asyncio.to_thread(
                XPGatekeeper(LiveXPStore(live_db.adapter)).settle_segment_xp,
                seg_id, live_db.user_id, 20,
            )
            for _ in range(2)
        ])

    results = asyncio.run(run_both())
    assert sorted(r.success for r in results) == [False, True]
    assert _state(live_db, seg_id) == (120, 320, 1, [20])


def test_live_db_guard_stops_settlement_that_passed_python_check(live_db):
    """[SPEC §9 anti-pattern 2] The conditional UPDATE alone blocks a double award.

    Request A reads xp_settled = 0 and passes the Python check; before A writes,
    request B (another process in production) settles the same segment. A's
    commit must write nothing.
    """
    from services.m6_5_acid_gatekeeper.gatekeeper import XPGatekeeper
    from services.main import LiveXPStore

    seg_id = live_db.add_segment()
    store_a = LiveXPStore(live_db.adapter)
    real_get = store_a.users.get
    b_results = []

    def get_after_b_settles(uid):
        # A has already passed its xp_settled check at this point.
        store_b = LiveXPStore(live_db.adapter)
        b_results.append(XPGatekeeper(store_b).settle_segment_xp(seg_id, live_db.user_id, 20))
        return real_get(uid)

    store_a.users.get = get_after_b_settles
    result_a = XPGatekeeper(store_a).settle_segment_xp(seg_id, live_db.user_id, 20)

    assert b_results[0].success is True
    assert result_a.success is False
    assert result_a.error_code == "GATEKEEPER_002"
    assert _state(live_db, seg_id) == (120, 320, 1, [20])


def test_grant_badge_concurrent_calls_award_once(live_db, monkeypatch):
    """/api/m6_5/grant_badge: concurrent calls for one segment award XP once."""
    import services.main as main_mod

    seg_id = live_db.add_segment()
    monkeypatch.setattr(main_mod, "_db_adapter", live_db.adapter)
    request = SimpleNamespace(state=SimpleNamespace(user_id=str(live_db.user_id)))
    body = {"reflection_id": str(seg_id), "amount": 20}

    async def run_both():
        return await asyncio.gather(
            main_mod.m6_5_grant_badge(request, body),
            main_mod.m6_5_grant_badge(request, body),
        )

    results = asyncio.run(run_both())
    assert sorted(r["granted"] for r in results) == [False, True]
    assert any("GATEKEEPER_002" in r.get("reason", "") for r in results)
    assert _state(live_db, seg_id) == (120, 320, 1, [20])


def test_grant_badge_rejects_draft(live_db, monkeypatch):
    """/api/m6_5/grant_badge keeps the RISK-01 gate: a draft segment is refused."""
    import services.main as main_mod

    seg_id = live_db.add_segment(is_draft=1, is_reviewed=0)
    monkeypatch.setattr(main_mod, "_db_adapter", live_db.adapter)
    request = SimpleNamespace(state=SimpleNamespace(user_id=str(live_db.user_id)))

    result = asyncio.run(main_mod.m6_5_grant_badge(request, {"reflection_id": str(seg_id)}))
    assert result["granted"] is False
    assert result["reason"].startswith("GATEKEEPER_001")
    assert _state(live_db, seg_id) == (100, 300, 0, [])
