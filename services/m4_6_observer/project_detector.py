"""
M4.6 -- 主題標籤偵測與去重 (Topic Tag Detection & Dedup)

實作 SPEC: docs/modules/M4_6_observer_agent_SPEC.md §7.2 / §9
研究依據: [R10 §代理工作流]

NOTE: 「專案」在此系統是「聊天主題標籤 (Topic Tag)」，不一定是正式專案實體。
      例如「微積分練習方法」「找實習」「學 Python」都是合法的 topic tag。

流程 (SPEC §9 決策)：
  1. Regex 快速路徑：命中則跳過 LLM
  2. LLM 語意分析 (Gemma 邊緣 or Cloud fallback)：
     - 輸入：user_msg + 既有標籤清單
     - 輸出：匹配到既有標籤 / 新標籤名稱 / null (無明確主題)
  3. [RISK-12] Eguard PII 過濾
  4. 模糊去重（閾值 0.85）
  5. 新建 role_projects，發送 SSE
[RISK-06] 所有寫入綁定當前 role_id。
"""
from __future__ import annotations

import logging
import re
from difflib import SequenceMatcher
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Regex 快速路徑
# ---------------------------------------------------------------------------

EXTRACT_PATTERNS: list[str] = [
    r"(?:我想做|開始做|要做|在做|想開始做|正在做|準備做)\s*(.{2,20}?)(?:的(?:期末)?(?:專案|作業|報告|side project)|專案|作業|報告)",
    r"(.{2,20}?)(?:專案|project)\s*(?:開始|啟動|建立|進行|推進|開發)",
    r"(?:我(?:在|要|想|開始)學|正在學習)\s*(.{2,20}?)(?:$|，|。|，|這個|的)",
    r"(?:我有個|做一個|做個|建一個|建個)\s*(.{2,20}?)(?:$|，|。|的|，)",
    r"(.{2,20}?)(?:的期末|期末報告|期末考|期中報告|作業|homework)",
    r"(?:side project|副業|個人專案|自己的專案)\s*[：:是叫叫做]?\s*(.{2,20}?)(?:$|，|。)",
]

_TRAILING_NOISE = (
    "的", "期末", "這個", "那個", "一個", "個", "要做", " 要做",
    "一下", "看看", "之類的", "什麼的", "吧", "啊", "喔", "欸",  # [W9.6] 口語化尾綴
)

FUZZY_THRESHOLD = 0.85


def _clean_candidate(text: str) -> str:
    text = text.strip()
    changed = True
    while changed:
        changed = False
        for noise in _TRAILING_NOISE:
            if text.endswith(noise):
                text = text[: -len(noise)].strip()
                changed = True
    return text


def regex_extract_project(user_msg: str) -> str | None:
    """Regex 快速路徑：抽取主題標籤候選；無命中回傳 None。"""
    for pattern in EXTRACT_PATTERNS:
        m = re.search(pattern, user_msg)
        if m:
            candidate = _clean_candidate(m.group(1))
            if len(candidate) >= 2:
                return candidate
    return None


def fuzzy_match(
    candidate: str, existing: list[str], threshold: float = FUZZY_THRESHOLD
) -> str | None:
    """子字串包含 + SequenceMatcher，回傳第一個相似度 >= threshold 的既有標籤。"""
    for name in existing:
        if name in candidate or candidate in name:
            return name
        ratio = SequenceMatcher(None, candidate, name).ratio()
        if ratio >= threshold:
            return name
    return None


# ---------------------------------------------------------------------------
# LLM 語意分析路徑 (SPEC §9 回退)
# ---------------------------------------------------------------------------

async def _llm_extract_topic(
    user_msg: str,
    existing_names: list[str],
    gemma: Any | None,
) -> str | None:
    """
    [SPEC §9] LLM 語意路徑：判斷 user_msg 的主要討論主題。
    - 優先使用 Gemma 邊緣推論（若可用）
    - Gemma 不可用時 fallback 到 Cloud LLM (gemini-3.1-flash-lite)
    - 兩者都失敗則靜默回傳 None

    輸出規則：
    - 若訊息主題能對應到 existing_names 中的某個標籤 -> 回傳那個標籤名稱（原文）
    - 若訊息有清晰主題但無既有標籤 -> 回傳一個 2~10 字的繁體中文主題標籤
    - 若訊息是日常寒暄/無明確主題 -> 回傳 null
    """
    existing_str = "、".join(existing_names) if existing_names else "（無）"
    prompt = (
        "你是一個對話主題標籤分析器。\n"
        f"既有主題標籤：{existing_str}\n"
        f"使用者訊息：{user_msg}\n\n"
        "任務：抽出這則訊息的「主題標籤」——一個簡短的『名詞性主題短語』。\n"
        "規則：\n"
        "1. 若主題符合某個既有標籤 -> 只回傳那個標籤的原文。\n"
        "2. 若有新主題 -> 回傳 2~10 字的繁體中文『名詞短語』標籤"
        "（像書籤名稱，例如「微積分數值積分」「找實習」「OpenStack 部署」）。\n"
        "3. 標籤必須是名詞短語，不可是整句話、問句、或描述動作的句子。\n"
        "4. 不可包含標點符號（句號、問號、逗號、驚嘆號等）。\n"
        "5. 若是日常寒暄、無明確主題、或只是在問問題 -> 只回傳 null。\n"
        "錯誤示範（這些都要回 null 或重新濃縮成名詞）："
        "「詢問狀態轉移的概念」「測試情緒狀態的流程」「我想知道怎麼做」。\n"
        "只輸出標籤文字或 null，不要任何解釋。"
    )

    # 1. 嘗試 Gemma 邊緣
    if gemma is not None:
        try:
            raw = await gemma.generate_text(prompt)
            result = _sanitize_topic(raw)
            if result:
                logger.debug("[M4.6] Gemma topic extracted: %s", result)
                return result
        except Exception as e:
            logger.debug("[M4.6] Gemma topic extraction failed: %s", e)

    # 2. Fallback 到 Cloud LLM
    try:
        from m4_1_router.routing_engine import (
            PERSONA_MODEL_FALLBACK,
            RateLimitError,
            ServiceUnavailableError,
            get_cloud_llm_client,
        )
        client = get_cloud_llm_client(PERSONA_MODEL_FALLBACK)
        raw = await client.complete(prompt, max_output_tokens=30, temperature=0.1)
        result = _sanitize_topic(raw)
        if result:
            logger.debug("[M4.6] Cloud LLM topic extracted: %s", result)
            return result
        return None
    except (RateLimitError, ServiceUnavailableError):
        logger.debug("[M4.6] Cloud LLM topic extraction rate limited")
        return None
    except Exception as e:
        logger.debug("[M4.6] Cloud LLM topic extraction failed: %s", e)
        return None


