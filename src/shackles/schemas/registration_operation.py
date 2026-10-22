"""RegistrationOperation schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from shackles.models.enums import (
    RegistrationOperationType,
    RegistrationSyncStatus,
)
from shackles.schemas.common import ApiRead, ApiWrite


class RegistrationOperationCreate(ApiWrite):
    """Payload for recording a scanner operation (from offline queue)."""

    operation_id: str = Field(min_length=1, max_length=200)
    station_id: str = Field(min_length=1, max_length=100)
    operation_type: RegistrationOperationType
    participant_id: str | None = Field(default=None, max_length=50)
    event_name: str | None = Field(default=None, max_length=200)
    team_name: str | None = Field(default=None, max_length=200)
    payload: dict[str, Any] | None = None
    payload_hash: str | None = Field(default=None, max_length=128)


class RegistrationOperationRead(ApiRead):
    """Public operation record."""

    id: UUID
    operation_id: str
    station_id: str
    operation_type: RegistrationOperationType
    actor_user_id: str | None
    participant_id: str | None
    event_name: str | None
    team_name: str | None
    status: RegistrationSyncStatus
    conflict_reason: str | None
    error_message: str | None
    processed_at: datetime | None
    created_at: datetime
    updated_at: datetime