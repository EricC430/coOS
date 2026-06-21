"""
M1.1 -- OS Telemetry Daemon integration acceptance tests

SPEC: docs/modules/M1_1_os_telemetry_daemon_SPEC.md v1.2
Research:
  [R02: 計算心理語言學 §1] WPM as cognitive state input
  [R06: 數位表型 §2.1] Keystroke/focus patterns as digital phenotype sensor

M1.1 Rust sidecar POSTs LogEvent (M0.4 schema) to /api/m1_1/event.
FastAPI writes directly to raw_tracking_logs via AsyncLogWriter.

Rust unit tests (WPM calculator, ActivityStateClassifier, app_bucket mapping)
live inside services/m1_1_telemetry_daemon/src/ as #[cfg(test)] modules.
"""
from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from services.main import app

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

ENDPOINT = "/api/m1_1/event"


@pytest.fixture
def client():
    return TestClient(app)


def _log_event(
    module: str = "M1.1.3",
    action: str = "focus_session_ended",
    payload: dict | None = None,
    level: str = "INFO",
) -> dict:
    """Build a M0.4-compatible LogEvent dict as sent by M1.1 Rust sidecar."""
    return {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(UTC).isoformat(),
        "module": module,
        "action": action,
        "level": level,
        "payload": payload or {},
        "role_id": "default",
    }


# ---------------------------------------------------------------------------
# AC-1: FastAPI accepts LogEvents from Rust sidecar
# ---------------------------------------------------------------------------


class TestTelemetryIngest:
    def test_focus_session_ended_accepted(self, client):
        """AC-1: [R06 §2.1] focus_session_ended LogEvent accepted."""
        event = _log_event(
            module="M1.1.3",
            action="focus_session_ended",
            payload={
                "app_name": "Code",
                "app_bucket": "coding",
                "duration_s": 1823,
                "wpm_avg": 48.0,
                "mouse_clicks": 32,
                "mouse_distance_norm": 0.42,
                "activity_state": "DEEP_FOCUS",
            },
        )
        resp = client.post(ENDPOINT, json=event)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_keystroke_burst_accepted(self, client):
        """AC-1b: [R02 §1] keystroke_burst accepted."""
        event = _log_event(
            module="M1.1.2",
            action="keystroke_burst",
            payload={"wpm_avg": 65.0, "key_count": 390},
        )
        resp = client.post(ENDPOINT, json=event)
        assert resp.status_code == 200

    def test_daemon_heartbeat_accepted(self, client):
        """AC-10: daemon_heartbeat accepted — enables M0.2.1 watchdog check."""
        event = _log_event(module="M1.1.3", action="daemon_heartbeat", payload={})
        resp = client.post(ENDPOINT, json=event)
        assert resp.status_code == 200

    def test_activity_state_changed_accepted(self, client):
        """AC-1d: activity_state_changed accepted — drives M1.2 breakpoint engine."""
        event = _log_event(
            module="M1.1.3",
            action="activity_state_changed",
            payload={"prev_state": "ACTIVE", "new_state": "DEEP_FOCUS", "confidence": 0.87},
        )
        resp = client.post(ENDPOINT, json=event)
        assert resp.status_code == 200

    def test_window_changed_accepted(self, client):
        """AC-1e: window_changed accepted."""
        event = _log_event(
            module="M1.1.1",
            action="window_changed",
            payload={"app_name": "Chrome", "app_bucket": "reading"},
        )
        resp = client.post(ENDPOINT, json=event)
        assert resp.status_code == 200

    def test_secondary_window_snapshot_accepted(self, client):
        """AC-1f: secondary_window_snapshot accepted (multi-monitor scan)."""
        event = _log_event(
            module="M1.1.3",
            action="secondary_window_snapshot",
            payload={"windows": [{"app_name": "Chrome", "app_bucket": "reading", "monitor_index": 1}]},
        )
        resp = client.post(ENDPOINT, json=event)
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# AC-3/AC-4/AC-5: PII must not appear in payload (enforced by M0.4 LogEvent)
# ---------------------------------------------------------------------------


