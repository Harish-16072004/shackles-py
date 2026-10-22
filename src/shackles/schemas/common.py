"""Shared Pydantic base classes and validators.

This module provides:
  - Base classes: ApiBase, ApiRead, ApiWrite
  - Validators: normalize_phone(), validate_password_strength()
  - Pagination: PaginationParams, PaginatedResponse
  - Responses: MessageResponse, ErrorResponse

Validators are plain functions (not Annotated types) so schemas can call
them from their own `field_validator` methods. This keeps validation logic
reusable and easy to test in isolation.
"""

import re

from pydantic import BaseModel, ConfigDict, Field


# ============================================================
# Base classes
# ============================================================

class ApiBase(BaseModel):
    """Base for all API schemas — shared config.

    Config options:
      - from_attributes: allows `Model.model_validate(orm_obj)` to read
        from SQLAlchemy model instances.
      - str_strip_whitespace: auto-trims leading/trailing whitespace on
        all string fields before validation.
      - validate_assignment: re-validates on attribute assignment (useful
        for catching bugs during development, costs a bit of performance).
      - extra: 'forbid' rejects unexpected fields — catches typos early.
    """

    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )


class ApiRead(ApiBase):
    """Base for read (output) schemas.

    Use for anything returned to clients. Additional config could go here
    (e.g., custom JSON encoders) without affecting input schemas.
    """

    pass


class ApiWrite(ApiBase):
    """Base for write (input) schemas.

    Use for anything accepted from clients. Extra='forbid' here is
    particularly important — it prevents clients from setting fields
    they shouldn't be able to set (like `id`, `created_at`, `role`).
    """

    pass


# ============================================================
# Phone number validation
# ============================================================

# Indian mobile: optional +91/91 prefix, then 10 digits starting with 6-9.
# Captures only the 10-digit portion in group 1.
_INDIAN_PHONE_REGEX = re.compile(r"^(?:\+91|91)?([6-9]\d{9})$")


def normalize_phone(value: str) -> str:
    """Normalize an Indian phone number to 10 digits.

    Accepts:
        '9876543210'
        '+919876543210'
        '919876543210'
        '+91 98765 43210'
        '98765-43210'

    Returns:
        '9876543210'  (10-digit string, no prefix)

    Raises:
        ValueError: if the number is not a valid Indian mobile number.
    """
    if not isinstance(value, str):
        raise ValueError("Phone number must be a string")

    # Strip spaces, hyphens, and other common separators
    cleaned = value.replace(" ", "").replace("-", "").strip()

    match = _INDIAN_PHONE_REGEX.match(cleaned)
    if not match:
        raise ValueError(
            "Enter a valid 10-digit Indian mobile number "
            "(e.g., 9876543210)"
        )
    return match.group(1)


# ============================================================
# Password validation
# ============================================================

def validate_password_strength(value: str) -> str:
    """Check password meets minimum strength requirements.

    Requirements:
        - At least 8 characters
        - At least one letter
        - At least one digit

    Args:
        value: The plaintext password to validate.

    Returns:
        The password unchanged if valid.

    Raises:
        ValueError: if any requirement is not met.
    """
    if not isinstance(value, str):
        raise ValueError("Password must be a string")

    if len(value) < 8:
        raise ValueError("Password must be at least 8 characters")

    if not any(c.isalpha() for c in value):
        raise ValueError("Password must contain at least one letter")

    if not any(c.isdigit() for c in value):
        raise ValueError("Password must contain at least one digit")

    return value


# ============================================================
# Pagination
# ============================================================

class PaginationParams(ApiWrite):
    """Standard pagination query parameters.

    Use as a FastAPI dependency for list endpoints:

        @router.get("/users")
        async def list_users(
            pagination: PaginationParams = Depends(),
            ...
        ):
            ...
    """

    page: int = Field(
        default=1,
        ge=1,
        description="Page number, 1-indexed",
    )
    page_size: int = Field(
        default=25,
        ge=1,
        le=100,
        description="Items per page (max 100)",
    )

    @property
    def offset(self) -> int:
        """Compute the SQL OFFSET for this page."""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """Alias for page_size — reads better in some contexts."""
        return self.page_size


class PaginatedResponse(ApiRead):
    """Standard paginated response wrapper.

    Subclass this for specific resources:

        class UserListResponse(PaginatedResponse):
            items: list[UserRead]
    """

    total: int = Field(ge=0, description="Total number of items across all pages")
    page: int = Field(ge=1, description="Current page number")
    page_size: int = Field(ge=1, description="Items per page")
    total_pages: int = Field(ge=0, description="Total number of pages")

    @classmethod
    def compute_total_pages(cls, total: int, page_size: int) -> int:
        """Helper for endpoints to compute total_pages."""
        if page_size <= 0:
            return 0
        return (total + page_size - 1) // page_size


# ============================================================
# Standard response wrappers
# ============================================================

class MessageResponse(ApiRead):
    """Generic {success, message} response.

    Use for operations that don't return data:

        return MessageResponse(message="Team locked successfully")
    """

    success: bool = True
    message: str


class ErrorResponse(ApiRead):
    """Standard error response.

    Returned by exception handlers in the app. The `code` field should
    match a DomainError code (e.g., 'TEAM_FULL', 'PAYMENT_NOT_VERIFIED').
    """

    error: str
    code: str | None = None
    details: dict | None = None


# ============================================================
# Exports
# ============================================================

__all__ = [
    # Base classes
    "ApiBase",
    "ApiRead",
    "ApiWrite",
    # Validators
    "normalize_phone",
    "validate_password_strength",
    # Pagination
    "PaginationParams",
    "PaginatedResponse",
    # Responses
    "MessageResponse",
    "ErrorResponse",
]