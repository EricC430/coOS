"""
M4.2.2 -- MI (Motivational Interviewing) Technique Selector

SPEC: docs/modules/M4_2_persona_state_machine_SPEC.md
Research: [R16: Motivational Interviewing] OARS techniques
          [R09 ss4.1 SDT] Self-Determination Theory quick-check
Risk: RISK-02 (MI switch registered as legal in ARPM)
      RISK-03 (anxiety -> affirmation, never mirror)
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class MITechnique(StrEnum):
    """[R16] Core MI technique categories."""
    REFLECTIVE_LISTENING = "reflective_listening"
    AFFIRMATION = "affirmation"
    OPEN_QUESTION = "open_question"
    SUMMARY = "summary"
    CHANGE_TALK_REPLAY = "change_talk_replay"
    STRUCTURED_ADVICE = "structured_advice"


class SDTNeed(StrEnum):
    """[R09 ss4.1] Self-Determination Theory basic needs."""
    AUTONOMY = "autonomy"
    COMPETENCE = "competence"
    RELATEDNESS = "relatedness"


@dataclass
class MIDirective:
    """Output of the MI selector: 2-3 line behavioral instruction for system prompt."""
    technique: MITechnique
    instruction: str
    forbidden_actions: list[str]
    sdt_target: SDTNeed | None = None


# [R16] Change talk trigger phrases (English)
CHANGE_TALK_MARKERS_EN = [
    "i want to", "i need to", "i should",
    "i could", "i will", "i'm going to",
    "maybe i can", "perhaps i should",
    "i'd like", "let me try",
]

# [W9.2] 繁體中文 change talk markers — 使用者表達改變意圖的語句
CHANGE_TALK_MARKERS_ZH = [
    "我想試", "我想要", "我應該", "我要開始",
    "也許我可以", "我打算", "我決定",
    "讓我試試", "我覺得我可以", "我會試",
    "我要去", "我想學", "我來做",
    "下次我會", "我準備", "我想改",
]

# Combined list for detection
CHANGE_TALK_MARKERS = CHANGE_TALK_MARKERS_EN + CHANGE_TALK_MARKERS_ZH


def detect_change_talk(user_message: str) -> bool:
    """[R16 ss Change Talk] Detect if user expresses change intention."""
    msg_lower = user_message.lower()
    for marker in CHANGE_TALK_MARKERS:
        if marker in msg_lower:
            return True
    return False


def select_mi_technique(
    reactance_score: float,
    implicit_state: str | None = None,
    tone_state: str = "authoritative",
    user_message: str = "",
) -> MIDirective:
    """
    [R16: Motivational Interviewing ssOARS]
    Select MI technique based on user state and inject behavioral directive.

    Priority:
    1. High reactance (>0.7) -> reflective listening + rolling with resistance
    2. Change talk detected -> replay change talk
    3. Anxiety state -> affirmation + task chunking [RISK-03: no mirror]
    4. Avoidance state -> open question [RISK-03: no guilt]
    5. Flow/stable -> structured advice (normal expert mode)
    """
    # [R16 ssRolling with Resistance] High reactance
    if reactance_score > 0.7:
        return MIDirective(
            technique=MITechnique.REFLECTIVE_LISTENING,
            instruction=(
                "The user is defensive. Use reflective listening: "
                "'It sounds like you feel...' Roll with resistance. "
                "Do NOT give advice or suggestions this turn."
            ),
            forbidden_actions=["giving advice", "suggesting solutions", "correcting"],
            sdt_target=SDTNeed.AUTONOMY,
        )

    # [R16 ssChange Talk] User expressed change intention
    if detect_change_talk(user_message):
        return MIDirective(
            technique=MITechnique.CHANGE_TALK_REPLAY,
            instruction=(
                "The user just expressed change intention. "
                "Summarize and replay their own words: "
                "'You just said you want to...' Reinforce their motivation."
            ),
            forbidden_actions=["dismissing their intention", "adding new goals"],
            sdt_target=SDTNeed.COMPETENCE,
        )

    # [RISK-03] Anxiety -> affirmation, NEVER mirror anxiety
    if implicit_state == "anxiety":
        return MIDirective(
            technique=MITechnique.AFFIRMATION,
            instruction=(
                "The user is anxious. Affirm their efforts: "
                "'You've already taken an important step by...' "
                "Break tasks into small pieces. Stay calm and grounding."
            ),
            forbidden_actions=["mirroring anxiety", "using urgent language", "pressuring"],
            sdt_target=SDTNeed.COMPETENCE,
        )

    # [RISK-03] Avoidance -> open question, NO guilt induction
    if implicit_state == "avoidance":
        return MIDirective(
            technique=MITechnique.OPEN_QUESTION,
            instruction=(
                "The user is avoiding. Use curious, open-ended questions: "
                "'What would it look like if...' Evoke exploration. "
                "Never use guilt or shame."
            ),
            forbidden_actions=["guilt induction", "shame", "pressure", "blame"],
            sdt_target=SDTNeed.AUTONOMY,
        )

    # Flow/stable -> structured advice (normal expert mode)
    return MIDirective(
        technique=MITechnique.STRUCTURED_ADVICE,
        instruction=(
            "The user is stable. Provide clear, structured advice. "
            "Summarize key points and offer concrete next steps."
        ),
        forbidden_actions=[],
        sdt_target=SDTNeed.COMPETENCE,
    )


def sdt_quick_check(response: str) -> list[SDTNeed]:
    """
    [R09 ss4.1 SDT] Quick-check: does the response touch at least one
    of autonomy / competence / relatedness?
    [W9.3] 新增繁體中文關鍵字，因為 persona 回應為繁體中文。
    """
    needs_found: list[SDTNeed] = []

    # Autonomy markers (EN + ZH)
    autonomy_words = [
        "your choice", "you decide", "up to you",
        "what do you think", "how would you",
        # [W9.3] 繁體中文
        "你可以決定", "你自己選", "由你決定", "你覺得呢",
        "你怎麼想", "你想怎麼做", "看你", "隨你",
    ]
    # Competence markers (EN + ZH)
    competence_words = [
        "you can", "you're capable", "you've done",
        "well done", "good job", "progress",
        "you've learned", "you've grown",
        # [W9.3] 繁體中文
        "你可以", "你做到了", "你很厲害", "進步",
        "你已經學會", "做得好", "你有能力", "你辦到",
    ]
    # Relatedness markers (EN + ZH)
    relatedness_words = [
        "together", "I'm here", "support",
        "I understand", "I hear you",
        # [W9.3] 繁體中文
        "我們一起", "我在", "我懂", "我理解",
        "我支持", "一起", "陪你", "我聽到了",
    ]

    response_lower = response.lower()
    if any(w in response_lower for w in autonomy_words):
        needs_found.append(SDTNeed.AUTONOMY)
    if any(w in response_lower for w in competence_words):
        needs_found.append(SDTNeed.COMPETENCE)
    if any(w in response_lower for w in relatedness_words):
        needs_found.append(SDTNeed.RELATEDNESS)

    return needs_found
