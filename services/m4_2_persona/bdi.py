"""
M4.2.1 -- BDI Reconciler (Belief-Desire-Intention)

SPEC: docs/modules/M4_2_persona_state_machine_SPEC.md §7.1
Research: [R09: §6.2 BDI 框架] 信念-渴望-意圖建模
Risk: RISK-08 (belief/desire 矛盾不可直接拼接給 Persona)
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class BDIInput:
    belief: str   # 使用者當前相信的能力/情境
    desire: str   # 使用者想達成的目標


@dataclass
class BDIOutput:
    intention: str  # 已 reconcile 的行動意圖，可安全注入 Persona


# 橋接詞模板，用於 belief/desire 相悖時生成漸進型 intention
_BRIDGE_TEMPLATES = [
    "先從{gap_start}開始，逐步達到{goal}",
    "從{gap_start}的基礎開始，一步步完成{goal}",
    "首先掌握{gap_start}，再挑戰{goal}",
]

# 判斷 belief 是否包含「不懂/不會/不熟」等能力缺口詞
_GAP_PATTERNS = re.compile(
    r"不(懂|會|熟|清楚|了解|明白)|缺乏|沒學過|初學|從沒|從未"
)


def reconcile_bdi(inp: BDIInput) -> BDIOutput:
    """
    [R09 §6.2] 將 belief + desire 整合為可安全注入 Persona 的 intention。

    [RISK-08] 禁止直接拼接 belief + desire；
    矛盾時生成橋接型漸進意圖，一致時生成直接行動意圖。
    """
    if not inp.belief:
        # belief 為空 → intention 直接行動化 desire
        return BDIOutput(intention=f"協助完成：{inp.desire}")

    has_gap = bool(_GAP_PATTERNS.search(inp.belief))

    if has_gap:
        # [RISK-08] belief 有能力缺口，desire 超出當前能力 → 橋接意圖
        # 從 belief 提取缺口關鍵詞作為起點
        gap_keyword = _extract_gap_keyword(inp.belief)
        template = _BRIDGE_TEMPLATES[0]
        intention = template.format(gap_start=gap_keyword, goal=inp.desire)
        return BDIOutput(intention=intention)

    # belief 與 desire 一致 → 直接行動意圖
    return BDIOutput(intention=f"在{inp.belief}的基礎上完成{inp.desire}")


def _extract_gap_keyword(belief: str) -> str:
    """從 belief 文字提取能力缺口的主題關鍵詞。"""
    # 簡單取第一個名詞片段（2~6 字的中文詞）
    candidates = re.findall(r"[一-鿿]{2,6}", belief)
    # 過濾掉否定詞本身
    stop = {"不懂", "不會", "不熟", "不清楚", "不了解", "不明白", "缺乏", "沒學過"}
    for c in candidates:
        if c not in stop:
            return c
    return belief[:6] if belief else "基礎"
