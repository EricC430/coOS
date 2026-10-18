"""
M4.6 -- Topic Anchor Detection (Intent-Anchored Descriptive Labels)

Upgraded from project_detector.py (short noun-phrase tags) to descriptive
intent-anchored topic labels with motivation context.

Research: [R10 §Agent Workflow] [R02 §Dynamic State Decode]
Risks: RISK-06 (role scoped), RISK-08 (no direct Persona injection), RISK-12 (Eguard PII)

Flow:
  1. LLM prompt -> extract descriptive topic label + intent + motivation
  2. Eguard PII filter on all extracted fields
  3. Two-phase dedup (exact text + embedding cosine)
  4. Upsert topic_anchors table
  5. Emit SSE event (TOPIC_CREATED / TOPIC_SWITCHED)
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from .topic_dedup import (
    TopicAnchor,
    resolve_topic,
)

logger = logging.getLogger(__name__)


@dataclass
class TopicAnchorResult:
    topic_id: str
    label: str
    intent: str | None = None
    motivation: str | None = None
    is_new: bool = False


TOPIC_ANCHOR_PROMPT = """你是一個對話主題分析器，為個人目標管理系統服務。

既有主題標籤：
{existing_labels}

使用者訊息：{user_msg}

任務：判斷此訊息屬於哪個主題，或是否建立新主題。

規則：
1. 若訊息主題能語意對應到某個既有標籤 -> 回傳 JSON: {{"match": "既有標籤原文"}}
2. 若有新主題 -> 回傳 JSON: {{"new": "敘述性短句", "intent": "使用者想做什麼", "motivation": "為什麼在乎"}}
   - 標籤是一句含意圖的敘述短句（10~30字），如「了解微積分極限的學習意義」「廣泛探索個人職涯方向」
   - 不是名詞短語、不是問句、不是完整句子
   - intent: 使用者想達成什麼（動詞開頭）
   - motivation: 背後驅力（因為...、為了...）
3. 若是日常寒暄、無明確主題 -> 回傳 {{"none": true}}

