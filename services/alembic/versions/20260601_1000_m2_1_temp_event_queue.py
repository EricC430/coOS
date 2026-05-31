"""M2.1 temp_event_queue -- offline buffer for debounced event batches

Revision ID: 20260601_1000
Revises: 20260531_1200
Create Date: 2026-06-01

SPEC: docs/modules/M2_1_event_debouncing_SPEC.md v1.1 RISK-M2.1-A
Privacy: L1 -- local-only, stores EventBatch JSON pending delivery to M2.2.
"""

from __future__ import annotations

from alembic import op

revision: str = "20260601_1000"
down_revision: str | None = "20260531_1200"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS temp_event_queue (
            id           TEXT PRIMARY KEY,
            batch_id     TEXT NOT NULL,
            events_json  TEXT NOT NULL,
            role_id      TEXT NOT NULL,
            created_at   TEXT NOT NULL
                         DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
            retry_count  INTEGER NOT NULL DEFAULT 0,
            next_retry_at TEXT
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_teq_next_retry ON temp_event_queue(next_retry_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_teq_batch ON temp_event_queue(batch_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_teq_next_retry")
    op.execute("DROP INDEX IF EXISTS idx_teq_batch")
    op.execute("DROP TABLE IF EXISTS temp_event_queue")
