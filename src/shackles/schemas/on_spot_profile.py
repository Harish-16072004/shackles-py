"""OnSpotProfile schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from shackles.schemas.common import ApiRead, ApiWrite


class OnSpotProfileCreate(ApiWrite):
    """Payload for creating an on-spot profile."""

    station_id: str | None = Field(default=None, max_length=100)
    device_id: str | None = Field(default=None, max_length=100)
    referral_source: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=500)


class OnSpotProfileRead(ApiRead):
    """Public on-spot profile representation."""

    id: UUID
    user_id: UUID
    created_by_user_id: UUID | None
    station_id: str | None
    device_id: str | None
    referral_source: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime