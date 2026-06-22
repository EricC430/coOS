import pytest
from fastapi.testclient import TestClient
import uuid
from services.main import app
from m6_2_postgresql.engine import get_cloud_session
from sqlalchemy import text

client = TestClient(app)

@pytest.fixture
def unique_headers():
    uid = str(uuid.uuid4())
    rid = str(uuid.uuid4())
    
    # If cloud connection is configured, insert this user so ForeignKey constraints are satisfied
    session = get_cloud_session()
    if session is not None:
        try:
            session.execute(
                text("INSERT INTO users (id, display_name) VALUES (:uid, 'Test User') ON CONFLICT DO NOTHING"),
                {"uid": uid}
            )
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error seeding test user: {e}")
        finally:
            session.close()

    return {
        "X-User-Id": uid,
        "X-Role-ID": rid,
        "Content-Type": "application/json"
    }

def test_list_communities_fallback(unique_headers):
    # Tests that /api/m6_6/communities responds with mock or live communities
    response = client.get("/api/m6_6/communities", headers=unique_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "id" in data[0]
        assert "name" in data[0]
        assert "type" in data[0]

def test_explore_communities(unique_headers):
    response = client.get("/api/m6_6/communities/explore", headers=unique_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "id" in data[0]
        assert "name" in data[0]
        assert "type" in data[0]


def test_create_community_mock_or_real(unique_headers):
    payload = {
        "name": "New Test Community",
        "type": "user_created",
        "member_cap": 6
    }
    response = client.post("/api/m6_6/communities", json=payload, headers=unique_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New Test Community"
    assert data["member_cap"] == 6

def test_join_community(unique_headers):
    payload = {
        "mode": "system_random",
        "theme": "study"
    }
    response = client.post("/api/m6_6/communities/join", json=payload, headers=unique_headers)
    assert response.status_code in (200, 404)

def test_get_codex(unique_headers):
    # Fetch first community to get a valid ID
    res_list = client.get("/api/m6_6/communities", headers=unique_headers)
    assert res_list.status_code == 200
    comms = res_list.json()
    if comms:
        comm_id = comms[0]["id"]
        response = client.get(f"/api/m6_6/communities/{comm_id}/codex", headers=unique_headers)
        assert response.status_code == 200
        data = response.json()
        assert "goal" in data
        assert "rules" in data

def test_post_draft_and_publish_flow(unique_headers):
    # Create community first to ensure we are a member
    payload = {
        "name": "Flow Test Community",
        "type": "user_created",
        "member_cap": 5
    }
    comm_res = client.post("/api/m6_6/communities", json=payload, headers=unique_headers)
    assert comm_res.status_code == 200
    comm_id = comm_res.json()["id"]

    # Create draft
    draft_payload = {
        "community_id": comm_id,
        "content": "This is a test post that passes Eguard.",
        "kind": "achievement"
    }
    response = client.post("/api/m6_6/posts/draft", json=draft_payload, headers=unique_headers)
    assert response.status_code == 200
    draft_data = response.json()
    assert draft_data["is_draft"] is True
    assert "id" in draft_data

    # Publish draft
    publish_payload = {
        "draft_id": draft_data["id"]
    }
    pub_response = client.post("/api/m6_6/posts/publish", json=publish_payload, headers=unique_headers)
    assert pub_response.status_code == 200
    pub_data = pub_response.json()
    assert pub_data["published"] is True

def test_like_post(unique_headers):
    # Create community first
    payload = {
        "name": "Like Test Community",
        "type": "user_created",
        "member_cap": 5
    }
    comm_res = client.post("/api/m6_6/communities", json=payload, headers=unique_headers)
    assert comm_res.status_code == 200
    comm_id = comm_res.json()["id"]

    # Create draft
    draft_payload = {
        "community_id": comm_id,
        "content": "Post to be liked",
        "kind": "achievement"
    }
    draft_res = client.post("/api/m6_6/posts/draft", json=draft_payload, headers=unique_headers)
    assert draft_res.status_code == 200
    draft_id = draft_res.json()["id"]

    # Publish
    pub_res = client.post("/api/m6_6/posts/publish", json={"draft_id": draft_id}, headers=unique_headers)
    assert pub_res.status_code == 200

    # Like
    response = client.post(f"/api/m6_6/posts/{draft_id}/like", headers=unique_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["likes_count"] >= 1

def test_list_stakes(unique_headers):
    response = client.get("/api/m6_6/stakes", headers=unique_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_create_stake_allowed(unique_headers):
    # Create community first
    payload = {
        "name": "Stake Test Community",
        "type": "user_created",
        "member_cap": 5
    }
    comm_res = client.post("/api/m6_6/communities", json=payload, headers=unique_headers)
    assert comm_res.status_code == 200
    comm_id = comm_res.json()["id"]

    stake_payload = {
        "xp_amount": 50,
        "community_id": comm_id,
        "deadline": "2026-06-25T00:00:00"
    }
    response = client.post("/api/m6_6/stakes", json=stake_payload, headers=unique_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["xp_amount"] == 50
    assert data["status"] == "held"

def test_create_stake_blocked_by_invalid_amount(unique_headers):
    # Create community first
    payload = {
        "name": "Stake Fail Community",
        "type": "user_created",
        "member_cap": 5
    }
    comm_res = client.post("/api/m6_6/communities", json=payload, headers=unique_headers)
    assert comm_res.status_code == 200
    comm_id = comm_res.json()["id"]

    stake_payload = {
        "xp_amount": -10,
        "community_id": comm_id
    }
    response = client.post("/api/m6_6/stakes", json=stake_payload, headers=unique_headers)
    assert response.status_code == 422  # validation error (gt=0)


def test_update_codex(unique_headers):
    # Create community first
    payload = {
        "name": "Codex Test Community",
        "type": "user_created",
        "member_cap": 5
    }
    comm_res = client.post("/api/m6_6/communities", json=payload, headers=unique_headers)
    assert comm_res.status_code == 200
    comm_id = comm_res.json()["id"]

    codex_payload = {
        "goal": "New Test Goal",
        "vision": "New Test Vision",
        "codex": "New Test Codex",
        "rules": ["Rule 1", "Rule 2"],
        "quotes": ["Quote 1"]
    }
    response = client.post(f"/api/m6_6/communities/{comm_id}/codex", json=codex_payload, headers=unique_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["goal"] == "New Test Goal"
    assert "Rule 1" in data["rules"]


def test_create_challenge(unique_headers):
    # Create community first
    payload = {
        "name": "Challenge Test Community",
        "type": "user_created",
        "member_cap": 5
    }
    comm_res = client.post("/api/m6_6/communities", json=payload, headers=unique_headers)
    assert comm_res.status_code == 200
    comm_id = comm_res.json()["id"]

    ch_payload = {
        "title": "Manual Challenge",
        "description": "Manual Desc",
        "period": "weekly",
        "source": "admin"
    }
    response = client.post(f"/api/m6_6/communities/{comm_id}/challenges", json=ch_payload, headers=unique_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Manual Challenge"
    assert data["source"] == "admin"


def test_generate_ai_challenge(unique_headers):
    # Create community first
    payload = {
        "name": "AI Challenge Community",
        "type": "user_created",
        "member_cap": 3  # Enforce conservative template
    }
    comm_res = client.post("/api/m6_6/communities", json=payload, headers=unique_headers)
    assert comm_res.status_code == 200
    comm_id = comm_res.json()["id"]

    response = client.post(f"/api/m6_6/communities/{comm_id}/challenges/generate-ai", headers=unique_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["source"] == "ai_reviewed"
    assert data["is_draft"] is True
    # Verify conservative template is used because member_cap = 3
    assert "社群挑戰" in data["title"] or "學習" in data["title"]


def test_validate_with_evidence(unique_headers):
    # Create community first
    payload = {
        "name": "Validation Test Community",
        "type": "user_created",
        "member_cap": 5
    }
    comm_res = client.post("/api/m6_6/communities", json=payload, headers=unique_headers)
    assert comm_res.status_code == 200
    comm_id = comm_res.json()["id"]

    # Create post draft
    draft_payload = {
        "community_id": comm_id,
        "content": "Evidence test post",
        "kind": "achievement"
    }
    draft_res = client.post("/api/m6_6/posts/draft", json=draft_payload, headers=unique_headers)
    assert draft_res.status_code == 200
    post_id = draft_res.json()["id"]

    # Publish post
    client.post("/api/m6_6/posts/publish", json={"draft_id": post_id}, headers=unique_headers)

    # Validate with evidence
    val_payload = {
        "post_id": post_id,
        "evidence_url": "https://example.com/screenshot.png"
    }
    response = client.post("/api/m6_6/validations", json=val_payload, headers=unique_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["post_id"] == post_id

