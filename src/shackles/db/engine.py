"""Async SQLAlchemy engine and session factory."""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from shackles.config import settings


def create_engine() -> AsyncEngine:
    """Create a configured async engine."""
    return create_async_engine(
        settings.database_url,
        echo=settings.database_echo,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600,
    )


engine: AsyncEngine = create_engine()


SessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)
