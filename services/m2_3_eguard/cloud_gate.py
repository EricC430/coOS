"""M2.3 cloud gate -- mask PII in any text right before it is sent to a cloud LLM

DEVIATION-09 / decision D1(a): persona and tool-AI prompts carry user messages,
chat history and episodic memories (L1). The local copies stay untouched; only
the cloud-bound copy is masked here.

[R07: POST §4.3] raw L1 text must not go to the cloud as-is
[R07: §5 Eguard] discrete text masking before upload
Risk: RISK-06 (role_id propagated into SanitizedPayload and the audit log)

Callers must fail closed: if masking raises, do not send the raw text.
"""

from __future__ import annotations

import json
import logging

from .filter import EguardFilter
from .schema import SanitizedPayload

logger = logging.getLogger(__name__)

_filter: EguardFilter | None = None


def _get_filter() -> EguardFilter:
    global _filter
    if _filter is None:
        _filter = EguardFilter()
    return _filter


def mask_text_for_cloud(text: str, role_id: str = "") -> SanitizedPayload:
    """Mask PII in one cloud-bound text. Never mutates the caller's data."""
    return _get_filter().mask_pii(text or "", role_id=role_id)


def mask_history_for_cloud(
    history: list[dict] | None, role_id: str = ""
) -> tuple[list[dict], list[str]]:
    """Return a masked copy of chat history ({role, content} dicts) plus masked entity names."""
    masked_history: list[dict] = []
    entities: list[str] = []
    for item in history or []:
        result = mask_text_for_cloud(item.get("content", ""), role_id=role_id)
        masked_history.append({**item, "content": result.sanitized_text})
        entities.extend(result.masked_entities)
    return masked_history, entities


async def emit_cloud_mask_log(caller_module: str, role_id: str, entities: list[str]) -> None:
    """Write a raw_tracking_logs event (M0.4) when something was masked.

    Payload holds entity names and counts only -- never the masked text.
    Non-blocking: logging failures are swallowed.
    """
    if not entities:
        return
    counts: dict[str, int] = {}
    for name in entities:
        counts[name] = counts.get(name, 0) + 1
    try:
        from m0_4_logging.writer import get_logger as get_log_writer

        await get_log_writer().emit(
            module="M2.3",
            action="pii_masked_before_cloud",
            level="INFO",
            payload=json.dumps({"caller": caller_module, "entities": counts}, ensure_ascii=False),
            role_id=role_id,
        )
    except Exception as e:
        logger.debug("[M2.3] Failed to emit cloud mask log: %s", e)
