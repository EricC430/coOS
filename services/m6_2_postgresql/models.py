"""
M6.2 v1.1 -- Pydantic v2 models for cloud PostgreSQL L3 tables

SPEC: docs/modules/M6_2_postgresql_schemas_SPEC.md v1.1
Research: [R03 §1.1] BDI-aligned ai_experts; [R08 §六.1] lifetime_xp invariant
Risk mitigation:
  RISK-12: xp_ledger reason/source_module never contain L1 raw text
  RISK-14: lifetime_xp is incremented only on earn, never on spend

Privacy boundary: ALL models here represent L3 cloud data only.
L1/L2 data (chat_transcripts, edge events, role_implicit_states) MUST NOT appear here.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

class UserRead(BaseModel):
    id: uuid.UUID
    display_name: str
    email: str | None = None
    current_xp: int = 0
    lifetime_xp: int = 0          # [RISK-14] never decremented; level basis
    level: int = 1
    streak_days: int = 0
    active_role_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=50)
    email: str | None = None


class UserUpdate(BaseModel):
    display_name: str | None = Field(None, min_length=1, max_length=50)
    active_role_id: uuid.UUID | None = None


# ---------------------------------------------------------------------------
# Role
# ---------------------------------------------------------------------------

class RoleRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    slug: str
    display_name: str
    color_hex: str | None = None
    icon_name: str | None = None
    avatar_url: str | None = None    # v1.1: for UI rendering
    sort_order: int = 0
    is_active: bool = True
    created_at: datetime

    model_config = {"from_attributes": True}


class RoleCreate(BaseModel):
    user_id: uuid.UUID
    slug: str = Field(..., min_length=1, max_length=30, pattern=r"^[a-z0-9_-]+$")
    display_name: str = Field(..., min_length=1, max_length=50)
    color_hex: str | None = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    icon_name: str | None = Field(None, max_length=30)
    avatar_url: str | None = Field(None, max_length=512)


# ---------------------------------------------------------------------------
# AI Expert
# ---------------------------------------------------------------------------

class AIExpertRead(BaseModel):
    id: uuid.UUID
    name: str
    role_id: uuid.UUID
    personality_prompt: str
    backstory: str | None = None
    tone_default: str = "authoritative"
    trust_level: float = 0.5
    avatar_url: str | None = None
    is_active: bool = True
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("trust_level")
    @classmethod
    def validate_trust(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("trust_level must be in [0.0, 1.0]")
        return v


class AIExpertCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    role_id: uuid.UUID
    personality_prompt: str = Field(..., min_length=10, max_length=4096)
    backstory: str | None = Field(None, max_length=2048)
    tone_default: str = Field("authoritative", max_length=20)
    trust_level: float = Field(0.5, ge=0.0, le=1.0)
    avatar_url: str | None = Field(None, max_length=512)


# ---------------------------------------------------------------------------
# XP Ledger
# ---------------------------------------------------------------------------

XPType = Literal["earned", "spent_gacha", "spent_stake", "refund"]


class XPLedgerEntry(BaseModel):
    """[RISK-12] reason and source_module must never contain L1 raw text."""
    id: uuid.UUID
    user_id: uuid.UUID
    amount: int
    xp_type: XPType
    reason: str          # business description only (e.g. "segment approved")
    source_module: str   # e.g. "M6.5"
    role_id: uuid.UUID | None = None
    expert_id: uuid.UUID | None = None
    project: str | None = None        # v1.1: project/course tag
    segment_id: uuid.UUID | None = None  # v1.1: FK to daily_reflection_segments
    task_id: uuid.UUID | None = None  # v1.1: future M4.13 task FK
    reflection_id: uuid.UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("amount")
    @classmethod
    def validate_nonzero(cls, v: int) -> int:
        if v == 0:
            raise ValueError("XP amount must not be zero")
        return v


class XPLedgerCreate(BaseModel):
    user_id: uuid.UUID
    amount: int = Field(..., ne=0)
    xp_type: XPType
    reason: str = Field(..., min_length=1, max_length=255)
    source_module: str = Field(..., min_length=1, max_length=10)
    role_id: uuid.UUID | None = None
    expert_id: uuid.UUID | None = None
    project: str | None = None
    segment_id: uuid.UUID | None = None
    task_id: uuid.UUID | None = None
    reflection_id: uuid.UUID | None = None


# ---------------------------------------------------------------------------
# Badge
# ---------------------------------------------------------------------------

class BadgeDefinitionRead(BaseModel):
    id: uuid.UUID
    slug: str
    display_name: str
    description: str | None = None
    icon_url: str | None = None
    category: str
    is_hidden: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class UserBadgeRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    badge_id: uuid.UUID
    unlocked_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Role Projects (v1.1)
# ---------------------------------------------------------------------------

class RoleProjectRead(BaseModel):
    id: uuid.UUID
    role_id: uuid.UUID
    name: str
    description: str | None = None
    status: str = "active"
    sort_order: int = 0
    inferred_by_ai: bool = False      # v1.1: AI auto-discovery flag
    alias_keywords: str | None = None  # v1.1: JSON array string
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RoleProjectCreate(BaseModel):
    role_id: uuid.UUID
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    status: Literal["active", "completed", "paused", "archived"] = "active"
    inferred_by_ai: bool = False
    alias_keywords: str | None = None


# ---------------------------------------------------------------------------
# Role Settings (v1.1)
# ---------------------------------------------------------------------------

class RoleSettingsRead(BaseModel):
    id: uuid.UUID
    role_id: uuid.UUID
    theme: str | None = "default"
    notification_enabled: bool | None = True
    daily_report_time: str | None = "22:00"
    focus_hours_start: str | None = "09:00"
    focus_hours_end: str | None = "18:00"
    weekly_target_minutes: int = 0    # v1.1: focus goal management
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
