"""
M6.2 Alembic cloud env.py -- PostgreSQL (Supabase)

Uses SUPABASE_DB_URL env var for connection.
All tables here are L3 business state only (never L1/L2).
"""
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

config = context.config
fileConfig(config.config_file_name)

target_metadata = None


def _resolve_url() -> str:
    url = os.environ.get("SUPABASE_DB_URL", "")
    if not url:
        raise RuntimeError(
            "alembic_cloud requires SUPABASE_DB_URL env var. "
            "Set it in .env or export SUPABASE_DB_URL=postgresql://..."
        )
    return url


def run_migrations_offline() -> None:
    url = _resolve_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = _resolve_url()
    connectable = engine_from_config(
        {"sqlalchemy.url": url},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
