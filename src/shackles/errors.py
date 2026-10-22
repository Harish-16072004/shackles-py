
"""Domain errors — business-rule violations with stable codes.

Services raise these instead of generic exceptions. API handlers catch
them and translate to HTTP status codes with structured error bodies.
"""

from typing import Any


class DomainError(Exception):
    """Base class for all business-rule violations.

    Carries a stable `code` (e.g., 'TEAM_FULL') that clients can switch on,
    plus optional `details` for extra context.
    """

    def __init__(
        self,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details


# ============================================================
# Common domain error codes — use these as `code` arguments
# ============================================================

# --- Generic ---
NOT_FOUND = "NOT_FOUND"
ALREADY_EXISTS = "ALREADY_EXISTS"
INVALID_INPUT = "INVALID_INPUT"
UNAUTHORIZED = "UNAUTHORIZED"
FORBIDDEN = "FORBIDDEN"

# --- User / Auth ---
USER_NOT_FOUND = "USER_NOT_FOUND"
EMAIL_ALREADY_EXISTS = "EMAIL_ALREADY_EXISTS"
PHONE_ALREADY_EXISTS = "PHONE_ALREADY_EXISTS"
INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
INVALID_TOKEN = "INVALID_TOKEN"
TOKEN_EXPIRED = "TOKEN_EXPIRED"

# --- Payment ---
PAYMENT_NOT_FOUND = "PAYMENT_NOT_FOUND"
PAYMENT_NOT_VERIFIED = "PAYMENT_NOT_VERIFIED"
PAYMENT_ALREADY_VERIFIED = "PAYMENT_ALREADY_VERIFIED"
NO_VERIFIED_PACKAGE = "NO_VERIFIED_PACKAGE"

# --- Event ---
EVENT_NOT_FOUND = "EVENT_NOT_FOUND"
EVENT_WRONG_YEAR = "EVENT_WRONG_YEAR"
EVENT_INACTIVE = "EVENT_INACTIVE"
EVENT_FULL = "EVENT_FULL"
NOT_TEAM_EVENT = "NOT_TEAM_EVENT"
NOT_INDIVIDUAL_EVENT = "NOT_INDIVIDUAL_EVENT"

# --- Registration ---
ALREADY_REGISTERED = "ALREADY_REGISTERED"
NOT_REGISTERED = "NOT_REGISTERED"
TIME_CLASH = "TIME_CLASH"
PACKAGE_NOT_ALLOWED = "PACKAGE_NOT_ALLOWED"

# --- Team ---
TEAM_NOT_FOUND = "TEAM_NOT_FOUND"
TEAM_LOCKED = "TEAM_LOCKED"
TEAM_FULL = "TEAM_FULL"
TEAM_NAME_EXISTS = "TEAM_NAME_EXISTS"
TEAM_BELOW_MIN_SIZE = "TEAM_BELOW_MIN_SIZE"
TEAM_ABOVE_MAX_SIZE = "TEAM_ABOVE_MAX_SIZE"
JOIN_CODE_INVALID = "JOIN_CODE_INVALID"
ALREADY_IN_TEAM = "ALREADY_IN_TEAM"

# --- Marking ---
CRITERIA_NOT_FOUND = "CRITERIA_NOT_FOUND"
CRITERIA_ALREADY_EXISTS = "CRITERIA_ALREADY_EXISTS"
INVALID_MARKS = "INVALID_MARKS"

# --- Paper ---
SUBMISSION_NOT_FOUND = "SUBMISSION_NOT_FOUND"
DEADLINE_PASSED = "DEADLINE_PASSED"
NOT_SELECTED = "NOT_SELECTED"