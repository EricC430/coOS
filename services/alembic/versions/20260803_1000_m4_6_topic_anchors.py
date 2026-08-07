"""M4.6 -- topic_anchors and topic_sessions tables

Revision ID: 20260803_1000
Revises: 20260603_1000
Create Date: 2026-08-03 10:00:00.000000

Changes:
  - topic_anchors: intent-anchored descriptive topic labels with dedup support
  - topic_sessions: per-session context accumulation for each topic

Upgrade from role_projects (short noun-phrase tags) to topic_anchors
(descriptive intent-anchored labels with motivation, embedding, lifecycle).

SPEC: docs/modules/M4_6_observer_agent_SPEC.md
Research: [R10: Agent Workflow] [R02: Dynamic State Decode]
Risk: RISK-06 (role isolation via role_id FK), RISK-12 (PII filtered upstream)
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260803_1000"
down_revision: str | None = "20260603_1000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "topic_anchors",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("role_id", sa.Text(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("intent", sa.Text(), nullable=True),
        sa.Column("motivation", sa.Text(), nullable=True),
        sa.Column("parent_id", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), server_default="active"),
        sa.Column("mention_count", sa.Integer(), server_default="1"),
        sa.Column("first_seen", sa.Text(), nullable=False),
        sa.Column("last_seen", sa.Text(), nullable=False),
        sa.Column("embedding", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
    )
    op.create_index("idx_ta_role_status", "topic_anchors", ["role_id", "status"])
    op.create_index("idx_ta_last_seen", "topic_anchors", ["last_seen"])

    op.create_table(
        "topic_sessions",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("topic_id", sa.Text(), nullable=False),
        sa.Column("thread_id", sa.Text(), nullable=False),
        sa.Column("context_summary", sa.Text(), nullable=True),
        sa.Column("progress_note", sa.Text(), nullable=True),
        sa.Column("recorded_at", sa.Text(), nullable=False),
    )
    op.create_index("idx_ts_topic", "topic_sessions", ["topic_id"])
    op.create_index("idx_ts_thread", "topic_sessions", ["thread_id"])


def downgrade() -> None:
    op.drop_table("topic_sessions")
    op.drop_table("topic_anchors")
