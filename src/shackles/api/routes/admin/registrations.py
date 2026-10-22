"""Admin routes for managing event registrations."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from shackles.api.deps import CurrentAdmin
from shackles.db.session import get_session
from shackles.repositories.event_registration_repo import (
    EventRegistrationRepository,
)
from shackles.schemas.common import MessageResponse
from shackles.schemas.event_registration import EventRegistrationWithUser


router = APIRouter(prefix="/events/{event_id}/registrations", tags=["admin-registrations"])


@router.get("", response_model=list[EventRegistrationWithUser])
async def list_event_registrations(
    event_id: UUID,
    admin: CurrentAdmin,
    session: AsyncSession = Depends(get_session),
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[EventRegistrationWithUser]:
    """List all registrations for an event, with user details."""
    repo = EventRegistrationRepository(session)
    rows = await repo.list_by_event(event_id, limit=limit, offset=offset)

    out: list[EventRegistrationWithUser] = []
    for r in rows:
        u = r.user
        out.append(
            EventRegistrationWithUser(
                id=r.id,
                user_id=r.user_id,
                event_id=r.event_id,
                team_id=r.team_id,
                member_role=r.member_role,  # type: ignore[arg-type]
                team_name=r.team_name,
                team_size=r.team_size,
                attended=r.attended,
                attended_at=r.attended_at,
                source=r.source,  # type: ignore[arg-type]
                sync_status=r.sync_status,  # type: ignore[arg-type]
                station_id=r.station_id,
                year=r.year,
                created_at=r.created_at,
                updated_at=r.updated_at,
                user_first_name=u.first_name if u else "",
                user_last_name=u.last_name if u else "",
                user_email=u.email if u else "",
                user_phone=u.phone if u else "",
                user_college_name=u.college_name if u else "",
                user_shackles_id=u.shackles_id if u else None,
            )
        )
    return out


@router.delete("/{registration_id}", response_model=MessageResponse)
async def delete_registration(
    event_id: UUID,
    registration_id: UUID,
    admin: CurrentAdmin,
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    """Delete a single registration."""
    repo = EventRegistrationRepository(session)
    reg = await repo.get(registration_id)
    if reg is None:
        from shackles.errors import NOT_FOUND, DomainError

        raise DomainError(NOT_FOUND, "Registration not found.")
    await repo.delete(registration_id)
    await session.commit()
    return MessageResponse(message="Registration deleted.")