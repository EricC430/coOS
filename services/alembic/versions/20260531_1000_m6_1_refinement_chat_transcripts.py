"""M6.1 v1.1 Refinement -- chat_transcripts expansion for project linkage & audio

Revision ID: 20260531_1000
Revises: 20260530_1400
Create Date: 2026-05-31 10:00:00.000000

Changes:
  - chat_transcripts: add project, audio_path, paralinguistic_metadata
    project: links transcript to a role project for GraphRAG context injection
    audio_path: local raw audio file path (L1, NEVER cloud-synced)
    paralinguistic_metadata: JSON string of voice features (tempo, pitch variance,
      stress index) for M4.2 tone state machine analysis

Privacy:
  All three columns remain L1 (local SQLite only).
  audio_path MUST NOT be synced to cloud.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260531_1000"
down_revision: str | None = "20260530_1400"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # project: link to role_projects.name for context filtering and GraphRAG
    op.add_column("chat_transcripts", sa.Column("project", sa.Text(), nullable=True))
    # audio_path: local filesystem path to raw voice recording (L1 only)
    op.add_column("chat_transcripts", sa.Column("audio_path", sa.Text(), nullable=True))
    # paralinguistic_metadata: JSON {tempo, pitch_variance, stress_index, ...}
    op.add_column("chat_transcripts", sa.Column("paralinguistic_metadata", sa.Text(), nullable=True))

    op.create_index("idx_ct_project", "chat_transcripts", ["project"])


def downgrade() -> None:
    op.drop_index("idx_ct_project", "chat_transcripts")
    op.drop_column("chat_transcripts", "paralinguistic_metadata")
    op.drop_column("chat_transcripts", "audio_path")
    op.drop_column("chat_transcripts", "project")
