"""Admin paper submission routes."""

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from shackles.api.deps import CurrentAdmin
from shackles.db.session import get_session
from shackles.schemas.paper_submission import (
    DeadlineUpdate,
    PaperSelectionUpdate,
    PaperSubmissionRead,
)
from shackles.services.paper_submission_service import PaperSubmissionService


router = APIRouter(tags=["admin-papers"])


class BulkDeadlineRequest(BaseModel):
    """Payload for updating a bulk deadline."""

    deadline_iso: str  # ISO 8601 datetime string


@router.get(
    "/events/{event_id}/papers",
    response_model=list[PaperSubmissionRead],
)
async def list_papers(
    event_id: UUID,
    admin: CurrentAdmin,
    session: AsyncSession = Depends(get_session),
) -> list[PaperSubmissionRead]:
    """List all paper submissions for an event."""
    service = PaperSubmissionService(session)
    submissions = await service.list_for_event(event_id)
    return [PaperSubmissionRead.model_validate(s) for s in submissions]


@router.post("/papers/{team_id}/selection", response_model=PaperSubmissionRead)
async def set_selection(
    team_id: UUID,
    payload: PaperSelectionUpdate,
    admin: CurrentAdmin,
    session: AsyncSession = Depends(get_session),
) -> PaperSubmissionRead:
    """Set selection status for one team's submission."""
    service = PaperSubmissionService(session)
    submission = await service.set_selection(
        team_id, payload, admin_id=admin.id
    )
    await session.commit()
    return PaperSubmissionRead.model_validate(submission)


@router.post("/events/{event_id}/papers/publish")
async def publish_results(
    event_id: UUID,
    admin: CurrentAdmin,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Send result notifications to all teams."""
    service = PaperSubmissionService(session)
    result = await service.publish_selection_results(
        event_id, admin_id=admin.id
    )
    await session.commit()
    return result


@router.patch("/events/{event_id}/papers/abstract-deadline")
async def set_abstract_deadline(
    event_id: UUID,
    payload: DeadlineUpdate,
    admin: CurrentAdmin,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Update the abstract deadline for all submissions of an event."""
    service = PaperSubmissionService(session)
    updated = await service.set_abstract_deadline(event_id, payload)
    await session.commit()
    return {"updated": updated}


@router.patch("/events/{event_id}/papers/presentation-deadline")
async def set_presentation_deadline(
    event_id: UUID,
    payload: DeadlineUpdate,
    admin: CurrentAdmin,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Update the presentation deadline for selected teams."""
    service = PaperSubmissionService(session)
    updated = await service.set_presentation_deadline(event_id, payload)
    await session.commit()
    return {"updated": updated}