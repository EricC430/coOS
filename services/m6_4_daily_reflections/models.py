"""
M6.4 -- Daily Reflection Pydantic models

SPEC: docs/modules/M6_4_daily_reflections_SPEC.md §7.3
Research: [R08 §四.2] micro-friction mandatory fields
         [R08 §五]   AI objective vs user subjective split
         [R10 §MindScape] structured reflection template
"""
from datetime import date, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class DailyReflectionCreate(BaseModel):
    """Schema for AI auto-generating a draft reflection."""

    user_id: UUID
    role_id: UUID
    reflection_date: date
    # [R08 §五] AI fills objective description, min 10 chars to prevent empty stubs
    ai_description: str = Field(min_length=10)
    ai_analysis: str | None = None
    projects_touched: list[str] | None = None
    activity_minutes: int | None = Field(default=None, ge=0)
    source_log_ids: list[str] | None = None


class UserReflectionInput(BaseModel):
    """
    [R08 §四.2] User-written subjective section.
    Both user_feeling and user_action_plan are mandatory micro-friction fields.
    They cannot be empty or whitespace-only -- that would defeat the IKEA effect.
    """

    user_feeling: str = Field(min_length=1, description="Subjective feeling, must not be empty")
    user_action_plan: str = Field(min_length=1, description="Action plan, must not be empty")
    user_learned: str | None = None
    # [RISK-10] mood_score as absolute baseline for Wrapped stats; optional per SPEC §9
    mood_score: int | None = Field(default=None, ge=1, le=10)

    @field_validator("user_feeling", "user_action_plan")
    @classmethod
    def must_not_be_whitespace_only(cls, v: str) -> str:
        """[R08 §四.2] Whitespace-only inputs bypass the micro-friction intent."""
        if not v.strip():
            raise ValueError("must not be whitespace-only")
        return v.strip()


class DailyReflectionResponse(BaseModel):
    """Full reflection record for reading/rendering."""

    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    role_id: UUID
    reflection_date: date
    ai_description: str
    ai_analysis: str | None = None
    projects_touched: list[str] | None = None
    activity_minutes: int | None = None
    user_feeling: str | None = None
    user_action_plan: str | None = None
    user_learned: str | None = None
    mood_score: int | None = None
    is_draft: bool = True
    is_reviewed: bool = False
    reviewed_at: datetime | None = None
    earned_xp: int = 0
    xp_settled: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None
