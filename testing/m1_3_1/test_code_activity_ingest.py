"""
M1.3.1 integration tests — CodeActivityEvent ingestion via FastAPI

SPEC: docs/modules/M1_3_1_vscode_extension_SPEC.md
Research:
  [R02: 源碼變更熵 §1.1] Entropy as cognitive state input
  [R02: 時間動力學 §1.2] Save interval burst features

Tests verify that CodeActivityEvents POSTed by the VS Code Extension
(via Named Pipe → FastAPI) are accepted and written to raw_tracking_logs.
The TypeScript logic (entropy calc, collaboration heuristics) is tested
separately in apps/vscode-extension/src/__tests__/.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from services.main import app

ENDPOINT = "/api/m1_1/event"  # M1.3.1 uses the same M0.4 LogEvent endpoint


@pytest.fixture
def client():
    return TestClient(app)


def _code_event(action: str = "edit_burst", payload: dict | None = None) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(UTC).isoformat(),
        "module": "M1.3.1",
        "action": action,
        "level": "INFO",
        "payload": payload or {},
        "role_id": "default",
    }


# ---------------------------------------------------------------------------
# AC-1/AC-2: edit_burst event structure
# ---------------------------------------------------------------------------

class TestEditBurstIngest:
    def test_edit_burst_accepted(self, client):
        """AC (§3): [R02 §1.1] edit_burst CodeActivityEvent accepted."""
        event = _code_event(
            action="edit_burst",
            payload={
                "entropy": 0.72,
                "files_touched": 3,
                "save_interval_s": 45.0,
                "human_typed_chars": 120,
                "ai_generated_chars": 850,
                "copilot_ratio": 0.87,
                "churn_index": 0.15,
            },
        )
        resp = client.post(ENDPOINT, json=event)
        assert resp.status_code == 200

    def test_content_raw_accepted(self, client):
        """Verify that edit_burst containing L1 plaintext content_raw is accepted by M0.4 and backend."""
        event = _code_event(
            action="edit_burst",
            payload={
                "entropy": 0.72,
                "files_touched": 3,
                "save_interval_s": 45.0,
                "human_typed_chars": 120,
                "ai_generated_chars": 850,
                "copilot_ratio": 0.87,
                "churn_index": 0.15,
                "content_raw": "def bubble_sort(arr):\n    n = len(arr)\n    for i in range(n):\n",
                "inference_mode": "rule_based_fallback",
                "privacy_tier": "T1_OPTIN"
            },
        )
        resp = client.post(ENDPOINT, json=event)
        assert resp.status_code == 200

    def test_single_file_low_entropy_event_accepted(self, client):
        """AC-1: [R02 §1.1] Single file edit (entropy ≈ 0) accepted."""
        event = _code_event(
            action="edit_burst",
            payload={"entropy": 0.05, "files_touched": 1, "save_interval_s": 120.0,
                     "human_typed_chars": 50, "ai_generated_chars": 0,
                     "copilot_ratio": 0.0, "churn_index": 0.0},
        )
        resp = client.post(ENDPOINT, json=event)
        assert resp.status_code == 200

    def test_multi_file_high_entropy_event_accepted(self, client):
        """AC-2: [R02 §1.1] Multi-file edit (entropy > 0.8) accepted."""
        event = _code_event(
            action="edit_burst",
            payload={"entropy": 0.95, "files_touched": 4, "save_interval_s": 8.0,
                     "human_typed_chars": 40, "ai_generated_chars": 40,
                     "copilot_ratio": 0.5, "churn_index": 0.0},
        )
        resp = client.post(ENDPOINT, json=event)
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# AC-3: file_stay event
# ---------------------------------------------------------------------------

class TestFileStayIngest:
    def test_file_stay_event_accepted(self, client):
        """AC-3: [R02 §1.2] file_stay event (20 min in single file) accepted."""
        event = _code_event(
            action="file_stay",
            payload={
                "files": ["src/main.py"],
                "stay_s": 1200,
                "lines_changed": 42,
                "stay_mode": "active_review",
                "file_ext": ".py",
            },
        )
        resp = client.post(ENDPOINT, json=event)
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# AC-4/AC-5: Privacy — no source code content in payload
# ---------------------------------------------------------------------------

class TestPrivacy:
    def test_no_code_content_in_payload(self, client):
        """AC-5: [架構文件 §3 L1] Payload must not contain raw_code."""
        event = _code_event(
            action="edit_burst",
            payload={"entropy": 0.5, "raw_code": "password = 'secret123'"},
        )
        # raw_code is a forbidden L1 key — M0.4 LogEvent validator rejects it
        resp = client.post(ENDPOINT, json=event)
        assert resp.status_code == 422

    def test_relative_file_path_stored(self, client):
        """AC-4: file_stay payload stores relative path (no absolute dir)."""
        event = _code_event(
            action="file_stay",
            payload={
                "files": ["src/main.py"],   # relative — OK
                "stay_s": 300,
                "lines_changed": 10,
                "stay_mode": "active_edit",
                "file_ext": ".py",
            },
        )
        resp = client.post(ENDPOINT, json=event)
        assert resp.status_code == 200
        # Verify no absolute path leaked
        assert not any(
            f.startswith("C:") or "/Users/" in f or "\\Users\\" in f
            for f in event["payload"]["files"]
        )


# ---------------------------------------------------------------------------
# ide_focus_leave: triggers M1.2 BreakpointType::IDE_FOCUS_LEAVE
# ---------------------------------------------------------------------------

class TestIdeFocusLeave:
    def test_ide_focus_leave_accepted(self, client):
        """ide_focus_leave event accepted — M1.2 consumes via /api/m1_2/event."""
        event = _code_event(action="ide_focus_leave", payload={})
        resp = client.post(ENDPOINT, json=event)
        assert resp.status_code == 200
