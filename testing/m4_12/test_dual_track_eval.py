import asyncio
import json
import pytest
from datetime import datetime
from services.m4_12_hidden_achievement.schemas import ArchetypeEnum, RarityEnum
from services.m4_12_hidden_achievement.models import (
    HiddenAchievementModel,
    UserAchievementModel,
    EpistemicEvidenceQueueModel,
)


@pytest.mark.asyncio
async def test_fast_path_regex_matcher_detects_cartographer(db_session, seed_achievements):
    """
    T009/T010: 快軌正則比對測試
    驗證使用者自主追問底層原理（如 SSA、AST、虛擬機器等關鍵字）能在 <100ms 內命中特徵。
    """
    from services.m4_12_hidden_achievement.feature_trap import FastPathMatcher

    matcher = FastPathMatcher()
    input_text = "我想理解這個編譯器底層架構中，SSA 形式與虛擬機器指令集是如何實現的？為什麼需要這層抽象？"

    match_result = matcher.evaluate(input_text, achievement_id="ha_curious_cartographer_01")
    assert match_result.is_matched is True
    assert match_result.execution_time_ms < 100.0
    assert len(match_result.matched_keywords) > 0


@pytest.mark.asyncio
async def test_fast_path_ignores_unrelated_messages(db_session, seed_achievements):
    """
    T009/T010: 快軌對無關一般對話不應誤觸發。
    """
    from services.m4_12_hidden_achievement.feature_trap import FastPathMatcher

    matcher = FastPathMatcher()
    input_text = "今天天氣真不錯，請問 Python 的 print 怎麼印出字串？"

    match_result = matcher.evaluate(input_text, achievement_id="ha_curious_cartographer_01")
    assert match_result.is_matched is False


@pytest.mark.asyncio
async def test_slow_path_gemma_semantic_analysis(db_session, seed_achievements):
    """
    T009/T011: 慢軌語意解析測試
    驗證 SlowPathAnalyzer 能夠分析認知跳躍深度與主動提問權重。
    """
    from services.m4_12_hidden_achievement.feature_trap import SlowPathAnalyzer

    analyzer = SlowPathAnalyzer()
    
    # 模擬高認知跳躍與主動探索文本
    excerpt = "我不只是想修好這個 bug，而是發現這背後是分散式一致性與 CAP 定理在快取失效時的根本權衡，我畫了一張架構圖來重構它。"
    
    analysis = await analyzer.analyze_epistemic_depth(excerpt)
    assert analysis.concept_leap_depth >= 0.60
    assert analysis.proactivity_score >= 0.70
    assert analysis.themes is not None


@pytest.mark.asyncio
async def test_gemma_timeout_fallback_to_queue(db_session, seed_achievements):
    """
    T009/T012: 本地 Gemma 逾時 (>3s) 或離線時，自動暫存至 epistemic_evidence_queue。
    """
    from services.m4_12_hidden_achievement.evidence_queue import EvidenceQueueManager
    from services.m4_12_hidden_achievement.feature_trap import SlowPathAnalyzer

    # 模擬逾時 analyzer
    slow_analyzer = SlowPathAnalyzer(timeout_seconds=0.01, simulate_timeout=True)
    queue_mgr = EvidenceQueueManager(db_session)

    item = await queue_mgr.enqueue_if_timeout_or_offline(
        session_id="session_test_123",
        user_id="user_alice",
        origin_role_id="role_coder",
        source_type="chat_message",
        raw_excerpt="深入探討分散式架構與共識演算法",
        analyzer=slow_analyzer,
    )

    assert item is not None
    assert item.status == "PENDING"

    # 驗證 DB 中已持久化
    persisted = db_session.query(EpistemicEvidenceQueueModel).filter_by(session_id="session_test_123").first()
    assert persisted is not None
    assert persisted.status == "PENDING"
    assert persisted.user_id == "user_alice"


@pytest.mark.asyncio
async def test_dual_track_service_unlock_flow(db_session, seed_achievements):
    """
    T009/T013: 整合雙軌服務端到端評估
    對話輸入觸發快軌 + 慢軌，若符合標準則完成達成並給予解鎖 Payload。
    """
    from services.m4_12_hidden_achievement.service import HiddenAchievementService

    service = HiddenAchievementService(db_session=db_session)
    input_text = "我想理解這個編譯器底層架構中，SSA 形式與虛擬機器指令集是如何實現的？為什麼需要這層抽象？"

    unlock_event = await service.evaluate_dialogue(
        user_id="user_alice",
        session_id="session_001",
        role_id="role_compiler_expert",
        user_message=input_text,
    )

    assert unlock_event is not None
    assert unlock_event.achievement_id == "ha_curious_cartographer_01"
    assert unlock_event.rarity == RarityEnum.RARE
    assert unlock_event.exp_reward == 100

    # 驗證 user_achievements 資料表已寫入
    record = db_session.query(UserAchievementModel).filter_by(
        user_id="user_alice",
        achievement_id="ha_curious_cartographer_01"
    ).first()
    assert record is not None
    assert record.is_acknowledged is False
