"""Database session dependency for FastAPI."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from shackles.db.engine import SessionLocal


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session, closing it when done."""
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
