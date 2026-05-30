"""M6.2 v1.1 Refinement -- XP ledger FK expansion + lifetime_xp + avatar_url

Revision ID: cloud_20260531_1100
Revises: cloud_20260531_1000
Create Date: 2026-05-31 11:00:00.000000

Changes from v1.0:
  - users: add lifetime_xp (唯增不減, 防等級倒退) [RISK-14]
  - roles: add avatar_url
  - xp_ledger: add role_id/expert_id/project/segment_id/task_id for statistics
  - role_projects: add inferred_by_ai/alias_keywords (AI auto-discovery)
  - role_settings: add weekly_target_minutes (focus goal management)
  - role_implicit_states: add valence/arousal/raw_triggers (emotion model)

Risk mitigation:
  RISK-14: lifetime_xp is incremented only on XP earn, never on spend --
           enforced in M6.5 gatekeeper.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "cloud_20260531_1100"
down_revision: str | None = "cloud_20260531_1000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- users: add lifetime_xp [RISK-14] ---
    op.add_column("users", sa.Column(
        "lifetime_xp", sa.Integer(), nullable=False, server_default="0",
    ))

    # --- roles: add avatar_url for UI rendering ---
    op.add_column("roles", sa.Column(
        "avatar_url", sa.VARCHAR(512), nullable=True,
    ))

    # --- xp_ledger: add FK columns for statistics dimensions ---
    op.add_column("xp_ledger", sa.Column("role_id", sa.UUID(), nullable=True))
    op.add_column("xp_ledger", sa.Column("expert_id", sa.UUID(), nullable=True))
    op.add_column("xp_ledger", sa.Column("project", sa.Text(), nullable=True))
    op.add_column("xp_ledger", sa.Column("segment_id", sa.UUID(), nullable=True))
    # task_id: no FK constraint -- task module not yet built
    op.add_column("xp_ledger", sa.Column("task_id", sa.UUID(), nullable=True))

    # FK constraints for xp_ledger new cols
    op.create_foreign_key(
        "fk_xl_role", "xp_ledger", "roles", ["role_id"], ["id"],
    )
    op.create_foreign_key(
        "fk_xl_expert", "xp_ledger", "ai_experts", ["expert_id"], ["id"],
    )
    op.create_foreign_key(
        "fk_xl_segment", "xp_ledger",
        "daily_reflection_segments", ["segment_id"], ["id"],
        ondelete="SET NULL",
    )

    # Indexes for ledger statistics queries
    op.create_index("idx_xl_role", "xp_ledger", ["role_id"])
    op.create_index("idx_xl_expert", "xp_ledger", ["expert_id"])
    op.create_index("idx_xl_project", "xp_ledger", ["project"])
    op.create_index(
        "idx_xl_task", "xp_ledger", ["task_id"],
        postgresql_where=sa.text("task_id IS NOT NULL"),
    )

    # --- role_projects: AI auto-discovery fields ---
    op.add_column("role_projects", sa.Column(
        "inferred_by_ai", sa.Boolean(), nullable=False, server_default="FALSE",
    ))
    op.add_column("role_projects", sa.Column(
        "alias_keywords", sa.Text(), nullable=True,  # JSON array of keyword strings
    ))

    # --- role_settings: focus goal management ---
    op.add_column("role_settings", sa.Column(
        "weekly_target_minutes", sa.Integer(), nullable=False, server_default="0",
    ))

    # --- role_implicit_states: Valence-Arousal emotion model ---
    # Valence: -1.0 (negative) to 1.0 (positive)
    # Arousal: -1.0 (calm) to 1.0 (excited)
    op.add_column("role_implicit_states", sa.Column(
        "valence", sa.Float(), nullable=True,
    ))
    op.add_column("role_implicit_states", sa.Column(
        "arousal", sa.Float(), nullable=True,
    ))
    op.add_column("role_implicit_states", sa.Column(
        "raw_triggers", sa.Text(), nullable=True,  # JSON array of telemetry event types
    ))
    op.create_check_constraint(
        "ck_ris_valence", "role_implicit_states",
        "valence IS NULL OR (valence >= -1.0 AND valence <= 1.0)",
    )
    op.create_check_constraint(
        "ck_ris_arousal", "role_implicit_states",
        "arousal IS NULL OR (arousal >= -1.0 AND arousal <= 1.0)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_ris_valence", "role_implicit_states", type_="check")
    op.drop_constraint("ck_ris_arousal", "role_implicit_states", type_="check")
    op.drop_column("role_implicit_states", "raw_triggers")
    op.drop_column("role_implicit_states", "arousal")
    op.drop_column("role_implicit_states", "valence")

    op.drop_column("role_settings", "weekly_target_minutes")
    op.drop_column("role_projects", "alias_keywords")
    op.drop_column("role_projects", "inferred_by_ai")

    op.drop_index("idx_xl_task", "xp_ledger")
    op.drop_index("idx_xl_project", "xp_ledger")
    op.drop_index("idx_xl_expert", "xp_ledger")
    op.drop_index("idx_xl_role", "xp_ledger")
    op.drop_constraint("fk_xl_segment", "xp_ledger", type_="foreignkey")
    op.drop_constraint("fk_xl_expert", "xp_ledger", type_="foreignkey")
    op.drop_constraint("fk_xl_role", "xp_ledger", type_="foreignkey")
    op.drop_column("xp_ledger", "task_id")
    op.drop_column("xp_ledger", "segment_id")
    op.drop_column("xp_ledger", "project")
    op.drop_column("xp_ledger", "expert_id")
    op.drop_column("xp_ledger", "role_id")

    op.drop_column("roles", "avatar_url")
    op.drop_column("users", "lifetime_xp")
