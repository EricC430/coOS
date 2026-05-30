"""M6.3 role_implicit_states v1.1 -- Valence-Arousal emotion model (local SQLite)

Revision ID: 20260531_1200
Revises: 20260531_1000
Create Date: 2026-05-31 12:00:00.000000

Adds Valence-Arousal circumplex model columns to local role_implicit_states.
[Phase 2.5 prerequisite for M2.2 edge inference]

Architecture:
  role_implicit_states is LOCAL-ONLY (L2 privacy boundary -- never cloud-synced).
  See CLAUDE.md §privacy and M6.3 SPEC §9.

Research:
  [R03 §6] Valence-Arousal model for affect-aware Persona transitions.
  Valence:  -1.0 (negative/sad) -> +1.0 (positive/happy)
  Arousal:  -1.0 (calm/drowsy)  -> +1.0 (excited/stressed)
"""
from collections.abc import Sequence

from alembic import op

revision: str = "20260531_1200"
down_revision: str | None = "20260531_1000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE role_implicit_states ADD COLUMN valence REAL")
    op.execute("ALTER TABLE role_implicit_states ADD COLUMN arousal REAL")
    op.execute("ALTER TABLE role_implicit_states ADD COLUMN raw_triggers TEXT")


def downgrade() -> None:
    # SQLite does not support DROP COLUMN before 3.35; use recreate pattern
    op.execute("""
        CREATE TABLE role_implicit_states_backup AS
        SELECT id, user_id, role_id, label, confidence,
               inferred_at, expires_at, source_module
        FROM role_implicit_states
    """)
    op.execute("DROP TABLE role_implicit_states")
    op.execute("""
        CREATE TABLE role_implicit_states (
            id              TEXT PRIMARY KEY,
            user_id         TEXT NOT NULL,
            role_id         TEXT NOT NULL,
            label           TEXT NOT NULL,
            confidence      REAL NOT NULL
                            CHECK (confidence >= 0 AND confidence <= 1),
            inferred_at     TEXT NOT NULL
                            DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
            expires_at      TEXT,
            source_module   TEXT NOT NULL DEFAULT 'M4.8'
        )
    """)
    op.execute("INSERT INTO role_implicit_states SELECT * FROM role_implicit_states_backup")
    op.execute("DROP TABLE role_implicit_states_backup")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_ris_user_role "
        "ON role_implicit_states(user_id, role_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_ris_inferred "
        "ON role_implicit_states(inferred_at)"
    )
