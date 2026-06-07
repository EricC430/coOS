"""
M4.6 -- 專案偵測與去重 (Project Detection & Dedup)

實作 SPEC: docs/modules/M4_6_observer_agent_SPEC.md §7.2
研究依據: [R10 §代理工作流]

流程：
  1. Regex 偵測專案提及（快速路徑；LLM 為回退，SPEC §9）
  2. [RISK-12] Eguard 過濾 PII
  3. [決策] 模糊匹配既有專案，閾值 0.85（高嚴格度，防過度合併 Topic Tag）
  4. 不存在 -> 寫入 role_projects (inferred_by_ai=True)，發送 project_created SSE
[RISK-06] 所有寫入綁定當前 role_id。
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any

# 專案提及模式（中文為主）。
EXTRACT_PATTERNS: list[str] = [
    r"(?:我想做|開始做|要做|在做|想開始做)\s*(.{2,20}?)(?:的(?:期末)?(?:專案|作業|報告)|專案|作業|報告)",
    r"(.{2,20}?)(?:專案|project)\s*(?:開始|啟動|建立)",
]

# 專案語意噪音詞：避免把「微積分的期末」這類殘留助詞納入標籤。
_TRAILING_NOISE = ("的", "期末", "這個", "那個")

FUZZY_THRESHOLD = 0.85  # [決策] 高嚴格度，防 Topic Tag 過度合併


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
    """Regex 快速路徑：抽取專案候選名稱；無命中回傳 None。"""
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
    """
    回傳第一個相似度 >= threshold 的既有專案名稱；否則 None。

    以子字串包含 (substring containment) 作為高信心匹配（如「微積分作業好難」含「微積分作業」），
    並輔以 SequenceMatcher 比值處理輕微措辭差異。
    """
    for name in existing:
        if name in candidate or candidate in name:
            return name
        ratio = SequenceMatcher(None, candidate, name).ratio()
        if ratio >= threshold:
            return name
    return None


async def detect_and_upsert_project(
    user_msg: str,
    role_id: str,
    db: Any,
    eguard: Any,
    sse: Any,
) -> str | None:
    """
    偵測 -> Eguard 過濾 -> 去重 -> upsert -> SSE。回傳最終專案名稱（新建或匹配）或 None。
    """
    
    # 1. Fetch existing projects for this role
    projects = await db.fetch_all(
        "SELECT name FROM role_projects WHERE role_id = :rid",
        {"rid": role_id}
    )
    existing_names = [p["name"] for p in projects]

    candidate = regex_extract_project(user_msg)
    if not candidate:
        # 無顯式「我想做 X」句型時，仍嘗試比對訊息是否再次提及既有專案
        rematch = fuzzy_match(user_msg, existing_names)
        return rematch

    # [RISK-12] Eguard 過濾 PII
    sanitized = eguard.mask_pii(candidate)
    candidate = sanitized.sanitized_text.strip()
    if not candidate or "[REDACTED" in candidate:
        # 過濾後為空或僅剩遮蔽標記 -> 放記萃取
        return None

    matched = fuzzy_match(candidate, existing_names)
    if matched:
        return matched  # 已存在，不新建

    # 新建 [R10 §代理工作流]，預設 inferred_by_ai=True
    import uuid
    await db.execute(
        "INSERT INTO role_projects (id, role_id, name, inferred_by_ai) "
        "VALUES (:id, :rid, :name, TRUE)",
        {"id": str(uuid.uuid4()), "rid": role_id, "name": candidate}
    )
    
    # SSE emit placeholder (if sse is available)
    if hasattr(sse, "emit"):
        await sse.emit("project_created", {"project_name": candidate, "role_id": role_id})
    
    return candidate
