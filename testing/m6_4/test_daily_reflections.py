"""
M6.4 -- Daily Reflections acceptance tests

SPEC: docs/modules/M6_4_daily_reflections_SPEC.md
Risk: RISK-01 (XP must not be granted before is_reviewed=True)
     RISK-10 (mood_score as absolute baseline for Wrapped)
Research:
  [R08 §四.2] user_feeling + user_action_plan are mandatory micro-friction
  [R08 §五]   AI fills objective data, user fills subjective
  [R08 §六.1] IKEA effect -- user effort gates XP
  [R10 §MindScape] structured reflection template
"""
import uuid
from datetime import date
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CLOUD_MIGRATION_DIR = PROJECT_ROOT / "services" / "alembic_cloud" / "versions"


# ---------------------------------------------------------------------------
# Static migration audit (always runs)
# ---------------------------------------------------------------------------

class TestMigrationAudit:
    def test_cloud_migration_has_daily_reflections(self):
        """AC: cloud migration must define daily_reflections table."""
        content = _cloud_migration_content()
        assert "daily_reflections" in content

    def test_daily_reflection_segments_has_is_draft_column(self):
        """AC: [R08 §五] v1.1 -- is_draft now on segments table."""
        content = _cloud_migration_content()
        assert "is_draft" in content
        assert "daily_reflection_segments" in content

    def test_daily_reflection_segments_has_is_reviewed_column(self):
        """AC: [RISK-01] is_reviewed on segments table."""
        content = _cloud_migration_content()
        assert "is_reviewed" in content

    def test_daily_reflection_segments_has_mood_score_check(self):
        """AC: [RISK-10] mood_score check constraint exists in segments migration."""
        content = _cloud_migration_content()
        assert "mood_score" in content
        assert "ck_drs_mood_score" in content or "mood_score >= 1" in content

    def test_daily_reflections_has_unique_constraint(self):
        """AC: [R08 §六.1] (user_id, role_id, reflection_date) unique constraint."""
        content = _cloud_migration_content()
        assert "reflection_date" in content
        assert "uq_dr" in content or "unique" in content.lower()


# ---------------------------------------------------------------------------
# Pydantic model tests (always runs)
# ---------------------------------------------------------------------------

class TestDailyReflectionModels:
    def test_draft_create_requires_ai_description(self):
        """AC-1: [R08 §五] ai_description must be non-empty (min 10 chars)."""
        from services.m6_4_daily_reflections.models import DailyReflectionCreate

        with pytest.raises(Exception):
            DailyReflectionCreate(
                user_id=uuid.uuid4(),
                role_id=uuid.uuid4(),
                reflection_date=date.today(),
                ai_description="short",  # < 10 chars
            )

    def test_user_reflection_input_rejects_empty_feeling(self):
        """AC-2: [R08 §四.2] user_feeling must not be empty or whitespace-only."""
        from services.m6_4_daily_reflections.models import UserReflectionInput

        with pytest.raises(Exception):
            UserReflectionInput(user_feeling="", user_action_plan="明天繼續")

        with pytest.raises(Exception):
            UserReflectionInput(user_feeling="   ", user_action_plan="明天繼續")

    def test_user_reflection_input_rejects_empty_action_plan(self):
        """AC-3: [R08 §四.2] user_action_plan must not be empty or whitespace-only."""
        from services.m6_4_daily_reflections.models import UserReflectionInput

        with pytest.raises(Exception):
            UserReflectionInput(user_feeling="有點挫折", user_action_plan="")

    def test_user_reflection_input_mood_score_range(self):
        """AC-7: [RISK-10] mood_score must be in [1, 10]."""
        from services.m6_4_daily_reflections.models import UserReflectionInput

        valid = UserReflectionInput(
            user_feeling="OK", user_action_plan="繼續", mood_score=7
        )
        assert valid.mood_score == 7

        with pytest.raises(Exception):
            UserReflectionInput(
                user_feeling="OK", user_action_plan="繼續", mood_score=0
            )

        with pytest.raises(Exception):
            UserReflectionInput(
                user_feeling="OK", user_action_plan="繼續", mood_score=11
            )

    def test_user_reflection_strips_whitespace(self):
        """AC: whitespace is stripped from user_feeling and user_action_plan."""
        from services.m6_4_daily_reflections.models import UserReflectionInput

        inp = UserReflectionInput(
            user_feeling="  有進步  ", user_action_plan="  繼續保持  "
        )
        assert inp.user_feeling == "有進步"
        assert inp.user_action_plan == "繼續保持"


# ---------------------------------------------------------------------------
# Business logic tests (always runs, in-memory only)
# ---------------------------------------------------------------------------

