"""
M4.6 -- 目標確立偵測 (Goal Establishment Detection, v1.2)

實作 SPEC: docs/modules/M4_6_observer_agent_SPEC.md §7.6
研究依據: [R10 §代理工作流] + [R09 §6.2 BDI]

使用本地 Gemma 判斷對話是否確立了新的最高階目標。
[RISK-12] 目標標題經 Eguard 泛化。
[決策] 去重模糊匹配閾值 0.7（較專案 0.85 寬鬆，因目標數量少、措辭多樣）。
觸發 GOAL_CONFIRMED SSE（區別於單純的 GOAL_INFERRED）。
"""
from __future__ import annotations

import json
import logging
from typing import Any

from .project_detector import fuzzy_match

logger = logging.getLogger(__name__)

GOAL_FUZZY_THRESHOLD = 0.7


async def detect_goal_establishment(
    user_msg: str,
    assistant_msg: str,
    thread_id: str,
    role_id: str,
    persona_id: str,
    existing_goals: list[dict],
    gemma: Any,
    eguard: Any,
    db: Any,
    sse: Any,
    expert_name: str | None = None,
) -> dict | None:
    """
    判斷對話是否確立新核心目標；若有且不與既有 active goals 重複 -> 寫入 goals 表。

    回傳已確立的目標 dict 或 None。LLM 失敗 / 無目標 -> None（靜默）。
    """
    prompt = (
        "以下對話中，使用者是否與專家確立了一個明確的核心目標或最高階目的？"
        '若有，回傳 JSON: {"title": "目標標題", "description": "詳細描述"}。'
        "若無明確目標確立，回傳 null。\n"
        f"專家：{assistant_msg[:500]}\n使用者：{user_msg[:500]}"
    )
    try:
        raw = await gemma.generate_json(prompt)
        result = raw if isinstance(raw, dict) or raw is None else json.loads(raw)
    except Exception as e:
        logger.warning("[M4.6] goal_detection_parse_error: %s", e)
        return None

    if not result or not result.get("title"):
        return None

    # [RISK-12] 泛化目標標題
    title = eguard.filter_pii(result["title"]).strip()
    if not title:
        return None

    existing_titles = [g.get("title", "") for g in existing_goals]
    if fuzzy_match(title, existing_titles, threshold=GOAL_FUZZY_THRESHOLD):
        return None  # 與既有目標重複，不新建

    await db.insert_goal(
        role_id=role_id,
        persona_id=persona_id,
        title=title,
        description=result.get("description", ""),
    )
    try:
        import uuid
        payload = {
            "type": "GOAL_CONFIRMED",
            "title": title,
            "persona_id": persona_id,
        }
        if expert_name:
            payload["expert_name"] = expert_name
        await db.execute(
            "INSERT INTO chat_transcripts (id, thread_id, persona_id, role, content, role_id) "
            "VALUES (:id, :tid, :pid, 'system_event', :content, :rid)",
            {
                "id": str(uuid.uuid4()),
                "tid": thread_id,
                "pid": persona_id,
                "content": json.dumps(payload, ensure_ascii=False),
                "rid": role_id,
            }
        )
    except Exception as ex:
        logger.warning("[M4.6] Failed to insert goal system_event to chat_transcripts: %s", ex)

    sse_payload = {"title": title, "persona_id": persona_id}
    if expert_name:
        sse_payload["expert_name"] = expert_name
    await sse.emit("GOAL_CONFIRMED", sse_payload)
    return {"title": title, "description": result.get("description", "")}
