"""TeamInvite schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, Field

from shackles.schemas.common import ApiBase, ApiRead, ApiWrite


class TeamInviteCreate(ApiWrite):
    """Payload for POST /api/teams/{id}/invite."""

    emails: list[EmailStr] = Field(min_length=1, max_length=10)


class TeamInviteRead(ApiRead):
    """Public invite representation."""

    id: UUID
    team_id: UUID
    invited_email: str | None
    invited_by_user_id: UUID
    used_by_user_id: UUID | None
    expires_at: datetime
    used_at: datetime | None
    created_at: datetime