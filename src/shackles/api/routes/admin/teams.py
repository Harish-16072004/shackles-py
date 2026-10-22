"""Admin team management routes."""

from uuid import UUID

from pydantic import BaseModel

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shackles.api.deps import CurrentAdmin
from shackles.db.session import get_session
from shackles.schemas.common import MessageResponse
from shackles.schemas.team import TeamRead
from shackles.services.team_service import TeamService


router = APIRouter(prefix="/teams", tags=["admin-teams"])


class ChangeLeaderRequest(BaseModel):
    new_leader_user_id: UUID


class BulkRegisterRequest(BaseModel):
    event_id: UUID
    team_name: str
    shackles_ids: list[str]
    leader_shackles_id: str
    station_id: str = "ADMIN_PANEL"
    lock: bool = True
    mark_attended: bool = False


@router.post("/{team_id}/lock", response_model=TeamRead)
async def admin_lock_team(
    team_id: UUID,
    admin: CurrentAdmin,
    session: AsyncSession = Depends(get_session),
) -> TeamRead:
    """Force-lock a team (admin override)."""
    service = TeamService(session)
    team = await service.lock_team(team_id, requesting_user_id=admin.id)
    await session.commit()
    return TeamRead.model_validate(team)


@router.post("/{team_id}/change-leader", response_model=TeamRead)
async def change_leader(
    team_id: UUID,
    payload: ChangeLeaderRequest,
    admin: CurrentAdmin,
    session: AsyncSession = Depends(get_session),
) -> TeamRead:
    """Swap the leader of a team."""
    service = TeamService(session)
    team = await service.change_leader(team_id, payload.new_leader_user_id)
    await session.commit()
    return TeamRead.model_validate(team)


@router.delete("/{team_id}", response_model=MessageResponse)
async def delete_team(
    team_id: UUID,
    admin: CurrentAdmin,
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    """Delete a team and all its member registrations."""
    service = TeamService(session)
    await service.delete_team(team_id)
    await session.commit()
    return MessageResponse(message="Team deleted.")


@router.post("/bulk-register", response_model=TeamRead)
async def bulk_register(
    payload: BulkRegisterRequest,
    admin: CurrentAdmin,
    session: AsyncSession = Depends(get_session),
) -> TeamRead:
    """On-spot bulk register: create/append a roster by Shackles IDs."""
    service = TeamService(session)
    team = await service.bulk_register_by_shackles_ids(
        event_id=payload.event_id,
        team_name=payload.team_name,
        shackles_ids=payload.shackles_ids,
        leader_shackles_id=payload.leader_shackles_id,
        lock=payload.lock,
        mark_attended=payload.mark_attended,
        station_id=payload.station_id,
    )
    await session.commit()
    return TeamRead.model_validate(team)