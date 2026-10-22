"""Accommodation schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from shackles.schemas.common import ApiBase, ApiRead, ApiWrite


class AccommodationCreate(ApiWrite):
    """Payload for POST /api/accommodation."""

    days: list[str] = Field(min_length=1, max_length=10)


class AccommodationRead(ApiRead):
    """Public accommodation representation."""

    id: UUID
    user_id: UUID
    days: list[str]
    created_at: datetime