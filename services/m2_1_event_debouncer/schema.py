"""M2.1 data schemas: RawTelemetryEvent and EventBatch

SPEC: docs/modules/M2_1_event_debouncing_SPEC.md v1.1 §7.2
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _uuid() -> str:
    return str(uuid.uuid4())


class RawTelemetryEvent(BaseModel):
    id: str = Field(default_factory=_uuid)
    event_type: str  # "keystroke", "mouse_click", "focus_change", "ast_change", "hover"
    module: str      # originating module e.g. "M1.1.2", "M1.3.1"
    timestamp: datetime = Field(default_factory=_utcnow)
    data: dict[str, Any] = Field(default_factory=dict)


class EventBatch(BaseModel):
    batch_id: str = Field(default_factory=_uuid)
    role_id: str
    created_at: datetime = Field(default_factory=_utcnow)
    events: list[RawTelemetryEvent]
    size: int = 0

    def model_post_init(self, __context: Any) -> None:
        self.size = len(self.events)
