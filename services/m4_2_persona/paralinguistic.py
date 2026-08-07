"""
M4.2.4 -- 副語言瑕疵注入器

SPEC: docs/modules/M4_2_persona_state_machine_SPEC.md §7.4
Research: [R05: §跨越恐怖谷] 填充詞與自我修正比例控制
          [R05: §諂媚效應] 比例上限 15%，過量破壞治療同盟
Risk: RISK-03 (填充詞注入不鏡像使用者情緒，僅影響表達風格)
"""
from __future__ import annotations

import random

# [R05 §跨越恐怖谷] 預設填充詞庫（PersonaCard 未提供時 fallback）
DEFAULT_FILLER_WORDS = ["嗯...", "讓我想想", "等等，我重新想一下", "啊對了"]

# [R05 §跨越恐怖谷] 自我修正片語
# 只使用「可獨立成句」的修正語，避免注入後接空白或語意斷裂
SELF_CORRECTIONS = [
    "或者換個角度想，",
    "嗯不對，我換個說法。",
    "等等，我重新整理一下。",
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


def inject_paralinguistic_sync(
    response: str,
    trust_level: float = 0.5,
    persona_fillers: list[str] | None = None,
) -> str:
    """
    [R05 §跨越恐怖谷] 同步版本（測試用）。

    根據 trust_level 動態決定填充詞注入率與自我修正率。
    persona_fillers: 從 PersonaCard.speech_profile.fillers 傳入，實現每位專家獨立語助詞。
    """
    filler_rate = _compute_filler_rate(trust_level)
    fillers = persona_fillers if persona_fillers else DEFAULT_FILLER_WORDS

    # 注入填充詞（句首）
    if random.random() < filler_rate:
        filler = random.choice(fillers)
        response = f"{filler} {response}"

    # [R05] 自我修正注入（僅對長回應，與 trust_level 負相關）
    # 修正語插在句號後，作為銜接下一句的過渡詞，而非懸空片段
    correction_rate = 0.05 * (1.5 - trust_level)
    if len(response) > 100 and random.random() < correction_rate:
        position = response.find("。", len(response) // 3)
        if position > 0 and position < len(response) - 2:
            correction = random.choice(SELF_CORRECTIONS)
            response = (
                response[: position + 1]
                + correction
                + response[position + 1 :].lstrip()
            )

    return response


async def inject_paralinguistic(
    response: str,
    trust_level: float = 0.5,
    persona_fillers: list[str] | None = None,
) -> str:
    """
    [R05 §跨越恐怖谷] 非同步版本（LangGraph 節點使用）。
    """
    return inject_paralinguistic_sync(
        response, trust_level=trust_level, persona_fillers=persona_fillers,
    )
