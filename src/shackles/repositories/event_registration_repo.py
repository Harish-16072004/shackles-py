"""EventRegistrationRepository — data access for event registrations."""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from shackles.errors import (
    ALREADY_REGISTERED,
    DomainError,
    NOT_REGISTERED,
)
from shackles.models.enums import RegistrationSource
from shackles.models.event_registration import EventRegistration
from shackles.repositories.base import BaseRepository


class EventRegistrationRepository(BaseRepository[EventRegistration]):
    """Data access for event registrations."""

    model = EventRegistration

    # ========================================================
    # Lookups
    # ========================================================

    async def get_by_user_and_event(
        self,
        user_id: UUID,
        event_id: UUID,
    ) -> EventRegistration | None:
        """Fetch a specific (user, event) registration.

        Uses the `userId_eventId` unique constraint for an index-backed
        single-row lookup.
        """
        stmt = select(EventRegistration).where(
            EventRegistration.user_id == user_id,
            EventRegistration.event_id == event_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_user_and_event_or_raise(
        self,
        user_id: UUID,
        event_id: UUID,
    ) -> EventRegistration:
        """Fetch a registration. Raises NOT_REGISTERED if missing."""
        reg = await self.get_by_user_and_event(user_id, event_id)
        if reg is None:
            raise DomainError(
                NOT_REGISTERED,
                "Participant is not registered for this event.",
                {"user_id": str(user_id), "event_id": str(event_id)},
            )
        return reg

    async def is_registered(
        self,
        user_id: UUID,
        event_id: UUID,
    ) -> bool:
        """Check whether a user is already registered for an event."""
        stmt = (
            select(func.count())
            .select_from(EventRegistration)
            .where(
                EventRegistration.user_id == user_id,
                EventRegistration.event_id == event_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() > 0

    # ========================================================
    # Lists
    # ========================================================

    async def list_by_user(
        self,
        user_id: UUID,
        *,
        year: int | None = None,
    ) -> list[EventRegistration]:
        """List all registrations for a user.

        Eager-loads the related Event so services can access
        `reg.event.name` without a lazy-load query.
        """
        stmt = (
            select(EventRegistration)
            .where(EventRegistration.user_id == user_id)
            .options(selectinload(EventRegistration.event))
            .order_by(EventRegistration.created_at.desc())
        )
        if year is not None:
            stmt = stmt.where(EventRegistration.year == year)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_event(
        self,
        event_id: UUID,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[EventRegistration]:
        """List all registrations for an event.

        Eager-loads the User so admin lists can render names without
        additional queries.
        """
        stmt = (
            select(EventRegistration)
            .where(EventRegistration.event_id == event_id)
            .options(selectinload(EventRegistration.user))
            .order_by(EventRegistration.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_team(
        self,
        team_id: UUID,
    ) -> list[EventRegistration]:
        """List all members of a team.

        Ordered by role (LEADER first) then by join time. Uses the
        `eventId_teamId` index as a prefix.
        """
        stmt = (
            select(EventRegistration)
            .where(EventRegistration.team_id == team_id)
            .options(selectinload(EventRegistration.user))
            .order_by(
                EventRegistration.member_role.desc(),  # LEADER > MEMBER alphabetically
                EventRegistration.created_at.asc(),
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_attended_for_event(
        self,
        event_id: UUID,
    ) -> list[EventRegistration]:
        """List registrations marked as attended for an event."""
        stmt = (
            select(EventRegistration)
            .where(
                EventRegistration.event_id == event_id,
                EventRegistration.attended.is_(True),
            )
            .options(selectinload(EventRegistration.user))
            .order_by(EventRegistration.attended_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ========================================================
    # Counts
    # ========================================================

    async def count_for_event(self, event_id: UUID) -> int:
        """Total registrations for an event.

        Note: counts rows, not distinct participants. For team events,
        each team member has their own row.
        """
        stmt = (
            select(func.count())
            .select_from(EventRegistration)
            .where(EventRegistration.event_id == event_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def count_participants_for_event(self, event_id: UUID) -> int:
        """Count distinct participants (teams count as 1).

        Mirrors the Node.js `getEventParticipantCount` logic:
          - Individual registrations count as 1 each
          - Team registrations count as 1 per distinct team

        The Node version does this via a groupBy; here we use a count
        of distinct team IDs for the team rows, plus individual rows.
        """
        # Team rows: 1 per distinct team_id (excluding NULLs)
        team_stmt = (
            select(func.count(func.distinct(EventRegistration.team_id)))
            .select_from(EventRegistration)
            .where(
                EventRegistration.event_id == event_id,
                EventRegistration.team_id.isnot(None),
            )
        )
        team_count = (await self.session.execute(team_stmt)).scalar_one() or 0

        # Individual rows: no team_id
        ind_stmt = (
            select(func.count())
            .select_from(EventRegistration)
            .where(
                EventRegistration.event_id == event_id,
                EventRegistration.team_id.is_(None),
            )
        )
        ind_count = (await self.session.execute(ind_stmt)).scalar_one() or 0

        return team_count + ind_count

    async def count_attended_for_event(self, event_id: UUID) -> int:
        """Count registrations marked attended for an event."""
        stmt = (
            select(func.count())
            .select_from(EventRegistration)
            .where(
                EventRegistration.event_id == event_id,
                EventRegistration.attended.is_(True),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def count_by_team(self, team_id: UUID) -> int:
        """Count registrations belonging to a team."""
        stmt = (
            select(func.count())
            .select_from(EventRegistration)
            .where(EventRegistration.team_id == team_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    # ========================================================
    # Duplicate prevention
    # ========================================================

    async def ensure_not_registered(
        self,
        user_id: UUID,
        event_id: UUID,
    ) -> None:
        """Raise ALREADY_REGISTERED if the user is registered."""
        if await self.is_registered(user_id, event_id):
            raise DomainError(
                ALREADY_REGISTERED,
                "You are already registered for this event.",
                {"user_id": str(user_id), "event_id": str(event_id)},
            )

    # ========================================================
    # Sync / offline helpers
    # ========================================================

    async def get_by_client_operation_id(
        self,
        client_operation_id: str,
    ) -> EventRegistration | None:
        """Look up a registration by the offline-sync dedup key."""
        stmt = select(EventRegistration).where(
            EventRegistration.client_operation_id == client_operation_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_pending_sync(
        self,
        station_id: str,
    ) -> list[EventRegistration]:
        """List registrations awaiting sync from a station (offline mode)."""
        stmt = (
            select(EventRegistration)
            .where(
                EventRegistration.station_id == station_id,
                EventRegistration.sync_status == "PENDING",
            )
            .order_by(EventRegistration.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())