class TestDraftApproveLifecycle:
    """[R08 §四~六] Draft & Approve business logic -- v1.1 segment-level API."""

    def _make_reflection(self):
        from services.m6_4_daily_reflections.approve import DraftReflection
        return DraftReflection(
            id=uuid.uuid4(), user_id=uuid.uuid4(), role_id=uuid.uuid4(),
            reflection_date=date.today(), ai_description="VS Code 寫了 3 小時 Rust",
        )

    def _make_segment(self, reflection_id, **kw):
        from datetime import UTC, datetime

        from services.m6_4_daily_reflections.approve import DraftReflectionSegment
        defaults = dict(
            id=uuid.uuid4(), reflection_id=reflection_id,
            project="OS", source_type="monitor",
            segment_time=datetime.now(UTC), ai_description="Wrote scheduler",
        )
        return DraftReflectionSegment(**{**defaults, **kw})

    def _make_update(self, segment_id, feeling=None, action=None):
        from services.m6_4_daily_reflections.approve import SegmentUpdateInput
        return SegmentUpdateInput(segment_id=segment_id, user_feeling=feeling, user_action_plan=action)

    def test_new_segment_is_draft(self):
        """AC-1: [R08 §五] new segment must start as draft."""
        seg = self._make_segment(uuid.uuid4())
        assert seg.is_draft is True
        assert seg.is_reviewed is False
        assert seg.user_feeling is None

    def test_approve_requires_user_feeling(self):
        """AC-2: [R08 §四.2] segment approval requires non-empty user_feeling."""
        from services.m6_4_daily_reflections.approve import approve_daily_reflection_flow
        r = self._make_reflection()
        seg = self._make_segment(r.id)
        with pytest.raises(ValueError, match=r"\[R08"):
            approve_daily_reflection_flow(r, [seg], [self._make_update(seg.id, feeling="OK", action=None)])

    def test_approve_requires_user_action_plan(self):
        """AC-3: [R08 §四.2] segment approval requires non-empty user_action_plan."""
        from services.m6_4_daily_reflections.approve import approve_daily_reflection_flow
        r = self._make_reflection()
        seg = self._make_segment(r.id)
        with pytest.raises(ValueError, match=r"\[R08"):
            approve_daily_reflection_flow(r, [seg], [self._make_update(seg.id, feeling=None, action="Plan")])

    def test_approved_reflection_flips_flags(self):
        """AC-4: after segment approval, parent is_completed=True, segment is_reviewed=True."""
        from services.m6_4_daily_reflections.approve import approve_daily_reflection_flow
        r = self._make_reflection()
        seg = self._make_segment(r.id)
        up = self._make_update(seg.id, feeling="覺得有進步", action="繼續保持現在的節奏")
        r2, segs = approve_daily_reflection_flow(r, [seg], [up])
        assert r2.is_completed is True
        assert segs[0].is_reviewed is True
        assert segs[0].reviewed_at is not None

    def test_cannot_approve_already_approved(self):
        """AC: [R08 §六.1] already-reviewed segment re-approve is rejected."""

        from services.m6_4_daily_reflections.approve import (
            approve_daily_reflection_flow,
        )
        r = self._make_reflection()
        seg = self._make_segment(r.id, is_draft=False, is_reviewed=True)
        up = self._make_update(seg.id, feeling="再試", action="再試")
        with pytest.raises(ValueError, match="already approved"):
            approve_daily_reflection_flow(r, [seg], [up])


class TestXPGating:
    """[RISK-01] XP must not be granted before segment is_reviewed=True."""

    def _make_segment(self, is_draft=True, is_reviewed=False, user_feeling=None, is_active=True):
        from datetime import UTC, datetime

        from services.m6_4_daily_reflections.approve import DraftReflectionSegment
        return DraftReflectionSegment(
            id=uuid.uuid4(), reflection_id=uuid.uuid4(),
            project="OS", source_type="monitor",
            segment_time=datetime.now(UTC), ai_description="Wrote code",
            is_draft=is_draft, is_reviewed=is_reviewed,
            user_feeling=user_feeling, is_active=is_active,
        )

    def test_xp_blocked_for_draft(self):
        """AC-5: [RISK-01] draft segment must block XP."""
        from services.m6_4_daily_reflections.approve import can_grant_segment_xp
        seg = self._make_segment(is_draft=True, is_reviewed=False)
        assert can_grant_segment_xp(seg) is False

    def test_xp_blocked_without_user_feeling(self):
        """AC-5b: [RISK-01] reviewed but no user_feeling still blocks XP."""
        from services.m6_4_daily_reflections.approve import can_grant_segment_xp
        seg = self._make_segment(is_draft=False, is_reviewed=True, user_feeling=None)
        assert can_grant_segment_xp(seg) is False

    def test_xp_allowed_after_review(self):
        """AC-6: [RISK-01] XP allowed after is_reviewed=True with user_feeling."""
        from services.m6_4_daily_reflections.approve import can_grant_segment_xp
        seg = self._make_segment(is_draft=False, is_reviewed=True, user_feeling="OK")
        assert can_grant_segment_xp(seg) is True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cloud_migration_content() -> str:
    content = ""
    for f in CLOUD_MIGRATION_DIR.glob("*.py"):
        if f.name != "__init__.py":
            content += f.read_text(encoding="utf-8")
    return content
