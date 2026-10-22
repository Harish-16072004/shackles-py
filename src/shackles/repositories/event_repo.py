"""EventRepository — data access for Event."""

from sqlalchemy import func, or_, select

from shackles.errors import EVENT_NOT_FOUND, DomainError
from shackles.models.enums import EventCategory, EventParticipationMode
from shackles.models.event import Event
from shackles.repositories.base import BaseRepository


class EventRepository(BaseRepository[Event]):
    """Data access for events."""

    model = Event

    # ========================================================
    # Common list queries
    # ========================================================

    async def list_active(
        self,
        year: int,
        *,
        category: EventCategory | str | None = None,
        event_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Event]:
        """List active, non-archived, non-template events for a year.

        This is the primary query for public event listings.
        """
        stmt = (
            select(Event)
            .where(
                Event.year == year,
                Event.is_active.is_(True),
                Event.is_archived.is_(False),
                Event.is_template.is_(False),
            )
        )
        if category is not None:
            category_value = (
                category.value if isinstance(category, EventCategory) else category
            )
            stmt = stmt.where(Event.category == category_value)
        if event_type is not None:
            stmt = stmt.where(Event.type == event_type)

        stmt = stmt.order_by(Event.date.asc().nullslast(), Event.name.asc())
        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_year(
        self,
        year: int,
        *,
        include_archived: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Event]:
        """List events for a year. Includes templates/archived by default."""
        stmt = select(Event).where(Event.year == year)
        if not include_archived:
            stmt = stmt.where(Event.is_archived.is_(False))
        stmt = stmt.order_by(Event.name.asc()).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_templates(
        self,
        year: int,
    ) -> list[Event]:
        """List template events for a year (used by bootstrap-year)."""
        stmt = (
            select(Event)
            .where(
                Event.year == year,
                Event.is_template.is_(True),
                Event.is_archived.is_(False),
            )
            .order_by(Event.name.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_team_events(
        self,
        year: int,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Event]:
        """List active team-mode events for a year."""
        stmt = (
            select(Event)
            .where(
                Event.year == year,
                Event.participation_mode == EventParticipationMode.TEAM.value,
                Event.is_active.is_(True),
                Event.is_archived.is_(False),
                Event.is_template.is_(False),
            )
            .order_by(Event.date.asc().nullslast(), Event.name.asc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ========================================================
    # Lookups
    # ========================================================

    async def get_by_name_and_year(
        self,
        name: str,
        year: int,
    ) -> Event | None:
        """Find an event by name (case-insensitive) within a year."""
        stmt = select(Event).where(
            func.lower(Event.name) == name.lower(),
            Event.year == year,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name_year_or_raise(
        self,
        name: str,
        year: int,
    ) -> Event:
        """Find by name and year. Raises if not found."""
        event = await self.get_by_name_and_year(name, year)
        if event is None:
            raise DomainError(
                EVENT_NOT_FOUND,
                f"Event '{name}' for year {year} not found",
                {"name": name, "year": year},
            )
        return event

    # ========================================================
    # Counts
    # ========================================================

    async def count_by_year(self, year: int) -> int:
        """Total events for a year (excluding archived)."""
        stmt = (
            select(func.count())
            .select_from(Event)
            .where(
                Event.year == year,
                Event.is_archived.is_(False),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def count_by_category(
        self,
        year: int,
        category: EventCategory | str,
    ) -> int:
        """Count events in a category for a year."""
        category_value = (
            category.value if isinstance(category, EventCategory) else category
        )
        stmt = (
            select(func.count())
            .select_from(Event)
            .where(
                Event.year == year,
                Event.category == category_value,
                Event.is_archived.is_(False),
                Event.is_active.is_(True),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    # ========================================================
    # Search
    # ========================================================

    async def search(
        self,
        query: str,
        year: int,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Event]:
        """Case-insensitive search by event name or description."""
        pattern = f"%{query}%"
        stmt = (
            select(Event)
            .where(
                Event.year == year,
                Event.is_archived.is_(False),
                or_(
                    Event.name.ilike(pattern),
                    Event.description.ilike(pattern),
                ),
            )
            .order_by(Event.name.asc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())