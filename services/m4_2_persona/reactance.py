"""
M4.2.2 -- 阻抗偵測器 (Reactance Detection)

SPEC: docs/modules/M4_2_persona_state_machine_SPEC.md §7.3
Research: [R03: §3.1 心理阻抗理論] 混合策略：規則層 + ML 層補充
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class ReactanceScore:
    score: float   # 0.0 ~ 1.0
    source: str    # "rule" | "hybrid" | "ml"


# [R03 §3.1] 防衛語句正則模式
_DEFENSIVE_PATTERNS = [
    r"你(根本)?不懂(我|我說的|我的意思)",
    r"我(說了|說過|已經說了)",
    r"不要再說(了)?",
    r"你(在|是在)?說什麼",
    r"你不瞭解",
    r"算了(啦?|吧?)",
    r"隨便(你|啦)",
    r"我不想(聽|討論|說)",
    r"沒有用",
    r"你(根本|根本就|就是)不(懂|明白|理解)",
    r"跟你說(不清楚|沒用)",
    r"你(怎麼|為什麼)(這樣|那樣)(說|做)",
    r"leave me alone",
    r"stop (telling|saying|lecturing)",
    r"you don'?t understand",
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in _DEFENSIVE_PATTERNS]


def rule_based_reactance(user_msg: str) -> ReactanceScore:
    """
    [R03 §3.1] 規則層阻抗偵測（永遠執行）。

    高分 (>0.9) 直接回傳；中分 (0.3~0.9) 留給 ML 層補充。
    """
    hit_count = sum(1 for p in _COMPILED if p.search(user_msg))

    if hit_count == 0:
        # 輕量語調分析：感嘆號、否定詞密度
        # [W9.5] 修補：否定詞 < 3 個不計入（排除「不是A也不是B，其實是C」等修辭場景）
        negations = len(re.findall(r"(不|沒|別|不要|沒有)", user_msg))
        exclamations = user_msg.count("！") + user_msg.count("!")
        neg_score = (negations * 0.08) if negations >= 3 else 0.0
        soft_score = min(neg_score + exclamations * 0.05, 0.29)
        return ReactanceScore(score=soft_score, source="rule")

    # 第一個命中 0.75，每增一個 +0.10，上限 0.95
    score = min(0.75 + (hit_count - 1) * 0.10, 0.95)
    return ReactanceScore(score=score, source="rule")


async def detect_reactance(user_msg: str) -> ReactanceScore:
    """
    [R03 §3.1] 混合阻抗偵測：規則層 + ML 層（Gemma 邊緣）補充。

    規則 > 0.9 → 直接回傳。
    規則 0.3 ~ 0.9 → 呼叫 Gemma 邊緣做情感分類（降級模式下直接回傳規則分）。
    規則 < 0.3 → 直接回傳 (無阻抗)。
    """
    rule_score = rule_based_reactance(user_msg)

    if rule_score.score > 0.9:
        return rule_score

    if 0.3 < rule_score.score < 0.9:
        try:
            from m2_2_gemma_edge.client import GemmaEdgeClient  # type: ignore
            client = GemmaEdgeClient()
            ml_score = await client.classify_reactance(user_msg)
            return ReactanceScore(score=ml_score, source="hybrid")
        except Exception:
            # Gemma 邊緣不可用時退化為規則層
            return ReactanceScore(score=rule_score.score, source="rule")

    return rule_score
