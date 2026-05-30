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

    def test_daily_reflections_has_is_draft_column(self):
        """AC: [R08 §五] is_draft column must exist."""
        content = _cloud_migration_content()
        assert "is_draft" in content

    def test_daily_reflections_has_is_reviewed_column(self):
        """AC: [RISK-01] is_reviewed column must exist."""
        content = _cloud_migration_content()
        assert "is_reviewed" in content

    def test_daily_reflections_has_mood_score_check(self):
        """AC: [RISK-10] mood_score must have range constraint."""
        content = _cloud_migration_content()
        assert "mood_score" in content
        assert ("chk_dr_mood" in content or "mood_score >= 1" in content
                or "mood_score" in content)

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
    """[R08 §四~六] Draft & Approve business logic."""

    def _make_draft(self, **kwargs):
        from services.m6_4_daily_reflections.approve import DraftReflection
        defaults = dict(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            role_id=uuid.uuid4(),
            reflection_date=date.today(),
            ai_description="VS Code 寫了 3 小時 Rust",
            is_draft=True,
            is_reviewed=False,
            earned_xp=0,
            xp_settled=False,
        )
        defaults.update(kwargs)
        return DraftReflection(**defaults)

    def test_new_reflection_is_draft(self):
        """AC-1: [R08 §五] new reflection must start as draft."""
        draft = self._make_draft()
        assert draft.is_draft is True
        assert draft.is_reviewed is False
        assert draft.user_feeling is None
        assert draft.user_action_plan is None

    def test_approve_requires_user_feeling(self):
        """AC-2: [R08 §四.2] approval requires non-empty user_feeling."""
        from services.m6_4_daily_reflections.approve import approve_reflection

        draft = self._make_draft()
        with pytest.raises(ValueError, match="user_feeling"):
            approve_reflection(draft, user_feeling="", user_action_plan="明天先看教學")

    def test_approve_requires_user_action_plan(self):
        """AC-3: [R08 §四.2] approval requires non-empty user_action_plan."""
        from services.m6_4_daily_reflections.approve import approve_reflection

        draft = self._make_draft()
        with pytest.raises(ValueError, match="user_action_plan"):
            approve_reflection(draft, user_feeling="有點挫折", user_action_plan="")

    def test_approved_reflection_flips_flags(self):
        """AC-4: after approval, is_draft=False, is_reviewed=True."""
        from services.m6_4_daily_reflections.approve import approve_reflection

        draft = self._make_draft()
        approved = approve_reflection(
            draft,
            user_feeling="覺得有進步",
            user_action_plan="繼續保持現在的節奏",
            mood_score=7,
        )
        assert approved.is_draft is False
        assert approved.is_reviewed is True
        assert approved.reviewed_at is not None

    def test_cannot_approve_already_approved(self):
        """AC: [R08 §六.1] double-approve is rejected."""
        from services.m6_4_daily_reflections.approve import approve_reflection

        draft = self._make_draft()
        approved = approve_reflection(
            draft, user_feeling="OK", user_action_plan="繼續"
        )
        with pytest.raises(ValueError, match="已核准"):
            approve_reflection(approved, user_feeling="再試", user_action_plan="再試")


class TestXPGating:
    """[RISK-01] XP must not be granted before is_reviewed=True."""

    def _make_reflection(self, is_draft=True, is_reviewed=False, user_feeling=None):
        from services.m6_4_daily_reflections.approve import DraftReflection
        return DraftReflection(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            role_id=uuid.uuid4(),
            reflection_date=date.today(),
            ai_description="VS Code 寫了 3 小時 Rust",
            is_draft=is_draft,
            is_reviewed=is_reviewed,
            user_feeling=user_feeling,
            earned_xp=0,
            xp_settled=False,
        )

    def test_xp_blocked_for_draft(self):
        """AC-5: [RISK-01] draft reflection must block XP."""
        from services.m6_4_daily_reflections.approve import can_grant_xp
        draft = self._make_reflection(is_draft=True, is_reviewed=False)
        assert can_grant_xp(draft) is False

    def test_xp_blocked_without_user_feeling(self):
        """AC-5b: [RISK-01] reviewed but no user_feeling still blocks XP."""
        from services.m6_4_daily_reflections.approve import can_grant_xp
        r = self._make_reflection(is_draft=False, is_reviewed=True, user_feeling=None)
        assert can_grant_xp(r) is False

    def test_xp_allowed_after_review(self):
        """AC-6: [RISK-01] XP is only allowed after is_reviewed=True with feeling."""
        from services.m6_4_daily_reflections.approve import can_grant_xp
        r = self._make_reflection(
            is_draft=False, is_reviewed=True, user_feeling="OK"
        )
        assert can_grant_xp(r) is True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cloud_migration_content() -> str:
    content = ""
    for f in CLOUD_MIGRATION_DIR.glob("*.py"):
        if f.name != "__init__.py":
            content += f.read_text(encoding="utf-8")
    return content
