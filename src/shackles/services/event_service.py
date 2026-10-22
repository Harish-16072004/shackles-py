"""EventService — event CRUD and public listings."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from shackles.config import settings
from shackles.errors import EVENT_NOT_FOUND, DomainError
from shackles.models.enums import EventCategory
from shackles.models.event import Event
from shackles.repositories.event_registration_repo import (
    EventRegistrationRepository,
)
from shackles.repositories.event_repo import EventRepository
from shackles.repositories.team_repo import TeamRepository
from shackles.schemas.event import EventCreate, EventListFilters, EventUpdate


class EventService:
    """Read and manage events."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.events = EventRepository(session)
        self.registrations = EventRegistrationRepository(session)
        self.teams = TeamRepository(session)

    # ========================================================
    # Public reads
    # ========================================================

    async def list_public_events(
        self,
        filters: EventListFilters | None = None,
    ) -> list[Event]:
        """List active events for the public site."""
        year = filters.year if filters and filters.year else settings.active_year
        return await self.events.list_active(
            year,
            category=filters.category if filters else None,
            event_type=filters.type if filters else None,
            limit=200,
        )

    async def get_event(self, event_id: UUID) -> Event:
        """Fetch an event by ID. Raises EVENT_NOT_FOUND if missing."""
        event = await self.events.get(event_id)
        if event is None:
            raise DomainError(
                EVENT_NOT_FOUND,
                "Event not found.",
                {"event_id": str(event_id)},
            )
        return event

    # ========================================================
    # Admin writes
    # ========================================================

    async def create_event(self, data: EventCreate) -> Event:
        """Create a new event (admin only — enforced by API layer)."""
        existing = await self.events.get_by_name_and_year(data.name, data.year)
        if existing is not None:
            raise DomainError(
                "ALREADY_EXISTS",
                f"An event named '{data.name}' already exists for {data.year}.",
                {"name": data.name, "year": data.year},
            )

        # Default team sizes for team events
        team_min = data.team_min_size if data.participation_mode.value == "TEAM" else None
        team_max = data.team_max_size if data.participation_mode.value == "TEAM" else None

        event = await self.events.create(
            name=data.name,
            year=data.year,
            type=data.type,
            category=data.category.value if data.category else None,
            day_label=data.day_label,
            date=data.date,
            end_date=data.end_date,
            is_all_day=data.is_all_day,
            description=data.description,
            rules_url=data.rules_url,
            submission_url=data.submission_url,
            submission_deadline=data.submission_deadline,
            requires_document_submission=data.requires_document_submission,
            coordinator_name=data.coordinator_name,
            coordinator_phone=data.coordinator_phone,
            trainer_name=data.trainer_name,
            contact_name=data.contact_name,
            contact_phone=data.contact_phone,
            participation_mode=data.participation_mode.value,
            team_min_size=team_min,
            team_max_size=team_max,
            max_teams=data.max_teams,
            max_participants=data.max_participants,
            is_active=data.is_active,
            is_archived=False,
            is_template=False,
        )
        return event

    async def update_event(
        self,
        event_id: UUID,
        data: EventUpdate,
    ) -> Event:
        """Update specific fields on an event."""
        event = await self.get_event(event_id)

        updates = data.model_dump(exclude_unset=True)

        # Convert enums to their string values
        if "category" in updates and updates["category"] is not None:
            updates["category"] = updates["category"].value
        if "participation_mode" in updates and updates["participation_mode"] is not None:
            updates["participation_mode"] = updates["participation_mode"].value

        for field, value in updates.items():
            setattr(event, field, value)

        # Validate team size consistency
        if (
            event.team_min_size is not None
            and event.team_max_size is not None
            and event.team_min_size > event.team_max_size
        ):
            raise DomainError(
                "INVALID_INPUT",
                "team_min_size cannot exceed team_max_size.",
            )

        await self.session.flush()
        await self.session.refresh(event)
        return event

    async def archive_event(self, event_id: UUID) -> Event:
        """Archive an event (soft-delete: no new registrations)."""
        event = await self.get_event(event_id)
        event.is_active = False
        event.is_archived = True
        await self.session.flush()
        await self.session.refresh(event)
        return event

    async def restore_event(self, event_id: UUID) -> Event:
        """Un-archive an event."""
        event = await self.get_event(event_id)
        event.is_active = True
        event.is_archived = False
        await self.session.flush()
        await self.session.refresh(event)
        return event

    # ========================================================
    # Stats
    # ========================================================

    async def get_event_stats(self, event_id: UUID) -> dict:
        """Return registration + attendance stats for an event."""
        event = await self.get_event(event_id)

        total_registrations = await self.registrations.count_for_event(event_id)
        attended = await self.registrations.count_attended_for_event(event_id)
        teams = await self.teams.count_for_event(event_id)

        participants = await self.registrations.count_participants_for_event(
            event_id
        )

        return {
            "event_id": str(event.id),
            "event_name": event.name,
            "participation_mode": event.participation_mode,
            "total_registration_rows": total_registrations,
            "total_participants": participants,
            "total_teams": teams if event.participation_mode == "TEAM" else 0,
            "attended": attended,
            "max_participants": event.max_participants,
            "max_teams": event.max_teams,
            "spots_left": (
                max(event.max_participants - participants, 0)
                if event.max_participants is not None
                else None
            ),
        }

    async def list_public_categories(
        self,
        year: int | None = None,
    ) -> dict[str, int]:
        """Return event counts per category, for the events landing page."""
        target_year = year or settings.active_year
        return {
            "technical": await self.events.count_by_category(
                target_year, EventCategory.EVENT
            ),
            "workshop": await self.events.count_by_category(
                target_year, EventCategory.WORKSHOP
            ),
        }