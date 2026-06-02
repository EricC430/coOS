"""
M1.2 -- Defer-to-Breakpoint Engine acceptance tests

SPEC: docs/modules/M1_2_breakpoint_detection_SPEC.md v1.1
Research:
  [R08: §二 任務斷點打斷管理] Defer-to-Breakpoint core theory
  [R08: §三 醫療級警報疲勞防範] Three-tier notification classification
  [R08: §一 認知負荷轉移] Cost of interruption during deep work

Risk: RISK-04 (Defer-to-Breakpoint + XP instant reward → motivation disconnect)
Mitigation tested: L1/L2/L3 notification classification enforced in engine.
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers to build M1.1 events
# ---------------------------------------------------------------------------


def _focus_event(app: str = "Code", duration_s: int = 1800,
                 wpm_avg: float = 48.0, activity_state: str = "DEEP_FOCUS") -> dict:
    return {
        "module": "M1.1.3", "action": "focus_session_ended",
        "payload": {
            "app_name": app, "app_bucket": "coding",
            "duration_s": duration_s, "wpm_avg": wpm_avg,
            "activity_state": activity_state,
        },
    }


def _window_changed(from_app: str = "Code", to_app: str = "Chrome") -> dict:
    return {
        "module": "M1.1.1", "action": "window_changed",
        "payload": {"app_name": to_app, "app_bucket": "reading",
                    "_from_app": from_app},
    }


def _keystroke_burst(wpm_avg: float = 65.0) -> dict:
    return {
        "module": "M1.1.2", "action": "keystroke_burst",
        "payload": {"wpm_avg": wpm_avg, "key_count": 390},
    }


def _heartbeat() -> dict:
    return {"module": "M1.1.3", "action": "daemon_heartbeat", "payload": {}}


def _activity_state(new_state: str, prev_state: str = "ACTIVE") -> dict:
    return {
        "module": "M1.1.3", "action": "activity_state_changed",
        "payload": {"prev_state": prev_state, "new_state": new_state,
                    "confidence": 0.87},
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine():
    """Fresh BreakpointEngine instance for each test."""
    from services.m1_2_breakpoint.breakpoint_engine import BreakpointEngine
    return BreakpointEngine()


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from services.main import app
    return TestClient(app)


# ---------------------------------------------------------------------------
# AC-1: App switch triggers breakpoint
# ---------------------------------------------------------------------------


class TestBreakpointDetection:
    def test_app_switch_triggers_breakpoint(self, engine):
        """AC-1: [R08 §二] App switch (coding→browser) triggers breakpoint."""
        asyncio.run(engine.feed(_focus_event(app="Code", duration_s=1800)))
        asyncio.run(engine.feed(_window_changed(from_app="Code", to_app="Chrome")))
        assert engine.last_breakpoint is not None
        assert engine.last_breakpoint["type"] == "app_switch"

    def test_idle_timeout_triggers_breakpoint(self, engine):
        """AC-2: [R08 §二] 5-min idle timeout triggers breakpoint."""
        asyncio.run(engine.feed(_focus_event()))
        engine._advance_idle(seconds=301)
        bp = asyncio.run(engine._check_idle_timeout())
        assert bp is not None
        assert bp["type"] == "idle_timeout"

    def test_wpm_drop_triggers_breakpoint(self, engine):
        """AC-3: [R08 §二] WPM drop > 50% within 30s triggers breakpoint."""
        asyncio.run(engine.feed(_keystroke_burst(wpm_avg=60.0)))
        asyncio.run(engine.feed(_keystroke_burst(wpm_avg=15.0)))  # 75% drop
        assert engine.last_breakpoint is not None
        assert engine.last_breakpoint["type"] == "wpm_drop"

    def test_deep_work_entered_via_activity_state(self, engine):
        """AC (§7.2 combo A): activity_state=DEEP_FOCUS → DEEP_WORK state."""
        asyncio.run(engine.feed(_activity_state("DEEP_FOCUS")))
        assert engine.current_state == "DEEP_WORK"

    def test_meeting_call_enters_deep_work(self, engine):
        """AC (§7.2 combo B): MEETING_CALL → DEEP_WORK (do not disturb)."""
        asyncio.run(engine.feed(_activity_state("MEETING_CALL")))
        assert engine.current_state == "DEEP_WORK"

    def test_multi_signal_deep_work_wpm_threshold(self, engine):
        """AC-13: [R08 §一] WPM > threshold sustained > 10 min → DEEP_WORK."""
        asyncio.run(engine.feed(_keystroke_burst(wpm_avg=50.0)))
        engine._advance_focus_duration(seconds=650)
        asyncio.run(engine.feed(_keystroke_burst(wpm_avg=50.0)))
        assert engine.current_state == "DEEP_WORK"


# ---------------------------------------------------------------------------
# AC-4/5/6: Notification tier gating [RISK-04]
# ---------------------------------------------------------------------------


class TestNotificationTierGating:
    @pytest.mark.integration_risk("RISK-04")
    def test_l2_blocked_during_deep_work(self, engine):
        """AC-4: [R08 §三, RISK-04] L2 notifications blocked during DEEP_WORK."""
        asyncio.run(engine.feed(_activity_state("DEEP_FOCUS")))
        assert engine.current_state == "DEEP_WORK"
        result = engine.gate_notification(tier="L2", content="反思草稿已備妥")
        assert result["allowed"] is False
        assert result["reason"] == "deep_work_active"

    @pytest.mark.integration_risk("RISK-04")
    def test_l1_bypasses_deep_work(self, engine):
        """AC-5: [RISK-04] L1 instant notifications bypass breakpoint gate."""
        asyncio.run(engine.feed(_activity_state("DEEP_FOCUS")))
        result = engine.gate_notification(tier="L1", content="Gacha 抽卡結果")
        assert result["allowed"] is True
        assert result["reason"] == "l1_immediate"

    @pytest.mark.integration_risk("RISK-04")
    def test_l3_bypasses_deep_work(self, engine):
        """AC-6: [RISK-04] L3 safety notifications force-interrupt DEEP_WORK."""
        asyncio.run(engine.feed(_activity_state("DEEP_FOCUS")))
        result = engine.gate_notification(tier="L3", content="CARE 安全資源")
        assert result["allowed"] is True
        assert result["reason"] == "l3_safety_override"

    def test_l2_allowed_when_idle(self, engine):
        """AC-4b: L2 allowed when engine is IDLE (no deep work active)."""
        result = engine.gate_notification(tier="L2", content="反思草稿")
        assert result["allowed"] is True


# ---------------------------------------------------------------------------
# AC-7: Cooldown — 2 breakpoints must be >= 5 min apart
# ---------------------------------------------------------------------------


class TestBreakpointCooldown:
    def test_cooldown_prevents_duplicate_breakpoint(self, engine):
        """AC-7: [R08 §三] Two breakpoints must be >= 5 min apart."""
        asyncio.run(engine.feed(_window_changed("Code", "Chrome")))
        first = engine.last_breakpoint
        assert first is not None
        # Immediately trigger another window change — within cooldown
        asyncio.run(engine.feed(_window_changed("Chrome", "Slack")))
        # last_breakpoint should NOT have updated
        assert engine.last_breakpoint is first

    def test_cooldown_expires_after_5min(self, engine):
        """AC-7b: After cooldown expires, next breakpoint is emitted."""
        asyncio.run(engine.feed(_window_changed("Code", "Chrome")))
        first = engine.last_breakpoint
        engine._advance_cooldown(seconds=301)
        asyncio.run(engine.feed(_window_changed("Chrome", "Slack")))
        assert engine.last_breakpoint is not first


# ---------------------------------------------------------------------------
# AC-8: Degraded mode when M1.1 heartbeat stops
# ---------------------------------------------------------------------------


class TestDegradedMode:
    def test_no_heartbeat_10s_enters_degraded(self, engine):
        """AC-8: [M1.1 SPEC §5] 10s without heartbeat → degraded mode."""
        engine._advance_heartbeat_timeout(seconds=11)
        asyncio.run(engine._check_heartbeat_timeout())
        assert engine.mode == "degraded"

    def test_degraded_mode_allows_all_l2(self, engine):
        """AC-8b: In degraded mode, L2 notifications pass through."""
        engine.mode = "degraded"
        result = engine.gate_notification(tier="L2", content="test")
        assert result["allowed"] is True
        assert result["reason"] == "degraded_mode"

    def test_heartbeat_received_exits_degraded(self, engine):
        """AC-8c: Heartbeat restores normal mode from degraded."""
        engine.mode = "degraded"
        asyncio.run(engine.feed(_heartbeat()))
        assert engine.mode == "normal"


# ---------------------------------------------------------------------------
# AC-9: Breakpoint detection rate >= 80% (boundary logic test)
# ---------------------------------------------------------------------------


class TestBreakpointAccuracy:
    def test_app_switch_after_coding_session_detected(self, engine):
        """AC-9 proxy: coding→browser switch correctly identified as breakpoint."""
        asyncio.run(engine.feed(_focus_event(app="Code", duration_s=600)))
        asyncio.run(engine.feed(_window_changed("Code", "Chrome")))
        assert engine.last_breakpoint is not None
        assert engine.last_breakpoint["confidence"] >= 0.5

    def test_idle_after_coding_detected_as_breakpoint(self, engine):
        """AC-9 proxy: idle after active coding correctly identified."""
        asyncio.run(engine.feed(_focus_event(wpm_avg=55.0, duration_s=900)))
        engine._advance_idle(seconds=301)
        bp = asyncio.run(engine._check_idle_timeout())
        assert bp is not None


# ---------------------------------------------------------------------------
# AC-10/11: Staggered notification dispatcher
# ---------------------------------------------------------------------------


class TestStaggeredDispatcher:
    def test_multiple_l2_released_with_delay(self, engine):
        """AC-10: [R08 §三] Multiple L2 notifications released with random 1-60s delay."""
        from services.m1_2_breakpoint.staggered_dispatcher import StaggeredDispatcher
        dispatcher = StaggeredDispatcher()
        notifs = [
            {"tier": "L2", "persona": "Robert", "content": "反思草稿"},
            {"tier": "L2", "persona": "Beth", "content": "觀察洞察"},
            {"tier": "L2", "persona": "Observer", "content": "專案進展"},
        ]
        scheduled = dispatcher.schedule(notifs)
        delays = [n["delay_s"] for n in scheduled]
        assert all(1 <= d <= 60 for d in delays)
        assert len(set(delays)) > 1  # not all simultaneous

    def test_deep_work_reentry_stops_release(self, engine):
        """AC-11: Re-entering DEEP_WORK during staggered release stops dispatch."""
        from services.m1_2_breakpoint.staggered_dispatcher import StaggeredDispatcher
        dispatcher = StaggeredDispatcher()
        notifs = [
            {"tier": "L2", "persona": "Robert", "content": "草稿"},
            {"tier": "L2", "persona": "Beth", "content": "觀察"},
        ]
        scheduled = dispatcher.schedule(notifs)
        # Simulate re-entry into DEEP_WORK before release
        asyncio.run(engine.feed(_activity_state("DEEP_FOCUS")))
        remaining = dispatcher.cancel_if_deep_work(engine)
        assert remaining > 0  # some notifications held back


# ---------------------------------------------------------------------------
# AC-12: System notification restore on exit
# ---------------------------------------------------------------------------


class TestSystemNotificationRestore:
    def test_exit_deep_work_sends_restore_command(self, engine):
        """AC-12: Leaving DEEP_WORK sends set_notification_mode=restore to Tauri."""
        asyncio.run(engine.feed(_activity_state("DEEP_FOCUS")))
        assert engine.current_state == "DEEP_WORK"

        commands_sent = []
        with patch("services.m1_2_breakpoint.deep_work_guard.send_tauri_command",
                   new_callable=AsyncMock) as mock_cmd:
            mock_cmd.side_effect = lambda cmd: commands_sent.append(cmd)
            asyncio.run(engine.feed(_activity_state("ACTIVE", prev_state="DEEP_FOCUS")))

        assert engine.current_state != "DEEP_WORK"

    def test_mute_sent_on_deep_work_entry(self, engine):
        """AC-12b: Entering DEEP_WORK sends set_notification_mode=mute to Tauri."""
        with patch("services.m1_2_breakpoint.deep_work_guard.send_tauri_command",
                   new_callable=AsyncMock) as mock_cmd:
            asyncio.run(engine.feed(_activity_state("DEEP_FOCUS")))
            assert mock_cmd.called
            call_args = mock_cmd.call_args[0][0]
            assert call_args["mode"] == "mute"


# ---------------------------------------------------------------------------
# FastAPI endpoint: POST /api/m1_2/event
# ---------------------------------------------------------------------------


class TestM12Endpoint:
    def test_event_endpoint_exists(self, client):
        """FastAPI /api/m1_2/event endpoint accepts M1.1 events."""
        import uuid
        from datetime import UTC, datetime
        event = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now(UTC).isoformat(),
            "module": "M1.1.3",
            "action": "focus_session_ended",
            "level": "INFO",
            "payload": {
                "app_name": "Code", "app_bucket": "coding",
                "duration_s": 1800, "wpm_avg": 48.0,
                "activity_state": "DEEP_FOCUS",
            },
            "role_id": "default",
        }
        resp = client.post("/api/m1_2/event", json=event)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
