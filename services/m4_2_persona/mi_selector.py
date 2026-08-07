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
                "對方現在有防衛心。用反射式傾聽回應：把他的感受說出來"
                "（「聽起來你覺得…」「你的意思是…」）。"
                "這一輪只傾聽，不給建議、不糾正、不推進議程。"
            ),
            forbidden_actions=["給建議", "糾正對方", "推進議題"],
            sdt_target=SDTNeed.AUTONOMY,
        )

    # [R16 ssChange Talk] User expressed change intention
    if detect_change_talk(user_message):
        return MIDirective(
            technique=MITechnique.CHANGE_TALK_REPLAY,
            instruction=(
                "對方剛說出想改變的意圖。把他自己的話回放給他聽"
                "（「你剛剛說想…」「你提到你打算…」），強化他的動機。"
                "不要幫他加新目標，不要否定他的意圖。"
            ),
            forbidden_actions=["否定對方意圖", "擅自加新目標"],
            sdt_target=SDTNeed.COMPETENCE,
        )

    # [RISK-03] Anxiety -> affirmation, NEVER mirror anxiety
    if implicit_state == "anxiety":
        return MIDirective(
            technique=MITechnique.AFFIRMATION,
            instruction=(
                "對方現在焦慮。先肯定他已經做到的事"
                "（「你已經跨出第一步了」「光是來問就很不錯」）。"
                "把大任務拆小，語氣平穩溫暖。"
                "絕對不鏡像他的焦慮、不催促、不用急迫語氣。"
            ),
            forbidden_actions=["鏡像焦慮", "催促語氣", "施壓"],
            sdt_target=SDTNeed.COMPETENCE,
        )

    # [RISK-03] Avoidance -> open question, NO guilt induction
    if implicit_state == "avoidance":
        return MIDirective(
            technique=MITechnique.OPEN_QUESTION,
            instruction=(
                "對方在迴避。用好奇的開放式問題引導探索"
                "（「如果…會怎樣？」「你理想中的狀態是什麼？」）。"
                "絕對不用愧疚感或羞恥感推動對方。"
            ),
            forbidden_actions=["引發罪惡感", "羞辱", "施壓", "指責"],
            sdt_target=SDTNeed.AUTONOMY,
        )

    # Flow/stable -> structured advice (normal expert mode)
    return MIDirective(
        technique=MITechnique.STRUCTURED_ADVICE,
        instruction=(
            "對方狀態穩定。可以正常給建議、分享觀點、推進討論。"
            "語氣自然，像朋友之間聊正事。"
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
