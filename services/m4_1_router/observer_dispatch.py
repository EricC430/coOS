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
    占位實作：實際萃取邏輯由 M4.6 提供。
    [RISK-12] 輸出預設 visibility='private'，不觸發上雲。
    """
    logger.debug("[M4.1.3] Observer task dispatched: thread=%s targets=%s",
                 task.thread_id, task.extract_targets)
    # M4.6 實作後替換此處


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
