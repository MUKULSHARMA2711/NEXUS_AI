from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from nexus.core.config import get_settings


@lru_cache
def get_engine() -> Engine:
    """Create and cache the SQLAlchemy engine using application settings."""
    settings = get_settings()
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
    )


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    """Create and cache the SQLAlchemy sessionmaker bound to the lazy engine."""
    return sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=get_engine(),
    )


def SessionLocal() -> Session:
    """Create a new database session from the lazy session factory."""
    factory = get_session_factory()
    return factory()


def get_db() -> Generator[Session, None, None]:
    """Provide a transactional database session scope for FastAPI dependencies."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
