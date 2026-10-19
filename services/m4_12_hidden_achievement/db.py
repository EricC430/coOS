from pathlib import Path
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from config import get_settings
from .models import Base

settings = get_settings()

db_path = settings.local_db_path
if isinstance(db_path, str):
    db_path = Path(db_path)

db_path.parent.mkdir(parents=True, exist_ok=True)
sqlite_url = f"sqlite:///{db_path}"

engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Auto-create tables for M4.12
Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
