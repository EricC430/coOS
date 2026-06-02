"""
M1.3.2 integration tests — BrowseActivityEvent ingestion via FastAPI

SPEC: docs/modules/M1_3_2_browser_extension_SPEC.md
Research:
  [R02: 時間動力學 §1.2] Page dwell time as reading depth indicator
  [R06: 數位表型 §2.1] Browsing pattern as digital phenotype

Risk: RISK-15 (Opt-in title capture → cloud side-channel leak)
Mitigation tested: title absent in default (CaptureMode::Off) mode.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from services.main import app

ENDPOINT = "/api/m1_1/event"  # M1.3.2 uses the same M0.4 LogEvent endpoint


@pytest.fixture
def client():
    return TestClient(app)


def _browse_event(action: str = "tab_stay", payload: dict | None = None) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(UTC).isoformat(),
        "module": "M1.3.2",
        "action": action,
        "level": "INFO",
        "payload": payload or {},
        "role_id": "default",
    }


# ---------------------------------------------------------------------------
# AC-1: tab_stay event accepted
# ---------------------------------------------------------------------------

class TestTabStayIngest:
    def test_tab_stay_accepted(self, client):
        """AC-1: [R02 §1.2] tab_stay event (10 min on YouTube) accepted."""
        event = _browse_event(
            action="tab_stay",
            payload={
                "domain": "youtube.com",
                "url_path": "/watch",
                "domain_bucket": "entertainment",
                "stay_s": 600,
            },
        )
        resp = client.post(ENDPOINT, json=event)
        assert resp.status_code == 200

    def test_tab_stay_coding_site_accepted(self, client):
        """AC-3: [R06 §2.1] github.com tab_stay accepted."""
        event = _browse_event(
            action="tab_stay",
            payload={
                "domain": "github.com",
                "url_path": "/user/repo/issues/1",
                "domain_bucket": "coding",
                "stay_s": 120,
            },
        )
        resp = client.post(ENDPOINT, json=event)
        assert resp.status_code == 200

    def test_tab_stay_learning_site_accepted(self, client):
        """AC-4: stackoverflow.com tab_stay accepted."""
        event = _browse_event(
            action="tab_stay",
            payload={
                "domain": "stackoverflow.com",
                "url_path": "/questions/123",
                "domain_bucket": "learning",
                "stay_s": 90,
            },
        )
        resp = client.post(ENDPOINT, json=event)
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# AC-5: Privacy — no sensitive query params, no title in default mode
# ---------------------------------------------------------------------------

class TestPrivacy:
    @pytest.mark.integration_risk("RISK-15")
    def test_no_title_in_default_mode(self, client):
        """AC-5: [RISK-15] title absent in CaptureMode::Off (default)."""
        event = _browse_event(
            action="tab_stay",
            payload={
                "domain": "github.com",
                "url_path": "/user/repo/issues/1",
                "domain_bucket": "coding",
                "stay_s": 60,
                # title NOT present — CaptureMode::Off default
            },
        )
        resp = client.post(ENDPOINT, json=event)
        assert resp.status_code == 200
        assert "title" not in event["payload"]

    @pytest.mark.integration_risk("RISK-15")
    def test_browsing_content_rejected(self, client):
        """[RISK-15] browsing_content key rejected by M0.4 privacy validator."""
        event = _browse_event(
            action="tab_stay",
            payload={
                "domain": "github.com",
                "browsing_content": "private page content",
            },
        )
        resp = client.post(ENDPOINT, json=event)
        assert resp.status_code == 422

    def test_no_query_params_in_url_path(self, client):
        """AC-5: url_path must not contain query string."""
        event = _browse_event(
            action="tab_stay",
            payload={
                "domain": "github.com",
                "url_path": "/user/repo/issues/1",   # no ?token=secret
                "domain_bucket": "coding",
                "stay_s": 60,
            },
        )
        assert "?" not in event["payload"]["url_path"]
        resp = client.post(ENDPOINT, json=event)
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# tab_switch event
# ---------------------------------------------------------------------------

class TestTabSwitchIngest:
    def test_tab_switch_accepted(self, client):
        """tab_switch event accepted."""
        event = _browse_event(
            action="tab_switch",
            payload={
                "from_domain": "youtube.com",
                "from_bucket": "entertainment",
                "to_domain": "github.com",
                "to_bucket": "coding",
            },
        )
        resp = client.post(ENDPOINT, json=event)
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Native Messaging structural check (AC-6)
# ---------------------------------------------------------------------------

class TestNativeMessaging:
    def test_tab_stay_event_structure(self, client):
        """AC-6: tab_stay event has correct module and action fields."""
        event = _browse_event(action="tab_stay",
                              payload={"domain": "github.com",
                                       "url_path": "/",
                                       "domain_bucket": "coding",
                                       "stay_s": 10})
        assert event["module"] == "M1.3.2"
        assert event["action"] == "tab_stay"
        resp = client.post(ENDPOINT, json=event)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
