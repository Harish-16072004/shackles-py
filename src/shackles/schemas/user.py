"""User schemas — register, read, update."""

from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, Field, field_validator

from shackles.models.enums import KitStatus, RegistrationType, Role
from shackles.schemas.common import (
    ApiBase,
    ApiRead,
    ApiWrite,
    normalize_phone,
    validate_password_strength,
)


class UserBase(ApiBase):
    """Shared user fields (no secrets)."""

    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    phone: str = Field(min_length=10, max_length=13)
    college_name: str = Field(min_length=1, max_length=255)
    college_loc: str = Field(min_length=1, max_length=255)
    department: str = Field(min_length=1, max_length=100)
    year_of_study: str = Field(min_length=1, max_length=10)
    gender: str | None = Field(default=None, max_length=10)

    @field_validator("phone", mode="before")
    @classmethod
    def _normalize_phone(cls, v: str) -> str:
        return normalize_phone(v)


class UserCreate(UserBase, ApiWrite):
    """Payload for POST /api/auth/register."""

    password: str = Field(min_length=8, max_length=128)
    registration_type: RegistrationType = RegistrationType.GENERAL
    gender: str = Field(min_length=1, max_length=10)

    @field_validator("password", mode="after")
    @classmethod
    def _check_password(cls, v: str) -> str:
        return validate_password_strength(v)


class UserLogin(ApiWrite):
    """Payload for POST /api/auth/login."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserRead(ApiRead):
    """Public user representation (never includes secrets)."""

    id: UUID
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    college_name: str
    college_loc: str
    department: str
    year_of_study: str
    gender: str | None
    role: Role
    registration_type: RegistrationType
    shackles_id: str | None
    kit_status: KitStatus
    kit_issued_at: datetime | None
    created_at: datetime
    updated_at: datetime


class UserReadWithQR(UserRead):
    """User with QR token — only returned to the user themselves or admins."""

    qr_token: str | None
    qr_image_url: str | None
    qr_token_expiry: datetime | None


class UserUpdate(ApiWrite):
    """Payload for PATCH /api/users/me — all fields optional."""

    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = Field(default=None, min_length=10, max_length=13)
    college_name: str | None = Field(default=None, max_length=255)
    college_loc: str | None = Field(default=None, max_length=255)
    department: str | None = Field(default=None, max_length=100)
    year_of_study: str | None = Field(default=None, max_length=10)
    gender: str | None = Field(default=None, max_length=10)

    @field_validator("phone", mode="before")
    @classmethod
    def _normalize_phone(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return normalize_phone(v)


class UserPasswordChange(ApiWrite):
    """Payload for POST /api/users/me/change-password."""

    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password", mode="after")
    @classmethod
    def _check_password(cls, v: str) -> str:
        return validate_password_strength(v)


class UserRoleUpdate(ApiWrite):
    """Payload for PATCH /api/admin/users/{id}/role — admin only."""

    role: Role