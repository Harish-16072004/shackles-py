"""UserService — profile reads/updates and admin user management."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from shackles.errors import FORBIDDEN, NOT_FOUND, DomainError
from shackles.models.enums import Role
from shackles.models.user import User
from shackles.repositories.user_repo import UserRepository
from shackles.schemas.user import UserUpdate


class UserService:
    """Read/update user profiles, role changes, admin listing."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)

    # ========================================================
    # Profile
    # ========================================================

    async def get_profile(self, user_id: UUID) -> User:
        """Fetch a user by ID. Raises if not found."""
        user = await self.users.get(user_id)
        if user is None:
            raise DomainError(
                NOT_FOUND,
                "User not found.",
                {"user_id": str(user_id)},
            )
        return user

    async def update_profile(
        self,
        user_id: UUID,
        data: UserUpdate,
    ) -> User:
        """Update the given user's profile fields.

        Only applies fields that are present in `data`. Uniqueness
        checks apply if `phone` is being changed.
        """
        user = await self.get_profile(user_id)

        # Only apply fields that were provided (not None)
        updates = data.model_dump(exclude_unset=True)

        # If phone is being updated, check uniqueness
        new_phone = updates.get("phone")
        if new_phone and new_phone != user.phone:
            if await self.users.phone_exists(new_phone):
                raise DomainError(
                    "PHONE_ALREADY_EXISTS",
                    "Another account already uses this phone number.",
                    {"phone": new_phone},
                )

        for field, value in updates.items():
            setattr(user, field, value)

        await self.session.flush()
        await self.session.refresh(user)
        return user

    # ========================================================
    # Admin actions
    # ========================================================

    async def list_users(
        self,
        *,
        role: Role | None = None,
        search: str | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> tuple[list[User], int]:
        """List users (admin). Returns (rows, total_count)."""
        if search:
            rows = await self.users.search(search, limit=limit, offset=offset)
            total = await self.users.search_count(search)
            return rows, total

        if role is not None:
            rows = await self.users.list_by_role(
                role, limit=limit, offset=offset
            )
            # Note: no dedicated count_by_role; use search_count with role filter
            total = await self.session.scalar(
                __import__("sqlalchemy").select(
                    __import__("sqlalchemy").func.count()
                ).select_from(User).where(User.role == role.value)
            ) or 0
            return rows, total

        rows = await self.users.list(limit=limit, offset=offset)
        total = await self.users.count()
        return rows, total

    async def set_role(
        self,
        user_id: UUID,
        new_role: Role,
        *,
        acting_user_id: UUID,
    ) -> User:
        """Change a user's role. Admin-only in the API layer.

        Refuses to demote the last remaining admin.
        """
        user = await self.get_profile(user_id)

        # If demoting an admin, ensure there's another admin left
        if user.role == Role.ADMIN.value and new_role != Role.ADMIN:
            if user_id == acting_user_id:
                raise DomainError(
                    FORBIDDEN,
                    "You cannot change your own role away from ADMIN.",
                )

            remaining = await self.users.list_by_role(
                Role.ADMIN, limit=2, offset=0
            )
            if len(remaining) <= 1:
                raise DomainError(
                    FORBIDDEN,
                    "Cannot demote the last remaining admin.",
                )

        user.role = new_role.value
        await self.session.flush()
        await self.session.refresh(user)
        return user