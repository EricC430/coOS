"""
M4.6 -- 承諾萃取 (Promise Extraction, v1.2)

實作 SPEC: docs/modules/M4_6_observer_agent_SPEC.md §7.4
研究依據: [R10 §代理工作流] + 時間 NER

純 Regex 無法涵蓋「我這週末應該可以搞定」等模糊承諾語句，因此以本地 Gemma 做語意理解。
[RISK-12] 承諾原文可能含 PII（如「幫陳小明做報告」），寫入 promises 表前必須先經 Eguard 泛化。

寫入的 promises 由 M4.3 build_commitment_context() 預撈，供 M4.2 Persona [記憶區塊] 注入。
"""
from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


async def extract_promises(
    user_msg: str,
    thread_id: str,
    role_id: str,
    persona_id: str,
    gemma: Any,
    eguard: Any,
    db: Any,
    sse: Any,
) -> list[dict]:
    """
    使用本地 Gemma 抽取口頭承諾，經 Eguard 泛化後寫入 promises 表並廣播 SSE。

    回傳已寫入的承諾清單（可能為空）。LLM 回傳格式錯誤 -> 靜默忽略（SPEC §7.7）。
    """
    prompt = (
        "從以下使用者訊息中抽取任何口頭承諾或時間約定。"
        "回傳 JSON 陣列，每個元素包含 text（承諾原文）和 deadline"
        "（ISO 格式，若無法確定則為 null）。若無承諾則回傳空陣列 []。\n"
        f"使用者訊息：{user_msg}"
    )
    try:
        raw = await gemma.generate_json(prompt)
        # Gemma edge model returns intent-vector dicts, not structured promise lists.
        # Only attempt to parse if raw is a JSON string or already a list.
        if isinstance(raw, list):
            promises = raw
        elif isinstance(raw, str):
            promises = json.loads(raw)
        else:
            # dict from Gemma edge (intent_label / context_summary format) — no promises inside
            return []
    except Exception as e:
        logger.warning("[M4.6] promise_extraction_parse_error: %s", e)
        return []

    written: list[dict] = []
    for promise in promises:
        try:
            # [RISK-12] 泛化承諾原文
            text = eguard.filter_pii(promise["text"]).strip()
            if not text or "[REDACTED]" == text:
                continue
            deadline = promise.get("deadline")
            await db.insert_promise(
                role_id=role_id,
                persona_id=persona_id,
                source_thread_id=thread_id,
                text=text,
                deadline=deadline,
            )
            await sse.emit("PROMISE_RECORDED", {
                "text": text, "deadline": deadline, "persona_id": persona_id,
            })
            written.append({"text": text, "deadline": deadline})
        except (KeyError, TypeError) as e:
            logger.warning("[M4.6] promise_extraction_parse_error item=%s: %s", promise, e)
            continue

    return written
