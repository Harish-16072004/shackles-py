"""ContactMessage schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, Field, field_validator

from shackles.schemas.common import ApiBase, ApiRead, ApiWrite, normalize_phone


class ContactMessageCreate(ApiWrite):
    """Payload for POST /api/contact."""

    name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    mobile: str = Field(min_length=10, max_length=13)
    message: str = Field(min_length=10, max_length=2000)

    @field_validator("mobile", mode="before")
    @classmethod
    def _normalize_phone(cls, v: str) -> str:
        return normalize_phone(v)


class ContactMessageRead(ApiRead):
    """Public contact message representation."""

    id: UUID
    name: str
    email: str
    mobile: str
    message: str
    user_id: UUID | None
    created_at: datetime