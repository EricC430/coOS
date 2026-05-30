"""
M6.4 v1.1 -- Draft & Approve business logic (segment-level)

SPEC: docs/modules/M6_4_daily_reflections_SPEC.md v1.1
Research:
  [R08 §四.2] micro-friction: user_feeling + user_action_plan mandatory per segment
  [R08 §六.1] IKEA effect: XP gated per approved segment, not per day
Risk mitigation:
  RISK-01: XP gated at segment level; parent marks is_completed only when >= 1 approved
  RISK-13: soft-delete semantics; approved segments MUST NOT be hard-deleted
"""
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from uuid import UUID


@dataclass
class DraftReflection:
    """Parent daily reflection -- container and day-level stats."""

    id: UUID
    user_id: UUID
    role_id: UUID
    reflection_date: date
    ai_description: str
    ai_analysis: str | None = None
    projects_touched: list | None = field(default=None)
    source_log_ids: list | None = field(default=None)

    # Completion tracking (v1.1 -- replaces is_draft/is_reviewed at parent level)
    is_completed: bool = False
    completed_at: datetime | None = None
    total_activity_minutes: int = 0
    overall_mood_score: int | None = None
    streak_multiplier: float = 1.0


@dataclass
class DraftReflectionSegment:
    """Single time-slot reflection card -- the XP settlement unit."""

    id: UUID
    reflection_id: UUID
    project: str
    source_type: str  # 'monitor' | 'calendar' | 'expert_chat'
    segment_time: datetime
    ai_description: str

    expert_id: UUID | None = None
    chat_id: UUID | None = None
    external_ref_id: str | None = None
    duration_minutes: int = 0
    focus_depth: float = 1.0
    distraction_count: int = 0
    ai_analysis: str | None = None
    scaffold_prompt: str | None = None

    # User reflection zone (mandatory on approve) [R08 §四.2]
    user_feeling: str | None = None
    user_action_plan: str | None = None
    user_learned: str | None = None
    is_aligned: bool | None = None
    mood_score: int | None = None

    # Engagement metrics [R08 §六.1]
    reflection_word_count: int = 0
    reflection_edit_seconds: int = 0

    task_id: UUID | None = None

    # Approval state [RISK-01]
    is_draft: bool = True
    is_reviewed: bool = False
    reviewed_at: datetime | None = None

    # XP settlement
    earned_xp: int = 0
    xp_settled: bool = False
    xp_settled_at: datetime | None = None

    # Soft-delete [RISK-13]
    is_active: bool = True
    deleted_at: datetime | None = None


@dataclass
class SegmentUpdateInput:
    """User-submitted update for one segment card."""

    segment_id: UUID
    user_feeling: str | None = None
    user_action_plan: str | None = None
    user_learned: str | None = None
    is_aligned: bool | None = None
    mood_score: int | None = None
    reflection_edit_seconds: int = 0


def approve_daily_reflection_flow(
    reflection: DraftReflection,
    segments: list[DraftReflectionSegment],
    updates: list[SegmentUpdateInput],
) -> tuple[DraftReflection, list[DraftReflectionSegment]]:
    """
    [R08 §四.2, RISK-01] Batch approve segment cards for one day/role.

    Rules:
    - At least one segment must be fully approved (feeling + action_plan non-empty).
    - Partial fill (only feeling OR only action_plan) raises ValueError immediately.
    - Segments with no update or both fields empty remain is_draft=True (optional).
    - Parent is_completed flips to True when >= 1 segment is approved.
    """
    update_map = {up.segment_id: up for up in updates}
    updated_segments = []
    any_approved = False
    total_minutes = 0

    for seg in segments:
        if not seg.is_active:
            continue  # skip soft-deleted segments

        total_minutes += seg.duration_minutes

        up = update_map.get(seg.id)
        if not up:
            updated_segments.append(seg)
            if seg.is_reviewed:
                any_approved = True
            continue

        has_feeling = bool(up.user_feeling and up.user_feeling.strip())
        has_action = bool(up.user_action_plan and up.user_action_plan.strip())

        if has_feeling and has_action:
            # Full approval path [R08 §四.2]
            if not seg.is_draft:
                raise ValueError(f"Segment {seg.id} already approved, cannot re-approve")

            seg.user_feeling = up.user_feeling.strip()
            seg.user_action_plan = up.user_action_plan.strip()
            seg.user_learned = up.user_learned.strip() if up.user_learned else None
            seg.is_aligned = up.is_aligned
            seg.mood_score = up.mood_score
            if up.mood_score is not None and not (1 <= up.mood_score <= 10):
                raise ValueError("mood_score must be 1-10")

            # Engagement metrics [R08 §六.1 IKEA effect proxy]
            full_text = " ".join(filter(None, [
                seg.user_feeling, seg.user_action_plan, seg.user_learned,
            ]))
            seg.reflection_word_count = len(full_text.split())
            seg.reflection_edit_seconds = max(0, up.reflection_edit_seconds)

            seg.is_draft = False
            seg.is_reviewed = True
            seg.reviewed_at = datetime.now(UTC)
            any_approved = True

        elif has_feeling or has_action:
            # Partial fill -- micro-friction guard rejects incomplete submissions
            raise ValueError(
                "[R08 §四.2] user_feeling and user_action_plan must both be filled "
                "or both be empty. Partial submission is not allowed."
            )
        else:
            # Both empty -- user skips this segment (optional)
            seg.user_learned = up.user_learned.strip() if up.user_learned else None
            seg.is_aligned = up.is_aligned
            seg.mood_score = up.mood_score

        updated_segments.append(seg)

    if not any_approved:
        raise ValueError(
            "[RISK-01] At least one segment must be approved for the day to be complete."
        )

    # Mark parent as completed
    reflection.is_completed = True
    reflection.completed_at = datetime.now(UTC)
    reflection.total_activity_minutes = total_minutes

    return reflection, updated_segments


def can_grant_segment_xp(segment: DraftReflectionSegment) -> bool:
    """
    [RISK-01] Segment-level XP gate predicate.

    Returns True only when segment is reviewed AND user_feeling non-empty.
    M6.5 ACID gatekeeper performs the full transactional enforcement.
    """
    return (
        not segment.is_draft
        and segment.is_reviewed
        and segment.is_active
        and bool(segment.user_feeling and segment.user_feeling.strip())
    )


# --- Backward compatibility (v1.0 callers) ---

def approve_reflection(
    reflection: DraftReflection,
    user_feeling: str,
    user_action_plan: str,
    mood_score: int | None = None,
    user_learned: str | None = None,
) -> DraftReflection:
    """
    Deprecated v1.0 API -- operates on parent reflection directly.
    Use approve_daily_reflection_flow() for segment-level approval.
    """
    if not user_feeling or not user_feeling.strip():
        raise ValueError("user_feeling cannot be empty [R08 §四.2]")
    if not user_action_plan or not user_action_plan.strip():
        raise ValueError("user_action_plan cannot be empty [R08 §四.2]")
    if mood_score is not None and not (1 <= mood_score <= 10):
        raise ValueError("mood_score must be 1-10")
    if reflection.is_completed:
        raise ValueError("Reflection already completed, cannot re-approve")

    reflection.is_completed = True
    reflection.completed_at = datetime.now(UTC)
    reflection.overall_mood_score = mood_score
    return reflection


def can_grant_xp(reflection: DraftReflection) -> bool:
    """Deprecated v1.0 API -- use can_grant_segment_xp() instead."""
    return reflection.is_completed
