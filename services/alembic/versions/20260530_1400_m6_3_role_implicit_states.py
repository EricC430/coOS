"""M6.3 role_implicit_states -- local SQLite only

Revision ID: 20260530_1400
Revises: 20260530_1300
Create Date: 2026-05-30 14:00:00.000000

Creates role_implicit_states in local SQLite.

Architecture decision (SPEC §9): implicit states are L2 private, short-lived,
and device-local -- no cross-device sync needed.

RISK-06 mitigation: (user_id, role_id) composite index enforces role isolation;
querying a single user_id would return all roles' states (forbidden per anti-pattern).
Research: [R03 §6] role switch must fully reset Persona state.
"""
from collections.abc import Sequence

from alembic import op

revision: str = "20260530_1400"
down_revision: str | None = "20260530_1300"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS role_implicit_states (
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
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_ris_user_role "
        "ON role_implicit_states(user_id, role_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_ris_inferred "
        "ON role_implicit_states(inferred_at)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS role_implicit_states")
