from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from .schemas import ArchetypeEnum, RarityEnum


class ArchetypeEvalRule(BaseModel):
    achievement_id: str
    archetype: ArchetypeEnum
    name: str
    description: str
    flavor_text_template: str
    rarity: RarityEnum
    exp_reward: int
    badge_icon_url: str
    regex_patterns: List[str] = Field(default_factory=list)
    semantic_anchors: List[str] = Field(default_factory=list)
    min_proactivity_score: float = 0.70
    min_concept_leap: float = 0.60
    required_role_context: Optional[str] = None


CORE_ARCHETYPES: Dict[str, ArchetypeEvalRule] = {
    "ha_curious_cartographer_01": ArchetypeEvalRule(
        achievement_id="ha_curious_cartographer_01",
        archetype=ArchetypeEnum.CURIOSITY,
        name="本質探求者",
        description="主動追問底層原理達五層以上，跳脫既定提示指針。",
        flavor_text_template="「你所觸碰的不是表象，而是深邃的知識核心。」",
        rarity=RarityEnum.RARE,
        exp_reward=100,
        badge_icon_url="/assets/badges/cartographer.svg",
        regex_patterns=[
            r"(底層|原理|IR|編譯器|SSA|AST|虛擬機器|記憶體佈局|系統調用)",
            r"(為什麼|如何實現|本質|機制|底層架構)",
        ],
        semantic_anchors=["底層原理", "內部機制", "深入探究", "架構設計"],
        min_proactivity_score=0.75,
        min_concept_leap=0.60,
    ),
    "ha_reframe_alchemist_01": ArchetypeEvalRule(
        achievement_id="ha_reframe_alchemist_01",
        archetype=ArchetypeEnum.METACOGNITION,
        name="心靈煉金術士",
        description="於反思中體察自我心理阻抗與脆弱，完成認知重構與接納。",
        flavor_text_template="「接納不完美的那一刻，真正的轉化已經開始。」",
        rarity=RarityEnum.EPIC,
        exp_reward=150,
        badge_icon_url="/assets/badges/alchemist.svg",
        regex_patterns=[
            r"(自省|脆弱|防衛|阻抗|接納|轉念|重構|自我覺察)",
        ],
        semantic_anchors=["薩提爾冰山", "內在對話", "心態重構", "接納脆弱", "自我轉化"],
        min_proactivity_score=0.70,
        min_concept_leap=0.50,
    ),
    "ha_serendipity_seeker_01": ArchetypeEvalRule(
        achievement_id="ha_serendipity_seeker_01",
        archetype=ArchetypeEnum.RESTORATION,
        name="微光漫遊者",
        description="於高認知負荷之際，果斷走向真實世界完成注意力恢復實踐。",
        flavor_text_template="「微風與綠意撫平了焦慮，世界在此刻向你敞開。」",
        rarity=RarityEnum.RARE,
        exp_reward=80,
        badge_icon_url="/assets/badges/seeker.svg",
        regex_patterns=[
            r"(散步|煮菜|烹飪|探店|脫離螢幕|大自然|五感覺察|放空)",
        ],
        semantic_anchors=["注意力恢復", "生活微冒險", "實體世界", "舒緩疲憊", "感官覺察"],
        min_proactivity_score=0.60,
        min_concept_leap=0.40,
    ),
    "ha_polyglot_synthesizer_01": ArchetypeEvalRule(
        achievement_id="ha_polyglot_synthesizer_01",
        archetype=ArchetypeEnum.CROSS_SYNTHESIS,
        name="通識織網者",
        description="巧妙揉合兩種以上截然不同角色領域的概念，創造結構性突破。",
        flavor_text_template="「當邊界消融，跨界的火花照亮了未知的群島。」",
        rarity=RarityEnum.LEGENDARY,
        exp_reward=250,
        badge_icon_url="/assets/badges/synthesizer.svg",
        regex_patterns=[
            r"(跨領域|知識融通|類比遷移|哲學.*程式|心理.*架構|音樂.*演算法)",
        ],
        semantic_anchors=["跨界融合", "概念類比", "多元思維模型", "跨領域綜合"],
        min_proactivity_score=0.80,
        min_concept_leap=0.80,
    ),
}


def evaluate_cartographer_rule(rule: ArchetypeEvalRule, text: str) -> tuple[bool, list[str]]:
    """T010: 好奇探險家 (THE_CURIOUS_CARTOGRAPHER) 評估器."""
    import re
    matched = []
    patterns_hit = 0
    for pat in rule.regex_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            patterns_hit += 1
            for match in re.finditer(pat, text, re.IGNORECASE):
                if match.group(0) not in matched:
                    matched.append(match.group(0))
    is_match = patterns_hit >= len(rule.regex_patterns)
    return is_match, matched


def evaluate_reframe_alchemist_rule(rule: ArchetypeEvalRule, text: str) -> tuple[bool, list[str]]:
    """T024: 心靈煉金術士 (THE_REFRAME_ALCHEMIST) 薩提爾冰山元認知重構評估器."""
    import re
    matched = []
    for pat in rule.regex_patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            if m.group(0) not in matched:
                matched.append(m.group(0))
    for anchor in rule.semantic_anchors:
        if anchor in text and anchor not in matched:
            matched.append(anchor)
    is_match = len(matched) >= 1
    return is_match, matched


def evaluate_serendipity_seeker_rule(rule: ArchetypeEvalRule, text: str) -> tuple[bool, list[str]]:
    """T025: 微光漫遊者 (THE_SERENDIPITY_SEEKER) 生活注意力恢復評估器."""
    import re
    matched = []
    for pat in rule.regex_patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            if m.group(0) not in matched:
                matched.append(m.group(0))
    for anchor in rule.semantic_anchors:
        if anchor in text and anchor not in matched:
            matched.append(anchor)
    is_match = len(matched) >= 1
    return is_match, matched


def evaluate_polyglot_synthesizer_rule(rule: ArchetypeEvalRule, text: str) -> tuple[bool, list[str]]:
    """T026: 通識織網者 (THE_POLYGLOT_SYNTHESIZER) 跨領域融通評估器."""
    import re
    matched = []
    for pat in rule.regex_patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            if m.group(0) not in matched:
                matched.append(m.group(0))
    for anchor in rule.semantic_anchors:
        if anchor in text and anchor not in matched:
            matched.append(anchor)
    is_match = len(matched) >= 1
    return is_match, matched


def evaluate_archetype_rule(rule: ArchetypeEvalRule, text: str) -> tuple[bool, list[str]]:
    """統一原型規則入口."""
    if rule.archetype == ArchetypeEnum.CURIOSITY:
        return evaluate_cartographer_rule(rule, text)
    elif rule.archetype == ArchetypeEnum.METACOGNITION:
        return evaluate_reframe_alchemist_rule(rule, text)
    elif rule.archetype == ArchetypeEnum.RESTORATION:
        return evaluate_serendipity_seeker_rule(rule, text)
    elif rule.archetype == ArchetypeEnum.CROSS_SYNTHESIS:
        return evaluate_polyglot_synthesizer_rule(rule, text)
    return False, []

