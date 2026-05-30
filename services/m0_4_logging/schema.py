"""
M0.4 -- LogEvent schema

SPEC: docs/modules/M0_4_structured_logging_SPEC.md
Privacy constraint: payload must never contain L1 plaintext field names
(CLAUDE.md privacy layer principle).
"""
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

# L1 plaintext fields that must never appear in logs (CLAUDE.md privacy rule)
_FORBIDDEN_PAYLOAD_KEYS = frozenset(
    {"raw_text", "raw_code", "transcript", "browsing_content"}
)

_VALID_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "AUDIT"})

_MODULE_RE = re.compile(r"^M\d+\.\d+")


class LogEvent(BaseModel):
    """coOS unified structured log event."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )
    module: str = Field(..., description="Module ID, format Mx.y")
    action: str = Field(..., description="Event action name")
    level: str = Field(default="INFO")
    payload: dict[str, Any] = Field(default_factory=dict)
    user_id: str | None = Field(default=None)
    role_id: str | None = Field(default=None)
    correlation_id: str | None = Field(
        default=None,
        description="Cross-module trace ID shared within one business flow",
    )

    @field_validator("module")
    @classmethod
    def validate_module_format(cls, v: str) -> str:
        if not _MODULE_RE.match(v):
            raise ValueError(f"Module ID must match Mx.y format, got: {v}")
        return v

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        upper = v.upper()
        if upper not in _VALID_LEVELS:
            raise ValueError(f"Log level must be one of {_VALID_LEVELS}, got: {v}")
        return upper

    @model_validator(mode="after")
    def validate_payload_privacy(self) -> "LogEvent":
        """Reject any attempt to log L1 plaintext field names in payload."""
        forbidden = _FORBIDDEN_PAYLOAD_KEYS.intersection(self.payload.keys())
        if forbidden:
            raise ValueError(
                f"Payload contains forbidden L1 plaintext keys: {forbidden}. "
                "Log summaries or statistics only, never raw content."
            )
        return self
