"""
M4.1.5 -- 自適應規則更新器 (每日排程批次)

SPEC: docs/modules/M4_1_agent_router_SPEC.md §7.6
Research: [R10: §代理工作流狀態機] 每日排程批次執行，非即時
Risk: RISK-06 (role_id 嚴格隔離), RISK-13a (只用任務標題，不用明文)
Schedule: 每日 03:00 (M4.4 草稿生成在 02:00，兩者錯開避免 DB 鎖)
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 促進/廢棄門檻 (SPEC §7.6)
# ---------------------------------------------------------------------------
PROMOTE_MIN_HITS = 3     # 候選規則至少觸發次數
PROMOTE_MIN_ACC = 0.80   # 正確率閾值
REJECT_MIN_HITS = 5      # 達此次數才考慮廢棄
REJECT_MAX_ACC = 0.60    # 低於此且達 REJECT_MIN_HITS -> rejected


def _extract_keyword_tokens(text: str) -> list[str]:
    """
    [RISK-13a] 從任務標題提取關鍵詞，不含 PII。
    """
    try:
        import jieba  # type: ignore
        tokens = list(jieba.cut_for_search(text))
    except ImportError:
        tokens = re.findall(r"[一-鿿]{2,}|[a-zA-Z]{3,}", text)

    stopwords = {"的", "了", "嗎", "我", "你", "他", "是", "在", "有", "這", "那", "和",
                 "一個", "可以", "如何", "怎麼", "什麼", "為什麼"}
    filtered = [t.strip() for t in tokens if len(t.strip()) >= 2 and t.strip() not in stopwords]
    return filtered[:4]


async def _extract_from_reflections(role_id: str, db) -> None:
    """
    從近 7 天已核准的 daily_reflections 任務標題抽取關鍵字。
    [RISK-13a] 只用任務標題（使用者自填結構化欄位），不用原始對話明文。
    """
    since = datetime.utcnow() - timedelta(days=7)
    try:
        rows = await db.fetch_all(
            "SELECT task_title, routed_persona_domain FROM daily_reflection_segments "
            "WHERE role_id=:rid AND is_reviewed=1 AND created_at > :since",
            {"rid": role_id, "since": since.isoformat()},
        )
        for row in rows:
            tokens = _extract_keyword_tokens(row.get("task_title", ""))
            if tokens:
                pattern = "|".join(re.escape(t) for t in tokens)
                await _propose_rule_candidate(
                    db=db,
                    role_id=role_id,
                    pattern=pattern,
                    target_domain=row.get("routed_persona_domain", ""),
                    source="reflection_title",
                )
    except Exception as e:
        logger.warning("[M4.1.5] _extract_from_reflections failed: %s", e)


async def _apply_negative_signals(role_id: str, db) -> None:
    """
    從 routing_samples 找「路由後立即重新配對」的樣本 -> 降低對應規則信心。
    """
    try:
        neg_samples = await db.fetch_all(
            "SELECT rule_persona_id, COUNT(*) as cnt FROM routing_samples "
            "WHERE role_id=:rid AND outcome='user_immediate_rematch' "
            "AND created_at > datetime('now','-7 days') "
            "GROUP BY rule_persona_id",
            {"rid": role_id},
        )
        for s in neg_samples:
            decay = s["cnt"] * 0.03
            await db.execute(
                "UPDATE role_router_rules "
                "SET confidence = MAX(0.3, confidence - :decay) "
                "WHERE role_id=:rid AND persona_id=:pid AND status='active'",
                {"rid": role_id, "pid": s["rule_persona_id"], "decay": decay},
            )
    except Exception as e:
        logger.warning("[M4.1.5] _apply_negative_signals failed: %s", e)


async def _promote_or_reject_candidates(role_id: str, db) -> None:
    """候選規則達門檻 -> active；達廢棄條件 -> rejected"""
    try:
        candidates = await db.fetch_all(
            "SELECT * FROM role_router_rules WHERE role_id=:rid AND status='candidate'",
            {"rid": role_id},
        )
        for c in candidates:
            acc = c["correct_count"] / c["hit_count"] if c.get("hit_count", 0) > 0 else 0.0
            if c.get("hit_count", 0) >= PROMOTE_MIN_HITS and acc >= PROMOTE_MIN_ACC:
                await db.execute(
                    "UPDATE role_router_rules SET status='active' WHERE id=:id",
                    {"id": c["id"]},
                )
                logger.info("[M4.1.5] Rule %s promoted to active (acc=%.2f)", c["id"], acc)
            elif c.get("hit_count", 0) >= REJECT_MIN_HITS and acc < REJECT_MAX_ACC:
                await db.execute(
                    "UPDATE role_router_rules SET status='rejected' WHERE id=:id",
                    {"id": c["id"]},
                )
                logger.info("[M4.1.5] Rule %s rejected (acc=%.2f)", c["id"], acc)
    except Exception as e:
        logger.warning("[M4.1.5] _promote_or_reject_candidates failed: %s", e)


async def _propose_rule_candidate(
    db,
    role_id: str,
    pattern: str,
    target_domain: str,
    source: str,
    persona_id: str = "tool_ai_default",
) -> None:
    """寫入候選規則到 role_router_rules（status='candidate'）。"""
    try:
        await db.execute(
            "INSERT OR IGNORE INTO role_router_rules "
            "(role_id, persona_id, pattern, target_domain, source, status, confidence) "
            "VALUES (:rid, :pid, :pat, :dom, :src, 'candidate', 0.50)",
            {"rid": role_id, "pid": persona_id, "pat": pattern,
             "dom": target_domain, "src": source},
        )
    except Exception as e:
        logger.debug("[M4.1.5] propose_rule_candidate failed: %s", e)


async def run_adaptive_updater(role_id: str, db=None) -> None:
    """
    [R10 §代理工作流] 每日深夜批次，三步執行：
    1. 從 daily_reflections 抽取新關鍵字 -> 提案候選規則
    2. 從 routing_samples 負向信號降低規則信心
    3. 晉升/廢棄候選規則
    [RISK-06] role_id 嚴格隔離，跨角色規則不互影響
    """
    if db is None:
        logger.info("[M4.1.5] No DB provided, skipping adaptive update for %s", role_id)
        return
    await _extract_from_reflections(role_id, db)
    await _apply_negative_signals(role_id, db)
    await _promote_or_reject_candidates(role_id, db)
    logger.info("[M4.1.5] Adaptive update complete for role %s", role_id)