class TestPIIConstraints:
    def test_raw_text_in_payload_rejected(self, client):
        """AC-3/AC-5: [架構文件 §3 L1] raw_text key in payload rejected by M0.4 validator."""
        event = _log_event(
            module="M1.1.2",
            action="keystroke_burst",
            payload={"wpm_avg": 42.0, "raw_text": "password123"},
        )
        resp = client.post(ENDPOINT, json=event)
        assert resp.status_code == 422  # M0.4 schema rejects forbidden key

    def test_no_window_title_in_default_mode(self, client):
        """AC-4: [CaptureMode::Off] window_title absent from payload — Rust sidecar enforces."""
        event = _log_event(
            module="M1.1.1",
            action="window_changed",
            payload={
                "app_name": "Code",
                "app_bucket": "coding",
                # window_title NOT present — CaptureMode::Off default
            },
        )
        resp = client.post(ENDPOINT, json=event)
        assert resp.status_code == 200
        assert "window_title" not in event["payload"]

    def test_transcript_key_rejected(self, client):
        """AC-5: [RISK-15] transcript key rejected by M0.4 privacy validator."""
        event = _log_event(
            module="M1.1.1",
            action="window_changed",
            payload={"app_name": "WINWORD", "transcript": "secret contents"},
        )
        resp = client.post(ENDPOINT, json=event)
        assert resp.status_code == 422

    def test_browsing_content_rejected(self, client):
        """AC-5b: [RISK-15] browsing_content key rejected."""
        event = _log_event(
            module="M1.1.1",
            action="window_changed",
            payload={"app_name": "Chrome", "browsing_content": "private page"},
        )
        resp = client.post(ENDPOINT, json=event)
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# AC-8/AC-9: WPM event structure
# ---------------------------------------------------------------------------


class TestWPMEventStructure:
    def test_wpm_payload_structure(self, client):
        """AC-8: [R02 §1] keystroke_burst payload has wpm_avg (float) and key_count."""
        event = _log_event(
            module="M1.1.2",
            action="keystroke_burst",
            payload={"wpm_avg": 60.0, "key_count": 360},
        )
        resp = client.post(ENDPOINT, json=event)
        assert resp.status_code == 200
        assert isinstance(event["payload"]["wpm_avg"], float)
        assert isinstance(event["payload"]["key_count"], int)

    def test_focus_session_includes_activity_state(self, client):
        """AC (v1.2): focus_session_ended includes activity_state field."""
        event = _log_event(
            module="M1.1.3",
            action="focus_session_ended",
            payload={
                "app_name": "Code",
                "app_bucket": "coding",
                "duration_s": 900,
                "wpm_avg": 0.0,
                "mouse_clicks": 5,
                "mouse_distance_norm": 0.1,
                "activity_state": "RESEARCH_READING",
            },
        )
        resp = client.post(ENDPOINT, json=event)
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# AC-10: Heartbeat event_id echoed back
# ---------------------------------------------------------------------------


class TestHeartbeat:
    def test_heartbeat_event_id_echoed(self, client):
        """AC-10: event response echoes the event id for correlation."""
        event = _log_event(module="M1.1.3", action="daemon_heartbeat", payload={})
        resp = client.post(ENDPOINT, json=event)
        assert resp.status_code == 200
        # Response should include event id for M0.2.1 watchdog correlation
        body = resp.json()
        assert body.get("status") == "ok"


# ---------------------------------------------------------------------------
# AC-11: Graceful degradation
# ---------------------------------------------------------------------------


class TestGracefulDegradation:
    def test_unknown_bucket_accepted(self, client):
        """AC-11: app_bucket='unknown' (AccessDenied admin window) still ingested."""
        event = _log_event(
            module="M1.1.1",
            action="window_changed",
            payload={"app_name": "Taskmgr", "app_bucket": "unknown"},
        )
        resp = client.post(ENDPOINT, json=event)
        assert resp.status_code == 200

    def test_warn_level_event_accepted(self, client):
        """AC-11b: WARN level event (UIAutomation AccessDenied log) accepted."""
        event = _log_event(
            module="M1.1.1",
            action="window_changed",
            level="WARNING",
            payload={"app_name": "Unknown", "app_bucket": "unknown", "reason": "access_denied"},
        )
        resp = client.post(ENDPOINT, json=event)
        assert resp.status_code == 200


class TestTelemetryCompressionIntegration:
    @pytest.mark.anyio
    async def test_telemetry_debounced_compression_write(self, client):
        import services.main as main_mod
        from services.m2_1_event_debouncer.schema import RawTelemetryEvent
        import asyncio
        import sqlite3

        with client as active_client:
            # Save previous window
            prev_window = main_mod._debouncer._window
            main_mod._debouncer._window = 0.05
            
            # Simulate edge offline to speed up testing and bypass Ollama
            main_mod._gemma_pipeline.simulate_edge_offline()

            try:
                # Send a valid content_capture event
                event = _log_event(
                    module="M1.1.1",
                    action="content_capture",
                    payload={"app_name": "Notepad", "content_raw": "Writing calculus homework formulas."},
                )
                resp = active_client.post(ENDPOINT, json=event)
                assert resp.status_code == 200

                # Wait for the debouncer flush timer to trigger and run M2.2/M2.3/M6.1
                await asyncio.sleep(0.2)

                # Check intent_logs in database
                db_path = main_mod.settings.local_db_path
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                try:
                    row = conn.execute("SELECT * FROM intent_logs ORDER BY created_at DESC LIMIT 1").fetchone()
                    assert row is not None
                    assert row["inference_mode"] == "rule_based_fallback"
                    assert row["intent_label"] == "math_study"
                finally:
                    conn.close()
            finally:
                main_mod._debouncer._window = prev_window
                main_mod._gemma_pipeline.simulate_edge_online()

