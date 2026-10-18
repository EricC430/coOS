"""M6.1 -- raw_content_stores table (L1 plaintext side table)

Revision ID: 20261018_1000
Revises: 20260803_1100
Create Date: 2026-10-18 10:00:00.000000

Changes:
  - raw_content_stores: opt-in captured window/document plaintext,
    kept apart from raw_tracking_logs.payload so the payload only carries
    a content_raw_ref (side-channel separation)
    L1 privacy tier -- stays local, never uploaded to cloud

SPEC: docs/modules/M6_1_sqlite_schemas_SPEC.md ss7.5
Consumer: docs/modules/M2_2_gemma_edge_inference_SPEC.md (content_raw_ref lookup)
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261018_1000"
down_revision: str | None = "20260803_1100"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "raw_content_stores",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("content_raw", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False,
                  server_default=sa.text("strftime('%Y-%m-%dT%H:%M:%fZ', 'now')")),
    )


def downgrade() -> None:
    op.drop_table("raw_content_stores")
