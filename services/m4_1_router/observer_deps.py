"""
M4.1.3 -- Observer 相依解析 (Dependency Resolver)

實作 SPEC: docs/modules/M4_1_agent_router_SPEC.md §7.4 (容器派發)

把 M4.6 Observer 所需的 db / eguard / sse 從 sidecar 環境組裝出來，與派發邏輯解耦。
若任一相依尚未就緒（例如尚未注入 DB session 的測試環境），回傳 None，
派發層據此靜默跳過 —— Observer 是背景萃取，缺相依時不得阻塞或汙染主對話流。

production 接線時把 _resolve_db / _resolve_sse 換成真實 session 與 SSE broker。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ObserverDeps:
    db: Any
    eguard: Any
    sse: Any
    gemma: Any


def _resolve_eguard() -> Any | None:
    """[RISK-12] M2.3 Eguard PII 過濾器，包裝為 filter_pii 介面供 M4.6 使用。"""
    try:
        from services.main import _eguard_filter
        if _eguard_filter is None:
            from m2_3_eguard.filter import EguardFilter
            _eguard_filter = EguardFilter()

        class _EguardAdapter:
            def __init__(self, f) -> None:
                self._f = f

            def mask_pii(self, text: str, role_id: str = "") -> Any:
                return self._f.mask_pii(text, role_id=role_id)
                
            def filter_pii(self, text: str) -> str:
                return self._f.mask_pii(text).sanitized_text

        return _EguardAdapter(_eguard_filter)
    except Exception as e:
        logger.warning("[M4.1.3] Eguard unavailable for observer: %s", e)
        return None


def _resolve_db(role_id: str) -> Any | None:
    """真實 DB 介面，包裝 M4.6 所需的特定方法。"""
    from services.main import _db_adapter
    if _db_adapter is None:
        return None
        
    class _DBAdapter:
        def __init__(self, db): self._db = db
        async def fetch_all(self, q, p=None): return await self._db.fetch_all(q, p)
        async def execute(self, q, p=None): await self._db.execute(q, p)
        
        async def insert_goal(self, role_id, persona_id, title, description):
            import uuid
            await self._db.execute(
                "INSERT INTO goals (id, role_id, persona_id, title, description) VALUES (:id, :rid, :pid, :t, :d)",
                {"id": str(uuid.uuid4()), "rid": role_id, "pid": persona_id, "t": title, "d": description}
            )
            
        async def insert_promise(self, role_id, persona_id, source_thread_id, text, deadline):
            import uuid
            await self._db.execute(
                "INSERT INTO promises (id, role_id, persona_id, source_thread_id, text, deadline) "
                "VALUES (:id, :rid, :pid, :tid, :t, :d)",
                {"id": str(uuid.uuid4()), "rid": role_id, "pid": persona_id, "tid": source_thread_id, "t": text, "d": deadline}
            )
            
    return _DBAdapter(_db_adapter)


def _resolve_sse() -> Any | None:
    """真實 SSE broker 尚未在此層接線；MVP 回傳一個 dummy 以通過 deps 檢查。"""
    class _DummySSE:
        async def emit(self, event_type, data):
            logger.debug("[M4.1.3] SSE emit (mock): %s %s", event_type, data)
    return _DummySSE()


def _resolve_gemma() -> Any | None:
    """[M2.2] Gemma 邊緣推論介面。"""
    try:
        from services.main import _gemma_pipeline
        if _gemma_pipeline is None:
            return None
            
        class _GemmaAdapter:
            def __init__(self, p): self._p = p
            async def generate_json(self, prompt):
                return await self._p.client.generate_json(prompt)
            async def generate_text(self, prompt):
                return await self._p.client.generate_text(prompt)
                
        return _GemmaAdapter(_gemma_pipeline)
    except Exception:
        return None


def resolve_observer_deps(role_id: str) -> ObserverDeps | None:
    """組裝 Observer 相依。"""
    db = _resolve_db(role_id)
    eguard = _resolve_eguard()
    sse = _resolve_sse()
    gemma = _resolve_gemma()
    # PII filter and DB are required
    if db is None or eguard is None:
        return None
    return ObserverDeps(db=db, eguard=eguard, sse=sse, gemma=gemma)
