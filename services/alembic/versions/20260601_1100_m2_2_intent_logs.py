"""M2.2 intent_logs -- persisted IntentVector output from Gemma edge inference

Revision ID: 20260601_1100
Revises: 20260601_1000
Create Date: 2026-06-01

SPEC: docs/modules/M2_2_gemma_edge_inference_SPEC.md v1.1 §7.2
Privacy: L2 -- intent vectors, no raw plaintext. source_log_id FK to raw_tracking_logs.
RISK-05 mitigation: source_log_id NOT NULL + FK enforced.
"""

from __future__ import annotations

from alembic import op

revision: str = "20260601_1100"
down_revision: str | None = "20260601_1000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS intent_logs (
            id                     TEXT PRIMARY KEY,
            source_log_id          TEXT NOT NULL,
            role_id                TEXT NOT NULL,
            intent_label           TEXT NOT NULL,
            context_summary        TEXT NOT NULL,
            semantic_embedding     BLOB,
            frustration_level      REAL NOT NULL DEFAULT 0.0
                                   CHECK(frustration_level BETWEEN 0.0 AND 1.0),
            valence                REAL DEFAULT 0.0
                                   CHECK(valence BETWEEN -1.0 AND 1.0),
            arousal                REAL DEFAULT 0.0
                                   CHECK(arousal BETWEEN 0.0 AND 1.0),
            stripped_entities_count INTEGER NOT NULL DEFAULT 0,
            inference_mode         TEXT NOT NULL DEFAULT 'gemma_edge',
            created_at             TEXT NOT NULL
                                   DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
            FOREIGN KEY (source_log_id) REFERENCES raw_tracking_logs(id)
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_il_source ON intent_logs(source_log_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_il_role ON intent_logs(role_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_il_mode ON intent_logs(inference_mode)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_il_source")
    op.execute("DROP INDEX IF EXISTS idx_il_role")
    op.execute("DROP INDEX IF EXISTS idx_il_mode")
    op.execute("DROP TABLE IF EXISTS intent_logs")
