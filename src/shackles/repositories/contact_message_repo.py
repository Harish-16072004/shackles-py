"""ContactMessageRepository — data access for contact form submissions."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, or_, select

from shackles.models.contact_message import ContactMessage
from shackles.repositories.base import BaseRepository


class ContactMessageRepository(BaseRepository[ContactMessage]):
    """Data access for contact messages."""

    model = ContactMessage

    # ========================================================
    # Lists
    # ========================================================

    async def list_recent(
        self,
        *,
        limit: int = 25,
        offset: int = 0,
    ) -> list[ContactMessage]:
        """List recent messages, newest first.

        This is the primary query for the admin messages page.
        """
        stmt = (
            select(ContactMessage)
            .order_by(ContactMessage.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_user(
        self,
        user_id: UUID,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ContactMessage]:
        """List messages submitted by a logged-in user."""
        stmt = (
            select(ContactMessage)
            .where(ContactMessage.user_id == user_id)
            .order_by(ContactMessage.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_anonymous(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ContactMessage]:
        """List messages from users who weren't logged in."""
        stmt = (
            select(ContactMessage)
            .where(ContactMessage.user_id.is_(None))
            .order_by(ContactMessage.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ========================================================
    # Search
    # ========================================================

    async def search(
        self,
        query: str,
        *,
        limit: int = 25,
        offset: int = 0,
    ) -> list[ContactMessage]:
        """Search messages by sender name, email, or body text."""
        pattern = f"%{query}%"
        stmt = (
            select(ContactMessage)
            .where(
                or_(
                    ContactMessage.name.ilike(pattern),
                    ContactMessage.email.ilike(pattern),
                    ContactMessage.message.ilike(pattern),
                )
            )
            .order_by(ContactMessage.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def search_count(self, query: str) -> int:
        """Count messages matching a search query."""
        pattern = f"%{query}%"
        stmt = (
            select(func.count())
            .select_from(ContactMessage)
            .where(
                or_(
                    ContactMessage.name.ilike(pattern),
                    ContactMessage.email.ilike(pattern),
                    ContactMessage.message.ilike(pattern),
                )
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    # ========================================================
    # Spam / rate-limit helpers
    # ========================================================

    async def count_recent_by_email(
        self,
        email: str,
        since: datetime,
    ) -> int:
        """Count messages from an email since a given timestamp.

        Used by rate-limit checks to reject repeat submissions from the
        same address. `since` should be timezone-aware.
        """
        stmt = (
            select(func.count())
            .select_from(ContactMessage)
            .where(
                func.lower(ContactMessage.email) == email.lower(),
                ContactMessage.created_at >= since,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()