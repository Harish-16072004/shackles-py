"""EventRegistration schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from shackles.models.enums import (
    RegistrationSource,
    RegistrationSyncStatus,
    TeamMemberRole,
)
from shackles.schemas.common import ApiBase, ApiRead, ApiWrite


class EventRegistrationBase(ApiBase):
    """Shared registration fields."""

    member_role: TeamMemberRole | None = None
    team_name: str | None = Field(default=None, max_length=200)
    team_size: int = Field(default=1, ge=1)
    source: RegistrationSource = RegistrationSource.ONLINE


class EventRegistrationCreate(ApiWrite):
    """Payload for POST /api/events/{event_id}/register."""

    event_id: UUID


class EventRegistrationRead(ApiRead):
    """Public registration representation."""

    id: UUID
    user_id: UUID
    event_id: UUID
    team_id: UUID | None
    member_role: TeamMemberRole | None
    team_name: str | None
    team_size: int
    attended: bool
    attended_at: datetime | None
    source: RegistrationSource
    sync_status: RegistrationSyncStatus
    station_id: str | None
    year: int | None
    created_at: datetime
    updated_at: datetime


class EventRegistrationWithUser(EventRegistrationRead):
    """Registration with nested user info — for admin lists."""

    user_first_name: str
    user_last_name: str
    user_email: str
    user_phone: str
    user_college_name: str
    user_shackles_id: str | None


class AttendanceMark(ApiWrite):
    """Payload for marking attendance."""

    event_id: UUID
    station_id: str = Field(min_length=1, max_length=100)
    client_operation_id: str | None = Field(default=None, max_length=200)   