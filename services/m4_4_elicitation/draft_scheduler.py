"""
M4.4.3 -- 深夜草稿排程器 (Nightly Draft Scheduler)

實作 SPEC: docs/modules/M4_4_natural_elicitation_draft_SPEC.md §7.3
研究依據: [R10 §MindScape + R08 §六.2 吉布斯循環]

[RISK-01] 產出的草稿永遠 is_draft=True, is_reviewed=False，主觀欄位留空 -- 絕不自動核准。
[RISK-15] ai_description 經 gibbs_template 結構性排除 content_summary，並再經 Eguard 泛化脫敏。
[RISK-06] 草稿嚴格歸屬當前 role_id。

排程：預設每日 02:00（與 M4.1.5 的 03:00 錯開，見 M4.1 SPEC §9）。
      可由 role_settings.daily_report_time 自訂（SPEC §9 決議）。
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from .gibbs_template import build_gibbs_analysis, build_gibbs_description

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Eguard 泛化 (second-layer PII defense, RISK-15)
# ---------------------------------------------------------------------------

def _eguard_generalize(text: str, role_id: str = "") -> str:
    """
    [RISK-15] 第二層脫敏：即使描述只用泛化指標，仍經 Eguard 遮蔽任何殘留 PII。

    Eguard 不可用時降級為原文（gibbs_template 已結構性排除 content_summary，
    描述本身不含 L1 明文，因此降級不會洩漏側通道）。
    """
    try:
        from m2_3_eguard.filter import EguardFilter

        return EguardFilter().mask_pii(text, role_id=role_id).sanitized_text
    except Exception as e:  # pragma: no cover - defensive
        logger.warning("[M4.4] Eguard generalize unavailable, passthrough: %s", e)
        return text


# ---------------------------------------------------------------------------
# 單一角色草稿生成
# ---------------------------------------------------------------------------

async def generate_draft(
    user_id: str,
    role_id: str,
    reflection_date: date,
    db: Any,
) -> Any | None:
    """
    為單一角色拼裝某一日的吉布斯反思草稿。

    無任何遙測記錄 -> 回傳 None（不產出空洞反思，SPEC §7.5）。
    [RISK-01] is_draft=True / is_reviewed=False / 主觀欄位 None。
    """
    logs = await db.fetch_tracking_logs(user_id, role_id, reflection_date)
    if not logs:
        return None

    elicited = await db.fetch_elicited_durations(user_id, role_id, reflection_date)

    ai_description = build_gibbs_description(logs, elicited)
    ai_analysis = build_gibbs_analysis(logs, elicited)

    # [RISK-15] 寫入前經 Eguard 泛化。
    ai_description = _eguard_generalize(ai_description, role_id=role_id)

    activity_minutes = sum(
        (log.get("payload", {}) if isinstance(log, dict) else getattr(log, "payload", {})).get(
            "duration_minutes", 0
        )
        for log in logs
    )
    source_log_ids = [
        log["id"] if isinstance(log, dict) else getattr(log, "id", None) for log in logs
    ]

    return await db.create_draft_reflection(
        user_id=user_id,
        role_id=role_id,
        reflection_date=reflection_date,
        ai_description=ai_description,
        ai_analysis=ai_analysis,
        source_log_ids=source_log_ids,
        activity_minutes=activity_minutes,
        # [RISK-01] 以下欄位永遠為預設值，絕不自動核准。
        is_draft=True,
        is_reviewed=False,
        user_feeling=None,
        user_action_plan=None,
    )


# ---------------------------------------------------------------------------
# 排程入口
# ---------------------------------------------------------------------------

async def run_draft_cron(
    user_id: str,
    db: Any,
    today: date | None = None,
) -> list:
    """
    每日排程入口（預設 02:00 由 arq 觸發）。

    為前一日 (today - 1) 的每個 active 角色產出草稿。
    `today` 可注入以利測試（避免依賴 freezegun / wall clock）。
    """
    if today is None:
        today = date.today()
    yesterday = today - timedelta(days=1)

    roles = await db.get_user_active_roles(user_id)
    drafts: list = []
    for role in roles:
        role_id = role["id"] if isinstance(role, dict) else getattr(role, "id")
        try:
            draft = await generate_draft(user_id, role_id, yesterday, db=db)
        except Exception as e:  # SPEC §7.5: 單一角色超時/失敗不影響其餘角色
            logger.warning("[M4.4] draft generation failed for role=%s: %s", role_id, e)
            continue
        if draft is not None:
            drafts.append(draft)

    return drafts
