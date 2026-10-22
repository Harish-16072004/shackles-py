"""Admin crew assignment routes."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shackles.api.deps import CurrentAdmin
from shackles.db.session import get_session
from shackles.errors import ALREADY_EXISTS, NOT_FOUND, DomainError
from shackles.models.enums import Role
from shackles.repositories.event_staff_assignment_repo import (
    EventStaffAssignmentRepository,
)
from shackles.repositories.user_repo import UserRepository
from shackles.schemas.common import MessageResponse
from shackles.schemas.event_staff_assignment import (
    StaffAssignmentCreate,
    StaffAssignmentRead,
    StaffUserCreate,
)
from shackles.schemas.user import UserRead
from shackles.services.auth_service import AuthService


router = APIRouter(tags=["admin-staff"])


@router.post("/staff", response_model=UserRead, status_code=201)
async def create_staff(
    payload: StaffUserCreate,
    admin: CurrentAdmin,
    session: AsyncSession = Depends(get_session),
) -> UserRead:
    """Create a new coordinator or volunteer account."""
    from shackles.schemas.user import UserCreate

    # Reuse AuthService registration with a forced role
    user_payload = UserCreate(
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        phone=payload.phone,
        password=payload.password,
        college_name="Staff",
        college_loc="Event",
        department="Operations",
        year_of_study="Staff",
        gender=None,
    )
    role = Role.COORDINATOR if payload.role.value == "COORDINATOR" else Role.VOLUNTEER
    service = AuthService(session)
    user = await service.register(user_payload, role=role)
    await session.commit()
    return UserRead.model_validate(user)


@router.post(
    "/events/{event_id}/staff",
    response_model=StaffAssignmentRead,
    status_code=201,
)
async def assign_staff(
    event_id: UUID,
    payload: StaffAssignmentCreate,
    admin: CurrentAdmin,
    session: AsyncSession = Depends(get_session),
) -> StaffAssignmentRead:
    """Assign an existing user to an event with a staff role."""
    user_repo = UserRepository(session)
    user = await user_repo.get(payload.user_id)
    if user is None:
        raise DomainError(NOT_FOUND, "User not found.")
    if user.role not in (Role.COORDINATOR.value, Role.VOLUNTEER.value):
        raise DomainError(
            "INVALID_INPUT",
            "User is not a staff member.",
        )

    repo = EventStaffAssignmentRepository(session)
    existing = await repo.get_by_event_user_and_role(
        event_id, payload.user_id, payload.staff_role
    )
    if existing is not None:
        raise DomainError(
            ALREADY_EXISTS,
            "Staff member is already assigned to this event with this role.",
        )

    assignment = await repo.create(
        event_id=event_id,
        user_id=payload.user_id,
        staff_role=payload.staff_role.value,
    )
    await session.commit()
    return StaffAssignmentRead.model_validate(assignment)


@router.delete(
    "/events/{event_id}/staff/{user_id}",
    response_model=MessageResponse,
)
async def remove_staff(
    event_id: UUID,
    user_id: UUID,
    admin: CurrentAdmin,
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    """Remove a staff assignment."""
    repo = EventStaffAssignmentRepository(session)
    existing = await repo.get_for_event_and_user(event_id, user_id)
    if existing is None:
        raise DomainError(NOT_FOUND, "Assignment not found.")
    await repo.delete(existing.id)
    await session.commit()
    return MessageResponse(message="Staff assignment removed.")


@router.get(
    "/events/{event_id}/staff",
    response_model=list[StaffAssignmentRead],
)
async def list_staff(
    event_id: UUID,
    admin: CurrentAdmin,
    session: AsyncSession = Depends(get_session),
) -> list[StaffAssignmentRead]:
    """List all staff assigned to an event."""
    repo = EventStaffAssignmentRepository(session)
    rows = await repo.list_by_event(event_id)
    return [StaffAssignmentRead.model_validate(r) for r in rows]