"""Public event listing routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from shackles.db.session import get_session
from shackles.schemas.event import EventListFilters, EventRead
from shackles.services.event_service import EventService


router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=list[EventRead])
async def list_events(
    year: int | None = Query(default=None, ge=2000, le=3000),
    category: str | None = Query(default=None),
    type: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> list[EventRead]:
    """List active events for the given year/category/type.

    Public endpoint — no authentication required.
    """
    service = EventService(session)
    filters = EventListFilters(
        year=year,
        category=category,  # type: ignore[arg-type]
        type=type,
    )
    events = await service.list_public_events(filters)
    return [EventRead.model_validate(e) for e in events]


@router.get("/{event_id}", response_model=EventRead)
async def get_event(
    event_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> EventRead:
    """Fetch a single event by ID."""
    service = EventService(session)
    event = await service.get_event(event_id)
    return EventRead.model_validate(event)