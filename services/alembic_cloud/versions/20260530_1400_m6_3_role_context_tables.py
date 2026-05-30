"""M6.3 role_projects + role_settings -- cloud PostgreSQL

Revision ID: cloud_20260530_1400
Revises: cloud_20260530_1300
Create Date: 2026-05-30 14:00:00.000000

role_projects  -- role-scoped project/course/goal records (L3)
role_settings  -- per-role UI and notification preferences (L3)

Note: role_implicit_states is intentionally excluded here -- it lives
in local SQLite (SPEC §9 decision). Putting it in cloud would violate
the L2 privacy boundary (CLAUDE.md §隱私三層原則).

RISK-06 mitigation: role_projects / role_settings use ON DELETE CASCADE
so orphan records are impossible when a role is deleted.
Research: [R03 §6] role-scoped data prevents cross-role contamination.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "cloud_20260530_1400"
down_revision: str | None = "cloud_20260530_1300"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "role_projects",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("role_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="'active'"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
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
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "status IN ('active','completed','paused','archived')",
            name="chk_rp_status",
        ),
    )
    op.create_index("idx_rp_role", "role_projects", ["role_id"])

    op.create_table(
        "role_settings",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("role_id", sa.UUID(), nullable=False),
        sa.Column("theme", sa.String(20), nullable=True, server_default="'default'"),
        sa.Column("notification_enabled", sa.Boolean(), nullable=True, server_default="TRUE"),
        sa.Column("daily_report_time", sa.Time(), nullable=True, server_default="'22:00'"),
        sa.Column("focus_hours_start", sa.Time(), nullable=True, server_default="'09:00'"),
        sa.Column("focus_hours_end", sa.Time(), nullable=True, server_default="'18:00'"),
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
        sa.UniqueConstraint("role_id", name="uq_rs_role"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("role_settings")
    op.drop_table("role_projects")
