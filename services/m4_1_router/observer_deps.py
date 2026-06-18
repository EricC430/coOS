"""
M4.1.3 -- Observer 相依解析 (Dependency Resolver)

實作 SPEC: docs/modules/M4_1_agent_router_SPEC.md §7.4 (容器派發)

把 M4.6 Observer 所需的 db / eguard / sse 從 sidecar 環境組裝出來，與派發邏輯解耦。
若任一相依尚未就緒（例如尚未注入 DB session 的測試環境），回傳 None，
派發層據此靜默跳過 —— Observer 是背景萃取，缺相依時不得阻塞或汙染主對話流。

production 接線時把 _resolve_db / _resolve_sse 換成真實 session 與 SSE broker。
"""
from __future__ import annotations

import asyncio
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
        import main as _main  # services/ is on sys.path; 'main' resolves to services/main.py
        _eguard = getattr(_main, "_eguard_filter", None)
        if _eguard is None:
            from m2_3_eguard.filter import EguardFilter
            _eguard = EguardFilter()

        class _EguardAdapter:
            def __init__(self, f) -> None:
                self._f = f

            def mask_pii(self, text: str, role_id: str = "") -> Any:
                return self._f.mask_pii(text, role_id=role_id)

            def filter_pii(self, text: str) -> str:
                return self._f.mask_pii(text).sanitized_text

        return _EguardAdapter(_eguard)
    except Exception as e:
        logger.warning("[M4.1.3] Eguard unavailable for observer: %s", e)
        return None


def _resolve_db(role_id: str) -> Any | None:  # noqa: ARG001
    """真實 DB 介面，包裝 M4.6 所需的特定方法。"""
    try:
        import main as _main  # services/ is on sys.path
        _db_adapter = getattr(_main, "_db_adapter", None)
    except Exception as e:
        logger.warning("[M4.1.3] DB unavailable for observer: %s", e)
        return None

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
    """[GAP-C1] 連接真實 _sse_broadcast，將 Observer 事件廣播至前端 SSE 訂閱者。"""
    try:
        import main as _main
        _broadcast = getattr(_main, "_sse_broadcast", None)
        if _broadcast is None:
            logger.warning("[M4.1.3] _sse_broadcast not found; SSE events will be dropped")
            return None

        class _SSEAdapter:
            def __init__(self, broadcast_fn):
                self._broadcast = broadcast_fn

            async def emit(self, event_type: str, data: dict):
                try:
                    await self._broadcast({"type": event_type, **data})
                except Exception as e:
                    logger.warning("[M4.1.3] SSE emit failed: %s", e)

        return _SSEAdapter(_broadcast)
    except Exception as e:
        logger.warning("[M4.1.3] SSE resolver failed: %s", e)
        return None


def _resolve_gemma(role_id: str) -> Any | None:
    """[M2.2] Gemma 邊緣推論介面。"""
    try:
        import main as _main  # services/ is on sys.path
        _gemma_pipeline = getattr(_main, "_gemma_pipeline", None)
        if _gemma_pipeline is None:
            return None

        class _GemmaAdapter:
            def __init__(self, p):
                self._p = p

            async def generate_json(self, prompt: str):
                import httpx
                import json
                import time
                from m0_4_logging.writer import get_logger as get_log_writer

                log_writer = get_log_writer()
                url = f"{self._p._client._base_url.rstrip('/')}/api/generate"
                payload = {
                    "model": self._p._client._model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"
                }

                async def _run_request():
                    t_start = time.monotonic()
                    status = "success"
                    error_msg = None
                    content = ""
                    try:
                        async with httpx.AsyncClient(timeout=15.0) as client:
                            resp = await client.post(url, json=payload)
                            resp.raise_for_status()
                            data = resp.json()
                            content = data.get("response", "{}").strip()
                            if content.startswith("```"):
                                lines = content.split("\n")
                                content = "\n".join(lines[1:-1]) if len(lines) > 2 else content
                            return json.loads(content)
                    except Exception as e:
                        status = "failed"
                        error_msg = str(e)
                        logger.warning("[M4.1.3] Gemma generate_json failed: %s", e)
                        return {}
                    finally:
                        latency_ms = int((time.monotonic() - t_start) * 1000)
                        asyncio.ensure_future(
                            log_writer.emit_llm_log(
                                model_name=self._p._client._model,
                                caller_module="M4.1",
                                prompt_text=prompt,
                                response_text=content,
                                prompt_tokens=None,
                                completion_tokens=None,
                                latency_ms=latency_ms,
                                temperature=None,
                                status=status,
                                error_message=error_msg,
                                role_id=role_id,
                            )
                        )

                from m2_2_gemma.queue import enqueue_inference
                return await enqueue_inference(priority=2, fn=_run_request, tag="observer_generate_json")

            async def generate_text(self, prompt: str) -> str:
                import httpx
                import time
                from m0_4_logging.writer import get_logger as get_log_writer

                log_writer = get_log_writer()
                url = f"{self._p._client._base_url.rstrip('/')}/api/generate"
                payload = {
                    "model": self._p._client._model,
                    "prompt": prompt,
                    "stream": False,
                }

                async def _run_request() -> str:
                    t_start = time.monotonic()
                    status = "success"
                    error_msg = None
                    content = ""
                    try:
                        async with httpx.AsyncClient(timeout=15.0) as client:
                            resp = await client.post(url, json=payload)
                            resp.raise_for_status()
                            data = resp.json()
                            content = data.get("response", "").strip()
                            return content
                    except Exception as e:
                        status = "failed"
                        error_msg = str(e)
                        logger.warning("[M4.1.3] Gemma generate_text failed: %s", e)
                        return ""
                    finally:
                        latency_ms = int((time.monotonic() - t_start) * 1000)
                        asyncio.ensure_future(
                            log_writer.emit_llm_log(
                                model_name=self._p._client._model,
                                caller_module="M4.1",
                                prompt_text=prompt,
                                response_text=content,
                                prompt_tokens=None,
                                completion_tokens=None,
                                latency_ms=latency_ms,
                                temperature=None,
                                status=status,
                                error_message=error_msg,
                                role_id=role_id,
                            )
                        )

                from m2_2_gemma.queue import enqueue_inference
                return await enqueue_inference(priority=2, fn=_run_request, tag="observer_generate_text")

        return _GemmaAdapter(_gemma_pipeline)
    except Exception:
        return None


def resolve_observer_deps(role_id: str) -> ObserverDeps | None:
    """組裝 Observer 相依。"""
    db = _resolve_db(role_id)
    eguard = _resolve_eguard()
    sse = _resolve_sse()
    gemma = _resolve_gemma(role_id)
    # PII filter and DB are required
    if db is None or eguard is None:
        return None
    return ObserverDeps(db=db, eguard=eguard, sse=sse, gemma=gemma)
