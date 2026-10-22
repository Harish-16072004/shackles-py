"""Team schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator

from shackles.models.enums import TeamStatus
from shackles.schemas.common import ApiBase, ApiRead, ApiWrite


class TeamBase(ApiBase):
    """Shared team fields."""

    name: str = Field(min_length=3, max_length=200)


class TeamCreate(TeamBase, ApiWrite):
    """Payload for POST /api/teams."""

    event_id: UUID

    @field_validator("name")
    @classmethod
    def _validate_name(cls, v: str) -> str:
        # Matches the Node.js validateTeamName logic
        import re
        if not re.match(r"^[A-Za-z0-9 _-]{3,40}$", v):
            raise ValueError(
                "Team name must be 3-40 characters, letters, numbers, "
                "spaces, hyphens, or underscores only"
            )
        banned = {"TEST", "ADMIN", "DUMMY", "MODERATOR", "ROOT"}
        upper = v.upper()
        for word in banned:
            if word in upper.split():
                raise ValueError("Please choose a professional team name")
        return v


class TeamJoin(ApiWrite):
    """Payload for POST /api/teams/join."""

    event_id: UUID
    team_code: str = Field(min_length=4, max_length=20)


class TeamJoinWithInvite(ApiWrite):
    """Payload for joining via emailed invite token."""

    event_id: UUID
    team_code: str = Field(min_length=4, max_length=20)
    invite_token: str = Field(min_length=1, max_length=200)


class TeamRead(ApiRead):
    """Public team representation."""

    id: UUID
    event_id: UUID
    name: str
    team_code: str
    join_code: str | None
    join_code_expires_at: datetime | None
    status: TeamStatus
    member_count: int
    leader_user_id: UUID | None
    leader_contact_phone_snapshot: str | None
    leader_contact_email_snapshot: str | None
    locked_at: datetime | None
    created_at: datetime
    updated_at: datetime


class TeamMemberRead(ApiRead):
    """A team member as seen from the team view."""

    user_id: UUID
    first_name: str
    last_name: str
    email: str
    role: str | None  # LEADER | MEMBER


class TeamDetailRead(TeamRead):
    """Team with its members."""

    members: list[TeamMemberRead] = []


class TeamLockRequest(ApiWrite):
    """Payload for POST /api/teams/{id}/lock — no body needed, but explicit."""

    pass


class TeamBulkRegister(ApiWrite):
    """Payload for admin/coordinator bulk team registration via Shackles IDs."""

    event_name: str = Field(min_length=1, max_length=200)
    team_name: str = Field(min_length=3, max_length=200)
    shackles_ids: list[str] = Field(min_length=1, max_length=10)
    leader_shackles_id: str = Field(min_length=1, max_length=20)
    station_id: str = Field(min_length=1, max_length=100)
    operation_id: str | None = Field(default=None, max_length=200)
    lock_team: bool = False
    mark_attended: bool = False