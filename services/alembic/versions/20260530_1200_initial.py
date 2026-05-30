"""initial

Revision ID: 20260530_1200
Revises:
Create Date: 2026-05-30 12:00:00.000000

Phase 0 空殼 migration — 建立 alembic_version 表即可。
M6.1 (SQLite schemas) 將在 Phase 1 加入真實資料表。
"""
from collections.abc import Sequence

revision: str = "20260530_1200"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
