"""Admin marking routes — criteria, marks, leaderboard."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shackles.api.deps import CurrentAdmin
from shackles.db.session import get_session
from shackles.schemas.marking import (
    JudgeMarkingCreate,
    MarkingCriteriaCreate,
    MarkingCriteriaRead,
)
from shackles.services.marking_service import MarkingService
from pydantic import BaseModel, Field


router = APIRouter(tags=["admin-marking"])


class SubmitMarksRequest(BaseModel):
    judge_id: UUID
    marks: list[JudgeMarkingCreate] = Field(min_length=1)


@router.post(
    "/events/{event_id}/criteria",
    response_model=MarkingCriteriaRead,
    status_code=201,
)
async def create_criteria(
    event_id: UUID,
    payload: MarkingCriteriaCreate,
    admin: CurrentAdmin,
    session: AsyncSession = Depends(get_session),
) -> MarkingCriteriaRead:
    """Create marking criteria + components for an event."""
    service = MarkingService(session)
    criteria = await service.create_criteria(event_id, payload)
    await session.commit()
    return MarkingCriteriaRead.model_validate(criteria)


@router.get(
    "/events/{event_id}/criteria",
    response_model=MarkingCriteriaRead,
)
async def get_criteria(
    event_id: UUID,
    admin: CurrentAdmin,
    session: AsyncSession = Depends(get_session),
) -> MarkingCriteriaRead:
    """Fetch the marking criteria for an event."""
    service = MarkingService(session)
    criteria = await service.get_criteria_for_event(event_id)
    return MarkingCriteriaRead.model_validate(criteria)


@router.post("/events/{event_id}/marks")
async def submit_marks(
    event_id: UUID,
    payload: SubmitMarksRequest,
    admin: CurrentAdmin,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Submit one judge's marks for multiple (team, component) pairs."""
    service = MarkingService(session)
    result = await service.submit_judge_marks(
        event_id=event_id,
        judge_id=payload.judge_id,
        marks=payload.marks,
    )
    await session.commit()
    return result


@router.get("/events/{event_id}/leaderboard")
async def get_leaderboard(
    event_id: UUID,
    admin: CurrentAdmin,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Computed leaderboard for an event."""
    service = MarkingService(session)
    return await service.get_leaderboard(event_id)