"""
M4.2.4 -- 副語言瑕疵注入器

SPEC: docs/modules/M4_2_persona_state_machine_SPEC.md §7.4
Research: [R05: §跨越恐怖谷] 填充詞與自我修正比例控制
          [R05: §諂媚效應] 比例上限 15%，過量破壞治療同盟
Risk: RISK-03 (填充詞注入不鏡像使用者情緒，僅影響表達風格)
"""
from __future__ import annotations

import random

# [R05 §跨越恐怖谷] 填充詞庫
FILLER_WORDS = ["嗯...", "讓我想想", "等等，我重新想一下", "啊對了"]

# 自我修正片語
SELF_CORRECTIONS = [
    "我剛剛說的不太精準，應該是說",
    "或者換個角度想",
    "讓我換個說法",
]

# [R05] 填充詞比例上限（超過此比例會觸發諂媚效應）
MAX_FILLER_RATE = 0.15


def _compute_filler_rate(trust_level: float) -> float:
    """
    [R05 §跨越恐怖谷] 填充詞比例與 trust_level 負相關。
    trust_level=0.5 → 8%；trust_level=0.0 → 12%；trust_level=1.0 → 4%。
    上限強制 ≤ 15%。
    """
    rate = 0.08 * (1.5 - trust_level)
    return min(rate, MAX_FILLER_RATE)


def inject_paralinguistic_sync(response: str, trust_level: float = 0.5) -> str:
    """
    [R05 §跨越恐怖谷] 同步版本（測試用）。

    根據 trust_level 動態決定填充詞注入率與自我修正率。
    """
    filler_rate = _compute_filler_rate(trust_level)

    # 注入填充詞（句首）
    if random.random() < filler_rate:
        filler = random.choice(FILLER_WORDS)
        response = f"{filler} {response}"

    # 注入自我修正（僅對長回應，同樣與 trust_level 負相關）
    correction_rate = 0.05 * (1.5 - trust_level)
    if len(response) > 100 and random.random() < correction_rate:
        position = response.find("。", len(response) // 2)
        if position > 0:
            correction = random.choice(SELF_CORRECTIONS)
            response = (
                response[: position + 1]
                + " "
                + correction
                + " "
                + response[position + 1 :]
            )

    return response


async def inject_paralinguistic(response: str, trust_level: float = 0.5) -> str:
    """
    [R05 §跨越恐怖谷] 非同步版本（LangGraph 節點使用）。
    """
    return inject_paralinguistic_sync(response, trust_level=trust_level)
