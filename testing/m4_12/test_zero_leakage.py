import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from services.m4_12_hidden_achievement.router import router as m4_12_router
from services.m4_12_hidden_achievement.models import (
    HiddenAchievementModel,
    UserAchievementModel,
)
from services.m4_12_hidden_achievement.db import get_db


@pytest.fixture
def client(db_session):
    app = FastAPI()
    app.include_router(m4_12_router)

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    yield test_client


def test_zero_leakage_unearned_hidden_achievements_absent(client, db_session, seed_achievements):
    """
    T014/T015: 測試未解鎖之隱藏成就 100% 不出現在 API 回傳中。
    seed_achievements 中有 4 個全為 is_hidden=True 的成就。
    使用者 'user_newbie' 尚未解鎖任何成就，回傳 items 必須為空，
    且 raw JSON 內絕不能出現成就 ID、名稱或描述。
    """
    resp = client.get("/api/achievements?user_id=user_newbie")
    assert resp.status_code == 200
    data = resp.json()

    assert data["user_id"] == "user_newbie"
    assert data["total_unlocked_count"] == 0
    assert len(data["items"]) == 0

    # 檢驗 raw response text，確保零佔位、零洩漏
    raw_text = resp.text
    for ach in seed_achievements:
        assert ach.id not in raw_text
        assert ach.name not in raw_text
        assert ach.flavor_text_template not in raw_text


def test_zero_leakage_user_sees_only_own_unlocked_hidden_achievement(client, db_session, seed_achievements):
    """
    T014/T015: 使用者 Alice 解鎖了 cartographer，Bob 尚未解鎖。
    Alice 能看到 cartographer，但看不到其他 3 個隱藏成就。
    Bob 什麼都看不到。
    """
    cartographer = seed_achievements[0]
    user_ach = UserAchievementModel(
        id="ua_alice_01",
        user_id="user_alice",
        achievement_id=cartographer.id,
        origin_role_id="role_coder",
        xp_awarded=100,
        transaction_id="tx_001",
        context_summary="於編譯器架構對話中觸發",
        is_acknowledged=False,
    )
    db_session.add(user_ach)
    db_session.commit()

    # Alice 查詢
    resp_alice = client.get("/api/achievements?user_id=user_alice")
    assert resp_alice.status_code == 200
    data_alice = resp_alice.json()
    assert data_alice["total_unlocked_count"] == 1
    assert len(data_alice["items"]) == 1
    assert data_alice["items"][0]["id"] == cartographer.id
    assert data_alice["items"][0]["is_new"] is True

    # 確保 Alice 也看不到未解鎖的另外 3 個隱藏成就
    for other_ach in seed_achievements[1:]:
        assert other_ach.id not in resp_alice.text
        assert other_ach.name not in resp_alice.text

    # Bob 查詢
    resp_bob = client.get("/api/achievements?user_id=user_bob")
    assert resp_bob.status_code == 200
    data_bob = resp_bob.json()
    assert data_bob["total_unlocked_count"] == 0
    assert len(data_bob["items"]) == 0
    assert cartographer.id not in resp_bob.text


def test_denominator_excludes_unearned_hidden_achievements(client, db_session, seed_achievements):
    """
    T016: 驗證成就統計排除邏輯 (FR-006)。
    若系統中有 1 個公開成就與 4 個隱藏成就，
    Alice 解鎖 1 個隱藏成就，此時可見總數 (分母) 應為 1 (公開) + 1 (已解鎖隱藏) = 2，
    嚴禁將其餘 3 個未解鎖隱藏成就計入分母。
    """
    public_ach = HiddenAchievementModel(
        id="ach_public_first_chat",
        archetype="curiosity",
        name="初次對話",
        description="完成第一次自主提問",
        flavor_text_template="歡迎踏入旅程",
        rarity="rare",
        exp_reward=50,
        badge_icon_url="/assets/badges/first.svg",
        eval_rules_json="{}",
        is_hidden=False,  # 公開成就
    )
    db_session.add(public_ach)
    db_session.commit()

    # Bob 未解鎖任何成就
    resp_bob = client.get("/api/achievements?user_id=user_bob")
    data_bob = resp_bob.json()
    # total_visible_count 應為 1 (僅公開成就)
    assert data_bob.get("total_visible_count", 1) == 1
    assert data_bob["total_unlocked_count"] == 0


def test_denominator_no_double_counting_for_unlocked_public_achievement(client, db_session, seed_achievements):
    """
    驗證解鎖公開成就時，分母不會重複計算：
    系統有 1 個公開成就與 4 個隱藏成就。
    使用者 Charlie 同時解鎖了 1 個公開成就與 1 個隱藏成就。
    此時：
    - total_unlocked_count = 2
    - total_visible_count 必須為 1 (公開) + 1 (已解鎖隱藏) = 2 (絕非 1 + 2 = 3)
    """
    public_ach = HiddenAchievementModel(
        id="ach_public_readme",
        archetype="curiosity",
        name="閱讀手冊",
        description="閱讀使用手冊",
        flavor_text_template="知識的起點",
        rarity="rare",
        exp_reward=50,
        badge_icon_url="/assets/badges/read.svg",
        eval_rules_json="{}",
        is_hidden=False,
    )
    db_session.add(public_ach)
    db_session.commit()

    # Charlie 解鎖公開成就
    db_session.add(
        UserAchievementModel(
            id="ua_charlie_pub",
            user_id="user_charlie",
            achievement_id=public_ach.id,
            xp_awarded=50,
            transaction_id="tx_pub",
            is_acknowledged=True,
        )
    )
    # Charlie 解鎖隱藏成就
    db_session.add(
        UserAchievementModel(
            id="ua_charlie_hid",
            user_id="user_charlie",
            achievement_id=seed_achievements[0].id,
            xp_awarded=100,
            transaction_id="tx_hid",
            is_acknowledged=True,
        )
    )
    db_session.commit()

    resp = client.get("/api/achievements?user_id=user_charlie")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_unlocked_count"] == 2
    assert data["total_visible_count"] == 2  # 1 public + 1 hidden = 2 (無重複累加)

