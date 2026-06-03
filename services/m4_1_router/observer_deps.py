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


def _resolve_eguard() -> Any | None:
    """[RISK-12] M2.3 Eguard PII 過濾器，包裝為 filter_pii 介面供 M4.6 使用。"""
    try:
        from m2_3_eguard.filter import EguardFilter

        class _EguardAdapter:
            def __init__(self) -> None:
                self._f = EguardFilter()

            def filter_pii(self, text: str) -> str:
                return self._f.mask_pii(text).sanitized_text

        return _EguardAdapter()
    except Exception as e:  # pragma: no cover - defensive
        logger.warning("[M4.1.3] Eguard unavailable for observer: %s", e)
        return None


def _resolve_db(role_id: str) -> Any | None:
    """
    真實 DB 介面（role_projects upsert / promises / goals）尚未在 sidecar 接線。
    MVP 階段回傳 None -> 派發層靜默跳過萃取持久化。
    """
    return None


def _resolve_sse() -> Any | None:
    """真實 SSE broker 尚未在此層接線；MVP 回傳 None。"""
    return None


def resolve_observer_deps(role_id: str) -> ObserverDeps | None:
    """組裝 Observer 相依；任一缺失即回傳 None（派發層靜默跳過）。"""
    db = _resolve_db(role_id)
    eguard = _resolve_eguard()
    sse = _resolve_sse()
    if db is None or eguard is None or sse is None:
        return None
    return ObserverDeps(db=db, eguard=eguard, sse=sse)
