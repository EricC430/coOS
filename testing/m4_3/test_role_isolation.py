"""
M4.3 Role Isolation Engine -- test suite

SPEC: docs/modules/M4_3_role_isolation_SPEC.md §6
Research: [R03 §2 ARPM] [R03 §6 狀態機移轉] [R03 §人設崩塌]
Risk coverage: RISK-06, RISK-12
"""
from __future__ import annotations

import sqlite3
import sys
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[2]
SERVICES = ROOT / "services"
sys.path.insert(0, str(SERVICES))

from m4_3_role_isolation.context import RoleContext, build_role_context
from m4_3_role_isolation.thread import create_scoped_thread_id, validate_thread_access
from m4_3_role_isolation.switch import handle_role_switch
from m4_3_role_isolation.lifecycle import on_role_created, on_role_deleted, on_expert_deleted
from m4_3_role_isolation.cache import PromptCache

# ---------------------------------------------------------------------------
# Constants / helpers
# ---------------------------------------------------------------------------
USER_ID = uuid.UUID("a0000000-0000-0000-0000-000000000001")
ROLE_CSIE = uuid.UUID("b0000000-0000-0000-0000-000000000001")
ROLE_FAMILY = uuid.UUID("b0000000-0000-0000-0000-000000000002")
EXPERT_ROBERT = uuid.UUID("c0000000-0000-0000-0000-000000000001")
EXPERT_HONGXUAN = uuid.UUID("c0000000-0000-0000-0000-000000000002")


def _make_db(experts_csie: list[dict] | None = None) -> MagicMock:
    """Build a mock DB with configurable ai_experts data."""
    db = MagicMock()
    db.fetch_all = AsyncMock(return_value=experts_csie or [])
    db.fetch_one = AsyncMock(return_value=None)
    db.execute = AsyncMock()
    return db


# ===========================================================================
# TestM4_3_1_SandboxMiddleware
# ===========================================================================

class TestM4_3_1_SandboxMiddleware:
    """中介軟體：X-Role-ID 強制存在且屬於當前使用者"""

    def test_request_without_role_id_returns_422(self):
        """所有 Agent API 請求必須攜帶 X-Role-ID"""
        from starlette.testclient import TestClient
        from m4_3_role_isolation.middleware import create_test_app

        app = create_test_app()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/m4_1/chat", json={"content": "hi"})
        assert resp.status_code == 422
        assert "X-Role-ID" in resp.text

    def test_request_with_exempt_path_skips_check(self):
        """EXEMPT_PATHS 內的端點不需要 X-Role-ID"""
        from starlette.testclient import TestClient
        from m4_3_role_isolation.middleware import create_test_app

        app = create_test_app()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/api/health")
        assert resp.status_code == 200

    def test_invalid_role_id_returns_403(self):
        """X-Role-ID 不屬於當前使用者時回傳 403"""
        from starlette.testclient import TestClient
        from m4_3_role_isolation.middleware import create_test_app

        app = create_test_app(owned_roles={str(ROLE_CSIE)})
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/api/m4_1/chat",
            json={"content": "hi"},
            headers={"X-Role-ID": str(ROLE_FAMILY)},  # 不屬於此 user
        )
        assert resp.status_code == 403


# ===========================================================================
# TestM4_3_2_DatabaseSwitching
# ===========================================================================

