"""
M6.3 -- Role Context Pydantic models

SPEC: docs/modules/M6_3_role_context_tables_SPEC.md §7.4
Risk: RISK-06 -- RoleImplicitState must always be queried by (user_id, role_id)
Research: [R03 §6] role switch must fully reset Persona state
"""
from datetime import datetime, time
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class RoleProject(BaseModel):
    """L3 cloud -- role-scoped project/course/goal."""

    id: UUID = Field(default_factory=uuid4)
    role_id: UUID
    name: str = Field(max_length=100)
    description: str | None = Field(default=None, max_length=500)
    status: str = Field(default="active")
    sort_order: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


class RoleSetting(BaseModel):
    """L3 cloud -- per-role UI and notification preferences."""

    id: UUID = Field(default_factory=uuid4)
    role_id: UUID
    theme: str = "default"
    notification_enabled: bool = True
    daily_report_time: time = time(22, 0)
    focus_hours_start: time = time(9, 0)
    focus_hours_end: time = time(18, 0)


class RoleImplicitState(BaseModel):
    """
    Local SQLite (L2) -- role-scoped implicit state cache.

    [R03 §6] MUST be queried by (user_id, role_id). Never query by
    user_id alone -- that would return all roles' states (RISK-06).
    """

    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    role_id: UUID
    label: str
    confidence: float = Field(ge=0.0, le=1.0)
    inferred_at: datetime | None = None
    expires_at: datetime | None = None
    source_module: str = "M4.8"
