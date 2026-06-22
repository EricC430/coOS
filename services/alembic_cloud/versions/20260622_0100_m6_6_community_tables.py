"""M6.6 community tables (L3 cloud PostgreSQL)

Revision ID: cloud_20260622_0100
Revises: 20260603_2000_m4_3_v1_2_goals_promises
Create Date: 2026-06-22 01:00:00.000000

Creates 6 community tables:
- m6_6_communities        社群實體 (member_cap CHECK 2~8)
- m6_6_community_members  成員關係 (admin/member)
- m6_6_social_posts       貼文 (visibility defaults private, RISK-12)
- m6_6_validations        同儕驗證 (unique per user per post)
- m6_6_stakes             XP 質押 (held/won/forfeited)
- m6_6_challenges         週期挑戰 (is_draft=true default, RISK-18)

Pre-seeds 5 default communities matching the wireframe.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "cloud_20260622_0100"
down_revision: str = "20260603_2000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# System user UUID for pre-seeded communities
SYSTEM_USER_ID = "00000000-0000-0000-0000-000000000000"


def upgrade() -> None:
    # --- m6_6_communities ---
    op.create_table(
        "m6_6_communities",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("type", sa.String(20), nullable=False, server_default="'user_created'"),
        sa.Column("theme", sa.String(50), nullable=True),
        sa.Column("member_cap", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("goal", sa.Text(), nullable=True),
        sa.Column("vision", sa.Text(), nullable=True),
        sa.Column("codex", sa.Text(), nullable=True),
        sa.Column("rules", sa.Text(), nullable=True),
        sa.Column("quotes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="TRUE"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("member_cap >= 2 AND member_cap <= 8", name="chk_member_cap_range"),
    )

    # --- m6_6_community_members ---
    op.create_table(
        "m6_6_community_members",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("community_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.String(10), nullable=False, server_default="'member'"),
        sa.Column("joined_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="TRUE"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["community_id"], ["m6_6_communities.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint("community_id", "user_id", name="uq_community_member"),
    )
    op.create_index("idx_m6_6_cm_user", "m6_6_community_members", ["user_id"])

    # --- m6_6_social_posts ---
    op.create_table(
        "m6_6_social_posts",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("community_id", sa.UUID(), nullable=False),
        sa.Column("author_id", sa.UUID(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False, server_default="'achievement'"),
        sa.Column("visibility", sa.String(10), nullable=False, server_default="'private'"),
        sa.Column("is_draft", sa.Boolean(), nullable=False, server_default="TRUE"),
        sa.Column("likes_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("published_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["community_id"], ["m6_6_communities.id"]),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"]),
    )
    op.create_index("idx_m6_6_sp_community", "m6_6_social_posts", ["community_id"])
    op.create_index("idx_m6_6_sp_author", "m6_6_social_posts", ["author_id"])

    # --- m6_6_validations ---
    op.create_table(
        "m6_6_validations",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("post_id", sa.UUID(), nullable=False),
        sa.Column("validator_id", sa.UUID(), nullable=False),
        sa.Column("evidence_url", sa.String(512), nullable=True),
        sa.Column("validated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["post_id"], ["m6_6_social_posts.id"]),
        sa.ForeignKeyConstraint(["validator_id"], ["users.id"]),
        sa.UniqueConstraint("post_id", "validator_id", name="uq_validation_per_user"),
    )

    # --- m6_6_stakes ---
    op.create_table(
        "m6_6_stakes",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("community_id", sa.UUID(), nullable=False),
        sa.Column("task_id", sa.UUID(), nullable=True),
        sa.Column("xp_amount", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(10), nullable=False, server_default="'held'"),
        sa.Column("deadline", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("settled_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["community_id"], ["m6_6_communities.id"]),
        sa.CheckConstraint("xp_amount > 0", name="chk_stake_positive"),
    )
    op.create_index("idx_m6_6_stakes_user", "m6_6_stakes", ["user_id"])

    # --- m6_6_challenges ---
    op.create_table(
        "m6_6_challenges",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("community_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("period", sa.String(10), nullable=False, server_default="'weekly'"),
        sa.Column("source", sa.String(20), nullable=False, server_default="'admin'"),
        sa.Column("is_draft", sa.Boolean(), nullable=False, server_default="TRUE"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="TRUE"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["community_id"], ["m6_6_communities.id"]),
    )
    op.create_index("idx_m6_6_challenges_community", "m6_6_challenges", ["community_id"])

    # --- Pre-seed 5 default communities (matching wireframe) ---
    op.execute(f"""
        INSERT INTO m6_6_communities (id, name, type, theme, member_cap, goal, vision, created_by)
        VALUES
            (gen_random_uuid(), 'Interview Preparer', 'system_random', 'career',    5, '面試準備互助', '一起拿到理想 Offer', '{SYSTEM_USER_ID}'),
            (gen_random_uuid(), 'Total Strangers',    'system_random', 'social',    8, '與陌生人建立連結', '踏出舒適圈', '{SYSTEM_USER_ID}'),
            (gen_random_uuid(), 'Friend Group',       'system_random', 'friends',   5, '朋友互相督促', '一起變更好', '{SYSTEM_USER_ID}'),
            (gen_random_uuid(), 'Cooking Lovers',     'system_random', 'cooking',   5, '一起學做菜', '每週嘗試新食譜', '{SYSTEM_USER_ID}'),
            (gen_random_uuid(), 'Study Group',        'system_random', 'study',     5, '一起讀書、一起進步', '期末考全員通過', '{SYSTEM_USER_ID}')
    """)


def downgrade() -> None:
    op.drop_table("m6_6_challenges")
    op.drop_table("m6_6_stakes")
    op.drop_table("m6_6_validations")
    op.drop_table("m6_6_social_posts")
    op.drop_table("m6_6_community_members")
    op.drop_table("m6_6_communities")
