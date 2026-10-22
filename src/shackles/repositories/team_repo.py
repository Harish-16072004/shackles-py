"""TeamRepository — data access for teams."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from shackles.errors import TEAM_NOT_FOUND, DomainError
from shackles.models.enums import TeamStatus
from shackles.models.team import Team
from shackles.repositories.base import BaseRepository


class TeamRepository(BaseRepository[Team]):
    """Data access for teams."""

    model = Team

    # ========================================================
    # Lookups
    # ========================================================

    async def get_by_event_and_name(
        self,
        event_id: UUID,
        name_normalized: str,
    ) -> Team | None:
        """Fetch a team by (event_id, normalized name)."""
        stmt = select(Team).where(
            Team.event_id == event_id,
            Team.name_normalized == name_normalized,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_team_code(
        self,
        event_id: UUID,
        team_code: str,
    ) -> Team | None:
        """Fetch a team by (event_id, team_code).

        team_code is what participants share with teammates; it's unique
        per event.
        """
        stmt = select(Team).where(
            Team.event_id == event_id,
            Team.team_code == team_code,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_join_code(self, join_code: str) -> Team | None:
        """Fetch a team by its global join code.

        join_code is a global unique string used in invite links.
        """
        stmt = select(Team).where(Team.join_code == join_code)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_members(self, team_id: UUID) -> Team | None:
        """Fetch a team with its members eagerly loaded."""
        from shackles.models.event_registration import EventRegistration

        stmt = (
            select(Team)
            .where(Team.id == team_id)
            .options(
                selectinload(Team.members).selectinload(
                    EventRegistration.user
                )
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_members_or_raise(self, team_id: UUID) -> Team:
        """Same as get_with_members but raises if not found."""
        team = await self.get_with_members(team_id)
        if team is None:
            raise DomainError(
                TEAM_NOT_FOUND,
                "Team not found.",
                {"team_id": str(team_id)},
            )
        return team

    # ========================================================
    # Uniqueness checks
    # ========================================================

    async def team_name_exists(
        self,
        event_id: UUID,
        name_normalized: str,
    ) -> bool:
        """Check whether a team with this normalized name exists."""
        stmt = (
            select(func.count())
            .select_from(Team)
            .where(
                Team.event_id == event_id,
                Team.name_normalized == name_normalized,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() > 0

    async def team_code_exists(
        self,
        event_id: UUID,
        team_code: str,
    ) -> bool:
        """Check whether a team code exists for this event."""
        stmt = (
            select(func.count())
            .select_from(Team)
            .where(
                Team.event_id == event_id,
                Team.team_code == team_code,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() > 0

    async def join_code_exists(self, join_code: str) -> bool:
        """Check whether a join code exists globally."""
        stmt = (
            select(func.count())
            .select_from(Team)
            .where(Team.join_code == join_code)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() > 0

    # ========================================================
    # Lists
    # ========================================================

    async def list_by_event(
        self,
        event_id: UUID,
        *,
        status: TeamStatus | str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Team]:
        """List teams for an event, optionally filtered by status."""
        stmt = select(Team).where(Team.event_id == event_id)
        if status is not None:
            status_value = (
                status.value if isinstance(status, TeamStatus) else status
            )
            stmt = stmt.where(Team.status == status_value)
        stmt = (
            stmt.order_by(Team.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_open_for_event(self, event_id: UUID) -> list[Team]:
        """List teams that are still open for new members."""
        return await self.list_by_event(
            event_id,
            status=TeamStatus.OPEN,
            limit=200,
        )

    async def list_locked_for_event(self, event_id: UUID) -> list[Team]:
        """List fully locked teams (used for marking, scoring, reports)."""
        return await self.list_by_event(
            event_id,
            status=TeamStatus.LOCKED,
            limit=500,
        )

    async def list_led_by_user(
        self,
        user_id: UUID,
    ) -> list[Team]:
        """List teams where this user is the leader."""
        stmt = (
            select(Team)
            .where(Team.leader_user_id == user_id)
            .order_by(Team.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ========================================================
    # Counts
    # ========================================================

    async def count_for_event(
        self,
        event_id: UUID,
        *,
        exclude_cancelled: bool = True,
    ) -> int:
        """Count teams for an event (excluding cancelled by default)."""
        stmt = select(func.count()).select_from(Team).where(Team.event_id == event_id)
        if exclude_cancelled:
            stmt = stmt.where(Team.status != TeamStatus.CANCELLED.value)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    # ========================================================
    # Optimistic-locking helpers
    # ========================================================

    async def try_lock(
        self,
        team_id: UUID,
        locked_by: str,
    ) -> bool:
        """Attempt to lock a team. Returns True on success.

        Uses `UPDATE WHERE status = OPEN` to avoid double-lock races
        under concurrent requests. Returns False if the team was
        already locked by someone else (or is no longer OPEN).
        """
        from datetime import datetime, timezone
        from sqlalchemy import update

        stmt = (
            update(Team)
            .where(
                Team.id == team_id,
                Team.status == TeamStatus.OPEN.value,
            )
            .values(
                status=TeamStatus.LOCKED.value,
                locked_at=datetime.now(timezone.utc),
                locked_by=locked_by,
                join_code=None,
                join_code_expires_at=None,
            )
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0

    async def increment_member_count(self, team_id: UUID) -> None:
        """Atomically increment the team's member count by 1."""
        from sqlalchemy import update

        stmt = (
            update(Team)
            .where(Team.id == team_id)
            .values(member_count=Team.member_count + 1)
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def set_member_count(self, team_id: UUID, count: int) -> None:
        """Set the exact member count (used after bulk imports)."""
        team = await self.get_or_raise(team_id, code=TEAM_NOT_FOUND)
        team.member_count = count
        await self.session.flush()

    async def cancel_team(self, team_id: UUID) -> bool:
        """Cancel a team. Returns True on success."""
        from datetime import datetime, timezone
        from sqlalchemy import update

        stmt = (
            update(Team)
            .where(
                Team.id == team_id,
                Team.status != TeamStatus.CANCELLED.value,
            )
            .values(
                status=TeamStatus.CANCELLED.value,
                cancelled_at=datetime.now(timezone.utc),
            )
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0