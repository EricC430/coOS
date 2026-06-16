"""
M4.5.2 -- 殭屍草稿淘汰 Cron

實作 SPEC: docs/modules/M4_5_xp_settlement_SPEC.md §7.3
研究依據: [R08 §四.2] 清理過期未審草稿，防止堆積導致倦怠（反向微摩擦力管理）。

[決策] 預設 7 天，使用者可自訂閾值。
[RISK-13] 已核准 (is_reviewed) 或已結算 (xp_settled) 的反思絕不刪除。
          僅硬刪除「純草稿」(is_draft=True 且未結算未核准) 的過期記錄。

設計：操作注入式 store（測試用 in-memory；正式為 SQLAlchemy session 包裝），
      並以注入式 `now` 取代 wall clock 以利測試。
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_STALE_THRESHOLD_DAYS = 7


def _is_protected(reflection: Any) -> bool:
    """[RISK-13] 已核准或已結算的反思受保護，永不刪除。"""
    if not getattr(reflection, "is_draft", True):
        return True
    if getattr(reflection, "is_reviewed", False):
        return True
    if getattr(reflection, "xp_settled", False):
        return True
    return False


async def run_zombie_cleanup_cron(
    store: Any,
    threshold_days: int | None = None,
    now: datetime | None = None,
) -> list:
    """
    清理過期未審草稿（in-memory store 版，用於測試）。
    回傳被刪除的 reflection id 清單。

    [RISK-13] 受保護的反思（已核准/已結算/非草稿）一律跳過。
    """
    if now is None:
        now = datetime.now(UTC)
    threshold = threshold_days or DEFAULT_STALE_THRESHOLD_DAYS
    cutoff = now - timedelta(days=threshold)

    deleted: list = []
    for rid, reflection in list(store.reflections.items()):
        if _is_protected(reflection):
            continue
        created = getattr(reflection, "created_at", None)
        if created is None or created >= cutoff:
            continue
        # 僅硬刪除純草稿過期記錄
        del store.reflections[rid]
        deleted.append(rid)
        logger.info("[M4.5] zombie_draft_deleted reflection=%s", rid)

    return deleted


async def run_zombie_cleanup_sql(
    db_adapter: Any,
    threshold_days: int | None = None,
    now: datetime | None = None,
) -> None:
    """
    [GAP-B4] 生產環境版：直接對 SQLite/PostgreSQL 執行 SQL DELETE。
    由 main.py lifespan periodic_maintenance 呼叫，取代原本的內聯 DELETE。

    [RISK-13] WHERE 條件確保僅刪除 is_draft=1 AND is_reviewed=0 AND xp_settled=0 的過期記錄。
    """
    if now is None:
        now = datetime.now(UTC)
    threshold = threshold_days or DEFAULT_STALE_THRESHOLD_DAYS
    cutoff = (now - timedelta(days=threshold)).isoformat()

    try:
        await db_adapter.execute(
            "DELETE FROM daily_reflections "
            "WHERE is_completed = 0 AND created_at < :cutoff",
            {"cutoff": cutoff},
        )
        await db_adapter.execute(
            "DELETE FROM daily_reflection_segments "
            "WHERE is_reviewed = 0 AND xp_settled = 0 AND created_at < :cutoff",
            {"cutoff": cutoff},
        )
        logger.info("[M4.5] zombie_cleanup_sql executed, cutoff=%s", cutoff)
    except Exception as e:
        logger.warning("[M4.5] zombie_cleanup_sql failed: %s", e)