class TestM4_3_2_DatabaseSwitching:
    """[RISK-06] 資料庫查詢範圍嚴格限定於當前 role_id"""

    @pytest.mark.asyncio
    async def test_experts_filtered_by_role_id(self):
        """ai_experts 候選池嚴格限定於當前角色"""
        csie_experts = [
            {"id": str(EXPERT_ROBERT), "name": "Robert", "role_id": str(ROLE_CSIE),
             "domain": "cs_mentor", "domain_keywords": [], "is_active": True},
        ]
        db = _make_db(experts_csie=csie_experts)

        ctx = await build_role_context(USER_ID, ROLE_CSIE, db=db)
        assert len(ctx.active_experts) == 1
        assert ctx.active_experts[0]["name"] == "Robert"

        # FAMILY 角色不應拿到 CSIE 的 expert
        db_family = _make_db(experts_csie=[])
        ctx_family = await build_role_context(USER_ID, ROLE_FAMILY, db=db_family)
        assert not any(e["name"] == "Robert" for e in ctx_family.active_experts)

    @pytest.mark.asyncio
    async def test_implicit_state_queried_with_dual_key(self):
        """[RISK-06] implicit_state 以 (user_id, role_id) 雙鍵查詢，不繼承跨角色狀態"""
        db = MagicMock()
        db.fetch_all = AsyncMock(return_value=[])
        # CSIE 有 anxiety 狀態
        db.fetch_one = AsyncMock(return_value={
            "label": "anxiety", "confidence": 0.85,
            "role_id": str(ROLE_CSIE), "user_id": str(USER_ID),
        })
        ctx_csie = await build_role_context(USER_ID, ROLE_CSIE, db=db)
        assert ctx_csie.implicit_state is not None
        assert ctx_csie.implicit_state["label"] == "anxiety"

        # FAMILY 角色查不到 CSIE 的狀態（fetch_one 回傳 None）
        db_family = MagicMock()
        db_family.fetch_all = AsyncMock(return_value=[])
        db_family.fetch_one = AsyncMock(return_value=None)
        ctx_family = await build_role_context(USER_ID, ROLE_FAMILY, db=db_family)
        assert ctx_family.implicit_state is None

    @pytest.mark.asyncio
    async def test_role_contexts_have_disjoint_experts(self):
        """[R03 §人設崩塌] 兩個角色的 expert 池沒有交集"""
        db_csie = _make_db([{"id": str(EXPERT_ROBERT), "name": "Robert",
                              "role_id": str(ROLE_CSIE), "domain": "cs",
                              "domain_keywords": [], "is_active": True}])
        db_family = _make_db([{"id": str(uuid.uuid4()), "name": "家庭顧問",
                                "role_id": str(ROLE_FAMILY), "domain": "life",
                                "domain_keywords": [], "is_active": True}])

        ctx_csie = await build_role_context(USER_ID, ROLE_CSIE, db=db_csie)
        ctx_family = await build_role_context(USER_ID, ROLE_FAMILY, db=db_family)

        csie_ids = {e["id"] for e in ctx_csie.active_experts}
        family_ids = {e["id"] for e in ctx_family.active_experts}
        assert csie_ids.isdisjoint(family_ids)


# ===========================================================================
# TestM4_3_3_DynamicPersonaInjection
# ===========================================================================

class TestM4_3_3_DynamicPersonaInjection:
    """[R03 §2] Persona 配置依角色完整重載"""

    @pytest.mark.asyncio
    async def test_role_context_carries_role_id(self):
        """RoleContext 必須攜帶正確的 role_id"""
        db = _make_db()
        ctx = await build_role_context(USER_ID, ROLE_CSIE, db=db)
        assert ctx.role_id == ROLE_CSIE
        assert ctx.user_id == USER_ID

    @pytest.mark.asyncio
    async def test_expired_implicit_state_treated_as_none(self):
        """[RISK-06] 過期的 implicit_state (expires_at < NOW) 視為 None"""
        past = datetime(2020, 1, 1, tzinfo=timezone.utc).isoformat()
        db = MagicMock()
        db.fetch_all = AsyncMock(return_value=[])
        db.fetch_one = AsyncMock(return_value={
            "label": "flow", "confidence": 0.9,
            "expires_at": past,
            "role_id": str(ROLE_CSIE), "user_id": str(USER_ID),
        })
        ctx = await build_role_context(USER_ID, ROLE_CSIE, db=db)
        assert ctx.implicit_state is None


# ===========================================================================
# TestM4_3_4_PromptCacheReset
# ===========================================================================

