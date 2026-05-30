"""
M6.4 v1.1 -- Segment-level approval tests

SPEC: docs/modules/M6_4_daily_reflections_SPEC.md v1.1
Risk: RISK-01 (XP gated per segment), RISK-13 (soft-delete guard)
Research:
  [R08 §四.2] micro-friction: both fields mandatory per approved segment
  [R08 §六.1] IKEA effect: user effort per segment gates XP
"""
import uuid
from datetime import UTC, datetime

import pytest
from services.m6_4_daily_reflections.approve import (
    DraftReflection,
    DraftReflectionSegment,
    SegmentUpdateInput,
    approve_daily_reflection_flow,
    can_grant_segment_xp,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_reflection(**kw) -> DraftReflection:
    defaults = dict(
        id=uuid.uuid4(), user_id=uuid.uuid4(), role_id=uuid.uuid4(),
        reflection_date=__import__("datetime").date.today(),
        ai_description="3h VS Code",
    )
    return DraftReflection(**{**defaults, **kw})


def make_segment(reflection_id: uuid.UUID = None, **kw) -> DraftReflectionSegment:
    defaults = dict(
        id=uuid.uuid4(),
        reflection_id=reflection_id or uuid.uuid4(),
        project="OS Lab",
        source_type="monitor",
        segment_time=datetime.now(UTC),
        ai_description="Wrote kernel scheduler",
        duration_minutes=60,
    )
    return DraftReflectionSegment(**{**defaults, **kw})


def make_update(segment_id: uuid.UUID, feeling: str = None, action: str = None, **kw) -> SegmentUpdateInput:
    return SegmentUpdateInput(
        segment_id=segment_id,
        user_feeling=feeling,
        user_action_plan=action,
        **kw,
    )


# ---------------------------------------------------------------------------
# TestSegmentApproval
# ---------------------------------------------------------------------------

class TestSegmentApproval:
    def test_approve_one_segment_marks_parent_completed(self):
        """AC-1: approving one segment marks parent is_completed=True."""
        r = make_reflection()
        seg = make_segment(reflection_id=r.id)
        up = make_update(seg.id, feeling="Proud", action="Keep momentum")

        r2, segs = approve_daily_reflection_flow(r, [seg], [up])

        assert r2.is_completed is True
        assert r2.completed_at is not None
        assert segs[0].is_reviewed is True
        assert segs[0].is_draft is False

    def test_reviewed_segment_flips_state_flags(self):
        """AC-2: approved segment is_draft=False, is_reviewed=True, reviewed_at set."""
        r = make_reflection()
        seg = make_segment(reflection_id=r.id)
        up = make_update(seg.id, feeling="OK", action="繼續")

        _, segs = approve_daily_reflection_flow(r, [seg], [up])
        s = segs[0]

        assert s.is_draft is False
        assert s.is_reviewed is True
        assert s.reviewed_at is not None

    def test_partial_fill_raises_microfiction_error(self):
        """AC-3: [R08 §四.2] feeling only or action only raises ValueError."""
        r = make_reflection()
        seg = make_segment(reflection_id=r.id)
        up_feeling_only = make_update(seg.id, feeling="Good", action=None)

        with pytest.raises(ValueError, match=r"\[R08"):
            approve_daily_reflection_flow(r, [seg], [up_feeling_only])

        seg2 = make_segment(reflection_id=r.id)
        up_action_only = make_update(seg2.id, feeling=None, action="Fix tests")
        with pytest.raises(ValueError, match=r"\[R08"):
            approve_daily_reflection_flow(r, [seg2], [up_action_only])

    def test_no_approved_segments_raises_error(self):
        """AC-4: [RISK-01] if no segment is approved, flow raises ValueError."""
        r = make_reflection()
        seg = make_segment(reflection_id=r.id)
        up = make_update(seg.id, feeling=None, action=None)  # both empty -- skip

        with pytest.raises(ValueError, match="At least one segment"):
            approve_daily_reflection_flow(r, [seg], [up])

    def test_mixed_segments_partial_approved(self):
        """AC-5: only one of two segments approved -> parent completes, skipped stays draft."""
        r = make_reflection()
        seg1 = make_segment(reflection_id=r.id)
        seg2 = make_segment(reflection_id=r.id)
        up1 = make_update(seg1.id, feeling="Great", action="Double down")
        up2 = make_update(seg2.id, feeling=None, action=None)  # skipped

        r2, segs = approve_daily_reflection_flow(r, [seg1, seg2], [up1, up2])

        assert r2.is_completed is True
        approved = [s for s in segs if s.is_reviewed]
        skipped = [s for s in segs if not s.is_reviewed]
        assert len(approved) == 1
        assert len(skipped) == 1
        assert skipped[0].is_draft is True

    def test_total_activity_minutes_aggregated(self):
        """AC-6: parent total_activity_minutes is sum of all active segment durations."""
        r = make_reflection()
        seg1 = make_segment(reflection_id=r.id, duration_minutes=60)
        seg2 = make_segment(reflection_id=r.id, duration_minutes=90)
        up = make_update(seg1.id, feeling="Good", action="Next task")

        r2, _ = approve_daily_reflection_flow(r, [seg1, seg2], [up])

        assert r2.total_activity_minutes == 150

    def test_reflection_word_count_recorded(self):
        """AC-7: [R08 §六.1] reflection_word_count is non-zero after approval."""
        r = make_reflection()
        seg = make_segment(reflection_id=r.id)
        up = make_update(seg.id, feeling="Felt great working on this", action="Keep coding every day")

        _, segs = approve_daily_reflection_flow(r, [seg], [up])

        assert segs[0].reflection_word_count > 0

    def test_mood_score_validation(self):
        """AC-8: mood_score must be 1-10, out-of-range raises ValueError."""
        r = make_reflection()
        seg = make_segment(reflection_id=r.id)
        up = make_update(seg.id, feeling="OK", action="Go", mood_score=11)

        with pytest.raises(ValueError, match="mood_score"):
            approve_daily_reflection_flow(r, [seg], [up])

    def test_soft_deleted_segment_skipped(self):
        """AC-9: [RISK-13] is_active=False segments are excluded from approval flow."""
        r = make_reflection()
        soft_deleted = make_segment(reflection_id=r.id, is_active=False)
        active = make_segment(reflection_id=r.id, is_active=True)
        up_soft = make_update(soft_deleted.id, feeling="Ignored", action="Ignored")
        up_active = make_update(active.id, feeling="Valid", action="Action")

        r2, segs = approve_daily_reflection_flow(r, [soft_deleted, active], [up_soft, up_active])

        assert r2.is_completed is True
        active_segs = [s for s in segs if s.is_active]
        assert active_segs[0].is_reviewed is True

    def test_already_approved_cannot_re_approve(self):
        """AC-10: attempting to approve an already-reviewed segment raises ValueError."""
        r = make_reflection()
        seg = make_segment(reflection_id=r.id, is_draft=False, is_reviewed=True)
        up = make_update(seg.id, feeling="Again", action="Again")

        with pytest.raises(ValueError, match="already approved"):
            approve_daily_reflection_flow(r, [seg], [up])

    def test_already_approved_segment_counts_for_completion(self):
        """AC-11: previously approved segment (no update) still contributes to completion."""
        r = make_reflection()
        already_done = make_segment(reflection_id=r.id, is_draft=False, is_reviewed=True)
        new_seg = make_segment(reflection_id=r.id)
        # No update for already_done; update for new_seg with empty fields (skip)
        up_new = make_update(new_seg.id, feeling=None, action=None)

        r2, _ = approve_daily_reflection_flow(r, [already_done, new_seg], [up_new])

        assert r2.is_completed is True


# ---------------------------------------------------------------------------
# TestCanGrantSegmentXP
# ---------------------------------------------------------------------------

class TestCanGrantSegmentXP:
    def test_xp_blocked_for_draft(self):
        """[RISK-01] draft segment cannot grant XP."""
        seg = make_segment(is_draft=True, is_reviewed=False)
        assert can_grant_segment_xp(seg) is False

    def test_xp_blocked_for_inactive(self):
        """[RISK-13] soft-deleted segment cannot grant XP."""
        seg = make_segment(is_draft=False, is_reviewed=True, user_feeling="OK", is_active=False)
        assert can_grant_segment_xp(seg) is False

    def test_xp_blocked_missing_user_feeling(self):
        """[RISK-01] reviewed but no user_feeling blocks XP."""
        seg = make_segment(is_draft=False, is_reviewed=True, user_feeling=None, is_active=True)
        assert can_grant_segment_xp(seg) is False

    def test_xp_allowed_for_approved_segment(self):
        """[RISK-01] fully approved active segment can grant XP."""
        seg = make_segment(
            is_draft=False, is_reviewed=True,
            user_feeling="Productive", is_active=True,
        )
        assert can_grant_segment_xp(seg) is True
