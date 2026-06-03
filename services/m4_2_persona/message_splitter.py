"""
M4.2.4.1 -- 多訊息分割器 (Message Splitter)

SPEC: docs/modules/M4_2_persona_state_machine_SPEC.md §7.4.1
Research: [R05 §跨越恐怖谷] 模擬真人分段發言，增強治療同盟真實感
Note: M4.4 套問的 ElicitationPromptFragment 已預先分割，不經過此分割器
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

# 語意斷句主要分割點
SPLIT_DELIMITERS = {"。", "？", "！", "\n\n"}

# 回應長度分級閾值 (SPEC §7.4.1)
SHORT_THRESHOLD = 60    # < 60 字 → 單一氣泡
LONG_THRESHOLD = 200    # > 200 字 → 3~4 個氣泡

# 延遲範圍 (ms)
MIN_DELAY_MS = 300
MAX_DELAY_MS = 1500

# 最小段落長度：過短的片段合併到下一段
MIN_SEGMENT_LEN = 30

# 最小觸發分割的字符數（確保當前段有實質內容再切）
MIN_SPLIT_LEN = 15


@dataclass
class SplitMessage:
    """單一訊息氣泡。"""
    content: str
    delay_ms: int  # 與前一個訊息的間隔 (ms)，首個訊息為 0


@dataclass
class MessageSequence:
    """多訊息序列，由前端逐一渲染。"""
    messages: list[SplitMessage] = field(default_factory=list)

    @property
    def bubble_count(self) -> int:
        return len(self.messages)

    @property
    def total_text(self) -> str:
        return "".join(m.content for m in self.messages)


def split_response(response: str, max_bubbles: int = 4) -> MessageSequence:
    """
    [R05 §跨越恐怖谷] 將 Persona 完整回應拆分為 2~4 個獨立訊息氣泡。

    規則（SPEC §7.4.1）：
    1. 短回應 (< 60 字) → 不拆分，單一氣泡
    2. 中等回應 (60~200 字) → 拆為 2 個氣泡
    3. 長回應 (> 200 字) → 拆為 3~4 個氣泡
    4. 每個氣泡之間插入 300~1500ms 的隨機延遲
    5. M4.4 套問的 ElicitationPromptFragment 已預先分割，不經過此函式
    """
    text = response.strip()

    # 規則 1：短回應不拆分
    if len(text) < SHORT_THRESHOLD:
        return MessageSequence(messages=[SplitMessage(content=text, delay_ms=0)])

    # 依語意斷句切割
    segments: list[str] = []
    current = ""
    i = 0
    while i < len(text):
        # 處理雙換行 (\n\n)
        if text[i] == "\n" and i + 1 < len(text) and text[i + 1] == "\n":
            current += "\n\n"
            i += 2
            if len(current.strip()) > MIN_SPLIT_LEN:
                segments.append(current.strip())
                current = ""
            continue
        current += text[i]
        if text[i] in SPLIT_DELIMITERS and len(current.strip()) > MIN_SPLIT_LEN:
            segments.append(current.strip())
            current = ""
        i += 1
    if current.strip():
        segments.append(current.strip())

    # 合併過短的段落（< MIN_SEGMENT_LEN 字）
    merged: list[str] = []
    buffer = ""
    for seg in segments:
        buffer += seg
        if len(buffer) >= MIN_SEGMENT_LEN:
            merged.append(buffer)
            buffer = ""
    if buffer:
        if merged:
            merged[-1] += buffer
        else:
            merged.append(buffer)

    # 若只有一段（無法找到斷句點），強制依長度二等分
    if len(merged) == 1 and len(text) >= SHORT_THRESHOLD:
        mid = len(text) // 2
        # 嘗試在 mid 附近找中文句號
        cut = mid
        for offset in range(30):
            if mid + offset < len(text) and text[mid + offset] in {"。", "？", "！", "\n"}:
                cut = mid + offset + 1
                break
            if mid - offset >= 0 and text[mid - offset] in {"。", "？", "！", "\n"}:
                cut = mid - offset + 1
                break
        merged = [text[:cut].strip(), text[cut:].strip()]
        merged = [m for m in merged if m]

    # 限制氣泡數量（合併最短相鄰段）
    while len(merged) > max_bubbles:
        min_idx = min(
            range(len(merged) - 1),
            key=lambda i: len(merged[i]) + len(merged[i + 1]),
        )
        merged[min_idx] = merged[min_idx] + merged[min_idx + 1]
        merged.pop(min_idx + 1)

    # 套用目標氣泡數量（依長度分級）
    target = _target_bubbles(len(text), max_bubbles)
    while len(merged) > target:
        min_idx = min(
            range(len(merged) - 1),
            key=lambda i: len(merged[i]) + len(merged[i + 1]),
        )
        merged[min_idx] = merged[min_idx] + merged[min_idx + 1]
        merged.pop(min_idx + 1)

    # 生成延遲
    messages = [
        SplitMessage(
            content=text_seg,
            delay_ms=0 if idx == 0 else random.randint(MIN_DELAY_MS, MAX_DELAY_MS),
        )
        for idx, text_seg in enumerate(merged)
    ]

    return MessageSequence(messages=messages)


def _target_bubbles(text_len: int, max_bubbles: int) -> int:
    """依回應長度決定目標氣泡數（SPEC §7.4.1 規則 2/3）。"""
    if text_len < SHORT_THRESHOLD:
        return 1
    if text_len <= LONG_THRESHOLD:
        return 2
    return min(max_bubbles, 3 + (text_len - LONG_THRESHOLD) // 200)
