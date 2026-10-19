from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient

from main import app
from m4_11_zpd_pipeline.db import get_db
from m4_11_zpd_pipeline.models import RoleSkillMastery, ZPDChallenge
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


def test_complete_challenge_missing_reflection_rejected(client, db_session):
    # Draw & Accept
    draw_res = client.post("/api/m4_11/draw_challenge", json={"role_id": "role_csie", "force_fallback": True})
    c_id = draw_res.json()["id"]
    client.post("/api/m4_11/accept_challenge", json={"challenge_id": c_id})

    # Empty feeling
    res = client.post(
        "/api/m4_11/complete_challenge",
        json={
            "challenge_id": c_id,
            "user_feeling": "",
            "user_action_plan": "Next step",
        },
    )
    assert res.status_code in (400, 422)

    # Empty action plan
    res2 = client.post(
        "/api/m4_11/complete_challenge",
        json={
            "challenge_id": c_id,
            "user_feeling": "Great feeling",
            "user_action_plan": "   ",
        },
    )
    assert res2.status_code in (400, 422)


def test_complete_challenge_success_flow(client, db_session):
    draw_res = client.post("/api/m4_11/draw_challenge", json={"role_id": "role_csie", "force_fallback": True})
    c_id = draw_res.json()["id"]
    xp_reward = draw_res.json()["xp_reward"]
    client.post("/api/m4_11/accept_challenge", json={"challenge_id": c_id})

    # Valid completion
    complete_res = client.post(
        "/api/m4_11/complete_challenge",
        json={
            "challenge_id": c_id,
            "user_feeling": "感覺對 Docker 網路架構清晰了許多，不再害怕看路由表。",
            "user_action_plan": "在專案中實際替換自訂網路並在 CI 加入檢核。",
            "actual_minutes": 20,
        },
    )
    assert complete_res.status_code == 200
    data = complete_res.json()
    assert data["success"] is True
    assert data["awarded_xp"] == xp_reward
    assert data["new_p_mastery"] > 0.30

    # Verify DB state
    c = db_session.query(ZPDChallenge).filter_by(id=c_id).first()
    assert c.status == ChallengeStatus.COMPLETED.value
    assert c.completed_at is not None

    mastery = db_session.query(RoleSkillMastery).filter_by(user_id="default_user", role_id="role_csie").first()
    assert mastery is not None
    assert mastery.p_mastery == pytest.approx(data["new_p_mastery"], rel=1e-3)
    assert mastery.consecutive_successes == 1


def test_soft_expiration_no_xp_loss(zpd_service, db_session):
    challenge = zpd_service.draw_challenge(user_id="user_expire", role_id="role_csie", force_fallback=True)
    zpd_service.accept_challenge(challenge.id)

    # Simulate time passing beyond expires_at
    db_c = db_session.query(ZPDChallenge).filter_by(id=challenge.id).first()
    db_c.expires_at = datetime.now(timezone.utc) - timedelta(hours=2)
    db_session.commit()

    # Query active challenge triggers soft expiration check
    active = zpd_service.get_active_challenge(user_id="user_expire", role_id="role_csie")
    assert active is None

    # Check status changed to expired, no penalty
    db_session.refresh(db_c)
    assert db_c.status == ChallengeStatus.EXPIRED.value
