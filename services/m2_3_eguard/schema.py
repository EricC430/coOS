"""M2.3 data schemas: RawTextPayload and SanitizedPayload

SPEC: docs/modules/M2_3_eguard_crypto_filter_SPEC.md v1.1 §7.5
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class RawTextPayload(BaseModel):
    text: str
    role_id: str
    source_path: str | None = None  # for .eguardignore matching


class SanitizedPayload(BaseModel):
    original_length: int
    sanitized_text: str
    flagged: bool = False
    masked_entities: list[str] = Field(default_factory=list)
    role_id: str = Field(..., description="Propagated from input, for M4.1 role-based routing")
    audit_level: Literal["OK", "WARNING", "BLOCKED"] = "OK"
