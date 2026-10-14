"""SQLAlchemy database primitives for the optional PostgreSQL integration."""

from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config.settings import settings


class Base(DeclarativeBase):
    """Base class for additive LegalTech tables."""


@lru_cache(maxsize=1)
def get_engine():
    """Create the configured database engine only when persistence is enabled."""
    if not settings.ENABLE_LEGALTECH_PERSISTENCE or not settings.DATABASE_URL:
        raise RuntimeError(
            "LegalTech persistence is disabled or DATABASE_URL is not configured."
        )
    return create_engine(settings.DATABASE_URL, pool_pre_ping=True, future=True)


@lru_cache(maxsize=1)
def get_session_factory():
    """Return a session factory for application services."""
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def get_db_session():
    """Yield a database session for feature-flagged LegalTech routes."""
    if settings.DATABASE_BACKEND.lower() == "mongo":
        yield None
        return
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()
