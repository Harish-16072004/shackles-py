"""TeamInviteRepository — data access for team invitations."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import delete, func, select

from shackles.models.team_invite import TeamInvite
from shackles.repositories.base import BaseRepository


class TeamInviteRepository(BaseRepository[TeamInvite]):
    """Data access for team invites."""

    model = TeamInvite

    # ========================================================
    # Lookups
    # ========================================================

    async def get_by_token(self, token: str) -> TeamInvite | None:
        """Fetch an invite by its token (used when clicking an invite link)."""
        stmt = select(TeamInvite).where(TeamInvite.token == token)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_active_for_team(self, team_id: UUID) -> list[TeamInvite]:
        """List unused, unexpired invites for a team."""
        now = datetime.now(timezone.utc)
        stmt = (
            select(TeamInvite)
            .where(
                TeamInvite.team_id == team_id,
                TeamInvite.used_at.is_(None),
                TeamInvite.expires_at > now,
            )
            .order_by(TeamInvite.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_for_team(
        self,
        team_id: UUID,
        *,
        limit: int = 100,
    ) -> list[TeamInvite]:
        """List all invites for a team, used and unused."""
        stmt = (
            select(TeamInvite)
            .where(TeamInvite.team_id == team_id)
            .order_by(TeamInvite.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ========================================================
    # Uniqueness / validity
    # ========================================================

    async def has_active_invite_for_email(
        self,
        team_id: UUID,
        invited_email: str,
    ) -> bool:
        """Check whether an active invite already exists for this email.

        Prevents duplicate invites from spamming a user.
        """
        now = datetime.now(timezone.utc)
        stmt = (
            select(func.count())
            .select_from(TeamInvite)
            .where(
                TeamInvite.team_id == team_id,
                func.lower(TeamInvite.invited_email) == invited_email.lower(),
                TeamInvite.used_at.is_(None),
                TeamInvite.expires_at > now,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() > 0

    async def is_valid(self, invite: TeamInvite) -> bool:
        """Check an invite object's validity (used, expired)."""
        if invite.used_at is not None:
            return False
        return invite.expires_at > datetime.now(timezone.utc)

    # ========================================================
    # Counts
    # ========================================================

    async def count_by_team(self, team_id: UUID) -> int:
        """Total invites (used + unused) for a team."""
        stmt = (
            select(func.count())
            .select_from(TeamInvite)
            .where(TeamInvite.team_id == team_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    # ========================================================
    # Cleanup
    # ========================================================

    async def delete_expired(self) -> int:
        """Delete all invites whose expiry has passed.

        Returns the number of rows deleted. Run periodically via a
        scheduled job.
        """
        now = datetime.now(timezone.utc)
        stmt = delete(TeamInvite).where(
            TeamInvite.expires_at < now,
            TeamInvite.used_at.is_(None),
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount or 0
        