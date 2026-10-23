"""Team routes — create, join, invite, lock, remove member, view."""

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from shackles.api.deps import CurrentUser
from shackles.db.session import get_session
from shackles.errors import INVALID_INPUT, DomainError
from shackles.schemas.common import MessageResponse
from shackles.schemas.team import (
    TeamDetailRead,
    TeamJoinWithInvite,
    TeamRead,
)
from shackles.schemas.team_invite import TeamInviteCreate, TeamInviteRead
from shackles.services.team_service import TeamService


router = APIRouter(prefix="/teams", tags=["teams"])


class CreateTeamRequest(BaseModel):
    """Body for POST /api/teams."""

    event_id: UUID
    name: str = Field(min_length=3, max_length=40)


class JoinTeamRequest(BaseModel):
    """Body for POST /api/teams/join."""

    event_id: UUID | None = None
    join_code: str | None = Field(default=None, min_length=4, max_length=20)
    team_code: str | None = Field(default=None, min_length=4, max_length=20)


@router.get("/me", response_model=list[TeamRead])
async def list_my_teams(
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> list[TeamRead]:
    """List all teams the current user belongs to in the active year."""
    service = TeamService(session)
    teams = await service.list_my_teams(user.id)
    return [TeamRead.model_validate(t) for t in teams]


@router.post("", response_model=TeamRead, status_code=201)
async def create_team(
    payload: CreateTeamRequest,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> TeamRead:
    """Create a new team for a TEAM event. Caller becomes the leader."""
    service = TeamService(session)
    team = await service.create_team(user.id, payload.event_id, payload.name)
    await session.commit()
    return TeamRead.model_validate(team)


@router.post("/join", response_model=TeamRead)
async def join_team(
    payload: JoinTeamRequest,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> TeamRead:
    """Join a team by join_code (global) or team_code (event-scoped)."""
    service = TeamService(session)

    if payload.join_code:
        team = await service.join_by_join_code(user.id, payload.join_code)
    elif payload.team_code and payload.event_id:
        team = await service.join_by_team_code(
            user.id, payload.event_id, payload.team_code
        )
    else:
        raise DomainError(
            INVALID_INPUT,
            "Provide either join_code or (team_code + event_id).",
        )

    await session.commit()
    return TeamRead.model_validate(team)


@router.post("/join-by-invite", response_model=TeamRead)
async def join_team_by_invite(
    payload: TeamJoinWithInvite,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> TeamRead:
    """Join a team using an emailed invitation token."""
    service = TeamService(session)
    team = await service.join_by_invite_token(
        user_id=user.id,
        event_id=payload.event_id,
        team_code=payload.team_code,
        invite_token=payload.invite_token,
    )
    await session.commit()
    return TeamRead.model_validate(team)


@router.get("/{team_id}", response_model=TeamDetailRead)
async def get_team(
    team_id: UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> TeamDetailRead:
    """Fetch a team with its members."""
    service = TeamService(session)
    team = await service.get_team_with_members(team_id)

    members = [
        {
            "user_id": reg.user_id,
            "first_name": reg.user.first_name if reg.user else "",
            "last_name": reg.user.last_name if reg.user else "",
            "email": reg.user.email if reg.user else "",
            "role": reg.member_role,
        }
        for reg in team.members
    ]

    return TeamDetailRead(
        id=team.id,
        event_id=team.event_id,
        name=team.name,
        team_code=team.team_code,
        join_code=team.join_code,
        join_code_expires_at=team.join_code_expires_at,
        status=team.status,  # type: ignore[arg-type]
        member_count=team.member_count,
        leader_user_id=team.leader_user_id,
        leader_contact_phone_snapshot=team.leader_contact_phone_snapshot,
        leader_contact_email_snapshot=team.leader_contact_email_snapshot,
        locked_at=team.locked_at,
        created_at=team.created_at,
        updated_at=team.updated_at,
        members=members,  # type: ignore[arg-type]
    )


@router.post("/{team_id}/lock", response_model=TeamRead)
async def lock_team(
    team_id: UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> TeamRead:
    """Lock a team. Allowed for the leader or any ADMIN/COORDINATOR."""
    service = TeamService(session)
    team = await service.lock_team(team_id, requesting_user_id=user.id)
    await session.commit()
    return TeamRead.model_validate(team)


@router.post(
    "/{team_id}/invites",
    response_model=list[TeamInviteRead],
    status_code=201,
)
async def create_team_invites(
    team_id: UUID,
    payload: TeamInviteCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> list[TeamInviteRead]:
    """Send email invitations to join the team (team leader only)."""
    service = TeamService(session)
    invites = await service.create_invites(
        team_id=team_id,
        requesting_user_id=user.id,
        emails=[str(e) for e in payload.emails],
    )
    await session.commit()
    return [TeamInviteRead.model_validate(i) for i in invites]


@router.get("/{team_id}/invites", response_model=list[TeamInviteRead])
async def list_team_invites(
    team_id: UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> list[TeamInviteRead]:
    """List active invitations for a team (leader or staff only)."""
    service = TeamService(session)
    invites = await service.list_invites_for_team(
        team_id=team_id,
        requesting_user_id=user.id,
    )
    return [TeamInviteRead.model_validate(i) for i in invites]


@router.delete(
    "/{team_id}/members/{member_user_id}",
    response_model=MessageResponse,
)
async def remove_team_member(
    team_id: UUID,
    member_user_id: UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    """Remove a member from an open team (leader, self, or admin)."""
    service = TeamService(session)
    remaining_team = await service.remove_member(
        team_id=team_id,
        user_id=member_user_id,
        requesting_user_id=user.id,
    )
    await session.commit()
    if remaining_team is None:
        return MessageResponse(message="Last member removed; team deleted.")
    return MessageResponse(message="Member removed from team.")