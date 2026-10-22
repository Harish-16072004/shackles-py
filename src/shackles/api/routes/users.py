"""User self-service routes — profile and password."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shackles.api.deps import CurrentUser
from shackles.db.session import get_session
from shackles.schemas.common import MessageResponse
from shackles.schemas.user import (
    UserPasswordChange,
    UserRead,
    UserUpdate,
)
from shackles.services.auth_service import AuthService
from shackles.services.user_service import UserService


router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
async def get_me(user: CurrentUser) -> UserRead:
    """Return the authenticated user's profile."""
    return UserRead.model_validate(user)


@router.patch("/me", response_model=UserRead)
async def update_me(
    payload: UserUpdate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> UserRead:
    """Update the authenticated user's profile."""
    service = UserService(session)
    updated = await service.update_profile(user.id, payload)
    await session.commit()
    return UserRead.model_validate(updated)


@router.post("/me/change-password", response_model=MessageResponse)
async def change_password(
    payload: UserPasswordChange,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    """Change the authenticated user's password."""
    service = AuthService(session)
    await service.change_password(
        user.id, payload.current_password, payload.new_password
    )
    await session.commit()
    return MessageResponse(message="Password changed successfully.")