"""
M4.13 — Community Engine Pydantic Schemas

SPEC: docs/modules/M3_7_community_ui_SPEC.md §3.1–§3.3
Request/response models for the community API.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Community
# ---------------------------------------------------------------------------

class CommunityRead(BaseModel):
    id: str
    name: str
    type: str
    theme: str | None = None
    member_cap: int
    member_count: int
    is_member: bool
    role: str = "member"
    challenge_mode: str = "manual"
    goal: str | None = None
    vision: str | None = None
    codex: str | None = None
    rules: list[str] = Field(default_factory=list)
    quotes: list[str] = Field(default_factory=list)


class CommunityCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    type: str = Field(default="user_created")
    theme: str | None = None
    member_cap: int = Field(default=5, ge=2, le=8)


class CommunityJoin(BaseModel):
    mode: str = Field(
        default="system_random",
        description="theme_random | system_random",
    )
    theme: str | None = None


# ---------------------------------------------------------------------------
# Codex
# ---------------------------------------------------------------------------

class CommunityCodex(BaseModel):
    goal: str = ""
    vision: str = ""
    codex: str = ""
    quotes: list[str] = Field(default_factory=list)
    rules: list[str] = Field(default_factory=list)


class CodexUpdate(BaseModel):
    goal: str = ""
    vision: str = ""
    codex: str = ""
    quotes: list[str] = Field(default_factory=list)
    rules: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Posts
# ---------------------------------------------------------------------------

class SocialPostRead(BaseModel):
    id: str
    author_id: str
    author_display: str = ""
    content: str
    kind: str = "achievement"
    likes_count: int = 0
    created_at: str | None = None
    published_at: str | None = None
    validation_count: int = 0


class SocialPostDraft(BaseModel):
    community_id: str
    content: str = Field(..., min_length=1, max_length=2000)
    kind: str = Field(default="achievement")


class PublishRequest(BaseModel):
    draft_id: str


class PublishResult(BaseModel):
    id: str
    published: bool
    published_at: str | None = None


class DraftResult(BaseModel):
    id: str
    is_draft: bool = True
    privacy_warning: str = ""


class LikeResult(BaseModel):
    id: str
    likes_count: int


# ---------------------------------------------------------------------------
# Validations
# ---------------------------------------------------------------------------

class ValidationCreate(BaseModel):
    post_id: str
    evidence_url: str | None = None


class ValidationResult(BaseModel):
    id: str
    post_id: str
    validated_at: str


# ---------------------------------------------------------------------------
# Stakes
# ---------------------------------------------------------------------------

class StakeCreate(BaseModel):
    task_id: str | None = None
    xp_amount: int = Field(..., gt=0)
    deadline: str | None = None
    community_id: str


class StakeRead(BaseModel):
    id: str
    community_id: str
    task_id: str | None = None
    xp_amount: int
    status: str = "held"
    deadline: str | None = None
    created_at: str


# ---------------------------------------------------------------------------
# Challenges
# ---------------------------------------------------------------------------

class ChallengeRead(BaseModel):
    id: str
    title: str
    description: str | None = None
    period: str = "weekly"
    source: str = "admin"
    progress: int = 0
    is_draft: bool = False
    created_at: str


class ChallengeCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    period: str = "weekly"  # weekly | monthly
    source: str = "admin"  # admin | member_rotation | ai_reviewed


class ChallengeApprove(BaseModel):
    edits: dict[str, str] | None = None


# ---------------------------------------------------------------------------
# Commitments (closed loop view)
# ---------------------------------------------------------------------------

class CommitmentItem(BaseModel):
    id: str
    content: str
    kind: str = "achievement"
    validation_count: int = 0
    published_at: str | None = None


class TaskToValidate(BaseModel):
    id: str
    content: str
    kind: str = "achievement"
    author_id: str
    published_at: str | None = None


class ActiveStake(BaseModel):
    id: str
    xp_amount: int
    deadline: str | None = None


class CommitmentsView(BaseModel):
    commitments: list[CommitmentItem] = Field(default_factory=list)
    to_validate: list[TaskToValidate] = Field(default_factory=list)
    active_stakes: list[ActiveStake] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# SSE Event
# ---------------------------------------------------------------------------

class CommunityEvent(BaseModel):
    type: str  # POST_PUBLISHED | COMMITMENT_VALIDATED | CHALLENGE_ACTIVATED
    community_id: str
    post_id: str | None = None
    challenge_id: str | None = None
    actor_id: str | None = None
    message: str = ""


# ---------------------------------------------------------------------------
# Membership and Management
# ---------------------------------------------------------------------------

class MemberRead(BaseModel):
    user_id: str
    role: str
    joined_at: str
    display_name: str


class RoleUpdateRequest(BaseModel):
    role: str


class JoinRequestRead(BaseModel):
    id: str
    community_id: str
    user_id: str
    status: str
    created_at: str
    display_name: str


class JoinRequestAction(BaseModel):
    action: str


class CommunitySettingsUpdate(BaseModel):
    challenge_mode: str
    member_cap: int

