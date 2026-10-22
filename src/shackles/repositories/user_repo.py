"""UserRepository — data access for User."""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from shackles.errors import USER_NOT_FOUND
from shackles.models.enums import Role
from shackles.models.user import User
from shackles.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Data access for users."""

    model = User

    # ========================================================
    # Lookups by unique fields
    # ========================================================

    async def get_by_email(self, email: str) -> User | None:
        """Fetch a user by email (case-insensitive)."""
        stmt = select(User).where(func.lower(User.email) == email.lower())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email_or_raise(self, email: str) -> User:
        """Fetch by email. Raises if not found."""
        user = await self.get_by_email(email)
        if user is None:
            from shackles.errors import DomainError
            raise DomainError(
                USER_NOT_FOUND,
                f"User with email {email} not found",
                {"email": email},
            )
        return user

    async def get_by_phone(self, phone: str) -> User | None:
        """Fetch a user by phone number."""
        stmt = select(User).where(User.phone == phone)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_shackles_id(self, shackles_id: str) -> User | None:
        """Fetch a user by their Shackles ID."""
        stmt = select(User).where(User.shackles_id == shackles_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_qr_token(self, qr_token: str) -> User | None:
        """Fetch a user by their QR token."""
        stmt = select(User).where(User.qr_token == qr_token)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_reset_token(self, reset_token: str) -> User | None:
        """Fetch a user by their password-reset token."""
        stmt = select(User).where(User.reset_token == reset_token)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    # ========================================================
    # Existence checks
    # ========================================================

    async def email_exists(self, email: str) -> bool:
        """Check whether an email is already registered."""
        stmt = (
            select(func.count())
            .select_from(User)
            .where(func.lower(User.email) == email.lower())
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() > 0

    async def phone_exists(self, phone: str) -> bool:
        """Check whether a phone number is already registered."""
        stmt = (
            select(func.count())
            .select_from(User)
            .where(User.phone == phone)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() > 0

    # ========================================================
    # Lists & filters
    # ========================================================

    async def list_by_role(
        self,
        role: Role | str,
        *,
        limit: int = 25,
        offset: int = 0,
    ) -> list[User]:
        """List users with a given role, newest first."""
        role_value = role.value if isinstance(role, Role) else role
        stmt = (
            select(User)
            .where(User.role == role_value)
            .order_by(User.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def search(
        self,
        query: str,
        *,
        limit: int = 25,
        offset: int = 0,
    ) -> list[User]:
        """Search users by name, email, phone, or college.

        Uses ILIKE-style case-insensitive matching. For production-scale
        data, consider a Postgres full-text search index.
        """
        pattern = f"%{query}%"
        stmt = (
            select(User)
            .where(
                or_(
                    User.first_name.ilike(pattern),
                    User.last_name.ilike(pattern),
                    User.email.ilike(pattern),
                    User.phone.ilike(pattern),
                    User.college_name.ilike(pattern),
                )
            )
            .order_by(User.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def search_count(self, query: str) -> int:
        """Total matching rows for a search query."""
        pattern = f"%{query}%"
        stmt = (
            select(func.count())
            .select_from(User)
            .where(
                or_(
                    User.first_name.ilike(pattern),
                    User.last_name.ilike(pattern),
                    User.email.ilike(pattern),
                    User.phone.ilike(pattern),
                    User.college_name.ilike(pattern),
                )
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    # ========================================================
    # Bulk lookups
    # ========================================================

    async def get_by_shackles_ids(
        self,
        shackles_ids: Sequence[str],
    ) -> list[User]:
        """Fetch multiple users by Shackles ID. Used in bulk team flows."""
        if not shackles_ids:
            return []
        stmt = select(User).where(User.shackles_id.in_(list(shackles_ids)))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())