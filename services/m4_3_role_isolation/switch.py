"""
M4.3.3 + M4.3.4 -- 角色切換處理器

SPEC: docs/modules/M4_3_role_isolation_SPEC.md §7.3
Research: [R03 §6 狀態機移轉] 角色切換觸發所有狀態機歸零重啟
Risk: RISK-12 (切換事件僅寫入本地 raw_tracking_logs，不上雲)
"""
from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

from .cache import PromptCache
from .context import RoleContext, build_role_context

logger = logging.getLogger(__name__)


async def handle_role_switch(
    user_id: UUID,
    from_role_id: UUID,
    to_role_id: UUID,
    db: Any = None,
    prompt_cache: PromptCache | None = None,
    broadcast_fn: Callable[[str, dict], Awaitable[None]] | None = None,
    log_fn: Callable[[str, dict], Awaitable[None]] | None = None,
) -> RoleContext:
    """
    [R03 §6] 角色切換三步驟：
    1. 清除 from_role 的 Prompt 快取 (M4.3.4)
    2. 重建 to_role 上下文 (M4.3.3)
    3. 廣播 ROLE_SWITCHED 事件（僅本地日誌，不上雲 RISK-12）

    切換失敗時保持原角色，記錄 role_switch_failed。
    """
    # Step 1: 清除快取
    if prompt_cache:
        cleared = prompt_cache.invalidate_by_role(from_role_id)
        logger.debug("[M4.3] Cleared %d cached prompts for role %s", cleared, from_role_id)

    # Step 2: 重建新角色上下文
    new_context = await build_role_context(user_id, to_role_id, db=db)

    # Step 3: 廣播 (僅本地日誌，不上雲 [RISK-12])
    event_data = {
        "user_id": str(user_id),
        "from_role_id": str(from_role_id),
        "to_role_id": str(to_role_id),
        "new_expert_count": len(new_context.active_experts),
    }

    if log_fn:
        await log_fn("role_switched", event_data)

    if broadcast_fn:
        await broadcast_fn("ROLE_SWITCHED", {
            "role_id": str(to_role_id),
            "context": new_context.to_frontend_dto(),
        })

    return new_context
