"""
M4.2.1 -- 系統提示詞工程 (BDI 結構)

SPEC: docs/modules/M4_2_persona_state_machine_SPEC.md §7.1
Research: [R03 §1 微觀認知架構] BDI 結構提示詞工程
          [R05 §治療同盟] 過往經歷敘事增強信任感
Risk: RISK-06 (提示詞以 role_id 隔離，不跨角色共用)
Note: Persona 人設由 M4.1 配對流程的 LLM 生成，此模組負責格式化注入。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PersonaConfig:
    """從 M6.2 ai_experts 表讀取的 Persona 設定。"""
    name: str
    personality_prompt: str
    backstory: str
    tone_default: str
    trust_level: float = 0.5


# 禁用的通用 AI 語（[R03 §1.1] 禁止出現）
_FORBIDDEN_PHRASES = [
    "我是 AI",
    "我是人工智慧",
    "作為 AI",
    "我會盡力協助",
    "我只是一個語言模型",
    "身為 AI",
]

# [R03 §1] 角色情境說明模板（依 role_id 差異化）
_ROLE_CONTEXT_TEMPLATES: dict[str, str] = {
    "role_csie": "你目前在協助資工系的學習情境，專注在程式設計、演算法與系統課題。",
    "role_family": "你目前在家庭生活情境中陪伴使用者，關注生活品質與人際關係。",
    "default": "你目前在協助使用者的個人成長與學習。",
}


def build_system_prompt(
    config: PersonaConfig,
    role_id: str = "default",
    user_id: str = "",
) -> str:
    """
    [R03 §1] 建構 BDI 結構的 Persona 系統提示詞。

    [RISK-06] 以 role_id 差異化角色情境描述，確保跨角色隔離。
    [R05] 嵌入過往經歷敘事強化治療同盟。
    禁止包含通用 AI 語（見 _FORBIDDEN_PHRASES）。
    """
    role_context = _ROLE_CONTEXT_TEMPLATES.get(role_id, _ROLE_CONTEXT_TEMPLATES["default"])

    prompt = (
        f"{config.personality_prompt}\n\n"
        f"背景：{config.backstory}\n\n"
        f"當前情境：{role_context}\n\n"
        "【行為守則】\n"
        "- 維持你的個性與過往經歷，在任何對話中保持一致。\n"
        "- 不使用通用客服語（如「很抱歉」「感謝您的耐心」）。\n"
        "- 用你真實的語氣表達，可以有情緒，但不失去邊界感。\n"
        "- 同角色的其他專家透過 AI 登錄系統共享進度，你可以提及。\n"
    )

    # 驗證不含禁用語（防禦性）
    for phrase in _FORBIDDEN_PHRASES:
        if phrase in prompt:
            prompt = prompt.replace(phrase, "")

    return prompt.strip()
