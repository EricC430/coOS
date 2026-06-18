"""
M4.2.1 -- 系統提示詞工程 (BDI 結構)

SPEC: docs/modules/M4_2_persona_state_machine_SPEC.md §7.1 / §7.1.1
Research: [R03 §1 微觀認知架構] BDI 結構提示詞工程
          [R05 §治療同盟] 過往經歷敘事增強信任感
Risk: RISK-06 (提示詞以 role_id 隔離，不跨角色共用)
v1.2: 新增 [記憶區塊] 注入 (active_goals + upcoming_promises，按 persona_id 篩選)
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
    persona_card: dict | None = None  # [R03 §1] 結構化人設卡（speech_profile / stances / taboos）


# 禁用的通用 AI 語（[R03 §1.1] 禁止出現）
_FORBIDDEN_PHRASES = [
    "我是 AI",
    "我是人工智慧",
    "作為 AI",
    "我會盡力協助",
    "我只是一個語言模型",
    "身為 AI",
]

# [R05 §治療同盟] personality_prompt 過長會壓垮回覆節奏感，截斷上限（字元）
_PERSONALITY_PROMPT_MAX = 280


def _truncate_personality(text: str) -> str:
    """
    [R05 §治療同盟] 過長人設描述（DB 中常 800+ 字）會讓 LLM 模仿其冗長語氣，
    破壞「短句、口語、像真人」的回覆節奏。截斷至核心段落，優先保留前段
    （identity + 最關鍵性格句通常在開頭）。
    """
    text = (text or "").strip()
    if len(text) <= _PERSONALITY_PROMPT_MAX:
        return text
    # 在上限附近找句號斷點，避免硬切句子中間
    cut = _PERSONALITY_PROMPT_MAX
    for offset in range(40):
        if cut - offset >= 0 and text[cut - offset] in {"。", "！", "？", "\n"}:
            cut = cut - offset + 1
            break
    return text[:cut].strip()


def _build_speech_style_block(persona_card: dict | None) -> str:
    """
    [R03 §1 微觀認知架構][R05 §跨越恐怖谷] 從 persona_card.speech_profile 注入說話風格。
    口頭禪/quirks 明確標註「偶爾使用」，避免每則回覆都冒出口頭禪（測試回饋：太頻繁反而不像人）。
    """
    if not persona_card:
        return ""
    sp = persona_card.get("speech_profile", {}) or {}
    parts: list[str] = []

    sentence_length = sp.get("sentence_length")
    if sentence_length == "short":
        parts.append("- 你習慣說短句，一次不會講太多。")
    elif sentence_length == "long":
        parts.append("- 你偶爾會講得稍長，但仍口語自然。")

    fillers = sp.get("fillers") or []
    if fillers:
        parts.append(f"- 偶爾（非每句）自然帶入語助詞：{ '、'.join(fillers[:3]) }。")

    catchphrase = sp.get("口頭禪") or sp.get("catchphrase")
    if catchphrase:
        parts.append(f"- 你有句口頭禪「{catchphrase}」，但只在真正貼切時偶爾用，不要每次都說。")

    quirks = sp.get("quirks") or []
    if quirks:
        parts.append(f"- 說話小習慣（偶爾展現）：{ '；'.join(quirks[:3]) }。")

    if not parts:
        return ""
    return "[說話風格]\n" + "\n".join(parts) + "\n\n"

# [R03 §1] 角色情境說明模板（依 role_id 差異化）
_ROLE_CONTEXT_TEMPLATES: dict[str, str] = {
    "role_csie": "你目前在協助資工系的學習情境，專注在程式設計、演算法與系統課題。",
    "role_family": "你目前在家庭生活情境中陪伴使用者，關注生活品質與人際關係。",
    "default": "你目前在協助使用者的個人成長與學習。",
}


def _build_memory_block(
    persona_id: str,
    active_goals: list[dict],
    upcoming_promises: list[dict],
    episodic_memories: list[dict] | None = None,
    last_session_summary: str | None = None,
) -> str:
    """
    [v1.2 §7.1.1] 組裝 [記憶區塊] 段落（<= 350 tokens）。
    依 persona_id 篩選，只注入屬於此專家的目標/承諾。
    P0: episodic_memories / last_session_summary 介面預留，P2 接入真實資料。
    [R11: Park et al. §3.2] top-5 情節記憶以 importance×recency 排序注入。
    [R15: MemGPT §Memory Management] 總 token 預算 <= 350。
    """
    my_goals = [g for g in active_goals if str(g.get("persona_id", "")) == persona_id]
    my_promises = [p for p in upcoming_promises if str(p.get("persona_id", "")) == persona_id]

    parts: list[str] = []

    if my_goals:
        goals_lines = "\n".join(
            f"  - {g['title']}"
            f"（確立於 {g.get('created_at', '未知')}, "
            f"進度 {int(g.get('progress', 0) * 100)}%）"
            for g in my_goals[:3]
        )
        parts.append(f"[核心目標]\n{goals_lines}")

    if my_promises:
        promises_lines = "\n".join(
            f"  - {p['text']}（deadline: {p.get('deadline', '未定')}）"
            for p in my_promises[:5]
        )
        parts.append(f"[即將到期的承諾]\n{promises_lines}")

    # [R11: Park et al. §3.2] P0 介面預留，P2 接入 PersonaMemoryStore.retrieve_top_k()
    if episodic_memories:
        mem_lines = "\n".join(
            f"  - {m.get('content', '')}"
            for m in episodic_memories[:5]
        )
        parts.append(f"[情節記憶]\n{mem_lines}")

    # [R15: MemGPT §Memory Management] 上次對話結尾摘要
    if last_session_summary:
        parts.append(f"[上次對話摘要]\n  {last_session_summary}")

    if parts:
        return "\n".join(parts)
    return "（目前無已確立的核心目標或即將到期的承諾）"


def build_system_prompt(
    config: PersonaConfig,
    role_id: str = "default",
    user_id: str = "",
    persona_id: str = "",
    active_goals: list[dict] | None = None,
    upcoming_promises: list[dict] | None = None,
    episodic_memories: list[dict] | None = None,   # [R11] P0 預留，P2 接入
    last_session_summary: str | None = None,        # [R15] P0 預留，P2 接入
    mi_directive: str | None = None,                # [W4] MI 行為策略指令
    anti_sycophancy_stances: list[dict] | None = None,  # [W3] 反談媽立場
) -> str:
    """
    [R03 §1] 建構 BDI 結構的 Persona 系統提示詞。

    [RISK-06] 以 role_id 差異化角色情境描述，確保跨角色隔離。
    [R05] 嵌入過往經歷敘事強化治療同盟。
    [v1.2 §7.1.1] 注入 [記憶區塊]：active_goals + upcoming_promises + episodic_memories。
    [R11: Park et al. §3.2] 情節記憶介面預留（P2 接入）。
    [R15: MemGPT §Memory Management] token 預算 <= 350。
    禁止包含通用 AI 語（見 _FORBIDDEN_PHRASES）。
    """
    role_context = _ROLE_CONTEXT_TEMPLATES.get(role_id, _ROLE_CONTEXT_TEMPLATES["default"])
    memory_block = _build_memory_block(
        persona_id=persona_id,
        active_goals=active_goals or [],
        upcoming_promises=upcoming_promises or [],
        episodic_memories=episodic_memories,
        last_session_summary=last_session_summary,
    )

    card = config.persona_card or {}

    # [W3] 若呼叫端未顯式傳 stances，從 persona_card 取
    if anti_sycophancy_stances is None and card.get("stances"):
        anti_sycophancy_stances = card.get("stances")

    # [R05 §治療同盟] 結構化卡（compile_to_prompt 已含節奏指令）不截斷；
    # 僅對「原始散文」personality_prompt（無 persona_card）做長度上限，避免冗長壓垮節奏。
    personality_text = config.personality_prompt
    if not card:
        personality_text = _truncate_personality(personality_text)

    prompt = (
        "[角色]\n"
        f"{personality_text}\n\n"
        f"背景：{config.backstory}\n\n"
        f"當前情境：{role_context}\n\n"
        f"{_build_speech_style_block(card)}"
        "​[記憶區塊 — AI登錄系統紀錄]\n"
        f"{memory_block}\n\n"
    )

    # [W4] MI 行為策略注入（優先序：安全 > MI > stances > 副語言）
    if mi_directive:
        prompt += f"[MI 行為策略]\n{mi_directive}\n\n"

    # [W3] 反談媽守則 [EXT-8][R03 §4]
    if anti_sycophancy_stances:
        stances_lines = "\n".join(
            f"  - {s.get('topic', '')}：{s.get('position', '')}"
            for s in anti_sycophancy_stances[:5]
        )
        prompt += (
            "[個人立場 — 反談媽守則]\n"
            f"{stances_lines}\n"
            "→ 使用者觀點與你的立場衝突時，先承認其合理處，再溫和堅持你的立場並給理由；不可立刻倒戈。\n\n"
        )

    prompt += (
        "[行為指令]\n"
        "- 若使用者尚未與你確立核心目標（[核心目標] 為空），在適當時機自然引導使用者說出"
        "「找你的最主要目的是什麼」，確立後記錄。\n"
        "- 若 [即將到期的承諾] 中有項目，以自然語氣主動提醒"
        "（如「對了，你之前提到...，進度怎麼樣了？」）。\n"
        "- 若使用者的對話內容明顯偏離 [核心目標]，溫和地提醒並引導回歸，"
        "或討論是否需要更新目標。偏離提醒每個 session 最多 1 次。\n"
        "- 這些提醒應自然融入對話，不可生硬打斷。\n"
        "- 維持你的個性與過往經歷，在任何對話中保持一致。\n"
        "- 不使用通用客服語（如「很抱歉」「感謝您的耐心」）。\n"
        "- 同角色的其他專家透過 AI 登錄系統共享進度，你可以提及。\n"
    )

    # 驗證不含禁用語（防禦性清理）；併入 persona_card.speech_profile.taboos
    taboos = []
    sp = card.get("speech_profile", {}) or {}
    if isinstance(sp.get("taboos"), list):
        taboos = sp["taboos"]
    for phrase in _FORBIDDEN_PHRASES + taboos:
        if phrase and phrase in prompt:
            prompt = prompt.replace(phrase, "")

    return prompt.strip()
