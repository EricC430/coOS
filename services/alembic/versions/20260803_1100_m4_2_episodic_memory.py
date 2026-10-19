"""M4.2 -- persona_episodic_memories table

Revision ID: 20260803_1100
Revises: 20260803_1000
Create Date: 2026-08-03 11:00:00.000000

Changes:
  - persona_episodic_memories: per-persona episodic memory store
    (role_id, persona_id) double-key isolation (RISK-06)
    L1 privacy tier -- stays local, never uploaded to cloud

SPEC: docs/modules/M4_2_persona_state_machine_SPEC.md
Research: [R11: Park et al. ss3.2] Retrieval scoring
          [R15: MemGPT] Tiered memory, token budget <= 350
Risk: RISK-06 (role_id isolation), RISK-12 (PII masking before write)
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260803_1100"
down_revision: str | None = "20260803_1000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "persona_episodic_memories",
        sa.Column("id", sa.Text(), primary_key=True,
                  server_default=sa.text("lower(hex(randomblob(16)))")),
        sa.Column("role_id", sa.Text(), nullable=False),
        sa.Column("persona_id", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False,
                  server_default="'observation'"),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("importance", sa.Float(), nullable=False,
                  server_default="0.5"),
        sa.Column("created_at", sa.Text(), nullable=False,
                  server_default=sa.text("strftime('%Y-%m-%dT%H:%M:%SZ', 'now')")),
        sa.Column("last_accessed_at", sa.Text(), nullable=False,
                  server_default=sa.text("strftime('%Y-%m-%dT%H:%M:%SZ', 'now')")),
    )
    op.create_index(
        "ix_persona_episodic_memories_lookup",
        "persona_episodic_memories",
        ["role_id", "persona_id", "kind"],
    )


def downgrade() -> None:
    op.drop_index("ix_persona_episodic_memories_lookup")
    op.drop_table("persona_episodic_memories")
