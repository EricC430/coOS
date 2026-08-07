"""
M4.6 -- Topic Batch Confirmation (Session-End Path)

When a session closes, re-evaluate the topic label with full conversation
context and extract accumulated context_summary + progress_note.

Research: [R10 §Agent Workflow] batch re-evaluation pattern
Risks: RISK-12 (context_summary must not contain PII -- filtered upstream at detect time)

Adapted from ai-elder-care's session-close batch extraction pattern,
but focused on confirming/correcting a single topic label (not extracting N events).
"""
from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class BatchConfirmResult:
    label_confirmed: bool
    corrected_label: str | None = None
    context_summary: str | None = None
    intent_update: str | None = None
    motivation_update: str | None = None
    progress_note: str | None = None


TOPIC_CONFIRM_PROMPT = """你是對話主題確認與脈絡萃取器。

對話內容：
{conversation}

即時路徑判定的主題標籤：{realtime_label}

任務：
1. 確認即時判定的主題標籤是否準確描述了此對話的核心主題。若不準確，回傳修正後的標籤。
2. 萃取此次對話中關於該主題的脈絡摘要（context_summary）：使用者的進度、新發現、情緒轉變。
3. 判斷使用者的 intent/motivation 是否需要更新。

回傳 JSON:
{{
  "label_confirmed": true/false,
  "corrected_label": "（若 label_confirmed=false，修正後的敘述性標籤，10~30字）",
  "context_summary": "此次對話的脈絡摘要（1-3句）",
  "intent_update": "更新後的意圖（若有變化，否則 null）",
  "motivation_update": "更新後的動機（若有變化，否則 null）",
  "progress_note": "進度更新（若有，否則 null）"
}}

只輸出 JSON，不要解釋。"""


async def batch_confirm_topic(
    thread_id: str,
    topic_id: str,
    realtime_label: str,
    role_id: str,
    gemma: Any,
    db: Any,
) -> BatchConfirmResult | None:
    """
    Session-end batch confirmation of topic anchor.

    Reads full conversation, confirms/corrects the realtime label,
    and extracts context_summary for topic_sessions accumulation.
    Returns None if no transcripts or LLM failure.
    """
    # 1. Fetch conversation
    transcripts = await db.fetch_thread_transcripts(thread_id)
    if not transcripts:
        return None

    conversation = "\n".join(
        f"{'使用者' if t.get('role') == 'user' else '專家'}: {t.get('content', '')}"
        for t in transcripts
    )
    # Truncate to avoid exceeding context window
    conversation = conversation[:3000]

    # 2. LLM confirmation
    prompt = TOPIC_CONFIRM_PROMPT.format(
        conversation=conversation,
        realtime_label=realtime_label,
    )

    try:
        raw = await gemma.generate_text(prompt)
    except Exception as e:
        logger.warning("[M4.6] batch_confirm LLM failed thread=%s: %s", thread_id, e)
        return None

    if not raw:
        return None

    # 3. Parse response
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        logger.warning("[M4.6] batch_confirm parse failed thread=%s", thread_id)
        return None

    result = BatchConfirmResult(
        label_confirmed=parsed.get("label_confirmed", True),
        corrected_label=parsed.get("corrected_label"),
        context_summary=parsed.get("context_summary"),
        intent_update=parsed.get("intent_update"),
        motivation_update=parsed.get("motivation_update"),
        progress_note=parsed.get("progress_note"),
    )

    # 4. Apply updates to topic_anchors
    if not result.label_confirmed and result.corrected_label:
        try:
            await db.execute(
                "UPDATE topic_anchors SET label = :label, updated_at = datetime('now') "
                "WHERE id = :tid",
                {"label": result.corrected_label, "tid": topic_id},
            )
        except Exception as e:
            logger.warning("[M4.6] Failed to correct topic label: %s", e)

    if result.intent_update:
        try:
            await db.execute(
                "UPDATE topic_anchors SET intent = :intent, updated_at = datetime('now') "
                "WHERE id = :tid",
                {"intent": result.intent_update, "tid": topic_id},
            )
        except Exception as e:
            logger.warning("[M4.6] Failed to update topic intent: %s", e)

    if result.motivation_update:
        try:
            await db.execute(
                "UPDATE topic_anchors SET motivation = :motivation, updated_at = datetime('now') "
                "WHERE id = :tid",
                {"motivation": result.motivation_update, "tid": topic_id},
            )
        except Exception as e:
            logger.warning("[M4.6] Failed to update topic motivation: %s", e)

    # 5. Insert topic_session record (context accumulation)
    if result.context_summary or result.progress_note:
        try:
            await db.execute(
                "INSERT INTO topic_sessions "
                "(id, topic_id, thread_id, context_summary, progress_note, recorded_at) "
                "VALUES (:id, :topic_id, :thread_id, :ctx, :prog, datetime('now'))",
                {
                    "id": str(uuid.uuid4()),
                    "topic_id": topic_id,
                    "thread_id": thread_id,
                    "ctx": result.context_summary,
                    "prog": result.progress_note,
                },
            )
        except Exception as e:
            logger.warning("[M4.6] Failed to insert topic_session: %s", e)

    return result