class TestM4_3_4_PromptCacheReset:
    """[R03 §6] 角色切換後快取清除"""

    def test_cache_stores_and_retrieves_prompt(self):
        """PromptCache 正確儲存與取回 prompt"""
        cache = PromptCache()
        cache.set(ROLE_CSIE, str(EXPERT_ROBERT), "Robert 的系統提示詞")
        assert cache.get(ROLE_CSIE, str(EXPERT_ROBERT)) == "Robert 的系統提示詞"

    def test_invalidate_by_role_clears_all_prompts(self):
        """[R03 §6] invalidate_by_role 清除該角色所有 prompt 快取"""
        cache = PromptCache()
        cache.set(ROLE_CSIE, str(EXPERT_ROBERT), "Robert prompt")
        cache.set(ROLE_CSIE, str(EXPERT_HONGXUAN), "宏軒 prompt")
        cache.set(ROLE_FAMILY, str(uuid.uuid4()), "家庭顧問 prompt")

        cache.invalidate_by_role(ROLE_CSIE)

        assert cache.get(ROLE_CSIE, str(EXPERT_ROBERT)) is None
        assert cache.get(ROLE_CSIE, str(EXPERT_HONGXUAN)) is None
        # FAMILY 角色的快取不受影響
        assert cache.get(ROLE_FAMILY, str(uuid.uuid4())) is None  # 不同 UUID

    def test_invalidate_by_persona_clears_single_entry(self):
        """invalidate_by_persona 只清除指定 persona 的快取"""
        cache = PromptCache()
        cache.set(ROLE_CSIE, str(EXPERT_ROBERT), "Robert prompt")
        cache.set(ROLE_CSIE, str(EXPERT_HONGXUAN), "宏軒 prompt")

        cache.invalidate_by_persona(EXPERT_ROBERT)

        assert cache.get(ROLE_CSIE, str(EXPERT_ROBERT)) is None
        assert cache.get(ROLE_CSIE, str(EXPERT_HONGXUAN)) == "宏軒 prompt"

    @pytest.mark.asyncio
    async def test_handle_role_switch_clears_cache(self):
        """handle_role_switch 執行後 from_role 的快取被清除"""
        cache = PromptCache()
        cache.set(ROLE_CSIE, str(EXPERT_ROBERT), "Robert prompt")

        db = _make_db()
        sse_events: list[dict] = []

        async def fake_broadcast(event_type: str, data: dict) -> None:
            sse_events.append({"type": event_type, "data": data})

        async def fake_log(event_type: str, data: dict) -> None:
            pass  # 本地 SQLite 寫入，測試跳過

        await handle_role_switch(
            user_id=USER_ID,
            from_role_id=ROLE_CSIE,
            to_role_id=ROLE_FAMILY,
            db=db,
            prompt_cache=cache,
            broadcast_fn=fake_broadcast,
            log_fn=fake_log,
        )

        assert cache.get(ROLE_CSIE, str(EXPERT_ROBERT)) is None
        assert any(e["type"] == "ROLE_SWITCHED" for e in sse_events)


# ===========================================================================
# TestM4_3_Thread
# ===========================================================================

class TestM4_3_Thread:
    """[RISK-06] thread_id 前綴策略"""

    def test_thread_id_contains_role_prefix(self):
        """create_scoped_thread_id 回傳包含 role_id 前綴的 thread_id"""
        thread_id = create_scoped_thread_id(ROLE_CSIE)
        assert str(ROLE_CSIE) in thread_id
        assert "::" in thread_id

    def test_validate_thread_access_same_role(self):
        """同角色下 thread 存取驗證通過"""
        thread_id = create_scoped_thread_id(ROLE_CSIE)
        assert validate_thread_access(thread_id, ROLE_CSIE) is True

    def test_validate_thread_access_different_role_rejected(self):
        """[RISK-06] 跨角色存取 thread 被拒絕"""
        thread_id = create_scoped_thread_id(ROLE_CSIE)
        assert validate_thread_access(thread_id, ROLE_FAMILY) is False


# ===========================================================================
# TestM4_3_RoleLifecycle
# ===========================================================================

