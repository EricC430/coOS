"""
MVP closed-loop integration test (MVP_CLOSURE_REPORT §7.1 W3 / LOOP-01)

chat_transcripts -> M2.2.2 ChatCompressor (chat_digest) -> M4.4.3 run_draft_cron
-> PATCH /api/m6_4/reflections (user approval) -> PATCH /api/m4_5/grant_xp
-> xp_ledger +1 exactly once.

Risks covered:
  RISK-01 drafts are never auto-approved; XP only after user approval
  RISK-14 current_xp and lifetime_xp move together
  RISK-15 chat L1 plaintext stays local; only a chat_digest row is derived
Research:
  [R08: 微摩擦力 §四.2] both subjective fields are mandatory before XP
  [R08 §六.1] IKEA effect -- the user's own approval is what earns XP

Isolation (TEST-02): every write goes to a tmp_path SQLite file. main._db_adapter
and settings.local_db_path are monkeypatched; the lifespan never runs (TestClient
is not used as a context manager). The test asserts data/coos.db and
services/coOS_local.db are byte-for-byte untouched (mtime + size).

External dependencies: the iPad Gemma edge (ChatCompressor) is forced offline so
the rule-based fallback runs; the Gibbs card builder gets no ai.local host and no
Gemini key, so it uses its deterministic template. No sidecar, no cloud.
"""
import re
import sqlite3
import uuid
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SERVICES_DIR = PROJECT_ROOT / "services"
REAL_DBS = [PROJECT_ROOT / "data" / "coos.db", SERVICES_DIR / "coOS_local.db"]

TARGET_DAY = date(2026, 10, 18)
ROLE_ID = "role_mvp_loop"
THREAD_ID = "thread_mvp_loop"

_RAW_TRACKING_DDL = """
CREATE TABLE IF NOT EXISTS raw_tracking_logs (
    id             TEXT PRIMARY KEY,
    timestamp      TEXT NOT NULL,
    module         TEXT NOT NULL,
    action         TEXT NOT NULL,
    level          TEXT NOT NULL DEFAULT 'INFO',
    payload        TEXT NOT NULL,
    user_id        TEXT,
    role_id        TEXT,
    correlation_id TEXT
)
"""


def _fingerprint(paths):
    return {str(p): (p.stat().st_mtime_ns, p.stat().st_size) for p in paths if p.exists()}


def _local_ddl() -> list[str]:
    """Reuse the lifespan's own CREATE TABLE statements so the schema cannot drift."""
    src = (SERVICES_DIR / "main.py").read_text(encoding="utf-8")
    ddls = re.findall(r'"""\s*(CREATE TABLE IF NOT EXISTS .*?)"""', src, re.S)
    assert ddls, "could not extract local DDL from main.py"
    return ddls + [_RAW_TRACKING_DDL]


@pytest.fixture
def loop_env(tmp_path, monkeypatch):
    real_before = _fingerprint(REAL_DBS)

    import main
    from m2_2_gemma import client as gemma_client
    from m4_4_elicitation import draft_scheduler

    db_path = tmp_path / "coos_loop.db"
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    for ddl in _local_ddl():
        conn.execute(ddl)
    conn.commit()

    monkeypatch.setattr(main.settings, "local_db_path", db_path)
    monkeypatch.setattr(main, "_db_adapter", main.AsyncDBAdapter(conn, None, sqlite_path=str(db_path)))

    async def _edge_offline(*_a, **_kw):
        raise ConnectionError("ai.local offline (test)")

    monkeypatch.setattr(gemma_client.GemmaEdgeClient, "generate", _edge_offline)
    monkeypatch.setattr(draft_scheduler, "_get_ai_local_host", lambda: "")
    monkeypatch.setattr(draft_scheduler, "_get_gemini_key", lambda: "")

    async def _no_sse(_event):
        return None

    monkeypatch.setattr(main, "_sse_broadcast", _no_sse)

    user_id = str(main.get_safe_user_id(SimpleNamespace(state=SimpleNamespace())))
    conn.execute(
        "INSERT INTO users (id, username, current_xp, lifetime_xp) VALUES (?, 'loop', 0, 0)",
        (user_id,),
    )
    conn.execute(
        "INSERT INTO roles (id, user_id, slug, display_name) VALUES (?, ?, 'csie', 'CSIE')",
        (ROLE_ID, user_id),
    )
    day = TARGET_DAY.isoformat()
    # L1 chat transcript (user turn + persona turn) on the target day
    for role, content in [
        ("user", "今天在準備演算法期中考，動態規劃一直卡住，有點焦慮"),
        ("assistant", "先把題目拆成子問題，我們一題一題來。"),
    ]:
        conn.execute(
            "INSERT INTO chat_transcripts (id, thread_id, persona_id, role, content, role_id, created_at) "
            "VALUES (?, ?, 'p1', ?, ?, ?, ?)",
            (str(uuid.uuid4()), THREAD_ID, role, content, ROLE_ID, f"{day}T09:00:00Z"),
        )
    # Telemetry: run_draft_cron only produces drafts from focus sessions
    conn.execute(
        "INSERT INTO raw_tracking_logs (id, timestamp, module, action, payload, user_id, role_id) "
        "VALUES (?, ?, 'M1.1', 'focus_session_ended', ?, ?, ?)",
        (
            str(uuid.uuid4()), f"{day}T10:30:00Z",
            '{"app_bucket": "coding", "app_name": "code.exe", "duration_s": 3600}',
            user_id, ROLE_ID,
        ),
    )
    conn.commit()

    client = TestClient(main.app, headers={"X-Role-ID": ROLE_ID})
    yield SimpleNamespace(conn=conn, client=client, user_id=user_id)

    conn.close()
    assert _fingerprint(REAL_DBS) == real_before, "test touched a real L1 database"


