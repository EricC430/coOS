"""
M4.3 Thread ID 角色前綴策略

SPEC: docs/modules/M4_3_role_isolation_SPEC.md §7.4
Risk: RISK-06 (防止跨角色對話歷史洩漏)
"""
from __future__ import annotations

import uuid


def create_scoped_thread_id(role_id: uuid.UUID) -> str:
    """
    [RISK-06] 產生包含 role_id 前綴的 thread_id。
    格式：{role_id}::{uuid4}
    查詢時強制過濾前綴，即使直接拼 thread_id 也無法跨角色讀取。
    """
    return f"{role_id}::{uuid.uuid4()}"


def validate_thread_access(thread_id: str, current_role_id: uuid.UUID) -> bool:
    """
    [RISK-06] 驗證 thread 屬於當前角色。
    前綴不匹配時拒絕存取。
    """
    parts = thread_id.split("::", 1)
    if len(parts) < 2:
        return False
    return parts[0] == str(current_role_id)


def extract_role_id_from_thread(thread_id: str) -> str | None:
    """從 thread_id 解析出 role_id 前綴（用於日誌或驗證）。"""
    parts = thread_id.split("::", 1)
    return parts[0] if len(parts) == 2 else None
