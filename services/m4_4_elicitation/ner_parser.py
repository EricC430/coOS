"""
M4.4.2 -- NER + Regex 時間解析器

實作 SPEC: docs/modules/M4_4_natural_elicitation_draft_SPEC.md §7.2
研究依據: [R10 §代理工作流] 從聊天抽取結構化時間

反模式 (SPEC §8): 無法確認時間時回傳 None，絕不猜測 -- 錯誤耗時會導致信任崩潰。
"""
from __future__ import annotations

import inspect
import re
from dataclasses import dataclass
from typing import Any

# 中文數字 -> 阿拉伯數字（涵蓋 1~10，足以表達常見耗時陳述）。
_CN_NUM = {
    "一": 1, "兩": 2, "二": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
}
# 數量子模式：ASCII 數字或單一中文數字。
_QTY = r"(\d+|[一兩二三四五六七八九十])"


def _qty(token: str) -> int:
    """將數量 token（阿拉伯或中文）轉為整數。"""
    return int(token) if token.isdigit() else _CN_NUM.get(token, 0)


@dataclass
class DurationResult:
    minutes: int
    raw_text: str
    confidence: float  # 0.0~1.0


# 中英文時間模式。順序重要：較具體的「N 個半小時」必須先於「N 小時」匹配。
# 每個 entry: (pattern, calc, exclusive)
#   exclusive=True 表示一旦命中即停止後續累加（避免重複計入）。
DURATION_PATTERNS: list[tuple[str, Any, bool]] = [
    # 「N 個半小時」= N 小時又半 = N*60 + 30（例：三個半小時 = 210 分）
    (rf"{_QTY}\s*個半\s*小時", lambda m: _qty(m.group(1)) * 60 + 30, True),
    (r"一個\s*(?:下午|上午|早上|晚上)", lambda _m: 240, True),  # 預設半天 4h
    (r"半\s*(?:小時|hour)", lambda _m: 30, True),
    (rf"{_QTY}\s*(?:小時|hours?|hrs?)", lambda m: _qty(m.group(1)) * 60, False),
    (rf"{_QTY}\s*(?:分鐘|minutes?|mins?)", lambda m: _qty(m.group(1)), False),
]


def extract_duration(text: str) -> DurationResult | None:
    """
    從自然語言抽取時間跨度（分鐘）。

    無法辨識 -> None（不猜測）。
    """
    total = 0
    matched = False
    for pattern, calc, exclusive in DURATION_PATTERNS:
        match = re.search(pattern, text)
        if match:
            total += calc(match)
            matched = True
            if exclusive:
                break
    if not matched:
        return None
    return DurationResult(minutes=total, raw_text=text, confidence=0.8)


async def extract_and_store(
    db: Any,
    thread_id: str,
    user_msg: str,
    role_id: str,
    project: str,
) -> DurationResult | None:
    """
    解析使用者回覆並寫入任務暫存槽 (task_slot)，供 M4.4.3 深夜排程拼裝草稿。

    [RISK-06] task_slot 綁定 role_id；解析失敗則不寫入，避免污染草稿。
    """
    result = extract_duration(user_msg)
    if result is None:
        return None

    slot = {
        "thread_id": thread_id,
        "role_id": role_id,
        "project": project,
        "duration_minutes": result.minutes,
    }

    # 支援注入式假 DB（測試）與真實 DB 介面兩種。
    if hasattr(db, "task_slots"):
        db.task_slots[thread_id] = slot
    upsert = getattr(db, "upsert_task_slot", None)
    if inspect.iscoroutinefunction(upsert):
        await upsert(slot)

    return result
