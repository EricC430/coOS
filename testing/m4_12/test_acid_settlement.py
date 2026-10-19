import asyncio
import pytest
from datetime import datetime, timezone
from services.m4_12_hidden_achievement.models import (
    HiddenAchievementModel,
    UserAchievementModel,
)
from services.m4_12_hidden_achievement.schemas import ArchetypeEnum, RarityEnum
from services.m4_12_hidden_achievement.rate_limiter import AchievementRateLimiter
from services.m4_12_hidden_achievement.telemetry import AchievementTelemetry
from services.m4_12_hidden_achievement.service import HiddenAchievementService


def test_rate_limiter_60s_cooldown():
    """
    T028/T030: 測試 60 秒滑動視窗防刷機制.
    在 60 秒內針對相同語意或成就觸發，第二次請求必須被攔截 (回傳 False)。
    """
    limiter = AchievementRateLimiter(cooldown_seconds=60.0)
    user_id = "user_spammer"
    ach_id = "ha_curious_cartographer_01"

    # 第一次請求：允許通過
    allowed_1 = limiter.check_and_acquire(user_id, ach_id, "signature_compiler_ssa")
    assert allowed_1 is True

    # 立即發送第二次請求：應被限流攔截
    allowed_2 = limiter.check_and_acquire(user_id, ach_id, "signature_compiler_ssa")
    assert allowed_2 is False

    # 另一位使用者發送請求：不受影響
    allowed_other = limiter.check_and_acquire("user_other", ach_id, "signature_compiler_ssa")
    assert allowed_other is True


@pytest.mark.asyncio
async def test_acid_idempotent_single_unlock(db_session, seed_achievements):
    """
    T028/T029: 測試併發/重複解鎖的 ACID 交易冪等性.
    即使多次呼叫解鎖同一個成就，資料庫只會保留 1 筆紀錄，且 XP 絕不重複核發。
    """
    service = HiddenAchievementService(db_session=db_session)
    cartographer = seed_achievements[0]
    user_id = "user_concurrent"

    rule = service.fast_matcher._compiled_rules
    from services.m4_12_hidden_achievement.archetypes import CORE_ARCHETYPES
    carto_rule = CORE_ARCHETYPES[cartographer.id]

    # 第一次解鎖
    payload_1 = service._unlock_achievement(
        user_id=user_id,
        rule=carto_rule,
        role_id="role_coder",
        context_summary="第一次解鎖",
    )
    assert payload_1 is not None

    # 第二次嘗試解鎖 (模擬併發或重複對話特徵命中)
    assert service.is_achievement_unlocked(user_id, cartographer.id) is True

    # 再次執行 evaluate_dialogue
    msg = "我想理解這個編譯器底層架構中，SSA 形式與虛擬機器指令集是如何實現的？為什麼需要這層抽象？"
    payload_2 = await service.evaluate_dialogue(
        user_id=user_id,
        session_id="session_002",
        role_id="role_coder",
        user_message=msg,
    )
    # 由於已解鎖過，應回傳 None
    assert payload_2 is None

    # 驗證資料表中只有 1 筆記錄
    records = (
        db_session.query(UserAchievementModel)
        .filter_by(user_id=user_id, achievement_id=cartographer.id)
        .all()
    )
    assert len(records) == 1
    assert records[0].xp_awarded == 100


def test_telemetry_audit_logging():
    """
    T028/T031: 測試 M0.4 [R01] 結構化日誌稽核事件產生.
    確保成就達成時產生日誌，且載荷符合規範（不含 L1 明文，包含 transaction_id 與 XP 資訊）。
    """
    telemetry = AchievementTelemetry()
    event = telemetry.create_unlock_audit_event(
        user_id="user_alice",
        achievement_id="ha_curious_cartographer_01",
        xp_awarded=100,
        transaction_id="tx_12345",
        origin_role_id="role_coder",
    )

    assert event.module == "M4.12"
    assert event.action == "ACHIEVEMENT_UNLOCKED"
    assert event.level == "AUDIT"
    assert event.payload["achievement_id"] == "ha_curious_cartographer_01"
    assert event.payload["xp_awarded"] == 100
    assert event.payload["transaction_id"] == "tx_12345"
    # 確保不洩漏任何 L1 對話明文欄位
    for forbidden in ["raw_text", "raw_code", "transcript"]:
        assert forbidden not in event.payload


def test_acid_concurrent_collision_gracefully_handled(db_session, seed_achievements):
    """
    驗證毫秒級並發衝突時，底層 UNIQUE(user_id, achievement_id) 觸發 IntegrityError，
    系統自動 rollback 並返回 None，絕不造成未捕獲異常崩潰或資料庫損毀。
    """
    service = HiddenAchievementService(db_session=db_session)
    from services.m4_12_hidden_achievement.archetypes import CORE_ARCHETYPES
    carto_rule = CORE_ARCHETYPES["ha_curious_cartographer_01"]

    user_id = "user_race_condition"

    # 第一次解鎖：成功
    first = service._unlock_achievement(
        user_id=user_id,
        rule=carto_rule,
        role_id="role_coder",
        context_summary="第一次解鎖",
    )
    assert first is not None

    # 第二次直接嘗試插入同使用者、同成就記錄 (模擬並發競態繞過前置檢查)
    second = service._unlock_achievement(
        user_id=user_id,
        rule=carto_rule,
        role_id="role_coder",
        context_summary="並發競態嘗試",
    )
    assert second is None  # 捕獲 IntegrityError 並安全 rollback

    # 驗證資料庫依然乾淨且只有 1 筆
    records = db_session.query(UserAchievementModel).filter_by(
        user_id=user_id,
        achievement_id=carto_rule.achievement_id,
    ).all()
    assert len(records) == 1