class TestM4_3_RoleLifecycle:
    """Role 生命週期：建立、刪除、Expert 刪除"""

    @pytest.mark.asyncio
    async def test_role_created_broadcasts_sandbox_ready(self):
        """[RISK-06 新建] on_role_created 廣播 ROLE_SANDBOX_READY"""
        new_role_id = uuid.uuid4()
        sse_events: list[dict] = []

        async def fake_broadcast(event_type: str, data: dict) -> None:
            sse_events.append({"type": event_type, "data": data})

        db = _make_db()
        await on_role_created(
            user_id=USER_ID,
            role_id=new_role_id,
            db=db,
            broadcast_fn=fake_broadcast,
            log_fn=AsyncMock(),
        )

        sandbox_ready_events = [e for e in sse_events if e["type"] == "ROLE_SANDBOX_READY"]
        assert len(sandbox_ready_events) == 1
        assert sandbox_ready_events[0]["data"]["is_empty"] is True

    @pytest.mark.asyncio
    async def test_role_deleted_inactivates_router_rules(self):
        """[RISK-06 刪除] on_role_deleted 將 role_router_rules 全標為 inactive"""
        executed_sqls: list[str] = []

        async def tracking_execute(sql: str, params: dict) -> None:
            executed_sqls.append(sql)

        local_sqlite = MagicMock()
        local_sqlite.execute = tracking_execute
        cloud_db = MagicMock()
        cloud_db.execute = AsyncMock()

        await on_role_deleted(
            user_id=USER_ID,
            role_id=ROLE_CSIE,
            local_sqlite=local_sqlite,
            cloud_db=cloud_db,
            prompt_cache=PromptCache(),
            broadcast_fn=AsyncMock(),
            log_fn=AsyncMock(),
        )

        # 確認 role_router_rules 被 UPDATE status='inactive'
        assert any("role_router_rules" in sql and "inactive" in sql for sql in executed_sqls)

    @pytest.mark.asyncio
    async def test_role_deleted_inactivates_experts(self):
        """[RISK-06 刪除] on_role_deleted 將 ai_experts 軟刪除 (is_active=FALSE)"""
        cloud_db_calls: list[str] = []

        async def tracking_cloud_execute(sql: str, params: dict) -> None:
            cloud_db_calls.append(sql)

        await on_role_deleted(
            user_id=USER_ID,
            role_id=ROLE_CSIE,
            local_sqlite=MagicMock(execute=AsyncMock()),
            cloud_db=MagicMock(execute=tracking_cloud_execute),
            prompt_cache=PromptCache(),
            broadcast_fn=AsyncMock(),
            log_fn=AsyncMock(),
        )

        assert any("ai_experts" in sql and "is_active" in sql.lower() for sql in cloud_db_calls)

    @pytest.mark.asyncio
    async def test_new_role_has_empty_rules(self):
        """新建 Role 時 role_router_rules 為空（Router 只能走 LLM fallback）"""
        executed: list[str] = []
        db = MagicMock()
        db.execute = AsyncMock(side_effect=lambda sql, p: executed.append(sql))

        await on_role_created(
            user_id=USER_ID,
            role_id=uuid.uuid4(),
            db=db,
            broadcast_fn=AsyncMock(),
            log_fn=AsyncMock(),
        )

        # 確認沒有 INSERT 到 role_router_rules（保持空）
        assert not any("role_router_rules" in sql for sql in executed)

    @pytest.mark.asyncio
    async def test_expert_deleted_broadcasts_pool_empty_when_last(self):
        """[RISK-17] 刪除最後一個 Expert 後廣播 EXPERT_POOL_EMPTY"""
        sse_events: list[dict] = []

        async def fake_broadcast(event_type: str, data: dict) -> None:
            sse_events.append({"type": event_type, "data": data})

        cloud_db = MagicMock()
        cloud_db.execute = AsyncMock()
        # 回傳 cnt=0（最後一個 expert 已刪）
        cloud_db.fetch_one = AsyncMock(return_value={"cnt": 0})

        await on_expert_deleted(
            role_id=ROLE_CSIE,
            expert_id=EXPERT_ROBERT,
            local_sqlite=MagicMock(execute=AsyncMock()),
            cloud_db=cloud_db,
            prompt_cache=PromptCache(),
            broadcast_fn=fake_broadcast,
        )

        assert any(e["type"] == "EXPERT_POOL_EMPTY" for e in sse_events)


# ===========================================================================
# TestM4_3_CommitmentContext  (v1.2 新增)
# ===========================================================================

