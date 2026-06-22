"""
M1.2 schemas

SPEC: docs/modules/M1_2_breakpoint_detection_SPEC.md §7.4
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class BreakpointEvent(BaseModel):
    type: Literal["app_switch", "idle_timeout", "wpm_drop", "ide_focus_leave", "doom_scrolling"]
    confidence: float           # 0.0~1.0
    timestamp: str
    preceding_app: str = ""
    preceding_duration_s: int = 0


class NotificationGateResult(BaseModel):
    allowed: bool
    # "deep_work_active" | "l1_immediate" | "l3_safety_override" | "degraded_mode" | "ok"
    reason: str
    tier: Literal["L1", "L2", "L3"]
