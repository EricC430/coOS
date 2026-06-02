"""
M1.2.3 -- Staggered Notification Dispatcher

SPEC: docs/modules/M1_2_breakpoint_detection_SPEC.md §7.6
Research: [R08: §三 醫療級警報疲勞防範] Prevent notification flooding at breakpoint.

When a breakpoint fires, queued L2 notifications are scheduled with random
1-60s delays so multiple Persona messages do not arrive simultaneously.
"""
from __future__ import annotations

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .breakpoint_engine import BreakpointEngine

# Priority order for L2 notifications (lower index = higher priority)
_PRIORITY_ORDER = ["safety", "tracked_persona", "reflection", "observer"]


class StaggeredDispatcher:
    """[R08 §三] Schedule L2 notifications with random delays on breakpoint."""

    DELAY_MIN_S: int = 1
    DELAY_MAX_S: int = 60

    def __init__(self) -> None:
        self._scheduled: list[dict] = []

    def schedule(self, notifications: list[dict]) -> list[dict]:
        """Assign a random delay_s (1-60) to each notification.

        Notifications are sorted by priority first, then each gets an
        independent random delay so they do not all fire at once.
        Stores internally so cancel_if_deep_work can operate on them.
        """
        sorted_notifs = sorted(
            notifications,
            key=lambda n: self._priority_rank(n.get("persona", "")),
        )
        result = []
        for notif in sorted_notifs:
            delay = random.uniform(self.DELAY_MIN_S, self.DELAY_MAX_S)
            entry = {**notif, "delay_s": delay, "status": "scheduled"}
            result.append(entry)
        self._scheduled = result
        return result

    def cancel_if_deep_work(self, engine: BreakpointEngine) -> int:
        """Cancel pending scheduled notifications if engine re-entered DEEP_WORK.

        Returns the number of notifications held back (marked 'held').
        """
        if engine.current_state == "DEEP_WORK":
            held = len([n for n in self._scheduled if n["status"] == "scheduled"])
            for n in self._scheduled:
                if n["status"] == "scheduled":
                    n["status"] = "held"
            return held
        return 0

    @staticmethod
    def _priority_rank(persona: str) -> int:
        lower = persona.lower()
        if "care" in lower or "safety" in lower:
            return 0
        if "robert" in lower or "tracked" in lower:
            return 1
        if "reflection" in lower or "beth" in lower:
            return 2
        return 3
