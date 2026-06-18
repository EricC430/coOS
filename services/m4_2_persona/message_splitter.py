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

# 回應長度分級閾值
# [測試回饋] 降低短回應門檻，讓短句即單泡；每泡目標 1~2 句，避免單泡過長
SHORT_THRESHOLD = 28    # < 28 字 → 單一氣泡（真人短訊息常 ~10-25 字）
LONG_THRESHOLD = 120    # > 120 字 → 較多氣泡

# 延遲範圍 (ms)：作為打字速度模型的上下界 clamp
MIN_DELAY_MS = 900      # 最小 0.9 秒，避免氣泡閃現
MAX_DELAY_MS = 4500     # 長句最多 4.5 秒停頓

# [測試回饋] 打字速度模型：真人讀+打的節奏，依氣泡字數估算延遲
PER_CHAR_MS = 85        # 每字約 85ms（含閱讀、思考、打字）
BASE_DELAY_MS = 800     # 基礎反應延遲（模擬收到訊息後開始打字前停頓）

# 每泡目標句數（盡量 1~2 句，不再合併回大段）
MAX_SENTENCES_PER_BUBBLE = 2

# 最小觸發分割的字符數（確保當前段有實質內容再切）
MIN_SPLIT_LEN = 8


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


def _split_sentences(text: str) -> list[str]:
    """依語意斷句切成句子（保留結尾標點），\\n\\n 也視為硬斷點。"""
    sentences: list[str] = []
    current = ""
    i = 0
    while i < len(text):
        if text[i] == "\n" and i + 1 < len(text) and text[i + 1] == "\n":
            if current.strip():
                sentences.append(current.strip())
            current = ""
            i += 2
            continue
        current += text[i]
        if text[i] in SPLIT_DELIMITERS:
            if current.strip():
                sentences.append(current.strip())
            current = ""
        i += 1
    if current.strip():
        sentences.append(current.strip())
    return sentences


def _typing_delay(content: str) -> int:
    """
    [測試回饋][R05 §跨越恐怖谷] 打字速度模型：依氣泡字數估算延遲，模擬真人讀+打。
    長泡延遲較長，短泡較短；加入隨機抖動後 clamp 至 [MIN_DELAY_MS, MAX_DELAY_MS]。
    """
    raw = BASE_DELAY_MS + len(content) * PER_CHAR_MS
    jitter = random.randint(-120, 120)
    return max(MIN_DELAY_MS, min(MAX_DELAY_MS, raw + jitter))


def split_response(response: str, max_bubbles: int = 4) -> MessageSequence:
    """
    [R05 §跨越恐怖谷] 將 Persona 完整回應拆分為多個短氣泡，模擬真人傳訊息。

    規則（v2，測試回饋調整）：
    1. 短回應 (< 28 字) → 不拆分，單一氣泡
    2. 其餘 → 依句子分組，每泡最多 2 句、盡量短；不再為了湊低泡數而合併回大段
    3. 問句獨立成泡（多問題不黏在一起）
    4. 氣泡數上限 max_bubbles；超過才合併最短相鄰段
    5. 延遲依「打字速度模型」估算（字越多延遲越長），clamp 至 300~1500ms
    6. M4.4 套問的 ElicitationPromptFragment 已預先分割，不經過此函式
    """
    text = response.strip()

    # 規則 1：短回應不拆分
    if len(text) < SHORT_THRESHOLD:
        return MessageSequence(messages=[SplitMessage(content=text, delay_ms=0)])

    sentences = _split_sentences(text)
    if not sentences:
        return MessageSequence(messages=[SplitMessage(content=text, delay_ms=0)])

    # 依句子分組：每泡最多 MAX_SENTENCES_PER_BUBBLE 句；問句單獨成泡
    bubbles: list[str] = []
    group: list[str] = []
    for sent in sentences:
        is_question = sent.endswith("？") or sent.endswith("?")
        if is_question and group:
            # 先收掉目前累積的群組，讓問句獨立
            bubbles.append("".join(group))
            group = []
        group.append(sent)
        if is_question or len(group) >= MAX_SENTENCES_PER_BUBBLE:
            bubbles.append("".join(group))
            group = []
    if group:
        bubbles.append("".join(group))

    # 合併極短的開頭碎片（< MIN_SPLIT_LEN）到下一泡，避免出現一兩個字的氣泡
    cleaned: list[str] = []
    for b in bubbles:
        if cleaned and len(cleaned[-1]) < MIN_SPLIT_LEN:
            cleaned[-1] += b
        else:
            cleaned.append(b)
    bubbles = cleaned or bubbles

    # 若仍只有一段（無斷句點的長文），依長度二等分
    if len(bubbles) == 1 and len(text) >= SHORT_THRESHOLD * 2:
        mid = len(text) // 2
        cut = mid
        for offset in range(30):
            if mid + offset < len(text) and text[mid + offset] in {"。", "？", "！", "\n", "，"}:
                cut = mid + offset + 1
                break
            if mid - offset >= 0 and text[mid - offset] in {"。", "？", "！", "\n", "，"}:
                cut = mid - offset + 1
                break
        bubbles = [b for b in (text[:cut].strip(), text[cut:].strip()) if b]

    # 上限：超過 max_bubbles 才合併最短相鄰段
    while len(bubbles) > max_bubbles:
        min_idx = min(
            range(len(bubbles) - 1),
            key=lambda i: len(bubbles[i]) + len(bubbles[i + 1]),
        )
        bubbles[min_idx] = bubbles[min_idx] + bubbles[min_idx + 1]
        bubbles.pop(min_idx + 1)

    messages = [
        SplitMessage(
            content=seg,
            delay_ms=0 if idx == 0 else _typing_delay(seg),
        )
        for idx, seg in enumerate(bubbles)
    ]
    return MessageSequence(messages=messages)
