"""
M4.2.4 -- State Inversion & REMT 隱性狀態注入

SPEC: docs/modules/M4_2_persona_state_machine_SPEC.md §7.4
Research: [R02: §REMT] 即時可編輯記憶拓樸上下文注入
          [R05: §合成心理病理學] 主動展現弱點安全邊界
Risk: RISK-03 (焦慮鏡像禁止，強制 State Inversion)
     RISK-06 (隱性狀態以 role_id 隔離)
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ImplicitStateLabel(str, Enum):
    """隱性狀態標籤（M4.8 推論輸出）。"""
    ANXIETY = "anxiety"
    AVOIDANCE = "avoidance"
    FLOW = "flow"
    FRUSTRATION = "frustration"
    NEUTRAL = "neutral"
    BOREDOM = "boredom"


@dataclass
class PersonaContext:
    """注入 Persona 系統提示詞的情境結構。"""
    persona_tone: str
    system_prompt_fragment: str
    challenge_level: str  # "gentle" | "probing" | "stretch"
    role_id: str = "default"


# [RISK-03] STATE_RESPONSE_MAP — 強制 State Inversion，禁止鏡像
# anxiety → calm (反轉)，avoidance → probing (引導)，flow → stretch (推進)
STATE_RESPONSE_MAP: dict[ImplicitStateLabel, dict] = {
    ImplicitStateLabel.ANXIETY: {
        "persona_tone": "calm",
        "system_prompt_fragment": (
            "使用者目前處於高壓狀態，請以平靜、穩定的語氣回應，"
            "避免使用催促或評判性語言，先確認對方的感受再提供建議。"
        ),
        "challenge_level": "gentle",
    },
    ImplicitStateLabel.AVOIDANCE: {
        "persona_tone": "probing",
        "system_prompt_fragment": (
            "使用者目前有些迴避，請用好奇、開放的提問引導對方思考，"
            "著重探索與理解，不評判也不施壓，讓對方自然說出想法。"
        ),
        "challenge_level": "probing",
    },
    ImplicitStateLabel.FLOW: {
        "persona_tone": "energetic",
        "system_prompt_fragment": (
            "使用者目前進入心流狀態，請提供具挑戰性的問題或任務，"
            "推進學習深度，保持高度參與感。"
        ),
        "challenge_level": "stretch",
    },
    ImplicitStateLabel.FRUSTRATION: {
        "persona_tone": "empathetic",
        "system_prompt_fragment": (
            "使用者目前感到挫折，請先認可其努力，"
            "再以小步驟引導重建信心，避免複雜說明。"
        ),
        "challenge_level": "gentle",
    },
    ImplicitStateLabel.NEUTRAL: {
        "persona_tone": "authoritative",
        "system_prompt_fragment": (
            "使用者目前狀態中性，按正常節奏進行對話。"
        ),
        "challenge_level": "probing",
    },
    ImplicitStateLabel.BOREDOM: {
        "persona_tone": "playful",
        "system_prompt_fragment": (
            "使用者可能感到無聊，請提高對話趣味性，"
            "嘗試以故事或類比方式吸引注意力。"
        ),
        "challenge_level": "stretch",
    },
}


def build_persona_context(
    label: ImplicitStateLabel,
    role_id: str = "default",
    user_id: str = "",
) -> PersonaContext:
    """
    [R02 §REMT] 根據隱性狀態標籤建構 PersonaContext。
    [RISK-03] 強制 State Inversion：焦慮 → calm，不可鏡像。
    [RISK-06] role_id 綁定，確保跨角色不共用狀態。
    """
    config = STATE_RESPONSE_MAP[label]
    return PersonaContext(
        persona_tone=config["persona_tone"],
        system_prompt_fragment=config["system_prompt_fragment"],
        challenge_level=config["challenge_level"],
        role_id=role_id,
    )
