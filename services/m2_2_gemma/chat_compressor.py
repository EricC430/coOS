"""
M2.2.2 -- Chat Digest Compressor

[R07: POST SS4.3] Edge-side semantic compression of chat transcripts.
[RISK-15] chat_transcripts.content is L1 plaintext -- NEVER leaves local device.
          Only the de-identified IntentVector (intent_label + context_summary)
          is written to intent_logs with source_type='chat_digest'.

Design:
  - Called ONCE per thread lifetime, triggered when a 30-minute inactivity split
    closes the thread (_resolve_session_thread_id returns ended_thread_id != None).
  - Also called at 02:00 by run_draft_cron to compress any threads that were never
    split (i.e. the user's last session of the day ended without a new message).
  - Groups all user-role messages from the ended thread for the current date.
  - Builds a privacy-scrubbing prompt and sends to local Gemma via GemmaEdgeClient.
  - Falls back to RuleBasedExtractor if Gemma is unreachable.
  - Idempotency: skips if an intent_log for this thread_id already exists.

Output schema in intent_logs:
  source_type = 'chat_digest'
  source_log_id = thread_id   (FK semantic, not strict FK)
  intent_label  = de-identified intent (e.g. "planning_exam_schedule")
  context_summary = de-identified summary (e.g. "user working on academic task, moderate focus")
  inference_mode = 'gemma_edge' | 'rule_based_fallback'
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from .client import GemmaEdgeClient
from .fallback import RuleBasedExtractor

logger = logging.getLogger(__name__)

_CHAT_COMPRESS_SYSTEM_PROMPT = (
    "You are a privacy-preserving chat summarizer. "
    "Read the user's recent conversation messages and output a de-identified summary.\n"
    "Rules:\n"
    "1. Remove ALL personal identifiers: real names, file paths, URLs, IPs, specific dates, "
    "   course codes, professor names, school names.\n"
    "2. Generalize concrete topics: ('calc exam next Tuesday' -> 'upcoming academic assessment'), "
    "   ('fix bug in auth.py' -> 'software debugging task').\n"
    "3. Preserve intent and cognitive load: capture WHAT TYPE of work and HOW the user felt "
    "   (stuck, in flow, anxious, planning).\n"
    "4. Output ONLY valid JSON with keys:\n"
    "   intent_label (short snake_case string, e.g. 'exam_preparation'),\n"
    "   context_summary (1-2 sentences, de-identified, Traditional Chinese preferred),\n"
    "   frustration_level (0.0-1.0),\n"
    "   valence (-1.0 to 1.0),\n"
    "   arousal (0.0 to 1.0),\n"
    "   stripped_entities_count (integer count of removed entities)."
)


class ChatCompressor:
    """
    M2.2.2: Compress user messages from an ended chat thread into an intent_log entry.
    One compression per thread lifetime; idempotent (skips if already compressed).
    """

    def __init__(
        self,
        ai_local_host: str = "http://192.168.0.79:11434",
        model: str = "gemma-4-e4b-it-4bit",
        timeout: float = 90.0,
    ) -> None:
        self._client = GemmaEdgeClient(ai_local_host, model, timeout)
        self._fallback = RuleBasedExtractor()

    async def compress_thread(
        self,
        thread_id: str,
        role_id: str,
        db: Any,
    ) -> bool:
        """
        Compress user messages from thread_id and write to intent_logs.

        Idempotent: returns False without writing if a chat_digest entry already exists
        for this thread_id (safe to call from both thread-split trigger and cron).
        Returns True if a new log entry was written.
        [RISK-15] Reads chat_transcripts locally; only de-identified output goes to intent_logs.
        """
        # Idempotency check: skip if already compressed for this thread
        try:
            existing = await db.fetch_one(
                "SELECT id FROM intent_logs "
                "WHERE source_log_id = :tid AND source_type = 'chat_digest' LIMIT 1",
                {"tid": thread_id},
            )
            if existing:
                logger.debug("[M2.2.2] thread=%s already compressed, skipping", thread_id)
                return False
        except Exception as e:
            logger.warning("[M2.2.2] idempotency check failed for thread=%s: %s", thread_id, e)

        # Fetch only user-role messages from this thread (L1 -- local SQLite only)
        try:
            rows = await db.fetch_all(
                "SELECT content FROM chat_transcripts "
                "WHERE thread_id = :tid AND role = 'user' "
                "ORDER BY created_at ASC",
                {"tid": thread_id},
            )
        except Exception as e:
            logger.warning("[M2.2.2] fetch chat_transcripts failed for thread=%s: %s", thread_id, e)
            return False

        if not rows:
            return False

        user_messages = [r["content"] if hasattr(r, "__getitem__") else getattr(r, "content", "") for r in rows]
        user_messages = [m for m in user_messages if m and m.strip()]
        if not user_messages:
            return False

        # Build compression input -- keep message count bounded to avoid prompt overflow
        capped = user_messages[-12:] if len(user_messages) > 12 else user_messages
        numbered = "\n".join(f"[{i+1}] {m}" for i, m in enumerate(capped))
        compress_input = f"Conversation thread ({len(capped)} user messages):\n{numbered}"

        # Compress via Gemma edge; fallback to rule-based on failure
        entry_id = str(uuid.uuid4())
        vector = await self._call_gemma(compress_input, thread_id, role_id)

        try:
            await db.execute(
                "INSERT INTO intent_logs "
                "(id, source_log_id, role_id, intent_label, context_summary, inference_mode, source_type) "
                "VALUES (:id, :src, :rid, :label, :ctx, :mode, 'chat_digest')",
                {
                    "id": entry_id,
                    "src": thread_id,
                    "rid": role_id,
                    "label": vector["intent_label"],
                    "ctx": vector["context_summary"],
                    "mode": vector["inference_mode"],
                },
            )
            logger.debug(
                "[M2.2.2] chat_digest written for thread=%s label=%s mode=%s",
                thread_id, vector["intent_label"], vector["inference_mode"],
            )
            return True
        except Exception as e:
            logger.warning("[M2.2.2] intent_logs insert failed for thread=%s: %s", thread_id, e)
            return False

    async def _call_gemma(self, text: str, thread_id: str, role_id: str) -> dict:
        """Try Gemma edge; fall back to rule-based. Always returns a valid dict."""
        full_input = _CHAT_COMPRESS_SYSTEM_PROMPT + "\n\n---\n\n" + text

        try:
            raw = await self._client.generate(full_input, role_id=role_id, correlation_id=thread_id)
            if not isinstance(raw, dict) or "intent_label" not in raw:
                raise ValueError(f"Missing intent_label in response: {raw!r}")
            return {
                "intent_label": str(raw.get("intent_label", "chat_activity")),
                "context_summary": str(raw.get("context_summary", "")),
                "inference_mode": "gemma_edge",
            }
        except Exception as e:
            logger.info("[M2.2.2] Gemma unavailable for chat compress (thread=%s): %s", thread_id, e)

        # Rule-based fallback: extract from raw text
        extracted = self._fallback.extract(text)
        return {
            "intent_label": extracted.get("intent_label", "chat_activity"),
            "context_summary": extracted.get("context_summary", "使用者今日進行對話互動。"),
            "inference_mode": "rule_based_fallback",
        }
