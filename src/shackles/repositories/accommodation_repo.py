"""AccommodationRepository — data access for accommodation requests."""

from uuid import UUID

from sqlalchemy import func, select

from shackles.errors import NOT_FOUND, DomainError
from shackles.models.accommodation import Accommodation
from shackles.models.user import User
from shackles.repositories.base import BaseRepository


class AccommodationRepository(BaseRepository[Accommodation]):
    """Data access for accommodation requests.

    One-to-one with User. A user either has requested accommodation or not.
    """

    model = Accommodation

    # ========================================================
    # Lookups
    # ========================================================

    async def get_by_user_id(self, user_id: UUID) -> Accommodation | None:
        """Fetch a user's accommodation request."""
        stmt = select(Accommodation).where(Accommodation.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_user_id_or_raise(self, user_id: UUID) -> Accommodation:
        """Fetch by user. Raises if not found."""
        acc = await self.get_by_user_id(user_id)
        if acc is None:
            raise DomainError(
                NOT_FOUND,
                "No accommodation request found for this user.",
                {"user_id": str(user_id)},
            )
        return acc

    # ========================================================
    # Existence
    # ========================================================

    async def has_requested(self, user_id: UUID) -> bool:
        """Check whether a user has already requested accommodation."""
        stmt = (
            select(func.count())
            .select_from(Accommodation)
            .where(Accommodation.user_id == user_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() > 0

    # ========================================================
    # Lists
    # ========================================================

    async def list_all(
        self,
        *,
        limit: int = 500,
        offset: int = 0,
    ) -> list[Accommodation]:
        """List all accommodation requests, newest first."""
        stmt = (
            select(Accommodation)
            .order_by(Accommodation.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_user_gender(
        self,
        gender: str,
        *,
        limit: int = 500,
        offset: int = 0,
    ) -> list[Accommodation]:
        """List accommodations filtered by the requesting user's gender.

        Requires a join against User. Used by the admin download endpoint
        that produces separate CSV files for male/female accommodation.
        """
        stmt = (
            select(Accommodation)
            .join(User, Accommodation.user_id == User.id)
            .where(User.gender == gender)
            .order_by(Accommodation.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ========================================================
    # Counts
    # ========================================================

    async def count_all(self) -> int:
        """Total accommodation requests."""
        return await self.count()

    async def count_by_user_gender(self, gender: str) -> int:
        """Count accommodations filtered by user gender."""
        stmt = (
            select(func.count())
            .select_from(Accommodation)
            .join(User, Accommodation.user_id == User.id)
            .where(User.gender == gender)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()