"""FastAPI dependencies — auth, session, and role guards.

Every protected route uses one of:

    user: User = Depends(get_current_user)        # any logged-in user
    admin: User = Depends(get_current_admin)      # ADMIN only
    staff: User = Depends(get_current_staff)      # ADMIN | COORDINATOR | VOLUNTEER

And every route that touches the DB uses:

    session: AsyncSession = Depends(get_session)
"""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from shackles.db.session import get_session
from shackles.errors import DomainError, UNAUTHORIZED
from shackles.models.enums import Role
from shackles.models.user import User
from shackles.repositories.user_repo import UserRepository
from shackles.services.tokens import decode_access_token


# Bearer token extractor. auto_error=False lets us craft our own 401
# messages instead of FastAPI's default.
_bearer = HTTPBearer(auto_error=False)


SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
) -> User:
    """Decode the JWT and return the authenticated user.

    Raises 401 if the header is missing, the token is invalid, or the
    user no longer exists.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = UUID(payload.sub)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = await UserRepository(session).get(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
) -> User | None:
    """Like get_current_user, but returns None instead of 401.

    Used by endpoints that behave differently for logged-in users but
    don't require authentication.
    """
    if credentials is None or not credentials.credentials:
        return None
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        return None
    try:
        user_id = UUID(payload.sub)
    except ValueError:
        return None
    return await UserRepository(session).get(user_id)


async def get_current_admin(
    user: User = Depends(get_current_user),
) -> User:
    """Require the ADMIN role."""
    if user.role != Role.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


async def get_current_staff(
    user: User = Depends(get_current_user),
) -> User:
    """Require ADMIN, COORDINATOR, or VOLUNTEER."""
    allowed = {Role.ADMIN.value, Role.COORDINATOR.value, Role.VOLUNTEER.value}
    if user.role not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff access required",
        )
    return user


# Aliases for cleaner signatures
CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]
CurrentAdmin = Annotated[User, Depends(get_current_admin)]
CurrentStaff = Annotated[User, Depends(get_current_staff)]