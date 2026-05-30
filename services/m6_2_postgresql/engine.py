"""
M6.2 -- SQLAlchemy engine factory for Supabase PostgreSQL

SPEC: docs/modules/M6_2_postgresql_schemas_SPEC.md §7.6
Returns None gracefully when SUPABASE_DB_URL is not set (local dev mode).
"""
import os
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

_engine = None
_SessionLocal = None


def _supabase_url() -> str | None:
    return os.environ.get("SUPABASE_DB_URL") or None


def get_cloud_engine():
    """Return SQLAlchemy engine for Supabase, or None if URL not configured."""
    global _engine
    if _engine is None:
        url = _supabase_url()
        if not url:
            return None
        _engine = create_engine(url, pool_pre_ping=True)
    return _engine


def get_cloud_session() -> Session | None:
    """Return a SQLAlchemy Session for Supabase, or None if not configured."""
    global _SessionLocal
    engine = get_cloud_engine()
    if engine is None:
        return None
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return _SessionLocal()


@contextmanager
def cloud_session_ctx():
    """Context manager yielding a cloud session, or skipping if unavailable."""
    session = get_cloud_session()
    if session is None:
        yield None
        return
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def is_cloud_available() -> bool:
    """Check whether Supabase connection is configured and reachable."""
    engine = get_cloud_engine()
    if engine is None:
        return False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
