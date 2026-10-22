"""Global exception handlers.

Translates DomainError and validation errors into structured JSON
responses with stable error codes.
"""

import logging
from uuid import uuid4

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from shackles.errors import DomainError


logger = logging.getLogger(__name__)


# ============================================================
# DomainError code → HTTP status
# ============================================================

_STATUS_BY_CODE: dict[str, int] = {
    # 404
    "NOT_FOUND": 404,
    "USER_NOT_FOUND": 404,
    "EVENT_NOT_FOUND": 404,
    "TEAM_NOT_FOUND": 404,
    "SUBMISSION_NOT_FOUND": 404,
    "PAYMENT_NOT_FOUND": 404,
    # 409
    "ALREADY_EXISTS": 409,
    "EMAIL_ALREADY_EXISTS": 409,
    "PHONE_ALREADY_EXISTS": 409,
    "ALREADY_REGISTERED": 409,
    "TEAM_NAME_EXISTS": 409,
    "CRITERIA_ALREADY_EXISTS": 409,
    # 401
    "UNAUTHORIZED": 401,
    "INVALID_CREDENTIALS": 401,
    "INVALID_TOKEN": 401,
    "TOKEN_EXPIRED": 401,
    "NOT_AUTHENTICATED": 401,
    # 403
    "FORBIDDEN": 403,
    "NOT_AUTHORIZED": 403,
    # 400 — default; covered by the fallthrough
    "INVALID_INPUT": 400,
    "INVALID_MARKS": 400,
    "INVALID_TEAM_NAME": 400,
    "INVALID_QR": 400,
    "WRONG_YEAR": 400,
    "EVENT_FULL": 400,
    "TEAM_FULL": 400,
    "TEAM_LOCKED": 400,
    "TEAM_BELOW_MIN_SIZE": 400,
    "TEAM_ABOVE_MAX_SIZE": 400,
    "PAYMENT_NOT_VERIFIED": 400,
    "NO_VERIFIED_PACKAGE": 400,
    "PACKAGE_NOT_ALLOWED": 400,
    "TIME_CLASH": 400,
    "DEADLINE_PASSED": 400,
    "NOT_SELECTED": 400,
    "EVENT_INACTIVE": 400,
    "EVENT_WRONG_YEAR": 400,
    "NOT_TEAM_EVENT": 400,
    "NOT_INDIVIDUAL_EVENT": 400,
    "JOIN_CODE_INVALID": 400,
    "INVALID_LEADER": 400,
    "NOT_A_MEMBER": 400,
    "NOT_REGISTERED": 400,
    "CRITERIA_NOT_FOUND": 404,
}


def _status_for_code(code: str) -> int:
    return _STATUS_BY_CODE.get(code, 400)


# ============================================================
# Handlers
# ============================================================

async def domain_error_handler(
    request: Request, exc: DomainError
) -> JSONResponse:
    """Translate a DomainError into an HTTP response."""
    status_code = _status_for_code(exc.code)
    return JSONResponse(
        status_code=status_code,
        content={
            "error": exc.message,
            "code": exc.code,
            "details": exc.details or None,
        },
    )


async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Return a clean 422 with field-level details."""
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation failed",
            "code": "VALIDATION_ERROR",
            "details": {"errors": exc.errors()},
        },
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Wrap FastAPI's HTTPException in our error envelope."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail if isinstance(exc.detail, str) else "HTTP error",
            "code": _code_for_status(exc.status_code),
            "details": exc.detail if not isinstance(exc.detail, str) else None,
        },
    )


async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Catch-all — 500 with a request ID for tracing."""
    request_id = getattr(request.state, "request_id", str(uuid4()))
    logger.exception(
        "[%s] Unhandled exception at %s: %s",
        request_id,
        request.url.path,
        exc,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "code": "INTERNAL_ERROR",
            "details": {"request_id": request_id},
        },
    )


def _code_for_status(status_code: int) -> str:
    return {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        422: "UNPROCESSABLE_ENTITY",
        429: "RATE_LIMITED",
        500: "INTERNAL_ERROR",
    }.get(status_code, f"HTTP_{status_code}")


# ============================================================
# Registration
# ============================================================

def register_exception_handlers(app: FastAPI) -> None:
    """Wire all handlers into the FastAPI app."""
    app.add_exception_handler(DomainError, domain_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)