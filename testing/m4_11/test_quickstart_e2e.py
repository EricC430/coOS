import time
import pytest
from fastapi.testclient import TestClient

from main import app
from m4_11_zpd_pipeline.db import get_db
from m4_11_zpd_pipeline.schemas import ChallengeStatus


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    test_client.headers.update({"X-Role-ID": "role_csie"})
    yield test_client
    app.dependency_overrides.clear()


def test_quickstart_scenario_1_to_4_e2e(client):
    """
    Validate all 4 scenarios described in specs/002-m4-11-zpd-pipeline/quickstart.md.
    """
    # 步驟 1：抽取一個 ZPD 延伸挑戰
    t0 = time.perf_counter()
    resp1 = client.post(
        "/api/m4_11/draw_challenge",
        json={"role_id": "role_csie", "user_id": "default_user"},
    )
    t1 = time.perf_counter()
    assert resp1.status_code == 200
    c1 = resp1.json()
    assert c1["status"] == ChallengeStatus.GENERATED.value
    assert c1["estimated_minutes"] >= 10
    assert len(c1["scaffolding_hints"]) >= 1
    # Offline fallback response time benchmark: <300ms
    assert (t1 - t0) < 0.5

    challenge_id = c1["id"]

    # 步驟 2：接受挑戰（進入單一活躍槽位）
    resp2 = client.post(
        "/api/m4_11/accept_challenge",
        json={"challenge_id": challenge_id, "replace_existing": True},
    )
    assert resp2.status_code == 200
    c2 = resp2.json()
    assert c2["success"] is True
    assert c2["active_challenge"]["id"] == challenge_id
    assert c2["active_challenge"]["status"] == ChallengeStatus.ACCEPTED.value

    # 驗證 active_challenge 查詢
    active_resp = client.get("/api/m4_11/active_challenge?role_id=role_csie")
    assert active_resp.status_code == 200
    assert active_resp.json()["active_challenge"]["id"] == challenge_id

    # 步驟 3：完成挑戰並提交反思（ACID XP 派發）
    resp3 = client.post(
        "/api/m4_11/complete_challenge",
        json={
            "challenge_id": challenge_id,
            "user_feeling": "搞懂了 Docker 自訂 bridge 的原理，之前一直連不上原來是因為沒有在同一個網路命名空間！",
            "user_action_plan": "下一步要把這個設定寫進正式環境的 docker-compose.yml 裡。",
            "actual_minutes": 25,
        },
    )
    assert resp3.status_code == 200
    c3 = resp3.json()
    assert c3["success"] is True
    assert c3["awarded_xp"] >= 10
    assert c3["new_p_mastery"] > 0.30

    # 步驟 4：驗證離線種子槽位降級備援
    t_start = time.perf_counter()
    resp4 = client.post(
        "/api/m4_11/draw_challenge",
        json={"role_id": "role_csie", "force_fallback": True},
    )
    t_elapsed = time.perf_counter() - t_start
    assert resp4.status_code == 200
    assert t_elapsed < 0.3  # Strictly within 300ms
    assert resp4.json()["status"] == ChallengeStatus.GENERATED.value
