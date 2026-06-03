"""
M4.3 Role 生命週期處理器 (v1.1 新增)

SPEC: docs/modules/M4_3_role_isolation_SPEC.md §7.5
Research: [R03 §6] Role 刪除時沙盒完整清除
Risk: RISK-06 (新建/刪除 Role 時沙盒邊界完整初始化與清除)
     RISK-17 (Expert 池清空時廣播 EXPERT_POOL_EMPTY)
"""
from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

from .cache import PromptCache

logger = logging.getLogger(__name__)


async def on_role_created(
    user_id: UUID,
    role_id: UUID,
    db: Any = None,
    broadcast_fn: Callable[[str, dict], Awaitable[None]] | None = None,
    log_fn: Callable[[str, dict], Awaitable[None]] | None = None,
) -> None:
    """
    [RISK-06 新建] 新 Role 建立後的沙盒初始化流程。
    前端在收到 ROLE_SANDBOX_READY 前必須鎖定 AI 幫手輸入框。
    role_router_rules 保持空（不預填種子規則）。
    """
    # 建立空的 role_settings 記錄（確保後續查詢不回傳 None）
    if db:
        await db.execute(
            "INSERT INTO role_settings (role_id, weekly_target_minutes) "
            "VALUES (:rid, 0) ON CONFLICT DO NOTHING",
            {"rid": str(role_id)},
        )

    if log_fn:
        await log_fn("role_sandbox_initialized", {
            "user_id": str(user_id),
            "role_id": str(role_id),
            "expert_count": 0,
            "rule_count": 0,
        })

    # 廣播 ROLE_SANDBOX_READY → 前端解鎖 AI 幫手輸入框
    if broadcast_fn:
        await broadcast_fn("ROLE_SANDBOX_READY", {
            "role_id": str(role_id),
            "is_empty": True,
        })


async def on_role_deleted(
    user_id: UUID,
    role_id: UUID,
    local_sqlite: Any = None,
    cloud_db: Any = None,
    prompt_cache: PromptCache | None = None,
    broadcast_fn: Callable[[str, dict], Awaitable[None]] | None = None,
    log_fn: Callable[[str, dict], Awaitable[None]] | None = None,
) -> None:
    """
    [RISK-06 刪除] Role 刪除後的沙盒清除流程。
    1. 清除 Prompt 快取
    2. 停用 role_router_rules（不硬刪除，保留歷史）
    3. 軟刪除 ai_experts（is_active=FALSE）
    4. 廣播 ROLE_DELETED
    """
    # Step 1: 清除快取
    if prompt_cache:
        prompt_cache.invalidate_by_role(role_id)

    # Step 2: 停用本地 SQLite 路由規則
    if local_sqlite:
        await local_sqlite.execute(
            "UPDATE role_router_rules SET status='inactive' WHERE role_id=:rid",
            {"rid": str(role_id)},
        )

    # Step 3: 軟刪除雲端 ai_experts
    if cloud_db:
        await cloud_db.execute(
            "UPDATE ai_experts SET is_active=FALSE WHERE role_id=:rid",
            {"rid": str(role_id)},
        )

    if log_fn:
        await log_fn("role_sandbox_torn_down", {
            "user_id": str(user_id),
            "role_id": str(role_id),
        })

    if broadcast_fn:
        await broadcast_fn("ROLE_DELETED", {"role_id": str(role_id)})


async def on_expert_deleted(
    role_id: UUID,
    expert_id: UUID,
    local_sqlite: Any = None,
    cloud_db: Any = None,
    prompt_cache: PromptCache | None = None,
    broadcast_fn: Callable[[str, dict], Awaitable[None]] | None = None,
) -> None:
    """
    Persona 刪除後的路由規則維護。
    [RISK-17] 若為最後一個 Persona，廣播 EXPERT_POOL_EMPTY。
    """
    # 停用對應路由規則
    if local_sqlite:
        await local_sqlite.execute(
            "UPDATE role_router_rules SET status='inactive' "
            "WHERE role_id=:rid AND persona_id=:pid",
            {"rid": str(role_id), "pid": str(expert_id)},
        )

    # 清除 Prompt 快取
    if prompt_cache:
        prompt_cache.invalidate_by_persona(expert_id)

    # 檢查是否清空了專家池 [RISK-17]
    if cloud_db and broadcast_fn:
        remaining = await cloud_db.fetch_one(
            "SELECT COUNT(*) as cnt FROM ai_experts "
            "WHERE role_id=:rid AND is_active=TRUE",
            {"rid": str(role_id)},
        )
        if remaining and remaining.get("cnt", 1) == 0:
            await broadcast_fn("EXPERT_POOL_EMPTY", {
                "role_id": str(role_id),
                "action_hint": "match_new_expert",
            })
