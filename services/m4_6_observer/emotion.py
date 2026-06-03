"""
M4.6 -- 情緒萃取 (Emotion Detection)

實作 SPEC: docs/modules/M4_6_observer_agent_SPEC.md §9 (決議：進行情緒萃取)
研究依據: [R02 §動態狀態解碼] 從對話表面語氣推斷當下情緒標籤

偵測到的情緒寫入 chat_transcripts metadata，供 Persona 動態調整語氣 / 觸發反思套問。
規則層作為快速路徑；本地 Gemma 可作為語意回退（SPEC §9）。
"""
from __future__ import annotations

# 情緒關鍵字 -> 標籤。順序代表優先序（焦慮的時間壓力訊號優先於泛化挫折）。
_EMOTION_RULES: list[tuple[str, list[str]]] = [
    ("anxious", ["緊張", "焦慮", "好慌", "壓力好大", "怕來不及", "睡不著"]),
    ("frustrated", ["寫不出來", "做不出來", "想放棄", "好煩", "卡住", "弄不好", "搞不定"]),
    ("sad", ["難過", "沮喪", "失落", "想哭", "好累"]),
    ("confident", ["搞定了", "終於懂了", "很有信心", "沒問題", "我可以"]),
    ("confused", ["不知道怎麼", "好亂", "搞不懂", "迷茫", "不確定"]),
]


def detect_emotion(text: str) -> str | None:
    """
    規則層情緒偵測。無明確情緒訊號 -> None（中性，不強加標籤）。
    """
    for label, keywords in _EMOTION_RULES:
        if any(kw in text for kw in keywords):
            return label
    return None
