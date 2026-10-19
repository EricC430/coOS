import pytest
from services.m4_12_hidden_achievement.archetypes import (
    CORE_ARCHETYPES,
    ArchetypeEvalRule,
    evaluate_archetype_rule,
)
from services.m4_12_hidden_achievement.feature_trap import (
    FastPathMatcher,
    SlowPathAnalyzer,
    generate_personalized_flavor_text,
)
from services.m4_12_hidden_achievement.schemas import ArchetypeEnum


def test_cartographer_rule_evaluation():
    """
    T023: 測試本質探求者 (THE_CURIOUS_CARTOGRAPHER) 原型匹配
    """
    text = "我想深入理解編譯器底層架構中 AST 如何轉換為 SSA 形式，其本質機制是什麼？"
    rule = CORE_ARCHETYPES["ha_curious_cartographer_01"]
    
    is_match, matched_keys = evaluate_archetype_rule(rule, text)
    assert is_match is True
    assert len(matched_keys) > 0


def test_reframe_alchemist_rule_evaluation():
    """
    T023/T024: 測試心靈煉金術士 (THE_REFRAME_ALCHEMIST) 薩提爾冰山元認知自省匹配
    """
    text = "在今天的每日反思中，我深刻體察到自己面對評審時的內在心理阻抗與脆弱，我選擇接納並進行認知重構與自我覺察。"
    rule = CORE_ARCHETYPES["ha_reframe_alchemist_01"]
    
    is_match, matched_keys = evaluate_archetype_rule(rule, text)
    assert is_match is True
    assert any("自省" in k or "脆弱" in k or "接納" in k or "重構" in k for k in matched_keys)


def test_serendipity_seeker_rule_evaluation():
    """
    T023/T025: 測試微光漫遊者 (THE_SERENDIPITY_SEEKER) 生活注意力恢復匹配
    """
    text = "經過五小時深度 coding，認知負荷已滿，我立刻脫離螢幕走到戶外散步，進行大自然的五感覺察與放空。"
    rule = CORE_ARCHETYPES["ha_serendipity_seeker_01"]
    
    is_match, matched_keys = evaluate_archetype_rule(rule, text)
    assert is_match is True
    assert any("散步" in k or "脫離螢幕" in k or "五感覺察" in k for k in matched_keys)


def test_polyglot_synthesizer_rule_evaluation():
    """
    T023/T026: 測試通識織網者 (THE_POLYGLOT_SYNTHESIZER) 跨領域融通匹配
    """
    text = "我試著將哲學思考與程式架構相結合，進行概念類比遷移與跨領域知識融通。"
    rule = CORE_ARCHETYPES["ha_polyglot_synthesizer_01"]
    
    is_match, matched_keys = evaluate_archetype_rule(rule, text)
    assert is_match is True
    assert any("跨領域" in k or "知識融通" in k or "類比遷移" in k or "哲學" in k for k in matched_keys)


@pytest.mark.asyncio
async def test_personalized_flavor_text_generation():
    """
    T023/T027: 測試本機 Gemma 個性化金句與情境摘要合成
    """
    rule = CORE_ARCHETYPES["ha_curious_cartographer_01"]
    user_excerpt = "追問 SSA 與編譯器虛擬機器的底層實現原理"
    themes = ["SSA", "編譯器", "底層原理"]
    
    flavor_text, context_summary = await generate_personalized_flavor_text(
        rule=rule,
        user_excerpt=user_excerpt,
        themes=themes,
        role_id="role_coder",
    )
    
    assert flavor_text is not None
    assert len(flavor_text) > 0
    # 應融合個人探究主題或原型韻味
    assert "「" in flavor_text and "」" in flavor_text
    assert context_summary is not None
    assert "role_coder" in context_summary or "SSA" in context_summary