# 標籤過濾：拒絕整句/問句/含標點的輸出
_TOPIC_PUNCT = set("。，、！？；：「」『』,.!?;:\"'()（）")
_SENTENCE_MARKERS = ("嗎", "呢", "嗎？", "如何", "怎麼", "為什麼", "請問", "我想知道", "說明", "解釋", "詢問")
_TOPIC_MAX_LEN = 12


def _sanitize_topic(raw: str | None) -> str | None:
    """
    [測試回饋] 收緊 LLM 標籤輸出：拒絕 null / 整句 / 問句 / 含標點 / 過長。
    回傳乾淨名詞短語或 None。
    """
    if not raw:
        return None
    result = raw.strip().strip('"').strip("'").strip("「」『』")
    if not result or result.lower() == "null":
        return None
    # 長度限制（名詞短語應簡短）
    if not (2 <= len(result) <= _TOPIC_MAX_LEN):
        return None
    # 含標點 → 多半是整句，拒絕
    if any(ch in _TOPIC_PUNCT for ch in result):
        return None
    # 問句/動作描述句特徵 → 拒絕
    if any(marker in result for marker in _SENTENCE_MARKERS):
        return None
    return result


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

async def detect_and_upsert_project(
    user_msg: str,
    role_id: str,
    db: Any,
    eguard: Any,
    sse: Any,
    gemma: Any | None = None,
    current_active_project: str | None = None,
    source: str = "chat",
    expert_name: str | None = None,
    intention: str | None = None,
) -> str | None:
    """
    [SPEC §9] 主題標籤偵測三段式流程：
      1. Regex 快速路徑
      2. LLM 語意分析（Gemma -> Cloud fallback）
      3. Eguard 過濾 -> 模糊去重 -> upsert -> SSE

    [測試回饋] current_active_project：此 thread 目前活躍專案。
      - 偵測結果與當前活躍專案相同 -> 不發事件、不建新（回傳該名稱）
      - 切換到既有專案 -> 發 PROJECT_SWITCHED
      - 全新主題 -> 建立並發 PROJECT_CREATED
    source / expert_name / intention 併入 SSE payload，供前端語意化顯示。
    回傳最終標籤名稱（新建或匹配）或 None。
    """
    # 1. 拉既有標籤
    try:
        projects = await db.fetch_all(
            "SELECT name FROM role_projects WHERE role_id = :rid",
            {"rid": role_id}
        )
        existing_names = [p["name"] for p in projects]
    except Exception as e:
        logger.warning("[M4.6] Failed to fetch existing projects: %s", e)
        existing_names = []

    # 2. Regex 快速路徑
    candidate = regex_extract_project(user_msg)

    # 3. 若 Regex 無結果，先對既有標籤做模糊比對（使用者重提舊主題）
    if not candidate:
        rematch = fuzzy_match(user_msg, existing_names)
        if rematch:
            candidate = rematch
        else:
            # 再嘗試 LLM 語意分析
            candidate = await _llm_extract_topic(user_msg, existing_names, gemma)

    if not candidate:
        return None

    # 4. [RISK-12] Eguard PII 過濾
    try:
        sanitized = eguard.mask_pii(candidate)
        candidate = sanitized.sanitized_text.strip()
    except Exception:
        pass
    if not candidate or "[REDACTED" in candidate:
        return None

    # 5. 模糊去重：對齊到既有標籤名稱（若存在）
    matched = fuzzy_match(candidate, existing_names)
    final_name = matched or candidate
    is_new = matched is None

    # 6. [測試回饋] 與當前活躍專案比對：相同則不發事件、不建新
    if current_active_project and fuzzy_match(final_name, [current_active_project]):
        return final_name

    # 7. 全新主題才寫入 role_projects
    if is_new:
        import uuid
        try:
            await db.execute(
                "INSERT INTO role_projects (id, role_id, name, inferred_by_ai) "
                "VALUES (:id, :rid, :name, 1)",
                {"id": str(uuid.uuid4()), "rid": role_id, "name": final_name}
            )
            logger.info("[M4.6] New topic tag created: '%s' for role %s", final_name, role_id)
        except Exception as e:
            logger.warning("[M4.6] Failed to insert project tag: %s", e)
            return None

    # 8. SSE：新建 → PROJECT_CREATED；切換到既有 → PROJECT_SWITCHED
    if hasattr(sse, "emit"):
        event_type = "PROJECT_CREATED" if is_new else "PROJECT_SWITCHED"
        payload = {
            "project_name": final_name,
            "role_id": role_id,
            "source": source,
        }
        if expert_name:
            payload["expert_name"] = expert_name
        if intention:
            payload["intention"] = intention
        try:
            await sse.emit(event_type, payload)
        except Exception:
            pass

    return final_name
