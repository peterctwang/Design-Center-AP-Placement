"""SQLite + SQLAlchemy 2.0 setup."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from .config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(
    settings.database_url,
    echo=settings.debug,
    connect_args={"check_same_thread": False},   # SQLite multi-threaded
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    """FastAPI dependency: yields a DB session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables on startup."""
    from . import models  # noqa: F401 — register models
    Base.metadata.create_all(bind=engine)
