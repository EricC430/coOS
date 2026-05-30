"""
M6.4 -- Draft & Approve business logic

SPEC: docs/modules/M6_4_daily_reflections_SPEC.md §7.2
Research:
  [R08 §四.2] micro-friction: user_feeling + user_action_plan mandatory
  [R08 §六.1] IKEA effect: user effort gates XP settlement
Risk mitigation:
  RISK-01: can_grant_xp() enforces is_reviewed + user_feeling before XP
"""
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from uuid import UUID


@dataclass
class DraftReflection:
    """In-memory representation of a daily reflection (service layer)."""

    id: UUID
    user_id: UUID
    role_id: UUID
    reflection_date: date
    ai_description: str
    is_draft: bool = True
    is_reviewed: bool = False
    earned_xp: int = 0
    xp_settled: bool = False
    ai_analysis: str | None = None
    projects_touched: list | None = field(default=None)
    activity_minutes: int | None = None
    source_log_ids: list | None = field(default=None)
    user_feeling: str | None = None
    user_action_plan: str | None = None
    user_learned: str | None = None
    mood_score: int | None = None
    reviewed_at: datetime | None = None
    xp_settled_at: datetime | None = None


def approve_reflection(
    reflection: DraftReflection,
    user_feeling: str,
    user_action_plan: str,
    mood_score: int | None = None,
    user_learned: str | None = None,
) -> DraftReflection:
    """
    [R08 §四.2 + RISK-01] Approve a draft reflection.

    Validates mandatory micro-friction fields before flipping state flags.
    Raises ValueError if validation fails -- callers must not catch silently.
    """
    if not user_feeling or not user_feeling.strip():
        raise ValueError("user_feeling 不可為空 [R08 §四.2 微摩擦力]")
    if not user_action_plan or not user_action_plan.strip():
        raise ValueError("user_action_plan 不可為空 [R08 §四.2 微摩擦力]")
    if mood_score is not None and not (1 <= mood_score <= 10):
        raise ValueError("mood_score 必須在 1-10 範圍")
    if not reflection.is_draft:
        raise ValueError("此反思已核准, 不可重複核准")

    reflection.user_feeling = user_feeling.strip()
    reflection.user_action_plan = user_action_plan.strip()
    reflection.user_learned = user_learned.strip() if user_learned else None
    reflection.mood_score = mood_score
    reflection.is_draft = False
    reflection.is_reviewed = True
    reflection.reviewed_at = datetime.now(UTC)

    return reflection


def can_grant_xp(reflection: DraftReflection) -> bool:
    """
    [RISK-01] XP gatekeeper predicate.

    Returns True only when the reflection has been reviewed AND has a non-empty
    user_feeling. This is the minimal check; M6.5 ACID gatekeeper performs
    the full transactional enforcement at DB level.
    """
    return (
        not reflection.is_draft
        and reflection.is_reviewed
        and bool(reflection.user_feeling and reflection.user_feeling.strip())
    )