只輸出 JSON，不要解釋。"""


def _build_prompt(user_msg: str, existing_labels: list[str]) -> str:
    labels_str = "\n".join(f"- {lbl}" for lbl in existing_labels) if existing_labels else "（無既有主題）"
    return TOPIC_ANCHOR_PROMPT.format(
        existing_labels=labels_str,
        user_msg=user_msg,
    )


def _parse_llm_response(raw: str) -> dict | None:
    """Parse LLM JSON response, tolerant of minor formatting issues."""
    if not raw:
        return None
    text = raw.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None


async def detect_topic_anchor(
    user_msg: str,
    role_id: str,
    db: Any,
    eguard: Any,
    sse: Any,
    gemma: Any | None = None,
    current_topic_id: str | None = None,
    thread_id: str | None = None,
) -> TopicAnchorResult | None:
    """
    Main entry: detect topic anchor from user message.

    Returns TopicAnchorResult or None (no topic detected / PII filtered).
    """
    # 1. Fetch existing topic anchors for this role
    try:
        rows = await db.fetch_all(
            "SELECT id, label, embedding, role_id FROM topic_anchors "
            "WHERE role_id = :rid AND status = 'active'",
            {"rid": role_id},
        )
        existing_topics = [
            TopicAnchor(
                id=r["id"],
                role_id=r["role_id"],
                label=r["label"],
                embedding=json.loads(r["embedding"]) if r.get("embedding") else None,
            )
            for r in rows
        ]
        existing_labels = [t.label for t in existing_topics]
    except Exception as e:
        logger.warning("[M4.6] Failed to fetch existing topics: %s", e)
        existing_topics = []
        existing_labels = []

    # 2. LLM extraction
    prompt = _build_prompt(user_msg, existing_labels)
    raw_response = None

    if gemma is not None:
        try:
            raw_response = await gemma.generate_text(prompt)
        except Exception as e:
            logger.debug("[M4.6] Gemma topic anchor extraction failed: %s", e)

    if not raw_response:
        try:
            from m4_1_router.routing_engine import (
                PERSONA_MODEL_FALLBACK,
                get_cloud_llm_client,
            )
            client = get_cloud_llm_client(PERSONA_MODEL_FALLBACK)
            raw_response = await client.complete(prompt, max_output_tokens=150, temperature=0.1)
        except Exception as e:
            logger.debug("[M4.6] Cloud LLM topic extraction failed: %s", e)
            return None

    # 3. Parse response
    parsed = _parse_llm_response(raw_response)
    if not parsed:
        return None

    # Case: no topic
    if parsed.get("none"):
        return None

    # Case: match existing
    if "match" in parsed:
        matched_label = parsed["match"]
        for topic in existing_topics:
            if topic.label == matched_label:
                if current_topic_id and topic.id == current_topic_id:
                    return TopicAnchorResult(
                        topic_id=topic.id, label=topic.label, is_new=False
                    )
                # Update last_seen + mention_count
                try:
                    await db.execute(
                        "UPDATE topic_anchors SET last_seen = datetime('now'), "
                        "mention_count = mention_count + 1, updated_at = datetime('now') "
                        "WHERE id = :tid",
                        {"tid": topic.id},
                    )
                except Exception as e:
                    logger.warning("[M4.6] Failed to update topic mention: %s", e)

                if sse and hasattr(sse, "emit"):
                    try:
                        await sse.emit("TOPIC_SWITCHED", {
                            "topic_id": topic.id,
                            "label": topic.label,
                            "role_id": role_id,
                        })
                    except Exception:
                        pass

                return TopicAnchorResult(
                    topic_id=topic.id, label=topic.label, is_new=False
                )
        return None

    # Case: new topic
    if "new" in parsed:
        label = parsed["new"]
        intent = parsed.get("intent")
        motivation = parsed.get("motivation")

        # 4. [RISK-12] Eguard PII filter on all fields
        try:
            label_sanitized = eguard.mask_pii(label).sanitized_text.strip()
            if "[REDACTED" in label_sanitized or not label_sanitized:
                return None
            label = label_sanitized

            if intent:
                intent_sanitized = eguard.mask_pii(intent).sanitized_text.strip()
                intent = intent_sanitized if "[REDACTED" not in intent_sanitized else None

            if motivation:
                motivation_sanitized = eguard.mask_pii(motivation).sanitized_text.strip()
                motivation = motivation_sanitized if "[REDACTED" not in motivation_sanitized else None
        except Exception:
            pass

        # 5. Two-phase dedup
        # TODO: compute embedding via local model when available
        candidate_embedding: list[float] | None = None

        topic_id, is_new = await resolve_topic(
            candidate_label=label,
            candidate_embedding=candidate_embedding,
            existing_topics=existing_topics,
            role_id=role_id,
        )

        # 6. Upsert
        if is_new:
            now = "datetime('now')"
            try:
                await db.execute(
                    "INSERT INTO topic_anchors "
                    "(id, role_id, label, intent, motivation, status, "
                    "mention_count, first_seen, last_seen, created_at, updated_at) "
                    "VALUES (:id, :rid, :label, :intent, :motivation, 'active', "
                    "1, datetime('now'), datetime('now'), datetime('now'), datetime('now'))",
                    {
                        "id": topic_id,
                        "rid": role_id,
                        "label": label,
                        "intent": intent,
                        "motivation": motivation,
                    },
                )
                logger.info("[M4.6] New topic anchor: '%s' (id=%s)", label, topic_id)
            except Exception as e:
                logger.warning("[M4.6] Failed to insert topic anchor: %s", e)
                return None

            if sse and hasattr(sse, "emit"):
                try:
                    await sse.emit("TOPIC_CREATED", {
                        "topic_id": topic_id,
                        "label": label,
                        "intent": intent,
                        "role_id": role_id,
                    })
                except Exception:
                    pass
        else:
            # Matched via dedup -> update mention
            try:
                await db.execute(
                    "UPDATE topic_anchors SET last_seen = datetime('now'), "
                    "mention_count = mention_count + 1, updated_at = datetime('now') "
                    "WHERE id = :tid",
                    {"tid": topic_id},
                )
            except Exception as e:
                logger.warning("[M4.6] Failed to update topic mention: %s", e)

            if sse and hasattr(sse, "emit"):
                try:
                    await sse.emit("TOPIC_SWITCHED", {
                        "topic_id": topic_id,
                        "label": label,
                        "role_id": role_id,
                    })
                except Exception:
                    pass

        # 7. Link to chat_transcripts if thread provided
        if thread_id:
            try:
                await db.execute(
                    "UPDATE chat_transcripts SET project = :tid "
                    "WHERE thread_id = :thread_id AND project IS NULL",
                    {"tid": topic_id, "thread_id": thread_id},
                )
            except Exception:
                pass

        return TopicAnchorResult(
            topic_id=topic_id,
            label=label,
            intent=intent,
            motivation=motivation,
            is_new=is_new,
        )

    return None