def _user_xp(conn):
    row = conn.execute("SELECT current_xp, lifetime_xp FROM users").fetchone()
    return row["current_xp"], row["lifetime_xp"]


def _ledger_count(conn):
    return conn.execute("SELECT COUNT(*) FROM xp_ledger").fetchone()[0]


@pytest.mark.integration_risk("RISK-01")
def test_chat_to_xp_closed_loop(loop_env):
    conn, client = loop_env.conn, loop_env.client

    # 1-2. Nightly cron (manual trigger) -> compresses the undigested thread + drafts
    resp = client.post(
        "/api/m4_4/trigger_draft_cron", params={"for_date": TARGET_DAY.isoformat()}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["drafted"] >= 1, resp.json()

    digest = conn.execute(
        "SELECT * FROM intent_logs WHERE source_type = 'chat_digest' AND source_log_id = ?",
        (THREAD_ID,),
    ).fetchall()
    assert len(digest) == 1
    assert digest[0]["inference_mode"] == "rule_based_fallback"
    assert digest[0]["role_id"] == ROLE_ID

    seg = conn.execute("SELECT * FROM daily_reflection_segments").fetchone()
    assert seg is not None
    # [RISK-01] draft is never auto-approved and subjective fields stay empty
    assert seg["is_draft"] == 1 and seg["is_reviewed"] == 0
    assert seg["user_feeling"] is None and seg["user_action_plan"] is None
    seg_id = seg["id"]

    # 3. XP before approval -> denied, nothing written
    early = client.patch("/api/m4_5/grant_xp", json={"reflection_id": seg_id})
    assert early.status_code == 200
    assert early.json()["granted"] is False
    assert _ledger_count(conn) == 0 and _user_xp(conn) == (0, 0)

    # 4. User approval exactly as useApprovalGuard.ts sends it
    patch = client.patch(
        f"/api/m6_4/reflections/{seg_id}",
        json={
            "user_feeling": "卡關時很焦慮，拆題後安心一點",
            "user_action_plan": "明天先寫兩題 DP 再看解答",
            "is_draft": False,
            "is_reviewed": True,
        },
    )
    assert patch.status_code == 200, patch.text

    # 5. Settlement -> exactly one ledger row, current & lifetime move together
    first = client.patch("/api/m4_5/grant_xp", json={"reflection_id": seg_id, "is_reviewed": True})
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["granted"] is True, body
    amount = body["amount"]
    assert amount > 0
    assert _ledger_count(conn) == 1
    assert _user_xp(conn) == (amount, amount)  # [RISK-14]
    ledger = conn.execute("SELECT * FROM xp_ledger").fetchone()
    assert ledger["segment_id"] == seg_id
    assert ledger["xp_type"] == "earned"
    assert conn.execute(
        "SELECT xp_settled FROM daily_reflection_segments WHERE id = ?", (seg_id,)
    ).fetchone()[0] == 1

    # 6. Second call -> no double grant
    second = client.patch("/api/m4_5/grant_xp", json={"reflection_id": seg_id})
    assert second.json() == {"granted": False, "reason": "already_settled"}
    assert _ledger_count(conn) == 1
    assert _user_xp(conn) == (amount, amount)


@pytest.mark.integration_risk("RISK-01")
def test_feeling_only_approval_earns_no_xp(loop_env):
    """[R08: 微摩擦力 §四.2] API caller skips the frontend and approves with
    user_feeling only -> grant_xp must refuse (LOOP-03)."""
    conn, client = loop_env.conn, loop_env.client
    resp = client.post(
        "/api/m4_4/trigger_draft_cron", params={"for_date": TARGET_DAY.isoformat()}
    )
    assert resp.json()["drafted"] >= 1
    seg_id = conn.execute("SELECT id FROM daily_reflection_segments").fetchone()[0]

    client.patch(
        f"/api/m6_4/reflections/{seg_id}",
        json={"user_feeling": "還可以", "is_draft": False, "is_reviewed": True},
    )
    for path, payload in [
        ("/api/m4_5/grant_xp", {"reflection_id": seg_id}),
        ("/api/m6_5/grant_badge", {"reflection_id": seg_id}),
    ]:
        call = client.patch if path.endswith("grant_xp") else client.post
        res = call(path, json=payload).json()
        assert res["granted"] is False, (path, res)
        assert "missing_user_action_plan" in res["reason"], (path, res)
    assert _ledger_count(conn) == 0
    assert _user_xp(conn) == (0, 0)

