"""M6.1 local SQLite schemas

Revision ID: 20260530_1300
Revises: 20260530_1200
Create Date: 2026-05-30 13:00:00.000000

Creates all L1/L2 local-only tables:
- raw_tracking_logs  (L1 plaintext event log, written by M0.4)
- edge_event_buffer  (L2 intent vector staging, written by M2.2)
- chat_transcripts   (L1 plaintext dialogue, written by M4.2)
- user_consents      (L1 local privacy consent)

RISK-05 mitigation: edge_event_buffer.source_log_id FK -> raw_tracking_logs.id
"""
from collections.abc import Sequence

from alembic import op

revision: str = "20260530_1300"
down_revision: str | None = "20260530_1200"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS raw_tracking_logs (
            id              TEXT PRIMARY KEY,
            timestamp       TEXT NOT NULL,
            module          TEXT NOT NULL,
            action          TEXT NOT NULL,
            level           TEXT NOT NULL DEFAULT 'INFO',
            payload         TEXT NOT NULL DEFAULT '{}',
            user_id         TEXT,
            role_id         TEXT,
            correlation_id  TEXT,
            created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_rtl_module      ON raw_tracking_logs(module)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_rtl_timestamp   ON raw_tracking_logs(timestamp)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_rtl_correlation ON raw_tracking_logs(correlation_id)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_rtl_level       ON raw_tracking_logs(level)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS edge_event_buffer (
            id              TEXT PRIMARY KEY,
            source_log_id   TEXT NOT NULL,
            intent_tag      TEXT NOT NULL,
            intent_vector   BLOB,
            confidence      REAL NOT NULL,
            model_version   TEXT NOT NULL,
            processed       INTEGER NOT NULL DEFAULT 0,
            created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
            FOREIGN KEY (source_log_id) REFERENCES raw_tracking_logs(id)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_eeb_processed ON edge_event_buffer(processed)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_eeb_source    ON edge_event_buffer(source_log_id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS chat_transcripts (
            id              TEXT PRIMARY KEY,
            thread_id       TEXT NOT NULL,
            persona_id      TEXT,
            role            TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
            content         TEXT NOT NULL,
            role_id         TEXT,
            token_count     INTEGER,
            created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_ct_thread  ON chat_transcripts(thread_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_ct_role_id ON chat_transcripts(role_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_ct_created ON chat_transcripts(created_at)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS user_consents (
            id              TEXT PRIMARY KEY,
            user_id         TEXT NOT NULL,
            consent_type    TEXT NOT NULL,
            granted         INTEGER NOT NULL,
            granted_at      TEXT NOT NULL,
            revoked_at      TEXT,
            ip_hash         TEXT
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_uc_user ON user_consents(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_uc_type ON user_consents(consent_type)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS user_consents")
    op.execute("DROP TABLE IF EXISTS chat_transcripts")
    op.execute("DROP TABLE IF EXISTS edge_event_buffer")
    op.execute("DROP TABLE IF EXISTS raw_tracking_logs")
