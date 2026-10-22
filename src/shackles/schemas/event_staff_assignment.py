"""EventStaffAssignment schemas.

Covers:
  - Assigning existing staff to an event (StaffAssignmentCreate)
  - Reading staff assignments (StaffAssignmentRead)
  - Creating new staff accounts (StaffUserCreate)
"""

from uuid import UUID

from pydantic import Field, field_validator

from shackles.models.enums import StaffRole
from shackles.schemas.common import ApiRead, ApiWrite, normalize_phone


class StaffAssignmentCreate(ApiWrite):
    """Payload for POST /api/admin/events/{event_id}/staff.

    Assigns an existing user (with COORDINATOR or VOLUNTEER role) to an
    event with a specific staff role.
    """

    user_id: UUID = Field(description="ID of the staff user to assign")
    staff_role: StaffRole = Field(description="Role for this assignment")


class StaffAssignmentRead(ApiRead):
    """Public representation of a staff assignment."""

    id: UUID
    event_id: UUID
    user_id: UUID
    staff_role: StaffRole


class StaffUserCreate(ApiWrite):
    """Payload for POST /api/admin/staff.

    Creates a brand new staff account (COORDINATOR or VOLUNTEER).
    These users have roles distinct from participants, and their
    college fields are filled with placeholder values ('Staff',
    'Event', 'Operations') to satisfy the User model's not-null
    constraints.
    """

    email: str = Field(
        min_length=5,
        max_length=255,
        description="Unique email for the staff account",
    )
    password: str = Field(
        min_length=8,
        max_length=128,
        description="Password (min 8 characters)",
    )
    first_name: str = Field(
        min_length=1,
        max_length=100,
    )
    last_name: str = Field(
        min_length=1,
        max_length=100,
    )
    phone: str = Field(
        min_length=10,
        max_length=13,
        description="Indian mobile number (10 digits, optional +91 prefix)",
    )
    role: StaffRole = Field(
        description="COORDINATOR or VOLUNTEER",
    )

    @field_validator("phone", mode="before")
    @classmethod
    def _normalize_phone(cls, v: str) -> str:
        """Normalize phone input to 10-digit format."""
        return normalize_phone(v)


class StaffListFilters(ApiWrite):
    """Query filters for listing staff users.

    Not strictly needed yet, but included for future admin endpoints
    that may filter by role, event assignment, etc.
    """

    role: StaffRole | None = None
    event_id: UUID | None = None
    search: str | None = Field(default=None, max_length=200)


# ============================================================
# Exports
# ============================================================

__all__ = [
    "StaffAssignmentCreate",
    "StaffAssignmentRead",
    "StaffUserCreate",
    "StaffListFilters",
]