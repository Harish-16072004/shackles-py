"""OnSpotProfileRepository — data access for on-spot registration metadata."""

from uuid import UUID

from sqlalchemy import func, select

from shackles.errors import NOT_FOUND, DomainError
from shackles.models.on_spot_profile import OnSpotProfile
from shackles.repositories.base import BaseRepository


class OnSpotProfileRepository(BaseRepository[OnSpotProfile]):
    """Data access for on-spot profiles.

    Each User can have at most one OnSpotProfile (one-to-one). Populated
    when a user registers via the on-spot kiosk flow.
    """

    model = OnSpotProfile

    # ========================================================
    # Lookups
    # ========================================================

    async def get_by_user_id(self, user_id: UUID) -> OnSpotProfile | None:
        """Fetch the on-spot profile for a user."""
        stmt = select(OnSpotProfile).where(OnSpotProfile.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_user_id_or_raise(self, user_id: UUID) -> OnSpotProfile:
        """Fetch by user ID. Raises if not found."""
        profile = await self.get_by_user_id(user_id)
        if profile is None:
            raise DomainError(
                NOT_FOUND,
                "On-spot profile not found for this user.",
                {"user_id": str(user_id)},
            )
        return profile

    # ========================================================
    # Existence
    # ========================================================

    async def has_profile(self, user_id: UUID) -> bool:
        """Check whether a user has an on-spot profile.

        Used to determine if a user is an on-spot registrant.
        """
        stmt = (
            select(func.count())
            .select_from(OnSpotProfile)
            .where(OnSpotProfile.user_id == user_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() > 0

    # ========================================================
    # Lists
    # ========================================================

    async def list_by_station(
        self,
        station_id: str,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[OnSpotProfile]:
        """List profiles created at a specific station."""
        stmt = (
            select(OnSpotProfile)
            .where(OnSpotProfile.station_id == station_id)
            .order_by(OnSpotProfile.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_created_by_user(
        self,
        creator_user_id: UUID,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[OnSpotProfile]:
        """List profiles created by a specific staff user (audit trail)."""
        stmt = (
            select(OnSpotProfile)
            .where(OnSpotProfile.created_by_user_id == creator_user_id)
            .order_by(OnSpotProfile.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ========================================================
    # Counts
    # ========================================================

    async def count_by_station(self, station_id: str) -> int:
        """Count profiles created at a station."""
        stmt = (
            select(func.count())
            .select_from(OnSpotProfile)
            .where(OnSpotProfile.station_id == station_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def count_by_creator(self, creator_user_id: UUID) -> int:
        """Count profiles created by a specific staff user."""
        stmt = (
            select(func.count())
            .select_from(OnSpotProfile)
            .where(OnSpotProfile.created_by_user_id == creator_user_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()