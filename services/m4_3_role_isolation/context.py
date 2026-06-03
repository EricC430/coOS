"""
M4.3.2 -- 角色上下文建構器

SPEC: docs/modules/M4_3_role_isolation_SPEC.md §7.2
Research: [R03 §人設崩塌] 角色-Persona 映射確保不跨角色共用
Risk: RISK-06 (implicit_state 以 (user_id, role_id) 雙鍵查詢)
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
    """
    role_id: UUID
    user_id: UUID
    active_experts: list[dict] = field(default_factory=list)
    projects: list[dict] = field(default_factory=list)
    settings: dict | None = None
    implicit_state: dict | None = None  # [RISK-06] 僅當前角色，None → 中性預設

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


async def build_role_context(
    user_id: UUID,
    role_id: UUID,
    db: Any = None,
) -> RoleContext:
    """
    [R03 §人設崩塌] 組裝當前角色的完整上下文。
    [RISK-06] implicit_state 嚴格以 (user_id, role_id) 雙鍵查詢。
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

        return RoleContext(
            role_id=role_id,
            user_id=user_id,
            active_experts=list(experts) if experts else [],
            projects=list(projects) if projects else [],
            settings=dict(settings) if settings else None,
            implicit_state=implicit_state,
        )
    except Exception as e:
        logger.error("[M4.3] build_role_context failed: %s. Returning empty context.", e)
        return RoleContext(role_id=role_id, user_id=user_id)
