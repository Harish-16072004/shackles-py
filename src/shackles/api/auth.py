"""Auth routes — register, login, forgot, reset."""

from pydantic import BaseModel, EmailStr, Field

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from shackles.db.session import get_session
from shackles.schemas.common import MessageResponse
from shackles.schemas.user import UserCreate, UserLogin, UserRead
from shackles.services.auth_service import AuthService
from shackles.services.rate_limit import (
    LIMIT_LOGIN,
    LIMIT_PASSWORD_RESET,
    LIMIT_REGISTER,
    limiter,
)


router = APIRouter(prefix="/auth", tags=["auth"])


class LoginResponse(BaseModel):
    user: UserRead
    access_token: str
    token_type: str = "bearer"


class RegisterResponse(BaseModel):
    user: UserRead
    message: str


class ForgotPasswordResponse(BaseModel):
    success: bool = True
    message: str


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=10, max_length=200)
    new_password: str = Field(min_length=8, max_length=128)


@router.post("/register", response_model=RegisterResponse, status_code=201)
@limiter.limit(LIMIT_REGISTER)
async def register(
    request: Request,
    payload: UserCreate,
    session: AsyncSession = Depends(get_session),
) -> RegisterResponse:
    """Create a new user account."""
    service = AuthService(session)
    user = await service.register(payload)
    await session.commit()
    return RegisterResponse(
        user=UserRead.model_validate(user),
        message="Account created. Please upload payment proof to activate.",
    )


@router.post("/login", response_model=LoginResponse)
@limiter.limit(LIMIT_LOGIN)
async def login(
    request: Request,
    payload: UserLogin,
    session: AsyncSession = Depends(get_session),
) -> LoginResponse:
    """Authenticate with email + password and receive a JWT."""
    service = AuthService(session)
    user, token = await service.login(payload.email, payload.password)
    return LoginResponse(
        user=UserRead.model_validate(user),
        access_token=token,
    )


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
@limiter.limit(LIMIT_PASSWORD_RESET)
async def forgot_password(
    request: Request,
    email: EmailStr,
    session: AsyncSession = Depends(get_session),
) -> ForgotPasswordResponse:
    """Request a password reset email."""
    service = AuthService(session)
    raw_token = await service.request_password_reset(email)
    await session.commit()
    return ForgotPasswordResponse(
        message="If an account exists, a reset link has been sent."
    )


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    payload: ResetPasswordRequest,
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    """Consume a reset token and set a new password."""
    service = AuthService(session)
    await service.reset_password(payload.token, payload.new_password)
    await session.commit()
    return MessageResponse(message="Password reset successfully.")