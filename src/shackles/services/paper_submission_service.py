"""PaperSubmissionService — abstract → selection → presentation."""

from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from shackles.errors import (
    DEADLINE_PASSED,
    NOT_SELECTED,
    SUBMISSION_NOT_FOUND,
    DomainError,
)
from shackles.models.enums import PaperSelectionStatus
from shackles.repositories.event_repo import EventRepository
from shackles.repositories.paper_submission_repo import (
    PaperSubmissionRepository,
)
from shackles.repositories.team_repo import TeamRepository
from shackles.repositories.user_repo import UserRepository
from shackles.schemas.paper_submission import (
    DeadlineUpdate,
    PaperSelectionUpdate,
)
from shackles.services.notifications import (
    notify_paper_selection_result,
)


class PaperSubmissionService:
    """The two-phase paper pipeline."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.papers = PaperSubmissionRepository(session)
        self.events = EventRepository(session)
        self.teams = TeamRepository(session)
        self.users = UserRepository(session)

    # ========================================================
    # Read
    # ========================================================

    async def get_for_team(self, team_id: UUID):
        """Fetch a team's submission. Raises if not found."""
        return await self.papers.get_by_team_id_or_raise(team_id)

    async def list_for_event(self, event_id: UUID):
        """List all submissions for an event."""
        return await self.papers.list_for_event(event_id)

    # ========================================================
    # Phase 1 — Abstract
    # ========================================================

    async def upload_abstract(
        self,
        *,
        team_id: UUID,
        acting_user_id: UUID,
        abstract_url: str,
    ):
        """Record an abstract upload.

        Authorization: only the team leader may upload.

        Raises:
            DomainError if deadline passed or uploader isn't the leader.
        """
        team = await self.teams.get(team_id)
        if team is None:
            raise DomainError("TEAM_NOT_FOUND", "Team not found.")

        if team.leader_user_id != acting_user_id:
            raise DomainError(
                "UNAUTHORIZED",
                "Only the team leader can upload documents.",
            )

        submission = await self.papers.get_by_team_id_or_raise(team_id)

        # Deadline enforcement
        if submission.abstract_deadline is not None:
            if datetime.now(submission.abstract_deadline.tzinfo) > submission.abstract_deadline:
                raise DomainError(
                    DEADLINE_PASSED,
                    "The abstract submission deadline has passed.",
                )

        return await self.papers.set_abstract(team_id, abstract_url)

    # ========================================================
    # Phase 2 — Selection (admin)
    # ========================================================

    async def set_selection(
        self,
        team_id: UUID,
        data: PaperSelectionUpdate,
        *,
        admin_id: UUID,
    ):
        """Set the selection status for one team. Admin action."""
        return await self.papers.set_selection(
            team_id=team_id,
            status=data.status,
            selected_by=str(admin_id),
            selection_note=data.selection_note,
        )

    async def publish_selection_results(
        self,
        event_id: UUID,
        *,
        admin_id: UUID,
    ) -> dict:
        """Notify all teams of their selection result.

        Assumes per-team statuses have already been set. This method
        dispatches notifications (currently stubbed) for every team
        whose status is SELECTED or REJECTED.
        """
        event = await self.events.get(event_id)
        if event is None:
            raise DomainError("EVENT_NOT_FOUND", "Event not found.")

        submissions = await self.papers.list_for_event(event_id)

        notified = 0
        for submission in submissions:
            if submission.selection_status == PaperSelectionStatus.PENDING.value:
                continue

            team = submission.team
            members = await self._get_team_members(team.id)

            for member in members:
                await notify_paper_selection_result(
                    member_email=member.email,
                    member_name=f"{member.first_name} {member.last_name}".strip(),
                    team_name=team.name,
                    event_name=event.name,
                    selection_status=submission.selection_status,
                    selection_note=submission.selection_note,
                    presentation_deadline=(
                        submission.presentation_deadline.isoformat()
                        if submission.presentation_deadline
                        else None
                    ),
                )
                notified += 1

        return {"teams_notified": len(submissions), "emails_queued": notified}

    # ========================================================
    # Phase 3 — Presentation
    # ========================================================

    async def upload_presentation(
        self,
        *,
        team_id: UUID,
        acting_user_id: UUID,
        presentation_url: str,
    ):
        """Record a presentation upload. Only for SELECTED teams."""
        team = await self.teams.get(team_id)
        if team is None:
            raise DomainError("TEAM_NOT_FOUND", "Team not found.")

        if team.leader_user_id != acting_user_id:
            raise DomainError(
                "UNAUTHORIZED",
                "Only the team leader can upload documents.",
            )

        submission = await self.papers.get_by_team_id_or_raise(team_id)

        if submission.selection_status != PaperSelectionStatus.SELECTED.value:
            raise DomainError(
                NOT_SELECTED,
                "Your team must be selected before uploading a presentation.",
            )

        if submission.presentation_deadline is not None:
            if datetime.now(submission.presentation_deadline.tzinfo) > submission.presentation_deadline:
                raise DomainError(
                    DEADLINE_PASSED,
                    "The presentation submission deadline has passed.",
                )

        return await self.papers.set_presentation(team_id, presentation_url)

    # ========================================================
    # Deadlines (admin)
    # ========================================================

    async def set_abstract_deadline(
        self,
        event_id: UUID,
        data: DeadlineUpdate,
    ) -> int:
        """Set the abstract deadline for all submissions of an event."""
        return await self.papers.set_abstract_deadline_for_event(
            event_id, data.deadline
        )

    async def set_presentation_deadline(
        self,
        event_id: UUID,
        data: DeadlineUpdate,
    ) -> int:
        """Set the presentation deadline for selected teams only."""
        return await self.papers.set_presentation_deadline_for_event(
            event_id, data.deadline
        )

    # ========================================================
    # Stats
    # ========================================================

    async def get_stats(self, event_id: UUID) -> dict:
        """Return submission counts for the admin dashboard."""
        return {
            "total": await self.papers.count_for_event(event_id),
            "abstracts_submitted": await self.papers.count_abstracts_submitted(event_id),
            "selected": await self.papers.count_by_status(
                event_id, PaperSelectionStatus.SELECTED
            ),
            "rejected": await self.papers.count_by_status(
                event_id, PaperSelectionStatus.REJECTED
            ),
            "presentations_submitted": await self.papers.count_presentations_submitted(
                event_id
            ),
        }

    # ========================================================
    # Private
    # ========================================================

    async def _get_team_members(self, team_id: UUID):
        from shackles.repositories.event_registration_repo import (
            EventRegistrationRepository,
        )
        reg_repo = EventRegistrationRepository(self.session)
        regs = await reg_repo.list_by_team(team_id)
        return [reg.user for reg in regs if reg.user is not None]