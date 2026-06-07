"""
M4.3.2 -- 角色上下文建構器

SPEC: docs/modules/M4_3_role_isolation_SPEC.md §7.2
Research: [R03 §人設崩塌] 角色-Persona 映射確保不跨角色共用
Risk: RISK-06 (implicit_state 以 (user_id, role_id) 雙鍵查詢)
v1.2: 新增 active_goals + upcoming_promises 供 M4.2 [記憶區塊] 注入
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


@dataclass
class RoleContext:
    """
    M4.1 Router 與 M4.2 Persona 共用的角色上下文。
    [RISK-06] 所有欄位嚴格限定於單一 role_id。
    [v1.2] active_goals / upcoming_promises 供 M4.2 [記憶區塊] 注入。
    """
    role_id: UUID
    user_id: UUID
    active_experts: list[dict] = field(default_factory=list)
    projects: list[dict] = field(default_factory=list)
    settings: dict | None = None
    implicit_state: dict | None = None       # [RISK-06] 僅當前角色，None → 中性預設
    active_goals: list[dict] = field(default_factory=list)        # v1.2
    upcoming_promises: list[dict] = field(default_factory=list)   # v1.2

    def to_frontend_dto(self) -> dict:
        return {
            "role_id": str(self.role_id),
            "expert_count": len(self.active_experts),
            "project_count": len(self.projects),
        }


def _is_expired(state: dict) -> bool:
    """[RISK-06] implicit_state.expires_at < NOW() 視為過期。"""
    expires_at_raw = state.get("expires_at")
    if not expires_at_raw:
        return False
    try:
        if isinstance(expires_at_raw, datetime):
            expires_at = expires_at_raw
        else:
            expires_at = datetime.fromisoformat(str(expires_at_raw))
        now = datetime.now(tz=UTC)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        return expires_at < now
    except (ValueError, TypeError):
        return False


async def build_commitment_context(
    role_id: UUID,
    db: Any = None,
) -> tuple[list[dict], list[dict]]:
    """
    [v1.2] 承諾與目標上下文建構器。
    """
    if db is None:
        return [], []

    try:
        # 1. 自動標記過期承諾
        # SQLite compatible NOW() is (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        # But AsyncDBAdapter already replaces NOW() with SQLite syntax
        await db.execute(
            "UPDATE promises SET status = 'expired', updated_at = NOW() "
            "WHERE role_id = :rid AND status = 'active' "
            "AND deadline IS NOT NULL AND deadline < NOW()",
            {"rid": str(role_id)},
        )

        # 2. 撈取 active 目標（最多 3 筆，按建立時間排序）
        active_goals = await db.fetch_all(
            "SELECT id, persona_id, title, description, progress, status "
            "FROM goals WHERE role_id = :rid AND status = 'active' "
            "ORDER BY created_at ASC LIMIT 3",
            {"rid": str(role_id)},
        )

        # 3. 撈取即將到期的承諾
        # Note: SQLite doesn't support INTERVAL '3 days' easily. 
        # For MVP, we fetch all active promises and filter or just fetch active ones.
        upcoming_promises = await db.fetch_all(
            "SELECT id, persona_id, text, deadline, source_thread_id, status "
            "FROM promises WHERE role_id = :rid AND status = 'active' "
            "ORDER BY deadline ASC LIMIT 5",
            {"rid": str(role_id)},
        )

        return list(active_goals) if active_goals else [], \
               list(upcoming_promises) if upcoming_promises else []

    except Exception as e:
        logger.warning("[M4.3] build_commitment_context failed: %s. Returning empty.", e)
        return [], []


async def build_role_context(
    user_id: UUID,
    role_id: UUID,
    db: Any = None,
) -> RoleContext:
    """
    [R03 §人設崩塌] 組裝當前角色的完整上下文。
    [RISK-06] implicit_state 嚴格以 (user_id, role_id) 雙鍵查詢。
    [v1.2] 同時撈取 active_goals / upcoming_promises。
    超時 >3s → 回傳空 RoleContext（M4.3 §7.6 異常處理）。
    """
    if db is None:
        return RoleContext(role_id=role_id, user_id=user_id)

    try:
        experts = await db.fetch_all(
            "SELECT * FROM ai_experts WHERE role_id = :rid AND is_active = TRUE",
            {"rid": str(role_id)},
        )
        projects = await db.fetch_all(
            "SELECT * FROM role_projects WHERE role_id = :rid AND status = 'active'",
            {"rid": str(role_id)},
        )
        settings = await db.fetch_one(
            "SELECT * FROM role_settings WHERE role_id = :rid",
            {"rid": str(role_id)},
        )
        # [RISK-06] 雙鍵查詢，絕不單用 user_id
        raw_state = await db.fetch_one(
            "SELECT * FROM role_implicit_states "
            "WHERE user_id = :uid AND role_id = :rid "
            "ORDER BY inferred_at DESC LIMIT 1",
            {"uid": str(user_id), "rid": str(role_id)},
        )

        # 過期狀態視為 None
        implicit_state = None
        if raw_state and not _is_expired(raw_state):
            implicit_state = dict(raw_state)

        # [v1.2] 承諾與目標
        active_goals, upcoming_promises = await build_commitment_context(role_id, db=db)

        return RoleContext(
            role_id=role_id,
            user_id=user_id,
            active_experts=list(experts) if experts else [],
            projects=list(projects) if projects else [],
            settings=dict(settings) if settings else None,
            implicit_state=implicit_state,
            active_goals=active_goals,
            upcoming_promises=upcoming_promises,
        )
    except Exception as e:
        logger.error("[M4.3] build_role_context failed: %s. Returning empty context.", e)
        return RoleContext(role_id=role_id, user_id=user_id)
