"""EventStaffAssignmentRepository — data access for staff assignments."""

from uuid import UUID

from sqlalchemy import func, select

from shackles.models.enums import StaffRole
from shackles.models.event_staff_assignment import EventStaffAssignment
from shackles.repositories.base import BaseRepository


class EventStaffAssignmentRepository(BaseRepository[EventStaffAssignment]):
    """Data access for event staff assignments."""

    model = EventStaffAssignment

    # ========================================================
    # Lookups
    # ========================================================

    async def get_by_event_user_and_role(
        self,
        event_id: UUID,
        user_id: UUID,
        staff_role: StaffRole | str,
    ) -> EventStaffAssignment | None:
        """Fetch a specific assignment by (event, user, role).

        Uses the composite unique constraint for an index-backed lookup.
        """
        role_value = (
            staff_role.value if isinstance(staff_role, StaffRole) else staff_role
        )
        stmt = select(EventStaffAssignment).where(
            EventStaffAssignment.event_id == event_id,
            EventStaffAssignment.user_id == user_id,
            EventStaffAssignment.staff_role == role_value,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_for_event_and_user(
        self,
        event_id: UUID,
        user_id: UUID,
    ) -> EventStaffAssignment | None:
        """Fetch any assignment for (event, user), regardless of role.

        A user could theoretically be assigned twice (once as coordinator,
        once as volunteer) but in practice the app assigns them once.
        """
        stmt = (
            select(EventStaffAssignment)
            .where(
                EventStaffAssignment.event_id == event_id,
                EventStaffAssignment.user_id == user_id,
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    # ========================================================
    # Existence checks
    # ========================================================

    async def is_assigned(
        self,
        event_id: UUID,
        user_id: UUID,
    ) -> bool:
        """Check whether a user is assigned to an event (any role)."""
        stmt = (
            select(func.count())
            .select_from(EventStaffAssignment)
            .where(
                EventStaffAssignment.event_id == event_id,
                EventStaffAssignment.user_id == user_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() > 0

    async def has_role(
        self,
        event_id: UUID,
        user_id: UUID,
        staff_role: StaffRole | str,
    ) -> bool:
        """Check whether a user has a specific role on an event."""
        role_value = (
            staff_role.value if isinstance(staff_role, StaffRole) else staff_role
        )
        stmt = (
            select(func.count())
            .select_from(EventStaffAssignment)
            .where(
                EventStaffAssignment.event_id == event_id,
                EventStaffAssignment.user_id == user_id,
                EventStaffAssignment.staff_role == role_value,
            )
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
        staff_role: StaffRole | str | None = None,
    ) -> list[EventStaffAssignment]:
        """List all staff assigned to an event, optionally by role."""
        stmt = select(EventStaffAssignment).where(
            EventStaffAssignment.event_id == event_id
        )
        if staff_role is not None:
            role_value = (
                staff_role.value if isinstance(staff_role, StaffRole) else staff_role
            )
            stmt = stmt.where(EventStaffAssignment.staff_role == role_value)
        stmt = stmt.order_by(EventStaffAssignment.staff_role.asc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_user(
        self,
        user_id: UUID,
    ) -> list[EventStaffAssignment]:
        """List all events a staff user is assigned to."""
        stmt = (
            select(EventStaffAssignment)
            .where(EventStaffAssignment.user_id == user_id)
            .order_by(EventStaffAssignment.staff_role.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_coordinators_for_event(
        self,
        event_id: UUID,
    ) -> list[EventStaffAssignment]:
        """List coordinators for an event."""
        return await self.list_by_event(
            event_id, staff_role=StaffRole.COORDINATOR
        )

    async def list_volunteers_for_event(
        self,
        event_id: UUID,
    ) -> list[EventStaffAssignment]:
        """List volunteers for an event."""
        return await self.list_by_event(
            event_id, staff_role=StaffRole.VOLUNTEER
        )

    # ========================================================
    # Counts
    # ========================================================

    async def count_for_event(self, event_id: UUID) -> int:
        """Total staff assigned to an event (all roles)."""
        stmt = (
            select(func.count())
            .select_from(EventStaffAssignment)
            .where(EventStaffAssignment.event_id == event_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def count_by_role_for_event(
        self,
        event_id: UUID,
        staff_role: StaffRole | str,
    ) -> int:
        """Count staff of a specific role on an event."""
        role_value = (
            staff_role.value if isinstance(staff_role, StaffRole) else staff_role
        )
        stmt = (
            select(func.count())
            .select_from(EventStaffAssignment)
            .where(
                EventStaffAssignment.event_id == event_id,
                EventStaffAssignment.staff_role == role_value,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()
        