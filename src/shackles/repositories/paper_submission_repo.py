"""PaperSubmissionRepository — data access for the paper pipeline.

Handles the two-phase flow:
  1. Abstract upload (when the team locks for a document-submission event)
  2. Selection by admin (SELECTED or REJECTED)
  3. Presentation upload (only for selected teams)
"""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import selectinload

from shackles.errors import SUBMISSION_NOT_FOUND, DomainError
from shackles.models.enums import PaperSelectionStatus
from shackles.models.paper_submission import PaperSubmission
from shackles.repositories.base import BaseRepository


class PaperSubmissionRepository(BaseRepository[PaperSubmission]):
    """Data access for paper submissions."""

    model = PaperSubmission

    # ========================================================
    # Lookups
    # ========================================================

    async def get_by_team_id(
        self, team_id: UUID
    ) -> PaperSubmission | None:
        """Fetch the submission for a team (unique per team)."""
        stmt = select(PaperSubmission).where(
            PaperSubmission.team_id == team_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_team_id_or_raise(
        self, team_id: UUID
    ) -> PaperSubmission:
        """Fetch by team. Raises if not found."""
        submission = await self.get_by_team_id(team_id)
        if submission is None:
            raise DomainError(
                SUBMISSION_NOT_FOUND,
                "No paper submission record for this team.",
                {"team_id": str(team_id)},
            )
        return submission

    async def get_with_team(
        self, submission_id: UUID
    ) -> PaperSubmission | None:
        """Fetch a submission with its team eagerly loaded."""
        stmt = (
            select(PaperSubmission)
            .where(PaperSubmission.id == submission_id)
            .options(selectinload(PaperSubmission.team))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    # ========================================================
    # Creation
    # ========================================================

    async def get_or_create_for_team(
        self,
        team_id: UUID,
        event_id: UUID,
        abstract_deadline: datetime | None = None,
    ) -> PaperSubmission:
        """Idempotently create the submission row for a team.

        Called when a team locks in a document-submission event. If the
        row already exists, returns it unchanged.
        """
        existing = await self.get_by_team_id(team_id)
        if existing is not None:
            return existing

        obj = PaperSubmission(
            team_id=team_id,
            event_id=event_id,
            selection_status=PaperSelectionStatus.PENDING.value,
            abstract_deadline=abstract_deadline,
        )
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    # ========================================================
    # Phase 1 — Abstract
    # ========================================================

    async def set_abstract(
        self,
        team_id: UUID,
        abstract_url: str,
    ) -> PaperSubmission:
        """Record a successful abstract upload.

        Sets abstract_url and abstract_submitted_at. Does not check the
        deadline — that's the service layer's responsibility.
        """
        submission = await self.get_by_team_id_or_raise(team_id)
        submission.abstract_url = abstract_url
        submission.abstract_submitted_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.session.refresh(submission)
        return submission

    # ========================================================
    # Phase 2 — Selection
    # ========================================================

    async def set_selection(
        self,
        team_id: UUID,
        status: PaperSelectionStatus,
        selected_by: str,
        selection_note: str | None = None,
    ) -> PaperSubmission:
        """Record an admin's selection decision."""
        submission = await self.get_by_team_id_or_raise(team_id)
        now = datetime.now(timezone.utc)

        submission.selection_status = status.value
        submission.selected_at = (
            None if status == PaperSelectionStatus.PENDING else now
        )
        submission.selected_by = (
            None if status == PaperSelectionStatus.PENDING else selected_by
        )
        submission.selection_note = selection_note

        await self.session.flush()
        await self.session.refresh(submission)
        return submission

    # ========================================================
    # Phase 3 — Presentation
    # ========================================================

    async def set_presentation(
        self,
        team_id: UUID,
        presentation_url: str,
    ) -> PaperSubmission:
        """Record a successful presentation upload."""
        submission = await self.get_by_team_id_or_raise(team_id)
        submission.presentation_url = presentation_url
        submission.presentation_submitted_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.session.refresh(submission)
        return submission

    # ========================================================
    # Lists
    # ========================================================

    async def list_for_event(
        self,
        event_id: UUID,
        *,
        limit: int = 500,
        offset: int = 0,
    ) -> list[PaperSubmission]:
        """List all submissions for an event, with team + leader loaded."""
        stmt = (
            select(PaperSubmission)
            .where(PaperSubmission.event_id == event_id)
            .options(selectinload(PaperSubmission.team))
            .order_by(PaperSubmission.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_selection_status(
        self,
        event_id: UUID,
        status: PaperSelectionStatus,
        *,
        limit: int = 500,
    ) -> list[PaperSubmission]:
        """List submissions filtered by selection status."""
        stmt = (
            select(PaperSubmission)
            .where(
                PaperSubmission.event_id == event_id,
                PaperSubmission.selection_status == status.value,
            )
            .options(selectinload(PaperSubmission.team))
            .order_by(PaperSubmission.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_selected_for_event(
        self, event_id: UUID
    ) -> list[PaperSubmission]:
        """List only the selected teams' submissions."""
        return await self.list_by_selection_status(
            event_id, PaperSelectionStatus.SELECTED
        )

    async def list_with_abstract_submitted(
        self, event_id: UUID
    ) -> list[PaperSubmission]:
        """List submissions that have an abstract on file.

        Used by the "download all abstracts" bulk export.
        """
        stmt = (
            select(PaperSubmission)
            .where(
                PaperSubmission.event_id == event_id,
                PaperSubmission.abstract_url.isnot(None),
            )
            .options(selectinload(PaperSubmission.team))
            .order_by(PaperSubmission.team_id.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ========================================================
    # Counts (for admin dashboard stats)
    # ========================================================

    async def count_for_event(self, event_id: UUID) -> int:
        """Total submissions for an event."""
        stmt = (
            select(func.count())
            .select_from(PaperSubmission)
            .where(PaperSubmission.event_id == event_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def count_by_status(
        self,
        event_id: UUID,
        status: PaperSelectionStatus,
    ) -> int:
        """Count submissions with a given selection status."""
        stmt = (
            select(func.count())
            .select_from(PaperSubmission)
            .where(
                PaperSubmission.event_id == event_id,
                PaperSubmission.selection_status == status.value,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def count_abstracts_submitted(self, event_id: UUID) -> int:
        """Count submissions with an abstract on file."""
        stmt = (
            select(func.count())
            .select_from(PaperSubmission)
            .where(
                PaperSubmission.event_id == event_id,
                PaperSubmission.abstract_submitted_at.isnot(None),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def count_presentations_submitted(self, event_id: UUID) -> int:
        """Count submissions with a presentation on file."""
        stmt = (
            select(func.count())
            .select_from(PaperSubmission)
            .where(
                PaperSubmission.event_id == event_id,
                PaperSubmission.presentation_url.isnot(None),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    # ========================================================
    # Bulk deadline updates
    # ========================================================

    async def set_abstract_deadline_for_event(
        self,
        event_id: UUID,
        deadline: datetime,
    ) -> int:
        """Update the abstract deadline for all submissions of an event.

        Returns the number of rows updated.
        """
        stmt = (
            update(PaperSubmission)
            .where(PaperSubmission.event_id == event_id)
            .values(abstract_deadline=deadline)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount or 0

    async def set_presentation_deadline_for_event(
        self,
        event_id: UUID,
        deadline: datetime,
    ) -> int:
        """Update the presentation deadline for selected teams only.

        Only touches submissions whose status is SELECTED, since only
        those teams are expected to upload a presentation.
        """
        stmt = (
            update(PaperSubmission)
            .where(
                PaperSubmission.event_id == event_id,
                PaperSubmission.selection_status
                == PaperSelectionStatus.SELECTED.value,
            )
            .values(presentation_deadline=deadline)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount or 0

    # ========================================================
    # Validity helpers
    # ========================================================

    async def is_abstract_deadline_passed(self, team_id: UUID) -> bool:
        """Check whether the abstract deadline has passed for a team.

        Returns False if no deadline is set (deadline is optional).
        """
        submission = await self.get_by_team_id(team_id)
        if submission is None or submission.abstract_deadline is None:
            return False
        return datetime.now(timezone.utc) > submission.abstract_deadline

    async def is_presentation_deadline_passed(self, team_id: UUID) -> bool:
        """Check whether the presentation deadline has passed for a team."""
        submission = await self.get_by_team_id(team_id)
        if submission is None or submission.presentation_deadline is None:
            return False
        return datetime.now(timezone.utc) > submission.presentation_deadline