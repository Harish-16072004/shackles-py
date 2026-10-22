"""JWT token creation and verification."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from jose import JWTError, jwt
from pydantic import BaseModel

from shackles.config import settings


_ALGORITHM = "HS256"


class TokenPayload(BaseModel):
    """Decoded JWT payload."""

    sub: str          # user_id
    role: str
    exp: datetime
    iat: datetime


def create_access_token(
    user_id: UUID,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token.

    Args:
        user_id: The user's UUID (stored as `sub`).
        role: The user's role at time of issuance.
        expires_delta: Optional custom expiry. Defaults to
            `settings.access_token_expire_minutes`.

    Returns:
        A signed JWT string.
    """
    now = datetime.now(timezone.utc)
    if expires_delta is None:
        expires_delta = timedelta(
            minutes=settings.access_token_expire_minutes
        )
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=_ALGORITHM)


def decode_access_token(token: str) -> TokenPayload | None:
    """Decode and verify a JWT. Returns None if invalid or expired."""
    try:
        raw = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[_ALGORITHM],
        )
        return TokenPayload(**raw)
    except (JWTError, ValueError, TypeError):
        return None


def extract_user_id(token: str) -> UUID | None:
    """Convenience: decode and return just the user_id."""
    payload = decode_access_token(token)
    if payload is None:
        return None
    try:
        return UUID(payload.sub)
    except ValueError:
        return None