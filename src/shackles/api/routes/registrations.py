"""Event registration routes — sign up, list my registrations."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shackles.api.deps import CurrentUser
from shackles.db.session import get_session
from shackles.schemas.event_registration import (
    EventRegistrationCreate,
    EventRegistrationRead,
)
from shackles.services.registration_service import RegistrationService


router = APIRouter(tags=["registrations"])


@router.post(
    "/events/{event_id}/register",
    response_model=EventRegistrationRead,
    status_code=201,
)
async def register_for_event(
    event_id: UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> EventRegistrationRead:
    """Register the current user for an INDIVIDUAL event."""
    service = RegistrationService(session)
    registration = await service.register_individual(user.id, event_id)
    await session.commit()
    return EventRegistrationRead.model_validate(registration)


@router.get(
    "/registrations/me",
    response_model=list[EventRegistrationRead],
)
async def list_my_registrations(
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> list[EventRegistrationRead]:
    """List all registrations for the current user in the active year."""
    service = RegistrationService(session)
    registrations = await service.list_my_registrations(user.id)
    return [EventRegistrationRead.model_validate(r) for r in registrations]