import asyncio
from datetime import datetime, timezone
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from services.m4_12_hidden_achievement.models import (
    HiddenAchievementModel,
    UserAchievementModel,
)
from services.m4_12_hidden_achievement.schemas import (
    ArchetypeEnum,
    RarityEnum,
    UnlockEventPayload,
    AckAchievementRequest,
)
from services.m4_12_hidden_achievement.db import get_db
from services.m4_12_hidden_achievement.router import router as m4_12_router, ws_manager


class MockWebSocket:
    def __init__(self):
        self.sent_messages = []

    async def send_json(self, message: dict):
        self.sent_messages.append(message)


@pytest.fixture
def mock_ws():
    return MockWebSocket()


@pytest.mark.asyncio
async def test_flow_gated_queue_delays_during_deep_flow(mock_ws):
    """
    T018/T019/T020: 心流感知微斷點推播測試 [RISK-04]
    當使用者處於高認知負荷/深層編程 (in_flow = True) 時，
    達成事件暫存於佇列，不中斷心流。
    直到收到 M1.2 微斷點信號，才推播 HIDDEN_ACHIEVEMENT_UNLOCKED 事件。
    """
    from services.m4_12_hidden_achievement.surprise_dispatcher import SurpriseDispatcher

    dispatcher = SurpriseDispatcher(ws_manager=ws_manager)
    user_id = "user_deep_flow"

    # 模擬連線
    ws_manager.active_connections[user_id] = [mock_ws]

    # 設定心流狀態為高負荷
    dispatcher.set_flow_state(user_id, is_in_flow=True)

    payload = UnlockEventPayload(
        achievement_id="ha_curious_cartographer_01",
        archetype=ArchetypeEnum.CURIOSITY,
        name="本質探求者",
        description="追問底層原理",
        flavor_text="「深邃的知識核心」",
        rarity=RarityEnum.RARE,
        exp_reward=100,
        badge_icon_url="/assets/badges/cartographer.svg",
        unlocked_at=datetime.now(timezone.utc),
        context_summary="於深層編程中發現",
    )

    # 嘗試推播，應被佇列暫存
    dispatched = await dispatcher.queue_or_dispatch(user_id, payload)
    assert dispatched is False
    assert len(mock_ws.sent_messages) == 0
    assert len(dispatcher.get_pending_surprises(user_id)) == 1

    # 模擬接收到 M1.2 微斷點信號 (使用者停頓思考/任務切換)
    released = await dispatcher.handle_micro_breakpoint(user_id)
    assert len(released) == 1
    assert len(mock_ws.sent_messages) == 1
    assert mock_ws.sent_messages[0]["event_type"] == "HIDDEN_ACHIEVEMENT_UNLOCKED"
    assert mock_ws.sent_messages[0]["achievement_id"] == "ha_curious_cartographer_01"
    assert len(dispatcher.get_pending_surprises(user_id)) == 0


@pytest.mark.asyncio
async def test_ack_endpoint_updates_database(db_session, seed_achievements):
    """
    T018/T021: 測試 POST /api/achievements/ack 更新確認狀態.
    前端 SurpriseModal 關閉後，發送 ACK，DB 中的 is_acknowledged 變為 True.
    """
    app = FastAPI()
    app.include_router(m4_12_router)

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    user_ach = UserAchievementModel(
        id="ua_ack_test_01",
        user_id="user_ack_test",
        achievement_id="ha_curious_cartographer_01",
        xp_awarded=100,
        transaction_id="tx_ack_01",
        is_acknowledged=False,
    )
    db_session.add(user_ach)
    db_session.commit()

    resp = client.post(
        "/api/achievements/ack",
        json={"user_id": "user_ack_test", "achievement_ids": ["ha_curious_cartographer_01"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["acknowledged_count"] == 1

    # 驗證 DB 狀態已變更
    db_session.refresh(user_ach)
    assert user_ach.is_acknowledged is True


@pytest.mark.asyncio
async def test_single_cap_catchup_on_reconnect(db_session, seed_achievements, mock_ws):
    """
    T018/T022: 測試開機與重連 Single Cap 補發 (FR-015).
    使用者積壓了 Rare 與 Legendary 兩筆未確認成就，
    重連時僅彈窗推播 1 筆最高稀有度 (Legendary) 的成就。
    """
    from services.m4_12_hidden_achievement.service import HiddenAchievementService

    user_id = "user_reconnect"
    ws_manager.active_connections[user_id] = [mock_ws]

    rare_ach = seed_achievements[0]  # rare
    legendary_ach = seed_achievements[3]  # legendary

    db_session.add(
        UserAchievementModel(
            id="ua_rare_01",
            user_id=user_id,
            achievement_id=rare_ach.id,
            xp_awarded=100,
            transaction_id="tx_rare",
            is_acknowledged=False,
        )
    )
    db_session.add(
        UserAchievementModel(
            id="ua_leg_01",
            user_id=user_id,
            achievement_id=legendary_ach.id,
            xp_awarded=250,
            transaction_id="tx_leg",
            is_acknowledged=False,
        )
    )
    db_session.commit()

    service = HiddenAchievementService(db_session=db_session, ws_manager=ws_manager)
    top_payload = await service.handle_reconnect_catch_up(user_id)

    assert top_payload is not None
    assert top_payload.achievement_id == legendary_ach.id
    assert top_payload.rarity == RarityEnum.LEGENDARY

    # 驗證 WebSocket 僅推播了 1 筆訊息 (Single Cap)
    assert len(mock_ws.sent_messages) == 1
    assert mock_ws.sent_messages[0]["achievement_id"] == legendary_ach.id

    # 驗證 Rare 成就仍然是 is_acknowledged = False，保留給畫廊呈現 'NEW'
    rare_record = (
        db_session.query(UserAchievementModel)
        .filter_by(user_id=user_id, achievement_id=rare_ach.id)
        .first()
    )
    assert rare_record.is_acknowledged is False
