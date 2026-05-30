"""M6.4 v1.1 Refinement -- Segment-level reflection cards

Revision ID: cloud_20260531_1000
Revises: cloud_20260530_1500
Create Date: 2026-05-31 10:00:00.000000

Changes from v1.0:
  - daily_reflections: replace is_draft/is_reviewed/xp flags with
    is_completed/completed_at/total_activity_minutes/streak_multiplier/overall_mood_score
  - daily_reflection_segments: NEW sub-table as the XP settlement unit

Research:
  [R08 §四.2] micro-friction: user_feeling + user_action_plan mandatory per segment
  [R08 §六.1] IKEA effect: XP gated per approved segment (not per day)

Risk mitigation:
  RISK-01: is_draft/is_reviewed moved to segment level; parent becomes a container
  RISK-13: soft-delete via is_active flag; approved segments cannot be hard-deleted
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "cloud_20260531_1000"
down_revision: str | None = "cloud_20260530_1500"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- 1. ALTER daily_reflections: remove draft/XP cols, add completion cols ---
    # Remove v1.0 cols that move to segment level
    op.drop_column("daily_reflections", "user_feeling")
    op.drop_column("daily_reflections", "user_action_plan")
    op.drop_column("daily_reflections", "user_learned")
    op.drop_column("daily_reflections", "mood_score")
    op.drop_column("daily_reflections", "is_draft")
    op.drop_column("daily_reflections", "is_reviewed")
    op.drop_column("daily_reflections", "reviewed_at")
    op.drop_column("daily_reflections", "earned_xp")
    op.drop_column("daily_reflections", "xp_settled")
    op.drop_column("daily_reflections", "xp_settled_at")
    op.drop_column("daily_reflections", "activity_minutes")

    # Add v1.1 completion-tracking cols
    op.add_column("daily_reflections", sa.Column(
        "is_completed", sa.Boolean(), nullable=False, server_default="FALSE",
    ))
    op.add_column("daily_reflections", sa.Column(
        "completed_at", sa.TIMESTAMP(timezone=True), nullable=True,
    ))
    op.add_column("daily_reflections", sa.Column(
        "total_activity_minutes", sa.Integer(), nullable=False, server_default="0",
    ))
    op.add_column("daily_reflections", sa.Column(
        "overall_mood_score", sa.Integer(), nullable=True,
    ))
    op.add_column("daily_reflections", sa.Column(
        "streak_multiplier", sa.Float(), nullable=False, server_default="1.0",
    ))
    # CHECK constraint on overall_mood_score
    op.create_check_constraint(
        "ck_daily_reflections_mood_score",
        "daily_reflections",
        "overall_mood_score >= 1 AND overall_mood_score <= 10",
    )

    # --- 2. CREATE daily_reflection_segments (XP settlement unit) ---
    op.create_table(
        "daily_reflection_segments",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False,
        ),
        sa.Column("reflection_id", sa.UUID(), nullable=False),

        # Source and attribution
        sa.Column("project", sa.Text(), nullable=False),
        sa.Column("expert_id", sa.UUID(), nullable=True),
        sa.Column("chat_id", sa.UUID(), nullable=True),
        sa.Column("source_type", sa.VARCHAR(20), nullable=False),  # monitor/calendar/expert_chat
        sa.Column("segment_time", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("external_ref_id", sa.VARCHAR(255), nullable=True),

        # Behavioural focus metrics (filled by M1.1/M1.2)  [R08 §六.1 IKEA proxy]
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("focus_depth", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("distraction_count", sa.Integer(), nullable=False, server_default="0"),

        # AI objective zone
        sa.Column("ai_description", sa.Text(), nullable=False),
        sa.Column("ai_analysis", sa.Text(), nullable=True),

        # User subjective reflection (micro-friction, mandatory on approve) [R08 §四.2]
        sa.Column("scaffold_prompt", sa.Text(), nullable=True),
        sa.Column("user_feeling", sa.Text(), nullable=True),
        sa.Column("user_action_plan", sa.Text(), nullable=True),
        sa.Column("user_learned", sa.Text(), nullable=True),
        sa.Column("is_aligned", sa.Boolean(), nullable=True),
        sa.Column("mood_score", sa.Integer(), nullable=True),

        # Reflection effort metrics (IKEA effect measurement) [R08 §六.1]
        sa.Column("reflection_word_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reflection_edit_seconds", sa.Integer(), nullable=False, server_default="0"),

        # Task linkage (soft, no FK constraint -- task module not yet built)
        sa.Column("task_id", sa.UUID(), nullable=True),

        # Approval state flags [RISK-01]
        sa.Column("is_draft", sa.Boolean(), nullable=False, server_default="TRUE"),
        sa.Column("is_reviewed", sa.Boolean(), nullable=False, server_default="FALSE"),
        sa.Column("reviewed_at", sa.TIMESTAMP(timezone=True), nullable=True),

        # XP settlement tracking [RISK-01, RISK-13]
        sa.Column("earned_xp", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("xp_settled", sa.Boolean(), nullable=False, server_default="FALSE"),
        sa.Column("xp_settled_at", sa.TIMESTAMP(timezone=True), nullable=True),

        # Soft-delete support [RISK-13]
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="TRUE"),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),

        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True),
            nullable=False, server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True),
            nullable=False, server_default=sa.text("NOW()"),
        ),

        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["reflection_id"], ["daily_reflections.id"], ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["expert_id"], ["ai_experts.id"]),
        sa.CheckConstraint("mood_score >= 1 AND mood_score <= 10", name="ck_drs_mood_score"),
        sa.CheckConstraint("focus_depth >= 0.0 AND focus_depth <= 1.0", name="ck_drs_focus_depth"),
    )

    op.create_index("idx_drs_reflection", "daily_reflection_segments", ["reflection_id"])
    op.create_index("idx_drs_reviewed", "daily_reflection_segments", ["is_reviewed"])
    op.create_index("idx_drs_active", "daily_reflection_segments", ["is_active"])
    op.create_index(
        "idx_drs_task",
        "daily_reflection_segments",
        ["task_id"],
        postgresql_where=sa.text("task_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_table("daily_reflection_segments")

    # Restore v1.0 cols on daily_reflections
    op.drop_column("daily_reflections", "is_completed")
    op.drop_column("daily_reflections", "completed_at")
    op.drop_column("daily_reflections", "total_activity_minutes")
    op.drop_column("daily_reflections", "overall_mood_score")
    op.drop_column("daily_reflections", "streak_multiplier")

    op.add_column("daily_reflections", sa.Column("activity_minutes", sa.Integer(), nullable=True))
    op.add_column("daily_reflections", sa.Column("user_feeling", sa.Text(), nullable=True))
    op.add_column("daily_reflections", sa.Column("user_action_plan", sa.Text(), nullable=True))
    op.add_column("daily_reflections", sa.Column("user_learned", sa.Text(), nullable=True))
    op.add_column("daily_reflections", sa.Column("mood_score", sa.Integer(), nullable=True))
    op.add_column("daily_reflections", sa.Column("is_draft", sa.Boolean(), nullable=False, server_default="TRUE"))
    op.add_column("daily_reflections", sa.Column("is_reviewed", sa.Boolean(), nullable=False, server_default="FALSE"))
    op.add_column("daily_reflections", sa.Column("reviewed_at", sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column("daily_reflections", sa.Column("earned_xp", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("daily_reflections", sa.Column("xp_settled", sa.Boolean(), nullable=False, server_default="FALSE"))
    op.add_column("daily_reflections", sa.Column("xp_settled_at", sa.TIMESTAMP(timezone=True), nullable=True))
