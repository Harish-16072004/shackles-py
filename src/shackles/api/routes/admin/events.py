"""Admin event CRUD."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shackles.api.deps import CurrentAdmin
from shackles.db.session import get_session
from shackles.schemas.event import EventCreate, EventRead, EventUpdate
from shackles.services.event_service import EventService


router = APIRouter(prefix="/events", tags=["admin-events"])


@router.post("", response_model=EventRead, status_code=201)
async def create_event(
    payload: EventCreate,
    admin: CurrentAdmin,
    session: AsyncSession = Depends(get_session),
) -> EventRead:
    """Create a new event."""
    service = EventService(session)
    event = await service.create_event(payload)
    await session.commit()
    return EventRead.model_validate(event)


@router.patch("/{event_id}", response_model=EventRead)
async def update_event(
    event_id: UUID,
    payload: EventUpdate,
    admin: CurrentAdmin,
    session: AsyncSession = Depends(get_session),
) -> EventRead:
    """Update fields on an event."""
    service = EventService(session)
    event = await service.update_event(event_id, payload)
    await session.commit()
    return EventRead.model_validate(event)


@router.post("/{event_id}/archive", response_model=EventRead)
async def archive_event(
    event_id: UUID,
    admin: CurrentAdmin,
    session: AsyncSession = Depends(get_session),
) -> EventRead:
    """Archive an event (soft delete)."""
    service = EventService(session)
    event = await service.archive_event(event_id)
    await session.commit()
    return EventRead.model_validate(event)


@router.post("/{event_id}/restore", response_model=EventRead)
async def restore_event(
    event_id: UUID,
    admin: CurrentAdmin,
    session: AsyncSession = Depends(get_session),
) -> EventRead:
    """Restore a previously archived event."""
    service = EventService(session)
    event = await service.restore_event(event_id)
    await session.commit()
    return EventRead.model_validate(event)