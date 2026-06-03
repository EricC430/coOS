"""
M4.6 -- Session 結束 Intention 抽取 (v1.2)

實作 SPEC: docs/modules/M4_6_observer_agent_SPEC.md §7.5
研究依據: [R10 §代理工作流]

每個 Session (thread) 結束時由本地 Gemma 抽取使用者進行此對話的核心 intention，
寫入 chat_transcripts 的 session metadata，供 M3.4 前端歷史時間軸的 intention 欄顯示。
抽取失敗 -> 記錄 intention_extraction_failed，前端顯示「(未抽取)」（SPEC §7.7）。
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def extract_session_intention(
    thread_id: str,
    role_id: str,
    persona_id: str,
    gemma: Any,
    db: Any,
) -> str | None:
    """
    從整段對話歷史抽取核心 intention 並寫入 session metadata。

    無對話 -> None。LLM 失敗 -> None（靜默，記錄日誌）。
    """
    transcripts = await db.fetch_thread_transcripts(thread_id)
    if not transcripts:
        return None

    conversation = "\n".join(
        f"{'使用者' if t.get('role') == 'user' else '專家'}: {t.get('content', '')}"
        for t in transcripts
    )
    prompt = (
        "請用一句話摘要此對話中使用者的核心意圖/目的是什麼。回傳純文字，不要 JSON。\n"
        f"對話內容：\n{conversation[:2000]}"
    )
    try:
        intention = (await gemma.generate_text(prompt)).strip()
    except Exception as e:
        logger.warning("[M4.6] intention_extraction_failed thread=%s: %s", thread_id, e)
        return None

    if not intention:
        return None
    await db.set_session_intention(thread_id=thread_id, intention=intention)
    return intention
