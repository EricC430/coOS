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


async def _run_observer(task: ObserverTask, persona_id: str = "") -> None:
    """
    [M4.6] 實際背景萃取由 M4.6 Observer Agent 執行。
    """
    logger.debug("[M4.1.3] Observer task dispatched: thread=%s targets=%s",
                 task.thread_id, task.extract_targets)
    try:
        from m4_6_observer.agent import run_observer

        from .observer_deps import resolve_observer_deps
        deps = resolve_observer_deps(task.role_id)
        if deps is None:
            return 
        await run_observer(
            user_msg=task.user_msg,
            role_id=task.role_id,
            db=deps.db,
            eguard=deps.eguard,
            sse=deps.sse,
            gemma=deps.gemma,
            thread_id=task.thread_id,
            persona_id=persona_id,
        )
    except Exception as e:
        logger.warning("[M4.1.3] observer run failed silently: %s", e)


async def dispatch_observer(state: dict) -> dict:
    """
    [R10 §代理工作流] Observer 與 Persona 並行，不阻塞對話。
    """
    decision = state.get("route_decision") or {}
    persona_id = decision.get("persona_id", "")
    
    task = ObserverTask(
        thread_id=state.get("thread_id", ""),
        user_msg=state.get("user_message", ""),
        extract_targets=["project", "intent", "time_span"],
        role_id=state.get("role_id", ""),
    )
    asyncio.create_task(_run_observer(task, persona_id=persona_id))
    return state
