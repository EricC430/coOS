import sys
from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SERVICES_DIR = PROJECT_ROOT / "services"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SERVICES_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICES_DIR))

from sqlalchemy.pool import StaticPool
from m4_11_zpd_pipeline.models import Base
from m4_11_zpd_pipeline.service import ZPDPipelineService

@pytest.fixture
def sqlite_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session(sqlite_engine):
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sqlite_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def zpd_service(db_session):
    return ZPDPipelineService(db_session=db_session)

@pytest.fixture(autouse=True)
def reset_global_rate_limiter():
    from m4_11_zpd_pipeline.service import _global_rate_limiter
    _global_rate_limiter.reset()
    yield
    _global_rate_limiter.reset()
