"""
M1.2.1 -- Breakpoint Detection Engine (state machine)

SPEC: docs/modules/M1_2_breakpoint_detection_SPEC.md
Research:
  [R08: §二 任務斷點打斷管理] Defer-to-Breakpoint: notify only at natural cognitive gaps.
  [R08: §三 醫療級警報疲勞防範] Three-tier notification classification.
  [R08: §一 認知負荷轉移] High-load interruption cost.

Risk: RISK-04 (Defer-to-Breakpoint + XP instant reward → motivation disconnect)
Mitigation: L1/L2/L3 tier classification — only L2 is deferred.

Architecture (per plan):
  Python = state machine logic (this file)
  Tauri Rust = Win32 SetNotificationMode (via IPC command through deep_work_guard.py)
"""
from __future__ import annotations

import logging
import time
from datetime import UTC, datetime

from .deep_work_guard import enter_deep_work, exit_deep_work

logger = logging.getLogger(__name__)

# Thresholds (all in seconds)
_WPM_DROP_THRESHOLD = 0.50      # 50% drop triggers breakpoint
_WPM_WINDOW = 30                # compare WPM within 30s
_IDLE_TIMEOUT_S = 300           # 5 min no activity → breakpoint
_HEARTBEAT_TIMEOUT_S = 10       # 10s no heartbeat → degraded
_COOLDOWN_S = 300               # 5 min minimum between breakpoints
_DEEP_FOCUS_DURATION_S = 600    # 10 min sustained work → DEEP_WORK (WPM path)
_WPM_THRESHOLD = 40             # default WPM threshold for DEEP_WORK (configurable 20-80)


