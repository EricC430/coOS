"""M4.3 v1.2 -- goals and promises tables for commitment context

Revision ID: 20260603_2000
Revises: 20260531_1200
Create Date: 2026-06-03 20:00:00.000000

SPEC: docs/modules/M4_3_role_isolation_SPEC.md §7.2 build_commitment_context()
Note: DDL already applied to Supabase via MCP migration.
      This file exists to keep alembic_cloud version history in sync.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260603_2000"
down_revision: str | None = "cloud_20260531_1200"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "goals",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("role_id", sa.UUID(), nullable=False),
        sa.Column("persona_id", sa.UUID(), nullable=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("progress", sa.Float(), server_default="0.0"),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(20), server_default="'active'"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["persona_id"], ["ai_experts.id"], ondelete="SET NULL"),
        sa.CheckConstraint("progress >= 0.0 AND progress <= 1.0"),
        sa.CheckConstraint("status IN ('active','completed','paused','abandoned')"),
    )
    op.create_index("idx_goals_role_status", "goals", ["role_id", "status"])
    op.create_index("idx_goals_persona", "goals", ["persona_id"])

    op.create_table(
        "promises",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("role_id", sa.UUID(), nullable=False),
        sa.Column("persona_id", sa.UUID(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("deadline", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("source_thread_id", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), server_default="'active'"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["persona_id"], ["ai_experts.id"], ondelete="SET NULL"),
        sa.CheckConstraint("status IN ('active','fulfilled','expired','cancelled')"),
    )
    op.create_index("idx_promises_role_status", "promises", ["role_id", "status"])
    op.create_index("idx_promises_deadline", "promises", ["deadline"])
    op.create_index("idx_promises_persona", "promises", ["persona_id"])


def downgrade() -> None:
    op.drop_index("idx_promises_persona", "promises")
    op.drop_index("idx_promises_deadline", "promises")
    op.drop_index("idx_promises_role_status", "promises")
    op.drop_table("promises")
    op.drop_index("idx_goals_persona", "goals")
    op.drop_index("idx_goals_role_status", "goals")
    op.drop_table("goals")
