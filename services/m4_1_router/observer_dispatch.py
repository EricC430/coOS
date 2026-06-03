"""
M4.1.3 -- Observer/Drafting 容器派發

SPEC: docs/modules/M4_1_agent_router_SPEC.md §7.4
Research: [R10: §代理工作流狀態機]
Note: 具體萃取邏輯在 M4.6，此處只負責容器啟動與任務派發。
Risk: RISK-12 (Observer 輸出預設 private + 二次 Eguard)
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ObserverTask:
    thread_id: str
    user_msg: str
    extract_targets: list[str]
    role_id: str
    visibility: str = "private"  # [RISK-12] 預設 private


async def _run_observer(task: ObserverTask) -> None:
    """
    [M4.6] 實際背景萃取由 M4.6 Observer Agent 執行。

    [RISK-12] M4.6 內部對萃取結果做 Eguard 過濾，自動成就預設 visibility='private'。
    本派發層維持「並行、不阻塞、靜默失敗」契約：任何萃取/相依不可用都不得拋出，
    以免汙染主對話流（SPEC M4.1 §8 反模式 / M4.6 §7.7）。
    """
    logger.debug("[M4.1.3] Observer task dispatched: thread=%s targets=%s",
                 task.thread_id, task.extract_targets)
    try:
        from m4_6_observer.agent import run_observer

        from .observer_deps import resolve_observer_deps
        deps = resolve_observer_deps(task.role_id)
        if deps is None:
            return  # 相依未就緒（如測試環境無 DB）-> 靜默跳過
        await run_observer(
            user_msg=task.user_msg,
            role_id=task.role_id,
            db=deps.db,
            eguard=deps.eguard,
            sse=deps.sse,
        )
    except Exception as e:  # 任何失敗都不得阻塞主對話
        logger.warning("[M4.1.3] observer run failed silently: %s", e)


async def dispatch_observer(state: dict) -> dict:
    """
    [R10 §代理工作流] Observer 與 Persona 並行，不阻塞對話。
    """
    task = ObserverTask(
        thread_id=state.get("thread_id", ""),
        user_msg=state.get("user_message", ""),
        extract_targets=["project", "intent", "time_span"],
        role_id=state.get("role_id", ""),
    )
    asyncio.create_task(_run_observer(task))
    return state
