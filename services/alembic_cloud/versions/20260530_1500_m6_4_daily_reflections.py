"""M6.4 daily_reflections -- cloud PostgreSQL

Revision ID: cloud_20260530_1500
Revises: cloud_20260530_1400
Create Date: 2026-05-30 15:00:00.000000

Draft & Approve mechanism for structured daily reflections.
Stores L3 business-state data (user_feeling is sensitive but consented per SPEC §9).

Research:
  [R08 §五]   AI fills ai_description (objective), user fills user_feeling (subjective)
  [R08 §四.2] user_feeling + user_action_plan mandatory to approve (micro-friction)
  [R08 §六.1] IKEA effect: is_reviewed=True gates XP settlement
  [R10 §MindScape] structured reflection template

Risk mitigation:
  RISK-01: is_draft + is_reviewed flags; M6.5 ACID gatekeeper enforces at tx level
  RISK-10: mood_score CHECK [1,10] provides absolute baseline for Wrapped stats
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "cloud_20260530_1500"
down_revision: str | None = "cloud_20260530_1400"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "daily_reflections",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("role_id", sa.UUID(), nullable=False),
        sa.Column("reflection_date", sa.Date(), nullable=False),

        # AI-generated zone (objective, system-written)
        sa.Column("ai_description", sa.Text(), nullable=False),
        sa.Column("ai_analysis", sa.Text(), nullable=True),
        sa.Column("projects_touched", sa.Text(), nullable=True),    # JSON array
        sa.Column("activity_minutes", sa.Integer(), nullable=True),
        sa.Column("source_log_ids", sa.Text(), nullable=True),       # JSON array

        # User-written zone (subjective, micro-friction) [R08 §四.2]
        sa.Column("user_feeling", sa.Text(), nullable=True),
        sa.Column("user_action_plan", sa.Text(), nullable=True),
        sa.Column("user_learned", sa.Text(), nullable=True),
        sa.Column("mood_score", sa.Integer(), nullable=True),        # [RISK-10] 1-10

        # State flags [RISK-01]
        sa.Column("is_draft", sa.Boolean(), nullable=False, server_default="TRUE"),
        sa.Column("is_reviewed", sa.Boolean(), nullable=False, server_default="FALSE"),
        sa.Column("reviewed_at", sa.TIMESTAMP(timezone=True), nullable=True),

        # XP settlement tracking
        sa.Column("earned_xp", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("xp_settled", sa.Boolean(), nullable=False, server_default="FALSE"),
        sa.Column("xp_settled_at", sa.TIMESTAMP(timezone=True), nullable=True),

        # Metadata
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),

        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"]),
        # [R08 §六.1] one reflection per role per day
        sa.UniqueConstraint("user_id", "role_id", "reflection_date", name="uq_dr_user_role_date"),
        # [RISK-10] mood_score absolute range
        sa.CheckConstraint("mood_score >= 1 AND mood_score <= 10", name="chk_dr_mood"),
    )
    op.create_index("idx_dr_user_date", "daily_reflections", ["user_id", "reflection_date"])
    op.create_index("idx_dr_role", "daily_reflections", ["role_id"])
    op.create_index("idx_dr_reviewed", "daily_reflections", ["is_reviewed"])
    # Partial index: only draft rows (PostgreSQL supports WHERE clause)
    op.execute(
        "CREATE INDEX idx_dr_draft ON daily_reflections(is_draft) WHERE is_draft = TRUE"
    )


def downgrade() -> None:
    op.drop_table("daily_reflections")