class BreakpointEngine:
    """[R08 §二] Multi-signal breakpoint detection state machine.

    States: IDLE → ACTIVE → DEEP_WORK → BREAKPOINT → (cooldown) → IDLE/ACTIVE
    """

    def __init__(self, wpm_threshold: int = _WPM_THRESHOLD):
        self.current_state: str = "IDLE"
        self.mode: str = "normal"          # "normal" | "degraded"
        self.last_breakpoint: dict | None = None

        self._wpm_history: list[tuple[float, float]] = []  # (timestamp, wpm)
        self._last_heartbeat: float = time.monotonic()
        self._last_breakpoint_time: float = 0.0
        self._last_activity: float = time.monotonic()
        self._focus_start: float = time.monotonic()
        self._current_app: str = ""
        self._wpm_threshold: int = wpm_threshold
        self._pending_notifications: list[dict] = []

        # Test-injectable time offsets (for unit tests that can't sleep)
        self._idle_offset: float = 0.0
        self._cooldown_offset: float = 0.0
        self._heartbeat_offset: float = 0.0
        self._focus_duration_offset: float = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def feed(self, event: dict) -> dict | None:
        """Process one M1.1 TelemetryEvent. Returns breakpoint dict if emitted."""
        action = event.get("action", "")
        payload = event.get("payload", {})

        if action == "daemon_heartbeat":
            return await self._on_heartbeat()
        if action == "activity_state_changed":
            return await self._on_activity_state(payload)
        if action == "focus_session_ended":
            return await self._on_focus_session(payload)
        if action == "window_changed":
            return await self._on_window_changed(payload)
        if action == "keystroke_burst":
            return await self._on_keystroke(payload)
        return None

    def gate_notification(self, tier: str, content: str) -> dict:
        """[R08 §三, RISK-04] Apply three-tier notification gate.

        L1 (user-triggered instant): always allowed.
        L2 (system-proactive insights): blocked during DEEP_WORK.
        L3 (safety): always allowed, force-interrupts.
        """
        if self.mode == "degraded":
            return {"allowed": True, "reason": "degraded_mode", "tier": tier}

        if tier == "L1":
            return {"allowed": True, "reason": "l1_immediate", "tier": tier}
        if tier == "L3":
            return {"allowed": True, "reason": "l3_safety_override", "tier": tier}
        # L2
        if self.current_state == "DEEP_WORK":
            return {"allowed": False, "reason": "deep_work_active", "tier": tier}
        return {"allowed": True, "reason": "ok", "tier": tier}

    # ------------------------------------------------------------------
    # Test helpers (injectable without sleeping)
    # ------------------------------------------------------------------

    def _advance_idle(self, seconds: float) -> None:
        self._idle_offset += seconds

    def _advance_cooldown(self, seconds: float) -> None:
        self._cooldown_offset += seconds

    def _advance_heartbeat_timeout(self, seconds: float) -> None:
        self._heartbeat_offset += seconds

    def _advance_focus_duration(self, seconds: float) -> None:
        self._focus_duration_offset += seconds

    # ------------------------------------------------------------------
    # Internal event handlers
    # ------------------------------------------------------------------

    async def _on_heartbeat(self) -> None:
        self._last_heartbeat = time.monotonic()
        if self.mode == "degraded":
            self.mode = "normal"
            logger.info("[M1.2] Heartbeat restored — exiting degraded mode")

    async def _check_heartbeat_timeout(self) -> None:
        elapsed = (time.monotonic() - self._last_heartbeat) + self._heartbeat_offset
        if elapsed > _HEARTBEAT_TIMEOUT_S:
            self.mode = "degraded"
            logger.warning("[M1.2] M1.1 heartbeat timeout — degraded mode")

    async def _on_activity_state(self, payload: dict) -> dict | None:
        new_state = payload.get("new_state", "")
        prev_state = payload.get("prev_state", "")

        deep_work_states = {"DEEP_FOCUS", "MEETING_CALL"}

        if new_state in deep_work_states:
            if self.current_state != "DEEP_WORK":
                self.current_state = "DEEP_WORK"
                await enter_deep_work()
                logger.info("[M1.2] Entered DEEP_WORK via ActivityState=%s", new_state)
        elif prev_state in deep_work_states and new_state not in deep_work_states:
            if self.current_state == "DEEP_WORK":
                await self._emit_breakpoint("app_switch", confidence=0.80)
                await exit_deep_work()
        else:
            if self.current_state not in ("DEEP_WORK", "IDLE"):
                self.current_state = "ACTIVE"

        return self.last_breakpoint

    async def _on_focus_session(self, payload: dict) -> dict | None:
        self._last_activity = time.monotonic()
        self._current_app = payload.get("app_name", "")

        # [R08 §二 combo C/D] WPM sustained → DEEP_WORK
        wpm = payload.get("wpm_avg", 0.0)
        duration_s = payload.get("duration_s", 0)
        effective_duration = duration_s + self._focus_duration_offset

        if (wpm >= self._wpm_threshold and effective_duration >= _DEEP_FOCUS_DURATION_S
                and self.current_state != "DEEP_WORK"):
            self.current_state = "DEEP_WORK"
            await enter_deep_work()

        return None

    async def _on_window_changed(self, payload: dict) -> dict | None:
        self._last_activity = time.monotonic()
        new_app = payload.get("app_name", "")

        if self.current_state == "DEEP_WORK":
            await self._emit_breakpoint("app_switch", confidence=0.90,
                                        preceding_app=self._current_app)
            await exit_deep_work()
        elif self.current_state in ("ACTIVE", "IDLE"):
            # Any app switch from active or idle qualifies as a natural breakpoint
            await self._emit_breakpoint("app_switch", confidence=0.75,
                                        preceding_app=self._current_app)
            self.current_state = "ACTIVE"

        self._current_app = new_app
        self._focus_start = time.monotonic()
        self._focus_duration_offset = 0.0
        return self.last_breakpoint

    async def _on_keystroke(self, payload: dict) -> dict | None:
        self._last_activity = time.monotonic()
        wpm = payload.get("wpm_avg", 0.0)
        now = time.monotonic()
        self._wpm_history.append((now, wpm))

        # Keep only last 30s
        cutoff = now - _WPM_WINDOW
        self._wpm_history = [(t, w) for t, w in self._wpm_history if t >= cutoff]

        # [R08 §二] WPM drop > 50% in 30s → breakpoint
        if len(self._wpm_history) >= 2:
            prev_wpm = self._wpm_history[0][1]
            if prev_wpm > 0 and wpm < prev_wpm * (1 - _WPM_DROP_THRESHOLD):
                await self._emit_breakpoint("wpm_drop", confidence=0.70)

        # Transition to ACTIVE if typing
        if self.current_state == "IDLE" and wpm > 0:
            self.current_state = "ACTIVE"

        # [R08 §二 combo C] WPM sustained > threshold + focus_duration > 10 min → DEEP_WORK
        if (wpm >= self._wpm_threshold
                and self.current_state == "ACTIVE"):
            focus_elapsed = (time.monotonic() - self._focus_start) + self._focus_duration_offset
            if focus_elapsed >= _DEEP_FOCUS_DURATION_S:
                self.current_state = "DEEP_WORK"
                await enter_deep_work()

        return self.last_breakpoint

    async def _check_idle_timeout(self) -> dict | None:
        """Called by polling loop. Returns breakpoint if idle > 5 min."""
        elapsed = (time.monotonic() - self._last_activity) + self._idle_offset
        if elapsed > _IDLE_TIMEOUT_S:
            bp = await self._emit_breakpoint("idle_timeout", confidence=0.95)
            self.current_state = "IDLE"
            return bp
        return None

    async def _emit_breakpoint(
        self,
        bp_type: str,
        confidence: float,
        preceding_app: str = "",
        preceding_duration_s: int = 0,
    ) -> dict | None:
        """[R08 §二] Emit breakpoint event with 5-min cooldown enforcement."""
        now = time.monotonic()
        elapsed_since_last = (now - self._last_breakpoint_time) + self._cooldown_offset
        if self._last_breakpoint_time > 0 and elapsed_since_last < _COOLDOWN_S:
            logger.debug("[M1.2] Breakpoint suppressed — cooldown active (%.0fs remaining)",
                         _COOLDOWN_S - elapsed_since_last)
            return None

        bp = {
            "type": bp_type,
            "confidence": confidence,
            "timestamp": datetime.now(UTC).isoformat(),
            "preceding_app": preceding_app or self._current_app,
            "preceding_duration_s": preceding_duration_s,
        }
        self.last_breakpoint = bp
        self._last_breakpoint_time = now
        self._cooldown_offset = 0.0  # reset test offset after use

        if self.current_state != "IDLE":
            self.current_state = "BREAKPOINT"

        logger.info("[M1.2] BREAKPOINT_DETECTED type=%s confidence=%.2f", bp_type, confidence)

        # Write to raw_tracking_logs via M0.4
        try:
            from m0_4_logging.writer import get_logger as get_log_writer
            log_writer = get_log_writer()
            await log_writer.emit(
                module="M1.2",
                action="breakpoint_detected",
                level="INFO",
                payload=bp,
            )
        except Exception as exc:
            logger.warning("[M1.2] Failed to write breakpoint to raw_tracking_logs: %s", exc)

        return bp
