"""
M0.3 Alembic env.py — 雙軌 DB 支援

實作 SPEC: docs/modules/M0_3_env_alembic_SPEC.md §7.3
根據啟動的 ini 檔（alembic_local.ini / alembic_cloud.ini）動態選擇 DB URL。
"""
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# services/ 目錄加入 sys.path，讓 config 可被匯入
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

config = context.config
fileConfig(config.config_file_name)

# 匯入所有 model metadata（Phase 1 起逐步加入）
# from services.m6_1_sqlite_schemas.models import Base
# target_metadata = Base.metadata
target_metadata = None


def _resolve_url() -> str:
    """Resolve DB URL from ini + environment variables.

    alembic_local.ini  -> uses LOCAL_DB_PATH env var (default: ../data/coos.db)
    alembic_cloud.ini  -> uses SUPABASE_DB_URL env var (required)
    """
    raw = config.get_main_option("sqlalchemy.url", "")

    if "PLACEHOLDER" in raw:
        # local SQLite: replace placeholder with real path from env
        db_path = os.environ.get("LOCAL_DB_PATH", "../data/coos.db")
        return f"sqlite:///{db_path}"

    if "%(SUPABASE_DB_URL)s" in raw:
        url = os.environ.get("SUPABASE_DB_URL", "")
        if not url:
            raise RuntimeError(
                "alembic_cloud.ini requires SUPABASE_DB_URL env var. "
                "Set it in .env or export SUPABASE_DB_URL=..."
            )
        return url

    return raw


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
