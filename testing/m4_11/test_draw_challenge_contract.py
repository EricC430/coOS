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


def test_draw_challenge_contract(client, db_session):
    response = client.post(
        "/api/m4_11/draw_challenge",
        json={"role_id": "role_csie", "force_fallback": True},
    )
    assert response.status_code == 200
    data = response.json()

    # Verify openapi.yaml required fields
    required_fields = [
        "id",
        "role_id",
        "title",
        "description",
        "task_type",
        "is_real_world",
        "difficulty",
        "skill_domain",
        "estimated_minutes",
        "xp_reward",
        "status",
        "zpd_zone",
        "scaffolding_hints",
        "expires_at",
    ]
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"

    assert data["role_id"] == "role_csie"
    assert data["status"] == ChallengeStatus.GENERATED.value
    assert isinstance(data["scaffolding_hints"], list)
    assert len(data["scaffolding_hints"]) >= 1
    assert data["estimated_minutes"] >= 10
    assert data["xp_reward"] >= 10


def test_accept_and_active_challenge_lifecycle(client, db_session):
    # 1. Draw challenge
    draw_resp = client.post(
        "/api/m4_11/draw_challenge",
        json={"role_id": "role_csie", "force_fallback": True},
    )
    assert draw_resp.status_code == 200
    challenge_id = draw_resp.json()["id"]

    # 2. Before accept, active challenge is None
    active_resp = client.get("/api/m4_11/active_challenge?role_id=role_csie")
    assert active_resp.status_code == 200
    assert active_resp.json()["active_challenge"] is None

    # 3. Accept challenge
    accept_resp = client.post(
        "/api/m4_11/accept_challenge",
        json={"challenge_id": challenge_id, "replace_existing": True},
    )
    assert accept_resp.status_code == 200
    accept_data = accept_resp.json()
    assert accept_data["success"] is True
    assert accept_data["active_challenge"]["id"] == challenge_id
    assert accept_data["active_challenge"]["status"] == ChallengeStatus.ACCEPTED.value

    # 4. Check active challenge returns accepted task
    active_resp2 = client.get("/api/m4_11/active_challenge?role_id=role_csie")
    assert active_resp2.status_code == 200
    assert active_resp2.json()["active_challenge"]["id"] == challenge_id

    # 5. Draw and accept a second challenge, replacing the previous one
    draw_resp2 = client.post(
        "/api/m4_11/draw_challenge",
        json={"role_id": "role_csie", "force_fallback": True},
    )
    challenge_id_2 = draw_resp2.json()["id"]

    accept_resp2 = client.post(
        "/api/m4_11/accept_challenge",
        json={"challenge_id": challenge_id_2, "replace_existing": True},
    )
    assert accept_resp2.status_code == 200
    assert accept_resp2.json()["active_challenge"]["id"] == challenge_id_2

    # Verify old challenge became abandoned in DB
    from m4_11_zpd_pipeline.models import ZPDChallenge
    old_c = db_session.query(ZPDChallenge).filter_by(id=challenge_id).first()
    assert old_c.status == ChallengeStatus.ABANDONED.value
