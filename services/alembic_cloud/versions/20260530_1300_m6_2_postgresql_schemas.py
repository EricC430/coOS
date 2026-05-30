"""M6.2 cloud PostgreSQL schemas (L3 business state only)

Revision ID: cloud_20260530_1300
Revises:
Create Date: 2026-05-30 13:00:00.000000

Creates all L3 cloud-only tables:
- roles          (user-defined role contexts)
- users          (account + global XP state)
- ai_experts     (Persona definitions, BDI-aligned per R03 §1)
- xp_ledger      (XP transaction log, RISK-12 mitigation: no L1 content)
- badge_definitions + user_badges

Privacy boundary: NO L1 tables (raw_tracking_logs, chat_transcripts,
edge_event_buffer) may ever appear here (CLAUDE.md §隱私三層原則).

RISK-12 mitigation: xp_ledger.reason stores only business descriptions,
never raw behavioural text.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "cloud_20260530_1300"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    # roles must exist before users (active_role_id FK) and ai_experts
    op.create_table(
        "roles",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("slug", sa.String(30), nullable=False),
        sa.Column("display_name", sa.String(50), nullable=False),
        sa.Column("color_hex", sa.CHAR(7), nullable=True),
        sa.Column("icon_name", sa.String(30), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="TRUE"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_roles_user", "roles", ["user_id"])
    op.create_unique_constraint("uq_roles_user_slug", "roles", ["user_id", "slug"])

    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("display_name", sa.String(50), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("current_xp", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("streak_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active_role_id", sa.UUID(), nullable=True),
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
        sa.UniqueConstraint("email"),
    )

    # Add FK from roles.user_id -> users.id after users table exists
    op.create_foreign_key("fk_roles_user", "roles", "users", ["user_id"], ["id"])

    op.create_table(
        "ai_experts",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("role_id", sa.UUID(), nullable=False),
        # [R03 §1.1] BDI personality prompt, max 4KB
        sa.Column("personality_prompt", sa.String(4096), nullable=False),
        sa.Column("backstory", sa.String(2048), nullable=True),
        sa.Column("tone_default", sa.String(20), nullable=False, server_default="'authoritative'"),
        sa.Column("trust_level", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("avatar_url", sa.String(512), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="TRUE"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"]),
    )
    op.create_unique_constraint(
        "uq_ae_role_name", "ai_experts", ["role_id", "name"]
    )

    op.create_table(
        "xp_ledger",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("role_id", sa.UUID(), nullable=True),
        # CHECK amount != 0 enforced via sa.CheckConstraint
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("xp_type", sa.String(20), nullable=False),
        sa.Column("reason", sa.String(255), nullable=False),
        sa.Column("source_module", sa.String(10), nullable=False),
        sa.Column("reflection_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.CheckConstraint("amount != 0", name="chk_xp_nonzero"),
    )
    op.create_index("idx_xl_user", "xp_ledger", ["user_id"])
    op.create_index("idx_xl_created", "xp_ledger", ["created_at"])
    op.create_index("idx_xl_type", "xp_ledger", ["xp_type"])

    op.create_table(
        "badge_definitions",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("slug", sa.String(50), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("icon_url", sa.String(512), nullable=True),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("is_hidden", sa.Boolean(), nullable=False, server_default="FALSE"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    op.create_table(
        "user_badges",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("badge_id", sa.UUID(), nullable=False),
        sa.Column(
            "unlocked_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["badge_id"], ["badge_definitions.id"]),
        sa.UniqueConstraint("user_id", "badge_id", name="uq_user_badge"),
    )


def downgrade() -> None:
    op.drop_table("user_badges")
    op.drop_table("badge_definitions")
    op.drop_table("xp_ledger")
    op.drop_table("ai_experts")
    op.drop_constraint("fk_roles_user", "roles", type_="foreignkey")
    op.drop_table("users")
    op.drop_table("roles")
