"""Generic base repository with common CRUD operations.

Every specific repository inherits from BaseRepository[ModelType] and adds
domain-specific queries on top.
"""

from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shackles.db.base import Base
from shackles.errors import DomainError, NOT_FOUND

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Generic repository providing CRUD primitives.

    Subclasses set `model` to the SQLAlchemy model class:

        class UserRepository(BaseRepository[User]):
            model = User
    """

    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ========================================================
    # Read
    # ========================================================

    async def get(self, id: UUID) -> ModelT | None:
        """Fetch by primary key. Returns None if not found."""
        return await self.session.get(self.model, id)

    async def get_or_raise(
        self,
        id: UUID,
        code: str = NOT_FOUND,
        message: str | None = None,
    ) -> ModelT:
        """Fetch by primary key. Raises DomainError if not found."""
        obj = await self.get(id)
        if obj is None:
            raise DomainError(
                code,
                message or f"{self.model.__name__} not found",
                {"id": str(id)},
            )
        return obj

    async def exists(self, id: UUID) -> bool:
        """Check whether a row with this primary key exists."""
        stmt = select(func.count()).select_from(self.model).where(
            self.model.id == id  # type: ignore[attr-defined]
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() > 0

    async def count(self) -> int:
        """Count all rows in the table."""
        stmt = select(func.count()).select_from(self.model)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def list(
        self,
        *,
        limit: int = 25,
        offset: int = 0,
    ) -> list[ModelT]:
        """List rows with pagination. Ordering is subclass responsibility."""
        stmt = select(self.model).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ========================================================
    # Write
    # ========================================================

    async def create(self, **kwargs: Any) -> ModelT:
        """Create a new row. Flushes to assign DB-generated values."""
        obj = self.model(**kwargs)
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def update(self, id: UUID, **kwargs: Any) -> ModelT | None:
        """Update specific fields. Returns None if the row doesn't exist."""
        obj = await self.get(id)
        if obj is None:
            return None
        for key, value in kwargs.items():
            setattr(obj, key, value)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def delete(self, id: UUID) -> bool:
        """Hard-delete a row. Returns True if deleted, False if not found."""
        obj = await self.get(id)
        if obj is None:
            return False
        await self.session.delete(obj)
        await self.session.flush()
        return True

    # ========================================================
    # Session helpers
    # ========================================================

    async def flush(self) -> None:
        """Flush pending changes. Exposed for services that batch writes."""
        await self.session.flush()

    async def refresh(self, obj: ModelT) -> None:
        """Refresh an object from the DB. Useful after external updates."""
        await self.session.refresh(obj)