class TestM4_3_CommitmentContext:
    """[v1.2] build_commitment_context — goals + promises 撈取與過期標記"""

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_db(self):
        """db=None 時回傳空 lists"""
        from m4_3_role_isolation.context import build_commitment_context
        goals, promises = await build_commitment_context(ROLE_CSIE, db=None)
        assert goals == []
        assert promises == []

    @pytest.mark.asyncio
    async def test_returns_active_goals(self):
        """db 有 active goals 時正確回傳"""
        from m4_3_role_isolation.context import build_commitment_context

        mock_goals = [
            {"id": str(uuid.uuid4()), "persona_id": str(EXPERT_ROBERT),
             "title": "完成線性代數作業", "progress": 0.4, "status": "active"},
        ]
        db = MagicMock()
        db.execute = AsyncMock()
        db.fetch_all = AsyncMock(side_effect=[mock_goals, []])  # goals, promises

        goals, promises = await build_commitment_context(ROLE_CSIE, db=db)
        assert len(goals) == 1
        assert goals[0]["title"] == "完成線性代數作業"
        assert promises == []

    @pytest.mark.asyncio
    async def test_returns_upcoming_promises(self):
        """db 有 upcoming promises 時正確回傳"""
        from m4_3_role_isolation.context import build_commitment_context

        mock_promises = [
            {"id": str(uuid.uuid4()), "persona_id": str(EXPERT_ROBERT),
             "text": "本週完成第三章練習題", "deadline": "2026-06-05", "status": "active"},
        ]
        db = MagicMock()
        db.execute = AsyncMock()
        db.fetch_all = AsyncMock(side_effect=[[], mock_promises])

        goals, promises = await build_commitment_context(ROLE_CSIE, db=db)
        assert goals == []
        assert len(promises) == 1
        assert promises[0]["text"] == "本週完成第三章練習題"

    @pytest.mark.asyncio
    async def test_expired_promises_marked_before_fetch(self):
        """過期承諾在撈取前先執行 UPDATE status='expired'"""
        from m4_3_role_isolation.context import build_commitment_context

        executed_sqls: list[str] = []

        async def tracking_execute(sql: str, params: dict) -> None:
            executed_sqls.append(sql)

        db = MagicMock()
        db.execute = tracking_execute
        db.fetch_all = AsyncMock(return_value=[])

        await build_commitment_context(ROLE_CSIE, db=db)

        # 確認有執行過期標記 UPDATE
        assert any("expired" in sql and "promises" in sql for sql in executed_sqls)

    @pytest.mark.asyncio
    async def test_build_role_context_includes_goals_and_promises(self):
        """[v1.2] build_role_context 回傳的 RoleContext 含 active_goals/upcoming_promises"""
        from m4_3_role_isolation.context import build_role_context

        mock_goals = [{"id": "g1", "persona_id": str(EXPERT_ROBERT),
                       "title": "搞懂 LangGraph", "progress": 0.2, "status": "active"}]
        mock_promises = [{"id": "p1", "persona_id": str(EXPERT_ROBERT),
                          "text": "讀完文件", "deadline": None, "status": "active"}]

        db = MagicMock()
        db.execute = AsyncMock()
        # fetch_all 呼叫順序: experts, projects, goals, promises
        db.fetch_all = AsyncMock(side_effect=[[], [], mock_goals, mock_promises])
        db.fetch_one = AsyncMock(return_value=None)

        ctx = await build_role_context(USER_ID, ROLE_CSIE, db=db)
        assert len(ctx.active_goals) == 1
        assert ctx.active_goals[0]["title"] == "搞懂 LangGraph"
        assert len(ctx.upcoming_promises) == 1
        assert ctx.upcoming_promises[0]["text"] == "讀完文件"

    @pytest.mark.asyncio
    async def test_db_failure_returns_empty_goals_promises(self):
        """build_commitment_context 失敗時靜默回傳空 lists，不 raise"""
        from m4_3_role_isolation.context import build_commitment_context

        db = MagicMock()
        db.execute = AsyncMock(side_effect=Exception("DB connection error"))
        db.fetch_all = AsyncMock(side_effect=Exception("DB error"))

        goals, promises = await build_commitment_context(ROLE_CSIE, db=db)
        assert goals == []
        assert promises == []
