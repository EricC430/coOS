"""M4.1 -- role_router_rules and routing_samples tables

Revision ID: 20260603_1000
Revises: 20260601_1100
Create Date: 2026-06-03 10:00:00.000000

Changes:
  - role_router_rules: per-role regex routing rules with confidence scoring
    and candidate/active/rejected lifecycle (RISK-06: strict role_id isolation)
  - routing_samples: SHA-256 hashed routing telemetry, no raw user text (RISK-13a)

SPEC: docs/modules/M4_1_agent_router_SPEC.md §7.7
Research: [R09: MAS §6.1] [R10: Agent Workflow State Machine]
Risk: RISK-06 (role isolation), RISK-13a (no raw msg stored)
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260603_1000"
down_revision: str | None = "20260601_1100"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # [RISK-06] role_id is the isolation key -- no cross-role queries allowed
    op.create_table(
        "role_router_rules",
        sa.Column("id", sa.Text(), primary_key=True,
                  server_default=sa.text("lower(hex(randomblob(16)))")),
        sa.Column("role_id", sa.Text(), nullable=False),
        sa.Column("persona_id", sa.Text(), nullable=False),
        sa.Column("pattern", sa.Text(), nullable=False),
        sa.Column("target_domain", sa.Text(), nullable=False, server_default="''"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.50"),
        sa.Column("source", sa.Text(), nullable=False, server_default="'manual'"),
        sa.Column("status", sa.Text(), nullable=False, server_default="'candidate'"),
        sa.Column("hit_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("correct_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("datetime('now')")),
        sa.Column("last_active", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "idx_router_rules_role_status",
        "role_router_rules",
        ["role_id", "status"],
    )

    # [RISK-13a] Only SHA-256 hash stored, never raw user message
    op.create_table(
        "routing_samples",
        sa.Column("id", sa.Text(), primary_key=True,
                  server_default=sa.text("lower(hex(randomblob(16)))")),
        sa.Column("role_id", sa.Text(), nullable=False),
        sa.Column("user_msg_hash", sa.Text(), nullable=False),
        sa.Column("keyword_tokens", sa.Text(), nullable=True),  # JSON array, PII-stripped
        sa.Column("rule_persona_id", sa.Text(), nullable=True),
        sa.Column("llm_persona_id", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("outcome", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("datetime('now')")),
    )
    op.create_index(
        "idx_routing_samples_role_outcome",
        "routing_samples",
        ["role_id", "outcome", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_routing_samples_role_outcome", "routing_samples")
    op.drop_table("routing_samples")
    op.drop_index("idx_router_rules_role_status", "role_router_rules")
    op.drop_table("role_router_rules")
