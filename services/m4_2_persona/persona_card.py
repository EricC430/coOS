"""
M4.2.1 -- PersonaCard v2 Schema + Compiler + Critic

SPEC: docs/modules/M4_2_persona_state_machine_SPEC.md
Research: [R12: Character-LLM] Experience Upload + Protective Experiences
          [R13: PersonaLLM] OCEAN 5-factor conditioning
          [R18: Sycophancy Mitigation] Anti-sycophancy stances
          [R05: Paralinguistic] speech_profile personalization
Risk: RISK-08 (stances + MI + BDI prompt priority)
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# [R13] OCEAN Big-Five valid range
BIG_FIVE_KEYS = ("O", "C", "E", "A", "N")

# [R03 ss1.1] Forbidden generic AI phrases
FORBIDDEN_PHRASES = [
    "I'm an AI", "I am an AI",
    "as an AI", "as a language model",
]

# [R13] Big Five <-> speech consistency rules
# E(Extraversion) low => should NOT have excessive exclamations
_CONSISTENCY_RULES = {
    "low_E_no_exclamation": {
        "trait": "E",
        "threshold": 0.3,
        "direction": "below",
        "forbidden_patterns": ["!", "!!", "!!!"],
        "description": "Low extraversion personas should not use excessive exclamation marks",
    },
    "high_A_no_harsh": {
        "trait": "A",
        "threshold": 0.7,
        "direction": "above",
        "forbidden_patterns": ["shut up", "stupid", "idiot"],
        "description": "High agreeableness personas should not use harsh language",
    },
}


@dataclass
class PersonaCard:
    """
    [R12][R13][R18] PersonaCard v2 structured personality schema.

    This is the single source of truth for persona definition, replacing
    raw personality_prompt prose.
    """
    # [R12] Identity
    identity: dict = field(default_factory=dict)
    # name: str, birth_year: int, education: str, career: str

    # [R13] OCEAN Big Five (0.0 - 1.0)
    big_five: dict = field(default_factory=dict)
    # {"O": 0.8, "C": 0.7, "E": 0.4, "A": 0.6, "N": 0.3}

    # Core values
    core_values: list[str] = field(default_factory=list)

    # [R05] Speech profile for paralinguistic personalization
    speech_profile: dict = field(default_factory=dict)
    # fillers: list[str], quirks: list[str], taboos: list[str]

    # [R12] Formative episodes (Experience Upload)
    formative_episodes: list[dict] = field(default_factory=list)
    # [{"age": 25, "event": "...", "impact": "..."}]

    # [R12] Knowledge boundary (Protective Experiences)
    knowledge_boundary: dict = field(default_factory=dict)
    # expert_in: list[str], casual_in: list[str], ignorant_of: list[str]

    # [R18] Anti-sycophancy stances
    stances: list[dict] = field(default_factory=list)
    # [{"topic": "...", "position": "...", "intensity": "firm|mild"}]

    # [R05][R12] Per-persona few-shot example exchanges
    # Generated at persona creation time to ground the LLM's output style
    example_exchanges: list[dict] = field(default_factory=list)
    # [{"context": "user_anxious", "user": "...", "assistant": ["...", "..."]}]


def validate_persona_card(card: PersonaCard) -> list[str]:
    """
    [R13][R18] Validate PersonaCard schema completeness and consistency.
    Returns list of error strings; empty list means valid.
    """
    errors: list[str] = []

    # Identity checks
    if not card.identity.get("name"):
        errors.append("identity.name is required")
    if not card.identity.get("career"):
        errors.append("identity.career is required for specificity")

    # Big Five checks
    for key in BIG_FIVE_KEYS:
        val = card.big_five.get(key)
        if val is None:
            errors.append(f"big_five.{key} is missing")
        elif not (0.0 <= val <= 1.0):
            errors.append(f"big_five.{key} must be 0.0-1.0, got {val}")

    # [R18] Stances minimum
    if len(card.stances) < 2:
        errors.append("stances must have at least 2 entries (anti-sycophancy)")

    # [R12] Knowledge boundary
    if not card.knowledge_boundary.get("expert_in"):
        errors.append("knowledge_boundary.expert_in is required")

    return errors


def check_big_five_speech_consistency(card: PersonaCard) -> list[str]:
    """
    [R13] Check Big Five <-> speech_profile consistency.
    E.g., E=0.2 personas should not have exclamation-heavy fillers.
    """
    warnings: list[str] = []
    fillers = card.speech_profile.get("fillers", [])
    filler_text = " ".join(fillers).lower()

    for rule_id, rule in _CONSISTENCY_RULES.items():
        trait_val = card.big_five.get(rule["trait"], 0.5)
        should_check = (
            (rule["direction"] == "below" and trait_val < rule["threshold"])
            or (rule["direction"] == "above" and trait_val > rule["threshold"])
        )
        if should_check:
            for pat in rule["forbidden_patterns"]:
                if pat.lower() in filler_text:
                    warnings.append(
                        f"[{rule_id}] {rule['description']}: "
                        f"found '{pat}' in fillers but {rule['trait']}={trait_val:.1f}"
                    )
    return warnings


def critic_check(card: PersonaCard) -> tuple[bool, list[str]]:
    """
    [R12][R13][R18] Critic pass: rubric-based validation.
    Returns (passed: bool, issues: list[str]).
    """
    issues = validate_persona_card(card)
    issues.extend(check_big_five_speech_consistency(card))

    # Check for vague identity (no specific year or workplace)
    identity_text = json.dumps(card.identity, ensure_ascii=False)
    if len(identity_text) < 40:
        issues.append("identity too vague: needs specific details (birth_year, workplace)")

    # Check for forbidden AI language in formative episodes
    for ep in card.formative_episodes:
        ep_text = json.dumps(ep, ensure_ascii=False).lower()
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in ep_text:
                issues.append(f"formative_episodes contains forbidden AI phrase: '{phrase}'")

    passed = len(issues) == 0
    return passed, issues


def compile_to_prompt(card: PersonaCard) -> str:
    """
    [R12][R13][R18][R05] 將 PersonaCard v2 編譯為繁體中文人設提示詞。

    全中文輸出，讓 LLM 從人設描述開始就在中文語境思考，
    避免英文→中文的語境切換導致語感斷裂。
    """
    sections: list[str] = []

    # --- 身份 ---
    identity = card.identity
    name = identity.get("name", "專家")
    birth_year = identity.get("birth_year", "")
    education = identity.get("education", "")
    career = identity.get("career", "")

    id_line = f"你是{name}"
    if birth_year:
        id_line += f"，{birth_year} 年生"
    if education:
        id_line += f"，{education}"
    if career:
        id_line += f"，{career}"
    id_line += "。"
    sections.append(id_line)

    # --- [R13] Big Five 性格 ---
    bf = card.big_five
    traits: list[str] = []
    if bf.get("O", 0.5) > 0.7:
        traits.append("有創造力、思想開放")
    elif bf.get("O", 0.5) < 0.3:
        traits.append("務實、偏好傳統方法")
    if bf.get("C", 0.5) > 0.7:
        traits.append("自律、有條理")
    if bf.get("E", 0.5) > 0.7:
        traits.append("外向、有活力")
    elif bf.get("E", 0.5) < 0.3:
        traits.append("內斂、深思熟慮")
    if bf.get("A", 0.5) > 0.7:
        traits.append("溫暖、善於合作")
    elif bf.get("A", 0.5) < 0.3:
        traits.append("直來直往、敢於挑戰")
    if bf.get("N", 0.5) > 0.7:
        traits.append("情感敏銳")
    elif bf.get("N", 0.5) < 0.3:
        traits.append("情緒穩定、沉著")
    if traits:
        sections.append("你的性格：" + "、".join(traits) + "。")

    # --- 核心價值 ---
    if card.core_values:
        sections.append("你最在意的事：" + "、".join(card.core_values[:5]) + "。")

    # --- [R12] 塑造你的關鍵經歷 ---
    if card.formative_episodes:
        ep_lines = []
        for ep in card.formative_episodes[:3]:
            age = ep.get("age", "?")
            event = ep.get("event", "")
            impact = ep.get("impact", "")
            ep_lines.append(f"  - {age} 歲時：{event}。這件事讓你{impact}")
        sections.append("塑造你的關鍵經歷：\n" + "\n".join(ep_lines))

    # --- [R12] 知識邊界 ---
    kb = card.knowledge_boundary
    if kb.get("expert_in"):
        sections.append("你擅長的領域：" + "、".join(kb["expert_in"][:5]) + "。")
    if kb.get("ignorant_of"):
        sections.append(
            "你不懂的領域：" + "、".join(kb["ignorant_of"][:5]) + "。"
            "被問到這些時，坦白說你不清楚，建議對方找專門的人。"
        )

    # --- [R18] 個人立場（反談媽） ---
    if card.stances:
        stance_lines = []
        for s in card.stances[:4]:
            topic = s.get("topic", "")
            position = s.get("position", "")
            intensity = s.get("intensity", "firm")
            firmness = "堅定" if intensity == "firm" else "溫和但不退讓"
            stance_lines.append(f"  - {topic}：{position}（{firmness}）")
        sections.append(
            "你的個人立場（不因對方反對就改口）：\n"
            + "\n".join(stance_lines) + "\n"
            "對方跟你意見不同時，先承認他說的有道理的地方，再溫和堅持你的看法並給理由。"
        )

    # --- [R05] 說話小習慣 ---
    if card.speech_profile.get("quirks"):
        sections.append(
            "你說話的小習慣（偶爾出現就好，不要每句都用）：" +
            "、".join(card.speech_profile["quirks"][:3]) + "。"
        )
    catchphrase = card.speech_profile.get("口頭禪") or card.speech_profile.get("catchphrase")
    if catchphrase:
        sections.append(
            f"你有句口頭禪「{catchphrase}」，但只在真的很貼切時才用，不要每次都說。"
        )
    if card.speech_profile.get("taboos"):
        sections.append(
            "絕對不說這些話：" + "、".join(card.speech_profile["taboos"][:3]) + "。"
        )

    # --- [R05 §跨越恐怖谷] 說話節奏 ---
    sentence_length = card.speech_profile.get("sentence_length", "short")
    if sentence_length == "short":
        sections.append(
            "你說話像在傳訊息：短句、口語、一次講一件事。"
            "不要一口氣把所有背景和學經歷交代完。"
        )

    # --- [R12] Per-persona few-shot 範例對話 ---
    example_exchanges = card.speech_profile.get("example_exchanges")
    if not example_exchanges and hasattr(card, "example_exchanges"):
        example_exchanges = card.example_exchanges
    if example_exchanges:
        ex_lines = []
        for ex in example_exchanges[:3]:
            user_msg = ex.get("user", "")
            assistant_msgs = ex.get("assistant", [])
            if isinstance(assistant_msgs, str):
                assistant_msgs = [assistant_msgs]
            ex_lines.append(f"  使用者：{user_msg}")
            for a_msg in assistant_msgs:
                ex_lines.append(f"  你：{a_msg}")
            ex_lines.append("")
        sections.append(
            "【語氣參考 — 模仿這個節奏和長度，不要照抄內容】\n" +
            "\n".join(ex_lines).rstrip()
        )

    return "\n\n".join(sections)


def persona_card_from_dict(data: dict) -> PersonaCard:
    """Deserialize a dict (from JSON/DB) into a PersonaCard."""
    return PersonaCard(
        identity=data.get("identity", {}),
        big_five=data.get("big_five", {}),
        core_values=data.get("core_values", []),
        speech_profile=data.get("speech_profile", {}),
        formative_episodes=data.get("formative_episodes", []),
        knowledge_boundary=data.get("knowledge_boundary", {}),
        stances=data.get("stances", []),
        example_exchanges=data.get("example_exchanges", []),
    )
"""
"""
