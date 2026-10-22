"""AuthService — registration, login, password reset.

Owns the user-facing authentication flows. Depends on:
  - UserRepository
  - PaymentRepository
  - password utilities
  - token utilities
"""

import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from shackles.errors import (
    EMAIL_ALREADY_EXISTS,
    INVALID_CREDENTIALS,
    INVALID_TOKEN,
    PHONE_ALREADY_EXISTS,
    TOKEN_EXPIRED,
    DomainError,
)
from shackles.models.enums import Role
from shackles.models.user import User
from shackles.repositories.user_repo import UserRepository
from shackles.schemas.user import UserCreate
from shackles.services.password import hash_password, verify_password
from shackles.services.tokens import create_access_token


_RESET_TOKEN_TTL = timedelta(minutes=15)
_RESET_TOKEN_BYTES = 32


class AuthService:
    """Registration, login, and password-reset flows."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)

    # ========================================================
    # Registration
    # ========================================================

    async def register(
        self,
        data: UserCreate,
        *,
        role: Role = Role.APPLICANT,
    ) -> User:
        """Create a new user from a validated UserCreate payload.

        Steps:
          1. Reject if email or phone already exists
          2. Hash the password
          3. Persist the user with the given role

        Does NOT create a payment record — that's the registration
        flow's responsibility (see registration_service).

        Raises:
            DomainError(EMAIL_ALREADY_EXISTS) if email is taken.
            DomainError(PHONE_ALREADY_EXISTS) if phone is taken.
        """
        # --- Uniqueness checks ---
        if await self.users.email_exists(data.email):
            raise DomainError(
                EMAIL_ALREADY_EXISTS,
                "An account with this email already exists.",
                {"email": data.email},
            )

        if await self.users.phone_exists(data.phone):
            raise DomainError(
                PHONE_ALREADY_EXISTS,
                "An account with this phone number already exists.",
                {"phone": data.phone},
            )

        # --- Hash password ---
        password_hash = hash_password(data.password)

        # --- Persist ---
        user = await self.users.create(
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email.lower(),
            phone=data.phone,
            password=password_hash,
            college_name=data.college_name,
            college_loc=data.college_loc,
            department=data.department,
            year_of_study=data.year_of_study,
            gender=data.gender,
            role=role.value,
            registration_type=data.registration_type.value,
        )
        return user

    # ========================================================
    # Login
    # ========================================================

    async def authenticate(
        self,
        email: str,
        password: str,
    ) -> User | None:
        """Verify credentials. Returns the User or None.

        Performs a constant-time password check even when the email
        isn't found, to avoid leaking account existence via timing.
        """
        user = await self.users.get_by_email(email)

        if user is None:
            # Dummy verify to burn comparable CPU time
            verify_password(password, "$2b$12$" + "x" * 53)
            return None

        if not verify_password(password, user.password):
            return None

        return user

    async def login(
        self,
        email: str,
        password: str,
    ) -> tuple[User, str]:
        """Full login flow: verify credentials, issue JWT.

        Returns:
            (user, access_token)

        Raises:
            DomainError(INVALID_CREDENTIALS) on bad email/password.
        """
        user = await self.authenticate(email, password)
        if user is None:
            raise DomainError(
                INVALID_CREDENTIALS,
                "Invalid email or password.",
            )

        token = create_access_token(user_id=user.id, role=user.role)
        return user, token

    # ========================================================
    # Password reset — request
    # ========================================================

    async def request_password_reset(self, email: str) -> str | None:
        """Generate and store a password reset token for the email.

        Returns the raw token if the user exists, else None.

        The caller is responsible for emailing the token. We never
        reveal via the API whether the email exists — that's the API
        layer's concern.
        """
        user = await self.users.get_by_email(email)
        if user is None:
            return None

        raw_token = secrets.token_urlsafe(_RESET_TOKEN_BYTES)
        expiry = datetime.now(timezone.utc) + _RESET_TOKEN_TTL

        user.reset_token = raw_token
        user.reset_token_expiry = expiry
        await self.session.flush()

        return raw_token

    # ========================================================
    # Password reset — consume
    # ========================================================

    async def reset_password(
        self,
        token: str,
        new_password: str,
    ) -> User:
        """Consume a reset token and set a new password.

        The token is invalidated on success (single-use).

        Raises:
            DomainError(INVALID_TOKEN) if the token doesn't exist.
            DomainError(TOKEN_EXPIRED) if it exists but is expired.
        """
        user = await self.users.get_by_reset_token(token)
        if user is None:
            raise DomainError(
                INVALID_TOKEN,
                "Invalid or expired reset token.",
            )

        if user.reset_token_expiry is None:
            raise DomainError(
                INVALID_TOKEN,
                "Invalid reset token.",
            )

        now = datetime.now(timezone.utc)
        if now > user.reset_token_expiry:
            raise DomainError(
                TOKEN_EXPIRED,
                "This reset link has expired. Please request a new one.",
            )

        # Update password, clear token
        user.password = hash_password(new_password)
        user.reset_token = None
        user.reset_token_expiry = None
        await self.session.flush()
        await self.session.refresh(user)

        return user

    # ========================================================
    # Password change (authenticated)
    # ========================================================

    async def change_password(
        self,
        user_id: UUID,
        current_password: str,
        new_password: str,
    ) -> User:
        """Change a logged-in user's password.

        Raises:
            DomainError(INVALID_CREDENTIALS) if current_password is wrong.
        """
        user = await self.users.get(user_id)
        if user is None:
            raise DomainError(
                INVALID_CREDENTIALS,
                "User not found.",
            )

        if not verify_password(current_password, user.password):
            raise DomainError(
                INVALID_CREDENTIALS,
                "Current password is incorrect.",
            )

        user.password = hash_password(new_password)
        await self.session.flush()
        await self.session.refresh(user)
        return user